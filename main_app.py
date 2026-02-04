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

# ---------------------------------------------------
# Análisis con Groq (LLM)
# ---------------------------------------------------
st.subheader("🧠 Análisis con Groq")
st.caption("Ingresa tu API key de Groq para generar un análisis automático del comportamiento por bodega.")

groq_api_key = st.text_input("GROQ API KEY", type="password", help="Tu clave se usa solo en esta sesión.")
groq_model = st.selectbox(
    "Modelo",
    ["llama-3.3-70b-versatile", "openai/gpt-oss-20b"],
    index=0
)
analisis_prompt = st.text_area(
    "Enfoque del análisis",
    value="Analiza riesgos operativos por bodega. Señala outliers, posibles causas y acciones recomendadas.",
    height=120
)

def _build_bodega_context(df):
    if df is None or df.empty:
        return "No hay datos agregados por bodega."
    resumen = df.describe(include="all").to_string()
    top_tickets = df.sort_values("Tasa_Tickets", ascending=False).head(5).to_string(index=False)
    top_antig = df.sort_values("Antiguedad_Revision_Prom", ascending=False).head(5).to_string(index=False)
    return (
        "Resumen estadístico (bodega_summary.describe):\n"
        f"{resumen}\n\n"
        "Top 5 por tasa de tickets:\n"
        f"{top_tickets}\n\n"
        "Top 5 por antigüedad de revisión:\n"
        f"{top_antig}\n"
    )

if st.button("Generar análisis"):
    if not groq_api_key:
        st.warning("Por favor ingresa tu GROQ API KEY.")
    else:
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)

            bodega_df = st.session_state.get("bodega_summary")
            if bodega_df is None or bodega_df.empty:
                st.warning("Aún no hay datos agregados por bodega. Carga los archivos y espera el cálculo.")
            else:
                context = _build_bodega_context(bodega_df)
                messages = [
                    {
                        "role": "system",
                        "content": "Eres un analista de datos senior enfocado en operaciones y calidad de datos."
                    },
                    {
                        "role": "user",
                        "content": f"{analisis_prompt}\n\nDatos:\n{context}"
                    }
                ]

                with st.spinner("Generando análisis con Groq..."):
                    resp = client.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=0.3,
                        max_completion_tokens=700
                    )

                st.markdown(resp.choices[0].message.content)
        except Exception as e:
            st.error(f"No se pudo generar el análisis con Groq: {e}")

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
    """
    Carga y limpia datos de feedback:
    - Filtra edades inválidas (< 0 o > 110)
    """
    df = pd.read_csv(file)
    filas_originales = len(df)
    
    # Filtrar edades válidas
    df_limpio = df[(df["Edad_Cliente"] >= 0) & (df["Edad_Cliente"] <= 110)].copy()
    
    filas_eliminadas = filas_originales - len(df_limpio)
    return df, df_limpio, filas_eliminadas

