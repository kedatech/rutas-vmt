import psycopg2
import json
import os

# Conexión a la base de datos PostgreSQL
conn = psycopg2.connect(
    dbname="chivorutas4", 
    user="myuser", 
    password="mypassword", 
    host="localhost"
)
cur = conn.cursor()

# Obtener la ruta relativa al archivo GeoJSON desde la carpeta 'migrate'
geojson_path = os.path.join(os.path.dirname(__file__), '../geojson/LIM DEPARTAMENTALES.geojson')

# Leer el archivo GeoJSON
with open(geojson_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Función para construir el WKT de un MultiPolygon
def create_multipolygon_wkt(coordinates):
    wkt = 'MULTIPOLYGON('
    for multipolygon in coordinates:
        wkt += '('
        for polygon in multipolygon:
            wkt += '('
            wkt += ', '.join([f'{point[0]} {point[1]}' for point in polygon])
            wkt += ')'
        wkt += '), '
    wkt = wkt.rstrip(', ')  # Eliminar la última coma
    wkt += ')'
    return wkt

# Función para construir el WKT de un Polygon
def create_polygon_wkt(coordinates):
    wkt = 'POLYGON('
    for polygon in coordinates:
        wkt += '('
        wkt += ', '.join([f'{point[0]} {point[1]}' for point in polygon])
        wkt += '), '
    wkt = wkt.rstrip(', ')  # Eliminar la última coma
    wkt += ')'
    return wkt

# Insertar datos de cada departamento
for feature in data['features']:
    name = feature['properties']['NA2']
    
    # Ignorar "ZONAS DE FRONTERAS"
    if name == "ZONAS DE FRONTERAS":
        print(f"Ignorando el departamento: {name}")
        continue
    
    area_km = feature['properties']['AREA_KM']
    perimeter_km = feature['properties']['PERIMETRO']
    
    # Manejo del campo 'NA3' para 'order'
    order_value = feature['properties']['NA3']
    try:
        order = int(order_value) if order_value.isdigit() else None  # Si no es numérico, se asigna None
    except ValueError:
        order = None

    # Convertir la geometría en formato WKT
    geometry_type = feature['geometry']['type']
    coordinates = feature['geometry']['coordinates']
    
    # Inicializar wkt_geom
    wkt_geom = None

    # Si es MultiPolygon
    if geometry_type == 'MultiPolygon':
        wkt_geom = create_multipolygon_wkt(coordinates)
    
    # Si es Polygon
    elif geometry_type == 'Polygon':
        wkt_geom = create_polygon_wkt(coordinates)

    # Imprimir el nombre y la geometría en WKT antes de la inserción
    print(f"Procesando departamento: {name}")
    print(f"WKT generado: {wkt_geom}")

    # Asegurarse de que wkt_geom esté definido
    if wkt_geom:
        # Insertar en la tabla
        sql = """
        INSERT INTO departments (name, geometry, area_km, perimeter_km, "order")
        VALUES (%s, ST_GeomFromText(%s, 4326), %s, %s, %s)
        """
        try:
            cur.execute(sql, (name, wkt_geom, area_km, perimeter_km, order))
        except Exception as e:
            print(f"Error al insertar el departamento: {name}")
            print(f"Error: {e}")
            conn.rollback()  # Hacer rollback si ocurre un error
    else:
        print(f"No se pudo procesar la geometría para el departamento: {name}")

# Confirmar cambios y cerrar conexión
conn.commit()
cur.close()
conn.close()