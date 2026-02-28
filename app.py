from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
import os
import datetime
from werkzeug.utils import secure_filename
from search import mock_search_files
from elasticsearch import Elasticsearch

app = Flask(__name__)
app.secret_key = 'grimoire_super_secret'

# Initialize Elasticsearch Client
try:
    es = Elasticsearch("http://localhost:9200")
    # Tenta crear el índice si no existe de forma simple
    if not es.indices.exists(index="grimoire_files"):
        es.indices.create(index="grimoire_files")
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
                    date_str = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
                    ext = filename.split('.')[-1] if '.' in filename else 'file'
                    
                    from search import search_model
                    embedding = search_model.encode(filename).tolist()
                    
                    doc = {
                        "name": filename,
                        "size": size_str,
                        "type": ext,
                        "date": date_str,
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

@app.route('/api/search', methods=['GET'])
def search_api():
    query = request.args.get('q', '')
    offset = request.args.get('offset', 0, type=int)
    results = mock_search_files(query, offset=offset)
    return jsonify({"query": query, "results": results})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
