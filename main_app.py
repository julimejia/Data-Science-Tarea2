import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="TechLogistics DSS - Health Score", layout="wide")

# Sidebar para carga de archivos
st.sidebar.header("📁 Carga de Datasets")
inventario_file = st.sidebar.file_uploader("Inventario Central", type="csv")
logistica_file = st.sidebar.file_uploader("Transacciones Logística", type="csv")
feedback_file = st.sidebar.file_uploader("Feedback Clientes", type="csv")

# Función para calcular métricas de calidad
def calculate_health_metrics(df, dataset_name):
    metrics = {}
    
    # 1. Nulidad
    null_percentage = (df.isnull().sum() / len(df)) * 100
    metrics['null_percentage'] = null_percentage
    
    # 2. Duplicados
    duplicate_count = df.duplicated().sum()
    metrics['duplicate_count'] = duplicate_count
    
    # 3. Outliers (solo columnas numéricas)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outlier_info = {}
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        outlier_info[col] = {
            'count': len(outliers),
            'percentage': (len(outliers) / len(df)) * 100
        }
    metrics['outliers'] = outlier_info
    
    # 4. Tipos de datos incorrectos (ej: fechas como string)
    # Aquí puedes agregar lógica personalizada según cada dataset
    
    return metrics

# Función para mostrar el Health Score
def display_health_score(metrics, dataset_name, stage):
    st.subheader(f"{dataset_name} - {stage}")
    
    # Métricas en columnas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Nulidad promedio", f"{metrics['null_percentage'].mean():.2f}%")
    
    with col2:
        st.metric("Duplicados", metrics['duplicate_count'])
    
    with col3:
        total_outliers = sum([v['count'] for v in metrics['outliers'].values()])
        st.metric("Outliers totales", total_outliers)
    
    # Detalles expandibles
    with st.expander("📋 Ver detalles por columna"):
        st.write("**Nulidad por columna:**")
        st.write(metrics['null_percentage'])
        
        st.write("**Outliers por columna numérica:**")
        for col, info in metrics['outliers'].items():
            st.write(f"- {col}: {info['count']} ({info['percentage']:.2f}%)")

# Procesar y mostrar
st.title("📈 Health Score de los Datasets - TechLogistics")

if inventario_file:
    df_inv = pd.read_csv(inventario_file)
    st.header("📦 Inventario Central")
    
    tab1, tab2 = st.tabs(["Antes de limpieza", "Después de limpieza"])
    
    with tab1:
        metrics_before = calculate_health_metrics(df_inv, "Inventario")
        display_health_score(metrics_before, "Inventario", "ANTES")
    
    with tab2:
        # Aquí iría la lógica de limpieza
        st.info("La limpieza se realizará en la siguiente fase.")

# Repetir para los otros datasets...
