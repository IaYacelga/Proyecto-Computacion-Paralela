import streamlit as st
import pandas as pd
import plotly.express as px
from Proyecto.conexion import conectar_mysql

st.set_page_config(
    page_title="Dashboard MISD - Funcion Renal",
    page_icon="📊",
    layout="wide"
)

st.title("Dashboard de Procesamiento MISD - Funcion Renal")
st.caption("Computacion Paralela | Python + MySQL")

ORDEN_ESTADIOS = ["G1", "G2", "G3a", "G3b", "G4", "G5"]


def cargar_datos():

    conexion = conectar_mysql()

    try:
        consulta = """
            SELECT
                c.id AS ejecucion,
                r.id AS registro,
                r.edad,
                r.sexo,
                r.creatinina_mg_dl,
                r.urea_mg_dl,
                c.tfge_ml_min_1_73m2 AS tfge,
                c.creatinina_umol_l,
                c.urea_mmol_l,
                c.estadio_erc,
                c.fecha_procesamiento
            FROM registros_renales r
            INNER JOIN resultados_misd c
                ON r.id = c.registro_id
            ORDER BY c.id
        """

        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        finally:
            cursor.close()

        df = pd.DataFrame(filas)

        columnas_numericas = ["creatinina_mg_dl", "urea_mg_dl", "tfge",
                              "creatinina_umol_l", "urea_mmol_l"]
        for columna in columnas_numericas:
            if columna in df.columns:
                df[columna] = df[columna].astype(float)

        return df

    finally:
        conexion.close()


def cargar_tiempos():

    conexion = conectar_mysql()

    try:
        consulta = """
            SELECT
                id AS ejecucion,
                tiempo_ms,
                num_registros,
                num_trabajadores,
                fecha_ejecucion
            FROM comparacion_tiempos
            WHERE arquitectura = 'MISD'
            ORDER BY id
        """

        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute(consulta)
            filas = cursor.fetchall()
        finally:
            cursor.close()

        df = pd.DataFrame(filas)

        if "tiempo_ms" in df.columns:
            df["tiempo_ms"] = df["tiempo_ms"].astype(float)

        return df

    finally:
        conexion.close()


try:
    datos = cargar_datos()
    tiempos = cargar_tiempos()

except Exception as error:
    st.error(f"Error de conexion: {error}")
    st.stop()

if datos.empty:
    st.warning("No existen resultados en MySQL.")
    st.stop()


st.sidebar.header("Filtros")

sexos = sorted(datos["sexo"].unique())

sexo_sel = st.sidebar.multiselect(
    "Sexo",
    options=sexos,
    default=sexos
)

estadios = [e for e in ORDEN_ESTADIOS if e in datos["estadio_erc"].unique()]

estadio_sel = st.sidebar.multiselect(
    "Estadio de ERC",
    options=estadios,
    default=estadios
)

edad_min = int(datos["edad"].min())
edad_max = int(datos["edad"].max())

rango_edad = st.sidebar.slider(
    "Rango de edad",
    min_value=edad_min,
    max_value=edad_max,
    value=(edad_min, edad_max)
)

filtrados = datos[
    datos["sexo"].isin(sexo_sel)
    & datos["estadio_erc"].isin(estadio_sel)
    & datos["edad"].between(rango_edad[0], rango_edad[1])
].copy()

variable = st.sidebar.selectbox(
    "Variable a analizar",
    ["tfge", "creatinina_umol_l", "urea_mmol_l",
     "creatinina_mg_dl", "urea_mg_dl"]
)

if filtrados.empty:
    st.warning("Los filtros no devuelven ningun registro.")
    st.stop()


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Registros",
    filtrados["registro"].nunique()
)

col2.metric("Hilos utilizados", 3)

col3.metric(
    "TFGe promedio",
    f"{filtrados['tfge'].mean():,.2f}"
)

col4.metric(
    "Edad promedio",
    f"{filtrados['edad'].mean():,.1f}"
)


st.subheader("Pacientes por estadio de ERC")

conteo = (
    filtrados.groupby("estadio_erc")
    .size()
    .reset_index(name="pacientes")
)

fig = px.bar(
    conteo,
    x="estadio_erc",
    y="pacientes",
    color="estadio_erc",
    category_orders={"estadio_erc": ORDEN_ESTADIOS},
    title="Cantidad de pacientes segun TFGe"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader(f"Promedio de {variable} por estadio")

promedio = (
    filtrados.groupby("estadio_erc")[variable]
    .mean()
    .reset_index()
)

fig_variable = px.bar(
    promedio,
    x="estadio_erc",
    y=variable,
    color="estadio_erc",
    category_orders={"estadio_erc": ORDEN_ESTADIOS},
    title=f"Promedio de {variable}"
)

st.plotly_chart(fig_variable, use_container_width=True)


st.subheader("Tiempo de procesamiento")

if tiempos.empty:
    st.info("Aun no hay tiempos registrados en comparacion_tiempos.")
else:
    fig_tiempo = px.line(
        tiempos,
        x="ejecucion",
        y="tiempo_ms",
        markers=True,
        title="Tiempo registrado por ejecucion MISD ms"
    )

    st.plotly_chart(fig_tiempo, use_container_width=True)

st.caption(
    "El tiempo corresponde al procesamiento completo "
    "de los tres hilos, no al tiempo individual de cada fila."
)


st.subheader("Resultados almacenados en MySQL")

st.dataframe(
    filtrados,
    use_container_width=True,
    hide_index=True
)


csv = filtrados.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Descargar resultados CSV",
    data=csv,
    file_name="resultados_misd.csv",
    mime="text/csv"
)