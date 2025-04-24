import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import re
import os
import unicodedata

# --- Configuración Global ---
USER_AGENT = "mi_verificador_de_columnas"
UMBRAL_DISTANCIA_KM = 0.2  # 200 metros
carpeta_datos = "Data_diaria"
patron_archivo = r"Actividades-RIELECOM - RM_\d{2}_\d{2}_\d{2}\.xlsx"

@st.cache_resource
def obtener_geolocator():
    # Ya no se usa directamente para geocodificar la dirección del cliente
    return None

@st.cache_data(show_spinner=True)
def geocodificar_direccion_cached(direccion, comuna, _geolocator):
    # Ya no se usa directamente para geocodificar la dirección del cliente
    return None

def calcular_distancia(coord1, coord2):
    if coord1 and coord2:
        return geodesic(coord1, coord2).km
    return float('inf')

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

def cargar_datos(carpeta, patron):
    """Carga y combina datos de múltiples archivos Excel en una carpeta."""
    all_data = []
    archivos_cargados = []
    try:
        for nombre_archivo in os.listdir(carpeta):
            if re.match(patron, nombre_archivo):
                ruta_archivo = os.path.join(carpeta, nombre_archivo)
                try:
                    df = pd.read_excel(ruta_archivo, engine="openpyxl")
                    all_data.append(df)
                    archivos_cargados.append(nombre_archivo)
                except Exception as e:
                    st.error(f"Error al cargar el archivo '{nombre_archivo}': {e}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            st.info(f"Se cargaron datos de los siguientes archivos: {', '.join(archivos_cargados)}")
            return combined_df
        else:
            st.warning(f"No se encontraron archivos válidos en la carpeta '{carpeta}'.")
            return None
    except FileNotFoundError:
        st.error(f"Error: No se encontró la carpeta '{carpeta}'.")
        return None

def remover_acentos(texto):
    if isinstance(texto, str):
        nfkd = unicodedata.normalize('NFKD', texto)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])
    return texto

