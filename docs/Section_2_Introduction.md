2. Introduction (Brief and practical)

2.1 Project Background and Motivation
- Practical relevance: Audio steganography enables covert communication, content authentication, and metadata embedding in consumer audio channels without perceptible artifacts. It is applicable to privacy-preserving messaging, digital watermarking for intellectual property protection, and low-profile telemetry in constrained environments.
- Problem statement: Design and simulate an adaptive embedding system that hides secret data in audio such that modifications remain below perceptual thresholds while maintaining robustness against common signal processing operations (e.g., compression, filtering, and additive noise). The key engineering trade-off is imperceptibility vs. payload capacity vs. robustness.
- Real-world applications: Secure audio-based alerts embedded in broadcast content, passive watermarking for ownership tracking, resilient metadata tags in voice recordings, and audio-guided low-bandwidth data channels in embedded systems.

2.2 Objectives and Scope
- Objectives:
  - Implement a content-adaptive, keyed LSB embedding scheme that prioritizes higher-energy frames for earlier use, producing a deterministic sample ordering based on audio energy and a user key.
  - Build end-to-end encoder/decoder in Python using NumPy/SciPy/SoundFile, with optional AES encryption of the payload and a fixed preamble + length header for reliable extraction.
  - Evaluate imperceptibility using objective metrics implemented in the codebase (SNR, LSB-level BER, sample change statistics) and visual analysis (waveform, spectrograms).
  - Assess robustness to additive white Gaussian noise (AWGN) via BER vs. SNR curves; optionally explore simple filtering effects.
  - Target practical payloads while preserving audio quality and synchronization; adapt capacity to audio content and key settings.
- Scope limitations:
  - Simulation-only: no hardware capture–playback loop or real-time DSP target; experiments conducted on WAV PCM 16-bit files (mono/stereo, 16–44.1 kHz; stereo reduced to first channel for embedding/extraction simplicity).
  - Transform-domain psychoacoustic modeling is not implemented; the approach is time-domain LSB with energy-based adaptivity rather than full STFT psychoacoustic masking.
  - Channels: robustness evaluation focuses on AWGN; compression robustness (e.g., MP3) and aggressive desynchronization attacks (time-scale modification, cropping) are out of scope.
  - Security: AES encryption of payload is supported; error-correcting codes are not included in the current implementation.
- Key deliverables:
  - Algorithm specification and block diagrams for keyed adaptive LSB embedding and extraction.
  - Python implementation (NumPy/SciPy/SoundFile/Matplotlib) of embedding/extraction, energy analysis, AES encryption, and metrics.
  - Test corpus, simulation scripts, and reproducible figures (waveform/spectrogram comparisons, BER vs. SNR, LSB modification heatmaps).
  - Performance summary tables and concise documentation suitable for an undergraduate project report.

2.3 Expected Outcomes
- Imperceptibility: Maintain high objective audio quality, evidenced by SNR values indicating low embedding noise and low LSB-change fractions; informal listening indicates no audible artifacts for typical speech and music clips at conservative payloads.
- Robustness: Demonstrate low BER at high SNRs in AWGN tests and characterize BER degradation as SNR decreases; confirm stable extraction via preamble/length header and deterministic ordering.
- Payload: Achieve content-adaptive throughput suitable for covert metadata and short messages, with conservative throttling in low-energy or tonal segments to protect perceptual quality.
- Reproducibility: Provide complete Python scripts and datasets enabling repeatable results; include figures and tables summarizing trade-offs between payload, imperceptibility, and BER under noise.
