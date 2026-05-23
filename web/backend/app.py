import os
import sys
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import tempfile
import time

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'stegcore_uploads')
PICS_FOLDER = os.path.join(tempfile.gettempdir(), 'stegcore_pics')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PICS_FOLDER, exist_ok=True)

def safe_save(file_obj, prefix=''):
    ext = os.path.splitext(file_obj.filename)[1]
    name = f"{prefix}{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_FOLDER, name)
    file_obj.save(path)
    return name, path

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Flask API running"})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    name, path = safe_save(request.files['file'], prefix='upload_')
    return jsonify({"filename": name, "original_name": request.files['file'].filename})

@app.route('/api/embed', methods=['POST'])
def api_embed():
    try:
        cover_file = request.files['cover']
        message_text = request.form.get('message', '')
        password = request.form.get('password', '')
        encrypt = request.form.get('encrypt') == 'true'
        energy_percentile = float(request.form.get('energy_percentile', 20.0))
        robust_repeat = int(request.form.get('robust_repeat', 1))
        
        cover_name, cover_path = safe_save(cover_file, prefix='cover_')
        stego_name = f"stego_{cover_name}"
        stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
        
        from src.embed import embed_adaptive_keyed
        embed_adaptive_keyed(
            cover_wav_path=cover_path,
            plaintext=message_text.encode('utf-8'),
            out_wav_path=stego_path,
            user_key=password,
            energy_percentile=energy_percentile,
            encrypt=encrypt,
            robust_repeat=robust_repeat
        )
        
        return jsonify({
            "stego_filename": stego_name,
            "cover_filename": cover_name,
            "original_name": cover_file.filename,
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/extract', methods=['POST'])
def api_extract():
    try:
        password = request.form.get('password', '')
        if 'stego' in request.files:
            stego_name, stego_path = safe_save(request.files['stego'], prefix='extr_')
        else:
            stego_name = request.form.get('stego_filename')
            stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
        
        from src.extract import extract_adaptive_keyed
        plaintext = extract_adaptive_keyed(stego_wav_path=stego_path, user_key=password)
        return jsonify({"message": plaintext.decode('utf-8')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>')
def api_download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/api/visualize/<plot_type>')
def api_visualize(plot_type):
    import matplotlib
    matplotlib.use('Agg')
    cover_name = request.args.get('cover')
    stego_name = request.args.get('stego')
    if not cover_name or not stego_name:
        return "Missing cover or stego filename", 400
    
    cover_path = os.path.join(UPLOAD_FOLDER, cover_name)
    stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
    
    out_name = f"{plot_type}_{uuid.uuid4().hex}.png"
    out_path = os.path.join(PICS_FOLDER, out_name)
    
    try:
        from src.visualize import (
            plot_waveform_comparison, 
            plot_spectrogram_comparison, 
            plot_snr_and_noise, 
            plot_bit_difference_heatmap
        )
        if plot_type == 'waveform':
            plot_waveform_comparison(cover_path, stego_path, save_path=out_path)
        elif plot_type == 'spectrogram':
            plot_spectrogram_comparison(cover_path, stego_path, save_path=out_path)
        elif plot_type == 'snr':
            plot_snr_and_noise(cover_path, stego_path, save_path=out_path)
        elif plot_type == 'heatmap':
            plot_bit_difference_heatmap(cover_path, stego_path, save_path=out_path)
        else:
            return "Invalid plot type", 400
            
        return send_file(out_path, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/features')
def api_ml_features():
    audio_name = request.args.get('audio')
    if not audio_name:
        return "Missing audio filename", 400
    audio_path = os.path.join(UPLOAD_FOLDER, audio_name)
    try:
        from src.detectability_ml import extract_audio_features
        feats = extract_audio_features(audio_path)
        return jsonify(feats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/mse')
def api_ml_mse():
    cover_name = request.args.get('cover')
    stego_name = request.args.get('stego')
    if not cover_name or not stego_name:
        return "Missing arguments", 400
    cover_path = os.path.join(UPLOAD_FOLDER, cover_name)
    stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
    try:
        from src.detectability_ml import compute_mse
        mse = compute_mse(cover_path, stego_path)
        return jsonify({"mse": mse})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000>
