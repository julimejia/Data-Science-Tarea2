# =============================================================================
# 📊 DASHBOARD STREAMLIT – CALIDAD DE DATOS & RIESGO OPERATIVO
# =============================================================================
#
# ┌──────────────────────────────────────────────────────────────────────────┐
# │                             VISIÓN GENERAL                                 │
# ├──────────────────────────────────────────────────────────────────────────┤
# │                                                                          │
# │  🟦 FASE 1 – INGESTA, LIMPIEZA Y HEALTHCHECK                               │
# │  • Carga controlada de archivos CSV                                      │
# │  • Limpieza explícita de filas inválidas                                  │
# │  • Validación estructural (columnas requeridas)                           │
# │  • Métricas de calidad de datos                                           │
# │  • Cálculo de Health Score como gate de análisis                          │
# │                                                                          │
# │  🟦 FASE 2 – SKU FANTASMA (RIESGO OPERATIVO)                                │
# │  • Detección de transacciones sin respaldo en inventario                  │
# │  • Cuantificación del impacto financiero                                  │
# │  • Storytelling ejecutivo para toma de decisiones                         │
# │                                                                          │
# │  🟦 PRINCIPIO CLAVE                                                         │
# │  Ningún análisis de negocio es confiable                                  │
# │  si los datos no superan un control de calidad previo.                   │
# │                                                                          │
# │  🟦 RESULTADO                                                              │
# │  • Transparencia en la calidad del dato                                   │
# │  • Riesgo operativo cuantificado                                          │
# │  • Evidencia clara de fallas de gobernanza                                 │
# │                                                                          │
# └──────────────────────────────────────────────────────────────────────────┘
#
# =============================================================================

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="Dashboard de Análisis de Datos",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard de Análisis - Datos Empresariales")
st.markdown("---")

# =============================================================================
# SIDEBAR – CARGA DE ARCHIVOS
# =============================================================================
with st.sidebar:
    st.header("📤 Carga de Archivos CSV")

    feedback_file = st.file_uploader(
        "Feedback Clientes (feedback_clientes_v2.csv)",
        type=["csv"]
    )

    inventario_file = st.file_uploader(
        "Inventario Central (inventario_central_v2.csv)",
        type=["csv"]
    )

    transacciones_file = st.file_uploader(
        "Transacciones Logísticas (transacciones_logisticas_v2.csv)",
        type=["csv"]
    )

    mostrar_limpieza = st.checkbox("Mostrar proceso de limpieza", value=True)

# =============================================================================
# ========================= FASE 1 – INGESTA Y LIMPIEZA =========================
# =============================================================================

def cargar_feedback(file):
    df = pd.read_csv(file)
    df_limpio = df[(df["Edad_Cliente"] >= 0) & (df["Edad_Cliente"] <= 110)].copy()
    return df, df_limpio, len(df) - len(df_limpio)

def cargar_inventario(file):
    df = pd.read_csv(file)
    df_limpio = df.copy()
    filas_eliminadas = 0

    if 500 in df_limpio.index:
        df_limpio = df_limpio.drop(index=500)
        filas_eliminadas += 1

    mask = df_limpio["Stock_Actual"] < 0
    filas_eliminadas += mask.sum()
    df_limpio = df_limpio[~mask]

    return df, df_limpio, filas_eliminadas

def cargar_transacciones(file):
    df = pd.read_csv(file)
    for col in df.columns:
        if "fecha" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df, df.copy(), 0

# =============================================================================
# HEALTHCHECK – CONTROL DE CALIDAD DE DATOS
# =============================================================================
def run_healthcheck(df_raw, required_cols=None):
    missing_pct = (df_raw.isna().mean() * 100).round(2)
    duplicates = df_raw.duplicated().sum()

    missing_required = []
    if required_cols:
        missing_required = list(set(required_cols) - set(df_raw.columns))

    score = 100
    score -= missing_pct.sum() / 10
    score -= duplicates * 0.5
    score = max(0, round(score, 2))

    return {
        "rows": len(df_raw),
        "cols": len(df_raw.columns),
        "duplicates": int(duplicates),
        "missing_pct": missing_pct.to_dict(),
        "missing_required_cols": missing_required,
        "health_score": score,
        "status": "ok" if not missing_required else "invalid"
    }

FILES_CONFIG = {
    "Feedback de Clientes": (feedback_file, cargar_feedback, ["Edad_Cliente", "Rating_Producto", "Satisfaccion_NPS"]),
    "Inventario Central": (inventario_file, cargar_inventario, ["SKU_ID", "Categoria", "Stock_Actual", "Punto_Reorden"]),
    "Transacciones Logísticas": (transacciones_file, cargar_transacciones, None)
}

