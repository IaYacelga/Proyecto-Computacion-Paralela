import csv
import sys
import threading
import time

from conexion import (conectar_mysql, guardar_registros,
                      guardar_resultados, guardar_tiempo)
import mysql.connector

NUM_HILOS = 4

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

def procesar_bloque(inicioBloque, finBloque):
    # Misma instruccion para todos los hilos, sobre bloques distintos de datos
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
        creatininaUmol[i] = creatinina[i] * 88.4
        ureaMmol[i] = urea[i] * 0.1665

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

tamano = total // NUM_HILOS

bloques = []
hilos = []

for n in range(NUM_HILOS):
    inicioBloque = n * tamano
    finBloque = total if n == NUM_HILOS - 1 else inicioBloque + tamano
    bloques.append((inicioBloque, finBloque))
    hilos.append(threading.Thread(target=procesar_bloque,
                                  args=(inicioBloque, finBloque)))

inicio = time.perf_counter_ns()

for h in hilos:
    h.start()

for h in hilos:
    h.join()

fin = time.perf_counter_ns()
tiempo = (fin - inicio) / 1000

for n in range(NUM_HILOS):
    inicioBloque, finBloque = bloques[n]
    print(f"Hilo {n + 1}: posiciones {inicioBloque} a {finBloque - 1} "
          f"(registros {ids[inicioBloque]} a {ids[finBloque - 1]})")

for i in range(total):
    print("\n-------------------------")
    print("REGISTRO :", ids[i])
    print("EDAD / SEXO :", edad[i], "/", sexo[i])
    print("TFGe mL/min/1.73m2 :", round(tfge[i], 2))
    print("CREATININA umol/L :", round(creatininaUmol[i], 2))
    print("UREA mmol/L :", round(ureaMmol[i], 3))

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
    guardar_resultados(conexion, "SIMD", resultados)

    guardar_tiempo(conexion, "SIMD", tiempo / 1000, total, NUM_HILOS)

    print("Datos insertados correctamente en la base de datos MySQL")
    print("Numero de registros insertados: ", total)

except (mysql.connector.Error, RuntimeError) as error:
    if conexion is not None:
        conexion.rollback()
    print("Error al insertar datos en la base de datos MySQL: ", error)

finally:
    if conexion is not None:
        conexion.close()