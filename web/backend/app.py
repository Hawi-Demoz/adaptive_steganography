import os
import sys
import uuid
import hashlib
import time
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory, session
from flask_cors import CORS
import numpy as np
import soundfile as sf
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps# Resolve system paths to load local python modules
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

app = Flask(__name__)
app.secret_key = 'vault-super-secret-key-1234' # Required for session

# Enable CORS for frontend integration
CORS(app, supports_credentials=True)

# Standardized folder structures inside workspace data/ folder
UPLOAD_FOLDER = os.path.join(BACKEND_DIR, 'uploads')
STEGO_FOLDER = os.path.join(BACKEND_DIR, 'generated')
VISUALIZATION_FOLDER = os.path.join(ROOT_DIR, 'data', 'visualizations')
SESSION_REGISTRY_FILE = os.path.join(STEGO_FOLDER, 'session_registry.json')
AUTH_FILE = os.path.join(BACKEND_DIR, 'data', 'auth.json')

os.makedirs(os.path.join(BACKEND_DIR, 'data'), exist_ok=True)

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
        return info.frames > 0
    except Exception:
        return False


def _normalize_wav_filename(raw_name, fallback_prefix='stego_'):
    safe_name = secure_filename(raw_name or '')
    stem, ext = os.path.splitext(safe_name)
    if not stem:
        stem = f"{fallback_prefix}{uuid.uuid4().hex}"
    if ext.lower() != '.wav':
        ext = '.wav'
    return f"{stem}{ext}"


def _ensure_unique_filename(folder, filename):
    stem, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{stem}_{counter}{ext}"
        counter += 1
    return candidate, os.path.join(folder, candidate)


