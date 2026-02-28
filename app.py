from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
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
    
    # Nuevo: Tabla de usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE, 
                  password_hash TEXT, 
                  department TEXT, 
                  is_admin BOOLEAN)''')
                  
    # Nuevo: Tabla de favoritos
    c.execute('''CREATE TABLE IF NOT EXISTS user_favorites
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  filename TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  UNIQUE(user_id, filename))''')
    
    # Nuevo: Tabla de recientes por usuario
    c.execute('''CREATE TABLE IF NOT EXISTS user_recent
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  filename TEXT,
                  accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Seed users if empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        users = [
            ('admin', generate_password_hash('admin123'), 'IT', True),
            ('juan_ventas', generate_password_hash('ventas123'), 'Ventas', False),
            ('ana_it', generate_password_hash('it123'), 'IT', False),
            ('pedro_marketing', generate_password_hash('mkt123'), 'Marketing', False)
        ]
        c.executemany("INSERT INTO users (username, password_hash, department, is_admin) VALUES (?, ?, ?, ?)", users)
    
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Login required"}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return jsonify({"error": "Admin privileges required"}), 403
        return f(*args, **kwargs)
    return decorated_function

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
    user = None
    if 'user_id' in session:
        user = {
            "username": session.get('username'),
            "department": session.get('department'),
            "is_admin": session.get('is_admin')
        }
    return render_template('index.html', user=user)

@app.route('/upload', methods=['POST'])
@login_required
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

    user_dept = session.get('department', '')
    user_name = session.get('username', '')
    uploaded_count = 0
    
    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Autotagging and identity assignment
            initial_tags = [user_dept.lower()] if user_dept else []
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO file_metadata (filename, tags, owner, department) VALUES (?, ?, ?, ?)",
                      (filename, json.dumps(initial_tags), user_name, user_dept))
            conn.commit()
            conn.close()

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
                        "tags": initial_tags,
                        "owner": user_name,
                        "department": user_dept,
                        "title_vector": embedding
                    }
                    es.index(index=ES_INDEX_NAME, id=filename, document=doc)
                except Exception as e:
                    print(f"Error indexando: {e}")
            uploaded_count += 1
            
    if uploaded_count > 0:
        flash(f'¡Subida completada! {uploaded_count} archivo(s) guardado(s).', 'success')
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash, department, is_admin FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['department'] = user[3]
            session['is_admin'] = bool(user[4])
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/search')
@login_required
def search_page():
    user = {
        "username": session.get('username'),
        "department": session.get('department'),
        "is_admin": session.get('is_admin')
    }
    return render_template('results.html', user=user)

@app.route('/api/search', methods=['GET'])
@login_required
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
        "type": request.args.get('type'),
        "user_dept": session.get('department'),
        "is_admin": session.get('is_admin')
    }
    results = mock_search_files(query, offset=offset, filters=filters)
    
    # Inject is_favorite flag
    user_id = session.get('user_id')
    if user_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT filename FROM user_favorites WHERE user_id = ?", (user_id,))
        favs = {row[0] for row in c.fetchall()}
        conn.close()
        for res in results:
            res['is_favorite'] = res['name'] in favs
            
    return jsonify({"query": query, "results": results, "user": {
        "username": session.get('username'),
        "department": session.get('department'),
        "is_admin": session.get('is_admin')
    }})

@app.route('/api/tags', methods=['GET'])
@login_required
def get_tags():
    return jsonify(get_all_tags_list())

@app.route('/api/file-types', methods=['GET'])
@login_required
def get_file_types():
    return jsonify(get_all_file_types())

