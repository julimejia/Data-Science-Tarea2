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
import io

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
# HEALTHCHECK – CONTROL DE CALIDAD DE DATOS (PROFUNDO)
# =============================================================================
def run_healthcheck(df_raw, required_cols=None):
    """
    Comprehensive health check including memory, numeric/categorical summaries,
    date parse issues, and actionable suggestions.
    """
    hc = {}
    hc["rows"] = len(df_raw)
    hc["cols"] = len(df_raw.columns)
    
    # Missing value analysis
    missing_frac = df_raw.isna().mean()
    hc["missing_pct"] = (missing_frac * 100).round(2).to_dict()
    hc["missing_count"] = df_raw.isna().sum().to_dict()
    hc["duplicates"] = int(df_raw.duplicated().sum())
    hc["dtypes"] = df_raw.dtypes.astype(str).to_dict()
    
    # Memory usage
    try:
        hc["memory_bytes"] = int(df_raw.memory_usage(deep=True).sum())
    except Exception:
        hc["memory_bytes"] = None

    # Numeric summaries (min, max, mean, std, percent zeros)
    numeric = df_raw.select_dtypes(include=["number"]).copy()
    num_summary = {}
    if not numeric.empty:
        desc = numeric.describe().T
        for col in desc.index:
            vals = desc.loc[col]
            zeros = int((numeric[col] == 0).sum())
            num_summary[col] = {
                "count": int(vals["count"]),
                "mean": float(vals.get("mean", float("nan"))),
                "std": float(vals.get("std", float("nan"))),
                "min": float(vals.get("min", float("nan"))),
                "max": float(vals.get("max", float("nan"))),
                "pct_zeros": round(zeros / max(1, int(vals["count"])) * 100, 2)
            }
    hc["numeric_summary"] = num_summary

    # Categorical summaries (unique count, top values)
    cat = df_raw.select_dtypes(include=["object", "category"]).copy()
    cat_summary = {}
    if not cat.empty:
        for col in cat.columns:
            nunique = int(cat[col].nunique(dropna=True))
            top = list(cat[col].value_counts(dropna=True).head(3).items())
            cat_summary[col] = {"unique": nunique, "top_values": top}
    hc["categorical_summary"] = cat_summary

    # Date parse / NaT issues for datetime columns
    date_issues = {}
    for col in df_raw.columns:
        if "datetime64" in str(df_raw[col].dtype) or "datetime" in col.lower():
            nat_count = int(df_raw[col].isna().sum())
            date_issues[col] = {"nat_count": nat_count, "pct_nat": round(nat_count / max(1, len(df_raw)) * 100, 2)}
    hc["date_issues"] = date_issues

    # Required columns
    missing_required = []
    if required_cols:
        missing_required = list(set(required_cols) - set(df_raw.columns))
    hc["missing_required_cols"] = missing_required
    hc["status"] = "ok" if not missing_required else "invalid"

    # Simple suggestions
    suggestions = []
    if hc["duplicates"] > 0:
        suggestions.append(f"Remove or investigate {hc['duplicates']} duplicate row(s)")
    high_missing = [k for k, v in hc["missing_pct"].items() if v > 30]
    if high_missing:
        suggestions.append(f"High missing (>30%) in: {', '.join(high_missing)}")
    if any(v["unique"] == 0 for v in cat_summary.values() if isinstance(v, dict)):
        suggestions.append("Categorical columns with no unique values detected")
    if hc.get("memory_bytes") and hc["memory_bytes"] > 200_000_000:
        suggestions.append("Large memory usage: consider downcasting types or sampling")
    
    hc["suggestions"] = suggestions

    # Health score
    score = 100
    if hc["missing_pct"]:
        score -= sum(hc["missing_pct"].values()) / 10
    score -= hc["duplicates"] * 0.5
    score = max(0, round(score, 2))
    hc["health_score"] = score

    return hc

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
# VISUALIZACIÓN DEL HEALTHCHECK (PROFUNDO)
# =============================================================================
st.subheader("📋 Estado de Calidad de los Datos")

