# Adaptive & Secure Audio Steganography (Password-Based)

This project hides a secret text message inside an uncompressed audio file by making extremely small changes to the audio samples.

The important idea is simple:

- A digital audio file is a long list of integer sample values.
- Each sample has a smallest bit (the least significant bit).
- This project stores the secret message by forcing that smallest bit to match the message bits.

Because the smallest bit only changes a sample by at most 1 unit, the cover audio and the stego audio usually look (and sound) almost identical.

## What this project adds beyond “basic least significant bit hiding”

- Confidentiality: the message can be encrypted with the Advanced Encryption Standard using cipher block chaining mode and standard padding.
- Unpredictable placement: message bits are not written sequentially; the write positions are determined from a password.
- Adaptivity: writing is biased toward louder regions of the audio where changes are harder to perceive.
- Optional robustness: a simple redundancy + shuffling + integrity check layer can be enabled to help recover from random bit errors.

## Folder Structure
- `data/original/`: Original audio files (e.g., `file_example_WAV_1MG.wav`)
- `data/stego/`: Files with embedded data (output `stego.wav`)
- `src/`: Source code and CLI
	- `embed.py`, `extract.py`: embedding/extraction (sequential + adaptive-keyed)
	- `keyed_adaptive.py`: keyed, energy-adaptive ordering of sample indices
	- `encrypt.py`: encryption helpers
	- `metrics.py`: quality and correctness metrics
	- `cli.py`: command-line interface
	- `sweep_experiments.py`: repeatable simulation sweep runner
	- `sim_cli.py`: interactive embed/extract demo
	- `robust_payload.py`: optional redundancy/shuffling/integrity utilities

## Install
Python 3.10+ recommended.

```powershell
cd "c:\Users\hawip\Desktop\adaptive_steganography"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Start Here: What “hiding a message” means (no prior knowledge required)

### The audio file is a list of numbers

This project uses uncompressed audio where each sample is a signed 16-bit integer in the range -32768 to 32767.

Example (conceptual):

- cover samples: 1000, 1001, 1000, 999, ...

### The smallest possible change is one unit

The least significant bit is the smallest bit inside an integer sample.

- If you force the least significant bit to 0, the sample becomes even.
- If you force the least significant bit to 1, the sample becomes odd.

That means to store one bit you change a sample by at most 1 unit.

### One message bit is stored in one chosen sample

If the secret message is 100 bytes, that is 800 bits.
To store 800 bits, the system chooses 800 sample positions and writes 1 bit into each position.

Important detail: if a sample already has the correct least significant bit, it does not change.
For random-looking bits (especially after encryption), roughly half of the chosen samples actually change.

## Worked example: hiding the letter “A”

The character “A” is the number 65 in a standard text encoding.

- 65 as an 8-bit binary value is: 01000001
- That means the message bits are: 0,1,0,0,0,0,0,1

To embed it, the algorithm chooses eight sample positions (chosen using the password-based ordering described below). At each chosen sample:

- If the next bit is 0: make the sample even.
- If the next bit is 1: make the sample odd.

After extraction, reading those eight least significant bits reconstructs 01000001, which is 65, which decodes back to “A”.

## How the project chooses which samples to modify

This project does not write message bits into sample 1, then sample 2, then sample 3. That would be predictable.

Instead, it produces a repeatable “ranking” of sample indices using:

1) A password-derived random number generator (so the same password gives the same ordering)
2) An energy score for each audio frame (so louder regions are preferred)

The result is:

- With the correct password and matching parameters, the extractor visits the exact same sample positions and recovers the bits.
- With the wrong password, the extractor visits different sample positions and recovers nonsense.

## How adaptivity works (louder regions get more embedding)

The audio is split into overlapping chunks called frames.
For each frame, the system computes a loudness-like energy score using the root mean square calculation.

Then the `energy-percentile` setting biases embedding toward higher-energy frames:

- 0 means little to no suppression of quiet frames.
- Higher values increasingly de-prioritize low-energy (quiet) frames.

This improves perceptual hiding because changes in loud/complex regions are harder to detect by ear.

## How encryption works (optional confidentiality)

If encryption is enabled, the plaintext message is encrypted before embedding.

- Cipher: Advanced Encryption Standard
- Mode: cipher block chaining
- Padding: PKCS#7
- A fresh random initialization vector is generated per message.

Effect:

- If an attacker extracts the embedded bits, they obtain encrypted data instead of readable text.

## How payload framing works (so extraction knows where to stop)

The embedded bitstream starts with a small header:

- A 4-byte marker: `ASTG`
- A 4-byte big-endian payload length

After reading the header, extraction knows exactly how many payload bytes to read.

## Optional robustness layer (helps with random bit errors)

Time-domain least significant bit embedding is fragile under heavy processing. This repository includes an optional protection layer that can help under random bit flips:

- Redundancy: repeat bits multiple times and use majority vote during recovery.
- Shuffling: interleave the bit order (key-seeded) so local damage is spread out.
- Integrity check: append a cyclic redundancy check so corrupted payloads can be detected.

Tradeoff:

- More redundancy means more embedded bits, which lowers audio quality slightly.

Limitations:

- This does not fully solve robustness to lossy compression (such as MP3/AAC) or resampling/time-scale changes.

## What the metrics mean

- Signal-to-noise ratio: higher means the stego audio is closer to the cover audio.
- Least-significant-bit difference rate: fraction of samples whose least significant bit changed.
- Payload bit error rate: fraction of recovered payload bits that are wrong.
- Localization fraction in top-energy frames: fraction of modifications that occur in the loudest frames.

## CLI Quickstart
Embed a short message (optionally encrypted) using password-based adaptive positions:

```powershell
python -m src.cli embed --cover data/original/file_example_WAV_1MG.wav --out data/stego/stego.wav --key "my secret key" --msg "Hello world" --energy-percentile 20 --frame-size 1024 --hop-size 512 --snr-against
```

Extract the message:

```powershell
python -m src.cli extract --stego data/stego/stego.wav --key "my secret key" --out-text --energy-percentile 20 --frame-size 1024 --hop-size 512
```

Optional robustness (example):

```powershell
python -m src.cli embed --cover data/original/file_example_WAV_1MG.wav --out data/stego/stego.wav --key "my secret key" --msg "Hello world" --energy-percentile 20 --frame-size 1024 --hop-size 512 --robust-repeat 3 --snr-against
python -m src.cli extract --stego data/stego/stego.wav --key "my secret key" --out-text --energy-percentile 20 --frame-size 1024 --hop-size 512 --robust-repeat 3
```

Notes:
- Input WAV should be PCM 16-bit mono. If stereo is provided, only the first channel is used.
- Capacity depends on audio length; overhead is 8 bytes (preamble + length).

## Python API

```python
from src.embed import embed_adaptive_keyed
from src.extract import extract_adaptive_keyed

