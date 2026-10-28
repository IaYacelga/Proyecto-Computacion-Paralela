import mysql.connector

config = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "admin",
    "password": "admin123",
}
nombreBd = "basedatos"

tRegistros = "registros_renales"
tTiempos = "comparacion_tiempos"
tablasResultados = {
    "MISD": "resultados_misd",
    "SIMD": "resultados_simd",
    "MIMD": "resultados_mimd",
}


def norm(nombre):
    return nombre.replace("_", "").lower()


def resolver_columnas(conexion, tabla, esperadas):
    cursor = conexion.cursor()
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{tabla}`")
        reales = {norm(fila[0]): fila[0] for fila in cursor.fetchall()}
    finally:
        cursor.close()

    faltan = [e for e in esperadas if norm(e) not in reales]
    if faltan:
        raise RuntimeError(
            f"la tabla {tabla} no tiene columnas equivalentes a {faltan}. "
            f"columnas reales: {list(reales.values())}"
        )
    return {e: reales[norm(e)] for e in esperadas}


def conectar_mysql():
    conexion = mysql.connector.connect(database=nombreBd, **config)
    return conexion


def guardarRegistros(conexion, datos):
    c = resolver_columnas(
        conexion, tRegistros,
        ["id", "edad", "sexo", "creatininaMgDl", "ureaMgDl"])
    sql = f"""
        INSERT INTO {tRegistros}
            ({c['id']}, {c['edad']}, {c['sexo']},
             {c['creatininaMgDl']}, {c['ureaMgDl']})
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            {c['edad']} = VALUES({c['edad']}),
            {c['sexo']} = VALUES({c['sexo']}),
            {c['creatininaMgDl']} = VALUES({c['creatininaMgDl']}),
            {c['ureaMgDl']} = VALUES({c['ureaMgDl']})
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, datos)
    conexion.commit()
    cursor.close()


def guardarResultados(conexion, arquitectura, filas):
    tabla = tablasResultados[arquitectura]
    c = resolver_columnas(
        conexion, tabla,
        ["registroId", "tfgeMlMin173m2", "creatininaUmolL",
         "ureaMmolL", "estadioErc", "fechaProcesamiento"])
    sql = f"""
        INSERT INTO {tabla}
            ({c['registroId']}, {c['tfgeMlMin173m2']},
             {c['creatininaUmolL']}, {c['ureaMmolL']},
             {c['estadioErc']})
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            {c['tfgeMlMin173m2']} = VALUES({c['tfgeMlMin173m2']}),
            {c['creatininaUmolL']} = VALUES({c['creatininaUmolL']}),
            {c['ureaMmolL']} = VALUES({c['ureaMmolL']}),
            {c['estadioErc']} = VALUES({c['estadioErc']}),
            {c['fechaProcesamiento']} = CURRENT_TIMESTAMP
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, filas)
    conexion.commit()
    cursor.close()


def guardarTiempo(conexion, arquitectura, tiempoMs, numRegistros,
                  numTrabajadores):
    c = resolver_columnas(
        conexion, tTiempos,
        ["arquitectura", "tiempoMs", "numRegistros", "numTrabajadores"])
    sql = f"""
        INSERT INTO {tTiempos}
            ({c['arquitectura']}, {c['tiempoMs']},
             {c['numRegistros']}, {c['numTrabajadores']})
        VALUES (%s, %s, %s, %s)
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (arquitectura, round(tiempoMs, 3),
                         numRegistros, numTrabajadores))
    conexion.commit()
    cursor.close()


if __name__ == "__main__":
    try:
        conexion = conectar_mysql()
        if conexion.is_connected():
            print("conexion exitosa a la base de datos mysql")
            print("base de datos: ", conexion.database)
            conexion.close()
    except mysql.connector.Error as error:
        print("error al conectar a la base de datos mysql", error)