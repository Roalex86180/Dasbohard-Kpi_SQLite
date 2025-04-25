import streamlit as st
import pandas as pd
from io import BytesIO
import re

def analizar_reincidencias_y_fallas_tempranas(df):
    

    columnas_mostrar = [
        "Fecha Agendamiento", "Recurso", "ID externo", "Tipo de actividad", "Observación", "Cod_Servicio",
        "Acción realizada", "Tipo de Vivienda", "Estado de actividad", "Nombre Cliente", "Dirección", "Comuna", "Región",
        "Teléfono móvil", "Cliente que recibe:", "Decos que Posee", "Cantidad de equipos telefónicos", "Diagnóstico",
        "Fecha Ingreso en OFSC", "Plan de internet", "Nombre del bundle", "Resultado cambio equipo", "Resultado activación",
        "Código activación", "SR de Siebel", "Recursos de red", "Análisis Cobertura WiFi", "Potencia en CTO",
        "Potencia en Gabinete", "Propietario de Red", "AccessID"
    ]

    df['Fecha Agendamiento'] = pd.to_datetime(df['Fecha Agendamiento'], errors='coerce')

    # --- REINCIDENCIAS ---
    st.markdown("---")
    st.header("Detección de Reincidencias")

    fecha_min = df['Fecha Agendamiento'].min()
    fecha_max = df['Fecha Agendamiento'].max()

    rango_reincidencias = st.date_input(
        "Selecciona el rango de fechas para análisis de reincidencias:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
        key="rango_reincidencias"
    )

    if isinstance(rango_reincidencias, tuple):
        fecha_inicio_r, fecha_fin_r = pd.to_datetime(rango_reincidencias[0]), pd.to_datetime(rango_reincidencias[1])
        df_reincidencias_rango = df[(df['Fecha Agendamiento'] >= fecha_inicio_r) & (df['Fecha Agendamiento'] <= fecha_fin_r)]
    else:
        df_reincidencias_rango = df.copy()

    resultado = []

    for cod, grupo in df_reincidencias_rango.groupby('Cod_Servicio'):
        grupo = grupo.sort_values(by='Fecha Agendamiento').reset_index(drop=True)
        if len(grupo) < 2:
            continue
        primera_visita = grupo.iloc[0]
        if "reparación" not in str(primera_visita['Tipo de actividad']).lower():
            continue
        fecha_inicio = primera_visita['Fecha Agendamiento']
        grupo_dentro_rango = grupo[grupo['Fecha Agendamiento'] <= fecha_inicio + pd.Timedelta(days=10)]
        grupo_filtrado = grupo_dentro_rango[
            ~(
                grupo_dentro_rango['Tipo de actividad'].str.contains('postventa', case=False, na=False) |
                grupo_dentro_rango['Estado de actividad'].str.contains('suspendida|no realizado|cancelada|pendiente', case=False, na=False)
            )
        ]
        if len(grupo_filtrado) > 1:
            grupo_filtrado = grupo_filtrado.copy()
            tipo_visitas = ['Reincidencia'] * (len(grupo_filtrado) - 1) + ['Última Visita']
            grupo_filtrado['Tipo Visita'] = tipo_visitas
            resultado.append(grupo_filtrado)

    if resultado:
        df_reincidencias = pd.concat(resultado)
        total_reincidencias = df_reincidencias['Tipo Visita'].value_counts().get('Reincidencia', 0)
        st.success(f"Se encontraron {total_reincidencias} reincidencias.")
        df_reincidencias_mostrar = df_reincidencias[columnas_mostrar + ['Tipo Visita']]
        st.dataframe(df_reincidencias_mostrar)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_reincidencias_mostrar.to_excel(writer, index=False, sheet_name='Reincidencias')
        st.download_button("📥 Descargar Reincidencias (.xlsx)", data=buffer.getvalue(), file_name="reincidencias.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No se encontraron reincidencias según los criterios definidos.")

    # --- FALLAS TEMPRANAS ---
    st.markdown("---")
    st.header(" Detección de Fallas Tempranas")

    rango_fallas = st.date_input(
        "Selecciona el rango de fechas para análisis de fallas tempranas:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
        key="rango_fallas_tempranas"
    )

    if isinstance(rango_fallas, tuple):
        fecha_inicio_f, fecha_fin_f = pd.to_datetime(rango_fallas[0]), pd.to_datetime(rango_fallas[1])
        df_fallas_rango = df[(df['Fecha Agendamiento'] >= fecha_inicio_f) & (df['Fecha Agendamiento'] <= fecha_fin_f)]
    else:
        df_fallas_rango = df.copy()

    resultado_fallas_tempranas = []

    for cod, grupo in df_fallas_rango.groupby('Cod_Servicio'):
        grupo = grupo.sort_values(by='Fecha Agendamiento').reset_index(drop=True)
        if len(grupo) < 2:
            continue
        primera_visita = grupo.iloc[0]
        if "instalación" not in str(primera_visita['Tipo de actividad']).lower():
            continue
        fecha_inicio = primera_visita['Fecha Agendamiento']
        grupo_dentro_rango = grupo[grupo['Fecha Agendamiento'] <= fecha_inicio + pd.Timedelta(days=10)]
        grupo_filtrado = grupo_dentro_rango[
            ~(
                grupo_dentro_rango['Tipo de actividad'].str.contains('postventa', case=False, na=False) |
                grupo_dentro_rango['Estado de actividad'].str.contains('suspendida|cancelada|no realizado|pendiente', case=False, na=False)
            )
        ]
        if len(grupo_filtrado) > 1:
            grupo_filtrado = grupo_filtrado.copy()
            tipo_visitas = ['Reincidencia'] * (len(grupo_filtrado) - 1) + ['Última Visita']
            grupo_filtrado['Tipo Visita'] = tipo_visitas
            resultado_fallas_tempranas.append(grupo_filtrado)

    if resultado_fallas_tempranas:
        df_fallas_tempranas = pd.concat(resultado_fallas_tempranas)
        total_fallas = df_fallas_tempranas['Tipo Visita'].value_counts().get('Reincidencia', 0)
        st.success(f"Se encontraron {total_fallas} registros con fallas tempranas.")
        df_fallas_mostrar = df_fallas_tempranas[columnas_mostrar + ['Tipo Visita']]
        st.dataframe(df_fallas_mostrar)

        buffer_fallas = BytesIO()
        with pd.ExcelWriter(buffer_fallas, engine='openpyxl') as writer:
            df_fallas_mostrar.to_excel(writer, index=False, sheet_name='Fallas_Tempranas')
        st.download_button("📥 Descargar Fallas Tempranas (.xlsx)", data=buffer_fallas.getvalue(), file_name="fallas_tempranas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No se encontraron fallas tempranas según los criterios definidos.")




