def safe_save(file_obj, folder, prefix=''):
    """Saves a file securely to the given folder using a unique UUID."""
    original_name = secure_filename(file_obj.filename or '')
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in {'.wav'}:
        ext = '.wav'
    name, path = _ensure_unique_filename(folder, f"{prefix}{uuid.uuid4().hex}{ext}")
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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({"error": "Authentication required. Please unlock the Vault."}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
def index():
    """Health status endpoint."""
    return jsonify({"status": "Flask API running"})

@app.route('/api/auth/status', methods=['GET'])
def api_auth_status():
    """Check authentication status and if setup is required."""
    setup_required = not os.path.exists(AUTH_FILE)
    authenticated = session.get('authenticated', False)
    return jsonify({
        "setupRequired": setup_required,
        "authenticated": authenticated
    })

@app.route('/api/auth/setup', methods=['POST'])
def api_auth_setup():
    """First-time setup for the Vault."""
    if os.path.exists(AUTH_FILE):
        return jsonify({"error": "Vault is already initialized."}), 400
        
    password = request.json.get('password')
    if not password:
        return jsonify({"error": "Password is required."}), 400
        
    hashed = generate_password_hash(password)
    try:
        with open(AUTH_FILE, 'w') as f:
            json.dump({"password_hash": hashed}, f)
        session['authenticated'] = True
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """Login to unlock the Vault."""
    if not os.path.exists(AUTH_FILE):
        return jsonify({"error": "Vault is not initialized."}), 400
        
    password = request.json.get('password')
    if not password:
        return jsonify({"error": "Password is required."}), 400
        
    try:
        with open(AUTH_FILE, 'r') as f:
            data = json.load(f)
        
        if check_password_hash(data.get('password_hash', ''), password):
            session['authenticated'] = True
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Invalid password."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    """Lock the Vault."""
    session.pop('authenticated', None)
    return jsonify({"success": True})


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Stages an audio file by saving it to standard upload folder."""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    name, path = safe_save(request.files['file'], UPLOAD_FOLDER, prefix='upload_')
    return jsonify({"filename": name, "original_name": request.files['file'].filename})


@app.route('/api/session/files', methods=['GET'])
@login_required
def api_session_files():
    """Returns the list of dynamically generated stego files from the server's session registry."""
    return jsonify(_load_registry())


@app.route('/api/session/files/<filename>', methods=['DELETE'])
@login_required
def api_delete_session_file(filename):
    """Deletes a stego file from storage and removes its registry entry."""
    safe = secure_filename(filename)
    # Remove file from storage folders
    for folder in (STEGO_FOLDER, UPLOAD_FOLDER):
        p = os.path.join(folder, safe)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    # Remove from registry
    registry = _load_registry()
    new_registry = [e for e in registry if e.get('stego_filename') != safe]
    _save_registry(new_registry)
    return jsonify({"success": True})


@app.route('/api/session/files/<filename>', methods=['PUT'])
@login_required
def api_rename_session_file(filename):
    """Rename an existing stego file and update the session registry."""
    data = request.get_json(silent=True) or request.form
    new_name_raw = data.get('new_name') if isinstance(data, dict) else request.form.get('new_name')
    if not new_name_raw:
        return json_error("new_name is required for rename.")

    safe_old = secure_filename(filename)
    new_name = _normalize_wav_filename(new_name_raw)
    # Ensure unique target name in stego folder
    target_name, target_path = _ensure_unique_filename(STEGO_FOLDER, new_name)

    # Locate existing file
    old_path = os.path.join(STEGO_FOLDER, safe_old)
    if not os.path.exists(old_path):
        old_path = os.path.join(UPLOAD_FOLDER, safe_old)
        if not os.path.exists(old_path):
            return json_error("File not found.", 404)

    try:
        os.replace(old_path, target_path)
    except Exception as e:
        return json_error(f"Failed to rename file: {e}")

    # Update registry
    registry = _load_registry()
    for entry in registry:
        if entry.get('stego_filename') == safe_old:
            entry['stego_filename'] = target_name
            entry['requested_stego_filename'] = target_name
            break
    _save_registry(registry)

    return jsonify({"success": True, "stego_filename": target_name})


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

    requested_stego_name = request.form.get('stego_filename') or request.form.get('output_name') or ''
    stego_name = _normalize_wav_filename(requested_stego_name)
    stego_name, stego_path = _ensure_unique_filename(STEGO_FOLDER, stego_name)

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
    entry_id = os.path.splitext(stego_name)[0]
    
    payload_size = len(message_text.encode('utf-8'))
    
    entry = {
        "id": entry_id,
        "timestamp": time.time(),
        "cover_filename": cover_name,
        "stego_filename": stego_name,
        "requested_stego_filename": requested_stego_name,
        "original_cover_name": original_name,
        "energy_percentile": energy_percentile,
        "robust_repeat": robust_repeat,
        "encrypt": encrypt,
        "snr_db": float(snr_val),
        "payload_ber": float(payload_ber_val) if payload_ber_val is not None else None,
        "payload_size": payload_size,
        "lsb_ber": float(lsb_ber_val),
        "password_protected": True
    }
    registry = _load_registry()
    registry.append(entry)
    _save_registry(registry)

    return jsonify(entry)


@app.route('/api/extract', methods=['POST'])
@login_required
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
@login_required
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
@login_required
def api_analytics_summary():
    """Return real comparative metrics for cover/stego pair."""
    pair, err = _resolve_pair_from_request()
    if err:
        return err
    cover_path, stego_path, session = pair

    from analytics import build_analytics_summary
    return jsonify(build_analytics_summary(cover_path, stego_path, session))


@app.route('/api/visualize/waveform')
@login_required
def api_viz_waveform():
    from src.viz_dashboard import plot_dashboard_waveform
    return _render_dashboard_plot(plot_dashboard_waveform)


@app.route('/api/visualize/spectrogram')
@login_required
def api_viz_spectrogram():
    from src.viz_dashboard import plot_dashboard_spectrogram
    return _render_dashboard_plot(plot_dashboard_spectrogram)


@app.route('/api/visualize/heatmap')
@login_required
def api_viz_heatmap():
    from src.viz_dashboard import plot_dashboard_heatmap
    return _render_dashboard_plot(plot_dashboard_heatmap)


@app.route('/api/visualize/energy-profile')
@login_required
def api_viz_energy_profile():
    from src.viz_dashboard import plot_dashboard_energy_profile
    return _render_dashboard_plot(plot_dashboard_energy_profile)


@app.route('/api/visualize/embedding-density')
@login_required
def api_viz_embedding_density():
    from src.viz_dashboard import plot_dashboard_embedding_density
    return _render_dashboard_plot(plot_dashboard_embedding_density)


@app.route('/api/visualize/lsb-analysis')
@login_required
def api_viz_lsb_analysis():
    from src.viz_dashboard import plot_dashboard_lsb_analysis
    return _render_dashboard_plot(plot_dashboard_lsb_analysis)


@app.route('/api/visualize/snr')
@login_required
def api_viz_snr():
    from src.viz_dashboard import plot_dashboard_snr
    return _render_dashboard_plot(plot_dashboard_snr)


@app.route('/api/visualize/<plot_type>')
@login_required
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
@login_required
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
@login_required
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
