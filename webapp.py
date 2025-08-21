from flask import Flask, request, send_file, render_template
import os
from subtitle_workflow import translate_subtitles

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    file = request.files['file']
    src_lang = request.form['src_lang']
    tgt_lang = request.form['tgt_lang']
    polish_only = request.form.get('polish_only', 'false') == 'true'
    filename = file.filename
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)
    output_path, _, _ = translate_subtitles(upload_path, src_lang, tgt_lang, polish_only=polish_only)
    result_filename = os.path.basename(output_path)
    result_path = os.path.join(RESULT_FOLDER, result_filename)
    os.rename(output_path, result_path)
    return send_file(result_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
