# app.py - Dashboard Streamlit para análisis de feedback, inventario y transacciones
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Análisis de Datos",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("📊 Dashboard de Análisis - Datos Empresariales")
st.markdown("---")

# Sidebar para carga de archivos
with st.sidebar:
    st.header("📤 Carga de Archivos CSV")
    
    st.markdown("### Sube tus archivos CSV:")
    
    # Cargar feedback de clientes
    st.markdown("#### 1. Feedback de Clientes")
    feedback_file = st.file_uploader(
        "Selecciona feedback_clientes_v2.csv",
        type=["csv"],
        key="feedback"
    )
    
    # Cargar inventario central
    st.markdown("#### 2. Inventario Central")
    inventario_file = st.file_uploader(
        "Selecciona inventario_central_v2.csv",
        type=["csv"],
        key="inventario"
    )
    
    # Cargar transacciones logísticas
    st.markdown("#### 3. Transacciones Logísticas")
    transacciones_file = st.file_uploader(
        "Selecciona transacciones_logisticas_v2.csv",
        type=["csv"],
        key="transacciones"
    )
    
    st.markdown("---")
    st.header("⚙️ Configuración")
    
    # Selector de dataset a mostrar
    dataset_option = st.selectbox(
        "Seleccionar dataset para análisis detallado:",
        ["Feedback de Clientes", "Inventario Central", "Transacciones Logísticas"]
    )
    
    # Filtros adicionales
    mostrar_limpieza = st.checkbox("Mostrar proceso de limpieza", value=True)
    
    st.markdown("---")
    st.caption("Versión 2.0 | Análisis de Datos")