def cargar_inventario(file):
    """
    Carga y limpia datos de inventario:
    
    VALIDACIONES EXHAUSTIVAS:
    ├─ A. INCONSISTENCIAS DE TIPO
    │  ├─ Parsea columnas de fecha (Ultima_Revision, Fecha_Ingreso)
    │  ├─ Valida Lead_Time_Dias como numérico (no fechas mezcladas)
    │  └─ Detecta valores de texto en columnas numéricas de costo/stock
    │
    ├─ B. COSTOS ATÍPICOS ($0.01 - $850k)
    │  ├─ Elimina costos <= $0.00 (lógica contable: debe haber valor)
    │  ├─ Elimina costos > $850,000 (outliers extremos - fila 500)
    │  └─ Detecta costos en rango válido Q1-Q3 para imputación
    │
    └─ C. EXISTENCIAS NEGATIVAS (Desafío a lógica contable)
       ├─ Elimina stock < 0 con Lead_Time NaN (datos irrecuperables)
       ├─ Imputa stock < 0 si costo está en Q1-Q3 (datos parcialmente confiables)
       └─ Elimina stock < 0 residual (datos sin base para reconstruir)
    """
    df = pd.read_csv(file)
    filas_originales = len(df)
    df_limpio = df.copy()
    
    # =================================================================
    # A. VALIDACIÓN DE TIPOS DE DATOS (Fechas vs Números Mezclados)
    # =================================================================
    
    # 1. Parsear columnas de fecha (case-insensitive)
    fecha_cols = [col for col in df_limpio.columns if "fecha" in col.lower() or "revision" in col.lower()]
    for col in fecha_cols:
        if col in df_limpio.columns:
            df_limpio[col] = pd.to_datetime(df_limpio[col], errors="coerce")
    
    # 2. Forzar Lead_Time_Dias como numérico (eliminar strings de fechas que pudieron colarse)
    if "Lead_Time_Dias" in df_limpio.columns:
        # Intentar conversión numérica; si falla, marca como NaN
        df_limpio["Lead_Time_Dias"] = pd.to_numeric(df_limpio["Lead_Time_Dias"], errors="coerce")
        # Validar rango lógico: lead time debe estar entre 0 y 365 días
        mask_lead_inválido = (df_limpio["Lead_Time_Dias"] < 0) | (df_limpio["Lead_Time_Dias"] > 365)
        df_limpio.loc[mask_lead_inválido, "Lead_Time_Dias"] = None
    
    # 3. Validar Stock_Actual como numérico
    if "Stock_Actual" in df_limpio.columns:
        df_limpio["Stock_Actual"] = pd.to_numeric(df_limpio["Stock_Actual"], errors="coerce")
        # Stock no puede ser negativo; llenar NaN inicialmente
        df_limpio["Stock_Actual"] = df_limpio["Stock_Actual"].fillna(-999)  # marker temporal
    
    # 4. Validar Costo_Unitario_USD como numérico
    if "Costo_Unitario_USD" in df_limpio.columns:
        df_limpio["Costo_Unitario_USD"] = pd.to_numeric(df_limpio["Costo_Unitario_USD"], errors="coerce")
    
    # =================================================================
    # B. COSTOS ATÍPICOS (Rango $0.01 - $850,000)
    # =================================================================
    
    # 1. Eliminar costos <= $0.00 (violación lógica contable)
    if "Costo_Unitario_USD" in df_limpio.columns:
        mask_costo_cero = df_limpio["Costo_Unitario_USD"] <= 0
        df_limpio = df_limpio[~mask_costo_cero]
    
    # 2. Eliminar costos > $850,000 (outliers extremos)
    if "Costo_Unitario_USD" in df_limpio.columns:
        mask_costo_extremo = df_limpio["Costo_Unitario_USD"] > 850000
        df_limpio = df_limpio[~mask_costo_extremo]
    
    # 3. Eliminar fila con índice 500 si existe (mecanismo de seguridad adicional)
    if 500 in df_limpio.index:
        df_limpio = df_limpio.drop(index=500)
    
    # =================================================================
    # C. EXISTENCIAS NEGATIVAS (Lógica Contable Violada)
    # =================================================================
    
    # 1. ELIMINAR FILAS CON MÚLTIPLES ANOMALÍAS
    #    (Stock < 0 AND Lead_Time NaN AND Costo atípico)
    #    → Estos datos son irrecuperables
    if "Stock_Actual" in df_limpio.columns and "Lead_Time_Dias" in df_limpio.columns:
        mask_multi = (df_limpio["Stock_Actual"] < 0) & (df_limpio["Lead_Time_Dias"].isna())
        if "Costo_Unitario_USD" in df_limpio.columns:
            mask_costo_fuera = (df_limpio["Costo_Unitario_USD"] < 0.01) | (df_limpio["Costo_Unitario_USD"] > 850000)
            mask_multi = mask_multi | ((df_limpio["Stock_Actual"] < 0) & mask_costo_fuera)
        df_limpio = df_limpio[~mask_multi]
    
    # 2. IMPUTAR Stock negativo con MEDIANA POR CATEGORÍA
    #    SOLO si el Costo está en rango razonable (Q1-Q3)
    if ("Categoria" in df_limpio.columns and 
        "Costo_Unitario_USD" in df_limpio.columns and 
        "Stock_Actual" in df_limpio.columns):
        
        # Calcular mediana de stock positivo por categoría
        median_stock = (
            df_limpio["Stock_Actual"]
            .where(df_limpio["Stock_Actual"] >= 0)  # negativos → NaN
            .groupby(df_limpio["Categoria"])
            .transform("median")
        )
        
        # Calcular Q1 y Q3 de Costo por categoría (rango razonable)
        q1_costo = df_limpio.groupby("Categoria")["Costo_Unitario_USD"].transform(lambda s: s.quantile(0.25))
        q3_costo = df_limpio.groupby("Categoria")["Costo_Unitario_USD"].transform(lambda s: s.quantile(0.75))
        
        # Máscara: stock negativo AND costo en rango Q1-Q3
        mask_imputar = (df_limpio["Stock_Actual"] < 0) & (df_limpio["Costo_Unitario_USD"].between(q1_costo, q3_costo, inclusive="both"))
        
        # Aplicar imputación
        df_limpio.loc[mask_imputar, "Stock_Actual"] = median_stock[mask_imputar]
    
    # 3. ELIMINAR STOCK NEGATIVO RESIDUAL
    #    → Datos sin base para reconstruir (sin mediana de categoría o costo fuera de rango)
    if "Stock_Actual" in df_limpio.columns:
        mask_stock_negativo = df_limpio["Stock_Actual"] < 0
        df_limpio = df_limpio[~mask_stock_negativo]
    
    # Limpiar marker temporal de Stock_Actual
    if "Stock_Actual" in df_limpio.columns:
        df_limpio["Stock_Actual"] = df_limpio["Stock_Actual"].replace(-999, None)

    filas_eliminadas = filas_originales - len(df_limpio)
    return df, df_limpio, int(filas_eliminadas)

