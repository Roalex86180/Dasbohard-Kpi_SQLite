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
exclusiones_actividades = ['Almuerzo', 'Permiso', 'Reunion', 'Mantencion Vehicular', 'Curso', 'Levantamiento', 'Apoyo Terreno', 'Planta - Mantención']
ids_excluir_recurso = [3824, 3825, 3826, 3823, 3822, 5286, 4131, 5362]
meses_orden_dict = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}
meses_orden_lista = list(meses_orden_dict.values())

# --- FUNCIONES PARA SQLITE ---
@st.cache_data
def cargar_datos_en_sqlite(carpeta: str, patron: str, db_path: str = 'datos_actividades.db') -> bool:
    """Carga datos desde archivos Excel o CSV en la carpeta especificada a una base de datos SQLite."""
    all_data = []
    try:
        for nombre_archivo in os.listdir(carpeta):
            if re.match(patron, nombre_archivo):
                ruta_archivo = os.path.join(carpeta, nombre_archivo)
                formato_correcto = True
                mensaje_formato = ""

                if nombre_archivo.endswith(".xlsx"):
                    try:
                        import verificar_formato  # Importar solo si es necesario
                        formato_correcto, mensaje_formato = verificar_formato.verificar_formato_actividades(ruta_archivo)
                    except ImportError:
                        st.warning("El módulo 'verificar_formato' no se encontró. La verificación de formato de Excel se omitirá.")

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
                    st.error(f"Formato incorrecto para '{nombre_archivo}': {mensaje_formato}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            with sqlite3.connect(db_path) as conn:
                combined_df.to_sql('actividades', conn, if_exists='replace', index=False)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error general al procesar archivos: {e}")
        return False

@st.cache_data
def obtener_datos_desde_sqlite(db_path: str = 'datos_actividades.db') -> pd.DataFrame:
    """Obtiene todos los datos desde la tabla 'actividades' en la base de datos SQLite."""
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM actividades", conn)
        return df
    except Exception as e:
        st.error(f"Error al conectar o leer la base de datos SQLite: {e}")
        return pd.DataFrame()

# --- CARGAR O CONSULTAR LOS DATOS ---
# Solo ejecutar esta línea si necesitas regenerar la base desde los archivos
# cargar_datos_en_sqlite(carpeta_datos, patron_archivo)

data_combinada = obtener_datos_desde_sqlite(db_path)

# --- CÁLCULO DE KPI ---
if not data_combinada.empty:
    df_filtered = data_combinada[~data_combinada['Tipo de actividad'].str.lower().isin([e.lower() for e in exclusiones_actividades])].copy()
    filtro_actividades_kpi = df_filtered['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)

    total_finalizadas = df_filtered[
        (df_filtered['Estado de actividad'].str.lower() == 'finalizada') & filtro_actividades_kpi
    ]['ID externo'].nunique()

    total_asignadas = df_filtered[
        (df_filtered['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])) & filtro_actividades_kpi
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
    columnas_a_mostrar = ['Fecha Agendamiento', 'Recurso', 'ID externo', 'Nombre Cliente', 'Rut Cliente', 'Tipo de actividad', 'Observación', 'Acción realizada', 'Tipo Cierre', 'Motivo', 'SR de Siebel', 'Dirección', 'Ciudad', 'Comuna', 'Tipo de Vivienda', 'Teléfono móvil', 'Correo electrónico', 'Diagnóstico', 'Tipo de Servicio (TS1/TS2)', 'Producto/Plan contratado', 'Plan de internet', 'Nombre del bundle', 'Pack de canales premium', 'Cantidad routers', 'Cantidad de STB', 'Propietario de Red', 'AccessID']

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

    data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')
    fecha_seleccionada = st.date_input("Filtrar ranking por fecha", value=None)

    if fecha_seleccionada:
        data_filtrada_ranking = data_combinada[data_combinada['Fecha Agendamiento'].dt.date == fecha_seleccionada].copy()
    else:
        data_filtrada_ranking = data_combinada.copy()

    st.subheader("Ranking de Técnicos Multiskill")

    actividades_validas_ranking = data_filtrada_ranking[
        (~data_filtrada_ranking['Tipo de actividad'].isin(exclusiones_actividades)) &
        (~data_filtrada_ranking['ID de recurso'].isin(ids_excluir_recurso))
    ].copy()

    total_asignadas_serie = actividades_validas_ranking['Recurso'].value_counts()
    ranking_asignadas_df = pd.DataFrame({'Técnico': total_asignadas_serie.index, 'Total Asignadas': total_asignadas_serie.values})

    actividades_finalizadas_ranking = actividades_validas_ranking[actividades_validas_ranking['Estado de actividad'].str.lower() == 'finalizada'].copy()
    productividad_ranking_serie = actividades_finalizadas_ranking['Recurso'].value_counts()
    productividad_ranking_df = pd.DataFrame({'Técnico': productividad_ranking_serie.index, 'Total Finalizadas': productividad_ranking_serie.values})

    tipos_por_tecnico = actividades_validas_ranking.groupby('Recurso')['Tipo de actividad'].apply(lambda x: ', '.join(sorted(set(x)))).reset_index()
    tipos_por_tecnico.columns = ['Técnico', 'Tipo de actividad']

    productividad_final_df = pd.merge(productividad_ranking_df, ranking_asignadas_df, on='Técnico', how='left')
    productividad_final_df = pd.merge(productividad_final_df, tipos_por_tecnico, on='Técnico', how='left')
    productividad_final_df['Porcentaje de Efectividad'] = (
        productividad_final_df['Total Finalizadas'] / productividad_final_df['Total Asignadas'] * 100
    ).round(2).fillna(0).astype(str) + '%'
    productividad_final_df = productividad_final_df.sort_values(by='Total Finalizadas', ascending=False).reset_index(drop=True)
    productividad_final_df.index = productividad_final_df.index + 1

    st.dataframe(productividad_final_df)

    total_tecnicos = actividades_validas_ranking['Recurso'].nunique()
    if fecha_seleccionada:
        st.markdown(f"### 👷‍♂️ Total de Técnicos = {total_tecnicos} técnicos el {fecha_seleccionada.strftime('%d de %B %Y')}")
    else:
        st.markdown(f"### 👷‍♂️ Total de Técnicos = {total_tecnicos} técnicos (sin filtro de fecha)")

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

    if not data_filtrada_ranking.empty:
        st.subheader("📌 Métricas de Efectividad")

        repa_asig, repa_fin, repa_eff, repa_color = calcular_metricas(actividades_validas_ranking, 'reparación', 90)
        inst_post_asig, inst_post_fin, inst_post_eff, inst_post_color = calcular_metricas(actividades_validas_ranking, ['instalación', 'postventa'], 80)

        multi_asig = repa_asig + inst_post_asig
        multi_fin = repa_fin + inst_post_fin
        multi_eff = (multi_fin / multi_asig * 100) if multi_asig > 0 else 0
        multi_color = "normal" if multi_eff >= 90 else "inverse"

        st.markdown("**Multiskill**")
        cols_multi = st.columns(4)
        cols_multi[0].metric("Asignadas", multi_asig)
        cols_multi[1].metric("Finalizadas", multi_fin)
        cols_multi[2].metric("Efectividad", f"{multi_eff:.2f}%")

        st.markdown("**Reparación**")
        cols_repa = st.columns(4)
        cols_repa[0].metric("Asignadas", repa_asig)
        cols_repa[1].metric("Finalizadas", repa_fin)
        cols_repa[2].metric("Efectividad", f"{repa_eff:.2f}%", delta="Meta: 90%", delta_color=repa_color)

        st.markdown("**Instalación + Postventa**")
        cols_inst = st.columns(4)
        cols_inst[0].metric("Asignadas", inst_post_asig)
        cols_inst[1].metric("Finalizadas", inst_post_fin)
        cols_inst[2].metric("Efectividad", f"{inst_post_eff:.2f}%", delta="Meta: 80%", delta_color=inst_post_color)

        # Grafico actividad por meses
        data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], format='%d/%m/%y', errors='coerce')
        data_2025_grafico_mes = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()
        data_2025_grafico_mes['Mes_Num'] = data_2025_grafico_mes['Fecha Agendamiento'].dt.month
        data_2025_grafico_mes['Mes'] = data_2025_grafico_mes['Mes_Num'].map(meses_orden_dict)

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
            ).reindex(meses_orden_lista).fillna(0).astype(int)

            df_grouped['Productividad'] = (
                df_grouped['Finalizadas'] / df_grouped['Asignadas'].replace(0, pd.NA) * 100
            ).round(2).fillna(0)

            return df_grouped.reset_index()

        def graficar(df, titulo):
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df['Mes'], y=df['Asignadas'], name='Asignadas',
                marker_color='#AED6F1'
            ))

            fig.add_trace(go.Bar(
                x=df['Mes'], y=df['Finalizadas'], name='Finalizadas',
                marker_color='#3498DB'
            ))

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

        multi_df = datos_mensuales(data_2025_grafico_mes, "multiskill")
        repa_df = datos_mensuales(data_2025_grafico_mes, "reparación")
        inst_df = datos_mensuales(data_2025_grafico_mes, "instalación")

        st.subheader("📊 Gráfico de Actividades Mensuales (2025)")
        st.plotly_chart(graficar(multi_df, "Multiskill (Reparación + Instalación + Postventa)"), use_container_width=True)
        st.plotly_chart(graficar(repa_df, "Reparación"), use_container_width=True)
        st.plotly_chart(graficar(inst_df, "Instalación + Postventa"), use_container_width=True)

        # Tecnicos promedios pormes
        data_2025_tecnicos = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()
        data_2025_tecnicos_filtrada = data_2025_tecnicos[
            (~data_2025_tecnicos['Estado de actividad'].isin([
                'Reparación CPE (Router, ONT, Modem)',
                'Atención de Incidencia con visita técnica',
                'Reparación Acceso Cobre',
                'Reparación Acceso Fibra',
                'Reparación Terminal de Usuario'
            ])) &
            (~data_2025_tecnicos['ID de recurso'].isin(ids_excluir_recurso))
        ].copy()

        data_2025_tecnicos_filtrada['Fecha'] = data_2025_tecnicos_filtrada['Fecha Agendamiento'].dt.date
        data_2025_tecnicos_filtrada['Mes_Num'] = data_2025_tecnicos_filtrada['Fecha Agendamiento'].dt.month
        data_2025_tecnicos_filtrada['Mes'] = data_2025_tecnicos_filtrada['Mes_Num'].map(meses_orden_dict)

        tecnicos_por_dia = data_2025_tecnicos_filtrada.groupby(['Fecha']).agg(
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
            .reindex(meses_orden_lista)
            .drop(columns='Mes_Num')
        )

        fig_tecnicos_promedio = go.Figure()
        fig_tecnicos_promedio.add_trace(go.Bar(
            x=promedio_tecnicos_final.index,
            y=promedio_tecnicos_final['Promedio_Tecnicos_Diario'],
            name='Promedio Diario de Técnicos',
            marker_color='#F5B041'
        ))

        for i, row in promedio_tecnicos_final.reset_index().iterrows():
            fig_tecnicos_promedio.add_annotation(
                x=row['Mes'],
                y=row['Promedio_Tecnicos_Diario'] + 5,
                text=f"{row['Promedio_Tecnicos_Diario']:.1f}",
                showarrow=False,
                font=dict(size=18, color='black')
            )

        fig_tecnicos_promedio.update_layout(
            title="📈 Promedio Diario de Técnicos por Mes (2025)",
            xaxis_title="Mes",
            yaxis_title="Promedio de Técnicos por Día",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )

        st.subheader("👷 Promedio Diario de Técnicos por Mes (2025)")
        st.plotly_chart(fig_tecnicos_promedio, use_container_width=True)

        # --- EXCEL CON TÉCNICOS POR DÍA ---
        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            for mes_num, mes_nombre in meses_orden_dict.items():
                data_mes_excel = data_2025_tecnicos_filtrada[data_2025_tecnicos_filtrada['Mes_Num'] == mes_num].copy()
                if data_mes_excel.empty:
                    continue

                data_mes_excel['Fecha_str'] = data_mes_excel['Fecha Agendamiento'].dt.strftime('%d/%m/%Y')
                data_mes_excel['ID Recurso y Nombre'] = data_mes_excel['ID de recurso'].astype(str) + ' ' + data_mes_excel['Recurso']

                pivot_mes = data_mes_excel.pivot_table(
                    index='ID Recurso y Nombre',
                    columns='Fecha_str',
                    values='Recurso',
                    aggfunc='first',
                    fill_value=''
                )

                pivot_mes['Días trabajados'] = (pivot_mes != '').sum(axis=1)
                cantidad_por_dia = (pivot_mes != '').sum(axis=0)
                pivot_mes.loc['Cantidad de Técnicos'] = cantidad_por_dia

                columnas_fechas = []  # Initialize columnas_fechas here
                columnas_fechas = [col for col in pivot_mes.columns if col != 'Días trabajados']
                columnas_ordenadas = sorted(columnas_fechas, key=lambda x: pd.to_datetime(x, dayfirst=True))
                pivot_mes = pivot_mes[columnas_ordenadas + ['Días trabajados']]

                pivot_mes.to_excel(writer, sheet_name=mes_nombre)

        st.download_button(
            label="📥 Descargar Excel con hojas por mes",
            data=excel_buffer.getvalue(),
            file_name="tecnicos_por_dia_por_mes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- Técnicos que mencionan U2000 ---
        st.markdown("---")
        st.subheader("Técnicos que Realizan U2000")

        meses_u2000 = ['Selecciona'] + meses_orden_lista
        mes_seleccionado_u2000 = st.selectbox("Selecciona un mes:", meses_u2000, key="mes_u2000")

        if mes_seleccionado_u2000 != 'Selecciona':
            mes_num_u2000 = list(meses_orden_dict.keys())[list(meses_orden_dict.values()).index(mes_seleccionado_u2000)]
            data_filtrada_mes_u2000 = data_combinada[data_combinada['Fecha Agendamiento'].dt.month == mes_num_u2000].copy()
        else:
            data_filtrada_mes_u2000 = data_combinada.copy()

        dias_del_mes_u2000 = sorted(data_filtrada_mes_u2000['Fecha Agendamiento'].dt.day.unique())
        dias_del_mes_u2000 = ['Selecciona'] + [int(d) for d in dias_del_mes_u2000 if pd.notna(d)]
        dia_seleccionado_u2000 = st.selectbox("Selecciona un día:", dias_del_mes_u2000, key="dia_u2000")

        if dia_seleccionado_u2000 != 'Selecciona':
            data_filtrada_dia_u2000 = data_filtrada_mes_u2000[data_filtrada_mes_u2000['Fecha Agendamiento'].dt.day == dia_seleccionado_u2000].copy()
        else:
            data_filtrada_dia_u2000 = data_filtrada_mes_u2000.copy()

        u2000_mentions = data_filtrada_dia_u2000[
            data_filtrada_dia_u2000['Observación'].str.contains(r'u\s?2000|u\s?200|u200', flags=re.IGNORECASE, na=False)
        ].copy()

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

        meses_rapidos = ['Selecciona'] + meses_orden_lista
        mes_seleccionado_rapidos = st.selectbox("Selecciona un mes:", meses_rapidos, key="mes_rapidos")

        if mes_seleccionado_rapidos != 'Selecciona':
            mes_num_rapidos = list(meses_orden_dict.keys())[list(meses_orden_dict.values()).index(mes_seleccionado_rapidos)]
            data_filtrada_mes_rapidos = data_combinada[data_combinada['Fecha Agendamiento'].dt.month == mes_num_rapidos].copy()
        else:
            data_filtrada_mes_rapidos = data_combinada.copy()

        dias_del_mes_rapidos = sorted(data_filtrada_mes_rapidos['Fecha Agendamiento'].dt.day.unique())
        dias_del_mes_rapidos = ['Selecciona'] + [int(d) for d in dias_del_mes_rapidos if pd.notna(d)]
        dia_seleccionado_rapidos = st.selectbox("Selecciona un día:", dias_del_mes_rapidos, key="dia_rapidos")

        if dia_seleccionado_rapidos != 'Selecciona':
            data_filtrada_dia_rapidos = data_filtrada_mes_rapidos[data_filtrada_mes_rapidos['Fecha Agendamiento'].dt.day == dia_seleccionado_rapidos].copy()
        else:
            data_filtrada_dia_rapidos = data_filtrada_mes_rapidos.copy()

        @st.cache_data
        def calcular_ranking_tiempo(df):
            actividades_filtradas_tiempo = df[
                df['Tipo de actividad'].astype(str).str.contains(
                    r'instalaci[oó]n|reparaci[oó]n|postventa',
                    case=False,
                    regex=True,
                    na=False
                )
            ].copy()

            actividades_finalizadas_tiempo = actividades_filtradas_tiempo[
                (actividades_filtradas_tiempo['Estado de actividad'].str.lower() == 'finalizada') &
                (actividades_filtradas_tiempo['Duración'] != '00:00') &
                (pd.notna(actividades_filtradas_tiempo['Duración']))
            ].copy()

            if actividades_finalizadas_tiempo.empty:
                return pd.DataFrame({'Técnico': [], 'Tiempo Promedio': []})

            def tiempo_a_minutos(tiempo_str):
                try:
                    horas, minutos = map(int, tiempo_str.split(':'))
                    return horas * 60 + minutos
                except:
                    return None

            actividades_finalizadas_tiempo['duracion_min'] = actividades_finalizadas_tiempo['Duración'].apply(tiempo_a_minutos)
            actividades_finalizadas_tiempo = actividades_finalizadas_tiempo.dropna(subset=['duracion_min'])

            if actividades_finalizadas_tiempo.empty:
                return pd.DataFrame({'Técnico': [], 'Tiempo Promedio': []})

            promedio_por_tecnico_tiempo = actividades_finalizadas_tiempo.groupby('Recurso')['duracion_min'].mean().sort_values()

            ranking_tiempo_df = pd.DataFrame({
                'Técnico': promedio_por_tecnico_tiempo.index,
                'Tiempo Promedio': promedio_por_tecnico_tiempo.apply(
                    lambda x: f"{int(x // 60)} hrs {int(x % 60)} min" if pd.notna(x) else "Sin datos"
                )
            }).reset_index(drop=True)

            ranking_tiempo_df.index = ranking_tiempo_df.index + 1
            return ranking_tiempo_df

        ranking_tiempo_df = calcular_ranking_tiempo(data_filtrada_dia_rapidos)
        if not ranking_tiempo_df.empty:
            st.dataframe(ranking_tiempo_df)
        else:
            st.info("No hay suficientes actividades finalizadas de instalación, reparación o postventa con tiempos válidos para calcular el ranking de tiempo promedio.")

        # --- Gráfico de Torta: Causa de la falla ---
        st.markdown("---")
        st.subheader("Distribución de Causas de la Falla")

        columna_causa_falla = 'Causa de la falla'
        grafico_placeholder_falla = st.empty()

        if columna_causa_falla in data_combinada.columns:
            causa_falla_counts_total = data_combinada[columna_causa_falla].dropna().value_counts()

            top_10_fallas = causa_falla_counts_total.head(10)
            otras_fallas = causa_falla_counts_total[10:]

            causa_falla_counts = top_10_fallas.copy()
            if not otras_fallas.empty:
                causa_falla_counts["Otras"] = otras_fallas.sum()
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
                grafico_placeholder_falla.plotly_chart(fig_causa_falla)
            else:
                grafico_placeholder_falla.warning("No hay datos válidos para mostrar en la columna 'Causa de la falla'.")
        else:
            grafico_placeholder_falla.warning(f"La columna '{columna_causa_falla}' no se encontró en los datos.")

            # --- Sección Reincidencias y fallas tempranas ---
            
        analizar_reincidencias_y_fallas_tempranas()

        # --- Sección de Verificación de Ubicación ---
        st.markdown("---")
        conn = sqlite3.connect("datos_actividades.db")
        mostrar_verificacion_ubicacion_sql(conn)


        # --- Nuevo KPI: Ranking de Técnicos WIFI-Design desde SQLite ---
        st.markdown("---")
        st.subheader("Ranking de Técnicos WIFI-Design")

        with sqlite3.connect('datos_actividades.db') as conn_wifi:
            query_wifi = """
            SELECT Recurso, Documento, Cod_Servicio, "ID externo", "Fecha Agendamiento",
                "Propietario de Red", Dirección
            FROM actividades;
            """
            df_wifi = pd.read_sql(query_wifi, conn_wifi)

        if all(col in df_wifi.columns for col in ['Documento', 'Cod_Servicio', 'Recurso', 'ID externo']):
            wifi_design_df = df_wifi[
                df_wifi['Documento'].astype(str).str.match(r'^CS_\d+\.pdf', case=False, na=False)
            ].copy()

            wifi_design_counts = wifi_design_df.groupby('Recurso')['Documento'].count().reset_index()
            wifi_design_counts.columns = ['Técnico', 'Cantidad WIFI-Design']

            trabajos_asignados_wifi = df_wifi.groupby('Recurso')['ID externo'].nunique().reset_index()
            trabajos_asignados_wifi.columns = ['Técnico', 'Trabajos Asignados']

            ranking_wifi_design = pd.merge(wifi_design_counts, trabajos_asignados_wifi, on='Técnico', how='left').fillna(0)
            ranking_wifi_design['% Cumplimiento'] = (
                (ranking_wifi_design['Cantidad WIFI-Design'] / ranking_wifi_design['Trabajos Asignados']) * 100
            ).round(2).astype(str) + '%'

            ranking_wifi_design = ranking_wifi_design.sort_values(by='Cantidad WIFI-Design', ascending=False).reset_index(drop=True)
            ranking_wifi_design.index += 1
            st.dataframe(ranking_wifi_design)

            # --- Detalle por Técnico ---
            st.subheader("Detalle de Trabajos WIFI-Design por Técnico")
            tecnicos_wifi_design = ranking_wifi_design['Técnico'].unique()
            opciones_tecnicos_wifi = ["Seleccione", "Todos"] + list(tecnicos_wifi_design)
            tecnico_seleccionado_wifi = st.selectbox("Seleccionar Técnico", opciones_tecnicos_wifi)

            columnas_base_detalle_wifi = ['Fecha Agendamiento', 'ID externo', 'Cod_Servicio', 'Propietario de Red', 'Dirección', 'Documento', 'Recurso']
            columnas_detalle_final_wifi = ['Fecha Agendamiento', 'ID externo', 'Cod_Servicio', 'WIFI-Design', 'Propietario de Red', 'Dirección', 'Técnico']

            def determinar_wifi_design(row):
                if pd.notna(row['Cod_Servicio']) or pd.notna(row['ID externo']):
                    if pd.notna(row['Documento']) and re.match(r'^CS_\d+\.pdf', str(row['Documento']), re.IGNORECASE):
                        return 'SI'
                    else:
                        return 'NO'
                else:
                    return 'Sin Datos'

            if tecnico_seleccionado_wifi == "Todos":
                detalle_todos_wifi = df_wifi[columnas_base_detalle_wifi].copy()
                detalle_todos_wifi['WIFI-Design'] = detalle_todos_wifi.apply(determinar_wifi_design, axis=1)
                detalle_todos_wifi['Técnico'] = detalle_todos_wifi['Recurso']
                detalle_filtrado_sin_datos_wifi = detalle_todos_wifi[detalle_todos_wifi['WIFI-Design'] != 'Sin Datos'][columnas_detalle_final_wifi]
                if not detalle_filtrado_sin_datos_wifi.empty:
                    st.dataframe(detalle_filtrado_sin_datos_wifi)
                else:
                    st.info("No hay detalles de WIFI-Design para mostrar.")
            elif tecnico_seleccionado_wifi != "Seleccione":
                detalle_tecnico_wifi = df_wifi[df_wifi['Recurso'] == tecnico_seleccionado_wifi][columnas_base_detalle_wifi].copy()
                detalle_tecnico_wifi['WIFI-Design'] = detalle_tecnico_wifi.apply(determinar_wifi_design, axis=1)
                detalle_tecnico_wifi['Técnico'] = detalle_tecnico_wifi['Recurso']
                detalle_filtrado_tecnico_wifi = detalle_tecnico_wifi[detalle_tecnico_wifi['WIFI-Design'] != 'Sin Datos'][columnas_detalle_final_wifi]
                if not detalle_filtrado_tecnico_wifi.empty:
                    st.dataframe(detalle_filtrado_tecnico_wifi)
                else:
                    st.info(f"No hay detalles de WIFI-Design para el técnico '{tecnico_seleccionado_wifi}'.")
        else:
            st.warning("Las columnas 'Documento', 'Cod_Servicio' o 'Recurso' no se encontraron en los datos para WIFI-Design.")

        # --- Gráfico de Barras: Distribución de Trabajos por Comuna y Categoría de Actividad desde SQLite ---
        st.markdown("---")
        st.subheader("Distribución de Trabajos por Comuna y Categoría de Actividad")

        with sqlite3.connect('datos_actividades.db') as conn_comuna:
            columnas_activas_comuna = pd.read_sql("PRAGMA table_info(actividades);", conn_comuna)['name'].tolist()
            if 'Comuna' in columnas_activas_comuna and 'Tipo de actividad' in columnas_activas_comuna:
                query_comuna = """
                SELECT Comuna, "Tipo de actividad"
                FROM actividades
                WHERE LOWER("Tipo de actividad") LIKE 'instalación%'
                OR LOWER("Tipo de actividad") LIKE 'reparación%'
                OR LOWER("Tipo de actividad") LIKE 'postventa%';
                """
                actividades_filtradas_comuna = pd.read_sql(query_comuna, conn_comuna)

                if not actividades_filtradas_comuna.empty:
                    actividades_filtradas_comuna['Categoria_Actividad'] = actividades_filtradas_comuna['Tipo de actividad'].str.lower().str.split('-').str[0]
                    totales_por_categoria_comuna = actividades_filtradas_comuna['Categoria_Actividad'].value_counts().to_dict()

                    if actividades_filtradas_comuna['Comuna'].nunique() > 0:
                        distribucion_comunal = (
                            actividades_filtradas_comuna
                            .groupby(['Comuna', 'Categoria_Actividad'])
                            .size()
                            .reset_index(name='Cantidad')
                        )

                        if not distribucion_comunal.empty:
                            fig_comuna = px.bar(
                                distribucion_comunal,
                                x='Comuna',
                                y='Cantidad',
                                color='Categoria_Actividad',
                                labels={'Cantidad': 'Cantidad de Trabajos', 'Comuna': 'Comuna', 'Categoria_Actividad': 'Tipo de Actividad'},
                                title='Distribución de Trabajos por Comuna y Categoría de Actividad'
                            )

                            new_legend_names_comuna = {
                                trace.name: f"{trace.name} ({totales_por_categoria_comuna.get(trace.name.lower(), 0)})"
                                for trace in fig_comuna.data
                            }

                            fig_comuna.for_each_trace(lambda t: t.update(
                                name=new_legend_names_comuna[t.name],
                                legendgroup=new_legend_names_comuna[t.name],
                                hovertemplate=t.hovertemplate.replace(t.name, new_legend_names_comuna[t.name])
                            ))

                            st.plotly_chart(fig_comuna)
                        else:
                            st.info("No hay datos agrupados por comuna y tipo de actividad.")
                    else:
                        st.info("No hay información de comunas para los tipos de actividad seleccionados.")
                else:
                    st.info("No hay actividades de instalación, reparación o postventa en los datos para el gráfico de comunas.")
            else:
                st.warning("Las columnas 'Comuna' o 'Tipo de actividad' no se encontraron en la base de datos para el gráfico de comunas.")

        # --- Ranking de Comunas por Trabajos Finalizados con Totales y Efectividad ---
        st.markdown("---")
        st.subheader("Ranking de Comunas Trabajos Multiskill Finalizados")

        with sqlite3.connect('datos_actividades.db') as conn_ranking_comuna:
            columnas_ranking_comuna = pd.read_sql("PRAGMA table_info(actividades);", conn_ranking_comuna)['name'].tolist()
            if all(col in columnas_ranking_comuna for col in ['Comuna', 'Estado de actividad', 'Tipo de actividad']):
                actividades_a_excluir_ranking_comuna = [e.lower() for e in ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']]
                query_filtrados_comuna = f"""
                    SELECT Comuna, "Estado de actividad", "Tipo de actividad"
                    FROM actividades
                    WHERE LOWER("Tipo de actividad") NOT IN ({','.join(['?']*len(actividades_a_excluir_ranking_comuna))})
                """
                trabajos_filtrados_comuna = pd.read_sql(query_filtrados_comuna, conn_ranking_comuna, params=actividades_a_excluir_ranking_comuna)

                total_asignados_comuna = trabajos_filtrados_comuna['Comuna'].value_counts().reset_index()
                total_asignados_comuna.columns = ['Comuna', 'Total Asignadas']

                finalizados_comuna = trabajos_filtrados_comuna[trabajos_filtrados_comuna['Estado de actividad'].str.lower() == 'finalizada']
                total_finalizados_comuna = finalizados_comuna.groupby('Comuna').size().reset_index(name='Total Finalizados')

                ranking_comuna = pd.merge(total_asignados_comuna, total_finalizados_comuna, on='Comuna', how='left').fillna(0)

                query_sin_zona_comuna = f"""
                    SELECT Comuna, "Estado de actividad", "Tipo de actividad"
                    FROM actividades
                    WHERE LOWER(Comuna) = 'sin zona'
                    AND (
                        LOWER("Tipo de actividad") LIKE 'reparación%' OR
                        LOWER("Tipo de actividad") LIKE 'instalación%' OR
                        LOWER("Tipo de actividad") LIKE 'postventa%'
                    )
                    AND LOWER("Tipo de actividad") NOT IN ({','.join(['?']*len(actividades_a_excluir_ranking_comuna))})
                """
                sin_zona_df_comuna = pd.read_sql(query_sin_zona_comuna, conn_ranking_comuna, params=actividades_a_excluir_ranking_comuna)

                total_asignados_sin_zona_comuna = len(sin_zona_df_comuna)
                total_finalizados_sin_zona_comuna = len(sin_zona_df_comuna[sin_zona_df_comuna['Estado de actividad'].str.lower() == 'finalizada'])

                if total_asignados_sin_zona_comuna > 0:
                    sin_zona_ranking_comuna = pd.DataFrame({
                        'Comuna': ['SIN ZONA'],
                        'Total Asignadas': [total_asignados_sin_zona_comuna],
                        'Total Finalizados': [total_finalizados_sin_zona_comuna]
                    })
                    sin_zona_ranking_comuna['% de Efectividad'] = (sin_zona_ranking_comuna['Total Finalizados'] / sin_zona_ranking_comuna['Total Asignadas'] * 100).round(2).astype(str) + '%'

                    ranking_comuna = ranking_comuna[ranking_comuna['Comuna'].str.lower() != 'sin zona']
                    ranking_comuna = pd.concat([ranking_comuna, sin_zona_ranking_comuna], ignore_index=True)
                else:
                    ranking_comuna = ranking_comuna[ranking_comuna['Comuna'].str.lower() != 'sin zona']

                ranking_comuna['% de Efectividad'] = (ranking_comuna['Total Finalizados'] / ranking_comuna['Total Asignadas'] * 100).round(2).astype(str) + '%'
                ranking_ordenado_comuna = ranking_comuna.sort_values(by='Total Finalizados', ascending=False).reset_index(drop=True)
                ranking_ordenado_comuna.index = ranking_ordenado_comuna.index + 1

                st.dataframe(ranking_ordenado_comuna)

            else:
                st.warning("Las columnas necesarias ('Comuna', 'Estado de actividad', 'Tipo de actividad') no se encontraron en la base de datos para el ranking de comunas.")

        # --- Ranking de Comunas por Trabajos de Instalación y Postventa ---
        st.markdown("---")
        st.subheader("Ranking de Comunas Provision + Postventas")

        if 'Comuna' in data_combinada.columns and 'Estado de actividad' in data_combinada.columns and 'Tipo de actividad' in data_combinada.columns:
            instalacion_postventa_filtrado = data_combinada[
                data_combinada['Tipo de actividad'].str.lower().str.contains(r'instalación|postventa', regex=True) &
                ~data_combinada['Tipo de actividad'].str.lower().isin([e.lower() for e in ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']])
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
                ~data_combinada['Tipo de actividad'].str.lower().isin([e.lower() for e in ['retiro equipos', 'levantamiento', 'curso', 'almuerzo', 'apoyo terreno', 'reunion', 'mantencion vehicular']])
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
            st.warning("Las columnas necesarias ('Comuna', 'Estado de actividad', 'Tipo de actividad') no se encontraron en los datos para los rankings de comunas.")

        # --- Resumen de Actividades Año 2023 ---
        st.markdown("---")
        st.subheader("Resumen de Actividades Año 2023 (Instalación + Reparación + Postventa)")

        columnas_resumen = ['Fecha Agendamiento', 'Tipo de actividad', 'Estado de actividad', 'Recurso', 'ID externo']
        if all(col in data_combinada.columns for col in columnas_resumen):
            data_combinada['Fecha Agendamiento'] = pd.to_datetime(data_combinada['Fecha Agendamiento'], errors='coerce')
            data_2023_resumen = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2023].copy()

            if not data_2023_resumen.empty:
                actividades_2023_resumen = data_2023_resumen[
                    data_2023_resumen['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
                ].copy()

                if not actividades_2023_resumen.empty:
                    resumen_2023_df = pd.DataFrame({
                        'Año': [2023],
                        'Cantidad de Técnicos': [actividades_2023_resumen['Recurso'].nunique()],
                        'Total Actividades Asignadas': [
                            actividades_2023_resumen[
                                actividades_2023_resumen['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
                            ]['ID externo'].nunique()
                        ],
                        'Total Actividades Finalizadas': [
                            actividades_2023_resumen[
                                actividades_2023_resumen['Estado de actividad'].str.lower() == 'finalizada'
                            ]['ID externo'].nunique()
                        ]
                    })
                    st.dataframe(resumen_2023_df)
                else:
                    st.info("No hay actividades de instalación, reparación o postventa para el año 2023.")
            else:
                st.info("No hay datos disponibles para el año 2023.")
        else:
            st.warning("Una o más de las columnas necesarias no se encontraron en los datos para el resumen de 2023.")

        # --- Resumen de Actividades Año 2024 ---
        st.subheader("Resumen de Actividades Año 2024 (Instalación + Reparación + Postventa)")
        if all(col in data_combinada.columns for col in columnas_resumen):
            data_2024_resumen = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2024].copy()
            if not data_2024_resumen.empty:
                actividades_2024_resumen = data_2024_resumen[
                    data_2024_resumen['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
                ].copy()
                if not actividades_2024_resumen.empty:
                    resumen_2024_df = pd.DataFrame({
                        'Año': [2024],
                        'Cantidad de Técnicos': [actividades_2024_resumen['Recurso'].nunique()],
                        'Total Actividades Asignadas': [
                            actividades_2024_resumen[
                                actividades_2024_resumen['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
                            ]['ID externo'].nunique()
                        ],
                        'Total Actividades Finalizadas': [
                            actividades_2024_resumen[
                                actividades_2024_resumen['Estado de actividad'].str.lower() == 'finalizada'
                            ]['ID externo'].nunique()
                        ]
                    })
                    st.dataframe(resumen_2024_df)
                else:
                    st.info("No hay actividades de instalación, reparación o postventa para el año 2024.")
            else:
                st.info("No hay datos disponibles para el año 2024.")
        else:
            st.warning("Una o más de las columnas necesarias no se encontraron en los datos para el resumen de 2024.")

        # -- Resumen Año 2025
        st.subheader("Resumen de Actividades Año 2025 (Instalación + Reparación + Postventa)")
        if all(col in data_combinada.columns for col in columnas_resumen):
            data_2025_resumen = data_combinada[data_combinada['Fecha Agendamiento'].dt.year == 2025].copy()
            if not data_2025_resumen.empty:
                actividades_2025_resumen = data_2025_resumen[
                    data_2025_resumen['Tipo de actividad'].str.lower().str.contains('instalación|reparación|postventa', na=False)
                ].copy()
                if not actividades_2025_resumen.empty:
                    resumen_2025_df = pd.DataFrame({
                        'Año': [2025],
                        'Cantidad de Técnicos': [actividades_2025_resumen['Recurso'].nunique()],
                        'Total Actividades Asignadas': [
                            actividades_2025_resumen[
                                actividades_2025_resumen['Estado de actividad'].str.lower().isin(['finalizada', 'no realizado'])
                            ]['ID externo'].nunique()
                        ],
                        'Total Actividades Finalizadas': [
                            actividades_2025_resumen[
                                actividades_2025_resumen['Estado de actividad'].str.lower() == 'finalizada'
                            ]['ID externo'].nunique()
                        ]
                    })
                    st.dataframe(resumen_2025_df)
                else:
                    st.info("No hay actividades de instalación, reparación o postventa para el año 2025.")
            else:
                st.info("No hay datos disponibles para el año 2025.")
        else:
            st.warning("Una o más de las columnas necesarias no se encontraron en los datos para el resumen de 2025.")

        # --- Gráficos de Mantención y Provisión ---
            # --- Gráficos de Mantención y Provisión ---
        st.markdown("---")
        st.subheader("Resumen de Actividades de Mantención y Provisión")
        resumen_general_sql.mostrar_grafico_mantencion()
        resumen_general_sql.mostrar_grafico_provision()
            # Ruta del archivo GIF
        gif_path = "Robertito_opt.gif"

        # Leer el archivo GIF en binario y codificarlo en base64
        try:
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
        except FileNotFoundError:
            st.warning(f"El archivo GIF '{gif_path}' no se encontró.")
        except Exception as e:
            st.error(f"Error al cargar o mostrar el GIF: {e}")
else:
    st.info("No se han cargado datos. Asegúrese de que la carpeta 'Data_diaria' contenga archivos .xlsx o .csv.")