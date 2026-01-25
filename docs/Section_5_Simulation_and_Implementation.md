5. Simulation and Implementation

5.1 Simulation Environment

This project is implemented and evaluated entirely in a **Python-based simulation environment** (offline processing). No MATLAB/Simulink or hardware capture–playback loop is used in the current implementation.

Tools and Libraries
- **Python 3.10+** (recommended)
- **NumPy**: array operations, bit packing/unpacking, deterministic RNG
- **SciPy**: signal analysis utilities (e.g., spectrogram computation used for visualization)
- **SoundFile**: WAV file I/O (read/write PCM 16‑bit)
- **Matplotlib**: figure generation (waveforms, spectrograms, BER curves, heatmaps)
- **PyCryptodome**: AES encryption/decryption (AES‑CBC with PKCS#7 padding)
- **SoundDevice** (optional): used for the live spectrogram viewer in `live_view.py`

Justification for Tool Selection
- Python + NumPy/SciPy provide a **reproducible, lightweight** environment for DSP simulation and analysis.
- SoundFile supports **reliable PCM WAV** I/O without manual parsing.
- Matplotlib enables publication‑ready figures for a thesis.
- PyCryptodome provides a standard AES implementation, allowing the project to focus on steganographic design rather than cryptographic re‑implementation.

Key Project Scripts (Simulation/Experiments)
- `src/cli.py`: non‑interactive CLI for embedding and extraction.
- `src/sim_cli.py`: interactive simulation workflow (embed/extract + metrics + figure generation).
- `src/viz_demo.py`: generates a standard suite of figures into `figures/`.
- `src/visualize.py`: plotting functions, including BER vs AWGN SNR.
- `src/tests.py`: simple round‑trip verification script.

5.2 Model Development

This section describes how the embedding/extraction “model” was built step‑by‑step, matching the implemented modules.

Step 1 — Payload framing
- A fixed header is prepended to every payload:
  - **Preamble**: `ASTG` (4 bytes)
  - **Length**: 4 bytes (big‑endian)
  - **Payload**: plaintext or ciphertext bytes

Step 2 — Optional AES encryption (confidentiality)
- If encryption is enabled, plaintext is encrypted using **AES‑CBC** with **PKCS#7 padding**.
- A random 16‑byte IV is generated per message and stored as `iv || ciphertext`.

Step 3 — Energy analysis (content adaptivity)
- The audio is divided into frames of size `frame_size` with hop `hop_size`.
- Frame energy is estimated using RMS:

  $$\mathrm{RMS}(k) = \sqrt{\frac{1}{N_k}\sum_{n\in \text{frame }k} x[n]^2}$$

- RMS values are normalized to a score in $[0,1]$ and optionally thresholded by an `energy_percentile` parameter to deprioritize low‑energy frames.

Important implementation detail (ordering stability)
- In `generate_order_indices()`, energy is computed on a version of the audio with **LSB cleared**: `data_energy = data & ~1`.
- This avoids tiny RMS drift between cover and stego caused by LSB flips and helps ensure **the ordering is identical** during extraction.

Step 4 — Keyed deterministic ordering (position selection)
- A deterministic RNG seed is derived from the user key via SHA‑256.
- A random value is generated per sample: $r[n] \sim U(0,1)$.
- A per‑sample priority score is assigned from the frame energy score.
- An ordering key is computed (smaller = earlier):

  $$\mathrm{ord\_key}[n] = \frac{r[n]}{\mathrm{score}[n] + \epsilon}$$

- Indices are sorted using a **stable sort** to obtain an ordering that is **prefix‑stable** (independent of message length).

Step 5 — LSB embedding (time-domain)
- Payload bytes are converted to bits and embedded by replacing the LSB of selected `int16` samples:

  $$y[i] = (x[i] \ \&\ \sim 1)\ \vert\ b$$

  where $b\in\{0,1\}$ is the next payload bit.

Step 6 — Extraction
- The same ordering is recomputed from stego audio + key + parameters.
- The first 64 bits are read to recover `ASTG + length`.
- The payload bits are read according to the length.
- If enabled, AES decryption is performed to recover the plaintext.

5.3 Simulation Setup and Configuration

Input Assumptions
- Input is **WAV PCM 16‑bit**.
- If input is stereo, the implementation uses the **first channel** only.
- Processing is offline (batch/simulation), not real‑time.

Core Parameters
- `frame_size`: default 1024 samples
- `hop_size`: default 512 samples
- `energy_percentile`: controls adaptivity strength (common values used in the project: 0, 20, 40)
- `key/passphrase`: used to derive 16‑byte AES key bytes (SHA‑256 truncation in CLI)
- `encrypt/decrypt`: toggles AES usage

Capacity and Overhead
- Header overhead is 8 bytes (preamble + length) = 64 bits.
- AES adds a 16‑byte IV plus ciphertext padding overhead.
- Capacity depends on audio length and how many indices remain available after energy thresholding.

AWGN Robustness Simulation (BER vs SNR)
- AWGN is added to the stego signal at a target SNR (dB). Noise variance is chosen from the signal power:

  $$\mathrm{SNR}_{\mathrm{lin}} = 10^{\mathrm{SNR}_{\mathrm{dB}}/10}$$
  $$P_{\mathrm{noise}} = \frac{P_{\mathrm{sig}}}{\mathrm{SNR}_{\mathrm{lin}}}$$
  $$\sigma = \sqrt{P_{\mathrm{noise}}}$$

- The noisy signal is rounded and clipped back into the `int16` range before extracting bits.
- In `plot_ber_vs_awgn()`, a fixed RNG seed is used for repeatability.

Boundary Conditions
- Audio sample range is limited to `[-32768, 32767]` by `int16` clipping.
- Extraction requires that `frame_size`, `hop_size`, and `energy_percentile` match embedding settings.

How to Run the Simulation Workflows
- Interactive simulation:

  ```powershell
  python -m src.sim_cli
  ```

- Batch figure generation:

  ```powershell
  python -m src.viz_demo
  ```

- CLI embed/extract:

  ```powershell
  python -m src.cli embed --cover data/original/sample.wav --out data/stego/stego.wav --key "my key" --msg "hello" --energy-percentile 20
  python -m src.cli extract --stego data/stego/stego.wav --key "my key" --out-text --energy-percentile 20
  ```

5.4 Results and Analysis

This section summarizes the key outputs produced by the simulation scripts and how they map to the design objectives.

Key Result Types (Graphs/Tables)
- **Waveform comparison**: illustrates that the stego waveform closely overlaps the cover waveform; modified samples appear sparse.
- **Spectrogram comparison**: shows that spectral energy distribution remains visually similar; the “noise spectrogram” is typically far below the main signal level.
- **SNR and noise histogram/time plot**: quantifies embedding distortion as low‑level noise.
- **LSB modification heatmap**: visualizes where LSB flips occur across time (block index) and within blocks.
- **BER vs AWGN SNR curve**: demonstrates robustness behavior under additive noise.

Interpretation Relative to Objectives
- **Imperceptibility objective**: High SNR and a low fraction of changed samples support that embedding noise is small. Concentrating embedding in higher‑energy regions improves perceptual masking.
- **Reliability objective**: In the noiseless case and with correct key/parameters, extraction should recover the full plaintext (payload BER = 0).
- **Robustness objective**: Under AWGN, BER is expected to be low at high SNR and increase as SNR decreases (a monotonic trend).

Common Observations and Expected Behaviors
- **~50% LSB flip rate in used positions**: Because embedded bits are effectively random (especially when AES is enabled), approximately half of the written bits differ from the original LSBs, producing ~50% flips among the used positions. This is reported in `sim_cli.py` as an “estimated flips” value.
- **Decryption failures under heavy noise**: AES‑CBC decryption may fail with padding errors if extracted ciphertext is corrupted by noise (an expected behavior without error‑control coding).
- **Parameter mismatch sensitivity**: Using a different energy percentile/frame size/hop size at extraction can change the ordering and prevent the preamble from being found.

Discrepancies / Limitations (Discussion)
- **No compression robustness**: Time‑domain LSB is generally fragile to lossy compression or resampling; this thesis implementation evaluates AWGN only.
- **Deterministic AWGN in plotting**: The BER curve uses a fixed RNG seed for repeatability; multiple seeds would show variance bands.
- **Energy adaptivity simplification**: Frame‑level RMS is a simple proxy for masking; no psychoacoustic model is implemented.
