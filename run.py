#!/usr/bin/env python
"""
Punto de entrada de la aplicación Grimoire
"""
import os
from app import create_app, db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Provide objects for the Flask shell"""
    return {'db': db}

@app.cli.command()
def init_db():
    """Initialize the database with tables"""
    with app.app_context():
        db.create_all()
        print('Database initialized successfully!')

@app.cli.command()
def drop_db():
    """Drop all database tables"""
    if input('Are you sure you want to drop all tables? (yes/no): ').lower() == 'yes':
        with app.app_context():
            db.drop_all()
            print('Database dropped successfully!')

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
