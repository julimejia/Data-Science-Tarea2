# app.py - Dashboard Streamlit para análisis de feedback, inventario y transacciones

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ==============================
# CONFIGURACIÓN DE LA PÁGINA
# ==============================
st.set_page_config(
    page_title="Dashboard de Análisis de Datos",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard de Análisis - Datos Empresariales")
st.markdown("---")

# ==============================
# SIDEBAR - CARGA DE ARCHIVOS
# ==============================
with st.sidebar:
    st.header("📤 Carga de Archivos CSV")

    feedback_file = st.file_uploader(
        "Feedback Clientes (feedback_clientes_v2.csv)",
        type=["csv"],
        key="feedback"
    )

    inventario_file = st.file_uploader(
        "Inventario Central (inventario_central_v2.csv)",
        type=["csv"],
        key="inventario"
    )

    transacciones_file = st.file_uploader(
        "Transacciones Logísticas (transacciones_logisticas_v2.csv)",
        type=["csv"],
        key="transacciones"
    )

    st.markdown("---")
    mostrar_limpieza = st.checkbox("Mostrar proceso de limpieza", value=True)

# ==============================
# FUNCIONES DE CARGA Y LIMPIEZA
# ==============================
def cargar_feedback(file):
    df = pd.read_csv(file)
    df_limpio = df[(df["Edad_Cliente"] >= 0) & (df["Edad_Cliente"] <= 110)].copy()
    return df, df_limpio

def cargar_inventario(file):
    df = pd.read_csv(file)
    df_limpio = df.copy()
    if 500 in df_limpio.index:
        df_limpio = df_limpio.drop(index=500)
    df_limpio = df_limpio[df_limpio["Stock_Actual"] >= 0]
    return df, df_limpio

def cargar_transacciones(file):
    df = pd.read_csv(file)
    for col in df.columns:
        if "fecha" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df, df.copy()

# ==============================
# HEALTHCHECK CENTRALIZADO (inmediato)
# - For each uploaded file we run an immediate health check that returns
#   basic metadata, missing-value percentages, duplicate counts, dtypes
#   and required-column validation. Results are stored in `datasets[name]["health"]`.
# ==============================
FILES_CONFIG = {
    "Feedback de Clientes": {
        "file": feedback_file,
        "required_cols": ["Edad_Cliente", "Rating_Producto", "Satisfaccion_NPS"],
        "loader": cargar_feedback
    },
    "Inventario Central": {
        "file": inventario_file,
        "required_cols": ["SKU_ID", "Categoria", "Stock_Actual", "Punto_Reorden"],
        "loader": cargar_inventario
    },
    "Transacciones Logísticas": {
        "file": transacciones_file,
        "required_cols": None,
        "loader": cargar_transacciones
    }
}

def run_healthcheck(df_raw, df_clean=None, required_cols=None):
    hc = {}
    hc["rows"] = len(df_raw)
    hc["cols"] = len(df_raw.columns)
    # percent missing (rounded)
    hc["missing_pct"] = (df_raw.isna().mean() * 100).round(2).to_dict()
    hc["missing_count"] = df_raw.isna().sum().to_dict()
    hc["duplicates"] = int(df_raw.duplicated().sum())
    hc["dtypes"] = df_raw.dtypes.astype(str).to_dict()
    hc["sample_head"] = df_raw.head(5)
    missing_required = []
    if required_cols:
        missing_required = list(set(required_cols) - set(df_raw.columns))
    hc["missing_required_cols"] = missing_required
    hc["status"] = "ok" if not missing_required else "invalid_cols"
    return hc

health_status = {}
datasets = {}

for name, cfg in FILES_CONFIG.items():
    file = cfg["file"]

    if file is None:
        health_status[name] = "missing"
        continue

    try:
        df_raw, df_clean = cfg["loader"](file)
        health = run_healthcheck(df_raw, df_clean, cfg.get("required_cols"))

        datasets[name] = {"raw": df_raw, "clean": df_clean, "health": health}

        if health["status"] == "ok":
            health_status[name] = "ok"
        else:
            health_status[name] = f"invalid_cols: {health['missing_required_cols']}"

    except Exception as e:
        health_status[name] = f"error: {e}"

# ==============================
# ESTADO DE CARGA
# ==============================
st.subheader("📋 Estado de Carga de Archivos")
cols = st.columns(3)

for col, (name, status) in zip(cols, health_status.items()):
    with col:
        if status == "ok":
            st.success(f"✅ {name}")
            # show a compact health summary
            health = datasets.get(name, {}).get("health")
            if health:
                with st.expander("Detalles Healthcheck"):
                    st.markdown(f"- **Filas:** {health['rows']}  \n- **Columnas:** {health['cols']}  \n- **Duplicados:** {health['duplicates']}")
                    # show top 5 missing columns by percent
                    missing_pct = {k: v for k, v in health["missing_pct"].items() if v > 0}
                    if missing_pct:
                        sorted_missing = dict(sorted(missing_pct.items(), key=lambda x: x[1], reverse=True))
                        top5 = list(sorted_missing.items())[:5]
                        st.table(pd.DataFrame(top5, columns=["Columna", "% Missing"]))
                    else:
                        st.info("No missing values detected")

        elif status == "missing":
            st.warning(f"⚠️ {name}\nNo cargado")

        elif "invalid_cols" in status:
            # show which required columns are missing if available
            missing_list = []
            if name in datasets:
                missing_list = datasets[name]["health"].get("missing_required_cols", [])
            st.error(f"❌ {name}\nColumnas faltantes: {missing_list}")
            if name in datasets:
                with st.expander("Ver detalles de healthcheck"):
                    st.write(datasets[name]["health"]["sample_head"])

        else:
            st.error(f"❌ {name}\nError al procesar")

# ==============================
# DATASETS DISPONIBLES
# ==============================
datasets_disponibles = [k for k, v in health_status.items() if v == "ok"]

if not datasets_disponibles:
    st.info("📤 Sube al menos un archivo para comenzar el análisis.")
    st.stop()

dataset_option = st.selectbox(
    "Seleccionar dataset para análisis:",
    datasets_disponibles
)

df_raw = datasets[dataset_option]["raw"]
df_clean = datasets[dataset_option]["clean"]

st.markdown("---")

# ==============================
# MÉTRICAS GENERALES
# ==============================
st.subheader("📊 Métricas Generales")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Filas (raw)", len(df_raw))
with col2:
    st.metric("Filas (clean)", len(df_clean))
with col3:
    st.metric("Columnas", len(df_clean.columns))

# ==============================
# PROCESO DE LIMPIEZA
# ==============================
if mostrar_limpieza:
    with st.expander("🔍 Proceso de Limpieza"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Antes")
            st.dataframe(df_raw.describe(include="all"), use_container_width=True)
        with col2:
            st.subheader("Después")
            st.dataframe(df_clean.describe(include="all"), use_container_width=True)

# ==============================
# ANÁLISIS POR DATASET
# ==============================
st.markdown("## 📈 Análisis Detallado")

if dataset_option == "Feedback de Clientes":
    fig, ax = plt.subplots()
    df_clean["Edad_Cliente"].hist(bins=30, ax=ax, edgecolor="black")
    ax.set_title("Distribución de Edad")
    st.pyplot(fig)

elif dataset_option == "Inventario Central":
    criticos = df_clean[df_clean["Stock_Actual"] < df_clean["Punto_Reorden"]]
    st.warning(f"🚨 Productos críticos: {len(criticos)}")
    st.dataframe(
        criticos[["SKU_ID", "Categoria", "Stock_Actual", "Punto_Reorden"]],
        use_container_width=True
    )

elif dataset_option == "Transacciones Logísticas":
    st.dataframe(df_clean.head(20), use_container_width=True)

# ==============================
# DESCARGA
# ==============================
st.markdown("---")
st.subheader("📥 Descargar Dataset Procesado")

csv = df_clean.to_csv(index=False)
st.download_button(
    "Descargar CSV",
    csv,
    f"{dataset_option.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
    "text/csv"
)

st.caption("Dashboard con healthcheck flexible | Streamlit")
