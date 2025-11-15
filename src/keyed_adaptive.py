import hashlib
import numpy as np
import soundfile as sf


def _read_wav_mono_int16(path: str):
    data, sr = sf.read(path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]
    return data.astype(np.int16), sr


def _frame_edges(n: int, frame_size: int, hop_size: int):
    edges = []
    for start in range(0, n, hop_size):
        end = min(start + frame_size, n)
        if start >= end:
            break
        edges.append((start, end))
    return edges


def _frame_rms(data: np.ndarray, frame_size=1024, hop_size=512) -> tuple[np.ndarray, list[tuple[int, int]]]:
    n = data.shape[0]
    edges = _frame_edges(n, frame_size, hop_size)
    rms = []
    for s, e in edges:
        frame = data[s:e].astype(np.float32)
        if frame.size == 0:
            rms.append(0.0)
        else:
            rms.append(float(np.sqrt(np.mean(frame.astype(np.float32) ** 2))))
    return np.array(rms, dtype=np.float32), edges


def _normalize_scores(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    mn = float(np.min(x))
    mx = float(np.max(x))
    if mx - mn < 1e-12:
        return np.ones_like(x, dtype=np.float32)
    return (x - mn) / (mx - mn)


def _hash_to_seed(key: bytes) -> int:
    h = hashlib.sha256(key).digest()
    # use 8 bytes for 64-bit seed
    return int.from_bytes(h[:8], 'big', signed=False)


def generate_order_indices(audio_path: str,
                            key: bytes,
                            frame_size: int = 1024,
                            hop_size: int = 512,
                            energy_percentile: float = 0.0) -> np.ndarray:
    """
    Produce a deterministic, key-dependent, energy-adaptive ordering of sample indices.
    - High-energy frames get earlier indices (higher priority), low-energy later.
    - Ordering is independent of the number of bits to embed (prefix-stable).
    - energy_percentile in [0,100): frames below this RMS percentile are strongly deprioritized.
    Returns: np.ndarray of indices sorted by adaptive key.
    """
    data, _ = _read_wav_mono_int16(audio_path)
    n = data.shape[0]
    rms, edges = _frame_rms(data, frame_size=frame_size, hop_size=hop_size)
    scores = _normalize_scores(rms)

    # Optional thresholding: attenuate frames below percentile by shrinking score
    if energy_percentile > 0.0:
        thr = np.percentile(scores, energy_percentile)
        # reduce low-energy scores to near-zero to push them late
        low = scores < thr
        scores = scores.copy()
        scores[low] *= 0.1

    # Build per-sample scores by mapping frame score to all samples in that frame
    per_sample_score = np.zeros(n, dtype=np.float32)
    for (s, e), sc in zip(edges, scores):
        per_sample_score[s:e] = sc

    # Deterministic random component from key (prefix stable for fixed n)
    seed = _hash_to_seed(key)
    rng = np.random.default_rng(seed)
    rand = rng.random(n, dtype=np.float32)

    # Compute ordering key: smaller is earlier. Avoid divide-by-zero via epsilon
    eps = 1e-6
    # Higher energy (score close to 1) -> rand/(1+score) is smaller on average
    ord_key = rand / (per_sample_score + eps)

    # Stable argsort to get deterministic ordering
    order = np.argsort(ord_key, kind='mergesort')
    return order.astype(np.int64)
