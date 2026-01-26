# extract.py
import soundfile as sf
import numpy as np
from .keyed_adaptive import generate_order_indices
from .encrypt import aes_decrypt
from .robust_payload import decode_payload

PREAMBLE = b"ASTG"

def _bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()

def extract_lsb(stego_wav_path: str, max_payload_bytes=5000, embed_map=None):
    data, sr = sf.read(stego_wav_path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]

    n = data.shape[0]
    if embed_map is None:
        # read sequentially
        bits = (data[:(8*(4+4+max_payload_bytes))] & 1).astype(np.uint8)
    else:
        bits = (data[embed_map] & 1).astype(np.uint8)

    # convert to bytes and search for preamble
    bytes_all = _bits_to_bytes(bits)
    # find preamble
    idx = bytes_all.find(PREAMBLE)
    if idx == -1:
        print("Preamble not found.")
        return None
    # read length
    start = idx + len(PREAMBLE)
    if start + 4 > len(bytes_all):
        print("Not enough data to read length.")
        return None
    length = int.from_bytes(bytes_all[start:start+4], 'big')
    data_start = start + 4
    data_end = data_start + length
    if data_end > len(bytes_all):
        print("Payload length indicates more data than available. Try increasing max_payload_bytes.")
        return None
    payload = bytes_all[data_start:data_end]
    print(f"Extracted payload of length {length} bytes.")
    return payload


def _read_wav_mono_int16(path: str):
    data, sr = sf.read(path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]
    return data.astype(np.int16), sr


def extract_adaptive_keyed(
    stego_wav_path: str,
    user_key: bytes,
    frame_size: int = 1024,
    hop_size: int = 512,
    energy_percentile: float = 0.0,
    decrypt: bool = True,
    max_total_bytes_hint: int | None = None,
    robust_repeat: int = 1,
    robust_interleave: bool = True,
):
    """
    Reverse of embed_adaptive_keyed. Uses the same deterministic ordering to read bits.
    Steps:
      - Generate order indices using key and energy.
      - Read first 64 bits to get PREAMBLE + length.
      - Read the remaining bits based on length.
      - Optionally AES-decrypt using user_key.
    """
    data, _ = _read_wav_mono_int16(stego_wav_path)
    order = generate_order_indices(
        stego_wav_path,
        key=user_key,
        frame_size=frame_size,
        hop_size=hop_size,
        energy_percentile=energy_percentile,
    )

    # Read header (64 bits)
    header_bits = (data[order[:64]] & 1).astype(np.uint8)
    header_bytes = _bits_to_bytes(header_bits)
    if not header_bytes.startswith(PREAMBLE):
        print("Preamble not found in header.")
        return None
    length = int.from_bytes(header_bytes[len(PREAMBLE):len(PREAMBLE)+4], 'big')

    total_bits = 64 + length * 8
    if total_bits > order.size:
        print("Indicated payload exceeds capacity.")
        return None

    bits = (data[order[:total_bits]] & 1).astype(np.uint8)
    bytes_all = _bits_to_bytes(bits)
    payload = bytes_all[8:8+length]
    print(f"Extracted payload of length {length} bytes (adaptive+keyed).")

    if robust_repeat > 1 or not robust_interleave:
        decoded = decode_payload(payload, key=user_key, repeat=robust_repeat, interleave=robust_interleave)
        if decoded is None:
            print("Robust decode failed (CRC/ECC).")
            return None
        payload = decoded

    if decrypt:
        try:
            payload = aes_decrypt(payload, user_key)
        except Exception as e:
            print(f"AES decrypt failed: {e}")
            return None
    return payload
