# Adaptive & Secure Audio Steganography — Session Summary

Date: 2025-11-15

## Overview
- Objective: Build a keyed, adaptive, AES-secure audio steganography system and add visualization tools for an academic final-year project.
- Outcome: Implemented adaptive key-based embedding/extraction, AES encryption, CLI, evaluation metrics, and a complete visualization suite. Verified with round-trip tests and generated figures.

## The Whole Idea (Concept)
This project hides secret text inside a 16‑bit PCM WAV audio file so that changes are inaudible and recovery is possible only with the correct key. Security and imperceptibility are achieved by combining three ideas:

- Confidentiality via AES: The message is AES‑encrypted before embedding, so even if bits are found, content remains unreadable without the key.
- Keyed positions: A user key deterministically seeds a pseudo‑random generator to choose where in the audio to write LSBs. Only the same key reproduces the exact positions for extraction.
- Adaptive placement: The audio is analyzed per frame (RMS energy). Louder segments get higher priority for embedding because small LSB changes are perceptually masked there; quieter segments get fewer or no changes.

High‑level pipeline:
- Embedding
  1) Encrypt plaintext with AES‑CBC → `iv || ciphertext`.
  2) Build payload header: `ASTG` preamble + 4‑byte length + encrypted bytes.
  3) Compute RMS per frame; normalize to energy scores.
  4) Derive a deterministic, key‑seeded random value per sample and combine with energy score to form an ordering key.
  5) Sort sample indices by this key (prefix‑stable). Write payload bits into the LSBs of the earliest indices.
  6) Save stego WAV.
- Extraction
  1) Recompute the same key‑based ordering from the stego audio and key.
  2) Read the first 64 bits (preamble + length), then read the indicated payload bits.
  3) Split `iv || ciphertext`, AES‑decrypt, and recover plaintext.

Why this works:
- Without the key, the sample positions appear random and are extremely hard to guess.
- Even if positions are guessed, the content is encrypted.
- Writing only 1 LSB per selected sample produces very small changes; concentrating in high‑energy regions further hides them psychoacoustically. Measured SNR remains high (≈ 96–98 dB in our demo).

## Key Concepts Implemented
- AES-CBC encryption with PKCS#7 padding; payload stored as `iv || ciphertext`.
- Deterministic key-based embedding order using SHA-256-derived seed and audio energy bias (RMS per frame).
- Prefix-stable ordering so extraction can always read header (preamble+length) first.
- LSB embedding into 16-bit PCM samples.
- Evaluation: SNR, BER, waveform comparison, spectrograms, and bit-change heatmaps.

## Files Added/Updated
- Added:
  - `src/keyed_adaptive.py`: Keyed, energy-adaptive ordering of sample indices.
  - `src/cli.py`: Command-line interface for embed/extract.
  - `src/metrics.py`: `compute_snr_db`, `compute_ber`.
  - `src/visualize.py`: Plotting functions (waveform/spectrogram/energy/random/SNR/BER/heatmap).
  - `src/viz_demo.py`: Demo script to generate all figures.
  - `src/live_view.py`: Live spectrogram playback with moving cursor; optional cover vs stego compare.
  - `requirements.txt`: numpy, soundfile, pycryptodome, matplotlib, scipy, sounddevice.
- Updated:
  - `src/embed.py`: Added `embed_adaptive_keyed(...)` (AES + keyed adaptive indices).
  - `src/extract.py`: Added `extract_adaptive_keyed(...)` (header-first, AES decrypt).
  - `src/tests.py`: Demo round-trip using sample WAV and SNR printout.
  - `README.md`: Install, CLI usage, API examples, evaluation notes.

## How to Run (CLI)
Ensure venv is activated and dependencies are installed.

```powershell
cd "c:\Users\hawip\Desktop\adaptive_steganography"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Embed a message (AES + keyed adaptive)
python -m src.cli embed --cover data/original/file_example_WAV_1MG.wav --out data/stego/stego.wav --key "my secret key" --msg "Hello world" --energy-percentile 20 --frame-size 1024 --hop-size 512 --snr-against

# Extract the message
python -m src.cli extract --stego data/stego/stego.wav --key "my secret key" --out-text --energy-percentile 20 --frame-size 1024 --hop-size 512
```

## Programmatic API
```python
from src.embed import embed_adaptive_keyed
from src.extract import extract_adaptive_keyed
import hashlib

key_bytes = hashlib.sha256(b"passphrase").digest()[:16]
embed_adaptive_keyed("cover.wav", b"secret", "stego.wav", key_bytes)
plaintext = extract_adaptive_keyed("stego.wav", key_bytes)
```

## Visualization Suite
Run the demo to generate figures into `figures/`:

```powershell
python -m src.viz_demo
```

Generated files:
- `figures/waveform_comparison.png`
- `figures/spectrogram_comparison.png`
- `figures/energy_analysis.png`
- `figures/random_positions.png`
- `figures/snr_and_noise.png`
- `figures/bit_difference_heatmap.png`
- `figures/ber_vs_awgn.png`

