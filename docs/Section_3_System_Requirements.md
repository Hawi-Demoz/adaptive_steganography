3. System Requirements and Specifications

3.1 Functional Requirements
- **Audio I/O**: Accept 16‑bit PCM WAV input (mono or stereo); reduce stereo to the first channel for embedding/extraction.
- **Embedding**: Implement `embed_lsb()` and `embed_adaptive_keyed()` to write payload bits into the LSBs of selected samples using energy‑biased, key‑dependent ordering. Include a plaintext header (`ASTG` preamble + 4‑byte length) before payload.
- **Extraction**: Implement `extract_adaptive_keyed()` (and sequential variant) to recover the header and payload from the same deterministic ordering. Support optional AES decryption of the recovered bytes.
- **Confidentiality**: Provide optional AES‑CBC encryption with PKCS#7 padding; store payload as `iv || ciphertext`. Header remains plaintext for synchronization.
- **Determinism**: For identical audio, key, and parameters, generate the same sample ordering to ensure reproducible embed/extract behavior.
- **Capacity Handling**: Check available capacity against payload size (accounting for 8‑byte header) and fail gracefully with informative errors if insufficient.
- **CLI Interface**: Provide commands for embed/extract with flags for `--cover`, `--stego/--out`, `--key`, `--msg/--msg-file`, `--frame-size`, `--hop-size`, `--energy-percentile`, and `--no-encrypt/--no-decrypt`.
- **Metrics & Visualization**: Offer objective metrics (SNR, LSB‑level BER, sample‑change statistics) and visual analyses (waveforms, spectrograms, LSB heatmaps) to assess imperceptibility and robustness.
- **Error Handling**: Detect and report common failure modes (missing preamble, wrong key, parameter mismatch) with clear messages.

Performance Criteria
- **Correctness (Noiseless)**: BER of 0 for payload extraction in the absence of channel noise when using the correct key and matching parameters.
- **Robustness (AWGN)**: Under additive white Gaussian noise at higher SNRs, maintain low BER (near zero at high SNR; monotonic degradation as SNR decreases). Exact thresholds are established empirically in evaluation.
- **Runtime Efficiency**: End‑to‑end embedding/extraction complexity scales linearly with number of samples (O(N)) and should complete quickly for minute‑scale audio on a typical laptop. No real‑time constraints.
- **Resource Use**: Memory usage remains proportional to audio length; no external hardware or GPU required.
- **Quality Metrics**: Maintain high SNR and low LSB‑change fraction at conservative payloads; provide reproducible metric reporting.
- **Power Efficiency**: Not a design driver (offline desktop simulation); aim for reasonable CPU utilization without specialized optimization.

3.2 Non‑Functional Requirements
- **Portability**: Runs on Windows with Python 3.10+; uses NumPy, SciPy, SoundFile, Matplotlib, and PyCryptodome as listed in requirements.
- **Maintainability**: Modular Python code with clear function boundaries (`embed.py`, `extract.py`, `keyed_adaptive.py`, `encrypt.py`, `metrics.py`); docstrings and CLI help text; straightforward parameterization.
- **Usability**: Simple CLI with explicit flags, informative errors, and optional stdout text output; minimal configuration required for typical runs.
- **Scalability**: Handles audio from seconds to hours within RAM limits; linear processing enables scaling on desktop machines. Streaming/real‑time operation is out of scope.
- **Security**: AES‑CBC optional encryption with SHA‑256‑derived keys from passphrases; header plaintext for synchronization. Integrity (MAC) and advanced authentication are out of scope.
- **Reliability**: Deterministic ordering and fixed header support stable extraction; reproducible scripts and figures ensure consistent results.
- **Cost/Licensing**: Relies on commonly available open‑source libraries; no paid licenses required.
- **Data Constraints**: Assumes PCM 16‑bit WAV; stereo reduced to first channel for simplicity. Compression‑robustness and desynchronization attacks are out of scope.

3.3 System Design Criteria
- **Audio Format Standard**: WAV PCM 16‑bit compliance; conservative single‑LSB modifications per selected sample to preserve quality.
- **Cryptographic Practices**: AES‑CBC with PKCS#7 padding; per‑message random IV prepended to ciphertext; key bytes derived via SHA‑256 truncation from user passphrase.
- **Deterministic Ordering**: Prefix‑stable ordering generated from frame‑level energy and user key; ensures header bits are read first during extraction.
- **Coding Style & Documentation**: Pythonic, modular design aligned with PEP‑8 conventions; CLI help, README usage examples, and reproducible figure scripts.
- **Evaluation Methodology**: Use SNR (dB), LSB‑level BER, and sample‑change stats; visualize waveform/spectrograms; characterize AWGN robustness via BER vs SNR curves.
- **Scope Discipline**: Limit to time‑domain LSB, AWGN robustness, and optional AES encryption; exclude transform‑domain psychoacoustic models, error‑correcting codes, compression robustness, and desynchronization defenses for this thesis implementation.

References to Implementation
- **Embedding**: See [src/embed.py](../src/embed.py) for `embed_lsb()` and `embed_adaptive_keyed()`.
- **Extraction**: See [src/extract.py](../src/extract.py) for `extract_adaptive_keyed()`.
- **Ordering**: See [src/keyed_adaptive.py](../src/keyed_adaptive.py) for deterministic energy‑keyed index generation.
- **Encryption**: See [src/encrypt.py](../src/encrypt.py) for AES helpers.
- **Metrics**: See [src/metrics.py](../src/metrics.py) for SNR/BER and sample‑change stats.