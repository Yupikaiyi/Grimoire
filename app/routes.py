"""
Definición de rutas de la aplicación
"""
from flask import Blueprint, render_template, request, jsonify, send_from_directory
from app.services.file_service import FileService
from app.services.ai_service import AIService
from app.services.search_service import SearchService

bp = Blueprint('main', __name__)

file_service = FileService()
ai_service = AIService()
search_service = SearchService()


@bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@bp.route('/about')
def about():
    """Página acerca de"""
    return render_template('about.html')


@bp.route('/api/upload', methods=['POST'])
def upload_file():
    """Endpoint para subir archivos"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        result = file_service.save_file(file)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/extract-text/<int:document_id>', methods=['POST'])
def extract_text(document_id):
    """Endpoint para extraer texto de documentos"""
    try:
        result = file_service.extract_text(document_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/summarize/<int:document_id>', methods=['POST'])
def summarize_document(document_id):
    """Endpoint para resumir documentos"""
    try:
        result = ai_service.summarize(document_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/search', methods=['POST'])
def search_documents():
    """Endpoint para búsqueda semántica"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        results = search_service.search(query)
        return jsonify({'results': results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/uploads/<filename>')
def download_file(filename):
    """Endpoint para descargar archivos"""
    return send_from_directory('uploads', filename)
