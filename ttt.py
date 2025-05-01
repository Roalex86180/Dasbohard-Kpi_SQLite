import sqlite3

# Conexión a la base de datos correcta
conn = sqlite3.connect("datos_actividades.db")
cursor = conn.cursor()

# Consulta de ejemplo: mostrar los primeros 10 valores de la columna "ID externo"
cursor.execute('SELECT "ID externo" FROM actividades LIMIT 10;')
resultados = cursor.fetchall()

# Mostrar resultados
print("Primeros 10 valores de 'ID externo':")
for fila in resultados:
    print(fila[0])

conn.close()
