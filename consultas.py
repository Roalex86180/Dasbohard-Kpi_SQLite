import streamlit as st
import pandas as pd
import re
import os
import verificacion_ubicacion
import verificar_formato
import plotly.express as px
import resumen_general
from Rt_Ft import analizar_reincidencias_y_fallas_tempranas
import base64


# Título del Dashboard
#st.title("KPI RIELECOM SPA")

# Carpeta que contiene los archivos de datos diarios
carpeta_datos = "Data_diaria"
patron_archivo = r"Actividades-(RIELECOM - RM|MultiSkill \(Rielecom-3Play-RM\))(_|-)\d{2}_\d{2}_\d{2}( \(\d+\))?\.((xlsx)|(csv))"

@st.cache_data
def cargar_y_verificar_datos(carpeta, patron):
    all_data = []
    archivos_cargados = []
    try:
        for nombre_archivo in os.listdir(carpeta):
            if re.match(patron, nombre_archivo):
                ruta_archivo = os.path.join(carpeta, nombre_archivo)
                formato_correcto = True  # Asumimos formato correcto para CSV inicialmente
                mensaje_formato = ""

                if nombre_archivo.endswith(".xlsx"):
                    formato_correcto, mensaje_formato = verificar_formato.verificar_formato_actividades(ruta_archivo)

                if formato_correcto:
                    try:
                        if nombre_archivo.endswith(".xlsx"):
                            df = pd.read_excel(ruta_archivo, engine="openpyxl")
                        elif nombre_archivo.endswith(".csv"):
                            df = pd.read_csv(ruta_archivo)
                        all_data.append(df)
                        archivos_cargados.append(nombre_archivo)
                    except Exception as e:
                        st.error(f"Error al cargar el archivo '{nombre_archivo}' después de la verificación: {e}")
                else:
                    st.error(f"Formato incorrecto para el archivo '{nombre_archivo}': {mensaje_formato}")
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return combined_df
        else:
            st.warning(f"No se encontraron archivos válidos en la carpeta '{carpeta}'.")
            return None
    except FileNotFoundError:
        st.error(f"Error: No se encontró la carpeta '{carpeta}'.")
        return None

data_combinada = cargar_y_verificar_datos(carpeta_datos, patron_archivo)

