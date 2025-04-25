import streamlit as st
import pandas as pd
import sqlite3
from geopy.distance import geodesic
import re
import unicodedata

UMBRAL_DISTANCIA_KM = 0.2  # 200 metros
conn = sqlite3.connect("datos_actividades.db")

def obtener_coordenadas(valor_coordenada):
    try:
        if pd.notna(valor_coordenada):
            valor_limpio = valor_coordenada.strip()
            lat_match = re.search(r"lat:([-+]?\d*\.?\d+)", valor_limpio.lower())
            lng_match = re.search(r"lng:([-+]?\d*\.?\d+)", valor_limpio.lower())
            if lat_match and lng_match:
                lat = float(lat_match.group(1))
                lon = float(lng_match.group(1))
                return (lat, lon)
        return None
    except (ValueError, AttributeError):
        return None

def calcular_distancia(coord1, coord2):
    if coord1 and coord2:
        return geodesic(coord1, coord2).km
    return float('inf')

def remover_acentos(texto):
    if isinstance(texto, str):
        nfkd = unicodedata.normalize('NFKD', texto)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])
    return texto

def mostrar_verificacion_ubicacion_sql(conn):
    st.subheader("Cumplimiento de Inicio y Cierre en Cliente")

    try:
        query = """
        SELECT 
            [Recurso], 
            [ID externo], 
            [Dirección], 
            [Comuna], 
            [Coordenadas Inicio], 
            [Coordenadas Fin], 
            [Coordenada Y], 
            [Coordenada X]
        FROM actividades
        WHERE [Recurso] IS NOT NULL 
            AND [ID externo] IS NOT NULL 
            AND [Coordenadas Inicio] IS NOT NULL 
            AND [Coordenadas Fin] IS NOT NULL 
            AND [Coordenada Y] IS NOT NULL 
            AND [Coordenada X] IS NOT NULL
        """
        data = pd.read_sql_query(query, conn)

        data['Inicio en Cliente'] = 'no ingreso coordenadas'
        data['Cierre en Cliente'] = 'no ingreso coordenadas'
        data['coord_cliente_lat'] = data['Coordenada Y'].astype(float)
        data['coord_cliente_lon'] = data['Coordenada X'].astype(float)
        data['coord_inicio_tecnico_lat'] = None
        data['coord_inicio_tecnico_lon'] = None
        data['coord_fin_tecnico_lat'] = None
        data['coord_fin_tecnico_lon'] = None

        for index, row in data.iterrows():
            coord_inicio = obtener_coordenadas(row['Coordenadas Inicio'])
            coord_fin = obtener_coordenadas(row['Coordenadas Fin'])

            if coord_inicio:
                data.at[index, 'coord_inicio_tecnico_lat'] = coord_inicio[0]
                data.at[index, 'coord_inicio_tecnico_lon'] = coord_inicio[1]

            if coord_fin:
                data.at[index, 'coord_fin_tecnico_lat'] = coord_fin[0]
                data.at[index, 'coord_fin_tecnico_lon'] = coord_fin[1]

        for index, row in data.iterrows():
            coord_cliente = (row['coord_cliente_lat'], row['coord_cliente_lon'])

            if pd.notna(row['coord_inicio_tecnico_lat']) and pd.notna(row['coord_inicio_tecnico_lon']):
                coord_inicio_tecnico = (row['coord_inicio_tecnico_lat'], row['coord_inicio_tecnico_lon'])
                dist_inicio = calcular_distancia(coord_inicio_tecnico, coord_cliente)
                data.at[index, 'Inicio en Cliente'] = 'si' if dist_inicio <= UMBRAL_DISTANCIA_KM else 'no'
            else:
                data.at[index, 'Inicio en Cliente'] = 'sin coordenadas técnico'

            if pd.notna(row['coord_fin_tecnico_lat']) and pd.notna(row['coord_fin_tecnico_lon']):
                coord_fin_tecnico = (row['coord_fin_tecnico_lat'], row['coord_fin_tecnico_lon'])
                dist_fin = calcular_distancia(coord_fin_tecnico, coord_cliente)
                data.at[index, 'Cierre en Cliente'] = 'si' if dist_fin <= UMBRAL_DISTANCIA_KM else 'no'
            else:
                data.at[index, 'Cierre en Cliente'] = 'sin coordenadas técnico'

        data['Recurso'] = data['Recurso'].apply(remover_acentos).str.lower()

        def calcular_porcentaje(series):
            total = series.count()
            cumplimiento = series[series.str.strip() == 'si'].count()
            return f"{((cumplimiento / total) * 100):.1f}%" if total > 0 else "0.0%"

        total_auditadas = data['Recurso'].value_counts().reset_index()
        total_auditadas.columns = ['Recurso', 'Total Actividades Auditadas']

        resultados = data.groupby('Recurso').agg(
            **{'% Inicio en cliente': pd.NamedAgg(column='Inicio en Cliente', aggfunc=calcular_porcentaje),
               '% Cierre en cliente': pd.NamedAgg(column='Cierre en Cliente', aggfunc=calcular_porcentaje)}
        ).reset_index()

        resultados_final = pd.merge(resultados, total_auditadas, on='Recurso', how='left')
        resultados_final = resultados_final[['Recurso', '% Inicio en cliente', 'Total Actividades Auditadas', '% Cierre en cliente']]
        resultados_final = resultados_final.sort_values(by='Recurso')

        def color_porcentaje(val):
            try:
                porcentaje = float(val.replace('%', ''))
                if porcentaje >= 80:
                    return 'background-color: #a8f0c6'
                elif porcentaje < 80:
                    return 'background-color: #f5b7b1'
            except ValueError:
                return ''
            return ''

        styled = resultados_final.style.applymap(color_porcentaje, subset=['% Inicio en cliente', '% Cierre en cliente'])
        st.dataframe(styled)

        tecnicos = [""] + resultados_final['Recurso'].tolist()
        tecnico_seleccionado = st.selectbox("Seleccionar Técnico para ver detalles:", tecnicos)

        if tecnico_seleccionado:
            st.subheader(f"Detalles para {tecnico_seleccionado}")
            detalles = data[data['Recurso'].str.strip().str.lower() == tecnico_seleccionado.strip().lower()]
            st.dataframe(detalles[[
                'ID externo', 'Dirección', 'Comuna',
                'Inicio en Cliente', 'Cierre en Cliente',
                'Coordenadas Inicio', 'Coordenadas Fin',
                'Coordenada Y', 'Coordenada X',
                'coord_inicio_tecnico_lat', 'coord_inicio_tecnico_lon',
                'coord_fin_tecnico_lat', 'coord_fin_tecnico_lon',
                'coord_cliente_lat', 'coord_cliente_lon'
            ]])

    except Exception as e:
        st.error(f"Error en verificación de ubicación: {e}")
