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

def calcular_tfge():
    for i in range(total):
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

def convertir_creatinina():
    for i in range(total):
        creatininaUmol[i] = creatinina[i] * 88.4

def convertir_urea():
    for i in range(total):
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

h1 = threading.Thread(target=calcular_tfge)
h2 = threading.Thread(target=convertir_creatinina)
h3 = threading.Thread(target=convertir_urea)

inicio = time.perf_counter_ns()

h1.start()
h2.start()
h3.start()

h1.join()
h2.join()
h3.join()

fin = time.perf_counter_ns()
tiempo = (fin - inicio) / 1000

for i in range(total):
    print("\n-------------------------")
    print("REGISTRO :", ids[i])
    print("EDAD / SEXO :", edad[i], "/", sexo[i])
    print("\nHILO1 TFGE mL/min/1.73m2")
    print("TFGe =", round(tfge[i], 2))
    print("\nHILO2 CREATININA mg/dL A umol/L")
    print(creatinina[i], "*", "88.4", "=", round(creatininaUmol[i], 2))
    print("\nHILO3 UREA mg/dL A mmol/L")
    print(urea[i], "*", "0.1665", "=", round(ureaMmol[i], 3))

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
    guardar_resultados(conexion, "MISD", resultados)

    guardar_tiempo(conexion, "MISD", tiempo / 1000, total, 3)

    print("Datos insertados correctamente en la base de datos MySQL")
    print("Numero de registros insertados: ", total)

except (mysql.connector.Error, RuntimeError) as error:
    if conexion is not None:
        conexion.rollback()
    print("Error al insertar datos en la base de datos MySQL: ", error)

finally:
    if conexion is not None:
        conexion.close()