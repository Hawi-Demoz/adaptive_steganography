import numpy as np
import soundfile as sf


def compute_snr_db(original_wav: str, stego_wav: str) -> float:
    x, _ = sf.read(original_wav, dtype='float32')
    y, _ = sf.read(stego_wav, dtype='float32')
    if x.ndim == 2:
        x = x[:, 0]
    if y.ndim == 2:
        y = y[:, 0]
    x = x.astype(np.float64)
    y = y.astype(np.float64)

    # Normalize to a common peak to avoid scale bias
    peak = max(np.max(np.abs(x)), np.max(np.abs(y)), 1e-12)
    x = x / peak
    y = y / peak

    noise = y - x
    p_sig = np.mean(x * x) + 1e-12
    p_noise = np.mean(noise * noise) + 1e-12
    return 10.0 * np.log10(p_sig / p_noise)


def compute_ber(bits_a: np.ndarray, bits_b: np.ndarray) -> float:
    if bits_a.size != bits_b.size:
        raise ValueError("Bit arrays must be same length for BER.")
    if bits_a.size == 0:
        return 0.0
    return float(np.sum(bits_a.astype(np.uint8) != bits_b.astype(np.uint8))) / bits_a.size


def compute_lsb_ber(original_wav: str, stego_wav: str) -> float:
    x, _ = sf.read(original_wav, dtype='int16')
    y, _ = sf.read(stego_wav, dtype='int16')
    if x.ndim == 2:
        x = x[:, 0]
    if y.ndim == 2:
        y = y[:, 0]
    n = min(x.shape[0], y.shape[0])
    if n == 0:
        return 0.0
    x = x[:n].astype(np.int16)
    y = y[:n].astype(np.int16)
    bits_a = (x & 1).astype(np.uint8)
    bits_b = (y & 1).astype(np.uint8)
    return compute_ber(bits_a, bits_b)


def compute_sample_change_stats(original_wav: str, stego_wav: str) -> dict:
    """
    Compute sample-level change metrics between cover and stego.
    Returns a dict with counts, fractions, max diff, SNR, and BER.
    """
    x, _ = sf.read(original_wav, dtype='int16')
    y, _ = sf.read(stego_wav, dtype='int16')
    if x.ndim == 2:
        x = x[:, 0]
    if y.ndim == 2:
        y = y[:, 0]

    n = min(x.shape[0], y.shape[0])
    if n == 0:
        return {
            "samples_total": 0,
            "samples_changed": 0,
            "fraction_changed": 0.0,
            "lsb_changed": 0,
            "max_abs_diff": 0,
            "snr_db": 0.0,
            "ber_lsb": 0.0,
        }

    x = x[:n].astype(np.int16)
    y = y[:n].astype(np.int16)
    diff = y.astype(np.int32) - x.astype(np.int32)
    samples_changed = int(np.sum(diff != 0))
    max_abs_diff = int(np.max(np.abs(diff))) if diff.size else 0
    lsb_changed = int(np.sum(((x ^ y) & 1) != 0))

    # SNR in dB using common peak normalization
    xf = x.astype(np.float64)
    yf = y.astype(np.float64)
    peak = max(np.max(np.abs(xf)), np.max(np.abs(yf)), 1e-12)
    xf /= peak
    yf /= peak
    noise = yf - xf
    p_sig = np.mean(xf * xf) + 1e-12
    p_noise = np.mean(noise * noise) + 1e-12
    snr_db = 10.0 * np.log10(p_sig / p_noise)

    # BER on LSBs
    bits_a = (x & 1).astype(np.uint8)
    bits_b = (y & 1).astype(np.uint8)
    ber_lsb = compute_ber(bits_a, bits_b)

    return {
        "samples_total": n,
        "samples_changed": samples_changed,
        "fraction_changed": float(samples_changed) / float(n),
        "lsb_changed": lsb_changed,
        "max_abs_diff": max_abs_diff,
        "snr_db": float(snr_db),
        "ber_lsb": float(ber_lsb),
    }
