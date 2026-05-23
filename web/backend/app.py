import os
import sys
import uuid
import hashlib
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import numpy as np

# Resolve system paths to load local python modules
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

app = Flask(__name__)
# Enable CORS for frontend integration
CORS(app)

# Standardized folder structures inside workspace data/ folder
UPLOAD_FOLDER = os.path.join(ROOT_DIR, 'data', 'uploads')
STEGO_FOLDER = os.path.join(ROOT_DIR, 'data', 'stego')
VISUALIZATION_FOLDER = os.path.join(ROOT_DIR, 'data', 'visualizations')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STEGO_FOLDER, exist_ok=True)
os.makedirs(VISUALIZATION_FOLDER, exist_ok=True)


def safe_save(file_obj, folder, prefix=''):
    """Saves a file securely to the given folder using a unique UUID."""
    ext = os.path.splitext(file_obj.filename)[1]
    name = f"{prefix}{uuid.uuid4().hex}{ext}"
    path = os.path.join(folder, name)
    file_obj.save(path)
    return name, path


@app.errorhandler(Exception)
def handle_exception(e):
    """Global JSON error handler for unexpected errors or exceptions."""
    import traceback
    traceback.print_exc()
    message = str(e)
    code = 500
    if hasattr(e, 'code'):
        code = e.code
    return jsonify({"error": message}), code


@app.route('/', methods=['GET'])
def index():
    """Health status endpoint."""
    return jsonify({"status": "Flask API running"})


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Stages an audio file by saving it to standard upload folder."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    name, path = safe_save(request.files['file'], UPLOAD_FOLDER, prefix='upload_')
    return jsonify({"filename": name, "original_name": request.files['file'].filename})


@app.route('/api/embed', methods=['POST'])
def api_embed():
    """Embeds a payload into a staged cover WAV container using robust adaptive steganography."""
    if 'cover' not in request.files:
        return jsonify({"error": "No cover audio file provided"}), 400
        
    cover_file = request.files['cover']
    message_text = request.form.get('message', '')
    password = request.form.get('password', '')
    encrypt = request.form.get('encrypt', 'true') == 'true'
    energy_percentile = float(request.form.get('energy_percentile', 20.0))
    robust_repeat = int(request.form.get('robust_repeat', 1))
    
    # Securely save the uploaded cover file
    cover_name, cover_path = safe_save(cover_file, UPLOAD_FOLDER, prefix='cover_')
    
    # Stego filename & path in standardized output folder
    stego_name = f"stego_{cover_name}"
    stego_path = os.path.join(STEGO_FOLDER, stego_name)
    
    # Cryptographic AES Key derivation from passphrase
    h = hashlib.sha256(password.encode('utf-8')).digest()
    key_bytes = h[:16]
    
    # Run the adaptive keyed steganographic embedding function
    from src.embed import embed_adaptive_keyed
    embed_adaptive_keyed(
        cover_wav_path=cover_path,
        plaintext=message_text.encode('utf-8'),
        out_wav_path=stego_path,
        user_key=key_bytes,
        energy_percentile=energy_percentile,
        encrypt=encrypt,
        robust_repeat=robust_repeat
    )
    
    # Compute cover vs stego metrics (SNR & LSB BER)
    from src.metrics import compute_snr_db, compute_lsb_ber, compute_ber
    snr_val = compute_snr_db(cover_path, stego_path)
    lsb_ber_val = compute_lsb_ber(cover_path, stego_path)
    
    # Verify exact extraction by performing in-memory check to evaluate payload BER
    from src.extract import extract_adaptive_keyed
    extracted_plain = extract_adaptive_keyed(
        stego_wav_path=stego_path,
        user_key=key_bytes,
        energy_percentile=energy_percentile,
        decrypt=encrypt,
        robust_repeat=robust_repeat
    )
    
    payload_ber_val = 0.0
    msg_bytes = message_text.encode('utf-8')
    if msg_bytes:
        bits_a = np.unpackbits(np.frombuffer(msg_bytes, dtype=np.uint8)).astype(np.uint8)
        if extracted_plain is None:
            payload_ber_val = 1.0
        else:
            bits_b = np.unpackbits(np.frombuffer(extracted_plain, dtype=np.uint8)).astype(np.uint8)
            min_len = min(bits_a.size, bits_b.size)
            if min_len > 0:
                payload_ber_val = compute_ber(bits_a[:min_len], bits_b[:min_len])
                if bits_a.size != bits_b.size:
                    mismatch_count = abs(bits_a.size - bits_b.size)
                    payload_ber_val = (payload_ber_val * min_len + mismatch_count) / max(bits_a.size, bits_b.size)
            else:
                payload_ber_val = 1.0
                
    return jsonify({
        "stego_filename": stego_name,
        "cover_filename": cover_name,
        "original_name": cover_file.filename,
        "timestamp": time.time(),
        "snr_db": float(snr_val),
        "lsb_ber": float(lsb_ber_val),
        "payload_ber": float(payload_ber_val)
    })


