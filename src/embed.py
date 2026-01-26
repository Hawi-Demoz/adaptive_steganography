# embed.py
# Provides simple sequential LSB embedding and an adaptive keyed variant.
import soundfile as sf
import numpy as np
from .keyed_adaptive import generate_order_indices
from .encrypt import aes_encrypt
from .robust_payload import encode_payload

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


def _read_wav_mono_int16(path: str):
    data, sr = sf.read(path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]
    return data.astype(np.int16), sr


def _capacity_from_order(order_len: int) -> int:
    overhead_bits = (len(PREAMBLE) + 4) * 8  # 64 bits
    return max(0, order_len - overhead_bits) // 8


def embed_adaptive_keyed(
    cover_wav_path: str,
    plaintext: bytes,
    out_wav_path: str,
    user_key: bytes,
    frame_size: int = 1024,
    hop_size: int = 512,
    energy_percentile: float = 0.0,
    encrypt: bool = True,
    robust_repeat: int = 1,
    robust_interleave: bool = True,
):
    """
    Adaptive, key-based embedding.
    - Builds deterministic ordering of sample indices based on key and energy.
    - Optionally encrypts the plaintext with AES-CBC using a key derived from user_key (caller provides raw bytes for AES).
    - Embeds PREAMBLE + 4-byte length + payload.
    Requirements: WAV PCM 16-bit mono (stereo will be reduced to first channel).
    """
    data, sr = _read_wav_mono_int16(cover_wav_path)
    order = generate_order_indices(
        cover_wav_path,
        key=user_key,
        frame_size=frame_size,
        hop_size=hop_size,
        energy_percentile=energy_percentile,
    )

    payload = aes_encrypt(plaintext, user_key) if encrypt else plaintext
    if robust_repeat > 1 or not robust_interleave:
        payload = encode_payload(payload, key=user_key, repeat=robust_repeat, interleave=robust_interleave)

    length_bytes = len(payload).to_bytes(4, 'big')
    full_payload = PREAMBLE + length_bytes + payload
    bits = _bytes_to_bits(full_payload)

    if bits.size > order.size:
        max_bytes = _capacity_from_order(order.size)
        raise ValueError(
            f"Payload too large. Capacity ~{max_bytes} bytes under current settings; got {len(payload)} bytes."
        )

    indices = order[:bits.size]
    flat = data.copy()
    flat[indices] = (flat[indices] & ~1) | bits.astype(np.int16)
    sf.write(out_wav_path, flat, sr, subtype='PCM_16')
    print(
        f"Embedded (adaptive+keyed) {len(payload)} bytes into {out_wav_path} (samples used: {bits.size})"
    )
