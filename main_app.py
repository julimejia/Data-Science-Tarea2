# app.py - Dashboard Streamlit para análisis de feedback e inventario
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Análisis de Datos",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("📊 Dashboard de Análisis - Feedback e Inventario")
st.markdown("---")

# Sidebar para configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Selector de dataset a mostrar
    dataset_option = st.selectbox(
        "Seleccionar dataset para análisis detallado:",
        ["Feedback de Clientes", "Inventario Central"]
    )
    
    # Filtros adicionales (opcional)
    mostrar_limpieza = st.checkbox("Mostrar proceso de limpieza", value=True)
    
    st.markdown("---")
    st.caption("Versión 1.0 | Análisis de Datos")

# Función para cargar y limpiar datos de feedback
@st.cache_data
def cargar_feedback():
    df = pd.read_csv('feedback_clientes_v2.csv')
    
    # Limpieza: filtrar edades entre 0 y 110 años
    df_limpio = df[
        (df["Edad_Cliente"] >= 0) & 
        (df["Edad_Cliente"] <= 110)
    ].copy()
    
    # Convertir columnas categóricas si es necesario
    for col in ['Recomienda_Marca', 'Ticket_Soporte_Abierto']:
        if col in df_limpio.columns:
            df_limpio[col] = df_limpio[col].astype('category')
    
    return df, df_limpio

# Función para cargar y limpiar datos de inventario
@st.cache_data
def cargar_inventario():
    df = pd.read_csv('inventario_central_v2.csv')
    
    # Limpieza: eliminar outlier en Costo_Unitario_USD (índice 500)
    if 500 in df.index:
        df_limpio = df.drop(index=500).reset_index(drop=True)
    else:
        df_limpio = df.copy()
    
    # Filtrar datos negativos en stock (si se desea)
    df_limpio = df_limpio[df_limpio['Stock_Actual'] >= 0]
    
    return df, df_limpio

# Cargar los datos
try:
    df_feedback_raw, df_feedback_clean = cargar_feedback()
    df_inventario_raw, df_inventario_clean = cargar_inventario()
    
    # Calcular métricas
    feedback_metrics = {
        'filas_originales': len(df_feedback_raw),
        'filas_limpias': len(df_feedback_clean),
        'edad_promedio': df_feedback_clean['Edad_Cliente'].mean(),
        'rating_producto_prom': df_feedback_clean['Rating_Producto'].mean(),
        'rating_logistica_prom': df_feedback_clean['Rating_Logistica'].mean(),
    }
    
    inventario_metrics = {
        'filas_originales': len(df_inventario_raw),
        'filas_limpias': len(df_inventario_clean),
        'categorias_unicas': df_inventario_clean['Categoria'].nunique(),
        'stock_total': df_inventario_clean['Stock_Actual'].sum(),
        'costo_promedio': df_inventario_clean['Costo_Unitario_USD'].mean(),
    }
    
except FileNotFoundError as e:
    st.error(f"Error al cargar archivos: {e}")
    st.stop()

# Mostrar información general
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📋 Feedback Clientes", f"{feedback_metrics['filas_limpias']:,}", 
              f"{feedback_metrics['filas_originales'] - feedback_metrics['filas_limpias']} filas limpiadas")
with col2:
    st.metric("📦 Inventario Central", f"{inventario_metrics['filas_limpias']:,}",
              f"{inventario_metrics['categorias_unicas']} categorías")
with col3:
    st.metric("💰 Valor Stock", f"${inventario_metrics['stock_total']:,.0f}",
              f"Costo promedio: ${inventario_metrics['costo_promedio']:,.2f}")

st.markdown("---")

