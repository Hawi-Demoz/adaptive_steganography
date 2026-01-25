4. System Design and Architecture

4.1 Overall System Architecture

The system is a simulation‑oriented, offline pipeline for embedding and extracting a payload from a 16‑bit PCM WAV audio signal. The design emphasizes:
- **Imperceptibility** via single‑LSB modifications and **energy‑adaptive placement** (prefer higher‑energy regions).
- **Security** via optional **AES‑CBC** encryption of the payload bytes.
- **Reliability** via a simple plaintext **header** (`ASTG` preamble + 4‑byte length) and **deterministic key‑dependent ordering**.

4.1.1 Embedding Architecture (High‑Level)

Block diagram (embedding):

```
 User message/file + Key + Parameters
          |
          v
   [Optional AES Encrypt]
          |
          v
 [Header + Payload Builder]
   (ASTG + length + bytes)
          |
          v
     [Bytes -> Bits]
          |
          v
 Cover WAV -> [Read int16 mono] -> [Energy analysis per frame]
                                  |
                                  v
                         [Keyed ordering of sample indices]
                                  |
                                  v
                     [LSB embed bits at earliest indices]
                                  |
                                  v
                           Stego WAV (PCM_16)
```

Data flow summary:
- The cover audio is loaded as `int16` (mono, or first channel of stereo).
- Frame‑level energy is computed and used to bias which samples are used earlier.
- A user key produces a deterministic permutation/order of candidate sample indices.
- The payload is optionally encrypted, then framed with a plaintext header.
- Payload bits replace the LSB of the selected samples; the stego audio is saved as PCM 16‑bit.

4.1.2 Extraction Architecture (High‑Level)

Block diagram (extraction):

```
 Stego WAV + Key + Parameters
          |
          v
 [Read int16 mono]
          |
          v
 [Energy analysis per frame]
          |
          v
 [Recompute keyed ordering]
          |
          v
 [Read header bits first]
  (ASTG + length)
          |
          v
 [Read payload bits (length)]
          |
          v
     [Bits -> Bytes]
          |
          v
  [Optional AES Decrypt]
          |
          v
     Recovered plaintext
```

Key point: extraction is reliable in the noiseless case only if the **same key and parameters** (frame size, hop size, energy thresholding) are used to reproduce the exact ordering.

4.1.3 Evaluation and Reporting Architecture

Evaluation is separate from embedding/extraction and is used to quantify transparency and robustness.

```
 Cover WAV + Stego WAV
         |
         v
 [Metrics]
  - SNR (dB)
  - LSB-BER
  - sample-change statistics
         |
         v
 [Plots / Figures]
  - waveform comparison
  - spectrogram comparison
  - BER vs AWGN SNR
  - LSB heatmaps
```

4.2 Subsystem Descriptions

This section breaks the system into subsystems that correspond closely to the source modules.

4.2.1 Command-Line Interface (CLI)
- **Responsibility**: Provide a repeatable interface for embedding and extraction; parse parameters; derive an AES key from a passphrase.
- **Inputs**: file paths, key string, message (text or file), energy/frame parameters, encrypt/decrypt toggles.
- **Outputs**: stego WAV, recovered plaintext (stdout or file), optional metrics printouts.
- **Module**: `src/cli.py`.

4.2.2 Audio I/O and Preprocessing
- **Responsibility**: Load WAV files for bit‑level operations and ensure consistent sample format.
- **Design choice**: Use `int16` for LSB manipulation. If stereo, use the first channel for simplicity.
- **Module**: `src/embed.py`, `src/extract.py` (SoundFile backend).

4.2.3 Energy Analysis (Content Adaptivity)
- **Responsibility**: Estimate per‑frame energy (e.g., RMS) to identify regions where LSB changes are more perceptually masked.
- **Output**: energy scores used to bias the ordering of indices.
- **Module**: `src/keyed_adaptive.py` (ordering generation is energy‑aware).

4.2.4 Keyed Deterministic Ordering
- **Responsibility**: Produce a deterministic ordering of sample indices from (audio energy, key, parameters) so the same order is reproducible at extraction.
- **Rationale**: Provides “position secrecy” and avoids a fixed sequential embedding pattern.
- **Module**: `src/keyed_adaptive.py`.

