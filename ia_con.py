import streamlit as st
import pandas as pd
import openai
import os
import math

# API Key de OpenAI
openai_api_key = os.environ.get("OPENAI_API_KEY")

st.title("Consultas inteligentes sobre técnicos")

# Cargar archivo Excel
df = pd.read_excel("CONSULTAS_PY.xlsx", engine="openpyxl")

# Función para extraer latitud y longitud
def extraer_lat_lon(coord):
    if isinstance(coord, str) and "lat" in coord and "lng" in coord:
        try:
            parts = coord.replace("lat:", "").replace("lng:", "").split(",")
            lat = float(parts[0])
            lon = float(parts[1])
            return lat, lon
        except:
            return None, None
    return None, None

# Función para calcular distancia entre coordenadas
def distancia_metros(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371000  # Radio de la Tierra en metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# Calcular distancias y estados
distancias = []
for i, row in df.iterrows():
    lat_ini, lon_ini = extraer_lat_lon(row.get("COORDENADAS INICIO", ""))
    lat_fin, lon_fin = extraer_lat_lon(row.get("COORDENADAS FIN", ""))
    lat_cli = row.get("COORDENADAS Y", None)
    lon_cli = row.get("COORDENADAS X", None)

    try:
        lat_cli = float(lat_cli)
        lon_cli = float(lon_cli)
    except:
        lat_cli, lon_cli = None, None

    dist_ini = distancia_metros(lat_ini, lon_ini, lat_cli, lon_cli) if lat_ini and lat_cli else None
    dist_fin = distancia_metros(lat_fin, lon_fin, lat_cli, lon_cli) if lat_fin and lat_cli else None

    estado_ini = "Sin registro de inicio" if lat_ini is None else (
        f"Inicio a {dist_ini} metros del cliente" if dist_ini <= 200 else f"Inicio a {dist_ini} metros del cliente, fuera de 200m"
    )

    estado_fin = "Sin registro de finalización" if lat_fin is None else (
        f"Finalizó a {dist_fin} metros del cliente" if dist_fin <= 200 else f"Finalizó a {dist_fin} metros del cliente, fuera de 200m"
    )

    distancias.append({
        "distancia_inicio_m": dist_ini,
        "distancia_fin_m": dist_fin,
        "estado_inicio": estado_ini,
        "estado_fin": estado_fin
    })

# Agregar al DataFrame
df_dist = pd.DataFrame(distancias)
df = pd.concat([df, df_dist], axis=1)

# Entrada de usuario
user_input = st.text_input("Escribe tu consulta:")

if user_input:
    with st.spinner("💡 Pensando..."):

        muestra = df.to_csv(index=False)

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente experto en análisis de datos. "
                    "Tienes una tabla con información sobre técnicos de telecomunicaciones. "
                    "Los campos 'estado_inicio' y 'estado_fin' indican si el técnico registró el inicio o finalización, "
                    "y si lo hizo, a cuántos metros del cliente fue. "
                    "Un inicio o finalización se considera válido si fue a 200 metros o menos del cliente. "
                    "También existe una columna 'estado' que indica si la actividad fue finalizada, suspendida, etc., "
                    "y este estado no depende de si se registraron las coordenadas de inicio o finalización. "
                    "Si no hay coordenadas, responde que no se registró inicio o finalización, pero no invalides el estado general. "
                    "Responde únicamente a lo que se consulta, no muestres toda la información."
                ),
            },
            {
                "role": "user",
                "content": f"Aquí tienes una muestra de los datos:\n\n{muestra}\n\nConsulta: {user_input}"
            }
        ]

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            st.markdown(response.choices[0].message.content)

        except Exception as e:
            st.error(f"❌ Error: {e}")






