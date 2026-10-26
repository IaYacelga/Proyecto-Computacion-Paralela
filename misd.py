import csv
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

with open('datos_renales_5000.csv', 'r', encoding="utf-8-sig", newline="") as archivo:

    lector = csv.reader(archivo)
    next(lector)

    for fila in lector:
        ids.append(int(fila[0]))
        edad.append(int(fila[1]))
        sexo.append(fila[2].strip())
        creatinina.append(float(fila[3]))
        urea.append(float(fila[4]))

    print("Dataset cargado correctamente")
    print("Numero de elementos cargados desde el dataset: ", len(ids))

tfge = [0.0] * len(ids)
creatininaUmol = [0.0] * len(ids)
ureaMmol = [0.0] * len(ids)

def calcular_tfge():
    for i in range(len(ids)):
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
    for i in range(len(ids)):
        creatininaUmol[i] = creatinina[i] * 88.4

def convertir_urea():
    for i in range(len(ids)):
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
tiempo = (fin - inicio) / 1000000

for i in range(5):
    print("\n-------------------------")
    print("REGISTRO :", ids[i])
    print("EDAD / SEXO :", edad[i], "/", sexo[i])
    print("TFGe mL/min/1.73m2 :", round(tfge[i], 2))
    print("CREATININA umol/L :", round(creatininaUmol[i], 2))
    print("UREA mmol/L :", round(ureaMmol[i], 3))

print("\n-------------------------")
print(f"TIEMPO : {tiempo:.4f} ms")


conexion = None

try:
    conexion = conectar_mysql()
    print("\nConexion exitosa a la base de datos MySQL")

    registros = [(ids[i], edad[i], sexo[i], creatinina[i], urea[i])
                 for i in range(len(ids))]
    guardar_registros(conexion, registros)

    resultados = [(ids[i],
                   round(tfge[i], 2),
                   round(creatininaUmol[i], 2),
                   round(ureaMmol[i], 3),
                   clasificar_estadio(tfge[i]))
                  for i in range(len(ids))]
    guardar_resultados(conexion, "MISD", resultados)

    guardar_tiempo(conexion, "MISD", tiempo, len(ids), 3)

    print("Datos insertados correctamente en la base de datos MySQL")
    print("Numero de registros insertados: ", len(ids))

except mysql.connector.Error as error:
    if conexion is not None:
        conexion.rollback()
    print("Error al insertar datos en la base de datos MySQL: ", error)

finally:
    if conexion is not None:
        conexion.close()