def cargar_transacciones(file):
    """
    Carga y limpia datos de transacciones:
    - Parsea TODAS las columnas de fecha
    - Elimina transacciones con anomalías de cantidad/costo
    - Elimina transacciones con entregas extremadamente atrasadas
    - Filtra transacciones con fecha futura
    """
    df = pd.read_csv(file)
    filas_originales = len(df)
    df_limpio = df.copy()
    
    # 1. Parsear TODAS las columnas con "fecha" (case-insensitive)
    for col in df_limpio.columns:
        if "fecha" in col.lower():
            df_limpio[col] = pd.to_datetime(df_limpio[col], errors="coerce")
    
    # 2. Eliminar filas con cantidad negativa Y costo envío NaN
    #    (anomalía: sin cantidad positiva y sin justificación de costo)
    if "Cantidad_Vendida" in df_limpio.columns and "Costo_Envio" in df_limpio.columns:
        mask1 = (df_limpio["Cantidad_Vendida"] < 0) & (df_limpio["Costo_Envio"].isna())
        df_limpio = df_limpio[~mask1]
    
    # 3. Eliminar filas con cantidad negativa Y tiempo entrega > 100 días
    #    (anomalía: cantidad inconsistente + entrega extremadamente atrasada)
    if "Cantidad_Vendida" in df_limpio.columns and "Tiempo_Entrega_Real" in df_limpio.columns:
        mask2 = (df_limpio["Cantidad_Vendida"] < 0) & (df_limpio["Tiempo_Entrega_Real"] > 100)
        df_limpio = df_limpio[~mask2]
    
    # 4. Eliminar cantidades negativas RESIDUALES (cualquier cantidad < 0 que no haya sido capturada)
    if "Cantidad_Vendida" in df_limpio.columns:
        mask_qty_neg = df_limpio["Cantidad_Vendida"] < 0
        df_limpio = df_limpio[~mask_qty_neg]
    
    # 5. Filtrar transacciones con fecha FUTURA (no deben existir)
    if "Fecha_Venta" in df_limpio.columns:
        df_limpio = df_limpio[df_limpio["Fecha_Venta"] <= pd.Timestamp.now()]
    
    filas_eliminadas = filas_originales - len(df_limpio)
    return df, df_limpio, int(filas_eliminadas)

# =============================================================================
# HEALTHCHECK – CONTROL DE CALIDAD DE DATOS (PROFUNDO)
# =============================================================================
def run_healthcheck(df_raw, required_cols=None, dataset_name=None):
    """
    Comprehensive health check including memory, numeric/categorical summaries,
    date parse issues, and actionable suggestions.
    
    VALIDACIONES ESPECIALIZADAS:
    - Para Inventario: detecta costos atípicos, inconsistencias de tipo, stock negativo
    - Para otros datasets: validaciones generales
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

    # VALIDACIONES ESPECIALIZADAS PARA INVENTARIO
    hc["inventory_validation"] = {}
    if dataset_name == "Inventario Central":
        # A. INCONSISTENCIAS DE TIPO
        type_issues = []
        
        # Lead_Time_Dias debe ser numérico, no fechas
        if "Lead_Time_Dias" in df_raw.columns:
            lead_time_na = df_raw["Lead_Time_Dias"].isna().sum()
            if lead_time_na > 0:
                type_issues.append(f"Lead_Time_Dias con NaN: {lead_time_na} ({(lead_time_na/len(df_raw)*100):.1f}%)")
            # Validar rango lógico: 0-365 días
            try:
                lead_numeric = pd.to_numeric(df_raw["Lead_Time_Dias"], errors="coerce")
                invalid_lead = ((lead_numeric < 0) | (lead_numeric > 365)).sum()
                if invalid_lead > 0:
                    type_issues.append(f"Lead_Time_Dias fuera de rango [0-365]: {invalid_lead} ({(invalid_lead/len(df_raw)*100):.1f}%)")
            except:
                pass
        
        # Ultima_Revision debe ser fecha, no numérica
        if "Ultima_Revision" in df_raw.columns:
            try:
                nat_dates = pd.to_datetime(df_raw["Ultima_Revision"], errors="coerce").isna().sum()
                if nat_dates > len(df_raw) * 0.1:
                    type_issues.append(f"Ultima_Revision con parse errors: {nat_dates} ({(nat_dates/len(df_raw)*100):.1f}%)")
            except:
                pass
        
        hc["inventory_validation"]["type_issues"] = type_issues if type_issues else ["✓ Sin inconsistencias de tipo detectadas"]
        
        # B. COSTOS ATÍPICOS ($0.01 - $850k)
        cost_issues = []
        if "Costo_Unitario_USD" in df_raw.columns:
            try:
                costo = pd.to_numeric(df_raw["Costo_Unitario_USD"], errors="coerce")
                
                # Costos <= $0.00
                costo_cero = (costo <= 0).sum()
                if costo_cero > 0:
                    cost_issues.append(f"Costos <= $0.00: {costo_cero} ({(costo_cero/len(df_raw)*100):.1f}%)")
                
                # Costos > $850k
                costo_extremo = (costo > 850000).sum()
                if costo_extremo > 0:
                    cost_issues.append(f"Costos > $850,000: {costo_extremo} ({(costo_extremo/len(df_raw)*100):.1f}%)")
                
                # Estadísticas de rango válido
                costo_valido = costo[(costo > 0) & (costo <= 850000)]
                if len(costo_valido) > 0:
                    cost_issues.append(f"Rango válido: ${costo_valido.min():.2f} - ${costo_valido.max():.2f}")
            except Exception as e:
                cost_issues.append(f"Error en análisis de costos: {str(e)}")
        
        hc["inventory_validation"]["cost_issues"] = cost_issues if cost_issues else ["✓ Costos dentro de rango válido"]
        
        # C. EXISTENCIAS NEGATIVAS
        stock_issues = []
        if "Stock_Actual" in df_raw.columns:
            try:
                stock = pd.to_numeric(df_raw["Stock_Actual"], errors="coerce")
                stock_negativo = (stock < 0).sum()
                stock_cero = (stock == 0).sum()
                stock_na = stock.isna().sum()
                
                if stock_negativo > 0:
                    stock_issues.append(f"Stock < 0 (desafío contable): {stock_negativo} ({(stock_negativo/len(df_raw)*100):.1f}%)")
                if stock_cero > 0:
                    stock_issues.append(f"Stock = 0 (sin existencias): {stock_cero} ({(stock_cero/len(df_raw)*100):.1f}%)")
                if stock_na > 0:
                    stock_issues.append(f"Stock con NaN: {stock_na} ({(stock_na/len(df_raw)*100):.1f}%)")
                
                # Estadísticas
                stock_valido = stock[stock > 0]
                if len(stock_valido) > 0:
                    stock_issues.append(f"Existencias activas: min={stock_valido.min():.0f}, promedio={stock_valido.mean():.0f}, máx={stock_valido.max():.0f}")
            except Exception as e:
                stock_issues.append(f"Error en análisis de stock: {str(e)}")
        
        hc["inventory_validation"]["stock_issues"] = stock_issues if stock_issues else ["✓ Existencias válidas"]

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
    
    # Añadir sugerencias de inventario
    if dataset_name == "Inventario Central":
        if hc["inventory_validation"].get("type_issues") and any("inconsistencias" in s for s in hc["inventory_validation"]["type_issues"]):
            suggestions.append("⚠️ Revisar inconsistencias de tipo (Lead_Time como texto o fechas)")
        if hc["inventory_validation"].get("cost_issues") and any("$" in s for s in hc["inventory_validation"]["cost_issues"]):
            suggestions.append("⚠️ Costos fuera del rango válido detectados")
        if hc["inventory_validation"].get("stock_issues") and any("desafío contable" in s or "NaN" in s for s in hc["inventory_validation"]["stock_issues"]):
            suggestions.append("⚠️ Existencias negativas o faltantes detectadas")
    
    hc["suggestions"] = suggestions

    # Health score
    score = 100
    if hc["missing_pct"]:
        score -= sum(hc["missing_pct"].values()) / 10
    score -= hc["duplicates"] * 0.5
    
    # Penalización adicional para inventario con problemas críticos
    if dataset_name == "Inventario Central":
        if hc["inventory_validation"].get("stock_issues"):
            for issue in hc["inventory_validation"]["stock_issues"]:
                if "desafío contable" in issue:
                    score -= 25
                elif "NaN" in issue:
                    score -= 10
    
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
    health_clean = run_healthcheck(df_clean, required_cols, dataset_name=name)
    health_clean["filas_eliminadas"] = filas_eliminadas

    datasets[name] = {"raw": df_raw, "clean": df_clean, "health": health_clean}
    health_status[name] = health_clean["status"]

# =============================================================================
# VISUALIZACIÓN DEL HEALTHCHECK (PROFUNDO)
# =============================================================================
st.subheader("📋 FASE 1 – Ingesta, Limpieza y Control de Calidad")

# Mostrar estado de carga
st.markdown("### 1️⃣ Estado de Carga de Archivos")
cols = st.columns(3)
for col, (name, status) in zip(cols, health_status.items()):
    with col:
        if status == "ok":
            st.success(f"✅ {name}")
        elif status == "missing":
            st.warning(f"⚠️ {name}\nNo cargado")
        else:
            st.error(f"❌ {name}\nInválido")

datasets_disponibles = [k for k, v in health_status.items() if v == "ok"]

if not datasets_disponibles:
    st.stop()

# Mostrar proceso de limpieza y health check antes/después
st.markdown("### 2️⃣ Proceso de Limpieza y Control de Calidad")

for name in datasets_disponibles:
    with st.expander(f"📊 {name} - Limpieza y Health Check"):
        hc_raw = run_healthcheck(datasets[name]["raw"], FILES_CONFIG.get(name, (None, None, None))[2], dataset_name=name)
        hc_clean = datasets[name]["health"]
        
        # Resumen de limpieza
        col1, col2, col3 = st.columns(3)
        col1.metric("Filas Originales", hc_raw["rows"])
        col2.metric("Filas Eliminadas", hc_clean["filas_eliminadas"])
        col3.metric("Filas Finales", hc_clean["rows"])
        
        # Comparación de health scores
        st.markdown("#### Health Score: Antes vs Después")
        col_before, col_after = st.columns(2)
        
        with col_before:
            st.metric("Health Score (Raw)", hc_raw["health_score"], delta=None)
            st.markdown("**Raw Data Metrics:**")
            st.write(f"- Columnas: {hc_raw['cols']}")
            st.write(f"- Duplicados: {hc_raw['duplicates']}")
            
            missing_raw = {k: v for k, v in hc_raw["missing_pct"].items() if v > 0}
            if missing_raw:
                st.write(f"- Valores faltantes: {len(missing_raw)} columnas")
            else:
                st.write("- Valores faltantes: 0")
        
        with col_after:
            st.metric("Health Score (Clean)", hc_clean["health_score"], delta=round(hc_clean["health_score"] - hc_raw["health_score"], 2))
            st.markdown("**Clean Data Metrics:**")
            st.write(f"- Columnas: {hc_clean['cols']}")
            st.write(f"- Duplicados: {hc_clean['duplicates']}")
            
            missing_clean = {k: v for k, v in hc_clean["missing_pct"].items() if v > 0}
            if missing_clean:
                st.write(f"- Valores faltantes: {len(missing_clean)} columnas")
            else:
                st.write("- Valores faltantes: 0")
        
        # Detalles completos del raw data
        with st.expander("📈 Detalles Raw Data"):
            st.markdown(f"**Métricas Básicas**")
            st.write(f"- Memoria: {round(hc_raw['memory_bytes']/(1024**2), 2) if hc_raw.get('memory_bytes') else 'N/A'} MB")
            
            missing_pct_raw = {k: v for k, v in hc_raw["missing_pct"].items() if v > 0}
            if missing_pct_raw:
                st.markdown("**Valores Faltantes (% por columna)**")
                sorted_missing = dict(sorted(missing_pct_raw.items(), key=lambda x: x[1], reverse=True))
                st.table(pd.DataFrame(list(sorted_missing.items()), columns=["Columna", "% Missing"]))
            
            if hc_raw.get("numeric_summary"):
                st.markdown("**Resumen Numérico**")
                num_df = pd.DataFrame(hc_raw["numeric_summary"]).T
                st.dataframe(num_df.style.format({
                    "mean": "{:.2f}",
                    "std": "{:.2f}",
                    "min": "{:.2f}",
                    "max": "{:.2f}",
                    "pct_zeros": "{:.1f}%"
                }), use_container_width=True)
        
        # Detalles completos del clean data
        with st.expander("📈 Detalles Clean Data"):
            st.markdown(f"**Métricas Básicas**")
            st.write(f"- Memoria: {round(hc_clean['memory_bytes']/(1024**2), 2) if hc_clean.get('memory_bytes') else 'N/A'} MB")
            
            missing_pct_clean = {k: v for k, v in hc_clean["missing_pct"].items() if v > 0}
            if missing_pct_clean:
                st.markdown("**Valores Faltantes (% por columna)**")
                sorted_missing = dict(sorted(missing_pct_clean.items(), key=lambda x: x[1], reverse=True))
                st.table(pd.DataFrame(list(sorted_missing.items()), columns=["Columna", "% Missing"]))
            else:
                st.info("✅ Sin valores faltantes en datos limpios")
            
            if hc_clean.get("numeric_summary"):
                st.markdown("**Resumen Numérico**")
                num_df = pd.DataFrame(hc_clean["numeric_summary"]).T
                st.dataframe(num_df.style.format({
                    "mean": "{:.2f}",
                    "std": "{:.2f}",
                    "min": "{:.2f}",
                    "max": "{:.2f}",
                    "pct_zeros": "{:.1f}%"
                }), use_container_width=True)
            
            # Sugerencias
            if hc_clean.get("suggestions"):
                st.markdown("**🔍 Sugerencias Adicionales**")
                for s in hc_clean["suggestions"]:
                    st.write(f"⚠️ {s}")
        
        # VALIDACIONES ESPECIALIZADAS DE INVENTARIO
        if name == "Inventario Central" and hc_clean.get("inventory_validation"):
            with st.expander("🔍 Validaciones Especializadas de Inventario"):
                st.markdown("#### A. Inconsistencias de Tipo (Fechas vs Lead Times)")
                for issue in hc_clean["inventory_validation"].get("type_issues", []):
                    if "✓" in issue:
                        st.success(issue)
                    else:
                        st.warning(issue)
                
                st.markdown("#### B. Costos Atípicos ($0.01 - $850k)")
                for issue in hc_clean["inventory_validation"].get("cost_issues", []):
                    if "✓" in issue or "Rango válido" in issue:
                        st.success(issue)
                    else:
                        st.error(issue)
                
                st.markdown("#### C. Existencias Negativas (Lógica Contable)")
                for issue in hc_clean["inventory_validation"].get("stock_issues", []):
                    if "✓" in issue or "Existencias activas" in issue:
                        st.success(issue)
                    else:
                        st.error(issue)

st.markdown("---")

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
    merged["Tiempo_Entrega_Real"] = pd.to_numeric(merged["Tiempo_Entrega_Real"], errors="coerce").fillna(0)
    merged["Lead_Time_Dias"] = pd.to_numeric(merged["Lead_Time_Dias"], errors="coerce").fillna(0)
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

# =============================================================================
# ========================= FASE 3 – STORYTELLING AVANZADO ==================
# =============================================================================

if "Feedback de Clientes" in datasets_disponibles:
    fb = datasets["Feedback de Clientes"]["clean"].copy()
else:
    st.warning("⚠️ No se cargó Feedback de Clientes. Algunas métricas no estarán disponibles.")
    fb = pd.DataFrame(columns=[
        "Feedback_ID","Transaccion_ID","Rating_Producto","Rating_Logistica",
        "Comentario_Texto","Recomienda_Marca","Ticket_Soporte_Abierto",
        "Edad_Cliente","Satisfaccion_NPS"
    ])

# Aseguramos que trx exista
if "Transacciones Logísticas" in datasets_disponibles:
    trx = datasets["Transacciones Logísticas"]["clean"].copy()
else:
    trx = pd.DataFrame(columns=[
        "Transaccion_ID","SKU_ID","Fecha_Venta","Cantidad_Vendida",
        "Precio_Venta_Final","Costo_Envio","Tiempo_Entrega_Real",
        "Estado_Envio","Ciudad_Destino","Canal_Venta"
    ])

# Normalizamos IDs para merge
fb["Transaccion_ID"] = fb["Transaccion_ID"].astype(str).str.strip()
trx["Transaccion_ID"] = trx["Transaccion_ID"].astype(str).str.strip()
trx["SKU_ID"] = trx["SKU_ID"].astype(str).str.strip()

# Merge Feedback + Transacciones para traer SKU_ID a Feedback
fb_sku = fb.merge(trx[["Transaccion_ID","SKU_ID"]], on="Transaccion_ID", how="left")

st.header("📊 Fase 3 – Storytelling Avanzado")

# Verificamos merged
if "merged" not in locals():
    st.warning("⚠️ Necesitas haber ejecutado la fase 2 para generar 'merged'.")
    st.stop()

# ---------- 1. Fuga de Capital ----------
st.subheader("1️⃣ Fuga de Capital y Rentabilidad")
negativos = merged[merged["Margen_Utilidad"] < 0].copy()
st.metric("SKUs con margen negativo", len(negativos))
st.metric("Ingreso en riesgo (USD)", f"{negativos['Ingreso'].sum():,.0f}")
st.metric("% Ingreso en riesgo", f"{(negativos['Ingreso'].sum()/merged['Ingreso'].sum())*100:.2f}%")

fig, ax = plt.subplots(figsize=(6,4))
margen_counts = merged["Margen_Utilidad"].apply(lambda x: "Negativo" if x<0 else "Positivo").value_counts()
ax.bar(margen_counts.index, margen_counts.values, color=["red","green"])
ax.set_title("Distribución de Margen de Utilidad")
ax.set_ylabel("Cantidad de Transacciones")
st.pyplot(fig)

st.dataframe(negativos[["SKU_ID","Cantidad_Vendida","Ingreso","Costo_Total","Margen_Utilidad"]])

# ---------- 2. Crisis Logística ----------
st.subheader("2️⃣ Crisis Logística y Cuellos de Botella")
log_merge = merged.merge(fb_sku[["Transaccion_ID","Satisfaccion_NPS"]], on="Transaccion_ID", how="left")
log_merge["Tiempo_Entrega_Real"] = log_merge["Tiempo_Entrega_Real"].fillna(0)
log_merge["Satisfaccion_NPS"] = log_merge["Satisfaccion_NPS"].fillna(0)

corr_ciudad = log_merge.groupby("Ciudad_Destino")[["Tiempo_Entrega_Real","Satisfaccion_NPS"]].corr().iloc[0::2,-1]
corr_ciudad = corr_ciudad.reset_index().rename(columns={"Satisfaccion_NPS":"Corr_Entrega_NPS"})
st.markdown("**Correlación Tiempo de Entrega vs NPS por Ciudad**")
st.dataframe(corr_ciudad.sort_values("Corr_Entrega_NPS"))

fig, ax = plt.subplots(figsize=(8,4))
top_ciudades = corr_ciudad.sort_values("Corr_Entrega_NPS").head(10)
ax.barh(top_ciudades["Ciudad_Destino"], top_ciudades["Corr_Entrega_NPS"], color="orange")
ax.set_xlabel("Correlación")
ax.set_title("Top 10 Ciudades con mayor impacto en satisfacción")
st.pyplot(fig)

# ---------- 3. Venta Invisible ----------
st.subheader("3️⃣ Análisis de la Venta Invisible")
ingreso_total = merged["Ingreso"].sum()
ingreso_fantasma = merged.loc[merged["sku_status"]=="FANTASMA","Ingreso"].sum()
st.metric("Ingreso total (USD)", f"{ingreso_total:,.0f}")
st.metric("Ingreso en riesgo (USD)", f"{ingreso_fantasma:,.0f}")
st.metric("% Ingreso en riesgo", f"{(ingreso_fantasma/ingreso_total)*100:.2f}%")

fig, ax = plt.subplots(figsize=(6,4))
ingresos_tipo = merged.groupby("sku_status")["Ingreso"].sum()
ax.bar(ingresos_tipo.index, ingresos_tipo.values, color=["red","green"])
ax.set_ylabel("Ingreso (USD)")
ax.set_title("Impacto financiero por tipo de SKU")
st.pyplot(fig)


# ---------- 4️⃣ Diagnóstico de Fidelidad ----------
st.subheader("4️⃣ Diagnóstico de Fidelidad: Stock Alto vs. Satisfacción Baja")

# Verificar que inv y fb_sku existan
if 'inv' not in locals() or 'fb_sku' not in locals():
    st.error("❌ No se han cargado Inventario Central o Feedback por SKU. Ejecuta Fase 2 primero.")
    st.stop()

# Normalizar nombres de categorías
if 'Categoria' in inv.columns:
    inv["Categoria"] = inv["Categoria"].fillna("").str.lower().str.replace("-", "").str.strip()
    inv["Categoria"] = inv["Categoria"].replace({
        "smartphone": "smartphone",
        "smartphones": "smartphone"
    })
else:
    st.error("❌ Columna 'Categoria' no encontrada en Inventario")
    st.stop()

# Merge con feedback por SKU
df_fidelidad = inv.merge(
    fb_sku.groupby("SKU_ID")["Satisfaccion_NPS"].mean().reset_index(),
    on="SKU_ID",
    how="left"
)

# Filtro de riesgo: stock alto (percentil 75) y NPS bajo (percentil 25)
stock_p75 = df_fidelidad["Stock_Actual"].quantile(0.75)
nps_p25 = df_fidelidad["Satisfaccion_NPS"].quantile(0.25)

fidelidad_riesgo = df_fidelidad[
    (df_fidelidad["Stock_Actual"] > stock_p75) &
    (df_fidelidad["Satisfaccion_NPS"] < nps_p25)
].copy()

# Agrupar por categoría para dashboard
categoria_summary = fidelidad_riesgo.groupby("Categoria").agg(
    Cantidad_SKU=("SKU_ID","count"),
    Stock_Total=("Stock_Actual","sum"),
    NPS_Promedio=("Satisfaccion_NPS","mean")
).reset_index()

categoria_summary = categoria_summary.sort_values(["Cantidad_SKU","NPS_Promedio"], ascending=[False,True])

# Mostrar tabla
st.subheader("📋 Categorías Críticas")
st.dataframe(categoria_summary, use_container_width=True, hide_index=True)

# Gráfico: Stock vs NPS
st.subheader("📍 Matriz de Riesgo: Stock vs Satisfacción")
fig, ax = plt.subplots(figsize=(10,6))

# Todos los SKUs
ax.scatter(
    df_fidelidad["Stock_Actual"],
    df_fidelidad["Satisfaccion_NPS"],
    alpha=0.5,
    s=50,
    color='blue',
    label='Todos los SKUs'
)

# SKUs en riesgo
if not fidelidad_riesgo.empty:
    ax.scatter(
        fidelidad_riesgo["Stock_Actual"],
        fidelidad_riesgo["Satisfaccion_NPS"],
        s=100,
        color='red',
        label=f'En Riesgo ({len(fidelidad_riesgo)})',
        zorder=5
    )

# Líneas de referencia
ax.axhline(y=nps_p25, color='orange', linestyle='--', label=f'NPS Bajo ({nps_p25:.0f})')
ax.axvline(x=stock_p75, color='green', linestyle='--', label=f'Stock Alto ({stock_p75:.0f})')

ax.set_xlabel("Stock Actual")
ax.set_ylabel("Satisfacción NPS")
ax.set_title("Identificación de SKUs Problemáticos")
ax.legend()
ax.grid(True, alpha=0.3)

st.pyplot(fig)

# Recomendaciones rápidas
st.subheader("🎯 Análisis Rápido")
if not fidelidad_riesgo.empty:
    st.success(f"**Se encontraron {len(fidelidad_riesgo)} SKUs en riesgo**")
    st.write("**Categorías más afectadas:**")
    for idx, row in categoria_summary.head(3).iterrows():
        st.write(f"- **{row['Categoria'].capitalize()}**: {row['Cantidad_SKU']} SKUs, NPS: {row['NPS_Promedio']:.0f}")
else:
    st.info("✅ No se encontraron SKUs con alto stock y baja satisfacción")

# Botón de exportación
if not fidelidad_riesgo.empty:
    csv = fidelidad_riesgo[['SKU_ID','Categoria','Stock_Actual','Satisfaccion_NPS']].to_csv(index=False)
    st.download_button(
        label="📥 Exportar SKUs en Riesgo",
        data=csv,
        file_name="skus_riesgo.csv",
        mime="text/csv"
    )

    st.info("Asegúrate de tener cargados los datasets de Inventario Central y Feedback de Clientes.") 


# Asegurarnos que los IDs estén limpios
fb_sku["Transaccion_ID"] = fb_sku["Transaccion_ID"].astype(str).str.strip()
trx["Transaccion_ID"] = trx["Transaccion_ID"].astype(str).str.strip()
trx["Bodega_ID"] = trx["Bodega_ID"].astype(str).str.strip() if "Bodega_ID" in trx.columns else "UNKNOWN"

# Merge Feedback + Transacciones para obtener SKU_ID y Bodega
fb_trx = fb_sku.merge(
    trx[["Transaccion_ID","SKU_ID","Bodega_ID"]], 
    on="Transaccion_ID", 
    how="left"
)
# ---------- 5 Relacion bodegas - satisfaccion ----------

inv = datasets["Inventario Central"]["clean"].copy()
trx = datasets["Transacciones Logísticas"]["clean"].copy()
fb = datasets["Feedback de Clientes"]["clean"].copy()

# Normalizar IDs
inv["SKU_ID"] = inv["SKU_ID"].astype(str).str.strip()
trx["SKU_ID"] = trx["SKU_ID"].astype(str).str.strip()
trx["Transaccion_ID"] = trx["Transaccion_ID"].astype(str).str.strip()
fb["Transaccion_ID"] = fb["Transaccion_ID"].astype(str).str.strip()

trx_inv = trx.merge(
    inv[["SKU_ID","Bodega_Origen","Ultima_Revision"]],
    on="SKU_ID",
    how="left"
)
trx_inv_fb = trx_inv.merge(
    fb[["Transaccion_ID","Ticket_Soporte_Abierto","Satisfaccion_NPS"]],
    on="Transaccion_ID",
    how="left"
)

# ---------------------------------------------------
# Cálculo de Antigüedad de Revisión
# ---------------------------------------------------
trx_inv_fb["Ultima_Revision"] = pd.to_datetime(trx_inv_fb["Ultima_Revision"], errors="coerce")
trx_inv_fb["Antiguedad_Revision_Dias"] = (pd.Timestamp.today() - trx_inv_fb["Ultima_Revision"]).dt.days

# Forzar a numérico las columnas que se promedian
for col in ["Antiguedad_Revision_Dias", "Ticket_Soporte_Abierto", "Satisfaccion_NPS"]:
    trx_inv_fb[col] = pd.to_numeric(trx_inv_fb[col], errors="coerce")

# Fill NA para tickets y satisfacción
trx_inv_fb["Ticket_Soporte_Abierto"] = trx_inv_fb["Ticket_Soporte_Abierto"].fillna(0)
trx_inv_fb["Satisfaccion_NPS"] = trx_inv_fb["Satisfaccion_NPS"].fillna(0)

bodega_summary = trx_inv_fb.groupby("Bodega_Origen").agg(
    Antiguedad_Revision_Prom=("Antiguedad_Revision_Dias","mean"),
    Tasa_Tickets=("Ticket_Soporte_Abierto","mean"),
    Satisfaccion_Prom=("Satisfaccion_NPS","mean"),
    Num_Transacciones=("Transaccion_ID","count")
).reset_index()
st.session_state["bodega_summary"] = bodega_summary

# ---------------------------------------------------
# Visualización Scatter
# ---------------------------------------------------
st.subheader("👁️ Riesgo Operativo por Bodega: Antigüedad de Revisión vs Tasa de Tickets")

fig, ax = plt.subplots(figsize=(10, 6))
sc = ax.scatter(
    bodega_summary["Antiguedad_Revision_Prom"],
    bodega_summary["Tasa_Tickets"],
    s=bodega_summary["Num_Transacciones"] * 5,  # tamaño burbuja según volumen
    c=bodega_summary["Satisfaccion_Prom"],      # color según satisfacción
    cmap="RdYlGn_r",
    alpha=0.8,
    edgecolors="black"
)

for _, row in bodega_summary.iterrows():
    ax.text(
        row["Antiguedad_Revision_Prom"] + 0.5,
        row["Tasa_Tickets"] + 0.005,
        row["Bodega_Origen"],
        fontsize=8
    )

ax.set_xlabel("Antigüedad Promedio de Última Revisión (días)")
ax.set_ylabel("Tasa de Tickets de Soporte Abierto")
ax.set_title("Bodegas Operando a Ciegas y su Impacto en Satisfacción")
cbar = plt.colorbar(sc)
cbar.set_label("Satisfacción NPS Promedio")
ax.grid(True, alpha=0.3)
st.pyplot(fig)

# ---------------------------------------------------
# Tabla de resumen por bodega
# ---------------------------------------------------
st.subheader("📋 Resumen por Bodega")
st.dataframe(bodega_summary.sort_values("Tasa_Tickets", ascending=False))
