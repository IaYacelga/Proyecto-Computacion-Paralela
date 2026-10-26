import mysql.connector

CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "admin",
    "password": "admin123",
}
NOMBRE_BD = "basedatos"

TABLAS_RESULTADOS = {
    "MISD": "resultados_misd",
    "SIMD": "resultados_simd",
    "MIMD": "resultados_mimd",
}


def _sql_tabla_resultados(nombre):
    return f"""
        CREATE TABLE IF NOT EXISTS {nombre} (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT,
            registro_id INT UNSIGNED NOT NULL,
            tfge_ml_min_1_73m2 DECIMAL(6,2) NOT NULL,
            creatinina_umol_l DECIMAL(7,2) NOT NULL,
            urea_mmol_l DECIMAL(6,3) NOT NULL,
            estadio_erc VARCHAR(3) NOT NULL,
            fecha_procesamiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_{nombre}_registro (registro_id),
            CONSTRAINT fk_{nombre}_registro FOREIGN KEY (registro_id)
                REFERENCES registros_renales (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """


def crear_base_y_tablas():
    conexion = mysql.connector.connect(**CONFIG)
    cursor = conexion.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {NOMBRE_BD} "
            "CHARACTER SET utf8mb4"
        )
        cursor.execute(f"USE {NOMBRE_BD}")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_renales (
                id INT UNSIGNED NOT NULL,
                edad TINYINT UNSIGNED NOT NULL,
                sexo ENUM('Hombre','Mujer') NOT NULL,
                creatinina_mg_dl DECIMAL(4,2) NOT NULL,
                urea_mg_dl DECIMAL(5,2) NOT NULL,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        for tabla in TABLAS_RESULTADOS.values():
            cursor.execute(_sql_tabla_resultados(tabla))

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparacion_tiempos (
                id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                arquitectura ENUM('SIMD','MISD','MIMD') NOT NULL,
                tiempo_ms DECIMAL(10,3) NOT NULL,
                num_registros INT UNSIGNED NOT NULL,
                num_trabajadores TINYINT UNSIGNED NOT NULL,
                fecha_ejecucion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()


def conectar_mysql():
    crear_base_y_tablas()
    conexion = mysql.connector.connect(database=NOMBRE_BD, **CONFIG)
    return conexion


def guardar_registros(conexion, datos):
    sql = """
        INSERT INTO registros_renales
            (id, edad, sexo, creatinina_mg_dl, urea_mg_dl)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            edad = VALUES(edad),
            sexo = VALUES(sexo),
            creatinina_mg_dl = VALUES(creatinina_mg_dl),
            urea_mg_dl = VALUES(urea_mg_dl)
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, datos)
    conexion.commit()
    cursor.close()


def guardar_resultados(conexion, arquitectura, filas):
    tabla = TABLAS_RESULTADOS[arquitectura]
    sql = f"""
        INSERT INTO {tabla}
            (registro_id, tfge_ml_min_1_73m2, creatinina_umol_l,
             urea_mmol_l, estadio_erc)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            tfge_ml_min_1_73m2 = VALUES(tfge_ml_min_1_73m2),
            creatinina_umol_l = VALUES(creatinina_umol_l),
            urea_mmol_l = VALUES(urea_mmol_l),
            estadio_erc = VALUES(estadio_erc),
            fecha_procesamiento = CURRENT_TIMESTAMP
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, filas)
    conexion.commit()
    cursor.close()


def guardar_tiempo(conexion, arquitectura, tiempo_ms, num_registros,
                   num_trabajadores):
    sql = """
        INSERT INTO comparacion_tiempos
            (arquitectura, tiempo_ms, num_registros, num_trabajadores)
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