"""Lightweight robustness layer for the audio steganography payload.

This module is intentionally dependency-free (no external ECC libs).
It provides a practical first step toward robustness by combining:
- a CRC32 integrity check, and
- a simple repetition code (majority vote) plus interleaving.

This improves recovery under random bit flips (e.g., AWGN / mild processing),
while remaining compatible with the existing time-domain keyed embedding.

NOTE: Surviving lossy codecs (MP3/AAC) generally requires transform-domain
embedding (e.g., QIM / spread-spectrum). This layer is still useful there as
an inner code, but it is not sufficient by itself.
"""

from __future__ import annotations

import hashlib
import zlib

import numpy as np


_MAGIC = b"RBST"  # 4 bytes


def _bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8)).astype(np.uint8)


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits.astype(np.uint8)).tobytes()


def _seed_from(key: bytes, nbits: int, repeat: int) -> int:
    h = hashlib.sha256(key + _MAGIC + nbits.to_bytes(8, "big") + repeat.to_bytes(4, "big")).digest()
    return int.from_bytes(h[:8], "big", signed=False)


def encode_payload(payload: bytes, *, key: bytes, repeat: int = 3, interleave: bool = True) -> bytes:
    """Encode payload bytes with CRC + repetition + interleaving.

    Args:
        payload: bytes to protect (typically ciphertext when encryption is enabled).
        key: user key bytes (used only to seed interleaver, not for secrecy).
        repeat: repetition factor (odd >= 1). 1 disables repetition.
        interleave: whether to interleave repeated bits.

    Returns:
        Encoded bytes suitable for embedding.
    """

    if repeat < 1:
        raise ValueError("repeat must be >= 1")
    if repeat % 2 == 0:
        raise ValueError("repeat must be odd (majority vote)")

    crc = zlib.crc32(payload) & 0xFFFFFFFF
    header = _MAGIC + len(payload).to_bytes(4, "big") + crc.to_bytes(4, "big")
    inner = header + payload

    if repeat == 1 and not interleave:
        return inner

    bits = _bytes_to_bits(inner)
    bits_rep = np.repeat(bits, repeat)

    if interleave and bits_rep.size > 0:
        seed = _seed_from(key, int(bits_rep.size), repeat)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(bits_rep.size)
        bits_rep = bits_rep[perm]

    return _bits_to_bytes(bits_rep)


def decode_payload(encoded: bytes, *, key: bytes, repeat: int = 3, interleave: bool = True) -> bytes | None:
    """Decode payload bytes.

    Returns the original payload if CRC passes, else None.
    """

    if repeat < 1:
        raise ValueError("repeat must be >= 1")
    if repeat % 2 == 0:
        raise ValueError("repeat must be odd (majority vote)")

    bits = _bytes_to_bits(encoded)

    if interleave and bits.size > 0:
        seed = _seed_from(key, int(bits.size), repeat)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(bits.size)
        inv = np.empty_like(perm)
        inv[perm] = np.arange(perm.size)
        bits = bits[inv]

    if repeat == 1:
        inner = _bits_to_bytes(bits)
    else:
        if bits.size % repeat != 0:
            return None
        grouped = bits.reshape(-1, repeat)
        # majority vote
        inner_bits = (np.sum(grouped, axis=1) >= (repeat // 2 + 1)).astype(np.uint8)
        inner = _bits_to_bytes(inner_bits)

    if len(inner) < 12:
        return None
    if inner[:4] != _MAGIC:
        return None

    msg_len = int.from_bytes(inner[4:8], "big")
    crc_expected = int.from_bytes(inner[8:12], "big")
    payload = inner[12:12 + msg_len]
    if len(payload) != msg_len:
        return None

    crc = zlib.crc32(payload) & 0xFFFFFFFF
    if crc != crc_expected:
        return None

    return payload
