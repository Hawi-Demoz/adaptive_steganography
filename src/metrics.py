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
