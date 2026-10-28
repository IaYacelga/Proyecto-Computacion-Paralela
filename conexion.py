import mysql.connector

CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "admin",
    "password": "admin123",
}
NOMBRE_BD = "basedatos"

T_REGISTROS = "registros_renales"
T_TIEMPOS = "comparacion_tiempos"
TABLAS_RESULTADOS = {
    "MISD": "resultados_misd",
    "SIMD": "resultados_simd",
    "MIMD": "resultados_mimd",
}


def _norm(nombre):
    return nombre.replace("_", "").lower()


def resolver_columnas(conexion, tabla, esperadas):
    """Devuelve {nombre_esperado: nombre_real_en_la_tabla}.

    Ignora mayusculas y guiones bajos, asi 'tfge_ml_min_1_73m2' encuentra
    'tfgeMlMin173m2' automaticamente.
    """
    cursor = conexion.cursor()
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{tabla}`")
        reales = {_norm(fila[0]): fila[0] for fila in cursor.fetchall()}
    finally:
        cursor.close()

    faltan = [e for e in esperadas if _norm(e) not in reales]
    if faltan:
        raise RuntimeError(
            f"La tabla {tabla} no tiene columnas equivalentes a {faltan}. "
            f"Columnas reales: {list(reales.values())}"
        )
    return {e: reales[_norm(e)] for e in esperadas}


def conectar_mysql():
    # Solo conecta: las tablas se crean directamente en MySQL (phpMyAdmin).
    conexion = mysql.connector.connect(database=NOMBRE_BD, **CONFIG)
    return conexion


def guardar_registros(conexion, datos):
    c = resolver_columnas(
        conexion, T_REGISTROS,
        ["id", "edad", "sexo", "creatinina_mg_dl", "urea_mg_dl"])
    sql = f"""
        INSERT INTO {T_REGISTROS}
            ({c['id']}, {c['edad']}, {c['sexo']},
             {c['creatinina_mg_dl']}, {c['urea_mg_dl']})
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            {c['edad']} = VALUES({c['edad']}),
            {c['sexo']} = VALUES({c['sexo']}),
            {c['creatinina_mg_dl']} = VALUES({c['creatinina_mg_dl']}),
            {c['urea_mg_dl']} = VALUES({c['urea_mg_dl']})
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, datos)
    conexion.commit()
    cursor.close()


def guardar_resultados(conexion, arquitectura, filas):
    """Para MISD, SIMD y MIMD: (registro_id, tfge, creatinina_umol, urea_mmol, estadio)."""
    tabla = TABLAS_RESULTADOS[arquitectura]
    c = resolver_columnas(
        conexion, tabla,
        ["registro_id", "tfge_ml_min_1_73m2", "creatinina_umol_l",
         "urea_mmol_l", "estadio_erc", "fecha_procesamiento"])
    sql = f"""
        INSERT INTO {tabla}
            ({c['registro_id']}, {c['tfge_ml_min_1_73m2']},
             {c['creatinina_umol_l']}, {c['urea_mmol_l']},
             {c['estadio_erc']})
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            {c['tfge_ml_min_1_73m2']} = VALUES({c['tfge_ml_min_1_73m2']}),
            {c['creatinina_umol_l']} = VALUES({c['creatinina_umol_l']}),
            {c['urea_mmol_l']} = VALUES({c['urea_mmol_l']}),
            {c['estadio_erc']} = VALUES({c['estadio_erc']}),
            {c['fecha_procesamiento']} = CURRENT_TIMESTAMP
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, filas)
    conexion.commit()
    cursor.close()


def guardar_tiempo(conexion, arquitectura, tiempo_ms, num_registros,
                   num_trabajadores):
    c = resolver_columnas(
        conexion, T_TIEMPOS,
        ["arquitectura", "tiempo_ms", "num_registros", "num_trabajadores"])
    sql = f"""
        INSERT INTO {T_TIEMPOS}
            ({c['arquitectura']}, {c['tiempo_ms']},
             {c['num_registros']}, {c['num_trabajadores']})
        VALUES (%s, %s, %s, %s)
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (arquitectura, round(tiempo_ms, 3),
                         num_registros, num_trabajadores))
    conexion.commit()
    cursor.close()


if __name__ == "__main__":
    try:
        conexion = conectar_mysql()
        if conexion.is_connected():
            print("Conexion exitosa a la base de datos mysql")
            print("BASE DE DATOS: ", conexion.database)
            conexion.close()
    except mysql.connector.Error as error:
        print("Error al conectar a la base de datos MySQL", error)