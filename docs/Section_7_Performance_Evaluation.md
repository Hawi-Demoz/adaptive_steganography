# 7. Performance Evaluation

This section evaluates the implemented adaptive audio steganography system with respect to **imperceptibility**, **correctness**, **capacity utilization**, and **computational efficiency**. Where applicable, results are reported from the reproducible sweep output in `figures/run_20260126_141809/sweep_results.csv` (cover file: `data/original/sample.wav`, mono `int16`, 44.1 kHz, 262,094 samples).

## 7.1 Key Performance Metrics

### 7.1.1 Imperceptibility / Distortion Metrics

**(a) Sample-domain distortion bound**

Because the embedding operation replaces only the least significant bit (LSB) of a 16-bit PCM sample,

$$y[i] = (x[i] \ \&\ \sim 1) \ \vert\ b_i, \quad b_i \in \{0,1\}$$

the maximum per-sample change is bounded by one quantization step:

$$\max_i |y[i]-x[i]| \le 1.$$

This bound is confirmed by the sweep metric `max_abs_diff_lsb = 1` for all cases.

**(b) Fraction of changed samples / LSB flip rate**

The metric `fraction_changed` reports the fraction of samples where the stego LSB differs from the cover LSB (equivalently, the LSB “flip rate”). For random payload bits, the expected number of flips is approximately half of the written bits:

$$\mathbb{E}[\text{LSB flips}] \approx 0.5 \times \text{bits\_used\_total}.$$

This relationship is observed across the sweep results and interactive logs.

**(c) Signal-to-noise ratio (SNR)**

SNR is computed between the cover and stego signals using a common peak normalization (to avoid scale bias across files), then noise is defined as the sample-wise difference:

$$n[i] = y[i] - x[i], \quad \mathrm{SNR}_{\mathrm{dB}} = 10\log_{10}\left(\frac{\mathbb{E}[x^2]}{\mathbb{E}[n^2]}\right).$$

Observed SNR remains very high for short payloads (≈ 101 dB) and decreases as payload length increases (≈ 82 dB at 2048 bytes), consistent with the increased number of modified samples.

### 7.1.2 Correctness / Accuracy Metrics

**(a) Extraction success (`extraction_ok`)**

A run is considered correct if the extracted payload matches the embedded payload exactly. In the sweep results, all cases report `extraction_ok = True`.

**(b) Payload bit error rate (Payload BER)**

Payload BER compares embedded payload bits to recovered payload bits:

$$\mathrm{BER} = \frac{1}{N}\sum_{k=1}^{N} \mathbf{1}[b_k \ne \hat{b}_k].$$

Across the parameter sweep, `payload_bit_ber = 0.0` for all successful extractions, indicating perfect recovery when the correct key and parameters are used.

**(c) LSB BER (cover vs stego)**

The project also computes LSB BER between cover and stego. This is not an extraction error metric; it is a *distortion metric* that indicates how frequently the LSB changed relative to the cover.

### 7.1.3 Capacity and Overhead Metrics

**(a) Bits used accounting**

The embedded bitstream always includes a fixed header:
- `ASTG` preamble (4 bytes)
- payload length (4 bytes)

Thus, header size is 8 bytes = 64 bits. Total used bits are:

$$\text{bits\_used\_total} = 64 + 8\cdot\text{payload\_bytes}.$$

**(b) AES encryption overhead (when enabled)**

When AES-CBC with PKCS#7 padding is enabled, the embedded payload becomes `IV || ciphertext`.
- IV length = 16 bytes
- ciphertext length = padded length (multiple of 16)

This increases `bits_used_total` and slightly reduces SNR. Example from the sweep:
- `message_len_bytes = 256`, `energy_percentile = 20`
  - without encryption: `bits_used_total = 2112`, `snr_db = 91.22`
  - with encryption: `bits_used_total = 2368`, `snr_db = 90.73`

### 7.1.4 Efficiency / Speed Metrics (runtime)

Runtime is evaluated on the thesis development machine using the same cover file (`262,094` samples) and file-based WAV I/O.

Two schemes are compared:
- **Sequential LSB (baseline)**: writes bits into samples starting at index 0 (no key ordering).
- **Adaptive + keyed embedding (baseline at `energy_percentile=0`)**: generates a deterministic key-based ordering over all samples and embeds into the first indices of that ordering.

Measured single-run times (seconds) are summarized below (file system caching can affect individual measurements, so values are interpreted as approximate).

| Scheme | Payload (bytes) | Embed time (s) | Extract time (s) | Extraction OK |
| --- | ---: | ---: | ---: | --- |
| Sequential LSB | 16 | 0.0190 | 0.0096 | True |
| Adaptive+Keyed (e=0) | 16 | 0.0467 | 0.0489 | True |
| Sequential LSB | 256 | 0.0056 | 0.0093 | True |
| Adaptive+Keyed (e=0) | 256 | 0.0476 | 0.0490 | True |
| Sequential LSB | 2048 | 0.0056 | 0.0094 | True |
| Adaptive+Keyed (e=0) | 2048 | 0.0480 | 0.0476 | True |

Key observation: **adaptive+keyed embedding incurs additional compute cost** due to generating a full-signal ordering (including an $O(N\log N)$ stable sort), while sequential embedding is closer to an $O(K)$ modification operation after file I/O.

### 7.1.5 Power Consumption

