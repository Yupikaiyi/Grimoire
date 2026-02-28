"""
Inicializa la aplicación Flask
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name='development'):
    """Factory function to create and configure Flask app"""
    app = Flask(__name__)
    
    # Configure app
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    if config_name == 'development':
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "database.db")}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['DEBUG'] = True
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
        app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
        app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file upload
    
    # Ensure upload and instance folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    from app.routes import bp
    app.register_blueprint(bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
