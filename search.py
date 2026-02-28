import os
import datetime
import json
import sqlite3
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

print("Cargando modelo multilingüe para búsqueda semántica...")
search_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Modelo cargado.")

DB_PATH = 'grimoire.db'

def get_tags_for_file(filename):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT tags FROM file_tags WHERE filename = ?", (filename,))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except:
        pass
    return []

def mock_search_files(query, offset=0, filters=None):
    """
    Realiza una búsqueda real sobre Elasticsearch (índice grimoire_files) usando KNN Semántico + Filtros.
    """
    if not query or query.strip() == "":
        return []
    
    query = query.lower().strip()
    results = []
    
    try:
        es = Elasticsearch("http://localhost:9200")
        
        # Generar vector de la búsqueda
        query_vector = search_model.encode(query).tolist()
        
        # Construir filtros de metadatos
        must_filters = []
        if filters:
            # Función auxiliar para construir rangos de fecha
            def build_date_range(filter_val):
                d_r = {}
                if filter_val == "today":
                    d_r["gte"] = "now/d"
                elif filter_val == "yesterday":
                    d_r["gte"] = "now-1d/d"
                    d_r["lt"] = "now/d"
                elif filter_val == "week":
                    d_r["gte"] = "now-7d/d"
                    d_r["lt"] = "now-1d/d"
                elif filter_val == "month":
                    d_r["gte"] = "now-30d/d"
                    d_r["lt"] = "now-7d/d"
                elif filter_val == "older":
                    d_r["lt"] = "now-30d/d"
                return d_r

            # Filtro de fecha de SUBIDA
            upload_range_val = filters.get("upload_date_range")
            if upload_range_val:
                u_range = build_date_range(upload_range_val)
                if u_range:
                    must_filters.append({"range": {"date": u_range}})

            # Filtro de fecha de CREACIÓN (Local)
            creation_range_val = filters.get("creation_date_range")
            if creation_range_val:
                c_range = build_date_range(creation_range_val)
                if c_range:
                    must_filters.append({"range": {"creation_date": c_range}})
            
            # Filtro de tamaño (específico por bytes)
            if filters.get("min_size") or filters.get("max_size"):
                size_range = {}
                if filters.get("min_size"):
                    size_range["gte"] = int(filters["min_size"] * 1024 * 1024)
                if filters.get("max_size"):
                    size_range["lte"] = int(filters["max_size"] * 1024 * 1024)
                
                must_filters.append({"range": {"size_bytes": size_range}})

            # Filtro por Etiquetas (Tags)
            tags_filter = filters.get("tags")
            if tags_filter:
                if isinstance(tags_filter, list) and len(tags_filter) > 0:
                    must_filters.append({"terms": {"tags": tags_filter}})
                elif isinstance(tags_filter, str) and tags_filter != "":
                    must_filters.append({"term": {"tags": tags_filter}})
        
        # Búsqueda vectorial KNN
        search_body = {
            "knn": {
                "field": "title_vector",
                "query_vector": query_vector,
                "k": 100,
                "num_candidates": 500
            },
            "from": offset,
            "size": 10
        }
        
        if must_filters:
            search_body["knn"]["filter"] = {"bool": {"must": must_filters}}
            
        res = es.search(index="grimoire_files", body=search_body)
        
        for hit in res['hits']['hits']:
            doc = hit['_source']
            doc['id'] = hit['_id']
            # MERGE con base de datos SQLite para asegurar que los tags son los más recientes
            doc['tags'] = get_tags_for_file(doc.get('name', ''))
            results.append(doc)
            
    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
            
    return results