passphrase = "my secret key"
embed_adaptive_keyed("cover.wav", b"secret", "stego.wav", passphrase)
plaintext = extract_adaptive_keyed("stego.wav", passphrase)
```

## Evaluation
- `metrics.compute_snr_db(cover, stego)` returns the signal-to-noise ratio in decibels.
- `metrics.compute_ber(a, b)` returns a bit error rate between two bit arrays.

## Development
Run the demo test:

```powershell
python src/tests.py
```

## Security Considerations
- The embedding positions are derived from the password and the audio energy scoring, so placement is not sequential.
- This repository is for academic purposes. Resistance against real-world detection and modification is not guaranteed.

## Glossary (terms used above)

- Cover audio: the original audio file before hiding a message.
- Stego audio: the output audio file after hiding a message.
- Sample: one integer value representing audio at a time instant.
- Signed 16-bit integer: an integer that can be negative or positive and fits in 16 bits.
- Least significant bit: the smallest bit of an integer; flipping it changes the value by 1.
- Frame: a short chunk of audio samples used for analysis.
- Root mean square: a standard way to measure frame energy.
- Signal-to-noise ratio: a ratio showing how large the signal is compared to the introduced distortion.
- Bit error rate: fraction of bits that differ between two bitstreams.
- Advanced Encryption Standard: a standard symmetric encryption algorithm.
- Cipher block chaining: an encryption mode where each block depends on the previous ciphertext block.
- Initialization vector: a random value used to start cipher block chaining encryption safely.
- PKCS#7 padding: a standard padding scheme for block ciphers.
- Cyclic redundancy check: a checksum used to detect accidental corruption.

---

**Concise Overview + Key Terms**
- **What the project is:** Adaptive audio steganography. Hides a secret message inside a WAV audio file by tweaking least significant bits of samples. Adds security (encryption), adaptivity (prefers louder frames), and optional robustness (redundancy + shuffling + integrity check).
- **Steganography:** Hiding the existence of a message within a cover medium (here, audio).
- **Least Significant Bit:** Lowest-value bit of a sample; changing it moves the sample by ±1 unit.
- **Advanced Encryption Standard:** Symmetric encryption used here in cipher block chaining mode.
- **Initialization Vector:** Random value prepended to ciphertext for cipher block chaining; required for decryption.
- **PKCS#7 padding:** Standard method to fill the last encryption block to full length.
- **Cyclic Redundancy Check:** Integrity checksum to detect corruption.
- **Error-Correcting Code:** Not fully implemented; current robustness uses repetition + majority vote.
- **Root Mean Square:** Frame energy measure used for adaptivity.
- **Signal-to-Noise Ratio:** Loudness of original signal relative to added noise (higher is better).
- **Bit Error Rate:** Fraction of bits that differ; used both for cover vs stego and recovered payload vs original.

**Pipeline at a Glance**
- **Framing:** Build header with `ASTG` + payload length (4 bytes) + payload bytes.
- **Optional encryption:** If enabled, encrypt payload with Advanced Encryption Standard in cipher block chaining with PKCS#7; payload becomes `InitializationVector || ciphertext`.
- **Energy analysis:** Split audio into overlapping frames; compute root mean square energy; normalize to [0,1].
- **Adaptive gating:** Frames below `energy-percentile` are de-prioritized; higher percentile increases bias to loud frames.
- **Password-based ordering:** Use the user key to seed a deterministic random process; rank samples by random value divided by frame score so louder frames get picked earlier.
- **Least significant bit embedding:** For each payload bit, set the chosen sample’s least significant bit to that bit (change bounded to ±1).
- **Extraction:** Recompute ordering with same key and parameters; read header; recover payload; decrypt if enabled; verify integrity if robustness used.
- **Optional robustness layer:** Repeat bits (configurable), key-seeded shuffling, integrity check; improves recovery under random bit flips with a small quality cost.

**Why Adaptive and Secure**
- **Adaptivity:** Uses `energy-percentile` so more changes land in louder regions where human hearing is less sensitive.
- **Security:** Encryption hides plaintext; password-based non-sequential embedding hides where bits are placed.
- **Integrity (optional):** Integrity checks detect corruption when robustness is enabled.
- **Robustness (optional):** Repetition + shuffling tolerate random bit errors (e.g., mild noise), but do not yet survive heavy compression/resampling.

**What It Does Not Yet Solve**
- **Lossy compression or resampling/time-scale changes:** Requires synchronization plus transform-domain embedding (for example, quantization index modulation in short-time Fourier transform or modified discrete cosine transform), potentially with stronger error correction.

**Core Files**
- [src/embed.py](src/embed.py): Embedding logic (header, optional encryption, ordering, least significant bit writing, optional robustness).
- [src/extract.py](src/extract.py): Extraction logic (recompute ordering, header parse, optional decryption, optional robustness decode).
- [src/cli.py](src/cli.py): Command-line interface; exposes robustness and adaptivity options.
- [src/robust_payload.py](src/robust_payload.py): Redundancy + shuffling + integrity helpers.
- [src/sweep_experiments.py](src/sweep_experiments.py): Runs sweeps across energy levels and message lengths; writes metrics and figures.
- [src/thesis_low_energy_case.py](src/thesis_low_energy_case.py): Parameterized case runner for thesis figures/metrics.
- [src/metrics.py](src/metrics.py): Signal-to-noise ratio, bit error rate, localization metrics.
- [docs/Section_5_Simulation_and_Implementation.md](docs/Section_5_Simulation_and_Implementation.md): Full write-up, logs, tables, and roadmap.
- Figures live under [figures/run_*/](figures/).

**Important Parameters**
- **energy-percentile:** 0 / 20 / 40 in thesis runs; higher increases bias toward loud frames.
- **frame-size, hop-size:** Defaults 1024 / 512.
- **encrypt:** Toggle encryption.
- **robustness flags:** `--robust-repeat N` (repetition factor), `--no-interleave` disables shuffling.

**Metrics You’ll See**
- **bits_used_total:** Header + payload bits actually embedded.
- **fraction_changed / least significant bit difference rate:** How many samples flipped in least significant bit.
- **snr_db:** Distortion level (higher is better).
- **payload_bit_ber:** Errors when recovering the payload (0 means perfect).
- **frac_mod_in_top_energy_frames:** Fraction of flips occurring in the loudest 20 percent frames (higher indicates better masking).

**How to Run**
- **Sweep (reproducible tables/figures):**

```powershell
python -m src.sweep_experiments
```

- **Interactive demo:**

```powershell
python -m src.sim_cli
```

- **Thesis cases (low/medium/high energy):**

```powershell
python -m src.thesis_low_energy_case --energy-percentile 0
python -m src.thesis_low_energy_case --energy-percentile 20
python -m src.thesis_low_energy_case --energy-percentile 40
```

**What Happens to Distortion**
- Each least significant bit change is ±1 per modified sample; total flips scale with payload size and any robustness overhead. More embedded bits slightly lower the signal-to-noise ratio.

**Why This Encryption Setup**
- **Cipher block chaining** ensures identical plaintext blocks encrypt differently (thanks to the initialization vector).
- **PKCS#7 padding** fills the last block to full length.
- **Initialization vector** is random per message and stored with the ciphertext; required for decryption.

**Roadmap (from the documentation)**
- Add stronger error correction plus shuffling.
- Add synchronization to survive time shifts and resampling.
- Move to transform-domain embedding (short-time Fourier transform/modified discrete cosine transform) with quantization index modulation or spread-spectrum for compression robustness.
- Optionally add message authentication (for example, a keyed authenticator or authenticated encryption).
