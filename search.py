import os
import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

print("Cargando modelo multilingüe para búsqueda semántica...")
search_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Modelo cargado.")

def mock_search_files(query, offset=0):
    """
    Realiza una búsqueda real sobre Elasticsearch (índice grimoire_files) usando KNN Semántico con paginación.
    """
    if not query or query.strip() == "":
        return []
    
    query = query.lower().strip()
    results = []
    
    try:
        es = Elasticsearch("http://localhost:9200")
        
        # Generar vector de la búsqueda
        query_vector = search_model.encode(query).tolist()
        
        # Búsqueda vectorial KNN con paginación
        res = es.search(index="grimoire_files", knn={
            "field": "title_vector",
            "query_vector": query_vector,
            "k": 100, # Aumentar k para encontrar candidatos relevantes
            "num_candidates": 500
        }, from_=offset, size=10)
        
        for hit in res['hits']['hits']:
            doc = hit['_source']
            doc['id'] = hit['_id']
            results.append(doc)
            
    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
            
    return results
