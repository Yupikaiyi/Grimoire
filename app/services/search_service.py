"""
Lógica de búsqueda semántica
"""
import numpy as np
from app import db
from app.models import Document, SearchQuery
import google.generativeai as genai


class SearchService:
    """Servicio para búsqueda semántica en documentos"""
    
    def __init__(self):
        """Inicializar servicio"""
        pass
    
    def search(self, query_text, top_k=5):
        """
        Realizar búsqueda semántica en documentos.
        Retorna los documentos más relevantes.
        """
        try:
            # Get query embedding
            query_embedding = self._get_embedding(query_text)
            
            # Get all documents with embeddings
            documents = Document.query.filter(Document.embedding_vector.isnot(None)).all()
            
            if not documents:
                return {
                    'success': False,
                    'error': 'No documents with embeddings found. Please upload and process documents first.'
                }
            
            # Calculate similarity scores
            results = []
            for doc in documents:
                doc_embedding = self._parse_embedding(doc.embedding_vector)
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                
                results.append({
                    'document_id': doc.id,
                    'filename': doc.original_filename,
                    'similarity_score': float(similarity),
                    'summary': doc.summary[:200] if doc.summary else 'No summary available',
                    'created_at': doc.created_at.isoformat()
                })
            
            # Sort by similarity score and get top results
            results = sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:top_k]
            
            # Save search query
            if results:
                search_record = SearchQuery(
                    query_text=query_text,
                    document_id=results[0]['document_id'],
                    relevance_score=results[0]['similarity_score']
                )
                db.session.add(search_record)
                db.session.commit()
            
            return {
                'success': True,
                'query': query_text,
                'results': results
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_embedding(self, text):
        """Obtener embedding de texto usando Gemini"""
        try:
            model = genai.GenerativeModel('embedding-001')
            result = genai.embed_content(model_name='models/embedding-001', content=text)
            return np.array(result['embedding'])
        except Exception as e:
            raise Exception(f'Error generating embedding: {str(e)}')
    
    def _parse_embedding(self, embedding_str):
        """Parsear embedding guardado como string"""
        try:
            import json
            embedding_list = json.loads(embedding_str)
            return np.array(embedding_list)
        except:
            raise Exception('Invalid embedding format')
    
    def _cosine_similarity(self, vec1, vec2):
        """Calcular similitud coseno entre dos vectores"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm_vec1 = np.linalg.norm(vec1)
            norm_vec2 = np.linalg.norm(vec2)
            
            if norm_vec1 == 0 or norm_vec2 == 0:
                return 0.0
            
            return dot_product / (norm_vec1 * norm_vec2)
        except:
            return 0.0