@app.route('/api/extract', methods=['POST'])
def api_extract():
    """Extracts message payload from a staged stego WAV container."""
    password = request.form.get('password', '')
    if 'stego' in request.files:
        stego_name, stego_path = safe_save(request.files['stego'], UPLOAD_FOLDER, prefix='extr_')
    else:
        stego_name = request.form.get('stego_filename')
        if not stego_name:
            return jsonify({"error": "No stego file name or carrier uploaded."}), 400
        # Resolve target carrier from stego or uploads folders
        stego_path = os.path.join(STEGO_FOLDER, stego_name)
        if not os.path.exists(stego_path):
            stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
            
    if not os.path.exists(stego_path):
        return jsonify({"error": "Stego file not found on server."}), 404
        
    h = hashlib.sha256(password.encode('utf-8')).digest()
    key_bytes = h[:16]
    
    energy_percentile = float(request.form.get('energy_percentile', 0.0))
    robust_repeat = int(request.form.get('robust_repeat', 1))
    encrypt = request.form.get('encrypt', 'true') == 'true'
    
    from src.extract import extract_adaptive_keyed
    plaintext = extract_adaptive_keyed(
        stego_wav_path=stego_path,
        user_key=key_bytes,
        energy_percentile=energy_percentile,
        decrypt=encrypt,
        robust_repeat=robust_repeat
    )
    
    if plaintext is None:
        return jsonify({"error": "Extraction failed. Verification failed or payload is corrupted."}), 400
        
    return jsonify({"message": plaintext.decode('utf-8', errors='ignore')})


@app.route('/api/download/<filename>')
def api_download(filename):
    """Downloads a staged generated file."""
    if os.path.exists(os.path.join(STEGO_FOLDER, filename)):
        return send_from_directory(STEGO_FOLDER, filename, as_attachment=True)
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


@app.route('/api/visualize/<plot_type>')
def api_visualize(plot_type):
    """Renders and serves non-blocking comparative signal analytics charts."""
    import matplotlib
    matplotlib.use('Agg')
    
    cover_name = request.args.get('cover')
    stego_name = request.args.get('stego')
    if not cover_name or not stego_name:
        return jsonify({"error": "Missing cover or stego filename"}), 400
        
    # Resolve files from standardized directory structure
    cover_path = os.path.join(UPLOAD_FOLDER, cover_name)
    if not os.path.exists(cover_path):
        cover_path = os.path.join(STEGO_FOLDER, cover_name)
        
    stego_path = os.path.join(STEGO_FOLDER, stego_name)
    if not os.path.exists(stego_path):
        stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
        
    if not os.path.exists(cover_path) or not os.path.exists(stego_path):
        return jsonify({"error": "Audio carrier files not found on server."}), 404
        
    out_name = f"{plot_type}_{uuid.uuid4().hex}.png"
    out_path = os.path.join(VISUALIZATION_FOLDER, out_name)
    
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
        return jsonify({"error": "Invalid plot type"}), 400
        
    return send_file(out_path, mimetype='image/png')


@app.route('/api/ml/features')
def api_ml_features():
    """Extracts raw acoustic features from audio carrier files."""
    audio_name = request.args.get('audio')
    if not audio_name:
        return jsonify({"error": "Missing audio filename"}), 400
        
    audio_path = os.path.join(STEGO_FOLDER, audio_name)
    if not os.path.exists(audio_path):
        audio_path = os.path.join(UPLOAD_FOLDER, audio_name)
        
    if not os.path.exists(audio_path):
        return jsonify({"error": "Audio file not found."}), 404
        
    from src.detectability_ml import extract_audio_features
    feats = extract_audio_features(audio_path)
    return jsonify(feats)


@app.route('/api/ml/mse')
def api_ml_mse():
    """Computes Mean Squared Error divergence metrics."""
    cover_name = request.args.get('cover')
    stego_name = request.args.get('stego')
    if not cover_name or not stego_name:
        return jsonify({"error": "Missing arguments"}), 400
        
    cover_path = os.path.join(UPLOAD_FOLDER, cover_name)
    if not os.path.exists(cover_path):
        cover_path = os.path.join(STEGO_FOLDER, cover_name)
        
    stego_path = os.path.join(STEGO_FOLDER, stego_name)
    if not os.path.exists(stego_path):
        stego_path = os.path.join(UPLOAD_FOLDER, stego_name)
        
    if not os.path.exists(cover_path) or not os.path.exists(stego_path):
        return jsonify({"error": "Audio files not found."}), 404
        
    from src.detectability_ml import compute_mse
    mse = compute_mse(cover_path, stego_path)
    return jsonify({"mse": mse})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