This project is evaluated as an **offline software simulation** (Python on a desktop/laptop CPU). **Direct electrical power draw was not instrumented**, so no measured wattage is reported.

However, the implementation is lightweight in memory (primarily a few arrays of length $N$ samples) and runs in tens of milliseconds per embed/extract for a ~6 s audio clip, indicating low computational demand for offline use.

## 7.2 Comparative Analysis

### 7.2.1 Comparison Across Payload Length (capacity vs. distortion)

Increasing the secret message length increases `bits_used_total`, which increases the expected number of LSB flips and therefore increases distortion. This appears clearly in the sweep results (encryption disabled, all `extraction_ok=True`):

| message_len_bytes | bits_used_total | fraction_changed (≈ flips / N) | snr_db (e=0) |
| ---: | ---: | ---: | ---: |
| 16 | 192 | 0.039% | 101.02 |
| 256 | 2112 | 0.396% | 91.24 |
| 2048 | 16448 | 3.098% | 82.34 |

Interpretation in terms of design objectives:
- **Imperceptibility:** Even at 2048 bytes, the waveform difference is bounded to ±1 LSB per modified sample, and SNR remains > 80 dB.
- **Capacity:** The system can embed larger payloads by using more sample positions, at the cost of reduced SNR.

### 7.2.2 Comparison Across Energy Adaptivity Levels (distribution/localization)

The parameter `energy_percentile` does not primarily determine *how much* noise is injected (payload length dominates that). Instead, it determines **where** the modifications occur.

This is captured by `frac_mod_in_top_energy_frames`, defined as the fraction of modified samples that lie inside the top 20% highest-energy frames (computed from LSB-cleared cover audio so the ordering is stable).

For the 256-byte payload case (encryption disabled):

| energy_percentile | fraction_changed | snr_db | frac_mod_in_top_energy_frames |
| ---: | ---: | ---: | ---: |
| 0 | 0.396% | 91.24 | 42.775% |
| 20 | 0.398% | 91.22 | 45.298% |
| 40 | 0.436% | 90.82 | 48.164% |

Interpretation:
- **Perceptual masking improves with adaptivity**: a larger fraction of modifications are pushed into louder regions, where LSB noise is harder to perceive.
- **Global SNR changes little with adaptivity** for a fixed payload size, because the *total number* of modified samples is similar.

### 7.2.3 Comparison of Encryption Enabled vs Disabled (security overhead)

Encryption increases payload size due to the IV and padding, which increases the number of embedded bits and slightly increases distortion.

Example (256-byte message, `energy_percentile=20`):
- No encryption: `bits_used_total = 2112`, `fraction_changed = 0.398%`, `snr_db = 91.22`
- AES enabled: `bits_used_total = 2368`, `fraction_changed = 0.445%`, `snr_db = 90.73`

Design objective interpretation:
- **Security:** confidentiality is substantially improved because recovered bits without the correct key are ciphertext.
- **Imperceptibility trade-off:** the overhead produces a small but measurable SNR decrease.

### 7.2.4 Baseline Comparison: Sequential LSB vs Adaptive+Keyed

Sequential LSB embedding is computationally cheaper and yields similar distortion metrics for the same number of embedded bits; however, it has **weaker security properties**:
- Embedding locations are predictable (starting at sample 0).
- Simple steganalysis can target the early region of the signal.

Adaptive+keyed embedding improves security and perceptual placement by:
- Using a **key-seeded pseudo-random ordering** of positions.
- Biasing placement toward higher-energy frames (controlled by `energy_percentile`).

## 7.3 Optimization Efforts

Several implementation decisions were made to improve performance, robustness of extraction, and repeatability.

### 7.3.1 Ordering Stability (prevents extraction failure)

A critical optimization for correctness is computing frame energy on the **LSB-cleared** signal:

$$x_\mathrm{energy}[i] = x[i] \ \&\ \sim 1.$$

This ensures that the energy ranking (and therefore the deterministic ordering) does not drift between cover and stego due to the embedding itself.

### 7.3.2 Deterministic, Prefix-Stable Ordering

The ordering is computed using:

$$\mathrm{ord\_key}[i] = \frac{r[i]}{\mathrm{score}[i] + \epsilon},$$

where $r[i]$ is a deterministic pseudo-random value derived from the key and signal length, and `score[i]` is the per-sample energy score inherited from the frame RMS.

A **stable sort** (`mergesort`) is used to guarantee deterministic tie-handling and prefix stability, enabling the extractor to always read the fixed header first.

### 7.3.3 Efficient Data Types and Operations

- Embedding is performed in the `int16` domain to match WAV PCM and guarantee the ±1 LSB bound.
- Metrics use vectorized NumPy operations (`xor`, masking, mean-square computations) to keep evaluation overhead low.

### 7.3.4 Controlled Parameterization

The system exposes `frame_size`, `hop_size`, and `energy_percentile` to tune the imperceptibility–capacity trade-off without changing the algorithm. A reproducible non-interactive sweep (`src/sweep_experiments.py`) is used to generate consistent thesis figures and tables.

### 7.3.5 Optional Robustness Layer (extensible)

The pipeline includes an optional robustness wrapper (`repeat` and `interleave`) for payload encoding/decoding. While disabled in the core thesis sweep, this provides a structured path for future optimization toward robustness against mild channel noise (at the cost of capacity).
