import csv
import sys
import threading
import time

from conexion import (conectar_mysql, guardarRegistros,
                      guardarResultados, guardarTiempo)
import mysql.connector

numHilos = 4

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

def procesarBloque(inicioBloque, finBloque):
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

tamano = total // numHilos

bloques = []
hilos = []

for n in range(numHilos):
    inicioBloque = n * tamano
    finBloque = total if n == numHilos - 1 else inicioBloque + tamano
    bloques.append((inicioBloque, finBloque))
    hilos.append(threading.Thread(target=procesarBloque,
                                  args=(inicioBloque, finBloque)))

inicio = time.perf_counter_ns()

for h in hilos:
    h.start()

for h in hilos:
    h.join()

fin = time.perf_counter_ns()
tiempo = (fin - inicio) / 1000

for n in range(numHilos):
    inicioBloque, finBloque = bloques[n]
    print(f"hilo {n + 1}: posiciones {inicioBloque} a {finBloque - 1} "
          f"registros {ids[inicioBloque]} a {ids[finBloque - 1]}")

for i in range(total):
    print("\n-------------------------")
    print("registro :", ids[i])
    print("edad / sexo :", edad[i], "/", sexo[i])
    print("tfge ml/min/1.73m2 :", round(tfge[i], 2))
    print("creatinina umol/l :", round(creatininaUmol[i], 2))
    print("urea mmol/l :", round(ureaMmol[i], 3))

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
    guardarResultados(conexion, "SIMD", resultados)

    guardarTiempo(conexion, "SIMD", tiempo / 1000, total, numHilos)

    print("datos insertados correctamente en la base de datos mysql")
    print("numero de registros insertados: ", total)

except (mysql.connector.Error, RuntimeError) as error:
    if conexion is not None:
        conexion.rollback()
    print("error al insertar datos en la base de datos mysql: ", error)

finally:
    if conexion is not None:
        conexion.close()