if data_combinada is not None:


    # --- Cálculo de Total Finalizadas y Total Asignadas para las etiquetas ---
    exclusiones = ['Almuerzo', 'Permiso', 'Reunion', 'Mantencion Vehicular', 'Curso', 'Levantamiento', 'Apoyo Terreno','Planta - Mantención']

    # Filtrar las actividades excluyendo los tipos especificados
    df_filtered = data_combinada[~data_combinada['Tipo de actividad'].str.lower().str.contains('|'.join(exclusiones).lower(), na=False)].copy()

    # Calcular Total Finalizadas (Reparación, Posventa, Instalación)
    total_finalizadas = df_filtered[
        df_filtered['Estado de actividad'].str.lower() == 'finalizada'
    ][
        df_filtered['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
    ]['ID externo'].nunique()

    # Calcular Total Asignadas (Finalizadas + No Realizado)
    total_asignadas = df_filtered[
        df_filtered['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
    ][
        df_filtered['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
    ]['ID externo'].nunique()

    # --- Estilo CSS para las etiquetas grandes ---
    label_style = """
        <style>
            .label-container {
                display: flex;
                gap: 20px; /* Espacio entre las etiquetas */
                align-items: center; /* Alineación vertical */
                margin-left: -300px; /* Empuja el contenedor a la derecha */
                margin-top: -80px; /* Mueve el contenedor hacia arriba (ajusta el valor según necesites) */
            }
            .label-box {
                background-color: #f0f2f6; /* Color de fondo del cuadrado */
                border-radius: 5px; /* Bordes redondeados */
                padding: 15px 20px; /* Espacio interno */
                text-align: center;
                font-size: 1.2em;
                font-weight: bold;
            }
            .label-title {
                font-size: 0.8em;
                color: #555;
            }
        </style>
    """

    # --- Mostrar el título y las etiquetas con estilo ---
    st.markdown(label_style, unsafe_allow_html=True)

    st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h1>KPI RIELECOM SPA</h1>
        <div style="margin-left: 50px; margin-top: -15px;">
            <div class="label-container">
                <div class="label-box">
                    <div class="label-title">Total Finalizadas</div>
                    <div>{total_finalizadas}</div>
                </div>
                <div class="label-box">
                    <div class="label-title">Total Asignadas</div>
                    <div>{total_asignadas}</div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
    # --- Campo de Búsqueda de Cliente ---
    st.markdown("---")
    st.subheader("Buscar Información de Cliente")
    termino_busqueda = st.text_input("Ingrese Nombre, RUT, ID Externo, Dirección, Ciudad, Comuna, Teléfono, Correo o Cod_Servicio:")
    columnas_a_buscar = ['Nombre Cliente', 'Rut Cliente', 'ID externo', 'Dirección', 'Ciudad', 'Comuna', 'Teléfono móvil', 'Correo electrónico', 'Cod_Servicio', 'Recurso']
    columnas_a_mostrar = ['Fecha Agendamiento','Recurso','Nombre Cliente', 'Rut Cliente', 'ID externo', 'Tipo de actividad', 'Acción realizada','Tipo Cierre','Motivo','SR de Siebel', 'Dirección', 'Ciudad', 'Comuna', 'Tipo de Vivienda','Teléfono móvil', 'Correo electrónico','Diagnóstico','Tipo de Servicio (TS1/TS2)', 'Producto/Plan contratado', 'Plan de internet', 'Nombre del bundle', 'Pack de canales premium','Cantidad routers','Cantidad de STB','Propietario de Red','AccessID']
    
    if termino_busqueda:
        resultados_busqueda = pd.DataFrame()
        for columna in columnas_a_buscar:
            if columna in data_combinada.columns:
                resultados = data_combinada[data_combinada[columna].astype(str).str.contains(termino_busqueda, case=False, na=False, regex=False)]
                resultados_busqueda = pd.concat([resultados_busqueda, resultados], ignore_index=True).drop_duplicates()
                if not resultados_busqueda.empty:
                    break
            else:
                st.warning(f"La columna '{columna}' para buscar ('{columna}') no se encontró en los datos.")
        if not resultados_busqueda.empty:
            columnas_existentes_a_mostrar = [col for col in columnas_a_mostrar if col in resultados_busqueda.columns]
            st.subheader("Resultados de la Búsqueda")
            st.dataframe(resultados_busqueda[columnas_existentes_a_mostrar])
        else:
            st.info("No se encontraron resultados para la búsqueda.")

    # --- Ranking de Técnicos Más Productivos ----
    st.markdown("---")
    st.subheader("Ranking Diario")

# Selector de fecha para filtrar el ranking
fecha_seleccionada = st.date_input("Filtrar ranking por fecha", value=None)

# Filtrar el DataFrame data_combinada basado en la fecha seleccionada
if fecha_seleccionada:
    data_filtrada = data_combinada[data_combinada['Fecha Agendamiento'] == pd.to_datetime(fecha_seleccionada)].copy()
else:
    data_filtrada = data_combinada.copy()

# Asegúrate de que la columna 'Fecha Agendamiento' esté en formato datetime de Pandas
data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y')

st.subheader("Ranking de Técnicos Más Productivos (Finalizadas vs. Asignadas)")

# Filtrar el DataFrame data_combinada basado en la fecha seleccionada
if fecha_seleccionada:
    data_filtrada = data_combinada[data_combinada['Fecha Agendamiento'].dt.date == fecha_seleccionada].copy()
else:
    data_filtrada = data_combinada.copy()

# --- Ranking de Técnicos Más Productivos (con filtro de fecha aplicado) ----
actividades_asignadas = data_filtrada[~data_filtrada['Tipo de actividad'].isin(['Almuerzo', 'Espera INC nueva', 'Retiro Equipos', 'Reunion', 'Levantamiento', 'FZ', 'Apoyo Terreno','Planta - Mantención', 'Planta - Medición', 'Planta - Provisión', 'Incidencia Manual'])].copy()
total_asignadas_serie = actividades_asignadas['Recurso'].value_counts()
ranking_asignadas_df = pd.DataFrame({'Técnico': total_asignadas_serie.index, 'Total Asignadas': total_asignadas_serie.values})

actividades_a_contar = data_filtrada[~data_filtrada['Tipo de actividad'].isin(['Almuerzo', 'Espera INC nueva', 'Retiro Equipos', 'Reunion', 'Levantamiento','Apoyo Terreno', 'FZ','Planta - Mantención', 'Planta - Medición', 'Planta - Provisión', 'Incidencia Manual'])].copy()
actividades_finalizadas_tiempo = actividades_a_contar[actividades_a_contar['Estado de actividad'].str.lower() == 'finalizada'].copy()
productividad_ranking_serie = actividades_finalizadas_tiempo['Recurso'].value_counts()
productividad_ranking_df = pd.DataFrame({'Técnico': productividad_ranking_serie.index, 'Total Finalizadas': productividad_ranking_serie.values})

productividad_final_df = pd.merge(productividad_ranking_df, ranking_asignadas_df, on='Técnico', how='left').fillna(0)
productividad_final_df['Porcentaje de Efectividad'] = (productividad_final_df['Total Finalizadas'] / productividad_final_df['Total Asignadas'] * 100).round(2).fillna(0).astype(str) + '%'
productividad_final_df = productividad_final_df.sort_values(by='Total Finalizadas', ascending=False).reset_index(drop=True)
productividad_final_df.index = productividad_final_df.index + 1

# Mostrar la tabla del ranking
st.dataframe(productividad_final_df)

if fecha_seleccionada and productividad_final_df.empty:
    st.info(f"No hay datos de actividades para la fecha: {fecha_seleccionada.strftime('%Y-%m-%d')}")
elif not fecha_seleccionada:
    st.info("Mostrando el ranking completo (sin filtro de fecha).")

    # --- Técnicos que mencionan U2000 ---
    st.markdown("---")
    st.subheader("Técnicos que Realizan U2000")
    u2000_mentions = data_combinada[data_combinada['Observación'].str.contains(r'u\s?2000|u\s?200|u200', flags=re.IGNORECASE, na=False)].copy()
    if not u2000_mentions.empty:
        u2000_ranking_serie = u2000_mentions['Recurso'].value_counts()
        u2000_ranking_df = pd.DataFrame({'Técnico': u2000_ranking_serie.index, 'Cantidad U2000': u2000_ranking_serie.values})
        u2000_ranking_df.index = u2000_ranking_df.index + 1
        st.dataframe(u2000_ranking_df)
    else:
        st.info("Ningún técnico ha mencionado 'u2000' en las observaciones.")

    # --- Ranking de Técnicos Más Rápidos (Tiempo Promedio) ---
    st.markdown("---")
    st.subheader("Ranking de Técnicos Más Rápidos (Tiempo Promedio por Trabajo Finalizado en Horas)")

    @st.cache_data
    def calcular_ranking_tiempo(df):
        """Calcula el ranking de técnicos más rápidos basado en el tiempo promedio
        de trabajos de instalación, reparación o postventa finalizados.
        """
        # Filtrar las actividades por el tipo especificado
        actividades_filtradas = df[
            df['Tipo de actividad'].astype(str).str.contains(
                r'instalaci[oó]n|reparaci[oó]n|postventa',
                case=False,
                regex=True,
                na=False
            )
        ].copy()

        # Filtrar solo las actividades que están 'finalizadas' y donde 'Duración' no es '00:00'
        actividades_finalizadas_tiempo = actividades_filtradas[
            (actividades_filtradas['Estado de actividad'].str.lower() == 'finalizada') &
            (actividades_filtradas['Duración'] != '00:00') &  # Excluir duraciones de cero
            (pd.notna(actividades_filtradas['Duración'])) # Asegurarse de que no sea NaN
        ].copy()

        if not actividades_finalizadas_tiempo.empty:
            # Función para convertir 'HH:MM' a minutos
            def tiempo_a_minutos(tiempo_str):
                try:
                    horas, minutos = map(int, tiempo_str.split(':'))
                    return (horas * 60) + minutos
                except:
                    return None  # Manejar posibles errores de formato

            # Convertir la columna 'Duración' a minutos
            actividades_finalizadas_tiempo.loc[:, 'Duración (minutos)'] = actividades_finalizadas_tiempo['Duración'].apply(tiempo_a_minutos)

            # Eliminar filas donde la conversión a minutos falló
            actividades_finalizadas_tiempo = actividades_finalizadas_tiempo.dropna(subset=['Duración (minutos)'])

            if not actividades_finalizadas_tiempo.empty:
                # Calcular el tiempo promedio por técnico en minutos
                tiempo_promedio_por_tecnico = actividades_finalizadas_tiempo.groupby('Recurso')['Duración (minutos)'].mean().sort_values()

                # Formatear el tiempo promedio a horas y minutos
                ranking_tiempo_df = pd.DataFrame({
                    'Técnico': tiempo_promedio_por_tecnico.index,
                    'Tiempo Promedio': tiempo_promedio_por_tecnico.apply(
                        lambda x: f"{int(x // 60)} hrs {int(x % 60)} min" if pd.notna(x) else "Sin datos"
                    )
                })
                ranking_tiempo_df = ranking_tiempo_df.reset_index(drop=True)
                ranking_tiempo_df.index = ranking_tiempo_df.index + 1
                return ranking_tiempo_df
            else:
                return pd.DataFrame({'Técnico': [], 'Tiempo Promedio': []})
        else:
            return pd.DataFrame({'Técnico': [], 'Tiempo Promedio': []})

    ranking_tiempo_df = calcular_ranking_tiempo(data_combinada)
    if not ranking_tiempo_df.empty:
        st.dataframe(ranking_tiempo_df)
    else:
        st.info("No hay suficientes actividades finalizadas de instalación, reparación o postventa con tiempos válidos para calcular el ranking de tiempo promedio.")

        
        # --- Gráfico de Torta: Causa de la falla ---
    st.markdown("---")
    st.subheader("Distribución de Causas de la falla")
    columna_causa_falla = 'Causa de la falla'
    grafico_placeholder = st.empty()
    if columna_causa_falla in data_combinada.columns:
        causa_falla_counts = data_combinada[columna_causa_falla].value_counts().reset_index()
        causa_falla_counts.columns = ['Causa', 'Cantidad']
        if not causa_falla_counts.empty:
            fig_causa_falla = px.pie(causa_falla_counts, names='Causa', values='Cantidad', title='Porcentaje de Causas de la Falla')
            grafico_placeholder.plotly_chart(fig_causa_falla)
        else:
            grafico_placeholder.warning("No hay datos para mostrar.")
    else:
        grafico_placeholder.warning(f"La columna '{columna_causa_falla}' no se encontró en los datos.")
        
    # --- Sección Reincidencias y fallas tempranas ---
    analizar_reincidencias_y_fallas_tempranas(data_combinada)

    # --- Sección de Verificación de Ubicación ---
    st.markdown("---")
    verificacion_ubicacion.mostrar_verificacion_ubicacion(data_combinada.copy())

    # --- Nuevo KPI: Ranking de Técnicos WIFI-Design ---
    st.markdown("---")
    st.subheader("Ranking de Técnicos WIFI-Design")
    if 'Documento' in data_combinada.columns and 'Cod_Servicio' in data_combinada.columns and 'Recurso' in data_combinada.columns:
        wifi_design_df = data_combinada[
            data_combinada['Documento'].astype(str).str.match(r'^CS_\d+\.pdf', case=False)
        ].copy()
        
        # Contar la cantidad de WIFI-Design por técnico
        wifi_design_counts = wifi_design_df.groupby('Recurso')['Documento'].count().reset_index()
        wifi_design_counts.columns = ['Técnico', 'Cantidad WIFI-Design']
        
        # Contar la cantidad total de trabajos asignados por técnico
        trabajos_asignados = data_combinada.groupby('Recurso')['ID externo'].nunique().reset_index()
        trabajos_asignados.columns = ['Técnico', 'Trabajos Asignados']
        
        # Combinar los DataFrames
        ranking_wifi_design = pd.merge(wifi_design_counts, trabajos_asignados, on='Técnico', how='left').fillna(0)
        
        # Calcular el porcentaje de cumplimiento
        ranking_wifi_design['% Cumplimiento'] = ((ranking_wifi_design['Cantidad WIFI-Design'] / ranking_wifi_design['Trabajos Asignados']) * 100).round(2).astype(str) + '%'
        
        # Ordenar el ranking
        ranking_wifi_design = ranking_wifi_design.sort_values(by='Cantidad WIFI-Design', ascending=False).reset_index(drop=True)
        ranking_wifi_design.index = ranking_wifi_design.index + 1
        st.dataframe(ranking_wifi_design)
        
        # --- Desplegable de Detalle por Técnico ---
        st.subheader("Detalle de Trabajos WIFI-Design por Técnico")
        tecnicos_wifi_design = ranking_wifi_design['Técnico'].unique()
        opciones_tecnicos = ["Seleccione", "Todos"] + list(tecnicos_wifi_design)
        tecnico_seleccionado_wifi = st.selectbox("Seleccionar Técnico", opciones_tecnicos)
        columnas_base_detalle = ['Fecha Agendamiento', 'ID externo', 'Cod_Servicio', 'Propietario de Red', 'Dirección', 'Documento', 'Recurso']
        columnas_detalle_final = ['Fecha Agendamiento', 'ID externo', 'Cod_Servicio', 'WIFI-Design', 'Propietario de Red', 'Dirección', 'Técnico']
        
        def determinar_wifi_design(row):
            if pd.notna(row['Cod_Servicio']) or pd.notna(row['ID externo']):
                if pd.notna(row['Documento']) and re.match(r'^CS_\d+\.pdf', str(row['Documento']), re.IGNORECASE):
                    return 'SI'
                else:
                    return 'NO'
            else:
                return 'Sin Datos'

        if tecnico_seleccionado_wifi == "Todos":
            detalle_todos = data_combinada[columnas_base_detalle].copy()
            detalle_todos['WIFI-Design'] = detalle_todos.apply(determinar_wifi_design, axis=1)
            detalle_todos['Técnico'] = detalle_todos['Recurso']
            detalle_filtrado_sin_datos = detalle_todos[detalle_todos['WIFI-Design'] != 'Sin Datos'][columnas_detalle_final]
            if not detalle_filtrado_sin_datos.empty:
                st.dataframe(detalle_filtrado_sin_datos)
            else:
                st.info("No hay detalles de WIFI-Design para mostrar.")
        elif tecnico_seleccionado_wifi != "Seleccione" and tecnico_seleccionado_wifi:
            detalle_tecnico = data_combinada[data_combinada['Recurso'] == tecnico_seleccionado_wifi][columnas_base_detalle].copy()
            detalle_tecnico['WIFI-Design'] = detalle_tecnico.apply(determinar_wifi_design, axis=1)
            detalle_tecnico['Técnico'] = detalle_tecnico['Recurso']
            detalle_filtrado_tecnico = detalle_tecnico[detalle_tecnico['WIFI-Design'] != 'Sin Datos'][columnas_detalle_final]
            if not detalle_filtrado_tecnico.empty:
                st.dataframe(detalle_filtrado_tecnico)
            else:
                st.info(f"No hay detalles de WIFI-Design para el técnico '{tecnico_seleccionado_wifi}'.")
    else:
        st.warning("Las columnas 'Documento', 'Cod_Servicio' o 'Recurso' no se encontraron en los datos.")

    # --- Gráfico de Barras: Distribución de Trabajos por Comuna y Categoría de Actividad ---
    st.markdown("---")
    st.subheader("Distribución de Trabajos por Comuna y Categoría de Actividad")

    if 'Comuna' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns:
        # Filtrar los tipos de actividad que comienzan con las palabras clave
        actividades_filtradas = data_combinada[
            data_combinada['Tipo de actividad'].str.lower().str.startswith(('instalación', 'reparación', 'postventa'))
        ].copy()

        if not actividades_filtradas.empty:
            # Crear una columna para la categoría principal de actividad
            actividades_filtradas['Categoria_Actividad'] = actividades_filtradas['Tipo de actividad'].str.lower().str.split('-').str[0]

            # Calcular el total de cada categoría de actividad
            totales_por_categoria = actividades_filtradas['Categoria_Actividad'].value_counts().to_dict()

            # Verificar si hay al menos una comuna presente después del filtrado
            comunas_presentes = actividades_filtradas['Comuna'].nunique()

            if comunas_presentes > 0:
                # Agrupar por comuna y categoría de actividad, contando los trabajos
                distribucion_comunal = actividades_filtradas.groupby(['Comuna', 'Categoria_Actividad']).size().reset_index(name='Cantidad')

                if not distribucion_comunal.empty:
                    # Crear el gráfico de barras
                    fig = px.bar(
                        distribucion_comunal,
                        x='Comuna',
                        y='Cantidad',
                        color='Categoria_Actividad',
                        labels={'Cantidad': 'Cantidad de Trabajos', 'Comuna': 'Comuna', 'Categoria_Actividad': 'Tipo de Actividad'},
                        title='Distribución de Trabajos por Comuna y Categoría de Actividad'
                    )

                    # Modificar las etiquetas de la leyenda para incluir los totales
                    new_legend_names = {}
                    for trace in fig.data:
                        categoria = trace.name
                        total = totales_por_categoria.get(categoria.lower(), 0)
                        new_legend_names[trace.name] = f"{categoria} ({total})"

                    fig.for_each_trace(lambda t: t.update(name=new_legend_names[t.name],
                                                          legendgroup=new_legend_names[t.name],
                                                          hovertemplate=t.hovertemplate.replace(t.name, new_legend_names[t.name])))
                    st.plotly_chart(fig)
                else:
                    st.info("No hay datos de instalación, reparación o postventa agrupados por comuna.")
            else:
                st.info("No hay información de comunas para los tipos de actividad seleccionados.")
        else:
            st.info("No hay actividades de instalación, reparación o postventa en los datos.")
    else:
        st.warning("Las columnas 'Comuna' o 'Tipo de actividad' no se encontraron en los datos.")

    # --- Ranking de Comunas por Trabajos Finalizados con Totales y Efectividad (Lógica Específica para SIN ZONA) ---
    st.markdown("---")
    st.subheader("Ranking de Comunas Trabajos Finalizados)")

    actividades_a_excluir = ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']

    if 'Comuna' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns:
        # Filtrar los trabajos excluyendo actividades no operativas
        trabajos_filtrados = data_combinada[
            ~data_combinada['Tipo de actividad'].str.lower().isin(actividades_a_excluir)
        ].copy()

        # Calcular el total de trabajos asignados por comuna (sin actividades excluidas)
        total_asignados_por_comuna = trabajos_filtrados['Comuna'].value_counts().reset_index()
        total_asignados_por_comuna.columns = ['Comuna', 'Total Asignadas']

        # Filtrar solo los trabajos finalizados (sin actividades excluidas) y contar por comuna
        trabajos_finalizados_por_comuna = trabajos_filtrados[
            trabajos_filtrados['Estado de actividad'].str.lower() == 'finalizada'
        ].groupby('Comuna').size().reset_index(name='Total Finalizados')

        # Combinar los DataFrames
        ranking_completo = pd.merge(total_asignados_por_comuna, trabajos_finalizados_por_comuna, on='Comuna', how='left').fillna(0)

        # Lógica específica para SIN ZONA
        sin_zona_filtrado = data_combinada[
            (data_combinada['Comuna'].str.lower() == 'sin zona') &
            (data_combinada['Tipo de actividad'].str.lower().str.contains(r'reparación|instalación|postventa', regex=True)) &
            (~data_combinada['Tipo de actividad'].str.lower().isin(actividades_a_excluir))
        ]

        total_asignados_sin_zona = sin_zona_filtrado.groupby('Comuna').size().get('SIN ZONA', 0)
        total_finalizados_sin_zona = sin_zona_filtrado[sin_zona_filtrado['Estado de actividad'].str.lower() == 'finalizada'].groupby('Comuna').size().get('SIN ZONA', 0)

        if total_asignados_sin_zona > 0:
            sin_zona_ranking = pd.DataFrame({
                'Comuna': ['SIN ZONA'],
                'Total Asignadas': [total_asignados_sin_zona],
                'Total Finalizados': [total_finalizados_sin_zona]
            })
            sin_zona_ranking['% de Efectividad'] = (sin_zona_ranking['Total Finalizados'] / sin_zona_ranking['Total Asignadas'] * 100).round(2).astype(str) + '%'

            # Eliminar SIN ZONA del ranking general y luego agregar el ranking específico
            ranking_completo = ranking_completo[ranking_completo['Comuna'].str.lower() != 'sin zona']
            ranking_completo = pd.concat([ranking_completo, sin_zona_ranking], ignore_index=True)
        else:
            # Eliminar SIN ZONA del ranking general si no cumple la condición
            ranking_completo = ranking_completo[ranking_completo['Comuna'].str.lower() != 'sin zona']

        # Calcular el porcentaje de efectividad para el ranking general
        ranking_completo['% de Efectividad'] = (ranking_completo['Total Finalizados'] / ranking_completo['Total Asignadas'] * 100).round(2).astype(str) + '%'

        # Ordenar el ranking
        ranking_completo_ordenado = ranking_completo.sort_values(by='Total Finalizados', ascending=False).reset_index(drop=True)
        ranking_completo_ordenado.index = ranking_completo_ordenado.index + 1

        st.dataframe(ranking_completo_ordenado)
    else:
        st.warning("Las columnas necesarias ('Comuna', 'Estado de actividad', 'Tipo de actividad') no se encontraron en los datos.")

    # --- Ranking de Comunas por Trabajos de Instalación y Postventa (Excluyendo Actividades No Operativas) ---
    st.markdown("---")
    st.subheader("Ranking de Comunas Provision + Postventas)")

    actividades_a_excluir = ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']

    if 'Comuna' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns:
        # Filtrar trabajos de instalación y postventa excluyendo actividades no operativas
        instalacion_postventa_filtrado = data_combinada[
            (data_combinada['Tipo de actividad'].str.lower().str.contains(r'instalación|postventa', regex=True)) &
            (~data_combinada['Tipo de actividad'].str.lower().isin(actividades_a_excluir))
        ].copy()

        if not instalacion_postventa_filtrado.empty:
            # Calcular total asignados
            total_asignados_ip = instalacion_postventa_filtrado['Comuna'].value_counts().reset_index()
            total_asignados_ip.columns = ['Comuna', 'Total Asignadas (IP)']

            # Calcular total finalizados
            total_finalizados_ip = instalacion_postventa_filtrado[
                instalacion_postventa_filtrado['Estado de actividad'].str.lower() == 'finalizada'
            ].groupby('Comuna').size().reset_index(name='Total Finalizados (IP)')

            # Combinar y calcular efectividad
            ranking_ip = pd.merge(total_asignados_ip, total_finalizados_ip, on='Comuna', how='left').fillna(0)
            ranking_ip['% de Efectividad (IP)'] = (ranking_ip['Total Finalizados (IP)'] / ranking_ip['Total Asignadas (IP)'] * 100).round(2).astype(str) + '%'
            ranking_ip_ordenado = ranking_ip.sort_values(by='Total Finalizados (IP)', ascending=False).reset_index(drop=True)
            ranking_ip_ordenado.index = ranking_ip_ordenado.index + 1
            st.dataframe(ranking_ip_ordenado)
        else:
            st.info("No hay trabajos de Instalación o Postventa (excluyendo actividades no operativas) para mostrar en el ranking.")

        # --- Ranking de Comunas por Trabajos de Reparación (Excluyendo Actividades No Operativas) ---
        st.markdown("---")
        st.subheader("Ranking de Comunas Mantencion")

        # Filtrar trabajos de reparación excluyendo actividades no operativas
        reparacion_filtrado = data_combinada[
            (data_combinada['Tipo de actividad'].str.lower().str.contains(r'reparación', regex=True)) &
            (~data_combinada['Tipo de actividad'].str.lower().isin(actividades_a_excluir))
        ].copy()

        if not reparacion_filtrado.empty:
            # Calcular total asignados
            total_asignados_rep = reparacion_filtrado['Comuna'].value_counts().reset_index()
            total_asignados_rep.columns = ['Comuna', 'Total Asignadas (Rep)']

            # Calcular total finalizados
            total_finalizados_rep = reparacion_filtrado[
                reparacion_filtrado['Estado de actividad'].str.lower() == 'finalizada'
            ].groupby('Comuna').size().reset_index(name='Total Finalizados (Rep)')

            # Combinar y calcular efectividad
            ranking_rep = pd.merge(total_asignados_rep, total_finalizados_rep, on='Comuna', how='left').fillna(0)
            ranking_rep['% de Efectividad (Rep)'] = (ranking_rep['Total Finalizados (Rep)'] / ranking_rep['Total Asignadas (Rep)'] * 100).round(2).astype(str) + '%'
            ranking_rep_ordenado = ranking_rep.sort_values(by='Total Finalizados (Rep)', ascending=False).reset_index(drop=True)
            ranking_rep_ordenado.index = ranking_rep_ordenado.index + 1
            st.dataframe(ranking_rep_ordenado)
        else:
            st.info("No hay trabajos de Reparación (excluyendo actividades no operativas) para mostrar en el ranking.")
    else:
        st.warning("Las columnas necesarias ('Comuna', 'Estado de actividad', 'Tipo de actividad') no se encontraron en los datos.")

    # --- Resumen de Actividades Año 2023 ---
    st.markdown("---")
    st.subheader("Resumen de Actividades Año 2023 (Instalación + Reparación + Postventa)")
    if 'Fecha Agendamiento' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Recurso' in data_combinada.columns:
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
        data_2023 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2023].copy()
        if not data_2023.empty:
            # Filtrar las actividades por los tipos especificados
            actividades_2023 = data_2023[
                data_2023['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
            ].copy()

            if not actividades_2023.empty:
                año_2023 = 2023
                cantidad_tecnicos_2023 = actividades_2023['Recurso'].nunique()

                # Calcular la cantidad de actividades finalizadas
                actividades_finalizadas_2023 = actividades_2023[
                    actividades_2023['Estado de actividad'].str.lower() == 'finalizada'
                ]['ID externo'].nunique()

                # Calcular la cantidad de actividades no realizadas
                actividades_no_realizadas_2023 = actividades_2023[
                    actividades_2023['Estado de actividad'].str.lower() == 'no realizado'
                ]['ID externo'].nunique()

                # Calcular el total de actividades asignadas (finalizadas + no realizadas)
                total_actividades_asignadas_2023 = actividades_finalizadas_2023 + actividades_no_realizadas_2023

                resumen_2023 = pd.DataFrame({
                    'Año': [año_2023],
                    'Cantidad de Técnicos': [cantidad_tecnicos_2023],
                    'Total Actividades Asignadas': [total_actividades_asignadas_2023],
                    'Total Actividades Finalizadas': [actividades_finalizadas_2023]
                })
                st.dataframe(resumen_2023)
            else:
                st.info("No hay actividades de instalación, reparación o postventa para el año 2023.")
        else:
            st.info("No hay datos disponibles para el año 2023.")
    else:
        st.warning("Una o más de las columnas necesarias ('Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso') no se encontraron en los datos.")

    # --- Resumen de Actividades Año 2024 ---
    st.subheader("Resumen de Actividades Año 2024 (Instalación + Reparación + Postventa)")
    if 'Fecha Agendamiento' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Recurso' in data_combinada.columns:
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
        data_2024 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2024].copy()
        if not data_2024.empty:
            # Filtrar las actividades por los tipos especificados
            actividades_2024 = data_2024[
                data_2024['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
            ].copy()

            if not actividades_2024.empty:
                año_2024 = 2024
                cantidad_tecnicos_2024 = actividades_2024['Recurso'].nunique()

                # Calcular la cantidad de actividades finalizadas
                actividades_finalizadas_2024 = actividades_2024[
                    actividades_2024['Estado de actividad'].str.lower() == 'finalizada'
                ]['ID externo'].nunique()

                # Calcular la cantidad de actividades no realizadas
                actividades_no_realizadas_2024 = actividades_2024[
                    actividades_2024['Estado de actividad'].str.lower() == 'no realizado'
                ]['ID externo'].nunique()

                # Calcular el total de actividades asignadas (finalizadas + no realizadas)
                total_actividades_asignadas_2024 = actividades_finalizadas_2024 + actividades_no_realizadas_2024

                resumen_2024 = pd.DataFrame({
                    'Año': [año_2024],
                    'Cantidad de Técnicos': [cantidad_tecnicos_2024],
                    'Total Actividades Asignadas': [total_actividades_asignadas_2024],
                    'Total Actividades Finalizadas': [actividades_finalizadas_2024]
                })
                st.dataframe(resumen_2024)
            else:
                st.info("No hay actividades de instalación, reparación o postventa para el año 2024.")
        else:
            st.info("No hay datos disponibles para el año 2024.")
    else:
        st.warning("Una o más de las columnas necesarias ('Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso') no se encontraron en los datos.")

        #--Resumen año 2025
        st.subheader("Resumen de Actividades Año 2025 (Instalación + Reparación + Postventa)")
    if 'Fecha Agendamiento' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Recurso' in data_combinada.columns:
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
        data_2025 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()
        if not data_2025.empty:
            # Filtrar las actividades por los tipos especificados
            actividades_2025 = data_2025[
                data_2025['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
            ].copy()

            if not actividades_2025.empty:
                año_2025 = 2025
                cantidad_tecnicos_2025 = actividades_2025['Recurso'].nunique()

                # Calcular la cantidad de actividades finalizadas
                actividades_finalizadas_2025 = actividades_2025[
                    actividades_2025['Estado de actividad'].str.lower() == 'finalizada'
                ]['ID externo'].nunique()

                # Calcular la cantidad de actividades no realizadas
                actividades_no_realizadas_2025 = actividades_2025[
                    actividades_2025['Estado de actividad'].str.lower() == 'no realizado'
                ]['ID externo'].nunique()

                # Calcular el total de actividades asignadas (finalizadas + no realizadas)
                total_actividades_asignadas_2025 = actividades_finalizadas_2025 + actividades_no_realizadas_2025

                resumen_2025 = pd.DataFrame({
                    'Año': [año_2025],
                    'Cantidad de Técnicos': [cantidad_tecnicos_2025],
                    'Total Actividades Asignadas': [total_actividades_asignadas_2025],
                    'Total Actividades Finalizadas': [actividades_finalizadas_2025]
                })
                st.dataframe(resumen_2025)
            else:
                st.info("No hay actividades de instalación, reparación o postventa para el año 2025.")
        else:
            st.info("No hay datos disponibles para el año 2025.")
    else:
        st.warning("Una o más de las columnas necesarias ('Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso') no se encontraron en los datos.")

    # --- Gráficos de Mantención y Provisión ---
    st.markdown("---")
    st.subheader("Resumen de Actividades de Mantención y Provisión")
    resumen_general.mostrar_grafico_mantencion(data_combinada)
    resumen_general.mostrar_grafico_provision(data_combinada)



# Ruta del archivo GIF
gif_path = "Robertito_opt.gif"

# Leer el archivo GIF en binario y codificarlo en base64
with open(gif_path, "rb") as f:
    gif_bytes = f.read()
    encoded_gif = base64.b64encode(gif_bytes).decode("utf-8")

# Mostrar el GIF en la esquina superior izquierda
st.markdown(
    f"""
    <div style="position: fixed; top: 10px; left: 10px; z-index: 999;">
        <img src="data:image/gif;base64,{encoded_gif}" width="120">
    </div>
    """,
    unsafe_allow_html=True
)