@app.route('/api/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    filename = request.json.get('filename')
    if not filename: return jsonify({"error": "filename missing"}), 400
    user_id = session.get('user_id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM user_favorites WHERE user_id=? AND filename=?", (user_id, filename))
    existing = c.fetchone()
    if existing:
        c.execute("DELETE FROM user_favorites WHERE id=?", (existing[0],))
        is_fav = False
    else:
        c.execute("INSERT INTO user_favorites (user_id, filename) VALUES (?, ?)", (user_id, filename))
        is_fav = True
    conn.commit()
    conn.close()
    return jsonify({"success": True, "is_favorite": is_fav})

@app.route('/api/recent', methods=['GET'])
@login_required
def recent_files():
    user_id = session.get('user_id')
    is_admin = session.get('is_admin')
    user_dept = session.get('department')
    
    # Get the last 20 files accessed by this user, most recent first (deduplicated)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT filename FROM user_recent
        WHERE user_id = ?
        GROUP BY filename
        ORDER BY MAX(accessed_at) DESC
        LIMIT 6
    """, (user_id,))
    recent_files_list = [row[0] for row in c.fetchall()]
    
    # Fetch favorites for is_favorite flag
    c.execute("SELECT filename FROM user_favorites WHERE user_id = ?", (user_id,))
    favs = {row[0] for row in c.fetchall()}
    conn.close()
    
    if not recent_files_list:
        return jsonify({"results": []})
    
    # Fetch metadata from Elasticsearch
    results = []
    try:
        should_clauses = [{"term": {"name": f}} for f in recent_files_list]
        query_body = {
            "query": { "bool": { "should": should_clauses, "minimum_should_match": 1 } },
            "size": 6
        }
        res = es.search(index=ES_INDEX_NAME, body=query_body)
        hits_by_name = {hit['_source']['name']: hit['_source'] for hit in res['hits']['hits']}
        
        # Return in the order of recent access
        for fname in recent_files_list:
            if fname in hits_by_name:
                doc = hits_by_name[fname]
                dept = doc.get('department') or ''
                # Security check
                if is_admin or dept == user_dept or dept == '' or dept == 'Público':
                    doc['is_favorite'] = fname in favs
                    results.append(doc)
    except Exception as e:
        print("Error fetching recent files from ES:", e)
    
    return jsonify({"results": results})

@app.route('/api/favorites', methods=['GET'])
@login_required
def list_favorites():
    user_id = session.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename FROM user_favorites WHERE user_id = ?", (user_id,))
    fav_files = [row[0] for row in c.fetchall()]
    conn.close()
    
    results = []
    if fav_files:
        try:
            should_clauses = [{"term": {"name": f}} for f in fav_files]
            query_body = {
                "query": { "bool": { "should": should_clauses, "minimum_should_match": 1 } },
                "size": 50
            }
            res = es.search(index=ES_INDEX_NAME, body=query_body)
            
            is_admin = session.get('is_admin')
            user_dept = session.get('department')
            hits = res['hits']['hits']
            
            for hit in hits:
                doc = hit['_source']
                dept = doc.get('department', '')
                if dept is None: dept = ''
                
                if is_admin or dept == user_dept or dept == "" or dept == "Público":
                    doc['is_favorite'] = True
                    results.append(doc)
        except Exception as e:
            print("Error fetching favorites from ES:", e)
            
    return jsonify({"results": results})

@app.route('/api/check-duplicates', methods=['POST'])
@login_required
def check_duplicates():
    filenames = request.json.get('filenames', [])
    duplicates = []
    for name in filenames:
        safe = secure_filename(name)
        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], safe)):
            duplicates.append(name)
    return jsonify({"duplicates": duplicates})

@app.route('/api/files/<filename>')
@login_required
def get_file(filename):
    # Track file access for this user
    user_id = session.get('user_id')
    if user_id:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            # Keep only the last 50 accesses per user to avoid bloating the table
            c.execute("INSERT INTO user_recent (user_id, filename) VALUES (?, ?)", (user_id, filename))
            c.execute("""
                DELETE FROM user_recent WHERE id NOT IN (
                    SELECT id FROM user_recent WHERE user_id = ? ORDER BY accessed_at DESC LIMIT 50
                ) AND user_id = ?
            """, (user_id, user_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print("Error tracking recent file:", e)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/identity-options', methods=['GET'])
@login_required
def get_identity_options():
    user_dept = session.get('department', '')
    is_admin = session.get('is_admin', False)
    
    departments = get_all_departments() if is_admin else ([user_dept] if user_dept else [])
    
    return jsonify({
        "owners": get_all_owners(),
        "departments": departments
    })

@app.route('/api/files/<filename>/tags', methods=['POST'])
@login_required
def update_file_tags(filename):
    try:
        data = request.json
        tags = data.get('tags', [])
        save_file_tags(filename, tags)
        return jsonify({"success": True, "tags": tags})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files/<filename>/identity', methods=['POST'])
@login_required
@admin_required
def update_file_identity(filename):
    try:
        data = request.json
        owner = data.get('owner', '')
        department = data.get('department', '')
        save_file_identity(filename, owner, department)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin')
@admin_required
def admin_page():
    user = {
        "username": session.get('username'),
        "department": session.get('department'),
        "is_admin": session.get('is_admin')
    }
    return render_template('admin.html', user=user)

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, department, is_admin FROM users")
    users = [{"id": r[0], "username": r[1], "department": r[2], "is_admin": bool(r[3])} for r in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/admin/users/<int:user_id>/department', methods=['POST'])
@admin_required
def update_user_department(user_id):
    data = request.json
    new_dept = data.get('department')
    if not new_dept:
        return jsonify({"error": "Department is required"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET department = ? WHERE id = ?", (new_dept, user_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/departments-list', methods=['GET'])
@login_required
def get_departments_list():
    # Return a predefined list of valid departments for the admin dropdown
    return jsonify(["Ventas", "IT", "Marketing", "Administración", "Recursos Humanos", "Finanzas", "Logística"])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
