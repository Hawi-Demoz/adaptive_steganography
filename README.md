# Adaptive & Secure Audio Steganography (Key-Based)

This project implements an adaptive and secure audio steganography pipeline for WAV PCM 16-bit mono files. It encrypts the message (AES-CBC) and uses a user key to deterministically randomize embedding positions, biased towards high-energy regions of the audio.

Features:
- Key-based, deterministic embedding positions (prefix-stable).
- Adaptive to audio energy (RMS per frame): more bits in loud regions, fewer in quiet.
- AES-CBC encryption with PKCS#7 padding (`iv||ciphertext`).
- CLI and Python API.
- Basic evaluation: SNR (dB) and BER utility.

## Folder Structure
- `data/original/`: Original audio files (e.g., `file_example_WAV_1MG.wav`)
- `data/stego/`: Files with embedded data (output `stego.wav`)
- `src/`: Source code and CLI
	- `embed.py`, `extract.py`: embedding/extraction (sequential + adaptive-keyed)
	- `keyed_adaptive.py`: keyed, energy-adaptive ordering of sample indices
	- `encrypt.py`: AES helpers
	- `metrics.py`: SNR/BER
	- `cli.py`: command-line interface

## Install
Python 3.10+ recommended.

```powershell
cd "c:\Users\hawip\Desktop\adaptive_steganography"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## CLI Quickstart
Embed a short message (AES-encrypted) using key-based adaptive positions:

```powershell
python -m src.cli embed --cover data/original/file_example_WAV_1MG.wav --out data/stego/stego.wav --key "my secret key" --msg "Hello world" --energy-percentile 20 --frame-size 1024 --hop-size 512 --snr-against
```

Extract the message:

```powershell
python -m src.cli extract --stego data/stego/stego.wav --key "my secret key" --out-text --energy-percentile 20 --frame-size 1024 --hop-size 512
```

Notes:
- Input WAV should be PCM 16-bit mono. If stereo is provided, only the first channel is used.
- Capacity depends on audio length; overhead is 8 bytes (preamble + length).

## Python API

```python
from src.embed import embed_adaptive_keyed
from src.extract import extract_adaptive_keyed

key_bytes = b"16-byte-aes-key!"  # derive with SHA-256 from a passphrase
embed_adaptive_keyed("cover.wav", b"secret", "stego.wav", key_bytes)
pt = extract_adaptive_keyed("stego.wav", key_bytes)
```

## Evaluation
- `metrics.compute_snr_db(cover, stego)` – higher is better (less distortion).
- `metrics.compute_ber(a, b)` – compare two bit arrays.

## Development
Run the demo test:

```powershell
python src/tests.py
```

## Security Considerations
- Positions are derived from the user key and audio energy via a prefix-stable ordering.
- For academic purposes. Real-world steganalysis resistance is not guaranteed without further countermeasures.
