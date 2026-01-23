# tests.py
from pathlib import Path
import sys
import hashlib

# Ensure project root is on sys.path when executed as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.embed import embed_adaptive_keyed
from src.extract import extract_adaptive_keyed
from src.metrics import compute_snr_db


def demo_adaptive_keyed():
    cover = str(Path(__file__).parent.parent / "data" / "original" / "sample.wav")
    out = str(Path(__file__).parent.parent / "data" / "stego" / "stego.wav")
    message = "Hello! This is a secret for testing.".encode('utf-8')
    key_str = "correct horse battery staple"
    key_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()[:16]

    embed_adaptive_keyed(
        cover_wav_path=cover,
        plaintext=message,
        out_wav_path=out,
        user_key=key_bytes,
        frame_size=1024,
        hop_size=512,
        energy_percentile=20.0,
        encrypt=True,
    )
    recovered = extract_adaptive_keyed(
        stego_wav_path=out,
        user_key=key_bytes,
        frame_size=1024,
        hop_size=512,
        energy_percentile=20.0,
        decrypt=True,
    )
    print("Recovered:", recovered)
    print("Matches:", recovered == message)
    snr = compute_snr_db(cover, out)
    print(f"SNR: {snr:.2f} dB")

if __name__ == "__main__":
    demo_adaptive_keyed()
