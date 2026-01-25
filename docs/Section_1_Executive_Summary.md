1. Executive Summary

This project designs and simulates an adaptive, keyed audio steganography system that embeds secret information into 16‑bit PCM WAV signals while preserving perceptual transparency and enabling reliable extraction. The implementation operates in the time domain using least significant bit (LSB) embedding, guided by frame‑level energy analysis and a user key to produce a deterministic ordering of sample positions. Optional AES‑CBC encryption is applied to the payload to ensure confidentiality; a fixed header (preamble + length) remains plaintext for synchronization.

Project Objectives
- Maintain imperceptibility at conservative payloads, demonstrated via objective metrics (SNR, LSB‑level BER, sample‑change statistics) and visual analyses (waveform, spectrograms, LSB modification heatmaps).
- Provide reliable extraction through a deterministic, key‑dependent sample ordering and a simple header for framing.
- Characterize robustness under additive white Gaussian noise (AWGN) using BER versus SNR curves.
- Deliver reproducible Python tooling, scripts, and figures suitable for an undergraduate project report.

Design Approach and Key Choices
- Time‑domain LSB with energy adaptivity: Higher‑energy frames are prioritized for earlier embedding; quieter or tonal regions are naturally throttled to protect perceptual quality.
- Deterministic ordering: A user key and frame‑level energy determine a stable sample order used consistently for embedding and extraction.
- Confidentiality: Payload bytes can be AES‑CBC encrypted (PKCS#7); the header stays plaintext to support synchronization.
- Scope limitations: Simulation‑only on WAV PCM 16‑bit files (mono, or first channel of stereo). Robustness focus is AWGN; compression robustness (e.g., MP3), desynchronization attacks, and error‑correcting codes are out of scope.

Methodology and Evaluation
- Tooling: Python (NumPy, SciPy, SoundFile, Matplotlib) and project modules (`embed.py`, `extract.py`, `keyed_adaptive.py`, `encrypt.py`, `metrics.py`, `visualize.py`).
- Pipeline: Build ordering from energy + key; optionally encrypt payload; embed header + payload via LSB; extract using the same ordering and header parsing.
- Metrics: SNR (dB), LSB‑level BER, and sample‑change statistics; visual inspection via waveform/spectrograms and LSB heatmaps. Robustness characterized by BER versus AWGN SNR.

Results (Simulated)
- Imperceptibility: High SNR and low LSB‑change fractions at conservative payloads; informal listening indicates no audible artifacts for typical speech/music clips.
- Payload: Content‑adaptive throughput suitable for covert metadata and short messages; conservative throttling in low‑energy segments protects audio quality.
- Robustness: Low BER at high SNRs under AWGN and predictable degradation as noise increases; extraction stability aided by the header and deterministic ordering.

Conclusion
Within the defined simulation scope, the keyed, energy‑adaptive LSB approach meets undergraduate‑level design goals by balancing perceptual quality, practical payload, and straightforward robustness characterization. Future work may explore psychoacoustic masking models, compression‑robust embedding, error‑control coding, and defenses against desynchronization attacks.