def mostrar_verificacion_ubicacion(data):
    st.subheader("Cumplimiento de Inicio y Cierre en Cliente")
    try:
        # --- PASO 1: Operaciones iniciales y dropna ---
        ubicacion_verificacion = data.dropna(subset=['Recurso', 'ID externo', 'Coordenadas Inicio', 'Coordenadas Fin', 'Coordenada Y', 'Coordenada X']).copy()

        ubicacion_verificacion['Inicio en Cliente'] = 'no ingreso coordenadas'
        ubicacion_verificacion['Cierre en Cliente'] = 'no ingreso coordenadas'
        ubicacion_verificacion['coord_cliente_lat'] = ubicacion_verificacion['Coordenada Y'].astype(float)
        ubicacion_verificacion['coord_cliente_lon'] = ubicacion_verificacion['Coordenada X'].astype(float)
        ubicacion_verificacion['coord_inicio_tecnico_lat'] = None
        ubicacion_verificacion['coord_inicio_tecnico_lon'] = None
        ubicacion_verificacion['coord_fin_tecnico_lat'] = None
        ubicacion_verificacion['coord_fin_tecnico_lon'] = None

        # --- PASO 2: Ya no se usa geolocator para cliente ---
        geolocator = obtener_geolocator()

        # --- PASO 3: Ya no se geocodifica la dirección del cliente ---
        # --- PASO 4: Bucle para obtener coordenadas del técnico (DESCOMENTADO) ---
        for index, row in ubicacion_verificacion.iterrows():
            try:
                coord_inicio = obtener_coordenadas(row.get('Coordenadas Inicio'))
                if isinstance(coord_inicio, tuple) and len(coord_inicio) == 2:
                    ubicacion_verificacion.loc[index, 'coord_inicio_tecnico_lat'] = coord_inicio[0]
                    ubicacion_verificacion.loc[index, 'coord_inicio_tecnico_lon'] = coord_inicio[1]

                coord_fin = obtener_coordenadas(row.get('Coordenadas Fin'))
                if isinstance(coord_fin, tuple) and len(coord_fin) == 2:
                    ubicacion_verificacion.loc[index, 'coord_fin_tecnico_lat'] = coord_fin[0]
                    ubicacion_verificacion.loc[index, 'coord_fin_tecnico_lon'] = coord_fin[1]
            except Exception as e:
                st.error(f"Error al obtener coordenadas del técnico: {e}")
                continue

        # --- PASO 5: Bucle para calcular distancias y determinar cumplimiento (DESCOMENTADO) ---
        for index, row in ubicacion_verificacion.iterrows():
            try:
                coord_cliente = (ubicacion_verificacion.loc[index, 'coord_cliente_lat'], ubicacion_verificacion.loc[index, 'coord_cliente_lon'])
                if pd.notna(ubicacion_verificacion.loc[index, 'coord_inicio_tecnico_lat']) and pd.notna(ubicacion_verificacion.loc[index, 'coord_inicio_tecnico_lon']):
                    coord_inicio_tecnico = (ubicacion_verificacion.loc[index, 'coord_inicio_tecnico_lat'], ubicacion_verificacion.loc[index, 'coord_inicio_tecnico_lon'])
                    distancia_inicio = calcular_distancia(coord_inicio_tecnico, coord_cliente)
                    ubicacion_verificacion.loc[index, 'Inicio en Cliente'] = 'si' if distancia_inicio <= UMBRAL_DISTANCIA_KM else 'no'
                else:
                    ubicacion_verificacion.loc[index, 'Inicio en Cliente'] = 'sin coordenadas técnico'

                if pd.notna(ubicacion_verificacion.loc[index, 'coord_fin_tecnico_lat']) and pd.notna(ubicacion_verificacion.loc[index, 'coord_fin_tecnico_lon']):
                    coord_fin_tecnico = (ubicacion_verificacion.loc[index, 'coord_fin_tecnico_lat'], ubicacion_verificacion.loc[index, 'coord_fin_tecnico_lon'])
                    distancia_fin = calcular_distancia(coord_fin_tecnico, coord_cliente)
                    ubicacion_verificacion.loc[index, 'Cierre en Cliente'] = 'si' if distancia_fin <= UMBRAL_DISTANCIA_KM else 'no'
                else:
                    ubicacion_verificacion.loc[index, 'Cierre en Cliente'] = 'sin coordenadas técnico'
            except Exception as e:
                st.error(f"Error al asignar Inicio/Cierre: {e}")

        ubicacion_filtrada = ubicacion_verificacion[pd.notna(ubicacion_verificacion['coord_cliente_lat'])].copy()

        # --- PASO 6: Filtrado y cálculo de total_auditadas_por_recurso ---
        total_auditadas_por_recurso = ubicacion_filtrada['Recurso'].value_counts().reset_index()
        total_auditadas_por_recurso.columns = ['Recurso', 'Total Actividades Auditadas']
        total_auditadas_por_recurso['Recurso'] = total_auditadas_por_recurso['Recurso'].apply(remover_acentos).str.lower()

        def calcular_porcentaje(series):
            total = series.count()
            cumplimiento = series[series.str.strip() == 'si'].count()
            return f"{((cumplimiento / total) * 100):.1f}%" if total > 0 else "0.0%"

        # --- PASO 7: Cálculo de resultados_por_tecnico ---
        resultados_por_tecnico = ubicacion_filtrada.groupby('Recurso').agg(
            **{'% Inicio en cliente': pd.NamedAgg(column='Inicio en Cliente', aggfunc=calcular_porcentaje),
               '% Cierre en cliente': pd.NamedAgg(column='Cierre en Cliente', aggfunc=calcular_porcentaje)}
        ).reset_index()
        resultados_por_tecnico['Recurso'] = resultados_por_tecnico['Recurso'].apply(remover_acentos).str.lower()

        # --- PASO 8: Combinar con el total de actividades auditadas ---
        resultados_final = pd.merge(resultados_por_tecnico, total_auditadas_por_recurso, on='Recurso', how='left').fillna(0)
        resultados_final = resultados_final[['Recurso', '% Inicio en cliente', 'Total Actividades Auditadas', '% Cierre en cliente']] # Reordenar a la 3ra posición
        resultados_final = resultados_final.sort_values(by='Recurso') # Mantener el orden por recurso

        def color_porcentaje(val):
            try:
                porcentaje = float(val.replace('%', ''))
                if porcentaje >= 80:  # Cambiar > a >= para incluir 80%
                    return 'background-color: #a8f0c6'  # Verde claro
                elif porcentaje < 80:
                    return 'background-color: #f5b7b1'  # Rojo claro
                return ''
            except ValueError:
                return ''

        styled_resultados = resultados_final.style.applymap(color_porcentaje, subset=['% Inicio en cliente', '% Cierre en cliente'])
        st.dataframe(styled_resultados)

        tecnicos = [""] + resultados_final['Recurso'].tolist()
        tecnico_seleccionado = st.selectbox("Seleccionar Técnico para ver detalles:", tecnicos)

        if tecnico_seleccionado:
            st.subheader(f"Detalles para {tecnico_seleccionado}")
            detalles_tecnico = ubicacion_verificacion[ubicacion_verificacion['Recurso'].str.strip().str.lower() == tecnico_seleccionado.strip().lower()]
            st.dataframe(detalles_tecnico[['ID externo', 'Dirección', 'Comuna', 'Inicio en Cliente', 'Cierre en Cliente', 'Coordenadas Inicio', 'Coordenadas Fin', 'Coordenada Y', 'Coordenada X', 'coord_inicio_tecnico_lat', 'coord_inicio_tecnico_lon', 'coord_fin_tecnico_lat', 'coord_fin_tecnico_lon', 'coord_cliente_lat', 'coord_cliente_lon']])

    except Exception as e:
        st.error(f"Error al calcular o mostrar resultados: {e}")

if __name__ == "__main__":
    data_combinada = cargar_datos(carpeta_datos, patron_archivo)
    mostrar_verificacion_ubicacion(data_combinada.copy())