# Mostrar proceso de limpieza si está seleccionado
if mostrar_limpieza:
    with st.expander("🔍 Ver Proceso de Limpieza de Datos", expanded=False):
        tab1, tab2 = st.tabs(["Feedback Clientes", "Inventario Central"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Antes de limpieza")
                st.dataframe(df_feedback_raw.describe(), use_container_width=True)
                
                # Mostrar edades problemáticas
                edades_extremas = df_feedback_raw[
                    (df_feedback_raw['Edad_Cliente'] < 0) | 
                    (df_feedback_raw['Edad_Cliente'] > 110)
                ]
                if len(edades_extremas) > 0:
                    st.warning(f"Se encontraron {len(edades_extremas)} registros con edades fuera del rango [0-110]")
            
            with col2:
                st.subheader("Después de limpieza")
                st.dataframe(df_feedback_clean.describe(), use_container_width=True)
                st.success(f"✅ Datos limpiados: {len(df_feedback_raw) - len(df_feedback_clean)} registros eliminados")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Antes de limpieza")
                st.dataframe(df_inventario_raw.describe(), use_container_width=True)
                
                # Mostrar outlier de costo
                outliers = df_inventario_raw[df_inventario_raw['Costo_Unitario_USD'] > 85000]
                if len(outliers) > 0:
                    st.warning(f"Se encontró outlier: costo de ${outliers['Costo_Unitario_USD'].iloc[0]:,.2f}")
            
            with col2:
                st.subheader("Después de limpieza")
                st.dataframe(df_inventario_clean.describe(), use_container_width=True)
                st.success("✅ Outlier eliminado del dataset")

# Análisis detallado según selección
st.markdown("## 📈 Análisis Detallado")

if dataset_option == "Feedback de Clientes":
    # Pestañas para diferentes análisis
    tab1, tab2, tab3 = st.tabs(["📊 Resumen Estadístico", "📈 Distribuciones", "👥 Perfil de Clientes"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estadísticas Descriptivas")
            st.dataframe(df_feedback_clean.describe(), use_container_width=True)
        
        with col2:
            st.subheader("Información del Dataset")
            buffer = st.container()
            with buffer:
                st.write(f"**Filas:** {len(df_feedback_clean)}")
                st.write(f"**Columnas:** {len(df_feedback_clean.columns)}")
                st.write("**Tipos de datos:**")
                for dtype, count in df_feedback_clean.dtypes.value_counts().items():
                    st.write(f"  - {dtype}: {count}")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribución de Edades")
            fig, ax = plt.subplots(figsize=(10, 6))
            df_feedback_clean['Edad_Cliente'].hist(bins=30, ax=ax, edgecolor='black')
            ax.set_xlabel('Edad')
            ax.set_ylabel('Frecuencia')
            ax.set_title('Distribución de Edades de Clientes')
            st.pyplot(fig)
        
        with col2:
            st.subheader("Rating de Producto")
            fig, ax = plt.subplots(figsize=(10, 6))
            df_feedback_clean['Rating_Producto'].value_counts().sort_index().plot(kind='bar', ax=ax, edgecolor='black')
            ax.set_xlabel('Rating (1-5)')
            ax.set_ylabel('Cantidad')
            ax.set_title('Distribución de Ratings de Producto')
            plt.xticks(rotation=0)
            st.pyplot(fig)
    
    with tab3:
        st.subheader("Satisfacción por Edad")
        
        # Crear grupos de edad
        df_feedback_clean['Grupo_Edad'] = pd.cut(
            df_feedback_clean['Edad_Cliente'],
            bins=[18, 30, 40, 50, 60, 70, 85],
            labels=['18-29', '30-39', '40-49', '50-59', '60-69', '70+']
        )
        
        fig, ax = plt.subplots(figsize=(12, 6))
        df_grouped = df_feedback_clean.groupby('Grupo_Edad')['Satisfaccion_NPS'].mean()
        df_grouped.plot(kind='bar', ax=ax, color='skyblue', edgecolor='black')
        ax.set_xlabel('Grupo de Edad')
        ax.set_ylabel('Satisfacción NPS Promedio')
        ax.set_title('Satisfacción NPS por Grupo de Edad')
        plt.xticks(rotation=45)
        st.pyplot(fig)

else:  # Inventario Central
    # Pestañas para análisis de inventario
    tab1, tab2, tab3 = st.tabs(["📦 Resumen General", "📊 Análisis por Categoría", "🚨 Alertas de Stock"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estadísticas del Inventario")
            st.dataframe(df_inventario_clean.describe(), use_container_width=True)
        
        with col2:
            st.subheader("Distribución por Categoría")
            categoria_counts = df_inventario_clean['Categoria'].value_counts()
            fig, ax = plt.subplots(figsize=(10, 6))
            categoria_counts.plot(kind='pie', autopct='%1.1f%%', ax=ax)
            ax.set_ylabel('')
            ax.set_title('Distribución de Productos por Categoría')
            st.pyplot(fig)
    
    with tab2:
        st.subheader("Análisis por Categoría")
        
        # Selector de categoría
        categorias = df_inventario_clean['Categoria'].unique()
        categoria_seleccionada = st.selectbox("Seleccionar categoría:", categorias)
        
        if categoria_seleccionada:
            df_categoria = df_inventario_clean[df_inventario_clean['Categoria'] == categoria_seleccionada]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(f"Productos en {categoria_seleccionada}", len(df_categoria))
                st.metric("Stock Total", df_categoria['Stock_Actual'].sum())
            
            with col2:
                st.metric("Costo Promedio", f"${df_categoria['Costo_Unitario_USD'].mean():,.2f}")
                st.metric("Punto Reorden Promedio", f"{df_categoria['Punto_Reorden'].mean():.0f}")
            
            # Mostrar top productos
            st.subheader(f"Top 10 Productos - {categoria_seleccionada}")
            df_top = df_categoria.nlargest(10, 'Costo_Unitario_USD')[['SKU_ID', 'Costo_Unitario_USD', 'Stock_Actual']]
            st.dataframe(df_top, use_container_width=True)
    
    with tab3:
        st.subheader("🚨 Productos que Necesitan Reabastecimiento")
        
        # Identificar productos con stock bajo
        df_inventario_clean['Stock_Bajo'] = df_inventario_clean['Stock_Actual'] < df_inventario_clean['Punto_Reorden']
        productos_bajo_stock = df_inventario_clean[df_inventario_clean['Stock_Bajo']]
        
        if len(productos_bajo_stock) > 0:
            st.warning(f"⚠️ Se encontraron {len(productos_bajo_stock)} productos con stock bajo")
            
            # Mostrar tabla de productos críticos
            st.dataframe(
                productos_bajo_stock[['SKU_ID', 'Categoria', 'Stock_Actual', 'Punto_Reorden', 'Costo_Unitario_USD']]
                .sort_values('Stock_Actual'),
                use_container_width=True
            )
            
            # Gráfico de productos críticos por categoría
            fig, ax = plt.subplots(figsize=(12, 6))
            productos_bajo_stock['Categoria'].value_counts().plot(kind='bar', ax=ax, color='red', edgecolor='black')
            ax.set_xlabel('Categoría')
            ax.set_ylabel('Cantidad de Productos')
            ax.set_title('Productos con Stock Bajo por Categoría')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        else:
            st.success("✅ Todos los productos tienen stock suficiente")

# Sección de descarga de datos procesados
st.markdown("---")
st.subheader("📥 Exportar Datos Procesados")

col1, col2 = st.columns(2)
with col1:
    if st.button("📤 Descargar Feedback Procesado"):
        csv = df_feedback_clean.to_csv(index=False)
        st.download_button(
            label="Descargar CSV",
            data=csv,
            file_name=f"feedback_procesado_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with col2:
    if st.button("📤 Descargar Inventario Procesado"):
        csv = df_inventario_clean.to_csv(index=False)
        st.download_button(
            label="Descargar CSV",
            data=csv,
            file_name=f"inventario_procesado_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# Footer
st.markdown("---")
st.caption("Dashboard creado para análisis de datos | Procesamiento realizado según limpiezas del notebook original")