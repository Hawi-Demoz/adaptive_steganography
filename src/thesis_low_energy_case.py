"""Thesis-ready low-energy (energy_percentile=0) simulation run.

This script runs one fully reproducible embed/extract cycle and prints
all key values typically reported in the terminal (payload sizes, bits used,
flips, SNR/BER, recovered message). It also saves standard figures.

Run:
  python -m src.thesis_low_energy_case
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np

from .embed import embed_adaptive_keyed
from .extract import extract_adaptive_keyed
from .encrypt import aes_encrypt
from .metrics import compute_lsb_ber, compute_sample_change_stats, compute_snr_db, compute_ber
from .visualize import (
    plot_bit_difference_heatmap,
    plot_snr_and_noise,
    plot_spectrogram_comparison,
    plot_waveform_comparison,
)


FRAME_SIZE = 1024
HOP_SIZE = 512


def _derive_aes_key_bytes(passphrase: str, key_len: int = 16) -> bytes:
    h = hashlib.sha256(passphrase.encode("utf-8")).digest()
    return h[:key_len]


def _bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8)).astype(np.uint8)


def _new_fig_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    figs_dir = Path("figures") / f"run_{stamp}"
    figs_dir.mkdir(parents=True, exist_ok=True)
    return figs_dir


def main() -> int:
    cover = Path("data") / "original" / "sample.wav"
    if not cover.exists():
        print("Cover file not found:", cover)
        return 2

    out_dir = _new_fig_dir()

    # Low-energy level = 0th percentile (no energy thresholding)
    energy_percentile = 0.0

    # Thesis-friendly example message
    secret_message = (
        "LOW-ENERGY TEST: This message is embedded using keyed adaptive LSB (energy_percentile=0) "
        "with AES encryption enabled."
    )
    passphrase = "thesis-demo-key"

    cover_path = str(cover)
    stego_path = str(Path("data") / "stego" / "stego_low_energy.wav")

    key_bytes = _derive_aes_key_bytes(passphrase, 16)
    plaintext = secret_message.encode("utf-8")

    # Predict payload length exactly (AES-CBC stores IV || ciphertext)
    ciphertext = aes_encrypt(plaintext, key_bytes)
    bits_used_total = 64 + len(ciphertext) * 8

    print("=" * 60)
    print("Low Energy Level Simulation (energy_percentile = 0.0)")
    print("=" * 60)
    print(f"Cover WAV: {cover_path}")
    print(f"Output stego WAV: {stego_path}")
    print(f"Figures directory: {out_dir}")
    print("\n[Embedding Inputs]")
    print(f"Secret message (UTF-8): {secret_message}")
    print(f"Secret message length: {len(plaintext)} bytes")
    print("Encryption: ENABLED (AES-CBC + PKCS#7)")
    print("Key-based random embedding: ENABLED (SHA-256 seeded ordering)")
    print(f"Energy-adaptive embedding: ENABLED (energy_percentile={energy_percentile})")

    embed_adaptive_keyed(
        cover_wav_path=cover_path,
        plaintext=plaintext,
        out_wav_path=stego_path,
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=energy_percentile,
        encrypt=True,
        robust_repeat=1,
        robust_interleave=True,
    )

    stats = compute_sample_change_stats(cover_path, stego_path)
    snr_db = compute_snr_db(cover_path, stego_path)
    ber_lsb = compute_lsb_ber(cover_path, stego_path)

    print("\n[Payload Accounting]")
    print(f"Ciphertext length (IV + CT): {len(ciphertext)} bytes")
    print(f"Header length: 8 bytes (ASTG + payload length)")
    print(f"Bits used (header + ciphertext): {bits_used_total}")
    print(f"Estimated flips (~50% of used bits): {bits_used_total/2:.0f}")
    print(
        f"Actual flips (LSB changed): {stats['lsb_changed']} / {stats['samples_total']} "
        f"({stats['fraction_changed']*100:.4f}%)"
    )

    recovered = extract_adaptive_keyed(
        stego_wav_path=stego_path,
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=energy_percentile,
        decrypt=True,
        robust_repeat=1,
        robust_interleave=True,
    )

    ok = recovered == plaintext
    payload_ber = None
    if recovered is not None:
        a = _bytes_to_bits(plaintext)
        b = _bytes_to_bits(recovered)
        n = min(a.size, b.size)
        payload_ber = compute_ber(a[:n], b[:n]) if n > 0 else 0.0

    print("\n[Performance Metrics]")
    print(f"SNR (cover vs stego): {snr_db:.2f} dB")
    print(f"LSB BER (cover vs stego): {ber_lsb:.6f}")
    if payload_ber is None:
        print("Payload BER: unavailable (extraction failed)")
    else:
        print(f"Payload BER (recovered vs original): {payload_ber:.6f}")

    print("\n[Extraction Result]")
    print("Extraction OK:", ok)
    if recovered is None:
        print("Recovered message: <None>")
    else:
        try:
            print("Recovered message (UTF-8):", recovered.decode("utf-8"))
        except Exception:
            print("Recovered message (bytes):", recovered)

    # Figures
    plot_waveform_comparison(
        cover_path,
        stego_path,
        num_samples=5000,
        save_path=str(out_dir / "low_energy_waveform.png"),
        report_stats=False,
    )
    plot_snr_and_noise(
        cover_path,
        stego_path,
        save_path=str(out_dir / "low_energy_snr_noise.png"),
        report_stats=False,
    )
    plot_spectrogram_comparison(
        cover_path,
        stego_path,
        save_path=str(out_dir / "low_energy_spectrogram.png"),
        show_difference=True,
        report_stats=False,
    )
    plot_bit_difference_heatmap(
        cover_path,
        stego_path,
        save_path=str(out_dir / "low_energy_lsb_heatmap.png"),
        report_stats=False,
    )

    print("\n[Saved Figures]")
    print("-", out_dir / "low_energy_waveform.png")
    print("-", out_dir / "low_energy_snr_noise.png")
    print("-", out_dir / "low_energy_spectrogram.png")
    print("-", out_dir / "low_energy_lsb_heatmap.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