cols = st.columns(3)
for col, (name, status) in zip(cols, health_status.items()):
    with col:
        if status == "ok":
            hc = datasets[name]["health"]
            st.success(f"✅ {name}\nScore: {hc['health_score']}")
            
            with st.expander("📊 Detalles Completos"):
                # Basic metrics
                st.markdown(f"""
                **Métricas Básicas**
                - Filas: {hc['rows']}
                - Columnas: {hc['cols']}
                - Duplicados: {hc['duplicates']}
                - Filas eliminadas: {hc['filas_eliminadas']}
                """)
                
                # Memory
                if hc.get("memory_bytes") is not None:
                    mb = round(hc["memory_bytes"] / (1024 ** 2), 2)
                    st.metric("Memoria Estimada", f"{mb} MB")
                
                # Missing values table
                missing_pct = {k: v for k, v in hc["missing_pct"].items() if v > 0}
                if missing_pct:
                    st.markdown("**Valores Faltantes (% por columna)**")
                    sorted_missing = dict(sorted(missing_pct.items(), key=lambda x: x[1], reverse=True))
                    st.table(pd.DataFrame(list(sorted_missing.items()), columns=["Columna", "% Missing"]))
                else:
                    st.info("✅ Sin valores faltantes")
                
                # Numeric summary
                if hc.get("numeric_summary"):
                    st.markdown("**Resumen de Columnas Numéricas**")
                    num_df = pd.DataFrame(hc["numeric_summary"]).T
                    st.dataframe(num_df.style.format({
                        "mean": "{:.2f}",
                        "std": "{:.2f}",
                        "min": "{:.2f}",
                        "max": "{:.2f}",
                        "pct_zeros": "{:.1f}%"
                    }), use_container_width=True)
                
                # Categorical summary
                if hc.get("categorical_summary"):
                    st.markdown("**Resumen de Columnas Categóricas**")
                    cat_rows = []
                    for col, meta in hc["categorical_summary"].items():
                        tops = ", ".join([f"{v[0]} ({v[1]})" for v in meta["top_values"]]) if meta["top_values"] else "N/A"
                        cat_rows.append({"Columna": col, "Únicos": meta["unique"], "Top 3": tops})
                    st.table(pd.DataFrame(cat_rows))
                
                # Date issues
                if hc.get("date_issues"):
                    di = {k: v for k, v in hc["date_issues"].items() if v["nat_count"] > 0}
                    if di:
                        st.markdown("**Problemas de Fecha (NaT)**")
                        st.table(pd.DataFrame(di).T)
                
                # Suggestions
                if hc.get("suggestions"):
                    st.markdown("**🔍 Sugerencias de Limpieza**")
                    for s in hc["suggestions"]:
                        st.write(f"⚠️ {s}")
                
        elif status == "missing":
            st.warning(f"⚠️ {name} no cargado")
        else:
            st.error(f"❌ {name} inválido")
            hc = datasets.get(name, {}).get("health")
            if hc and hc.get("missing_required_cols"):
                st.write(f"Columnas faltantes: {hc['missing_required_cols']}")

datasets_disponibles = [k for k, v in health_status.items() if v == "ok"]

if not datasets_disponibles:
    st.stop()

