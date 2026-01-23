from pathlib import Path
import sys
import hashlib

# Ensure project root is on sys.path when executed as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.visualize import plot_spectrogram_comparison
from src.embed import embed_adaptive_keyed


def main():
    root = Path(__file__).parent.parent
    cover = root / 'data' / 'original' / 'sample.wav'
    stego = root / 'data' / 'stego' / 'stego.wav'
    figs = root / 'figures'
    figs.mkdir(exist_ok=True)

    # Ensure stego exists; create minimal one if missing
    if not stego.exists():
        key_bytes = hashlib.sha256(b"spectrogram-key").digest()[:16]
        embed_adaptive_keyed(str(cover), b"Spectrogram test", str(stego), key_bytes, energy_percentile=20.0)

    out_path = figs / 'spectrogram_on_demand.png'
    plot_spectrogram_comparison(str(cover), str(stego), save_path=str(out_path))
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()
