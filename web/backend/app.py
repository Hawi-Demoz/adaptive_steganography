import os
import sys
import uuid
import hashlib
import time
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import numpy as np
import soundfile as sf
from werkzeug.utils import secure_filename

# Resolve system paths to load local python modules
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

app = Flask(__name__)
# Enable CORS for frontend integration
CORS(app)

# Standardized folder structures inside workspace data/ folder
UPLOAD_FOLDER = os.path.join(BACKEND_DIR, 'uploads')
STEGO_FOLDER = os.path.join(BACKEND_DIR, 'generated')
VISUALIZATION_FOLDER = os.path.join(ROOT_DIR, 'data', 'visualizations')
SESSION_REGISTRY_FILE = os.path.join(STEGO_FOLDER, 'session_registry.json')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STEGO_FOLDER, exist_ok=True)
os.makedirs(VISUALIZATION_FOLDER, exist_ok=True)


def _load_registry():
    if not os.path.exists(SESSION_REGISTRY_FILE):
        return []
    try:
        with open(SESSION_REGISTRY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_registry(registry_data):
    try:
        with open(SESSION_REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(registry_data, f, indent=2)
    except Exception:
        pass


def json_error(message, status_code=400):
    return jsonify({"error": message}), status_code


def parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def validate_wav_file(path):
    try:
        info = sf.info(path)
    except Exception:
        return False
    return info.format == 'WAV'


def safe_save(file_obj, folder, prefix=''):
    """Saves a file securely to the given folder using a unique UUID."""
    original_name = secure_filename(file_obj.filename or '')
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in {'.wav'}:
        ext = '.wav'
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


@app.route('/api/session/files', methods=['GET'])
def api_session_files():
    """Returns the list of dynamically generated stego files from the server's session registry."""
    return jsonify(_load_registry())


@app.route('/api/embed', methods=['POST'])
def api_embed():
    """Embeds a payload into a staged cover WAV container using robust adaptive steganography."""
    cover_file = request.files.get('cover')
    if cover_file is None or not cover_file.filename:
        return json_error("Missing cover WAV file.")

    original_name = cover_file.filename
    if not original_name.lower().endswith('.wav'):
        return json_error("Only WAV files are supported for cover uploads.")

    message_text = request.form.get('message')
    password = request.form.get('password')
    if message_text is None or message_text == '':
        return json_error("Missing message field.")
    if password is None or password == '':
        return json_error("Missing password field.")

    encrypt = parse_bool(request.form.get('encrypt'), default=False)

    energy_raw = request.form.get('energy_percentile', '0.0')
    robust_raw = request.form.get('robust_repeat', '1')
    try:
        energy_percentile = float(energy_raw)
    except ValueError:
        return json_error("energy_percentile must be a number.")
    try:
        robust_repeat = int(robust_raw)
    except ValueError:
        return json_error("robust_repeat must be an integer.")

    if energy_percentile < 0.0 or energy_percentile >= 100.0:
        return json_error("energy_percentile must be in the range [0, 100).")
    if robust_repeat < 1 or robust_repeat % 2 == 0:
        return json_error("robust_repeat must be an odd integer greater than or equal to 1.")

    cover_name, cover_path = safe_save(cover_file, UPLOAD_FOLDER, prefix='cover_')
    if not validate_wav_file(cover_path):
        try:
            os.remove(cover_path)
        except OSError:
            pass
        return json_error("Uploaded cover file is not a valid WAV file.")

    stego_name = f"stego_{uuid.uuid4().hex}.wav"
    stego_path = os.path.join(STEGO_FOLDER, stego_name)

    h = hashlib.sha256(password.encode('utf-8')).digest()
    key_bytes = h[:16]

    try:
        from src.embed import embed_adaptive_keyed
        embed_adaptive_keyed(
            cover_wav_path=cover_path,
            plaintext=message_text.encode('utf-8'),
            out_wav_path=stego_path,
            user_key=key_bytes,
            energy_percentile=energy_percentile,
            encrypt=encrypt,
            robust_repeat=robust_repeat,
        )
    except Exception as exc:
        try:
            if os.path.exists(stego_path):
                os.remove(stego_path)
        except OSError:
            pass
        return json_error(str(exc), 400)

    from src.metrics import compute_snr_db, compute_lsb_ber, compute_ber
    snr_val = compute_snr_db(cover_path, stego_path)
    lsb_ber_val = compute_lsb_ber(cover_path, stego_path)

    payload_ber_val = None
    try:
        from src.extract import extract_adaptive_keyed
        extracted_plain = extract_adaptive_keyed(
            stego_wav_path=stego_path,
            user_key=key_bytes,
            energy_percentile=energy_percentile,
            decrypt=encrypt,
            robust_repeat=robust_repeat,
        )
        msg_bytes = message_text.encode('utf-8')
        if msg_bytes:
            if extracted_plain is None:
                payload_ber_val = 1.0
            else:
                bits_a = np.unpackbits(np.frombuffer(msg_bytes, dtype=np.uint8)).astype(np.uint8)
                bits_b = np.unpackbits(np.frombuffer(extracted_plain, dtype=np.uint8)).astype(np.uint8)
                min_len = min(bits_a.size, bits_b.size)
                if min_len == 0:
                    payload_ber_val = 1.0
                else:
                    ber = compute_ber(bits_a[:min_len], bits_b[:min_len])
                    if bits_a.size == bits_b.size:
                        payload_ber_val = ber
                    else:
                        mismatch_count = abs(bits_a.size - bits_b.size)
                        payload_ber_val = ((ber * min_len) + mismatch_count) / max(bits_a.size, bits_b.size)
        else:
            payload_ber_val = 0.0
    except Exception:
        payload_ber_val = None

    # Track in registry
    entry = {
        "stego_filename": stego_name,
        "cover_filename": cover_name,
        "original_name": original_name,
        "timestamp": time.time(),
        "energy_percentile": energy_percentile,
        "encrypt": encrypt,
        "robust_repeat": robust_repeat
    }
    registry = _load_registry()
    registry.append(entry)
    _save_registry(registry)

    return jsonify({
        "stego_filename": stego_name,
        "cover_filename": cover_name,
        "original_name": original_name,
        "timestamp": time.time(),
        "energy_percentile": energy_percentile,
        "encrypt": encrypt,
        "robust_repeat": robust_repeat,
        "snr_db": float(snr_val),
        "lsb_ber": float(lsb_ber_val),
        "payload_ber": None if payload_ber_val is None else float(payload_ber_val),
    })


@app.route('/api/extract', methods=['POST'])
def api_extract():
    """Extracts message payload from a staged stego WAV container."""
    try:
        print("FORM:", request.form)
        print("FILES:", request.files)
        
        password = request.form.get('password')
        print(f"password: {'[PROVIDED]' if password else '[MISSING]'}")
        if not password:
            print("Validation failed: missing password")
            return jsonify({"success": False, "error": "missing password"}), 400

        encrypt = parse_bool(request.form.get('encrypt'), default=False)
        energy_raw = request.form.get('energy_percentile', '0.0')
        robust_raw = request.form.get('robust_repeat', '1')
        
        energy_percentile = float(energy_raw)
        robust_repeat = int(robust_raw)

        if energy_percentile < 0.0 or energy_percentile >= 100.0:
            return jsonify({"success": False, "error": "energy_percentile must be in the range [0, 100)."}), 400
        if robust_repeat < 1 or robust_repeat % 2 == 0:
            return jsonify({"success": False, "error": "robust_repeat must be an odd integer greater than or equal to 1."}), 400

        stego_path = None
        if 'stego' in request.files and request.files['stego'].filename:
            stego_file = request.files['stego']
            print(f"uploaded file name: {stego_file.filename}")
            if not stego_file.filename.lower().endswith('.wav'):
                print("Validation failed: invalid path")
                return jsonify({"success": False, "error": "Invalid password or extraction failed"}), 400
            
            stego_name, stego_path = safe_save(stego_file, UPLOAD_FOLDER, prefix='extr_')
            if not validate_wav_file(stego_path):
                print("Validation failed: invalid wave format")
                try:
                    os.remove(stego_path)
                except OSError:
                    pass
                return jsonify({"success": False, "error": "Invalid password or extraction failed"}), 400
        else:
            stego_name = request.form.get('stego_filename')
            print(f"Using session stego file: {stego_name}")
            print(f"stego_filename: {stego_name}")
            if not stego_name:
                print("Validation failure: missing stego_filename")
                return jsonify({"success": False, "error": "Missing stego file"}), 400
            
            stego_path = os.path.join(STEGO_FOLDER, secure_filename(stego_name))
            if not os.path.exists(stego_path):
                stego_path = os.path.join(UPLOAD_FOLDER, secure_filename(stego_name))
                if not os.path.exists(stego_path):
                    print("Validation failed: file not found")
                    return jsonify({"success": False, "error": "Selected generated file not found"}), 400

        print(f"extracted file path: {stego_path}")
        print(f"whether file exists: {os.path.exists(stego_path)}")

        h = hashlib.sha256(password.encode('utf-8')).digest()
        key_bytes = h[:16]

        from src.extract import extract_adaptive_keyed
        plaintext = extract_adaptive_keyed(
            stego_wav_path=stego_path,
            user_key=key_bytes,
            energy_percentile=energy_percentile,
            decrypt=encrypt,
            robust_repeat=robust_repeat
        )
        
        if plaintext is None:
            print("Validation failure: extraction failure")
            return jsonify({
                "success": False,
                "error": "Invalid password or extraction failed. Use the same key and embed settings used during embedding.",
            }), 400

        try:
            decoded_message = plaintext.decode('utf-8')
            return jsonify({
                "success": True,
                "message": decoded_message
            })
        except UnicodeDecodeError as ude:
            import base64
            app.logger.warning(f"UTF-8 decode failed: {ude}")
            b64 = base64.b64encode(plaintext).decode('ascii')
            return jsonify({
                "success": True,
                "message_b64": b64,
                "utf8_error": str(ude),
                "note": "Payload is binary or wrong parameters were used for extraction."
            })
    except Exception as e:
        print(f"Extraction exception: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route('/api/download/<filename>')
def api_download(filename):
    """Downloads a staged generated file."""
    if os.path.exists(os.path.join(STEGO_FOLDER, filename)):
        return send_from_directory(STEGO_FOLDER, filename, as_attachment=True)
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


def _resolve_pair_from_request():
    cover_name = request.args.get('cover', '')
    stego_name = request.args.get('stego', '')
    if not cover_name or not stego_name:
        return None, json_error("Missing cover or stego filename.")

    from analytics import resolve_session_pair
    cover_path, stego_path, session = resolve_session_pair(
        cover_name, stego_name, UPLOAD_FOLDER, STEGO_FOLDER, _load_registry()
    )
    if not cover_path or not stego_path:
        return None, (jsonify({"error": "Audio carrier files not found on server."}), 404)
    return (cover_path, stego_path, session), None


def _render_dashboard_plot(plot_fn, plot_kwargs=None):
    import inspect
    import matplotlib
    matplotlib.use('Agg')

    pair, err = _resolve_pair_from_request()
    if err:
        return err
    cover_path, stego_path, session = pair
    plot_kwargs = dict(plot_kwargs or {})

    energy_raw = request.args.get('energy_percentile')
    energy_val = None
    if energy_raw is not None:
        energy_val = float(energy_raw)
    elif session and session.get('energy_percentile') is not None:
        energy_val = float(session['energy_percentile'])

    if energy_val is not None and 'energy_percentile' in inspect.signature(plot_fn).parameters:
        plot_kwargs['energy_percentile'] = energy_val

    out_name = f"{plot_fn.__name__}_{uuid.uuid4().hex}.png"
    out_path = os.path.join(VISUALIZATION_FOLDER, out_name)
    plot_fn(cover_path, stego_path, save_path=out_path, **plot_kwargs)
    return send_file(out_path, mimetype='image/png')


@app.route('/api/analytics/summary')
def api_analytics_summary():
    """Return real comparative metrics for cover/stego pair."""
    pair, err = _resolve_pair_from_request()
    if err:
        return err
    cover_path, stego_path, session = pair

    from analytics import build_analytics_summary
    return jsonify(build_analytics_summary(cover_path, stego_path, session))


@app.route('/api/visualize/waveform')
def api_viz_waveform():
    from src.viz_dashboard import plot_dashboard_waveform
    return _render_dashboard_plot(plot_dashboard_waveform)


@app.route('/api/visualize/spectrogram')
def api_viz_spectrogram():
    from src.viz_dashboard import plot_dashboard_spectrogram
    return _render_dashboard_plot(plot_dashboard_spectrogram)


@app.route('/api/visualize/heatmap')
def api_viz_heatmap():
    from src.viz_dashboard import plot_dashboard_heatmap
    return _render_dashboard_plot(plot_dashboard_heatmap)


@app.route('/api/visualize/energy-profile')
def api_viz_energy_profile():
    from src.viz_dashboard import plot_dashboard_energy_profile
    return _render_dashboard_plot(plot_dashboard_energy_profile)


@app.route('/api/visualize/embedding-density')
def api_viz_embedding_density():
    from src.viz_dashboard import plot_dashboard_embedding_density
    return _render_dashboard_plot(plot_dashboard_embedding_density)


@app.route('/api/visualize/lsb-analysis')
def api_viz_lsb_analysis():
    from src.viz_dashboard import plot_dashboard_lsb_analysis
    return _render_dashboard_plot(plot_dashboard_lsb_analysis)


@app.route('/api/visualize/snr')
def api_viz_snr():
    from src.viz_dashboard import plot_dashboard_snr
    return _render_dashboard_plot(plot_dashboard_snr)


@app.route('/api/visualize/detectability')
def api_viz_detectability():
    import matplotlib
    matplotlib.use('Agg')

    pair, err = _resolve_pair_from_request()
    if err:
        return err
    cover_path, stego_path, session = pair

    from analytics import _compute_mse, _detectability_from_mse
    from src.viz_dashboard import plot_dashboard_detectability

    mse = _compute_mse(cover_path, stego_path)
    score, _ = _detectability_from_mse(mse)

    out_name = f"detectability_{uuid.uuid4().hex}.png"
    out_path = os.path.join(VISUALIZATION_FOLDER, out_name)
    plot_dashboard_detectability(
        cover_path,
        stego_path,
        save_path=out_path,
        detectability_score=score,
        score_source="mse_proxy",
    )
    return send_file(out_path, mimetype='image/png')


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
