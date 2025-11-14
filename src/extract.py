# extract.py
import soundfile as sf
import numpy as np

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
