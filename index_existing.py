import os
import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

# Cargar el modelo multilingüe para generar embeddings
print("Cargando modelo de IA (primera vez puede tardar un poco en bajar los pesos)...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

es = Elasticsearch("http://localhost:9200")
index_name = "grimoire_files"

# Recrear el índice con el mapeo para vectores densos (KNN)
if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)

mapping = {
    "mappings": {
        "properties": {
            "name": {"type": "keyword"},
            "size": {"type": "keyword"},
            "size_bytes": {"type": "long"},
            "type": {"type": "keyword"},
            "date": {"type": "date", "format": "yyyy-MM-dd"},
            "creation_date": {"type": "date", "format": "yyyy-MM-dd"},
            "tags": {"type": "keyword"},
            "title_vector": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine"
            }
        }
    }
}
es.indices.create(index=index_name, body=mapping)
print("Índice Elasticsearch recreado con soporte para búsqueda vectorial.")

upload_folder = 'testfiles'

if not os.path.exists(upload_folder):
    pass
else:
    for filename in os.listdir(upload_folder):
        filepath = os.path.join(upload_folder, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            size_kb = stat.st_size / 1024
            size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"
            date_str = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
            creation_date_str = datetime.datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d')
            ext = filename.split('.')[-1] if '.' in filename else 'file'
            
            # Generar Vector Semántico del nombre del archivo
            embedding = model.encode(filename).tolist()
            
            # Obtener tags de SQLite para no perderlos al re-indexar
            import sqlite3
            import json
            tags = []
            try:
                conn = sqlite3.connect('grimoire.db')
                c = conn.cursor()
                c.execute("SELECT tags FROM file_tags WHERE filename = ?", (filename,))
                row = c.fetchone()
                conn.close()
                if row:
                    tags = json.loads(row[0])
            except:
                pass

            doc = {
                "name": filename,
                "size": size_str,
                "size_bytes": stat.st_size,
                "type": ext,
                "date": date_str,
                "creation_date": creation_date_str,
                "tags": tags,
                "title_vector": embedding
            }
            try:
                es.index(index=index_name, document=doc)
                print(f"Indexed with Vector: {filename}")
            except Exception as e:
                print(f"Failed to index {filename}: {e}")
