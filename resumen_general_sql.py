import sqlite3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Conexión a la base de datos SQLite
conn = sqlite3.connect("datos_actividades.db")
cursor = conn.cursor()

# --- Función para cargar los datos desde la base de datos --- 
def cargar_datos_sqlite():
    try:
        query = """
        SELECT * FROM actividades
        """
        df = pd.read_sql(query, conn)
        if df.empty:
            st.warning("No se encontraron datos en la base de datos.")
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos de la base de datos: {e}")
        return None

# --- Función para calcular y mostrar el gráfico de Mantención --- 
def mostrar_grafico_mantencion():
    """
    Calcula y muestra un gráfico de barras verticales agrupadas para el resumen de Mantención.
    """
    # Cargar los datos desde SQLite
    df = cargar_datos_sqlite()
    if df is None or df.empty:
        st.info("No hay datos para mostrar el gráfico de Mantención.")
        return

    if not all(col in df.columns for col in ['Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad']):
        st.error("Error: No se encontraron las columnas necesarias en el DataFrame.")
        return

    df['Fecha Agendamiento'] = pd.to_datetime(df['Fecha Agendamiento'])
    df['Año'] = df['Fecha Agendamiento'].dt.year.astype(str)
    df['Estado de actividad'] = df['Estado de actividad'].str.lower()

    df_mantencion = df[(df['Tipo de actividad'].str.lower().str.contains('reparación'))].copy()

    if df_mantencion.empty:
        st.info("No hay datos de Mantención para mostrar el gráfico.")
        return

    resumen_mantencion = df_mantencion.groupby(['Año', 'Estado de actividad'])['ID externo'].nunique().reset_index(name='Cantidad')
    pivot_mantencion = resumen_mantencion.pivot_table(index='Año', columns='Estado de actividad', values='Cantidad', fill_value=0).reset_index()
    pivot_mantencion = pivot_mantencion.rename(columns={'finalizada': 'Finalizadas', 'no realizado': 'No Realizadas'})

    pivot_mantencion['Asignadas'] = pivot_mantencion['Finalizadas'] + pivot_mantencion['No Realizadas']

    anios = sorted(pivot_mantencion['Año'].unique())

    fig = go.Figure(data=[
        go.Bar(name='Finalizadas', x=[str(año) for año in anios], y=[pivot_mantencion[pivot_mantencion['Año'] == año]['Finalizadas'].values[0] if año in pivot_mantencion['Año'].values else 0 for año in anios], marker_color='steelblue'),
        go.Bar(name='Asignadas', x=[str(año) for año in anios], y=[pivot_mantencion[pivot_mantencion['Año'] == año]['Asignadas'].values[0] if año in pivot_mantencion['Año'].values else 0 for año in anios], marker_color='coral')
    ])

    fig.update_layout(
        barmode='group',
        title=dict(
            text='Resumen Mantención últimos 3 años',
            x=0.3,  # Centra el título horizontalmente
            font=dict(size=20)
        ),
        xaxis_title="Año",
        yaxis_title="Número de Actividades",
        legend_title="Estado"
    )

    st.plotly_chart(fig)

# --- Función para calcular y mostrar el gráfico de Provisión --- 
def mostrar_grafico_provision():
    """
    Calcula y muestra un gráfico de barras verticales agrupadas para el resumen de Provisión.
    """
    # Cargar los datos desde SQLite
    df = cargar_datos_sqlite()
    if df is None or df.empty:
        st.info("No hay datos para mostrar el gráfico de Provisión.")
        return

    if not all(col in df.columns for col in ['Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad']):
        st.error("Error: No se encontraron las columnas necesarias en el DataFrame.")
        return

    df['Fecha Agendamiento'] = pd.to_datetime(df['Fecha Agendamiento'])
    df['Año'] = df['Fecha Agendamiento'].dt.year.astype(str)
    df['Estado de actividad'] = df['Estado de actividad'].str.lower()

    df_provision = df[(df['Tipo de actividad'].str.lower().str.contains('instalación') | df['Tipo de actividad'].str.lower().str.contains('postventa'))].copy()

    if df_provision.empty:
        st.info("No hay datos de Provisión para mostrar el gráfico.")
        return

    resumen_provision = df_provision.groupby(['Año', 'Estado de actividad'])['ID externo'].nunique().reset_index(name='Cantidad')
    pivot_provision = resumen_provision.pivot_table(index='Año', columns='Estado de actividad', values='Cantidad', fill_value=0).reset_index()
    pivot_provision = pivot_provision.rename(columns={'finalizada': 'Finalizadas', 'no realizado': 'No Realizadas'})

    pivot_provision['Asignadas'] = pivot_provision['Finalizadas'] + pivot_provision['No Realizadas']

    anios = sorted(pivot_provision['Año'].unique())

    fig = go.Figure(data=[
        go.Bar(name='Finalizadas', x=[str(año) for año in anios], y=[pivot_provision[pivot_provision['Año'] == año]['Finalizadas'].values[0] if año in pivot_provision['Año'].values else 0 for año in anios], marker_color='steelblue'),
        go.Bar(name='Asignadas', x=[str(año) for año in anios], y=[pivot_provision[pivot_provision['Año'] == año]['Asignadas'].values[0] if año in pivot_provision['Año'].values else 0 for año in anios], marker_color='coral')
    ])

    fig.update_layout(
        barmode='group',
        title=dict(
            text='Resumen Provisión últimos 3 años',
            x=0.3,  # Centra el título horizontalmente
            font=dict(size=20)
        ),
        xaxis_title="Año",
        yaxis_title="Número de Actividades",
        legend_title="Estado"
    )

    st.plotly_chart(fig)

if __name__ == "__main__":
    # Llamar directamente a las funciones de gráficos sin pasar argumentos
    mostrar_grafico_mantencion()
    mostrar_grafico_provision()
