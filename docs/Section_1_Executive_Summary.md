1. Executive Summary

This project designs and simulates an adaptive, keyed audio steganography system that embeds secret information into 16‑bit PCM WAV signals while preserving perceptual transparency and enabling reliable extraction. The implementation operates in the time domain using least significant bit (LSB) embedding. Embedding locations are selected by a deterministic ordering that combines (i) frame‑level energy (RMS) and (ii) a user key (pseudo‑random seed). Optional AES‑CBC encryption (with PKCS#7 padding) is applied to the payload to provide confidentiality; a fixed, plaintext header (preamble + payload length) is used for synchronization during extraction.

Project Objectives
- Maintain imperceptibility at conservative payloads, demonstrated via objective metrics (SNR, LSB‑level BER, sample‑change statistics) and visual analyses (waveform, spectrograms, LSB modification heatmaps).
- Provide reliable extraction through a deterministic, key‑dependent sample ordering and a simple header for framing.
- Characterize robustness under additive white Gaussian noise (AWGN) using BER versus added‑noise SNR curves (to illustrate the inherent fragility of time‑domain LSB to channel noise).
- Deliver reproducible Python tooling, scripts, and figures suitable for an undergraduate project report.

Design Approach and Key Choices
- Time‑domain LSB with energy adaptivity: Higher‑energy frames are prioritized for earlier embedding so that modifications occur more often in perceptually masked (louder) regions.
- Deterministic ordering: A user key and frame‑level energy determine a stable sample order used consistently for embedding and extraction.
- Confidentiality: Payload bytes can be AES‑CBC encrypted (PKCS#7); the header stays plaintext to support synchronization.
- Scope limitations: Simulation‑only on uncompressed WAV PCM 16‑bit files (mono, or first channel of stereo). Robustness testing focuses on AWGN; robustness to resampling, lossy compression (e.g., MP3), desynchronization attacks, and error‑correcting codes are out of scope.

Methodology and Evaluation
- Tooling: Python (NumPy, SciPy, SoundFile, Matplotlib) and project modules (`embed.py`, `extract.py`, `keyed_adaptive.py`, `encrypt.py`, `metrics.py`, `visualize.py`).
- Pipeline: Build ordering from energy + key; optionally encrypt payload; embed header + payload via LSB; extract using the same ordering and header parsing.
- Metrics: SNR (dB), LSB flip rate / sample‑change statistics (including the ±1 LSB distortion bound), and payload BER (to confirm lossless extraction when parameters match). Visual inspection is supported via waveform/spectrogram plots and LSB‑difference heatmaps. Robustness is illustrated by BER versus AWGN SNR.

Results (Simulated)
- Imperceptibility: High SNR and very small bounded waveform differences (±1 LSB per modified sample) at conservative payloads; plots show strong overlap between cover and stego waveforms and negligible spectrogram differences.
- Payload capacity: Capacity scales with the number of available audio samples (one embedded bit per selected sample) minus a fixed 64‑bit header and any encryption overhead. The energy adaptivity parameter primarily changes *where* modifications occur rather than increasing the theoretical capacity.
- Robustness: Under AWGN, BER increases as added noise increases, consistent with known limitations of LSB embedding. Extraction remains exact when the correct key and matching parameters are used and the stego signal is not significantly distorted.

Conclusion
Within the defined simulation scope, the keyed, energy‑adaptive LSB approach meets undergraduate‑level design goals by balancing perceptual quality, practical payload, and deterministic extraction. Future work may explore stronger psychoacoustic masking models, compression‑robust embedding, error‑control coding, and defenses against desynchronization attacks.
