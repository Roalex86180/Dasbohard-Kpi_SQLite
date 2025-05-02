import streamlit as st
import pandas as pd
import re
import os
import sqlite3
from verificacion_ubicacion_sql import mostrar_verificacion_ubicacion_sql
import verificar_formato
import plotly.express as px
import resumen_general_sql
from Rt_Ft_Sql import analizar_reincidencias_y_fallas_tempranas
import base64
import plotly.graph_objects as go
import io

st.set_page_config(layout="wide")

# --- PARÁMETROS ---
carpeta_datos = "Data_diaria"
patron_archivo = r"Actividades-(RIELECOM - RM|MultiSkill \(Rielecom-3Play-RM\))(_|-)\d{2}_\d{2}_\d{2}( \(\d+\))?\.((xlsx)|(csv))"
db_path = "datos_actividades.db"

# --- FUNCIONES PARA SQLITE ---
@st.cache_data
def cargar_datos_en_sqlite(carpeta, patron, db_path='datos_actividades.db'):
    all_data = []
    try:
        for nombre_archivo in os.listdir(carpeta):
            if re.match(patron, nombre_archivo):
                ruta_archivo = os.path.join(carpeta, nombre_archivo)
                formato_correcto = True
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
                    except Exception as e:
                        st.error(f"Error al cargar el archivo '{nombre_archivo}': {e}")
                else:
                    st.error(f"Formato incorrecto: {mensaje_formato}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            # Crear una nueva conexión dentro de la función
            with sqlite3.connect(db_path) as conn:
                combined_df.to_sql('actividades', conn, if_exists='replace', index=False)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error general: {e}")
        return False

@st.cache_data
def obtener_datos_desde_sqlite(db_path='datos_actividades.db'):
    # Crear una nueva conexión dentro de la función
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM actividades", conn)
    return df


# --- CARGAR O CONSULTAR LOS DATOS ---
# Solo ejecutar esta línea si necesitas regenerar la base desde los archivos
#cargar_datos_en_sqlite(carpeta_datos, patron_archivo)

data_combinada = obtener_datos_desde_sqlite(db_path)


# --- CÁLCULO DE KPI ---
if data_combinada is not None:
    exclusiones = ['Almuerzo', 'Permiso', 'Reunion', 'Mantencion Vehicular', 'Curso', 'Levantamiento', 'Apoyo Terreno','Planta - Mantención']
    df_filtered = data_combinada[~data_combinada['Tipo de actividad'].str.lower().str.contains('|'.join(exclusiones).lower(), na=False)].copy()

    total_finalizadas = df_filtered[
        df_filtered['Estado de actividad'].str.lower() == 'finalizada'
    ][
        df_filtered['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
    ]['ID externo'].nunique()

    total_asignadas = df_filtered[
        df_filtered['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
    ][
        df_filtered['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
    ]['ID externo'].nunique()

    label_style = """
        <style>
            .label-container {
                display: flex;
                gap: 20px;
                align-items: center;
                margin-left: -300px;
                margin-top: -80px;
            }
            .label-box {
                background-color: #f0f2f6;
                border-radius: 5px;
                padding: 15px 20px;
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

    # --- CAMPO DE BÚSQUEDA DE CLIENTE ---
    st.markdown("---")
    st.subheader("Buscar Información de Cliente")
    termino_busqueda = st.text_input("Ingrese Nombre, RUT, ID Externo, Dirección, Ciudad, Comuna, Teléfono, Correo o Cod_Servicio:")
    columnas_a_buscar = ['Nombre Cliente', 'Rut Cliente', 'ID externo', 'Dirección', 'Ciudad', 'Comuna', 'Teléfono móvil', 'Correo electrónico', 'Cod_Servicio', 'Recurso']
    columnas_a_mostrar = ['Fecha Agendamiento','Recurso', 'ID externo','Nombre Cliente', 'Rut Cliente', 'Tipo de actividad','Observación' ,'Acción realizada','Tipo Cierre','Motivo','SR de Siebel', 'Dirección', 'Ciudad', 'Comuna', 'Tipo de Vivienda','Teléfono móvil', 'Correo electrónico','Diagnóstico','Tipo de Servicio (TS1/TS2)', 'Producto/Plan contratado', 'Plan de internet', 'Nombre del bundle', 'Pack de canales premium','Cantidad routers','Cantidad de STB','Propietario de Red','AccessID']

    if termino_busqueda:
        resultados_busqueda = pd.DataFrame()
        for columna in columnas_a_buscar:
            if columna in data_combinada.columns:
                resultados = data_combinada[data_combinada[columna].astype(str).str.contains(termino_busqueda, case=False, na=False, regex=False)]
                resultados_busqueda = pd.concat([resultados_busqueda, resultados], ignore_index=True).drop_duplicates()
                if not resultados_busqueda.empty:
                    break
            else:
                st.warning(f"La columna '{columna}' no se encontró en los datos.")
        if not resultados_busqueda.empty:
            columnas_existentes_a_mostrar = [col for col in columnas_a_mostrar if col in resultados_busqueda.columns]
            st.subheader("Resultados de la Búsqueda")
            st.dataframe(resultados_busqueda[columnas_existentes_a_mostrar])
        else:
            st.info("No se encontraron resultados para la búsqueda.")

           # --- Ranking de Técnicos Más Productivos ----
        st.markdown("---")
    st.subheader("Ranking Diario")

    # Asegúrate de que la columna 'Fecha Agendamiento' esté en formato datetime
    data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')

    # Selector de fecha
    fecha_seleccionada = st.date_input("Filtrar ranking por fecha", value=None)

    # Filtrar datos por fecha
    if fecha_seleccionada:
        data_filtrada = data_combinada[data_combinada['Fecha Agendamiento'].dt.date == fecha_seleccionada].copy()
    else:
        data_filtrada = data_combinada.copy()

    st.subheader("Ranking de Técnicos Multiskill")

    # Actividades a excluir
    excluir_actividades = [
        'Almuerzo', 'Espera INC nueva', 'Reunión', 'Reunion', 'Reparación CPE (Router, ONT, Modem)', 'Retiro Equipos', 'Levantamiento', 'Permiso Administrativo', 'Reparación Acceso Cobre', 
        'Mantención Vehicular', 'Apoyo Terreno', 'Inventario', 'Curso', 'Atención de Incidencia con visita técnica', 'Reparación Acceso Fibra', 'Reparación Terminal de Usuario',
    ]

    # ID de recurso a excluir
    ids_excluir = [3824, 3825, 3826, 3823, 3822, 5286, 4131, 5362]

    # Filtrar actividades válidas
    actividades_validas = data_filtrada[
        (~data_filtrada['Tipo de actividad'].isin(excluir_actividades)) &
        (~data_filtrada['ID de recurso'].isin(ids_excluir))
    ].copy()

    # Ranking por técnico
    total_asignadas_serie = actividades_validas['Recurso'].value_counts()
    ranking_asignadas_df = pd.DataFrame({'Técnico': total_asignadas_serie.index, 'Total Asignadas': total_asignadas_serie.values})

    actividades_finalizadas = actividades_validas[actividades_validas['Estado de actividad'].str.lower() == 'finalizada'].copy()
    productividad_ranking_serie = actividades_finalizadas['Recurso'].value_counts()
    productividad_ranking_df = pd.DataFrame({'Técnico': productividad_ranking_serie.index, 'Total Finalizadas': productividad_ranking_serie.values})

    # Agregar columna con tipos de actividad (en una misma línea separados por coma)
    tipos_por_tecnico = actividades_validas.groupby('Recurso')['Tipo de actividad'].apply(lambda x: ', '.join(sorted(set(x)))).reset_index()
    tipos_por_tecnico.columns = ['Técnico', 'Tipo de actividad']

    # Unir y calcular efectividad
    productividad_final_df = pd.merge(productividad_ranking_df, ranking_asignadas_df, on='Técnico', how='left')
    productividad_final_df = pd.merge(productividad_final_df, tipos_por_tecnico, on='Técnico', how='left')
    productividad_final_df['Porcentaje de Efectividad'] = (
        productividad_final_df['Total Finalizadas'] / productividad_final_df['Total Asignadas'] * 100
    ).round(2).fillna(0).astype(str) + '%'
    productividad_final_df = productividad_final_df.sort_values(by='Total Finalizadas', ascending=False).reset_index(drop=True)
    productividad_final_df.index = productividad_final_df.index + 1

    # Mostrar tabla
    st.dataframe(productividad_final_df)

    # Mostrar KPI de total de técnicos (ahora está debajo de la tabla)
    total_tecnicos = actividades_validas['Recurso'].nunique()
    if fecha_seleccionada:
        st.markdown(f"### 👷‍♂️ Total de Técnicos = {total_tecnicos} técnicos el {fecha_seleccionada.strftime('%d de %B %Y')}")
    else:
        st.markdown(f"### 👷‍♂️ Total de Técnicos = {total_tecnicos} técnicos (sin filtro de fecha)")

    # Mensaje informativo
    if fecha_seleccionada and productividad_final_df.empty:
        st.info(f"No hay datos de actividades para la fecha: {fecha_seleccionada.strftime('%Y-%m-%d')}")
    elif not fecha_seleccionada:
        st.info("Mostrando el ranking completo (sin filtro de fecha).")

    # --- Métricas de efectividad ---
    def calcular_metricas(df, palabras_clave, meta):
        if isinstance(palabras_clave, str):
            palabras_clave = [palabras_clave]
        filtro_tipo = df['Tipo de actividad'].str.contains('|'.join(palabras_clave), case=False, na=False)
        asignadas = df[filtro_tipo & df['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])].shape[0]
        finalizadas = df[filtro_tipo & (df['Estado de actividad'].str.lower() == 'finalizada')].shape[0]
        efectividad = (finalizadas / asignadas * 100) if asignadas > 0 else 0
        color = "normal" if efectividad >= meta else "inverse"
        return asignadas, finalizadas, efectividad, color

    # Calcular métricas con data_filtrada válida
    repa_asig, repa_fin, repa_eff, repa_color = calcular_metricas(actividades_validas, 'reparación', 90)
    inst_post_asig, inst_post_fin, inst_post_eff, inst_post_color = calcular_metricas(actividades_validas, ['instalación', 'postventa'], 80)

    multi_asig = repa_asig + inst_post_asig
    multi_fin = repa_fin + inst_post_fin
    multi_eff = (multi_fin / multi_asig * 100) if multi_asig > 0 else 0
    multi_color = "normal" if multi_eff >= 90 else "inverse"

    # Mostrar métricas
    if not data_filtrada.empty:
        st.subheader("📌 Métricas de Efectividad")

        # Multiskill
        st.markdown("**Multiskill**")
        cols_multi = st.columns(4)
        cols_multi[0].metric("Asignadas", multi_asig)
        cols_multi[1].metric("Finalizadas", multi_fin)
        cols_multi[2].metric("Efectividad", f"{multi_eff:.2f}%")

        # Reparación
        st.markdown("**Reparación**")
        cols_repa = st.columns(4)
        cols_repa[0].metric("Asignadas", repa_asig)
        cols_repa[1].metric("Finalizadas", repa_fin)
        cols_repa[2].metric("Efectividad", f"{repa_eff:.2f}%", delta="Meta: 90%", delta_color=repa_color)

        # Instalación + Postventa
        st.markdown("**Instalación + Postventa**")
        cols_inst = st.columns(4)
        cols_inst[0].metric("Asignadas", inst_post_asig)
        cols_inst[1].metric("Finalizadas", inst_post_fin)
        cols_inst[2].metric("Efectividad", f"{inst_post_eff:.2f}%", delta="Meta: 80%", delta_color=inst_post_color)

        
        #Grafico actividad por meses
        # Asegurar formato datetime y filtrar solo año 2025

        # Convertir fechas y generar columnas de mes
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')
        data_2025 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()

        # Mapeo y orden de meses en español
        meses_orden = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        data_2025['Mes_Num'] = data_2025['Fecha Agendamiento'].dt.month
        data_2025['Mes'] = data_2025['Mes_Num'].map(meses_orden)
        orden_meses = list(meses_orden.values())

        # Función para calcular los datos mensuales
        def datos_mensuales(df, tipo):
            if tipo == "instalación":
                filtro = df['Tipo de actividad'].str.contains('instalación|postventa', case=False, na=False)
            elif tipo == "reparación":
                filtro = df['Tipo de actividad'].str.contains('reparación', case=False, na=False)
            elif tipo == "multiskill":
                filtro = df['Tipo de actividad'].str.contains('instalación|postventa|reparación', case=False, na=False)
            else:
                return pd.DataFrame()

            df_filtrado = df[filtro].copy()
            df_filtrado['Finalizada'] = df_filtrado['Estado de actividad'].str.lower() == 'finalizada'
            df_filtrado['Asignada'] = df_filtrado['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])

            df_grouped = df_filtrado.groupby('Mes').agg(
                Finalizadas=('Finalizada', 'sum'),
                Asignadas=('Asignada', 'sum')
            ).reindex(orden_meses).fillna(0).astype(int)

            df_grouped['Productividad'] = (
                df_grouped['Finalizadas'] / df_grouped['Asignadas'].replace(0, pd.NA) * 100
            ).round(2).fillna(0)

            return df_grouped.reset_index()

        # Función para graficar las actividades
        def graficar(df, titulo):
            fig = go.Figure()
            
            # Barras apiladas
            fig.add_trace(go.Bar(
                x=df['Mes'], y=df['Asignadas'], name='Asignadas',
                marker_color='#AED6F1'  # azul clarito
            ))
            
            fig.add_trace(go.Bar(
                x=df['Mes'], y=df['Finalizadas'], name='Finalizadas',
                marker_color='#3498DB'  # Azul actual
            ))

            # Etiquetas de productividad sobre la barra
            for i, row in df.iterrows():
                altura_total = row['Asignadas'] + row['Finalizadas']
                fig.add_annotation(
                    x=row['Mes'],
                    y=altura_total + 20,
                    text=f"{row['Productividad']:.1f}%",
                    showarrow=False,
                    font=dict(size=20, color='black')
                )

            fig.update_layout(
                barmode='stack',
                title=titulo,
                xaxis_title='Mes',
                yaxis_title='Cantidad de Actividades',
                legend_title='Estado',
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=400
            )
            
            return fig

        # Generar DataFrames por tipo de actividad
        multi_df = datos_mensuales(data_2025, "multiskill")
        repa_df = datos_mensuales(data_2025, "reparación")
        inst_df = datos_mensuales(data_2025, "instalación")

        # Mostrar en la app de Streamlit
        st.subheader("📊 Gráfico de Actividades Mensuales (2025)")
        st.plotly_chart(graficar(multi_df, "Multiskill (Reparación + Instalación + Postventa)"), use_container_width=True)
        st.plotly_chart(graficar(repa_df, "Reparación"), use_container_width=True)
        st.plotly_chart(graficar(inst_df, "Instalación + Postventa"), use_container_width=True)


        #Tecnicos promedios pormes
        # Crear mapeo y orden de meses
        # Mapeo y orden de meses en español (mantener al inicio)
        meses_orden = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        orden_meses = list(meses_orden.values())

        # Asegurar datetime y filtrar 2025
        # Asegurar datetime y filtrar por año 2025
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')
        data_2025 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()

        # Aplicar filtros de exclusión
        excluir_estados = [
            'Reparación CPE (Router, ONT, Modem)',
            'Atención de Incidencia con visita técnica',
            'Reparación Acceso Cobre',
            'Reparación Acceso Fibra',
            'Reparación Terminal de Usuario'
        ]
        ids_excluir = [3824, 3825, 3826, 3823, 3822, 5286, 4131, 5362]

        data_2025_filtrada = data_2025[
            (~data_2025['Estado de actividad'].isin(excluir_estados)) &
            (~data_2025['ID de recurso'].isin(ids_excluir))
        ].copy()

        # Generar columnas auxiliares para mes y fecha
        data_2025_filtrada['Fecha'] = data_2025_filtrada['Fecha Agendamiento'].dt.date
        data_2025_filtrada['Mes_Num'] = data_2025_filtrada['Fecha Agendamiento'].dt.month
        data_2025_filtrada['Mes'] = data_2025_filtrada['Mes_Num'].map(meses_orden)

        # Agrupación por día para gráfico
        tecnicos_por_dia = data_2025_filtrada.groupby(['Fecha']).agg(
            Tecnicos_Unicos=('Recurso', 'nunique'),
            Mes_Num=('Mes_Num', 'first'),
            Mes=('Mes', 'first')
        ).reset_index()

        promedio_tecnicos_final = (
            tecnicos_por_dia
            .groupby(['Mes_Num', 'Mes'])
            .agg(Promedio_Tecnicos_Diario=('Tecnicos_Unicos', 'mean'))
            .round(2)
            .reset_index()
            .sort_values('Mes_Num')
            .set_index('Mes')
            .reindex(orden_meses)
            .drop(columns='Mes_Num')
        )

        # Mostrar gráfico en Streamlit
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=promedio_tecnicos_final.index,
            y=promedio_tecnicos_final['Promedio_Tecnicos_Diario'],
            name='Promedio Diario de Técnicos',
            marker_color='#F5B041'
        ))

        for i, row in promedio_tecnicos_final.reset_index().iterrows():
            fig.add_annotation(
                x=row['Mes'],
                y=row['Promedio_Tecnicos_Diario'] + 5,
                text=f"{row['Promedio_Tecnicos_Diario']:.1f}",
                showarrow=False,
                font=dict(size=18, color='black')
            )

        fig.update_layout(
            title="📈 Promedio Diario de Técnicos por Mes (2025)",
            xaxis_title="Mes",
            yaxis_title="Promedio de Técnicos por Día",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )

        # Mostrar gráfico
        st.subheader("👷 Promedio Diario de Técnicos por Mes (2025)")
        st.plotly_chart(fig, use_container_width=True)

        # --- EXCEL CON TÉCNICOS POR DÍA ---
       # Crear un Excel con una hoja por mes: cada hoja muestra técnicos por día
        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            for mes_num, mes_nombre in meses_orden.items():
                # Filtrar por mes
                data_mes = data_2025_filtrada[data_2025_filtrada['Mes_Num'] == mes_num].copy()
                if data_mes.empty:
                    continue

                # Preparar columnas necesarias
                data_mes['Fecha_str'] = data_mes['Fecha Agendamiento'].dt.strftime('%d/%m/%Y')
                data_mes['ID Recurso y Nombre'] = data_mes['ID de recurso'].astype(str) + ' ' + data_mes['Recurso']

                # Crear tabla dinámica
                pivot_mes = data_mes.pivot_table(
                    index='ID Recurso y Nombre',
                    columns='Fecha_str',
                    values='Recurso',
                    aggfunc='first',
                    fill_value=''
                )

                # Agregar columna de total (días trabajados en ese mes)
                pivot_mes['Días trabajados'] = (pivot_mes != '').sum(axis=1)

                # Agregar fila de cantidad de técnicos por día
                cantidad_por_dia = (pivot_mes != '').sum(axis=0)
                pivot_mes.loc['Cantidad de Técnicos'] = cantidad_por_dia

                # Ordenar columnas por fecha
                columnas_fechas = [col for col in pivot_mes.columns if col != 'Días trabajados']
                columnas_ordenadas = sorted(columnas_fechas, key=lambda x: pd.to_datetime(x, dayfirst=True))
                pivot_mes = pivot_mes[columnas_ordenadas + ['Días trabajados']]

                # Escribir en hoja del mes
                pivot_mes.to_excel(writer, sheet_name=mes_nombre)

        # Botón para descargar
        st.download_button(
            label="📥 Descargar Excel con hojas por mes",
            data=excel_buffer.getvalue(),
            file_name="tecnicos_por_dia_por_mes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


        # --- Técnicos que mencionan U2000 ---
        st.markdown("---")
        st.subheader("Técnicos que Realizan U2000")

        # Crear un selector de mes
        meses_orden = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        meses = ['Selecciona'] + list(meses_orden.values())

        # Agregar un selector de mes
        mes_seleccionado = st.selectbox("Selecciona un mes:", meses)

        # Filtrar la data según el mes seleccionado
        if mes_seleccionado != 'Selecciona':
            mes_num = list(meses_orden.keys())[list(meses_orden.values()).index(mes_seleccionado)]
            data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')
            data_filtrada_por_mes = data_combinada[data_combinada['Fecha Agendamiento'].dt.month == mes_num]
        else:
            data_filtrada_por_mes = data_combinada.copy()

        # Crear un selector de día
        dias_del_mes = sorted(data_filtrada_por_mes['Fecha Agendamiento'].dt.day.unique())
        dias_del_mes = ['Selecciona'] + dias_del_mes  # Agregar opción de 'Selecciona' al principio
        dia_seleccionado = st.selectbox("Selecciona un día:", dias_del_mes)

        # Filtrar la data según el día seleccionado
        if dia_seleccionado != 'Selecciona':
            data_filtrada_por_dia = data_filtrada_por_mes[data_filtrada_por_mes['Fecha Agendamiento'].dt.day == dia_seleccionado]
        else:
            data_filtrada_por_dia = data_filtrada_por_mes.copy()

        # Filtrar menciones de "u2000", "u 2000", "u200", etc., sin importar mayúsculas/minúsculas
        u2000_mentions = data_filtrada_por_dia[
            data_filtrada_por_dia['Observación'].str.contains(r'u\s?2000|u\s?200|u200', flags=re.IGNORECASE, na=False)
        ].copy()

        # Mostrar ranking si hay resultados
        if not u2000_mentions.empty:
            u2000_ranking_serie = u2000_mentions['Recurso'].value_counts()
            u2000_ranking_df = pd.DataFrame({
                'Técnico': u2000_ranking_serie.index,
                'Cantidad U2000': u2000_ranking_serie.values
            })
            u2000_ranking_df.index = u2000_ranking_df.index + 1
            st.dataframe(u2000_ranking_df)
        else:
            st.info("Ningún técnico ha mencionado 'u2000' en las observaciones.")

        # --- Ranking de Técnicos Más Rápidos (Tiempo Promedio) ---
        st.markdown("---")
        st.subheader("Ranking de Técnicos Más Rápidos (Tiempo Promedio por Trabajo Finalizado en Horas)")

        # Crear un selector de mes
        meses_orden = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        meses = ['Selecciona'] + list(meses_orden.values())

        # Agregar un selector de mes con un key único
        mes_seleccionado = st.selectbox("Selecciona un mes:", meses, key="mes_selector")

        # Filtrar la data según el mes seleccionado
        if mes_seleccionado != 'Selecciona':
            mes_num = list(meses_orden.keys())[list(meses_orden.values()).index(mes_seleccionado)]
            data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')
            data_filtrada_por_mes = data_combinada[data_combinada['Fecha Agendamiento'].dt.month == mes_num]
        else:
            data_filtrada_por_mes = data_combinada.copy()

        # Crear un selector de día
        dias_del_mes = sorted(data_filtrada_por_mes['Fecha Agendamiento'].dt.day.unique())
        dias_del_mes = ['Selecciona'] + dias_del_mes  # Agregar opción de 'Selecciona' al principio
        dia_seleccionado = st.selectbox("Selecciona un día:", dias_del_mes, key="dia_selector")

        # Filtrar la data según el día seleccionado
        if dia_seleccionado != 'Selecciona':
            data_filtrada_por_dia = data_filtrada_por_mes[data_filtrada_por_mes['Fecha Agendamiento'].dt.day == dia_seleccionado]
        else:
            data_filtrada_por_dia = data_filtrada_por_mes.copy()

        @st.cache_data
        def calcular_ranking_tiempo(df):
            """Calcula el ranking de técnicos más rápidos basado en el tiempo promedio
            de trabajos de instalación, reparación o postventa finalizados.
            """
            # Filtrar por tipos de actividad relevantes
            actividades_filtradas = df[
                df['Tipo de actividad'].astype(str).str.contains(
                    r'instalaci[oó]n|reparaci[oó]n|postventa',
                    case=False,
                    regex=True,
                    na=False
                )
            ].copy()

            # Filtrar por actividades finalizadas con duración válida
            actividades_finalizadas = actividades_filtradas[
                (actividades_filtradas['Estado de actividad'].str.lower() == 'finalizada') & 
                (actividades_filtradas['Duración'] != '00:00') & 
                (pd.notna(actividades_filtradas['Duración']))
            ].copy()

            if actividades_finalizadas.empty:
                return pd.DataFrame({'Técnico': [], 'Tiempo Promedio': []})

            # Convertir duración HH:MM a minutos
            def tiempo_a_minutos(tiempo_str):
                try:
                    horas, minutos = map(int, tiempo_str.split(':'))
                    return horas * 60 + minutos
                except:
                    return None

            actividades_finalizadas = actividades_finalizadas.assign(
                duracion_min=actividades_finalizadas['Duración'].apply(tiempo_a_minutos)
            ).dropna(subset=['duracion_min'])

            if actividades_finalizadas.empty:
                return pd.DataFrame({'Técnico': [], 'Tiempo Promedio': []})

            # Calcular promedio por técnico
            promedio_por_tecnico = actividades_finalizadas.groupby('Recurso')['duracion_min'].mean().sort_values()

            # Armar el DataFrame final
            ranking_df = pd.DataFrame({
                'Técnico': promedio_por_tecnico.index,
                'Tiempo Promedio': promedio_por_tecnico.apply(
                    lambda x: f"{int(x // 60)} hrs {int(x % 60)} min" if pd.notna(x) else "Sin datos"
                )
            }).reset_index(drop=True)

            ranking_df.index = ranking_df.index + 1
            return ranking_df

        # Mostrar ranking en la app
        ranking_tiempo_df = calcular_ranking_tiempo(data_filtrada_por_dia)
        if not ranking_tiempo_df.empty:
            st.dataframe(ranking_tiempo_df)
        else:
            st.info("No hay suficientes actividades finalizadas de instalación, reparación o postventa con tiempos válidos para calcular el ranking de tiempo promedio.")

      
        # --- Gráfico de Torta: Causa de la falla ---
        st.markdown("---")
        st.subheader("Distribución de Causas de la Falla")

        columna_causa_falla = 'Causa de la falla'
        grafico_placeholder = st.empty()

        if columna_causa_falla in data_combinada.columns:
            # Eliminar valores nulos y contar ocurrencias
            causa_falla_counts_total = data_combinada[columna_causa_falla].dropna().value_counts()
            
            # Separar top 10 causas
            top_10 = causa_falla_counts_total.head(10)
            otras = causa_falla_counts_total[10:]
            
            # Crear DataFrame con "Otras" sumadas
            causa_falla_counts = top_10.copy()
            if not otras.empty:
                causa_falla_counts["Otras"] = otras.sum()
            causa_falla_counts = causa_falla_counts.reset_index()
            causa_falla_counts.columns = ['Causa', 'Cantidad']

            if not causa_falla_counts.empty:
                fig_causa_falla = px.pie(
                    causa_falla_counts,
                    names='Causa',
                    values='Cantidad',
                    title='Distribución de Causas de la Falla (Top 10 + Otras)',
                    hole=0.3
                )
                fig_causa_falla.update_traces(textinfo='percent+label')
                grafico_placeholder.plotly_chart(fig_causa_falla)
            else:
                grafico_placeholder.warning("No hay datos válidos para mostrar en la columna 'Causa de la falla'.")
        else:
            grafico_placeholder.warning(f"La columna '{columna_causa_falla}' no se encontró en los datos.")

    # --- Sección Reincidencias y fallas tempranas ---
    analizar_reincidencias_y_fallas_tempranas()

    # --- Sección de Verificación de Ubicación ---
    st.markdown("---")
    conn = sqlite3.connect("datos_actividades.db")
    mostrar_verificacion_ubicacion_sql(conn)

    # Conectar a la base de datos SQLite
    conn = sqlite3.connect('datos_actividades.db')  # Asegúrate de que el nombre del archivo es correcto
    cursor = conn.cursor()

    # --- Nuevo KPI: Ranking de Técnicos WIFI-Design desde SQLite ---
    st.markdown("---")
    st.subheader("Ranking de Técnicos WIFI-Design")

    # Leer los datos desde la tabla 'actividades'
    query = """
    SELECT Recurso, Documento, Cod_Servicio, "ID externo", "Fecha Agendamiento", 
        "Propietario de Red", Dirección
    FROM actividades;
    """
    df = pd.read_sql(query, conn)

    # Verifica que las columnas existen
    if 'Documento' in df.columns and 'Cod_Servicio' in df.columns and 'Recurso' in df.columns:

        # Filtrar los que cumplen con el patrón de WIFI-Design
        wifi_design_df = df[
            df['Documento'].astype(str).str.match(r'^CS_\d+\.pdf', case=False)
        ].copy()

        # Contar cantidad de WIFI-Design por técnico
        wifi_design_counts = wifi_design_df.groupby('Recurso')['Documento'].count().reset_index()
        wifi_design_counts.columns = ['Técnico', 'Cantidad WIFI-Design']

        # Total de trabajos por técnico
        trabajos_asignados = df.groupby('Recurso')['ID externo'].nunique().reset_index()
        trabajos_asignados.columns = ['Técnico', 'Trabajos Asignados']

        # Combinar y calcular porcentaje
        ranking_wifi_design = pd.merge(wifi_design_counts, trabajos_asignados, on='Técnico', how='left').fillna(0)
        ranking_wifi_design['% Cumplimiento'] = (
            (ranking_wifi_design['Cantidad WIFI-Design'] / ranking_wifi_design['Trabajos Asignados']) * 100
        ).round(2).astype(str) + '%'

        # Ordenar
        ranking_wifi_design = ranking_wifi_design.sort_values(by='Cantidad WIFI-Design', ascending=False).reset_index(drop=True)
        ranking_wifi_design.index += 1
        st.dataframe(ranking_wifi_design)

        # --- Detalle por Técnico ---
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
            detalle_todos = df[columnas_base_detalle].copy()
            detalle_todos['WIFI-Design'] = detalle_todos.apply(determinar_wifi_design, axis=1)
            detalle_todos['Técnico'] = detalle_todos['Recurso']
            detalle_filtrado_sin_datos = detalle_todos[detalle_todos['WIFI-Design'] != 'Sin Datos'][columnas_detalle_final]
            if not detalle_filtrado_sin_datos.empty:
                st.dataframe(detalle_filtrado_sin_datos)
            else:
                st.info("No hay detalles de WIFI-Design para mostrar.")
        elif tecnico_seleccionado_wifi != "Seleccione":
            detalle_tecnico = df[df['Recurso'] == tecnico_seleccionado_wifi][columnas_base_detalle].copy()
            detalle_tecnico['WIFI-Design'] = detalle_tecnico.apply(determinar_wifi_design, axis=1)
            detalle_tecnico['Técnico'] = detalle_tecnico['Recurso']
            detalle_filtrado_tecnico = detalle_tecnico[detalle_tecnico['WIFI-Design'] != 'Sin Datos'][columnas_detalle_final]
            if not detalle_filtrado_tecnico.empty:
                st.dataframe(detalle_filtrado_tecnico)
            else:
                st.info(f"No hay detalles de WIFI-Design para el técnico '{tecnico_seleccionado_wifi}'.")
    else:
        st.warning("Las columnas 'Documento', 'Cod_Servicio' o 'Recurso' no se encontraron en los datos.")

        
        # --- Gráfico de Barras: Distribución de Trabajos por Comuna y Categoría de Actividad desde SQLite ---
    st.markdown("---")
    st.subheader("Distribución de Trabajos por Comuna y Categoría de Actividad")

    # Verificamos si las columnas existen en la tabla
    columnas_activas = pd.read_sql("PRAGMA table_info(actividades);", conn)['name'].tolist()
    if 'Comuna' in columnas_activas and 'Tipo de actividad' in columnas_activas:

        # Traer solo columnas necesarias
        query = """
        SELECT Comuna, "Tipo de actividad"
        FROM actividades
        WHERE LOWER("Tipo de actividad") LIKE 'instalación%' 
        OR LOWER("Tipo de actividad") LIKE 'reparación%' 
        OR LOWER("Tipo de actividad") LIKE 'postventa%';
        """
        actividades_filtradas = pd.read_sql(query, conn)

        if not actividades_filtradas.empty:
            # Extraer la categoría principal (instalación, reparación, postventa)
            actividades_filtradas['Categoria_Actividad'] = actividades_filtradas['Tipo de actividad'].str.lower().str.split('-').str[0]

            # Totales por categoría (para la leyenda del gráfico)
            totales_por_categoria = actividades_filtradas['Categoria_Actividad'].value_counts().to_dict()

            # Verificar si hay comunas
            if actividades_filtradas['Comuna'].nunique() > 0:
                distribucion_comunal = (
                    actividades_filtradas
                    .groupby(['Comuna', 'Categoria_Actividad'])
                    .size()
                    .reset_index(name='Cantidad')
                )

                if not distribucion_comunal.empty:
                    fig = px.bar(
                        distribucion_comunal,
                        x='Comuna',
                        y='Cantidad',
                        color='Categoria_Actividad',
                        labels={'Cantidad': 'Cantidad de Trabajos', 'Comuna': 'Comuna', 'Categoria_Actividad': 'Tipo de Actividad'},
                        title='Distribución de Trabajos por Comuna y Categoría de Actividad'
                    )

                    # Actualizar leyenda con totales
                    new_legend_names = {
                        trace.name: f"{trace.name} ({totales_por_categoria.get(trace.name.lower(), 0)})"
                        for trace in fig.data
                    }

                    fig.for_each_trace(lambda t: t.update(
                        name=new_legend_names[t.name],
                        legendgroup=new_legend_names[t.name],
                        hovertemplate=t.hovertemplate.replace(t.name, new_legend_names[t.name])
                    ))

                    st.plotly_chart(fig)
                else:
                    st.info("No hay datos agrupados por comuna y tipo de actividad.")
            else:
                st.info("No hay información de comunas para los tipos de actividad seleccionados.")
        else:
            st.info("No hay actividades de instalación, reparación o postventa en los datos.")
    else:
        st.warning("Las columnas 'Comuna' o 'Tipo de actividad' no se encontraron en la base de datos.")


        # --- Ranking de Comunas por Trabajos Finalizados con Totales y Efectividad ---
    st.markdown("---")
    st.subheader("Ranking de Comunas Trabajos Multiskill Finalizados")

    actividades_a_excluir = ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']

    # Verificar columnas
    columnas = pd.read_sql("PRAGMA table_info(actividades);", conn)['name'].tolist()
    if all(col in columnas for col in ['Comuna', 'Estado de actividad', 'Tipo de actividad']):

        # Filtrar trabajos excluyendo actividades no operativas
        query_filtrados = f"""
            SELECT Comuna, "Estado de actividad", "Tipo de actividad"
            FROM actividades
            WHERE LOWER("Tipo de actividad") NOT IN ({','.join(['?']*len(actividades_a_excluir))})
        """
        trabajos_filtrados = pd.read_sql(query_filtrados, conn, params=actividades_a_excluir)

        # Total asignados por comuna
        total_asignados = trabajos_filtrados['Comuna'].value_counts().reset_index()
        total_asignados.columns = ['Comuna', 'Total Asignadas']

        # Total finalizados por comuna
        finalizados = trabajos_filtrados[trabajos_filtrados['Estado de actividad'].str.lower() == 'finalizada']
        total_finalizados = finalizados.groupby('Comuna').size().reset_index(name='Total Finalizados')

        # Unir ambos
        ranking = pd.merge(total_asignados, total_finalizados, on='Comuna', how='left').fillna(0)

        # --- Tratamiento especial para SIN ZONA ---
        query_sin_zona = f"""
            SELECT Comuna, "Estado de actividad", "Tipo de actividad"
            FROM actividades
            WHERE LOWER(Comuna) = 'sin zona'
            AND (
                    LOWER("Tipo de actividad") LIKE 'reparación%' OR 
                    LOWER("Tipo de actividad") LIKE 'instalación%' OR 
                    LOWER("Tipo de actividad") LIKE 'postventa%'
            )
            AND LOWER("Tipo de actividad") NOT IN ({','.join(['?']*len(actividades_a_excluir))})
        """
        sin_zona_df = pd.read_sql(query_sin_zona, conn, params=actividades_a_excluir)

        total_asignados_sin_zona = len(sin_zona_df)
        total_finalizados_sin_zona = len(sin_zona_df[sin_zona_df['Estado de actividad'].str.lower() == 'finalizada'])

        if total_asignados_sin_zona > 0:
            sin_zona_ranking = pd.DataFrame({
                'Comuna': ['SIN ZONA'],
                'Total Asignadas': [total_asignados_sin_zona],
                'Total Finalizados': [total_finalizados_sin_zona]
            })
            sin_zona_ranking['% de Efectividad'] = (sin_zona_ranking['Total Finalizados'] / sin_zona_ranking['Total Asignadas'] * 100).round(2).astype(str) + '%'

            # Eliminar cualquier 'sin zona' anterior y agregar el correcto
            ranking = ranking[ranking['Comuna'].str.lower() != 'sin zona']
            ranking = pd.concat([ranking, sin_zona_ranking], ignore_index=True)
        else:
            ranking = ranking[ranking['Comuna'].str.lower() != 'sin zona']

        # Calcular % de efectividad
        ranking['% de Efectividad'] = (ranking['Total Finalizados'] / ranking['Total Asignadas'] * 100).round(2).astype(str) + '%'

        # Ordenar por finalizados
        ranking_ordenado = ranking.sort_values(by='Total Finalizados', ascending=False).reset_index(drop=True)
        ranking_ordenado.index = ranking_ordenado.index + 1

        st.dataframe(ranking_ordenado)

    else:
        st.warning("Las columnas necesarias ('Comuna', 'Estado de actividad', 'Tipo de actividad') no se encontraron en la base de datos.")


        # --- Ranking de Comunas por Trabajos de Instalación y Postventa ---
    st.markdown("---")
    st.subheader("Ranking de Comunas Provision + Postventas")

    actividades_a_excluir = ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']

    if 'Comuna' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns:
        # --- INSTALACIÓN Y POSTVENTA ---
        instalacion_postventa_filtrado = data_combinada[
            data_combinada['Tipo de actividad'].str.lower().str.contains(r'instalación|postventa', regex=True) &
            ~data_combinada['Tipo de actividad'].str.lower().isin(actividades_a_excluir)
        ].copy()

        if not instalacion_postventa_filtrado.empty:
            total_asignados_ip = instalacion_postventa_filtrado['Comuna'].value_counts().reset_index()
            total_asignados_ip.columns = ['Comuna', 'Total Asignadas (IP)']

            total_finalizados_ip = instalacion_postventa_filtrado[
                instalacion_postventa_filtrado['Estado de actividad'].str.lower() == 'finalizada'
            ].groupby('Comuna').size().reset_index(name='Total Finalizados (IP)')

            ranking_ip = pd.merge(total_asignados_ip, total_finalizados_ip, on='Comuna', how='left').fillna(0)
            ranking_ip['% de Efectividad (IP)'] = (ranking_ip['Total Finalizados (IP)'] / ranking_ip['Total Asignadas (IP)'] * 100).round(2).astype(str) + '%'
            ranking_ip_ordenado = ranking_ip.sort_values(by='Total Finalizados (IP)', ascending=False).reset_index(drop=True)
            ranking_ip_ordenado.index = ranking_ip_ordenado.index + 1
            st.dataframe(ranking_ip_ordenado)
        else:
            st.info("No hay trabajos de Instalación o Postventa (excluyendo actividades no operativas) para mostrar en el ranking.")

        # --- REPARACIÓN ---
        st.markdown("---")
        st.subheader("Ranking de Comunas Mantencion")

        reparacion_filtrado = data_combinada[
            data_combinada['Tipo de actividad'].str.lower().str.contains(r'reparación', regex=True) &
            ~data_combinada['Tipo de actividad'].str.lower().isin(actividades_a_excluir)
        ].copy()

        if not reparacion_filtrado.empty:
            total_asignados_rep = reparacion_filtrado['Comuna'].value_counts().reset_index()
            total_asignados_rep.columns = ['Comuna', 'Total Asignadas (Rep)']

            total_finalizados_rep = reparacion_filtrado[
                reparacion_filtrado['Estado de actividad'].str.lower() == 'finalizada'
            ].groupby('Comuna').size().reset_index(name='Total Finalizados (Rep)')

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

    # Verificación de columnas necesarias
    columnas_necesarias = ['Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo']
    if all(col in data_combinada.columns for col in columnas_necesarias):
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
        data_2023 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2023].copy()

        if not data_2023.empty:
            # Filtrar actividades de interés
            actividades_2023 = data_2023[
                data_2023['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
            ].copy()

            if not actividades_2023.empty:
                resumen_2023 = pd.DataFrame({
                    'Año': [2023],
                    'Cantidad de Técnicos': [actividades_2023['Recurso'].nunique()],
                    'Total Actividades Asignadas': [
                        actividades_2023[
                            actividades_2023['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
                        ]['ID externo'].nunique()
                    ],
                    'Total Actividades Finalizadas': [
                        actividades_2023[
                            actividades_2023['Estado de actividad'].str.lower() == 'finalizada'
                        ]['ID externo'].nunique()
                    ]
                })

                st.dataframe(resumen_2023)
            else:
                st.info("No hay actividades de instalación, reparación o postventa para el año 2023.")
        else:
            st.info("No hay datos disponibles para el año 2023.")
    else:
        st.warning("Una o más de las columnas necesarias no se encontraron en los datos: 'Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo'.")


        # --- Resumen de Actividades Año 2024 ---
    st.subheader("Resumen de Actividades Año 2024 (Instalación + Reparación + Postventa)")

    # Verificación de columnas necesarias
    columnas_necesarias = ['Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo']
    if all(col in data_combinada.columns for col in columnas_necesarias):
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
        data_2024 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2024].copy()

        if not data_2024.empty:
            # Filtrar actividades de interés
            actividades_2024 = data_2024[
                data_2024['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
            ].copy()

            if not actividades_2024.empty:
                resumen_2024 = pd.DataFrame({
                    'Año': [2024],
                    'Cantidad de Técnicos': [actividades_2024['Recurso'].nunique()],
                    'Total Actividades Asignadas': [
                        actividades_2024[
                            actividades_2024['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
                        ]['ID externo'].nunique()
                    ],
                    'Total Actividades Finalizadas': [
                        actividades_2024[
                            actividades_2024['Estado de actividad'].str.lower() == 'finalizada'
                        ]['ID externo'].nunique()
                    ]
                })

                st.dataframe(resumen_2024)
            else:
                st.info("No hay actividades de instalación, reparación o postventa para el año 2024.")
        else:
            st.info("No hay datos disponibles para el año 2024.")
    else:
        st.warning("Una o más de las columnas necesarias no se encontraron en los datos: 'Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo'.")


        # -- Resumen Año 2025
    st.subheader("Resumen de Actividades Año 2025 (Instalación + Reparación + Postventa)")

    # Verificación de columnas necesarias
    columnas_necesarias = ['Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo']
    if all(col in data_combinada.columns for col in columnas_necesarias):
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
        data_2025 = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()

        if not data_2025.empty:
            # Filtrar actividades de interés
            actividades_2025 = data_2025[
                data_2025['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
            ].copy()

            if not actividades_2025.empty:
                resumen_2025 = pd.DataFrame({
                    'Año': [2025],
                    'Cantidad de Técnicos': [actividades_2025['Recurso'].nunique()],
                    'Total Actividades Asignadas': [
                        actividades_2025[
                            actividades_2025['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
                        ]['ID externo'].nunique()
                    ],
                    'Total Actividades Finalizadas': [
                        actividades_2025[
                            actividades_2025['Estado de actividad'].str.lower() == 'finalizada'
                        ]['ID externo'].nunique()
                    ]
                })

                st.dataframe(resumen_2025)
            else:
                st.info("No hay actividades de instalación, reparación o postventa para el año 2025.")
        else:
            st.info("No hay datos disponibles para el año 2025.")
    else:
        st.warning("Una o más de las columnas necesarias no se encontraron en los datos: 'Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo'.")

        # --- Gráficos de Mantención y Provisión ---
    st.markdown("---")
    st.subheader("Resumen de Actividades de Mantención y Provisión")
    resumen_general_sql.mostrar_grafico_mantencion()
    resumen_general_sql.mostrar_grafico_provision()

        # Ruta del archivo GIF
    gif_path = "Robertito_opt.gif"

    # Leer el archivo GIF en binario y codificarlo en base64
    with open(gif_path, "rb") as f:
        gif_bytes = f.read()
        encoded_gif = base64.b64encode(gif_bytes).decode("utf-8")

    # Mostrar el GIF en la esquina superior izquierda
    st.markdown(
        f"""
        <div style="position: absolute; top: 10px; left: 10px; z-index: 999;">
            <img src="data:image/gif;base64,{encoded_gif}" width="120">
        </div>
        """,
        unsafe_allow_html=True
    ) 


    









            
