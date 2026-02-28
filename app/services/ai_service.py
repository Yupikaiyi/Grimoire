"""
Servicio de resumen con Google Gemini API
"""
import os
import google.generativeai as genai
from app import db
from app.models import Document


class AIService:
    """Servicio para utilizar la API de Gemini"""
    
    def __init__(self):
        """Inicializar servicio con API key"""
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
    
    def summarize(self, document_id):
        """Resumir documento usando Gemini"""
        try:
            document = Document.query.get(document_id)
            if not document:
                return {'success': False, 'error': 'Document not found'}
            
            if not document.extracted_text:
                return {'success': False, 'error': 'No text extracted. Please extract text first.'}
            
            # Call Gemini API for summarization
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Please provide a concise summary of the following text in the same language it is written.
            The summary should be 2-3 paragraphs and capture the main points.
            
            Text:
            {document.extracted_text}
            """
            
            response = model.generate_content(prompt)
            summary = response.text
            
            # Save summary to database
            document.summary = summary
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Summary generated successfully',
                'summary': summary,
                'document_id': document_id
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def analyze_sentiment(self, text):
        """Analizar sentimiento del texto"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Analyze the sentiment of the following text and respond with a JSON object containing:
            - sentiment: positive, negative, or neutral
            - confidence: a score from 0 to 1
            - explanation: brief explanation
            
            Text: {text}
            """
            
            response = model.generate_content(prompt)
            return {'success': True, 'result': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
