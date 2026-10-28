import csv
import sys
import threading
import time

from conexion import (conectar_mysql, guardarRegistros,
                      guardarResultados, guardarTiempo)
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

print("dataset cargado correctamente")
print("total procesado: ", len(ids))

total = len(ids)

if total != 5000:
    print("error no se cargo los elementos necesarios")
    sys.exit(1)

tfge = [0.0] * total
creatininaUmol = [0.0] * total
ureaMmol = [0.0] * total

tercio = total // 3

inicioH1 = 0
finH1 = tercio
inicioH2 = tercio
finH2 = tercio * 2
inicioH3 = tercio * 2
finH3 = total

bloques = [(inicioH1, finH1), (inicioH2, finH2), (inicioH3, finH3)]

def calcularTfge(inicioBloque, finBloque):
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

def convertirCreatinina(inicioBloque, finBloque):
    for i in range(inicioBloque, finBloque):
        creatininaUmol[i] = creatinina[i] * 88.4

def convertirUrea(inicioBloque, finBloque):
    for i in range(inicioBloque, finBloque):
        ureaMmol[i] = urea[i] * 0.1665

instrucciones = [calcularTfge, convertirCreatinina, convertirUrea]

def trabajoHilo(n):
    for ronda in range(3):
        inicioBloque, finBloque = bloques[(n + ronda) % 3]
        instrucciones[n](inicioBloque, finBloque)

def clasificarEstadio(valor):
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

h1 = threading.Thread(target=trabajoHilo, args=(0,))
h2 = threading.Thread(target=trabajoHilo, args=(1,))
h3 = threading.Thread(target=trabajoHilo, args=(2,))

inicio = time.perf_counter_ns()

h1.start()
h2.start()
h3.start()

h1.join()
h2.join()
h3.join()

fin = time.perf_counter_ns()
tiempo = (fin - inicio) / 1000

print("hilo 1 tfge: bloque", inicioH1, "a", finH1 - 1)
print("hilo 2 creatinina: bloque", inicioH2, "a", finH2 - 1)
print("hilo 3 urea: bloque", inicioH3, "a", finH3 - 1)

print("=============resultado=============")

for i in range(total):
    print("registro:          ", ids[i],
          "/edad:          ", edad[i],
          "/sexo:          ", sexo[i],
          "/creatinina mg/dl:          ", creatinina[i],
          "/urea mg/dl:          ", urea[i],
          "/tfge:          ", round(tfge[i], 2),
          "/creatinina umol/l:          ", round(creatininaUmol[i], 2),
          "/urea mmol/l:          ", round(ureaMmol[i], 3))

print("\n-----------------------------------")
print("registros realizados: ", total)
print(f"tiempo de ejecucion: {tiempo:.4f} microsegundos")


conexion = None

try:
    conexion = conectar_mysql()
    print("\nconexion exitosa a la base de datos mysql")

    registros = [(ids[i], edad[i], sexo[i], creatinina[i], urea[i])
                 for i in range(total)]
    guardarRegistros(conexion, registros)

    resultados = [(ids[i],
                   round(tfge[i], 2),
                   round(creatininaUmol[i], 2),
                   round(ureaMmol[i], 3),
                   clasificarEstadio(tfge[i]))
                  for i in range(total)]
    guardarResultados(conexion, "MIMD", resultados)

    guardarTiempo(conexion, "MIMD", tiempo / 1000, total, 3)

    print("datos insertados correctamente en la base de datos mysql")
    print("numero de registros insertados: ", total)

except (mysql.connector.Error, RuntimeError) as error:
    if conexion is not None:
        conexion.rollback()
    print("error al insertar datos en la base de datos mysql: ", error)

finally:
    if conexion is not None:
        conexion.close()