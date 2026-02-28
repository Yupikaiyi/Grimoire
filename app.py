from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'grimoire_super_secret'
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            uploaded_count += 1
            
    if uploaded_count > 0:
        flash(f'¡Subida completada! {uploaded_count} archivo(s) guardado(s) correctamente.', 'success')
    else:
        flash('Error: Hubo un problema al guardar los archivos.', 'error')
        
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
