import csv
import sys
import threading
import time

from conexion import (conectar_mysql, guardar_registros,
                      guardar_resultados, guardar_tiempo)
import mysql.connector

ids = []
edad = []
sexo = []
creatinina = []
urea = []

try:
    archivo = open('datos_renales_5000.csv', 'r', encoding="utf-8-sig", newline="")
except OSError:
    print("error")
    sys.exit(1)

print("el archivo es")

with archivo:

    lector = csv.reader(archivo)
    next(lector)

    for fila in lector:
        if not fila:
            continue
        ids.append(int(fila[0]))
        edad.append(int(fila[1]))
        sexo.append(fila[2].strip())
        creatinina.append(float(fila[3]))
        urea.append(float(fila[4]))

print("Dataset cargado correctamente")
print("Total procesado: ", len(ids))

total = len(ids)

if total != 5000:
    print("ERROR NO SE CARGO LOS ELEMENTOS NECESARIOS")
    sys.exit(1)

tfge = [0.0] * total
creatininaUmol = [0.0] * total
ureaMmol = [0.0] * total

tercio = total // 3

inicioh1 = 0
finh1 = tercio
inicioh2 = tercio
finh2 = tercio * 2
inicioh3 = tercio * 2
finh3 = total

bloques = [(inicioh1, finh1), (inicioh2, finh2), (inicioh3, finh3)]

def calcular_tfge(inicioBloque, finBloque):
    for i in range(inicioBloque, finBloque):
        if sexo[i] == "Mujer":
            k = 0.7
            a = -0.241
            factor = 1.012
        else:
            k = 0.9
            a = -0.302
            factor = 1.0
        cociente = creatinina[i] / k
        tfge[i] = (142 * min(cociente, 1) ** a * max(cociente, 1) ** -1.200
                   * 0.9938 ** edad[i] * factor)

def convertir_creatinina(inicioBloque, finBloque):
    for i in range(inicioBloque, finBloque):
        creatininaUmol[i] = creatinina[i] * 88.4

def convertir_urea(inicioBloque, finBloque):
    for i in range(inicioBloque, finBloque):
        ureaMmol[i] = urea[i] * 0.1665

# Cada hilo ejecuta una instruccion distinta (MIMD) y en cada ronda trabaja
# sobre un bloque de datos distinto al de los otros hilos. Tras 3 rondas,
# los 3 indicadores quedan calculados para todos los registros.
instrucciones = [calcular_tfge, convertir_creatinina, convertir_urea]

def trabajo_hilo(n):
    for ronda in range(3):
        inicioBloque, finBloque = bloques[(n + ronda) % 3]
        instrucciones[n](inicioBloque, finBloque)

def clasificar_estadio(valor):
    valor = round(valor, 2)
    if valor >= 90:
        return "G1"
    if valor >= 60:
        return "G2"
    if valor >= 45:
        return "G3a"
    if valor >= 30:
        return "G3b"
    if valor >= 15:
        return "G4"
    return "G5"

h1 = threading.Thread(target=trabajo_hilo, args=(0,))
h2 = threading.Thread(target=trabajo_hilo, args=(1,))
h3 = threading.Thread(target=trabajo_hilo, args=(2,))

inicio = time.perf_counter_ns()

h1.start()
h2.start()
h3.start()

h1.join()
h2.join()
h3.join()

fin = time.perf_counter_ns()
tiempo = (fin - inicio) / 1000

print("Hilo 1 (TFGe): bloque", inicioh1, "a", finh1 - 1)
print("Hilo 2 (Creatinina): bloque", inicioh2, "a", finh2 - 1)
print("Hilo 3 (Urea): bloque", inicioh3, "a", finh3 - 1)

print("=============Resultado=============")

for i in range(total):
    print("REGISTRO:          ", ids[i],
          "/EDAD:          ", edad[i],
          "/SEXO:          ", sexo[i],
          "/CREATININA mg/dL:          ", creatinina[i],
          "/UREA mg/dL:          ", urea[i],
          "/TFGE:          ", round(tfge[i], 2),
          "/CREATININA umol/L:          ", round(creatininaUmol[i], 2),
          "/UREA mmol/L:          ", round(ureaMmol[i], 3))

print("\n-----------------------------------")
print("Registros realizados: ", total)
print(f"Tiempo de ejecucion: {tiempo:.4f} microsegundos")


conexion = None

try:
    conexion = conectar_mysql()
    print("\nConexion exitosa a la base de datos MySQL")

    registros = [(ids[i], edad[i], sexo[i], creatinina[i], urea[i])
                 for i in range(total)]
    guardar_registros(conexion, registros)

    resultados = [(ids[i],
                   round(tfge[i], 2),
                   round(creatininaUmol[i], 2),
                   round(ureaMmol[i], 3),
                   clasificar_estadio(tfge[i]))
                  for i in range(total)]
    guardar_resultados(conexion, "MIMD", resultados)

    guardar_tiempo(conexion, "MIMD", tiempo / 1000, total, 3)

    print("Datos insertados correctamente en la base de datos MySQL")
    print("Numero de registros insertados: ", total)

except (mysql.connector.Error, RuntimeError) as error:
    if conexion is not None:
        conexion.rollback()
    print("Error al insertar datos en la base de datos MySQL: ", error)

finally:
    if conexion is not None:
        conexion.close()