import openai
import os

openai_api_key = os.environ.get("OPENAI_API_KEY")

models = openai.models.list()
for model in models.data:
    print(model.id)


import tiktoken

# Seleccionamos la codificación usada en GPT-4
encoding = tiktoken.get_encoding("cl100k_base")

texto = """Para determinar cuántas actividades finalizadas se realizaron que sean específicamente reparaciones, podemos filtrar los datos por el campo 'ESTADO DE ACTIVIDAD' y 'TIPO DE ACTIVIDAD'...Para determinar cuántas actividades finalizadas se realizaron que sean específicamente reparaciones, podemos filtrar los datos por el campo "ESTADO DE ACTIVIDAD" y "TIPO DE ACTIVIDAD". Debemos buscar aquellas filas donde el "ESTADO DE ACTIVIDAD" sea "finalizada" y el "TIPO DE ACTIVIDAD" contenga la palabra "Reparación".

En la muestra de datos proporcionada, las siguientes actividades cumplen con estos criterios:

Carlos Alberto Figueroa Valdivia - Reparación-Hogar-Fibra - finalizada
Juan Francisco Bravo Bustamante - Reparación-Hogar-Fibra - finalizada
Juan Francisco Bravo Bustamante - Reparación-Hogar-Fibra - finalizada
Braulio Cristobal Castillo Palma - Reparación-Hogar-Fibra - finalizada
Braulio Cristobal Castillo Palma - Reparación-Hogar-Fibra - finalizada
Braulio Cristobal Castillo Palma - Reparación-Hogar-Fibra - finalizada
Braulio Cristobal Castillo Palma - Reparación-Hogar-Fibra - finalizada
Bryan Andres Godoy Bravo - Reparación-Hogar-Fibra - finalizada
Bryan Andres Godoy Bravo - Reparación-Hogar-Fibra - finalizada
Bryan Andres Godoy Bravo - Reparación-Hogar-Fibra - finalizada
Bryan Andres Godoy Bravo - Reparación-Hogar-Fibra - finalizada
Hans Bryan Huenchucoy Castillo - Reparación-Hogar-Fibra - finalizada
Hans Bryan Huenchucoy Castillo - Reparación-Hogar-Fibra - finalizada
En total, hay 13 actividades de reparación que fueron finalizadas."""  # Tu texto aquí

tokens = encoding.encode(texto)
print(f"Cantidad de tokens estimada para GPT-4: {len(tokens)}")
