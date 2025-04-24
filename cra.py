import streamlit as st
import pandas as pd
import os

# --- Cargar la base de datos combinada ---
def cargar_data_combinada():
    carpeta_data = "Data_diaria"
    all_files = [f for f in os.listdir(carpeta_data) if f.endswith('.xlsx') and not f.startswith('~$')]
    df_from_each_file = (pd.read_excel(os.path.join(carpeta_data, f), engine="openpyxl") for f in all_files)
    data_combinada = pd.concat(df_from_each_file, ignore_index=True)
    return data_combinada

# --- Cargar todas las hojas del archivo GPON ---
def cargar_data_gpon_multiples_hojas(nombre_archivo):
    try:
        excel_file = pd.ExcelFile(nombre_archivo, engine="openpyxl")
        hojas = excel_file.sheet_names
        data_gpon = {}
        for hoja in hojas:
            data_gpon[hoja] = excel_file.parse(hoja)
        return data_gpon, hojas
    except FileNotFoundError:
        st.error(f"Error: El archivo '{nombre_archivo}' no se encontró.")
        return None, None

# --- Main de la aplicación GPON ---
def main():
    st.title("Análisis Comparativo GPON")

    # Cargar los datos
    data_combinada = cargar_data_combinada()
    nombre_archivo_gpon = "Copia de Reporte GPON V2 para CRA_20241204.xlsx"
    data_gpon, hojas_gpon = cargar_data_gpon_multiples_hojas(nombre_archivo_gpon)

    hojas_a_eliminar = ['Splitters', 'Doble_Conectores', 'Cajas_de_Doble_Conector', 'Cajas_de_Gabinete', 'LDD_GO_GPON2']

    if data_combinada is not None and data_gpon is not None:
        st.subheader("Base de Datos Combinada (Muestra)")
        if 'Recursos de red' in data_combinada.columns:
            st.dataframe(data_combinada[['Recursos de red']].head())
        else:
            st.warning("La columna 'Recursos de red' no se encontró en la base de datos combinada.")

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
            if 'Recursos de red' in data_combinada.columns:
                resultados['data_combinada'] = data_combinada[data_combinada['Recursos de red'].str.contains(recurso_a_buscar, case=False, na=False)]

            for hoja, df in data_gpon_filtrada.items():
                # Buscar la columna que podría contener información similar a 'Recursos de red'
                # Esto puede variar dependiendo de la estructura de tus hojas GPON
                for col in df.columns:
                    try:
                        if df[col].astype(str).str.contains(recurso_a_buscar, case=False, na=False).any():
                            if hoja not in resultados:
                                resultados[hoja] = pd.DataFrame()
                            resultados[hoja] = pd.concat([resultados[hoja], df[df[col].astype(str).str.contains(recurso_a_buscar, case=False, na=False)]], ignore_index=True)
                            break # Asumimos que la primera columna que contiene la búsqueda es suficiente por hoja
                    except Exception as e:
                        st.warning(f"Error al procesar la columna '{col}' en la hoja '{hoja}': {e}")

            if resultados:
                st.subheader("Resultados de la Búsqueda:")
                for nombre_df, df_resultado in resultados.items():
                    st.subheader(f"Fuente: {nombre_df}")
                    st.dataframe(df_resultado)
            else:
                st.info(f"No se encontraron coincidencias para '{recurso_a_buscar}'.")

    else:
        st.warning("No se pudieron cargar los datos. Verifica los archivos Excel.")

if __name__ == "__main__":
    main()