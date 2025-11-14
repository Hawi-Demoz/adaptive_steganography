# embed.py
# Usage: import and call embed_lsb(cover_path, payload_bytes, out_path, key_frames=None)
import soundfile as sf
import numpy as np

PREAMBLE = b"ASTG"  # 4 bytes to identify start

def _bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8)).astype(np.uint8)

def _bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()

def embed_lsb(cover_wav_path: str, payload_bytes: bytes, out_wav_path: str, embed_map=None):
    """
    embed_map: optional boolean array length = num_samples indicating where to write bits.
               if None, writes sequentially from sample 0 (not recommended for stereo).
    Payload layout: PREAMBLE (4 bytes) + 4-byte length + payload_bytes
    """
    data, sr = sf.read(cover_wav_path, dtype='int16')  # keep int16 for LSB ops
    mono = False
    if data.ndim == 2:
        # Convert to mono for simplicity by using first channel
        data = data[:, 0]
        mono = True

    # build payload with header
    length_bytes = len(payload_bytes).to_bytes(4, 'big')
    full_payload = PREAMBLE + length_bytes + payload_bytes
    bits = _bytes_to_bits(full_payload)
    n_samples = data.shape[0]

    if embed_map is None:
        if bits.size > n_samples:
            raise ValueError("Payload too large for cover audio samples.")
        indices = np.arange(bits.size)
    else:
        # embed_map must be boolean array same length as data and have enough True entries
        indices = np.where(embed_map)[0]
        if bits.size > indices.size:
            raise ValueError("Payload too large for selected embedding map.")
        indices = indices[:bits.size]

    flat = data.copy()
    # clear LSB and set new
    flat[indices] = (flat[indices] & ~1) | bits.astype(np.int16)

    sf.write(out_wav_path, flat, sr, subtype='PCM_16')
    print(f"Embedded {len(payload_bytes)} bytes into {out_wav_path} (samples used: {bits.size})")