4.2.5 Payload Framing (Header)
- **Responsibility**: Provide synchronization and length information for extraction.
- **Format**: `ASTG` (4 bytes) + payload length (4 bytes, big‑endian) + payload bytes.
- **Rationale**: The plaintext header lets the extractor know where the payload starts and how many bits to read.
- **Modules**: `src/embed.py`, `src/extract.py`.

4.2.6 LSB Embedding Core
- **Responsibility**: Convert bytes to bits and write one bit per selected audio sample by replacing the LSB.
- **Design choice**: Modify exactly one bit-plane (LSB) to preserve audio quality.
- **Modules**: `src/embed.py`.

4.2.7 Extraction Core
- **Responsibility**: Read LSBs from the same deterministic index order, recover header, then recover payload bytes.
- **Error modes**: wrong key/parameters, header mismatch, insufficient capacity.
- **Modules**: `src/extract.py`.

4.2.8 Cryptography (Optional AES)
- **Responsibility**: Encrypt the payload before embedding and decrypt after extraction.
- **Mode**: AES‑CBC with PKCS#7 padding; random 16‑byte IV prepended to ciphertext.
- **Key handling**: CLI derives AES key bytes from the passphrase via SHA‑256 truncation.
- **Modules**: `src/encrypt.py` and key derivation in `src/cli.py`.

4.2.9 Metrics and Visualization
- **Responsibility**: Quantify transparency and robustness and generate plots for the thesis.
- **Metrics**: SNR, LSB‑BER, sample‑change statistics.
- **Visuals**: waveform and spectrogram comparisons, BER vs SNR curves, heatmaps.
- **Modules**: `src/metrics.py`, `src/visualize.py`, `src/viz_demo.py`.

4.3 Design Considerations

4.3.1 Imperceptibility vs Capacity
- **Trade‑off**: Increasing payload generally increases the fraction of samples modified.
- **Decision**: Use one LSB per selected sample and bias selection toward higher‑energy regions to improve masking.
- **Rationale**: Provides a simple, explainable approach with strong perceptual performance at conservative payloads.

4.3.2 Robustness vs Simplicity
- **Trade‑off**: Time‑domain LSB is fragile to heavy signal processing (lossy compression, resampling).
- **Decision**: Focus robustness evaluation on AWGN (additive noise) in a simulation setting.
- **Rationale**: Matches the project’s scope limitations and keeps the implementation compact and reproducible.

4.3.3 Security Layering (Positions + Encryption)
- **Trade‑off**: Keyed ordering hides positions but does not protect message content if bits are recovered.
- **Decision**: Add optional AES‑CBC encryption so recovered bits appear as ciphertext without the key.
- **Rationale**: “Defense in depth”: position secrecy + content confidentiality.

4.3.4 Determinism and Reproducibility
- **Trade‑off**: True randomness improves unpredictability but complicates reproducibility.
- **Decision**: Use deterministic key‑dependent ordering so embed/extract are perfectly reproducible for a fixed configuration.
- **Rationale**: Ensures consistent results for experiments and thesis figures.

4.3.5 Parameter Choices (Frame Size, Hop Size, Energy Threshold)
- **Frame/hop**: Controls smoothing of energy estimates and how strongly adaptivity follows short‑term dynamics.
- **Energy percentile**: Skips low‑energy frames to reduce perceptible distortion.
- **Rationale**: Exposes simple tuning knobs for controlling quality/capacity trade‑offs.

4.3.6 Mono Handling and Implementation Scope
- **Decision**: Reduce stereo to the first channel.
- **Rationale**: Minimizes complexity and avoids stereo image artifacts from asymmetric embedding.
- **Limitation**: Does not preserve stereo embedding capacity; stereo‑aware embedding is a future extension.

4.3.7 Error Handling and Failure Modes
- Wrong key or mismatched parameters → preamble mismatch or unintelligible decrypted payload.
- Payload too large → capacity error before embedding.
- Channel distortion/noise → BER increase; decryption may fail due to padding errors.

4.3.8 Future Extensions (Beyond Current Scope)
- Payload integrity (e.g., HMAC over ciphertext) to detect tampering.
- Error‑control coding to improve robustness under mild distortions.
- Compression robustness evaluation (MP3/AAC) and desynchronization defenses.
- Stereo‑aware embedding and improved perceptual models.
