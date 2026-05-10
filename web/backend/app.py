import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile

# Add project root to path to import your existing src modules
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.embed import embed_adaptive_keyed
from src.extract import extract_adaptive_keyed

app = Flask(__name__)
CORS(app) # Allow React frontend to communicate with Flask

UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Flask API is running. Use the React frontend to interact with this API."})

@app.route('/api/embed', methods=['POST'])
def api_embed():
    """Endpoint for embedding messages into audio."""
    try:
        # 1. Get input files and form data
        cover_file = request.files['cover']
        message_text = request.form.get('message', '')
        password = request.form.get('password', '')
        encrypt = request.form.get('encrypt') == 'true'
        energy_percentile = float(request.form.get('energy_percentile', 20.0))
        robust_repeat = int(request.form.get('robust_repeat', 1))
        
        # 2. Save temporary cover file
        cover_path = os.path.join(UPLOAD_FOLDER, cover_file.filename)
        cover_file.save(cover_path)
        
        stego_path = os.path.join(UPLOAD_FOLDER, f"stego_{cover_file.filename}")
        
        # 3. Call your existing embed function
        embed_adaptive_keyed(
            cover_wav_path=cover_path,
            plaintext=message_text.encode('utf-8'),
            out_wav_path=stego_path,
            user_key=password,
            energy_percentile=energy_percentile,
            encrypt=encrypt,
            robust_repeat=robust_repeat
        )
        
        # 4. Return the generated stego file
        return send_file(stego_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """Endpoint for extracting messages from stego audio."""
    try:
        stego_file = request.files['stego']
        password = request.form.get('password', '')
        
        stego_path = os.path.join(UPLOAD_FOLDER, stego_file.filename)
        stego_file.save(stego_path)
        
        # Call your existing extract function
        plaintext = extract_adaptive_keyed(
            stego_wav_path=stego_path, 
            user_key=password
        )
        
        return jsonify({"message": plaintext.decode('utf-8')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