Use functions from `src/visualize.py` for individual plots.

## Verification Results (Observed)
- Round-trip extraction: success; recovered text matched input.
- Example SNR: ~96–98 dB on sample WAV (transparent changes).
- BER vs AWGN: plotted across SNR values (configurable).

## Reproducibility & Security Notes
- Key derivation: CLI derives a 16-byte AES key from passphrase via SHA-256.
- Ordering randomness is fully determined by the key and audio length; extraction reproduces it exactly.
- Mono PCM 16-bit expected; stereo is reduced to first channel for simplicity.

## Design Choices, Trade-offs, and Limits
- Imperceptibility vs capacity: Using one LSB per selected sample preserves quality; capacity scales with audio length and proportion of high-energy samples. Overhead is 8 bytes (preamble + length).
- Robustness: Scheme is fragile to heavy processing (lossy compression, resampling) typical of LSB methods; intended for same-format storage/transmission.
- Parameters matter: Frame size, hop size, and energy percentile tune how aggressively we favor loud regions. Larger frames smooth energy; higher percentile skips more quiet regions.
- Security layers: Position secrecy (keyed ordering) + content secrecy (AES). For integrity, consider adding a MAC/HMAC over ciphertext in future work.

## Potential Extensions
- Capacity preview (`--dry-run --show-capacity`) and automatic parameter suggestions.
- Stereo-aware embedding (distribute across channels) and psychoacoustic models beyond RMS.
- Integrity protection (HMAC) and optional error-correcting codes for mild distortions.
- Simple Flask web UI for demos (upload, parameters, plots, results).

## Suggested Next Steps
- Capacity reporting: show maximum embeddable bytes before embedding.
- Stereo-aware embedding to preserve stereo.
- Optional integrity tag (e.g., HMAC of ciphertext) for corruption detection.
- Flask UI for interactive demos (file upload, parameters, plots).

## Appendix — Commands Used During Session
```powershell
# Install dependencies
python -m pip install -r requirements.txt

# Run Python module tests/demo
python -m src.tests

# CLI embed/extract (example)
python -m src.cli embed --cover data/original/file_example_WAV_1MG.wav --out data/stego/stego.wav --key "final-year-key" --msg "Final-year demo run" --energy-percentile 20 --frame-size 1024 --hop-size 512 --snr-against
python -m src.cli extract --stego data/stego/stego.wav --key "final-year-key" --out-text --energy-percentile 20 --frame-size 1024 --hop-size 512

# Generate all figures
python -m src.viz_demo
```

## Live Spectrogram Viewer (src/live_view.py)

This tool plays audio while displaying a spectrogram with a live, moving time cursor. In compare mode, it shows cover vs stego side-by-side with unified color scaling.

### What It Does
- Precompute spectrogram(s): Reads WAV as mono int16, computes spectrogram once with `scipy.signal.spectrogram`, converts to dB.
- Plot spectrograms: Uses `matplotlib` (`pcolormesh`) to render. In `--compare` mode, shows cover and stego side-by-side with a shared colorbar.
- Play audio: Normalizes the `int16` to `float32` in [-1, 1] and plays non-blocking via `sounddevice.sd.play(...)`.
- Animate cursor: A cyan vertical line is updated ~30 fps using a Matplotlib timer, positioned by elapsed wall-clock time since playback started.

### Why This Is Correct
- Efficient live feel: Spectrogram is computed once; only the cursor moves. This avoids heavy real-time FFT work and keeps UI smooth.
- Sync strategy: Uses `time.perf_counter()` from the moment `sd.play(...)` starts, closely matching playback time.
- Robust startup: Delays playback by ~100 ms after window draw (when supported) to reduce backend-induced lag and improve alignment.
- Compare mode: Keeps both plots on the same dB scale and moves two cursors in lockstep for fair visual comparison.

### Minor Caveats
- Sample-rate mismatch: Compare mode assumes the same sample rate for cover and stego; otherwise time axes can differ slightly. If needed, add an explicit resample or per-file time axis handling.
- Tiny drift: Wall-clock vs audio device clock can introduce very small drift. For near-perfect sync, consider stream timing (`sounddevice` stream callbacks or stream time).
- GUI backend: The small startup delay uses a Tk-specific hook when available; the code gracefully falls back if a different backend is active.

### Usage
```powershell
# Stego-only live spectrogram with moving cursor
python -m src.live_view --stego data/stego/stego.wav

# Side-by-side cover vs stego with synchronized cursors
python -m src.live_view --stego data/stego/stego.wav --cover data/original/file_example_WAV_1MG.wav --compare
```

### Tuning
- `--nperseg`: Higher values improve frequency resolution but smear time; lower values react faster in time.
- `--noverlap`: Increase to smooth the image, decrease for faster computation and less smoothing.

### Dependencies
- Requires `sounddevice` in addition to NumPy/Matplotlib/SciPy/SoundFile. This is listed in `requirements.txt`.
