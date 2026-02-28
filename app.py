from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
import os
import datetime
from werkzeug.utils import secure_filename
from search import mock_search_files
from elasticsearch import Elasticsearch
import json
import sqlite3

app = Flask(__name__)
app.secret_key = 'grimoire_super_secret'

app.config['UPLOAD_FOLDER'] = 'testfiles'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración de la base de datos SQLite para metadatos (Tags, Owner, Dept)
DB_PATH = 'grimoire.db'
ES_INDEX_NAME = "grimoire_files"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS file_metadata
                 (filename TEXT PRIMARY KEY, tags TEXT, owner TEXT, department TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_file_metadata(filename):
    conn = sqlite3.connect(DB_PATH)
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

def save_file_tags(filename, tags):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM file_metadata WHERE filename = ?", (filename,))
    if c.fetchone()[0] > 0:
        c.execute("UPDATE file_metadata SET tags = ? WHERE filename = ?", (json.dumps(tags), filename))
    else:
        c.execute("INSERT INTO file_metadata (filename, tags) VALUES (?, ?)", (filename, json.dumps(tags)))
    conn.commit()
    conn.close()
    sync_metadata_to_es(filename)

def save_file_identity(filename, owner, department):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM file_metadata WHERE filename = ?", (filename,))
    if c.fetchone()[0] > 0:
        c.execute("UPDATE file_metadata SET owner = ?, department = ? WHERE filename = ?", (owner, department, filename))
    else:
        c.execute("INSERT INTO file_metadata (filename, owner, department) VALUES (?, ?, ?)", (filename, owner, department))
    conn.commit()
    conn.close()
    sync_metadata_to_es(filename)

def get_all_tags_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT tags FROM file_metadata")
    rows = c.fetchall()
    conn.close()
    all_tags = set()
    for row in rows:
        if row[0]:
            tags = json.loads(row[0])
            for t in tags:
                all_tags.add(t)
    return sorted(list(all_tags))

def get_all_owners():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT owner FROM file_metadata WHERE owner IS NOT NULL AND owner != ''")
    data = [row[0] for row in c.fetchall()]
    conn.close()
    return data

def get_all_departments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT department FROM file_metadata WHERE department IS NOT NULL AND department != ''")
    data = [row[0] for row in c.fetchall()]
    conn.close()
    return data

def get_all_file_types():
    if not es: return []
    try:
        # Use ES aggregation to get unique types
        res = es.search(index=ES_INDEX_NAME, body={
            "size": 0,
            "aggs": {
                "unique_types": {
                    "terms": {"field": "type", "size": 100}
                }
            }
        })
        return [bucket['key'] for bucket in res['aggregations']['unique_types']['buckets']]
    except Exception as e:
        print(f"Error fetching types: {e}")
        return []

# Initialize Elasticsearch Client
try:
    es = Elasticsearch("http://localhost:9200")
    if not es.indices.exists(index=ES_INDEX_NAME):
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
                    "owner": {"type": "keyword"},
                    "department": {"type": "keyword"},
                    "title_vector": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            }
        }
        es.indices.create(index=ES_INDEX_NAME, body=mapping)
except Exception as e:
    print(f"Error connecting to Elasticsearch: {e}")
    es = None

def sync_metadata_to_es(filename):
    if not es: return
    meta = get_file_metadata(filename)
    try:
        res = es.search(index=ES_INDEX_NAME, query={"term": {"name": filename}})
        if res['hits']['total']['value'] > 0:
            doc_id = res['hits']['hits'][0]['_id']
            es.update(index=ES_INDEX_NAME, id=doc_id, body={
                "doc": {
                    "tags": meta['tags'],
                    "owner": meta['owner'],
                    "department": meta['department']
                }
            })
    except Exception as e:
        print(f"Error syncing to ES: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('home'))
        
    files = request.files.getlist('file')
    local_metadata = request.form.get('local_metadata')
    local_metadata_parsed = {}
    if local_metadata:
        try:
            items = json.loads(local_metadata)
            local_metadata_parsed = {item['name']: item['lastModified'] for item in items}
        except: pass

    uploaded_count = 0
    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if es:
                try:
                    stat = os.stat(filepath)
                    size_kb = stat.st_size / 1024
                    size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"
                    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
                    
                    if filename in local_metadata_parsed:
                        creation_date_str = local_metadata_parsed[filename]
                    else:
                        creation_date_str = datetime.datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d')
                        
                    from search import search_model
                    embedding = search_model.encode(filename).tolist()
                    
                    doc = {
                        "name": filename,
                        "size": size_str,
                        "size_bytes": stat.st_size,
                        "type": filename.split('.')[-1] if '.' in filename else 'file',
                        "date": date_str,
                        "creation_date": creation_date_str,
                        "tags": [],
                        "owner": "",
                        "department": "",
                        "title_vector": embedding
                    }
                    es.index(index=ES_INDEX_NAME, document=doc)
                except Exception as e:
                    print(f"Error indexando: {e}")
            uploaded_count += 1
            
    if uploaded_count > 0:
        flash(f'¡Subida completada! {uploaded_count} archivo(s) guardado(s).', 'success')
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/files/<path:filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/search')
def search_page():
    return render_template('results.html')

@app.route('/api/search', methods=['GET'])
def search_api():
    query = request.args.get('q', '')
    offset = request.args.get('offset', 0, type=int)
    filters = {
        "min_size": request.args.get('min_size', type=float),
        "max_size": request.args.get('max_size', type=float),
        "upload_date_range": request.args.get('upload_date_range'),
        "creation_date_range": request.args.get('creation_date_range'),
        "tags": request.args.getlist('tags'),
        "owner": request.args.get('owner'),
        "department": request.args.get('department'),
        "type": request.args.get('type')
    }
    results = mock_search_files(query, offset=offset, filters=filters)
    return jsonify({"query": query, "results": results})

@app.route('/api/tags', methods=['GET'])
def get_tags():
    return jsonify(get_all_tags_list())

@app.route('/api/file-types', methods=['GET'])
def get_file_types():
    return jsonify(get_all_file_types())

@app.route('/api/identity-options', methods=['GET'])
def get_identity_options():
    return jsonify({
        "owners": get_all_owners(),
        "departments": get_all_departments()
    })

@app.route('/api/files/<filename>/tags', methods=['POST'])
def update_file_tags(filename):
    try:
        data = request.json
        tags = data.get('tags', [])
        save_file_tags(filename, tags)
        return jsonify({"success": True, "tags": tags})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files/<filename>/identity', methods=['POST'])
def update_file_identity(filename):
    try:
        data = request.json
        owner = data.get('owner', '')
        department = data.get('department', '')
        save_file_identity(filename, owner, department)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