datasets = {}
health_status = {}

for name, (file, loader, required_cols) in FILES_CONFIG.items():
    if not file:
        health_status[name] = "missing"
        continue

    df_raw, df_clean, filas_eliminadas = loader(file)
    health = run_healthcheck(df_raw, required_cols)
    health["filas_eliminadas"] = filas_eliminadas

    datasets[name] = {"raw": df_raw, "clean": df_clean, "health": health}
    health_status[name] = health["status"]

# =============================================================================
# VISUALIZACIÓN DEL HEALTHCHECK
# =============================================================================
st.subheader("📋 Estado de Calidad de los Datos")

cols = st.columns(3)
for col, (name, status) in zip(cols, health_status.items()):
    with col:
        if status == "ok":
            st.success(f"✅ {name}")
            hc = datasets[name]["health"]
            with st.expander("Detalles del Healthcheck"):
                st.write(f"Filas: {hc['rows']}")
                st.write(f"Columnas: {hc['cols']}")
                st.write(f"Duplicados: {hc['duplicates']}")
                st.write(f"Filas eliminadas: {hc['filas_eliminadas']}")
                st.metric("Health Score", hc["health_score"])
        elif status == "missing":
            st.warning(f"⚠️ {name} no cargado")
        else:
            st.error(f"❌ {name} inválido")

datasets_disponibles = [k for k, v in health_status.items() if v == "ok"]

if not datasets_disponibles:
    st.stop()

# =============================================================================
# ========================= FASE 2 – SKU FANTASMA ===============================
# =============================================================================

if "Inventario Central" in datasets_disponibles and "Transacciones Logísticas" in datasets_disponibles:

    st.markdown("---")
    st.header("👻 FASE 2 – Análisis de SKU Fantasma")

    inv = datasets["Inventario Central"]["clean"].copy()
    trx = datasets["Transacciones Logísticas"]["clean"].copy()

    inv["SKU_ID"] = inv["SKU_ID"].astype(str).str.strip()
    trx["SKU_ID"] = trx["SKU_ID"].astype(str).str.strip()

    merged = trx.merge(inv[["SKU_ID"]], on="SKU_ID", how="left", indicator=True)
    merged["sku_status"] = merged["_merge"].apply(
        lambda x: "FANTASMA" if x == "left_only" else "VALIDO"
    )

    # -------------------------------------------------------------------------
    # DASHBOARD 1 – VISIBILIDAD DEL SKU FANTASMA
    # -------------------------------------------------------------------------
    st.subheader("📦 Visibilidad de SKUs Fantasma")

    resumen = merged["sku_status"].value_counts().reset_index()
    resumen.columns = ["Estado SKU", "Cantidad"]

    col1, col2 = st.columns(2)
    col1.metric("Transacciones Totales", len(merged))
    col2.metric("SKUs Fantasma", resumen.loc[resumen["Estado SKU"] == "FANTASMA", "Cantidad"].sum())

    fig, ax = plt.subplots()
    ax.bar(resumen["Estado SKU"], resumen["Cantidad"])
    st.pyplot(fig)

    # -------------------------------------------------------------------------
    # DASHBOARD 2 – IMPACTO FINANCIERO
    # -------------------------------------------------------------------------
    st.subheader("💰 Impacto Financiero del SKU Fantasma")

    merged["Cantidad_Vendida"] = merged["Cantidad_Vendida"].fillna(0)
    merged["Precio_Venta_Final"] = merged["Precio_Venta_Final"].fillna(0)
    merged["ingreso"] = merged["Cantidad_Vendida"] * merged["Precio_Venta_Final"]

    impacto = merged.groupby("sku_status")["ingreso"].sum().reset_index()

    total = impacto["ingreso"].sum()
    fantasma = impacto.loc[impacto["sku_status"] == "FANTASMA", "ingreso"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Ingreso Total (USD)", f"{total:,.0f}")
    col2.metric("% Ingresos en Riesgo", f"{(fantasma/total)*100:.2f}%")

    # -------------------------------------------------------------------------
    # DASHBOARD 3 – STORYTELLING EJECUTIVO
    # -------------------------------------------------------------------------
    st.subheader("🧠 Storytelling Ejecutivo del Riesgo")

    resumen_exec = merged.groupby("sku_status").agg(
        transacciones=("SKU_ID", "count"),
        ingreso_total=("ingreso", "sum")
    ).reset_index()

    st.dataframe(resumen_exec, use_container_width=True)

    st.info(
        "Los SKUs fantasma representan una falla crítica de gobernanza del inventario: "
        "generan ingresos sin respaldo físico, distorsionan márgenes y comprometen "
        "la toma de decisiones estratégicas."
    )
