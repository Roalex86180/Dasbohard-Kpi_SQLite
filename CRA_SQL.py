import mysql.connector
import pandas as pd
import os
import re
import streamlit as st
import json

# --- Función para conectarse a MySQL ---
def conectar_mysql():
    try:
        conn = mysql.connector.connect(
            host='localhost',        # Cambia esto por tu host (por ejemplo, 'localhost' o la IP de tu servidor MySQL)
            user='root',     # Cambia esto por tu usuario
            password='Rielecom2-',  # Cambia esto por tu contraseña
            database='datos_actividades'  # Asegúrate de que la base de datos existe
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error de conexión: {err}")
        return None

# --- Función para cargar los datos desde archivos Excel a MySQL ---
def cargar_datos_en_mysql(carpeta_data, db_conn):
    cursor = db_conn.cursor()

    # Leemos los archivos y los insertamos en la base de datos
    all_files = [f for f in os.listdir(carpeta_data) if f.endswith('.xlsx') and not f.startswith('~$')]
    for nombre_archivo in all_files:
        try:
            df = pd.read_excel(os.path.join(carpeta_data, nombre_archivo), engine="openpyxl")
            for _, row in df.iterrows():
                cursor.execute('''
                INSERT INTO actividades (recurso_red, datos) 
                VALUES (%s, %s)
                ''', (row['Recursos de red'], json.dumps(row.to_dict(), ensure_ascii=False)))
            db_conn.commit()
        except Exception as e:
            st.error(f"Error al cargar el archivo '{nombre_archivo}': {e}")

# --- Función para obtener datos desde MySQL ---
def obtener_datos_desde_mysql(db_conn):
    query = "SELECT * FROM actividades"
    df = pd.read_sql(query, db_conn)
    return df

# --- Función para cargar datos GPON desde varias hojas ---
def cargar_data_gpon_multiples_hojas(nombre_archivo_gpon):
    try:
        xls = pd.ExcelFile(nombre_archivo_gpon, engine="openpyxl")
        hojas_gpon = xls.sheet_names
        data_gpon = {hoja: pd.read_excel(xls, sheet_name=hoja) for hoja in hojas_gpon}
        return data_gpon, hojas_gpon
    except Exception as e:
        st.error(f"Error al cargar el archivo GPON: {e}")
        return None, None

# --- Función principal de la aplicación GPON ---
def main():
    st.title("Análisis Comparativo GPON")

    # Establecer la conexión a la base de datos MySQL
    db_conn = conectar_mysql()

    if db_conn:
        # Cargar los datos de MySQL
        data_combinada = obtener_datos_desde_mysql(db_conn)

        # Cargar archivo GPON
        nombre_archivo_gpon = "Copia de Reporte GPON V2 para CRA_20241204.xlsx"
        data_gpon, hojas_gpon = cargar_data_gpon_multiples_hojas(nombre_archivo_gpon)

        hojas_a_eliminar = ['Splitters', 'Doble_Conectores', 'Cajas_de_Doble_Conector', 'Cajas_de_Gabinete', 'LDD_GO_GPON2']

        if data_combinada is not None and data_gpon is not None:
            st.subheader("Base de Datos Combinada (Muestra)")
            st.dataframe(data_combinada[['recurso_red']].head())  # Muestra los primeros recursos de red

            # Eliminamos las hojas que no necesitamos
            hojas_gpon_filtradas = [hoja for hoja in hojas_gpon if hoja not in hojas_a_eliminar]
            data_gpon_filtrada = {hoja: data_gpon[hoja] for hoja in hojas_gpon_filtradas}

            st.subheader(f"Datos GPON del archivo '{nombre_archivo_gpon}'")
            for hoja, df in data_gpon_filtrada.items():
                st.subheader(f"Hoja: {hoja} (Muestra)")
                st.dataframe(df.head())

            st.subheader("Realizar Búsqueda")
            recurso_a_buscar = st.text_input("Ingresa el 'Recurso de red' a buscar:")

            if recurso_a_buscar:
                resultados = {}
                if 'recurso_red' in data_combinada.columns:
                    resultados['data_combinada'] = data_combinada[data_combinada['recurso_red'].str.contains(recurso_a_buscar, case=False, na=False)]

                for hoja, df in data_gpon_filtrada.items():
                    resultados_hoja = pd.DataFrame()
                    for col in df.columns:
                        try:
                            coincidencias = df[df[col].astype(str).str.contains(recurso_a_buscar, case=False, na=False)]
                            if not coincidencias.empty:
                                resultados_hoja = pd.concat([resultados_hoja, coincidencias], ignore_index=True)
                        except Exception as e:
                            st.warning(f"Error al procesar la columna '{col}' en la hoja '{hoja}': {e}")
                    if not resultados_hoja.empty:
                        resultados[hoja] = resultados_hoja

                if resultados:
                    st.subheader("Resultados de la Búsqueda:")
                    for nombre_df, df_resultado in resultados.items():
                        st.subheader(f"Fuente: {nombre_df}")
                        st.dataframe(df_resultado)
                else:
                    st.info(f"No se encontraron coincidencias para '{recurso_a_buscar}'.")

        else:
            st.warning("No se pudieron cargar los datos desde la base de datos MySQL.")
    else:
        st.error("No se pudo conectar a la base de datos MySQL.")

if __name__ == "__main__":
    main()
