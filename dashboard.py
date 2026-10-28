import streamlit as st
import pandas as pd
import plotly.express as px
from conexion import conectar_mysql, resolver_columnas

# ==========================================
# 1. CONFIGURACION DEL DASHBOARD
# ==========================================

st.set_page_config(
    page_title="Dashboard MISD, SIMD y MIMD",
    page_icon="📊",
    layout="wide"
)

st.title("Dashboard de Procesamiento MISD, SIMD y MIMD")
st.caption("Computacion Paralela | Python + MySQL")

TABLAS = {
    "MISD": "resultados_misd",
    "SIMD": "resultados_simd",
    "MIMD": "resultados_mimd",
}

ORDEN_ESTADIOS = ["G1", "G2", "G3a", "G3b", "G4", "G5"]


# ==========================================
# 2. CONSULTAR BASE DE DATOS
# ==========================================

def cargar_datos(tabla):

    conexion = conectar_mysql()

    try:
        r = resolver_columnas(
            conexion, "registros_renales",
            ["id", "edad", "sexo", "creatinina_mg_dl", "urea_mg_dl"])
        c = resolver_columnas(
            conexion, tabla,
            ["id", "registro_id", "tfge_ml_min_1_73m2", "creatinina_umol_l",
             "urea_mmol_l", "estadio_erc", "fecha_procesamiento"])

        consulta = f"""
            SELECT
                c.{c['id']} AS ejecucion,
                r.{r['id']} AS registro,
                r.{r['edad']} AS edad,
                r.{r['sexo']} AS sexo,
                r.{r['creatinina_mg_dl']} AS creatinina_mg_dl,
                r.{r['urea_mg_dl']} AS urea_mg_dl,
                c.{c['tfge_ml_min_1_73m2']} AS tfge,
                c.{c['creatinina_umol_l']} AS creatinina_umol_l,
                c.{c['urea_mmol_l']} AS urea_mmol_l,
                c.{c['estadio_erc']} AS estadio_erc,
                c.{c['fecha_procesamiento']} AS fecha_procesamiento
            FROM registros_renales r
            INNER JOIN {tabla} c
                ON r.{r['id']} = c.{c['registro_id']}
            ORDER BY c.{c['id']}
        """

        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        finally:
            cursor.close()

        datos = pd.DataFrame(filas)

        for columna in ["creatinina_mg_dl", "urea_mg_dl", "tfge",
                        "creatinina_umol_l", "urea_mmol_l"]:
            if columna in datos.columns:
                datos[columna] = datos[columna].astype(float)

        return datos

    finally:
        conexion.close()


def cargar_tiempos():

    conexion = conectar_mysql()

    try:
        t = resolver_columnas(
            conexion, "comparacion_tiempos",
            ["id", "arquitectura", "tiempo_ms", "num_registros",
             "num_trabajadores", "fecha_ejecucion"])

        consulta = f"""
            SELECT
                {t['id']} AS ejecucion,
                {t['arquitectura']} AS arquitectura,
                {t['tiempo_ms']} AS tiempo_ms,
                {t['num_registros']} AS num_registros,
                {t['num_trabajadores']} AS num_trabajadores,
                {t['fecha_ejecucion']} AS fecha_ejecucion
            FROM comparacion_tiempos
            ORDER BY {t['id']}
        """

        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        finally:
            cursor.close()

        tiempos = pd.DataFrame(filas)

        if "tiempo_ms" in tiempos.columns:
            tiempos["tiempo_ms"] = tiempos["tiempo_ms"].astype(float)

        return tiempos

    finally:
        conexion.close()


# ==========================================
# 3. CARGAR REGISTROS
# ==========================================

arquitectura = st.sidebar.selectbox(
    "Arquitectura",
    ["MISD", "SIMD", "MIMD"]
)

try:
    datos = cargar_datos(TABLAS[arquitectura])
    tiempos = cargar_tiempos()

except Exception as error:
    st.error(f"Error de conexion: {error}")
    st.stop()

if datos.empty:
    st.warning(f"No existen resultados de {arquitectura} en MySQL.")
    st.stop()


# ==========================================
# 4. FILTROS INTERACTIVOS
# ==========================================

st.sidebar.header("Filtros")

sexos = sorted(datos["sexo"].unique())

seleccionados = st.sidebar.multiselect(
    "Sexo",
    options=sexos,
    default=sexos
)

filtrados = datos[
    datos["sexo"].isin(seleccionados)
].copy()

unidad = st.sidebar.selectbox(
    "Variable a analizar",
    ["tfge", "creatinina_umol_l", "urea_mmol_l",
     "creatinina_mg_dl", "urea_mg_dl"]
)


# ==========================================
# 5. INDICADORES GENERALES
# ==========================================

tiempos_arq = tiempos[tiempos["arquitectura"] == arquitectura]

hilos = (
    int(tiempos_arq.iloc[-1]["num_trabajadores"])
    if not tiempos_arq.empty else "-"
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Registros",
    filtrados["registro"].nunique()
)

col2.metric("Hilos utilizados", hilos)

col3.metric(
    "TFGe promedio",
    f"{filtrados['tfge'].mean():,.2f}"
)


# ==========================================
# 6. GRAFICO DE CONVERSIONES
# ==========================================

st.subheader("Resultados por estadio de ERC")

promedio = (
    filtrados.groupby("estadio_erc")[unidad]
    .mean()
    .reset_index()
)

fig = px.bar(
    promedio,
    x="estadio_erc",
    y=unidad,
    color="estadio_erc",
    category_orders={"estadio_erc": ORDEN_ESTADIOS},
    title=f"Promedio de {unidad} por estadio ({arquitectura})"
)

st.plotly_chart(fig, use_container_width=True)


# ==========================================
# 7. ANALISIS DE TIEMPOS
# ==========================================

st.subheader("Tiempo de procesamiento")

if tiempos.empty:
    st.info("Aun no hay tiempos registrados.")
else:
    fig_tiempo = px.line(
        tiempos,
        x="ejecucion",
        y="tiempo_ms",
        color="arquitectura",
        markers=True,
        title="Tiempo registrado por ejecucion (ms)"
    )

    st.plotly_chart(fig_tiempo, use_container_width=True)

st.caption(
    "El tiempo corresponde al procesamiento completo "
    "de todos los hilos, no al tiempo individual de cada fila."
)


# ==========================================
# 8. TABLA INTERACTIVA
# ==========================================

st.subheader(f"Resultados {arquitectura} almacenados en MySQL")

st.dataframe(
    filtrados,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# 9. DESCARGAR RESULTADOS
# ==========================================

csv = filtrados.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Descargar resultados CSV",
    data=csv,
    file_name=f"resultados_{arquitectura.lower()}.csv",
    mime="text/csv"
)