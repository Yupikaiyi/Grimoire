import datetime
import sqlite3
import json
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

# Initialize ES and Model (In prod, these would be global/singleton)
es = Elasticsearch("http://localhost:9200")
search_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def get_file_metadata_sync(filename):
    conn = sqlite3.connect('grimoire.db')
    c = conn.cursor()
    c.execute("SELECT tags, owner, department FROM file_metadata WHERE filename = ?", (filename,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'tags': json.loads(row[0]) if row[0] else [],
            'owner': row[1] or "",
            'department': row[2] or ""
        }
    return {'tags': [], 'owner': "", 'department': ""}

def mock_search_files(query, offset=0, filters=None):
    try:
        query_vector = search_model.encode(query).tolist()
        
        es_filters = []
        if filters:
            # Date Filter Helper
            def build_date_range(filter_val):
                if not filter_val or filter_val == 'all': return None
                date_map = {
                    "today": "now/d",
                    "yesterday": "now-1d/d",
                    "week": "now-7d/d",
                    "month": "now-30d/d"
                }
                if filter_val == "older":
                    return {"lt": "now-30d/d"}
                return {"gte": date_map.get(filter_val), "lte": "now/d"}

            # Apply Filters
            if filters.get('tags'):
                es_filters.append({"terms": {"tags": filters['tags']}})
            
            if filters.get('owner') and filters['owner'] != 'all':
                es_filters.append({"term": {"owner.keyword": filters['owner']}})
                
            if filters.get('department') and filters['department'] != 'all':
                es_filters.append({"term": {"department.keyword": filters['department']}})

            if filters.get('type') and filters['type'] != 'all':
                es_filters.append({"term": {"type": filters['type']}})

            u_range = build_date_range(filters.get('upload_date_range'))
            if u_range: es_filters.append({"range": {"date": u_range}})

            c_range = build_date_range(filters.get('creation_date_range'))
            if c_range: es_filters.append({"range": {"creation_date": c_range}})

            if filters.get("min_size") or filters.get("max_size"):
                size_range = {}
                if filters.get("min_size"): size_range["gte"] = int(filters["min_size"] * 1024 * 1024)
                if filters.get("max_size"): size_range["lte"] = int(filters["max_size"] * 1024 * 1024)
                es_filters.append({"range": {"size_bytes": size_range}})

        body = {
            "from": offset,
            "size": 10,
            "query": {
                "bool": {
                    "must": [],
                    "filter": es_filters
                }
            },
            "knn": {
                "field": "title_vector",
                "query_vector": query_vector,
                "k": 100,
                "num_candidates": 500,
                "filter": es_filters
            }
        }

        res = es.search(index="grimoire_files", body=body)
        results = []
        for hit in res['hits']['hits']:
            file = hit['_source']
            # Merge updated identity from SQLite
            meta = get_file_metadata_sync(file['name'])
            file['tags'] = meta['tags']
            file['owner'] = meta['owner']
            file['department'] = meta['department']
            results.append(file)
        return results
    except Exception as e:
        print(f"Error in search: {e}")
        return []
