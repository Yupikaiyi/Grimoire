"""
Modelos de base de datos
"""
from datetime import datetime
from app import db


class Document(db.Model):
    """Modelo para documentos subidos"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    extracted_text = db.Column(db.Text)
    summary = db.Column(db.Text)
    embedding_vector = db.Column(db.Text)  # Store embedding as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'


class SearchQuery(db.Model):
    """Modelo para búsquedas guardadas"""
    __tablename__ = 'search_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.String(500), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    relevance_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('Document', backref=db.backref('searches', lazy=True))
    
    def __repr__(self):
        return f'<SearchQuery {self.query_text}>'
