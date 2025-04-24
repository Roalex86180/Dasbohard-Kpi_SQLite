import pandas as pd
import os

def verificar_formato_actividades(ruta_archivo):
    """
    Verifica si un archivo Excel tiene el formato esperado para las actividades.

    Args:
        ruta_archivo (str): La ruta al archivo Excel.

    Returns:
        bool: True si el formato es correcto, False en caso contrario.
        str: Un mensaje descriptivo del resultado de la verificación.
    """
    try:
        df_prueba = pd.read_excel(ruta_archivo, engine="openpyxl", nrows=5)  # Leer solo las primeras filas
        columnas_esperadas = ['Recurso', 'ID externo', 'Coordenadas Inicio', 'Coordenadas Fin',
                               'Dirección', 'Comuna', 'Tipo de actividad', 'Estado de actividad',
                               'Inicio', 'Finalización', 'Observación']  # Ajusta a tus columnas

        columnas_presentes = list(df_prueba.columns)

        if all(col in columnas_presentes for col in columnas_esperadas):
            return True, f"El archivo '{ruta_archivo}' tiene el formato esperado (columnas: {', '.join(columnas_esperadas)})."
        else:
            columnas_faltantes = [col for col in columnas_esperadas if col not in columnas_presentes]
            return False, f"Error: El archivo '{ruta_archivo}' no tiene el formato esperado. Faltan las siguientes columnas: {', '.join(columnas_faltantes)}."

    except FileNotFoundError:
        return False, f"Error: No se encontró el archivo '{ruta_archivo}'."
    except Exception as e:
        return False, f"Error al leer el archivo '{ruta_archivo}': {e}"

if __name__ == "__main__":
    # Ejemplo de uso para probar la función con un archivo en Data_diaria
    carpeta_datos = "Data_diaria"
    archivo_ejemplo = None
    try:
        for nombre_archivo in os.listdir(carpeta_datos):
            if nombre_archivo.endswith(".xlsx"):
                archivo_ejemplo = os.path.join(carpeta_datos, nombre_archivo)
                break  # Tomamos el primer archivo .xlsx que encontremos
        if archivo_ejemplo:
            formato_correcto, mensaje_correcto = verificar_formato_actividades(archivo_ejemplo)
            print(f"Archivo: {archivo_ejemplo}, Formato Correcto: {formato_correcto}, Mensaje: {mensaje_correcto}")
        else:
            print(f"No se encontraron archivos .xlsx en la carpeta '{carpeta_datos}' para probar.")
    except FileNotFoundError:
        print(f"Error: No se encontró la carpeta '{carpeta_datos}'.")
