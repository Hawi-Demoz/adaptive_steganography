# adaptive_mask.py
import numpy as np
import soundfile as sf

def compute_energy_mask(wav_path: str, frame_size=1024, hop_size=512, percentile=60):
    """
    Returns: boolean mask of length = num_samples indicating good sample positions to embed.
    Approach:
      - Compute frame energies (mean absolute value).
      - Mark frames with energy >= percentile threshold as candidate frames.
      - Convert frame flags to per-sample boolean mask.
    """
    data, sr = sf.read(wav_path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]

    n = len(data)
    energies = []
    frames = []
    for i in range(0, n, hop_size):
        frame = data[i:i+frame_size]
        if frame.size == 0:
            break
        energies.append(np.mean(np.abs(frame)))
        frames.append((i, frame.size))
    energies = np.array(energies)
    thresh = np.percentile(energies, percentile)
    mask_frames = energies >= thresh

    # convert frames -> sample mask
    mask = np.zeros(n, dtype=bool)
    for flag, (start, size) in zip(mask_frames, frames):
        if flag:
            mask[start:start+size] = True
    return mask