# Función para cargar y limpiar datos de feedback
def cargar_feedback(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
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
    return None, None

# Función para cargar y limpiar datos de inventario
def cargar_inventario(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Limpieza: eliminar outlier en Costo_Unitario_USD (índice 500)
        if 500 in df.index:
            df_limpio = df.drop(index=500).reset_index(drop=True)
        else:
            df_limpio = df.copy()
        
        # Filtrar datos negativos en stock (si se desea)
        df_limpio = df_limpio[df_limpio['Stock_Actual'] >= 0]
        
        return df, df_limpio
    return None, None

# Función para cargar datos de transacciones
def cargar_transacciones(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Limpieza básica para transacciones
        # Convertir fechas si existen
        date_columns = [col for col in df.columns if 'Fecha' in col or 'fecha' in col.lower()]
        for col in date_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        
        return df, df.copy()  # Retornar mismo df para limpieza básica
    return None, None

# Inicializar variables
df_feedback_raw = df_feedback_clean = None
df_inventario_raw = df_inventario_clean = None
df_transacciones_raw = df_transacciones_clean = None

# Verificar si se cargaron los archivos
archivos_cargados = all([feedback_file, inventario_file, transacciones_file])

if not archivos_cargados:
    # Mostrar instrucciones si no están todos los archivos
    st.warning("⚠️ Por favor carga los 3 archivos CSV en la barra lateral:")
    st.info("""
    **Archivos requeridos:**
    1. **feedback_clientes_v2.csv** - Datos de satisfacción de clientes
    2. **inventario_central_v2.csv** - Datos de inventario y stock
    3. **transacciones_logisticas_v2.csv** - Datos de transacciones y logística
    
    Una vez cargados los 3 archivos, el dashboard se actualizará automáticamente.
    """)
    
    # Mostrar estado de carga
    st.subheader("📋 Estado de Carga")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Feedback Clientes", "✅ Cargado" if feedback_file else "❌ Pendiente")
    with col2:
        st.metric("Inventario Central", "✅ Cargado" if inventario_file else "❌ Pendiente")
    with col3:
        st.metric("Transacciones", "✅ Cargado" if transacciones_file else "❌ Pendiente")
    
    st.stop()

# Si todos los archivos están cargados, procesarlos
if archivos_cargados:
    try:
        # Cargar y procesar datos
        df_feedback_raw, df_feedback_clean = cargar_feedback(feedback_file)
        df_inventario_raw, df_inventario_clean = cargar_inventario(inventario_file)
        df_transacciones_raw, df_transacciones_clean = cargar_transacciones(transacciones_file)
        
        # Calcular métricas para feedback
        feedback_metrics = {
            'filas_originales': len(df_feedback_raw),
            'filas_limpias': len(df_feedback_clean),
            'edad_promedio': df_feedback_clean['Edad_Cliente'].mean(),
            'rating_producto_prom': df_feedback_clean['Rating_Producto'].mean(),
            'rating_logistica_prom': df_feedback_clean['Rating_Logistica'].mean(),
            'satisfaccion_prom': df_feedback_clean['Satisfaccion_NPS'].mean(),
        }
        
        # Calcular métricas para inventario
        inventario_metrics = {
            'filas_originales': len(df_inventario_raw),
            'filas_limpias': len(df_inventario_clean),
            'categorias_unicas': df_inventario_clean['Categoria'].nunique(),
            'stock_total': df_inventario_clean['Stock_Actual'].sum(),
            'costo_promedio': df_inventario_clean['Costo_Unitario_USD'].mean(),
            'productos_criticos': len(df_inventario_clean[df_inventario_clean['Stock_Actual'] < df_inventario_clean['Punto_Reorden']]),
        }
        
        # Calcular métricas para transacciones
        transacciones_metrics = {
            'filas_originales': len(df_transacciones_raw),
            'filas_limpias': len(df_transacciones_clean),
            'columnas': len(df_transacciones_clean.columns),
        }
        
        # Mostrar información general
        st.success(f"✅ Todos los archivos cargados correctamente")
        
        # Mostrar métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Feedback Clientes", f"{feedback_metrics['filas_limpias']:,}", 
                      f"Rating: {feedback_metrics['rating_producto_prom']:.1f}/5")
        with col2:
            st.metric("📦 Inventario", f"{inventario_metrics['filas_limpias']:,}",
                      f"{inventario_metrics['categorias_unicas']} categorías")
        with col3:
            st.metric("🚚 Transacciones", f"{transacciones_metrics['filas_limpias']:,}",
                      f"{transacciones_metrics['columnas']} columnas")
        with col4:
            st.metric("💰 Valor Stock", f"${inventario_metrics['stock_total']:,.0f}",
                      f"{inventario_metrics['productos_criticos']} productos críticos")
        
        st.markdown("---")
        
        # Mostrar proceso de limpieza si está seleccionado
        if mostrar_limpieza:
            with st.expander("🔍 Ver Proceso de Limpieza de Datos", expanded=False):
                tab1, tab2, tab3 = st.tabs(["Feedback Clientes", "Inventario Central", "Transacciones Logísticas"])
                
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
                        st.success(f"✅ Datos limpiados: {feedback_metrics['filas_originales'] - feedback_metrics['filas_limpias']} registros eliminados")
                
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
                        st.success(f"✅ Outlier eliminado: 1 registro")
                
                with tab3:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Dataset Original")
                        st.dataframe(df_transacciones_raw.head(), use_container_width=True)
                        st.write(f"**Filas:** {transacciones_metrics['filas_originales']}")
                        st.write(f"**Columnas:** {transacciones_metrics['columnas']}")
                    
                    with col2:
                        st.subheader("Dataset Limpio")
                        st.dataframe(df_transacciones_clean.head(), use_container_width=True)
                        st.write(f"**Filas:** {transacciones_metrics['filas_limpias']}")
                        st.write(f"**Columnas:** {transacciones_metrics['columnas']}")
                        st.success("✅ Limpieza básica aplicada")
        
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
        
        elif dataset_option == "Inventario Central":
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
        
        else:  # Transacciones Logísticas
            # Pestañas para análisis de transacciones
            tab1, tab2, tab3 = st.tabs(["📋 Vista General", "📊 Análisis Temporal", "🔍 Detalles por Tipo"])
            
            with tab1:
                st.subheader("Resumen del Dataset de Transacciones")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transacciones", f"{len(df_transacciones_clean):,}")
                with col2:
                    st.metric("Total Columnas", f"{len(df_transacciones_clean.columns)}")
                with col3:
                    st.metric("Tipos de Datos", f"{df_transacciones_clean.dtypes.nunique()}")
                
                # Mostrar primeras filas
                st.subheader("Primeras 10 Transacciones")
                st.dataframe(df_transacciones_clean.head(10), use_container_width=True)
                
                # Mostrar información de columnas
                with st.expander("📋 Información de Columnas"):
                    st.write("**Lista de Columnas:**")
                    for i, col in enumerate(df_transacciones_clean.columns, 1):
                        st.write(f"{i}. {col} - {df_transacciones_clean[col].dtype}")
            
            with tab2:
                st.subheader("Análisis Temporal")
                
                # Buscar columnas de fecha
                date_cols = [col for col in df_transacciones_clean.columns 
                           if 'fecha' in col.lower() or 'date' in col.lower() or 'Fecha' in col]
                
                if date_cols:
                    fecha_col = st.selectbox("Seleccionar columna de fecha:", date_cols)
                    
                    if fecha_col:
                        # Convertir a datetime si no lo está
                        if not pd.api.types.is_datetime64_any_dtype(df_transacciones_clean[fecha_col]):
                            df_transacciones_clean[fecha_col] = pd.to_datetime(df_transacciones_clean[fecha_col], errors='coerce')
                        
                        # Extraer año y mes
                        df_transacciones_clean['Año'] = df_transacciones_clean[fecha_col].dt.year
                        df_transacciones_clean['Mes'] = df_transacciones_clean[fecha_col].dt.month
                        
                        # Gráfico de transacciones por año
                        fig, ax = plt.subplots(figsize=(12, 6))
                        df_transacciones_clean['Año'].value_counts().sort_index().plot(kind='bar', ax=ax, edgecolor='black')
                        ax.set_xlabel('Año')
                        ax.set_ylabel('Número de Transacciones')
                        ax.set_title('Transacciones por Año')
                        plt.xticks(rotation=45)
                        st.pyplot(fig)
                else:
                    st.info("No se encontraron columnas de fecha en el dataset de transacciones.")
            
            with tab3:
                st.subheader("Análisis por Tipo de Transacción")
                
                # Buscar columnas que puedan ser categóricas
                categorical_cols = [col for col in df_transacciones_clean.columns 
                                  if df_transacciones_clean[col].dtype == 'object' or 
                                  df_transacciones_clean[col].nunique() < 20]
                
                if categorical_cols:
                    col_seleccionada = st.selectbox("Seleccionar columna para análisis:", categorical_cols)
                    
                    if col_seleccionada:
                        # Mostrar distribución
                        fig, ax = plt.subplots(figsize=(12, 6))
                        df_transacciones_clean[col_seleccionada].value_counts().head(15).plot(kind='bar', ax=ax, edgecolor='black')
                        ax.set_xlabel(col_seleccionada)
                        ax.set_ylabel('Cantidad')
                        ax.set_title(f'Distribución de {col_seleccionada}')
                        plt.xticks(rotation=45)
                        st.pyplot(fig)
                        
                        # Mostrar tabla de frecuencias
                        st.subheader(f"Frecuencia por {col_seleccionada}")
                        frecuencias = df_transacciones_clean[col_seleccionada].value_counts().reset_index()
                        frecuencias.columns = [col_seleccionada, 'Cantidad']
                        frecuencias['Porcentaje'] = (frecuencias['Cantidad'] / len(df_transacciones_clean) * 100).round(2)
                        st.dataframe(frecuencias, use_container_width=True)
                else:
                    st.info("No se encontraron columnas categóricas adecuadas para análisis.")
        
        # Sección de descarga de datos procesados
        st.markdown("---")
        st.subheader("📥 Exportar Datos Procesados")
        
        col1, col2, col3 = st.columns(3)
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
        
        with col3:
            if st.button("📤 Descargar Transacciones Procesado"):
                csv = df_transacciones_clean.to_csv(index=False)
                st.download_button(
                    label="Descargar CSV",
                    data=csv,
                    file_name=f"transacciones_procesado_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        # Footer
        st.markdown("---")
        st.caption("Dashboard creado para análisis de datos | Carga de archivos habilitada")
        
    except Exception as e:
        st.error(f"❌ Error al procesar los archivos: {str(e)}")
        st.info("""
        **Solución de problemas:**
        1. Verifica que los archivos CSV tengan el formato correcto
        2. Asegúrate de que los archivos tengan las columnas esperadas
        3. Verifica que no haya caracteres especiales problemáticos
        """)