# =============================================================================
# ========================= FASE 2 – SKU Fantasma + Variables Derivadas =======
# =============================================================================
if "Inventario Central" in datasets_disponibles and "Transacciones Logísticas" in datasets_disponibles:

    st.markdown("---")
    st.header("👻 FASE 2 – Análisis de SKU Fantasma y Variables Derivadas")

    # ---------------------------
    # 1. Merge Transacciones + Inventario
    # ---------------------------
    inv = datasets["Inventario Central"]["clean"].copy()
    trx = datasets["Transacciones Logísticas"]["clean"].copy()

    inv["SKU_ID"] = inv["SKU_ID"].astype(str).str.strip()
    trx["SKU_ID"] = trx["SKU_ID"].astype(str).str.strip()

    merged = trx.merge(
        inv[["SKU_ID", "Categoria", "Stock_Actual", "Costo_Unitario_USD", "Punto_Reorden", "Lead_Time_Dias"]],
        on="SKU_ID",
        how="left",
        indicator=True
    )

    # ---------------------------
    # 2. Identificación SKUs Fantasma
    # ---------------------------
    merged["sku_status"] = merged["_merge"].apply(lambda x: "FANTASMA" if x=="left_only" else "VALIDO")

    # ---------------------------
    # 3. Normalización de columnas y tipos
    # ---------------------------
    cols_defensivas = [
        "Cantidad_Vendida",
        "Precio_Venta_Final",
        "Costo_Envio",
        "Tiempo_Entrega_Real",
        "Lead_Time_Dias",
        "Ticket_Soporte_Abierto"
    ]
    for col in cols_defensivas:
        if col not in merged.columns:
            merged[col] = 0
    merged["Cantidad_Vendida"] = merged["Cantidad_Vendida"].fillna(0)
    merged["Precio_Venta_Final"] = merged["Precio_Venta_Final"].fillna(0)
    merged["Costo_Envio"] = merged["Costo_Envio"].fillna(0)
    merged["Tiempo_Entrega_Real"] = merged["Tiempo_Entrega_Real"].fillna(0)
    merged["Lead_Time_Dias"] = merged["Lead_Time_Dias"].fillna(0)
    merged["Ticket_Soporte_Abierto"] = merged["Ticket_Soporte_Abierto"].fillna(0).astype(int)
    merged["Costo_Unitario_USD"] = merged["Costo_Unitario_USD"].fillna(0)

    # ---------------------------
    # 4. Variables derivadas
    # ---------------------------
    merged["Ingreso"] = merged["Cantidad_Vendida"] * merged["Precio_Venta_Final"]
    merged["Costo_Total"] = (merged["Cantidad_Vendida"] * merged["Costo_Unitario_USD"]) + merged["Costo_Envio"]
    merged["Margen_Utilidad"] = merged["Ingreso"] - merged["Costo_Total"]
    merged["Margen_Pct"] = merged.apply(lambda x: x["Margen_Utilidad"]/x["Ingreso"] if x["Ingreso"]>0 else 0, axis=1)
    merged["Brecha_Entrega_Dias"] = merged["Tiempo_Entrega_Real"] - merged["Lead_Time_Dias"]

    # Riesgo operativo
    merged["Riesgo_Operativo"] = (
        (merged["sku_status"] == "FANTASMA") |
        (merged["Margen_Utilidad"] < 0) |
        (merged["Brecha_Entrega_Dias"] > 2) |
        (merged["Ticket_Soporte_Abierto"] == 1)
    ).astype(int)

    # Health Score
    merged["Health_Score"] = 100
    merged.loc[merged["sku_status"]=="FANTASMA","Health_Score"] -= 40
    merged.loc[merged["Margen_Utilidad"]<0,"Health_Score"] -= 30
    merged.loc[merged["Brecha_Entrega_Dias"]>2,"Health_Score"] -= 20
    merged.loc[merged["Ticket_Soporte_Abierto"]==1,"Health_Score"] -= 10
    merged["Health_Score"] = merged["Health_Score"].clip(0,100)

    # ---------------------------
    # 5. Dashboard visualizaciones
    # ---------------------------
    st.subheader("📦 Visibilidad de SKUs Fantasma")
    resumen = merged["sku_status"].value_counts().reset_index()
    resumen.columns = ["Estado SKU","Cantidad"]

    col1, col2 = st.columns(2)
    col1.metric("Transacciones Totales", len(merged))
    col2.metric("SKUs Fantasma", resumen.loc[resumen["Estado SKU"]=="FANTASMA","Cantidad"].sum())

    fig1, ax1 = plt.subplots()
    ax1.bar(resumen["Estado SKU"], resumen["Cantidad"], color=["green","red"])
    ax1.set_ylabel("Número de Transacciones")
    ax1.set_title("Distribución SKUs Fantasma vs Válidos")
    st.pyplot(fig1)

    st.subheader("💰 Impacto Financiero y Margen")
    fig2, ax2 = plt.subplots()
    ax2.scatter(merged["Margen_Pct"], merged["Ingreso"], c=merged["Health_Score"], cmap="RdYlGn", alpha=0.7)
    ax2.set_xlabel("Margen %")
    ax2.set_ylabel("Ingreso USD")
    ax2.set_title("Margen vs Ingreso (color = Health Score)")
    st.pyplot(fig2)

    st.subheader("🧠 Riesgo Operativo")
    st.dataframe(merged[[
        "Transaccion_ID","SKU_ID","sku_status","Ingreso","Costo_Total","Margen_Utilidad","Margen_Pct",
        "Brecha_Entrega_Dias","Ticket_Soporte_Abierto","Riesgo_Operativo","Health_Score"
    ]].head(50), use_container_width=True)

    # ---------------------------
    # 6. Descarga CSV de variables derivadas
    # ---------------------------
    csv_derivadas = merged.to_csv(index=False)
    st.download_button(
        "📥 Descargar CSV con Variables Derivadas",
        csv_derivadas,
        f"variables_derivadas_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )


