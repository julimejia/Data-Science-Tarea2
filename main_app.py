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
# CLASE PARA RASTREO DETALLADO DE LIMPIEZA
# =============================================================================
class CleaningLogger:
    """
    Registra cada paso del proceso de limpieza con detalles:
    - Qué paso se ejecutó
    - Cuántas filas había antes
    - Cuántas filas se eliminaron
    - POR QUÉ se eliminaron
    - QUÉ MÉTODO se utilizó
    - Observaciones adicionales
    """
    def __init__(self):
        self.steps = []
    
    def log_step(self, step_name, rows_before, rows_after, reason, method, details=""):
        """
        Registra un paso de limpieza
        
        Args:
            step_name: Nombre descriptivo del paso (ej: "Eliminar Duplicados Completos")
            rows_before: Número de filas ANTES de este paso
            rows_after: Número de filas DESPUÉS de este paso
            reason: POR QUÉ se eliminaron filas (lógica de negocio)
            method: CÓMO se detectaron/eliminaron (función, máscara, operación)
            details: Observaciones adicionales
        """
        self.steps.append({
            "paso": len(self.steps) + 1,
            "nombre": step_name,
            "filas_antes": rows_before,
            "filas_despues": rows_after,
            "filas_eliminadas": rows_before - rows_after,
            "pct_eliminado": round((rows_before - rows_after) / max(1, rows_before) * 100, 2),
            "razon": reason,
            "metodo": method,
            "detalles": details
        })
    
    def to_dict(self):
        """Convierte los logs a diccionario para visualización"""
        return {
            "total_pasos": len(self.steps),
            "total_filas_eliminadas": sum(s["filas_eliminadas"] for s in self.steps),
            "pasos": self.steps
        }
    
    def get_summary_text(self):
        """Genera resumen en texto para mostrar"""
        if not self.steps:
            return "Sin cambios detectados"
        
        lines = []
        for s in self.steps:
            lines.append(f"Paso {s['paso']}: {s['nombre']}")
            lines.append(f"  Filas: {s['filas_antes']} → {s['filas_despues']} (eliminadas: {s['filas_eliminadas']} = {s['pct_eliminado']}%)")
            lines.append(f"  Razón: {s['razon']}")
            lines.append(f"  Método: {s['metodo']}")
            if s['detalles']:
                lines.append(f"  Detalles: {s['detalles']}")
            lines.append("")
        
        return "\n".join(lines)


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
    Carga y limpia datos de feedback CON RASTREO DETALLADO DE CADA PASO.
    
    Retorna: (df_raw, df_clean, filas_eliminadas, cleaning_log)
    """
    df = pd.read_csv(file)
    filas_originales = len(df)
    df_limpio = df.copy()
    
    # Inicializar logger
    logger = CleaningLogger()
    
    # =================================================================
    # A. DUPLICADOS INTENCIONALES
    # =================================================================
    
    # PASO 1: Detectar duplicados completos
    filas_antes_dup_completos = len(df_limpio)
    df_limpio_sin_dup_completos = df_limpio.drop_duplicates(keep='first')
    filas_despues_dup_completos = len(df_limpio_sin_dup_completos)
    
    logger.log_step(
        step_name="Eliminar Duplicados Completos (filas exactamente iguales)",
        rows_before=filas_antes_dup_completos,
        rows_after=filas_despues_dup_completos,
        reason="Una misma fila de feedback aparece múltiples veces idénticamente. Esto genera sesgo en agregaciones: misma opinión se cuenta 2+ veces.",
        method=".drop_duplicates(keep='first') - compara TODOS los valores de columnas",
        details=f"Detectadas {filas_antes_dup_completos - filas_despues_dup_completos} filas idénticas. Se mantiene solo la primera ocurrencia."
    )
    df_limpio = df_limpio_sin_dup_completos
    
    # PASO 2: Detectar duplicados parciales (por Feedback_ID + Transaccion_ID)
    if "Feedback_ID" in df_limpio.columns and "Transaccion_ID" in df_limpio.columns:
        df_limpio["Feedback_ID"] = df_limpio["Feedback_ID"].astype(str).str.strip()
        df_limpio["Transaccion_ID"] = df_limpio["Transaccion_ID"].astype(str).str.strip()
        
        filas_antes_dup_parciales = len(df_limpio)
        df_limpio_sin_dup_parciales = df_limpio.drop_duplicates(
            subset=["Feedback_ID", "Transaccion_ID"], 
            keep='first'
        )
        filas_despues_dup_parciales = len(df_limpio_sin_dup_parciales)
        
        logger.log_step(
            step_name="Eliminar Duplicados Parciales (mismo Feedback_ID + Transaccion_ID)",
            rows_before=filas_antes_dup_parciales,
            rows_after=filas_despues_dup_parciales,
            reason="Mismo cliente comenta dos veces sobre la misma transacción. Intención: registrar cambios de opinión, pero causa sesgo si se cuenta ambas.",
            method=".drop_duplicates(subset=['Feedback_ID', 'Transaccion_ID'], keep='first') - clave compuesta",
            details=f"Detectadas {filas_antes_dup_parciales - filas_despues_dup_parciales} segundas opiniones. Se mantiene solo la PRIMERA (opinión más fresca)."
        )
        df_limpio = df_limpio_sin_dup_parciales
    
    # =================================================================
    # B. EDADES IMPOSIBLES
    # =================================================================
    
    if "Edad_Cliente" in df_limpio.columns:
        df_limpio["Edad_Cliente"] = pd.to_numeric(df_limpio["Edad_Cliente"], errors="coerce")
        
        # PASO 3: Eliminar edades negativas
        filas_antes_edad_neg = len(df_limpio)
        mask_edad_negativa = df_limpio["Edad_Cliente"] < 0
        df_limpio = df_limpio[~mask_edad_negativa]
        filas_despues_edad_neg = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Edades Negativas (< 0)",
            rows_before=filas_antes_edad_neg,
            rows_after=filas_despues_edad_neg,
            reason="Edad negativa es biológicamente imposible. Indica error de entrada o corrupción de datos.",
            method="Máscara booleana: edad < 0, filtrado con operador ~",
            details=f"Ej: edad = -5, -15. {filas_antes_edad_neg - filas_despues_edad_neg} registros. Causa probable: error manual o sincronización de sistemas."
        )
        
        # PASO 4: Eliminar edades > 110
        filas_antes_edad_ext = len(df_limpio)
        mask_edad_extrema = df_limpio["Edad_Cliente"] > 110
        edad_max = df_limpio.loc[mask_edad_extrema, "Edad_Cliente"].max() if mask_edad_extrema.sum() > 0 else 0
        df_limpio = df_limpio[~mask_edad_extrema]
        filas_despues_edad_ext = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Edades Imposibles (> 110 años)",
            rows_before=filas_antes_edad_ext,
            rows_after=filas_despues_edad_ext,
            reason="Edad > 110 viola límites biológicos. Persona más vieja documentada: 122 años. Valores como 195 = error de entrada.",
            method="Máscara booleana: edad > 110, filtrado con operador ~",
            details=f"Detectadas edades imposibles hasta {edad_max:.0f} años. {filas_antes_edad_ext - filas_despues_edad_ext} registros eliminados. Probable: error de digitación (195 vs 19,5) o campo con basura."
        )
        
        # PASO 5: Eliminar edades < 13 (menores de edad)
        filas_antes_edad_menor = len(df_limpio)
        mask_edad_minima = df_limpio["Edad_Cliente"] < 13
        df_limpio = df_limpio[~mask_edad_minima]
        filas_despues_edad_menor = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Edades < 13 años (menores)",
            rows_before=filas_antes_edad_menor,
            rows_after=filas_despues_edad_menor,
            reason="Clientes menores de 13 años no pueden comprar legalmente (restricción por edad). Probable: error de dato o cuenta fraudulenta.",
            method="Máscara booleana: edad < 13, filtrado con operador ~",
            details=f"{filas_antes_edad_menor - filas_despues_edad_menor} menores detectados. Acción: eliminar para cumplir normativa."
        )
    
    # =================================================================
    # C. NORMALIZACIÓN DE NPS
    # =================================================================
    
    if "Satisfaccion_NPS" in df_limpio.columns:
        nps_raw = pd.to_numeric(df_limpio["Satisfaccion_NPS"], errors="coerce")
        
        # PASO 6A: Aplicar valor absoluto a NPS negativos (convertir a positivo)
        nps_raw_abs = nps_raw.abs()
        df_limpio["Satisfaccion_NPS"] = nps_raw_abs
        
        logger.log_step(
            step_name="Aplicar Valor Absoluto a NPS (convertir negativos a positivos)",
            rows_before=len(df_limpio),
            rows_after=len(df_limpio),
            reason="NPS negativo es inconsistencia de entrada, no refleja insatisfacción. Aplicar abs() preserva datos y los convierte a escala válida.",
            method="df.abs() - transforma NPS negativo en positivo sin eliminar",
            details=f"Ej: NPS=-5 → NPS=5. Preserva información original con corrección de signo."
        )
        
        nps_max_original = nps_raw_abs.max()
        nps_min_original = nps_raw_abs.min()
        
        # PASO 6B: Normalización de escala (0-100 → 0-10)
        if nps_max_original > 10 and nps_max_original <= 100:
            filas_antes_nps_norm = len(df_limpio)
            df_limpio["Satisfaccion_NPS"] = (nps_raw_abs / 10).round(2)
            filas_despues_nps_norm = len(df_limpio)  # Sin eliminación, solo transformación
            
            logger.log_step(
                step_name="Normalizar Escala NPS de 0-100 a 0-10",
                rows_before=filas_antes_nps_norm,
                rows_after=filas_despues_nps_norm,
                reason="NPS tiene dos escalas mezcladas: 0-10 y 0-100. Análisis requiere escala uniforme 0-10.",
                method="División por 10: NPS_nuevo = NPS_original / 10. Auto-detección: si max > 10 AND max <= 100",
                details=f"Detectada escala 0-100 (max={nps_max_original:.0f}). Normalización: valor 95 → 9.5. Justificación: escala estándar NPS."
            )
        
        elif nps_max_original > 100:
            filas_antes_nps_ext = len(df_limpio)
            rango = nps_max_original - nps_min_original
            if rango > 0:
                df_limpio["Satisfaccion_NPS"] = ((nps_raw_abs - nps_min_original) / rango * 10).round(2)
            filas_despues_nps_ext = len(df_limpio)
            
            logger.log_step(
                step_name="Normalizar Escala NPS No Estándar (> 100) a 0-10",
                rows_before=filas_antes_nps_ext,
                rows_after=filas_despues_nps_ext,
                reason="Escala NPS no estándar detectada (máximo > 100). Requiere normalización Min-Max a [0, 10].",
                method="Normalización Min-Max: (x - min) / (max - min) * 10",
                details=f"Rango original: [{nps_min_original:.0f}, {nps_max_original:.0f}]. Transformación: Min-Max al rango [0, 10]."
            )
        
        # PASO 7: Eliminar NPS NaN (faltantes)
        filas_antes_nps_na = len(df_limpio)
        mask_nps_na = df_limpio["Satisfaccion_NPS"].isna()
        df_limpio = df_limpio[~mask_nps_na]
        filas_despues_nps_na = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Registros con NPS Faltante (NaN)",
            rows_before=filas_antes_nps_na,
            rows_after=filas_despues_nps_na,
            reason="NPS es métrica principal de satisfacción. Valor faltante = feedback incompleto, no procesable para análisis.",
            method="Máscara booleana: isna(Satisfaccion_NPS), filtrado con operador ~",
            details=f"{filas_antes_nps_na - filas_despues_nps_na} registros sin NPS eliminados. No se pueden imputar (esencial para análisis de satisfacción)."
        )
        
        # PASO 8: Eliminar NPS fuera de rango [0, 10]
        nps_normalizado = pd.to_numeric(df_limpio["Satisfaccion_NPS"], errors="coerce")
        filas_antes_nps_rango = len(df_limpio)
        mask_nps_inválido = (nps_normalizado < 0) | (nps_normalizado > 10)
        df_limpio = df_limpio[~mask_nps_inválido]
        filas_despues_nps_rango = len(df_limpio)
        
        if filas_antes_nps_rango - filas_despues_nps_rango > 0:
            logger.log_step(
                step_name="Eliminar NPS Fuera de Rango [0, 10] (después de normalización)",
                rows_before=filas_antes_nps_rango,
                rows_after=filas_despues_nps_rango,
                reason="NPS después de normalización debe estar en [0, 10]. Valores fuera = error de conversión o dato corrupto.",
                method="Máscara booleana: (NPS < 0) OR (NPS > 10), filtrado con operador ~",
                details=f"{filas_antes_nps_rango - filas_despues_nps_rango} registros fuera de rango. Probable: error en normalización o dato extraño."
            )

    
    filas_eliminadas = filas_originales - len(df_limpio)
    return df, df_limpio, int(filas_eliminadas), logger.to_dict()



def cargar_inventario(file):
    """
    Carga y limpia datos de inventario CON RASTREO DETALLADO DE CADA PASO.
    
    Retorna: (df_raw, df_clean, filas_eliminadas, cleaning_log)
    """
    df = pd.read_csv(file)
    filas_originales = len(df)
    df_limpio = df.copy()
    
    # Inicializar logger
    logger = CleaningLogger()
    
    # =================================================================
    # A. NORMALIZACIÓN DE FECHAS Y LEAD_TIME
    # =================================================================
    
    fecha_cols = [col for col in df_limpio.columns if "fecha" in col.lower() or "revision" in col.lower()]
    for col in fecha_cols:
        if col in df_limpio.columns:
            filas_antes_fecha = len(df_limpio)
            df_limpio[col] = pd.to_datetime(df_limpio[col], errors="coerce")
            filas_despues_fecha = len(df_limpio)
            
            logger.log_step(
                step_name=f"Normalizar Formato de Fecha: {col}",
                rows_before=filas_antes_fecha,
                rows_after=filas_despues_fecha,
                reason=f"Columna {col} tiene múltiples formatos de fecha mezclados. Requiere formato uniforme datetime64.",
                method="pd.to_datetime(errors='coerce') - convierte a formato estándar",
                details=f"Conversión de {filas_antes_fecha} valores a datetime64[ns]. NaT asignado a valores inválidos."
            )
    
    # PASO 2: Lead_Time_Dias validación mediante IQR (Rango Intercuartil)
    if "Lead_Time_Dias" in df_limpio.columns:
        df_limpio["Lead_Time_Dias"] = pd.to_numeric(df_limpio["Lead_Time_Dias"], errors="coerce")
        
        filas_antes_lead = len(df_limpio)
        
        # Calcular IQR
        lead_valid = df_limpio["Lead_Time_Dias"].dropna()
        if len(lead_valid) > 0:
            Q1_lead = lead_valid.quantile(0.25)
            Q3_lead = lead_valid.quantile(0.75)
            IQR_lead = Q3_lead - Q1_lead
            
            # Límites: [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
            lower_bound_lead = Q1_lead - 1.5 * IQR_lead
            upper_bound_lead = Q3_lead + 1.5 * IQR_lead
            
            # Eliminar outliers fuera del rango IQR y valores negativos/NaN
            mask_lead_valido = (df_limpio["Lead_Time_Dias"] >= lower_bound_lead) & (df_limpio["Lead_Time_Dias"] <= upper_bound_lead) & (df_limpio["Lead_Time_Dias"] >= 0)
            df_limpio = df_limpio[mask_lead_valido]
        
        filas_despues_lead = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Lead_Time_Dias Outliers mediante IQR (Rango Intercuartil)",
            rows_before=filas_antes_lead,
            rows_after=filas_despues_lead,
            reason="Lead_Time es días de resurtimiento. Outliers detectados mediante IQR exceden significativamente el rango esperado. Eliminados para garantizar análisis confiable.",
            method=f"Eliminar filas: (Lead_Time < {lower_bound_lead:.1f}) OR (Lead_Time > {upper_bound_lead:.1f}) OR (Lead_Time < 0) OR (Lead_Time NaN)",
            details=f"Q1={Q1_lead:.1f}, Q3={Q3_lead:.1f}, IQR={IQR_lead:.1f}. {filas_antes_lead - filas_despues_lead} outliers eliminados (negativos, NaN, y fuera de rango IQR)."
        )
    
    # =================================================================
    # B. VALIDACIÓN DE COSTOS (Detección de Outliers mediante IQR)
    # =================================================================
    
    if "Costo_Unitario_USD" in df_limpio.columns:
        df_limpio["Costo_Unitario_USD"] = pd.to_numeric(df_limpio["Costo_Unitario_USD"], errors="coerce")
        
        # PASO 3: Eliminar costos <= $0.00 (Restricción Contable Fundamental)
        filas_antes_costo_cero = len(df_limpio)
        mask_costo_cero = df_limpio["Costo_Unitario_USD"] <= 0
        df_limpio = df_limpio[~mask_costo_cero]
        filas_despues_costo_cero = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Costos <= $0.00",
            rows_before=filas_antes_costo_cero,
            rows_after=filas_despues_costo_cero,
            reason="Costo cero o negativo viola lógica contable. Producto debe tener valor >= $0.01.",
            method="Máscara booleana: (Costo <= 0), filtrado con operador ~",
            details=f"{filas_antes_costo_cero - filas_despues_costo_cero} productos con costo inválido eliminados."
        )
        
        # PASO 4: Detectar Outliers Extremos mediante IQR
        filas_antes_costo_iqr = len(df_limpio)
        
        # Calcular IQR
        costo_valid = df_limpio["Costo_Unitario_USD"].dropna()
        if len(costo_valid) > 0:
            Q1_costo = costo_valid.quantile(0.25)
            Q3_costo = costo_valid.quantile(0.75)
            IQR_costo = Q3_costo - Q1_costo
            
            # Límites: [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
            lower_bound_costo = Q1_costo - 1.5 * IQR_costo
            upper_bound_costo = Q3_costo + 1.5 * IQR_costo
            
            # Eliminar outliers fuera del rango IQR
            mask_costo_valido = (df_limpio["Costo_Unitario_USD"] >= lower_bound_costo) & (df_limpio["Costo_Unitario_USD"] <= upper_bound_costo)
            df_limpio = df_limpio[mask_costo_valido]
            
            filas_despues_costo_iqr = len(df_limpio)
            
            logger.log_step(
                step_name="Eliminar Outliers de Costos mediante IQR (Rango Intercuartil)",
                rows_before=filas_antes_costo_iqr,
                rows_after=filas_despues_costo_iqr,
                reason="Costos extremos detectados mediante IQR exceden significativamente el rango normal de costos. Eliminados para garantizar análisis confiable de márgenes.",
                method=f"Eliminar filas: (Costo < ${lower_bound_costo:,.2f}) OR (Costo > ${upper_bound_costo:,.2f})",
                details=f"Q1=${Q1_costo:,.2f}, Q3=${Q3_costo:,.2f}, IQR=${IQR_costo:,.2f}. {filas_antes_costo_iqr - filas_despues_costo_iqr} outliers eliminados (ejemplo: $850k excedía el límite)."
            )
        else:
            filas_despues_costo_iqr = len(df_limpio)

    
    # =================================================================
    # C. VALIDACIÓN DE STOCK (Stock < 0: Lógica Especial)
    # =================================================================
    
    if "Stock_Actual" in df_limpio.columns:
        df_limpio["Stock_Actual"] = pd.to_numeric(df_limpio["Stock_Actual"], errors="coerce")
        
        # PASO 5A: ELIMINAR stock < 0 IRRECUPERABLE (+ Lead_Time NaN)
        filas_antes_irrecuperable = len(df_limpio)
        
        mask_stock_negativo = df_limpio["Stock_Actual"] < 0
        mask_lead_na = df_limpio["Lead_Time_Dias"].isna() if "Lead_Time_Dias" in df_limpio.columns else pd.Series([False] * len(df_limpio))
        
        mask_irrecuperable = mask_stock_negativo & mask_lead_na
        df_limpio = df_limpio[~mask_irrecuperable]
        filas_despues_irrecuperable = len(df_limpio)
        
        logger.log_step(
            step_name="ELIMINAR Stock < 0 IRRECUPERABLE (+ Lead_Time NaN)",
            rows_before=filas_antes_irrecuperable,
            rows_after=filas_despues_irrecuperable,
            reason="Stock negativo + Lead_Time faltante = datos incompletos sin contexto de resurtimiento. Imposible de imputar o justificar.",
            method="Máscara: (Stock < 0) AND (Lead_Time.isna()), filtrado con operador ~",
            details=f"{filas_antes_irrecuperable - filas_despues_irrecuperable} registros irrecuperables eliminados."
        )
        
        # PASO 5B: IMPUTAR stock < 0 RECUPERABLE (con Lead_Time válido)
        if "Lead_Time_Dias" in df_limpio.columns:
            mask_stock_negativo_actualizado = df_limpio["Stock_Actual"] < 0
            mask_lead_valido = df_limpio["Lead_Time_Dias"].notna()
            mask_recuperable = mask_stock_negativo_actualizado & mask_lead_valido
            
            filas_a_imputar = mask_recuperable.sum()
            
            if filas_a_imputar > 0:
                stock_positivo = df_limpio.loc[df_limpio["Stock_Actual"] >= 0, "Stock_Actual"]
                mediana_stock = stock_positivo.median()
                df_limpio.loc[mask_recuperable, "Stock_Actual"] = mediana_stock
                
                logger.log_step(
                    step_name="IMPUTAR Stock < 0 RECUPERABLE (con Lead_Time válido)",
                    rows_before=filas_a_imputar,
                    rows_after=0,
                    reason="Stock negativo + Lead_Time válido = contexto suficiente para imputación. Lead_Time indica falta transitoria (en proceso de resurtir).",
                    method=f"Reemplazo con mediana de Stock ≥ 0. Mediana = {mediana_stock}",
                    details=f"{filas_a_imputar} registros imputados. Justificación: Lead_Time válido permite reconstruir inventario transitorio."
                )
        
        # PASO 5C: ELIMINAR stock < 0 residual
        filas_antes_residual = len(df_limpio)
        mask_stock_negativo_final = df_limpio["Stock_Actual"] < 0
        df_limpio = df_limpio[~mask_stock_negativo_final]
        filas_despues_residual = len(df_limpio)
        
        if filas_antes_residual - filas_despues_residual > 0:
            logger.log_step(
                step_name="ELIMINAR Stock < 0 Residual (después de imputación)",
                rows_before=filas_antes_residual,
                rows_after=filas_despues_residual,
                reason="Stock aún negativo después de imputación. Indica conflicto no resolvible automáticamente.",
                method="Máscara booleana: (Stock < 0), filtrado con operador ~",
                details=f"{filas_antes_residual - filas_despues_residual} registros residuales eliminados. Último recurso."
            )

    filas_eliminadas = filas_originales - len(df_limpio)
    return df, df_limpio, int(filas_eliminadas), logger.to_dict()

def cargar_transacciones(file, df_inventario=None):
    """
    Carga y limpia datos de transacciones logísticas CON RASTREO DETALLADO.
    
    Retorna: (df_raw, df_clean, filas_eliminadas, cleaning_log)
    """
    df = pd.read_csv(file)
    filas_originales = len(df)
    df_limpio = df.copy()
    
    # Inicializar logger
    logger = CleaningLogger()
    
    # =================================================================
    # A. NORMALIZACIÓN DE FECHAS (Multi-formato)
    # =================================================================
    
    fecha_cols = [col for col in df_limpio.columns if "fecha" in col.lower()]
    for col in fecha_cols:
        if col in df_limpio.columns:
            filas_antes_fecha = len(df_limpio)
            df_limpio[col] = pd.to_datetime(
                df_limpio[col], 
                errors="coerce",
                infer_datetime_format=True
            )
            filas_despues_fecha = len(df_limpio)
            
            logger.log_step(
                step_name=f"Normalizar Formato de Fecha: {col}",
                rows_before=filas_antes_fecha,
                rows_after=filas_despues_fecha,
                reason=f"Columna {col} tiene múltiples formatos de fecha mezclados (DD/MM/YYYY, YYYY-MM-DD, etc). Requiere normalización.",
                method="pd.to_datetime(format='mixed', errors='coerce') - auto-detecta múltiples formatos",
                details=f"Procesadas {filas_antes_fecha} fechas. {df_limpio[col].isna().sum()} valores inválidos marcados como NaT."
            )
    
    # =================================================================
    # B. INTEGRIDAD REFERENCIAL: SKU Fantasma (No existe en inventario)
    # =================================================================
    
    sku_fantasma_count = 0
    if "SKU_ID" in df_limpio.columns:
        # PASO 2: Validar SKUs contra inventario
        if df_inventario is not None and "SKU_ID" in df_inventario.columns:
            skus_validos = set(df_inventario["SKU_ID"].dropna().unique())
            mask_sku_fantasma = ~df_limpio["SKU_ID"].isin(skus_validos)
            sku_fantasma_count = mask_sku_fantasma.sum()
            
            # Crear columna de trazabilidad (no eliminar aún)
            df_limpio["SKU_Fantasma"] = mask_sku_fantasma
            
            logger.log_step(
                step_name="Detectar SKU Fantasma (no existe en inventario)",
                rows_before=len(df_limpio),
                rows_after=len(df_limpio),
                reason="SKU en transacción no coincide con SKU en inventario oficial. Indica: ventas no documentadas, integridad comprometida (8.3% de casos).",
                method="Validación referencial: set(transacciones.SKU) ∩ set(inventario.SKU)",
                details=f"{sku_fantasma_count} transacciones con SKU fantasma detectadas. Se marca pero NO se elimina (información valiosa para auditoría)."
            )
        
        # PASO 3: Eliminar SKU nulo o vacío
        filas_antes_sku_na = len(df_limpio)
        mask_sku_na = df_limpio["SKU_ID"].isna() | (df_limpio["SKU_ID"].astype(str).str.strip() == "")
        df_limpio = df_limpio[~mask_sku_na]
        filas_despues_sku_na = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Transacciones con SKU Nulo/Vacío",
            rows_before=filas_antes_sku_na,
            rows_after=filas_despues_sku_na,
            reason="SKU es identificador único de producto. Valor faltante = transacción sin producto identificable. No procesable.",
            method="Máscara: (SKU.isna()) OR (SKU == ''), filtrado con operador ~",
            details=f"{filas_antes_sku_na - filas_despues_sku_na} transacciones sin SKU válido eliminadas."
        )
    
    # =================================================================
    # C. VALIDACIÓN DE TIEMPO DE ENTREGA (Outliers: 999 días, >120 días)
    # =================================================================
    
    if "Tiempo_Entrega_Real" in df_limpio.columns:
        df_limpio["Tiempo_Entrega_Real"] = pd.to_numeric(
            df_limpio["Tiempo_Entrega_Real"], 
            errors="coerce"
        )
        
        # PASO 4: Eliminar entregas > 999 días (claramente erróneo)
        filas_antes_extrema = len(df_limpio)
        mask_entrega_extrema = df_limpio["Tiempo_Entrega_Real"] > 999
        entrega_max = df_limpio.loc[mask_entrega_extrema, "Tiempo_Entrega_Real"].max() if mask_entrega_extrema.sum() > 0 else 0
        df_limpio = df_limpio[~mask_entrega_extrema]
        filas_despues_extrema = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Entregas > 999 días (outliers extremos)",
            rows_before=filas_antes_extrema,
            rows_after=filas_despues_extrema,
            reason="Tiempo de entrega > 999 días es implausible. Período observado: 0-999. Valores > 999 = error de dato (p.ej: fecha invertida).",
            method="Máscara booleana: (Tiempo_Entrega > 999), filtrado con operador ~",
            details=f"{filas_antes_extrema - filas_despues_extrema} entregas extremas eliminadas (max detectado: {entrega_max:.0f} días)."
        )
        
        # PASO 5: Eliminar entregas > 120 días CON SKU fantasma (combinación sospechosa)
        if "SKU_Fantasma" in df_limpio.columns:
            filas_antes_sospechosa = len(df_limpio)
            mask_sospechosa = (df_limpio["Tiempo_Entrega_Real"] > 120) & (df_limpio["SKU_Fantasma"] == True)
            df_limpio = df_limpio[~mask_sospechosa]
            filas_despues_sospechosa = len(df_limpio)
            
            logger.log_step(
                step_name="Eliminar Transacciones SOSPECHOSAS (Entrega >120 días + SKU Fantasma)",
                rows_before=filas_antes_sospechosa,
                rows_after=filas_despues_sospechosa,
                reason="Combinación (Entrega larga + SKU no existe) sugiere fraude/error sistemático. Eliminar juntas previene distorsión.",
                method="Máscara: (Tiempo_Entrega > 120) AND (SKU_Fantasma == True), filtrado con operador ~",
                details=f"{filas_antes_sospechosa - filas_despues_sospechosa} transacciones sospechosas eliminadas."
            )
    
    # =================================================================
    # D. VALIDACIÓN DE CANTIDAD Y COSTO (Anomalías)
    # =================================================================
    
    # PASO 6: Eliminar cantidad negativa con Costo_Envio faltante
    if "Cantidad_Vendida" in df_limpio.columns and "Costo_Envio" in df_limpio.columns:
        filas_antes_qty_costo = len(df_limpio)
        mask_qty_costo = (pd.to_numeric(df_limpio["Cantidad_Vendida"], errors="coerce") < 0) & (df_limpio["Costo_Envio"].isna())
        df_limpio = df_limpio[~mask_qty_costo]
        filas_despues_qty_costo = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Cantidad Negativa + Costo_Envio NaN",
            rows_before=filas_antes_qty_costo,
            rows_after=filas_despues_qty_costo,
            reason="Cantidad negativa (devolución/ajuste) sin costo de envío = información incompleta. Ambiguo si es venta o ajuste.",
            method="Máscara: (Cantidad < 0) AND (Costo_Envio.isna())",
            details=f"{filas_antes_qty_costo - filas_despues_qty_costo} transacciones ambiguas eliminadas."
        )
    
    # PASO 7: Eliminar cantidad negativa con entrega > 100 días (anómalo)
    if "Cantidad_Vendida" in df_limpio.columns and "Tiempo_Entrega_Real" in df_limpio.columns:
        filas_antes_qty_entrega = len(df_limpio)
        mask_qty_entrega = (pd.to_numeric(df_limpio["Cantidad_Vendida"], errors="coerce") < 0) & (df_limpio["Tiempo_Entrega_Real"] > 100)
        df_limpio = df_limpio[~mask_qty_entrega]
        filas_despues_qty_entrega = len(df_limpio)
        
        logger.log_step(
            step_name="Eliminar Cantidad Negativa + Entrega > 100 días (anómalo)",
            rows_before=filas_antes_qty_entrega,
            rows_after=filas_despues_qty_entrega,
            reason="Cantidad negativa (devolución) con entrega > 100 días es lógicamente inconsistente. Probable: error de registro.",
            method="Máscara: (Cantidad < 0) AND (Tiempo_Entrega > 100)",
            details=f"{filas_antes_qty_entrega - filas_despues_qty_entrega} transacciones inconsistentes eliminadas."
        )
    
    # PASO 8: Eliminar cantidad negativa residual
    if "Cantidad_Vendida" in df_limpio.columns:
        filas_antes_qty_neg = len(df_limpio)
        mask_qty_neg = pd.to_numeric(df_limpio["Cantidad_Vendida"], errors="coerce") < 0
        df_limpio = df_limpio[~mask_qty_neg]
        filas_despues_qty_neg = len(df_limpio)
        
        if filas_antes_qty_neg - filas_despues_qty_neg > 0:
            logger.log_step(
                step_name="Eliminar Cantidad Negativa Residual",
                rows_before=filas_antes_qty_neg,
                rows_after=filas_despues_qty_neg,
                reason="Cantidad negativa sin contexto = anomalía. Después de filtros específicos, eliminar residuales.",
                method="Máscara: (Cantidad < 0), filtrado con operador ~",
                details=f"{filas_antes_qty_neg - filas_despues_qty_neg} cantidades negativas residuales eliminadas."
            )
    
    # =================================================================
    # E. FILTRAR TRANSACCIONES CON FECHA FUTURA
    # =================================================================
    
    if "Fecha_Venta" in df_limpio.columns:
        filas_antes_futura = len(df_limpio)
        mask_futura = df_limpio["Fecha_Venta"] > pd.Timestamp.now()
        df_limpio = df_limpio[~mask_futura]
        filas_despues_futura = len(df_limpio)
        
        if filas_antes_futura - filas_despues_futura > 0:
            logger.log_step(
                step_name="Eliminar Transacciones con Fecha Futura",
                rows_before=filas_antes_futura,
                rows_after=filas_despues_futura,
                reason="Fecha_Venta > ahora = error de fecha. Probable: error de ingreso o dato corrupto.",
                method="Máscara: (Fecha_Venta > now())",
                details=f"{filas_antes_futura - filas_despues_futura} transacciones futuras eliminadas."
            )
    
    filas_eliminadas = filas_originales - len(df_limpio)
    return df, df_limpio, int(filas_eliminadas), logger.to_dict()



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
    
    # VALIDACIONES ESPECIALIZADAS PARA FEEDBACK
    hc["feedback_validation"] = {}
    if dataset_name == "Feedback de Clientes":
        # A. DUPLICADOS INTENCIONALES
        duplicates_issues = []
        
        # Duplicados completos
        duplicados_completos = df_raw.duplicated().sum()
        if duplicados_completos > 0:
            duplicates_issues.append(f"Duplicados completos: {duplicados_completos} ({(duplicados_completos/len(df_raw)*100):.1f}%)")
        
        # Duplicados parciales (Feedback_ID + Transaccion_ID)
        if "Feedback_ID" in df_raw.columns and "Transaccion_ID" in df_raw.columns:
            try:
                dup_parciales = df_raw.duplicated(subset=["Feedback_ID", "Transaccion_ID"], keep=False).sum()
                if dup_parciales > 0:
                    duplicates_issues.append(f"Duplicados parciales (ID + Transaccion): {dup_parciales} ({(dup_parciales/len(df_raw)*100):.1f}%)")
            except:
                pass
        
        hc["feedback_validation"]["duplicates_issues"] = duplicates_issues if duplicates_issues else ["✓ Sin duplicados detectados"]
        
        # B. EDADES IMPOSIBLES (Validación Lógica)
        age_issues = []
        if "Edad_Cliente" in df_raw.columns:
            try:
                edad = pd.to_numeric(df_raw["Edad_Cliente"], errors="coerce")
                
                # Edades negativas
                edad_negativa = (edad < 0).sum()
                if edad_negativa > 0:
                    age_issues.append(f"Edades negativas: {edad_negativa} ({(edad_negativa/len(df_raw)*100):.1f}%)")
                
                # Edades > 110 (ej: 195 años)
                edad_extrema = (edad > 110).sum()
                if edad_extrema > 0:
                    outliers = df_raw.loc[df_raw["Edad_Cliente"].astype(str).str.isnumeric(), "Edad_Cliente"].astype(float)
                    outliers = outliers[outliers > 110]
                    max_edad = outliers.max() if len(outliers) > 0 else 0
                    age_issues.append(f"Edades > 110: {edad_extrema} ({(edad_extrema/len(df_raw)*100):.1f}%) [máx: {max_edad:.0f}]")
                
                # Edades < 13 (menores)
                edad_menor = (edad < 13).sum()
                if edad_menor > 0:
                    age_issues.append(f"Edades < 13 años: {edad_menor} ({(edad_menor/len(df_raw)*100):.1f}%)")
                
                # Edades faltantes
                edad_na = edad.isna().sum()
                if edad_na > 0:
                    age_issues.append(f"Edades con NaN: {edad_na} ({(edad_na/len(df_raw)*100):.1f}%)")
                
                # Estadísticas de rango válido
                edad_valida = edad[(edad >= 13) & (edad <= 110)]
                if len(edad_valida) > 0:
                    age_issues.append(f"Rango válido: {edad_valida.min():.0f} - {edad_valida.max():.0f} años (promedio: {edad_valida.mean():.1f})")
            except Exception as e:
                age_issues.append(f"Error en análisis de edades: {str(e)}")
        
        hc["feedback_validation"]["age_issues"] = age_issues if age_issues else ["✓ Edades válidas"]
        
        # C. NORMALIZACIÓN DE NPS (Escala de Satisfacción)
        nps_issues = []
        if "Satisfaccion_NPS" in df_raw.columns:
            try:
                nps = pd.to_numeric(df_raw["Satisfaccion_NPS"], errors="coerce")
                
                # NPS faltantes
                nps_na = nps.isna().sum()
                if nps_na > 0:
                    nps_issues.append(f"NPS con NaN: {nps_na} ({(nps_na/len(df_raw)*100):.1f}%)")
                
                # Detectar escala
                nps_max = nps.max()
                nps_min = nps.min()
                
                # Si está en escala 0-100, requiere normalización
                if nps_max > 10 and nps_max <= 100:
                    nps_issues.append(f"NPS en escala 0-100: será normalizado a 0-10")
                
                # Si está en escala no estándar
                elif nps_max > 100:
                    nps_issues.append(f"NPS en escala no estándar [0, {nps_max:.0f}]: requiere normalización")
                
                # Valores fuera de rango (después de normalizar deberían estar en 0-10)
                nps_invalid = ((nps < 0) | (nps > 100)).sum()  # Checkeando antes de normalizar
                if nps_invalid > 0:
                    nps_issues.append(f"NPS fuera de rango esperado: {nps_invalid} ({(nps_invalid/len(df_raw)*100):.1f}%)")
                
                # Estadísticas después de detección de escala
                if len(nps.dropna()) > 0:
                    nps_issues.append(f"Rango observado: [{nps_min:.1f}, {nps_max:.1f}] (promedio: {nps.mean():.1f})")
            except Exception as e:
                nps_issues.append(f"Error en análisis de NPS: {str(e)}")
        
        hc["feedback_validation"]["nps_issues"] = nps_issues if nps_issues else ["✓ NPS válido y normalizado"]

    # VALIDACIONES ESPECIALIZADAS PARA TRANSACCIONES LOGÍSTICAS
    hc["transacciones_validation"] = {}
    if dataset_name == "Transacciones Logísticas":
        # A. INTEGRIDAD REFERENCIAL (SKU FANTASMA)
        referential_issues = []
        if "SKU_Fantasma" in df_raw.columns:
            sku_fantasma = (df_raw["SKU_Fantasma"] == True).sum()
            if sku_fantasma > 0:
                referential_issues.append(f"SKU fantasma (no en inventario): {sku_fantasma} ({(sku_fantasma/len(df_raw)*100):.1f}%)")
        
        if "SKU_ID" in df_raw.columns:
            sku_na = df_raw["SKU_ID"].isna().sum()
            if sku_na > 0:
                referential_issues.append(f"SKU con NaN: {sku_na} ({(sku_na/len(df_raw)*100):.1f}%)")
        
        hc["transacciones_validation"]["referential_issues"] = referential_issues if referential_issues else ["✓ Integridad referencial verificada"]
        
        # B. NORMALIZACIÓN DE FECHAS
        date_format_issues = []
        fecha_cols = [col for col in df_raw.columns if "fecha" in col.lower()]
        for col in fecha_cols:
            if col in df_raw.columns:
                # Contar NaT después de parsing
                nat_count = df_raw[col].isna().sum()
                if nat_count > 0:
                    date_format_issues.append(f"{col} con NaT después de parsing: {nat_count} ({(nat_count/len(df_raw)*100):.1f}%)")
        
        hc["transacciones_validation"]["date_format_issues"] = date_format_issues if date_format_issues else ["✓ Fechas normalizadas correctamente"]
        
        # C. OUTLIERS DE TIEMPO DE ENTREGA (999 días, extremos)
        delivery_issues = []
        if "Tiempo_Entrega_Real" in df_raw.columns:
            try:
                entrega = pd.to_numeric(df_raw["Tiempo_Entrega_Real"], errors="coerce")
                
                # Outliers > 999 días
                entrega_999 = (entrega > 999).sum()
                if entrega_999 > 0:
                    delivery_issues.append(f"Outliers extremos (>999 días): {entrega_999} ({(entrega_999/len(df_raw)*100):.1f}%)")
                
                # Cálculo de P95 para detectar sospechosos
                p95 = entrega.quantile(0.95)
                umbral = p95 * 1.2
                
                # Marcar outliers
                if "Entrega_Outlier" in df_raw.columns:
                    outlier_count = (df_raw["Entrega_Outlier"] == True).sum()
                    if outlier_count > 0:
                        delivery_issues.append(f"Outliers sospechosos (>P95 * 1.2): {outlier_count} ({(outlier_count/len(df_raw)*100):.1f}%) [umbral: {umbral:.0f} días]")
                
                # Entregas > 100 días
                entrega_100 = (entrega > 100).sum()
                if entrega_100 > 0:
                    delivery_issues.append(f"Entregas retrasadas (>100 días): {entrega_100} ({(entrega_100/len(df_raw)*100):.1f}%)")
                
                # Estadísticas
                entrega_valida = entrega[(entrega >= 0) & (entrega <= 999)]
                if len(entrega_valida) > 0:
                    delivery_issues.append(f"Rango válido: {entrega_valida.min():.0f} - {entrega_valida.max():.0f} días (P95: {p95:.0f})")
            except Exception as e:
                delivery_issues.append(f"Error en análisis de entregas: {str(e)}")
        
        hc["transacciones_validation"]["delivery_issues"] = delivery_issues if delivery_issues else ["✓ Entregas dentro de rango normal"]

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
    
    # Añadir sugerencias de feedback
    if dataset_name == "Feedback de Clientes":
        if hc["feedback_validation"].get("duplicates_issues") and any("Duplicados" in s for s in hc["feedback_validation"]["duplicates_issues"]):
            suggestions.append("⚠️ Duplicados intencionales detectados - revisar y eliminar")
        if hc["feedback_validation"].get("age_issues") and any("imposibles" in s.lower() or ">" in s or "<" in s for s in hc["feedback_validation"]["age_issues"]):
            suggestions.append("⚠️ Edades imposibles o faltantes detectadas")
        if hc["feedback_validation"].get("nps_issues") and any("NaN" in s or "no estándar" in s for s in hc["feedback_validation"]["nps_issues"]):
            suggestions.append("⚠️ NPS requiere normalización o tiene valores faltantes")
    
    # Añadir sugerencias de transacciones
    if dataset_name == "Transacciones Logísticas":
        if hc["transacciones_validation"].get("referential_issues") and any("fantasma" in s or "NaN" in s for s in hc["transacciones_validation"]["referential_issues"]):
            suggestions.append("⚠️ SKU fantasma detectado: transacciones sin respaldo en inventario")
        if hc["transacciones_validation"].get("date_format_issues") and any("NaT" in s for s in hc["transacciones_validation"]["date_format_issues"]):
            suggestions.append("⚠️ Errores en normalización de fechas: formatos inconsistentes detectados")
        if hc["transacciones_validation"].get("delivery_issues") and any("999" in s or "retrasadas" in s for s in hc["transacciones_validation"]["delivery_issues"]):
            suggestions.append("⚠️ Outliers de tiempo de entrega detectados (hasta 999 días o extremadamente retrasados)")

    
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
    
    # Penalización adicional para feedback con problemas críticos
    if dataset_name == "Feedback de Clientes":
        if hc["feedback_validation"].get("duplicates_issues"):
            for issue in hc["feedback_validation"]["duplicates_issues"]:
                if "Duplicados" in issue:
                    score -= 20  # Duplicados intencionales son graves
        
        if hc["feedback_validation"].get("age_issues"):
            for issue in hc["feedback_validation"]["age_issues"]:
                if "imposibles" in issue.lower() or (">" in issue and "110" in issue):
                    score -= 15  # Edades imposibles son graves
                elif "NaN" in issue:
                    score -= 10
        
        if hc["feedback_validation"].get("nps_issues"):
            for issue in hc["feedback_validation"]["nps_issues"]:
                if "NaN" in issue:
                    score -= 15  # NPS faltante es grave
    
    # Penalización adicional para transacciones con problemas críticos
    if dataset_name == "Transacciones Logísticas":
        if hc["transacciones_validation"].get("referential_issues"):
            for issue in hc["transacciones_validation"]["referential_issues"]:
                if "fantasma" in issue:
                    score -= 30  # SKU fantasma es crítico (impacto financiero alto)
                elif "NaN" in issue:
                    score -= 15
        
        if hc["transacciones_validation"].get("delivery_issues"):
            for issue in hc["transacciones_validation"]["delivery_issues"]:
                if "999" in issue:
                    score -= 20  # Outliers extremos son graves
                elif "retrasadas" in issue:
                    score -= 10
        
        if hc["transacciones_validation"].get("date_format_issues"):
            for issue in hc["transacciones_validation"]["date_format_issues"]:
                if "NaT" in issue:
                    score -= 15  # Errores de fecha son críticos en logística
    
    score = max(0, round(score, 2))
    hc["health_score"] = score

    return hc

FILES_CONFIG = {
    "Feedback de Clientes": (feedback_file, cargar_feedback, ["Edad_Cliente", "Rating_Producto", "Satisfaccion_NPS"]),
    "Inventario Central": (inventario_file, cargar_inventario, ["SKU_ID", "Categoria", "Stock_Actual", "Punto_Reorden"]),
}

datasets = {}
health_status = {}

# Cargar inventario primero (necesario para validar transacciones)
inventario_limpio = None
for name, (file, loader, required_cols) in FILES_CONFIG.items():
    if not file:
        health_status[name] = "missing"
        continue

    df_raw, df_clean, filas_eliminadas, cleaning_log = loader(file)
    health_clean = run_healthcheck(df_clean, required_cols, dataset_name=name)
    health_clean["filas_eliminadas"] = filas_eliminadas
    health_clean["cleaning_log"] = cleaning_log  # Agregar log de limpieza

    datasets[name] = {"raw": df_raw, "clean": df_clean, "health": health_clean}
    health_status[name] = health_clean["status"]
    
    # Guardar inventario limpio para validar transacciones
    if name == "Inventario Central":
        inventario_limpio = df_clean

# Cargar transacciones (con validación de integridad referencial contra inventario)
if transacciones_file:
    df_raw_trans, df_clean_trans, filas_eliminadas_trans, cleaning_log_trans = cargar_transacciones(transacciones_file, inventario_limpio)
    health_clean_trans = run_healthcheck(df_clean_trans, None, dataset_name="Transacciones Logísticas")
    health_clean_trans["filas_eliminadas"] = filas_eliminadas_trans
    health_clean_trans["cleaning_log"] = cleaning_log_trans  # Agregar log de limpieza
    
    datasets["Transacciones Logísticas"] = {"raw": df_raw_trans, "clean": df_clean_trans, "health": health_clean_trans}
    health_status["Transacciones Logísticas"] = health_clean_trans["status"]
else:
    health_status["Transacciones Logísticas"] = "missing"

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
        
        # 🔧 LOG DETALLADO DE LIMPIEZA - NUEVO
        if hc_clean.get("cleaning_log"):
            st.markdown("#### 🔧 Detalle Paso a Paso de Limpieza")
            cleaning_log = hc_clean["cleaning_log"]
            
            # Crear tabla de resumen de pasos
            if "pasos" in cleaning_log and cleaning_log["pasos"]:
                steps_data = []
                for paso in cleaning_log["pasos"]:
                    steps_data.append({
                        "Paso": paso.get("paso", 0),
                        "Nombre": paso.get("nombre", ""),
                        "Antes": paso.get("filas_antes", 0),
                        "Después": paso.get("filas_despues", 0),
                        "Eliminadas": paso.get("filas_eliminadas", 0),
                        "% Elim": f"{paso.get('pct_eliminado', 0):.1f}%"
                    })
                
                steps_df = pd.DataFrame(steps_data)
                st.dataframe(steps_df, use_container_width=True, hide_index=True)
                
                # Expandibles para cada paso con detalles
                st.markdown("##### 📋 Detalles de Cada Paso")
                for paso in cleaning_log["pasos"]:
                    paso_name = paso.get("nombre", "Paso desconocido")
                    paso_num = paso.get("paso", 0)
                    with st.expander(f"#{paso_num}: {paso_name}", expanded=False):
                        st.markdown(f"**Filas Antes:** {paso.get('filas_antes', 0)}")
                        st.markdown(f"**Filas Después:** {paso.get('filas_despues', 0)}")
                        st.markdown(f"**Eliminadas:** {paso.get('filas_eliminadas', 0)} ({paso.get('pct_eliminado', 0):.1f}%)")
                        
                        st.markdown("**Razón (¿Por qué?):**")
                        st.info(paso.get("razon", "Sin descripción"))
                        
                        st.markdown("**Método (¿Cómo?):**")
                        st.code(paso.get("metodo", "Sin método especificado"), language="python")
                        
                        st.markdown("**Detalles Técnicos:**")
                        st.markdown(paso.get("detalles", "Sin detalles adicionales"))
        
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
        
        # VALIDACIONES ESPECIALIZADAS DE FEEDBACK
        if name == "Feedback de Clientes" and hc_clean.get("feedback_validation"):
            with st.expander("🔍 Validaciones Especializadas de Feedback"):
                st.markdown("#### A. Duplicados Intencionales")
                for issue in hc_clean["feedback_validation"].get("duplicates_issues", []):
                    if "✓" in issue:
                        st.success(issue)
                    else:
                        st.error(issue)
                
                st.markdown("#### B. Edades Imposibles (< 0 o > 110 años)")
                for issue in hc_clean["feedback_validation"].get("age_issues", []):
                    if "✓" in issue or "Rango válido" in issue:
                        st.success(issue)
                    else:
                        st.error(issue)
                
                st.markdown("#### C. Normalización de NPS (Escala de Satisfacción)")
                for issue in hc_clean["feedback_validation"].get("nps_issues", []):
                    if "✓" in issue or "Rango observado" in issue or "normalizado" in issue:
                        st.success(issue)
                    else:
                        st.warning(issue)
        
        # VALIDACIONES ESPECIALIZADAS DE TRANSACCIONES LOGÍSTICAS
        if name == "Transacciones Logísticas" and hc_clean.get("transacciones_validation"):
            with st.expander("🔍 Validaciones Especializadas de Transacciones Logísticas"):
                st.markdown("#### A. Integridad Referencial (SKU Fantasma)")
                for issue in hc_clean["transacciones_validation"].get("referential_issues", []):
                    if "✓" in issue:
                        st.success(issue)
                    else:
                        st.error(issue)
                
                st.markdown("#### B. Normalización de Formatos de Fecha")
                for issue in hc_clean["transacciones_validation"].get("date_format_issues", []):
                    if "✓" in issue:
                        st.success(issue)
                    else:
                        st.error(issue)
                
                st.markdown("#### C. Outliers de Tiempo de Entrega (999 días, extremos)")
                for issue in hc_clean["transacciones_validation"].get("delivery_issues", []):
                    if "✓" in issue or "Rango válido" in issue:
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
st.metric(
    "Ingreso en riesgo (USD)",
    f"{negativos['Ingreso'].sum():,.0f}"
)
st.metric(
    "% Ingreso en riesgo",
    f"{(negativos['Ingreso'].sum()/merged['Ingreso'].sum())*100:.2f}%"
)

fig, ax = plt.subplots(figsize=(6,4))
margen_counts = merged["Margen_Utilidad"].apply(
    lambda x: "Negativo" if x < 0 else "Positivo"
).value_counts()

ax.bar(margen_counts.index, margen_counts.values, color=["red","green"])
ax.set_title("Distribución de Margen de Utilidad")
ax.set_ylabel("Cantidad de Transacciones")

st.pyplot(fig)

# ⬇️ DESCARGA DIRECTA DE LA GRÁFICA
buffer = io.BytesIO()
fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
buffer.seek(0)

st.download_button(
    label="📥 Descargar gráfica: Distribución de Margen",
    data=buffer,
    file_name="distribucion_margen_utilidad.png",
    mime="image/png"
)

st.dataframe(
    negativos[
        ["SKU_ID","Cantidad_Vendida","Ingreso","Costo_Total","Margen_Utilidad"]
    ]
)

# ---------- 2. Crisis Logística ----------
st.subheader("2️⃣ Crisis Logística y Cuellos de Botella")

log_merge = merged.merge(
    fb_sku[["Transaccion_ID","Satisfaccion_NPS"]],
    on="Transaccion_ID",
    how="left"
)

log_merge["Tiempo_Entrega_Real"] = log_merge["Tiempo_Entrega_Real"].fillna(0)
log_merge["Satisfaccion_NPS"] = log_merge["Satisfaccion_NPS"].fillna(0)

corr_ciudad = (
    log_merge
    .groupby("Ciudad_Destino")[["Tiempo_Entrega_Real","Satisfaccion_NPS"]]
    .corr()
    .iloc[0::2, -1]
    .reset_index()
    .rename(columns={"Satisfaccion_NPS": "Corr_Entrega_NPS"})
)

st.markdown("**Correlación Tiempo de Entrega vs NPS por Ciudad**")
st.dataframe(corr_ciudad.sort_values("Corr_Entrega_NPS"))

# ---------------------------
# GRÁFICA
# ---------------------------
fig, ax = plt.subplots(figsize=(8,4))
top_ciudades = corr_ciudad.sort_values("Corr_Entrega_NPS").head(10)

ax.barh(
    top_ciudades["Ciudad_Destino"],
    top_ciudades["Corr_Entrega_NPS"],
    color="orange"
)
ax.set_xlabel("Correlación")
ax.set_title("Top 10 Ciudades con mayor impacto en satisfacción")

st.pyplot(fig)

# ⬇️ DESCARGA DE LA GRÁFICA
buffer = io.BytesIO()
fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
buffer.seek(0)

st.download_button(
    label="📥 Descargar gráfica: Impacto logístico por ciudad",
    data=buffer,
    file_name="impacto_logistico_nps_por_ciudad.png",
    mime="image/png"
)

# ---------------------------
# (OPCIONAL) DESCARGA DE TABLA
# ---------------------------
csv_buffer = io.BytesIO()
corr_ciudad.to_csv(csv_buffer, index=False)
csv_buffer.seek(0)

st.download_button(
    label="📥 Descargar tabla de correlaciones (CSV)",
    data=csv_buffer,
    file_name="correlacion_entrega_nps_por_ciudad.csv",
    mime="text/csv"
)
# ---------- 3. Venta Invisible ----------
st.subheader("3️⃣ Análisis de la Venta Invisible")

ingreso_total = merged["Ingreso"].sum()
ingreso_fantasma = merged.loc[merged["sku_status"] == "FANTASMA", "Ingreso"].sum()

st.metric("Ingreso total (USD)", f"{ingreso_total:,.0f}")
st.metric("Ingreso en riesgo (USD)", f"{ingreso_fantasma:,.0f}")
st.metric(
    "% Ingreso en riesgo",
    f"{(ingreso_fantasma / ingreso_total) * 100:.2f}%"
    if ingreso_total > 0 else "0.00%"
)

# ---------------------------
# GRÁFICA
# ---------------------------
fig, ax = plt.subplots(figsize=(6,4))

ingresos_tipo = merged.groupby("sku_status")["Ingreso"].sum()

ax.bar(
    ingresos_tipo.index,
    ingresos_tipo.values,
    color=["red", "green"]
)
ax.set_ylabel("Ingreso (USD)")
ax.set_title("Impacto financiero por tipo de SKU")

st.pyplot(fig)

# ⬇️ DESCARGA DE LA GRÁFICA
buffer = io.BytesIO()
fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
buffer.seek(0)

st.download_button(
    label="📥 Descargar gráfica: Venta Invisible por SKU",
    data=buffer,
    file_name="venta_invisible_ingreso_por_sku.png",
    mime="image/png"
)

# ---------------------------
# (OPCIONAL) DESCARGA DE DATOS
# ---------------------------
csv_buffer = io.BytesIO()
ingresos_tipo.reset_index().to_csv(csv_buffer, index=False)
csv_buffer.seek(0)

st.download_button(
    label="📥 Descargar resumen financiero (CSV)",
    data=csv_buffer,
    file_name="resumen_ingreso_por_tipo_sku.csv",
    mime="text/csv"
)


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

# Filtro de riesgo: stock alto (p75) y NPS bajo (p25)
stock_p75 = df_fidelidad["Stock_Actual"].quantile(0.75)
nps_p25 = df_fidelidad["Satisfaccion_NPS"].quantile(0.25)

fidelidad_riesgo = df_fidelidad[
    (df_fidelidad["Stock_Actual"] > stock_p75) &
    (df_fidelidad["Satisfaccion_NPS"] < nps_p25)
].copy()

# Agrupar por categoría
categoria_summary = fidelidad_riesgo.groupby("Categoria").agg(
    Cantidad_SKU=("SKU_ID","count"),
    Stock_Total=("Stock_Actual","sum"),
    NPS_Promedio=("Satisfaccion_NPS","mean")
).reset_index()

categoria_summary = categoria_summary.sort_values(
    ["Cantidad_SKU","NPS_Promedio"],
    ascending=[False, True]
)

# ---------------------------
# Tabla categorías críticas + descarga
# ---------------------------
st.subheader("📋 Categorías Críticas")
st.dataframe(categoria_summary, use_container_width=True, hide_index=True)

csv_categoria = categoria_summary.to_csv(index=False)
st.download_button(
    label="📥 Descargar categorías críticas (CSV)",
    data=csv_categoria,
    file_name="categorias_criticas_stock_alto_nps_bajo.csv",
    mime="text/csv"
)

# ---------------------------
# Gráfico Stock vs NPS
# ---------------------------
st.subheader("📍 Matriz de Riesgo: Stock vs Satisfacción")

fig, ax = plt.subplots(figsize=(10,6))

# Todos los SKUs
ax.scatter(
    df_fidelidad["Stock_Actual"],
    df_fidelidad["Satisfaccion_NPS"],
    alpha=0.5,
    s=50,
    color="blue",
    label="Todos los SKUs"
)

# SKUs en riesgo
if not fidelidad_riesgo.empty:
    ax.scatter(
        fidelidad_riesgo["Stock_Actual"],
        fidelidad_riesgo["Satisfaccion_NPS"],
        s=100,
        color="red",
        label=f"En Riesgo ({len(fidelidad_riesgo)})",
        zorder=5
    )

# Líneas de referencia
ax.axhline(y=nps_p25, color="orange", linestyle="--", label=f"NPS Bajo ({nps_p25:.0f})")
ax.axvline(x=stock_p75, color="green", linestyle="--", label=f"Stock Alto ({stock_p75:.0f})")

ax.set_xlabel("Stock Actual")
ax.set_ylabel("Satisfacción NPS")
ax.set_title("Identificación de SKUs Problemáticos")
ax.legend()
ax.grid(True, alpha=0.3)

st.pyplot(fig)

# Descarga de la gráfica
buffer = io.BytesIO()
fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
buffer.seek(0)

st.download_button(
    label="📥 Descargar gráfica Stock vs NPS",
    data=buffer,
    file_name="matriz_riesgo_stock_vs_nps.png",
    mime="image/png"
)

# ---------------------------
# Análisis rápido
# ---------------------------
st.subheader("🎯 Análisis Rápido")

if not fidelidad_riesgo.empty:
    st.success(f"**Se encontraron {len(fidelidad_riesgo)} SKUs en riesgo**")
    st.write("**Categorías más afectadas:**")
    for _, row in categoria_summary.head(3).iterrows():
        st.write(
            f"- **{row['Categoria'].capitalize()}**: "
            f"{row['Cantidad_SKU']} SKUs, NPS: {row['NPS_Promedio']:.0f}"
        )
else:
    st.info("✅ No se encontraron SKUs con alto stock y baja satisfacción")

# ---------------------------
# Exportar SKUs en riesgo
# ---------------------------
if not fidelidad_riesgo.empty:
    csv_riesgo = fidelidad_riesgo[
        ["SKU_ID","Categoria","Stock_Actual","Satisfaccion_NPS"]
    ].to_csv(index=False)

    st.download_button(
        label="📥 Exportar SKUs en Riesgo",
        data=csv_riesgo,
        file_name="skus_riesgo_stock_alto_nps_bajo.csv",
        mime="text/csv"
    )

    st.info("Asegúrate de tener cargados Inventario Central y Feedback de Clientes.")

# ---------- 5 Relacion bodegas - satisfaccion ----------

inv = datasets["Inventario Central"]["clean"].copy()
trx = datasets["Transacciones Logísticas"]["clean"].copy()
fb = datasets["Feedback de Clientes"]["clean"].copy()

# ---------------------------
# Normalizar IDs
# ---------------------------
inv["SKU_ID"] = inv["SKU_ID"].astype(str).str.strip()
trx["SKU_ID"] = trx["SKU_ID"].astype(str).str.strip()
trx["Transaccion_ID"] = trx["Transaccion_ID"].astype(str).str.strip()
fb["Transaccion_ID"] = fb["Transaccion_ID"].astype(str).str.strip()

# ---------------------------
# Merge Inventario + Transacciones
# ---------------------------
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

# ---------------------------
# Cálculo Antigüedad de Revisión
# ---------------------------
trx_inv_fb["Ultima_Revision"] = pd.to_datetime(
    trx_inv_fb["Ultima_Revision"], errors="coerce"
)
trx_inv_fb["Antiguedad_Revision_Dias"] = (
    pd.Timestamp.today() - trx_inv_fb["Ultima_Revision"]
).dt.days

# Forzar columnas numéricas
for col in ["Antiguedad_Revision_Dias", "Ticket_Soporte_Abierto", "Satisfaccion_NPS"]:
    trx_inv_fb[col] = pd.to_numeric(trx_inv_fb[col], errors="coerce")

trx_inv_fb["Ticket_Soporte_Abierto"] = trx_inv_fb["Ticket_Soporte_Abierto"].fillna(0)
trx_inv_fb["Satisfaccion_NPS"] = trx_inv_fb["Satisfaccion_NPS"].fillna(0)

# ---------------------------
# Agregación por Bodega
# ---------------------------
bodega_summary = trx_inv_fb.groupby("Bodega_Origen").agg(
    Antiguedad_Revision_Prom=("Antiguedad_Revision_Dias","mean"),
    Tasa_Tickets=("Ticket_Soporte_Abierto","mean"),
    Satisfaccion_Prom=("Satisfaccion_NPS","mean"),
    Num_Transacciones=("Transaccion_ID","count")
).reset_index()

st.session_state["bodega_summary"] = bodega_summary

# ---------------------------
# Visualización Scatter
# ---------------------------
st.subheader("👁️ Riesgo Operativo por Bodega: Antigüedad de Revisión vs Tasa de Tickets")

fig, ax = plt.subplots(figsize=(10, 6))
sc = ax.scatter(
    bodega_summary["Antiguedad_Revision_Prom"],
    bodega_summary["Tasa_Tickets"],
    s=bodega_summary["Num_Transacciones"] * 5,
    c=bodega_summary["Satisfaccion_Prom"],
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

# ---------------------------
# Descarga de la gráfica
# ---------------------------
buffer = io.BytesIO()
fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
buffer.seek(0)

st.download_button(
    label="📥 Descargar gráfica Riesgo Operativo por Bodega",
    data=buffer,
    file_name="riesgo_operativo_por_bodega.png",
    mime="image/png"
)

# ---------------------------
# Tabla resumen + descarga
# ---------------------------
st.subheader("📋 Resumen por Bodega")

st.dataframe(
    bodega_summary.sort_values("Tasa_Tickets", ascending=False),
    use_container_width=True
)

csv_bodega = bodega_summary.sort_values(
    "Tasa_Tickets", ascending=False
).to_csv(index=False)

st.download_button(
    label="📥 Descargar resumen por bodega (CSV)",
    data=csv_bodega,
    file_name="resumen_riesgo_operativo_bodegas.csv",
    mime="text/csv"
)
