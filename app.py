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

# Configuración de la base de datos SQLite para metadatos (Tags)
DB_PATH = 'grimoire.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS file_tags 
                 (filename TEXT PRIMARY KEY, tags TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_tags_from_db(filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT tags FROM file_tags WHERE filename = ?", (filename,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def save_tags_to_db(filename, tags):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO file_tags (filename, tags) VALUES (?, ?)", 
              (filename, json.dumps(tags)))
    conn.commit()
    conn.close()

def get_all_tags_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT tags FROM file_tags")
    rows = c.fetchall()
    conn.close()
    all_tags = set()
    for row in rows:
        tags = json.loads(row[0])
        for t in tags:
            all_tags.add(t)
    return sorted(list(all_tags))

# Initialize Elasticsearch Client
try:
    es = Elasticsearch("http://localhost:9200")
    if not es.indices.exists(index="grimoire_files"):
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
        es.indices.create(index="grimoire_files", body=mapping)
        print("Índice 'grimoire_files' creado con mapeo correcto.")
except Exception as e:
    print(f"Error connecting to Elasticsearch: {e}")
    es = None
app.config['UPLOAD_FOLDER'] = 'testfiles'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Error: No se ha enviado ninguna parte de archivo.', 'error')
        return redirect(url_for('home'))
        
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('Error: No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('home'))
        
    uploaded_count = 0
    import json
    local_metadata = request.form.get('local_metadata')
    local_metadata_parsed = {}
    if local_metadata:
        try:
            items = json.loads(local_metadata)
            local_metadata_parsed = {item['name']: item['lastModified'] for item in items}
        except Exception as e:
            print(f"Error parsing local_metadata: {e}")

    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Indexar en Elasticsearch
            if es:
                try:
                    stat = os.stat(filepath)
                    size_kb = stat.st_size / 1024
                    size_str = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"
                    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
                    
                    # Priorizar la fecha enviada desde el front (lastModified real)
                    if filename in local_metadata_parsed:
                        creation_date_str = local_metadata_parsed[filename]
                    else:
                        creation_date_str = datetime.datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d')
                        
                    ext = filename.split('.')[-1] if '.' in filename else 'file'
                    
                    from search import search_model
                    embedding = search_model.encode(filename).tolist()
                    
                    doc = {
                        "name": filename,
                        "size": size_str,
                        "size_bytes": stat.st_size,
                        "type": ext,
                        "date": date_str,
                        "creation_date": creation_date_str,
                        "tags": [],
                        "title_vector": embedding
                    }
                    es.index(index="grimoire_files", document=doc)
                except Exception as e:
                    print(f"Error indexando en ES {filename}: {e}")
            
            uploaded_count += 1
            
    if uploaded_count > 0:
        flash(f'¡Subida completada! {uploaded_count} archivo(s) guardado(s) correctamente.', 'success')
    else:
        flash('Error: Hubo un problema al guardar los archivos.', 'error')
        
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
    
    # Metadata filters
    filters = {
        "min_size": request.args.get('min_size', type=float), # in MB
        "max_size": request.args.get('max_size', type=float),
        "upload_date_range": request.args.get('upload_date_range'),
        "creation_date_range": request.args.get('creation_date_range'),
        "tags": request.args.getlist('tags') # Permite múltiples tags
    }
    
    results = mock_search_files(query, offset=offset, filters=filters)
    return jsonify({"query": query, "results": results})

@app.route('/api/tags', methods=['GET'])
def get_all_tags():
    try:
        tags = get_all_tags_list()
        return jsonify(tags)
    except Exception as e:
        print(f"Error fetching tags: {e}")
        return jsonify([])

@app.route('/api/files/<filename>/tags', methods=['POST'])
def update_file_tags(filename):
    try:
        data = request.json
        tags = data.get('tags', [])
        
        # 1. Guardar en SQLite (Base de datos persistente)
        save_tags_to_db(filename, tags)
        
        # 2. Sincronizar con Elasticsearch (Para filtrado rápido)
        if es:
            # Buscar el ID del documento por nombre
            res = es.search(index="grimoire_files", query={"term": {"name": filename}})
            if res['hits']['total']['value'] > 0:
                doc_id = res['hits']['hits'][0]['_id']
                es.update(index="grimoire_files", id=doc_id, doc={"tags": tags})
                print(f"Sincronizado {filename} con ES.")
            else:
                print(f"Advertencia: {filename} no encontrado en ES para sincronizar tags.")
        
        return jsonify({"status": "success", "tags": tags})
    except Exception as e:
        print(f"Error updating tags for {filename}: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
