"""Thesis-ready low-energy (energy_percentile=0) simulation run.

This script runs one fully reproducible embed/extract cycle and prints
all key values typically reported in the terminal (payload sizes, bits used,
flips, SNR/BER, recovered message). It also saves standard figures.

Run:
  python -m src.thesis_low_energy_case

Optional:
    python -m src.thesis_low_energy_case --energy-percentile 20
    python -m src.thesis_low_energy_case --energy-percentile 40
"""

from __future__ import annotations

import hashlib
import argparse
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
    ap = argparse.ArgumentParser(description="Thesis simulation case runner")
    ap.add_argument("--energy-percentile", type=float, default=0.0, help="Energy adaptivity level (e.g., 0, 20, 40)")
    ap.add_argument(
        "--message",
        type=str,
        default=(
            "LOW-ENERGY TEST: This message is embedded using keyed adaptive LSB (energy_percentile=0) "
            "with AES encryption enabled."
        ),
        help="Secret message to embed (UTF-8)",
    )
    ap.add_argument("--passphrase", type=str, default="thesis-demo-key", help="Passphrase used to derive AES/key bytes")
    ap.add_argument("--robust-repeat", type=int, default=1, help="Robust repetition factor (odd >= 1). 1 disables")
    ap.add_argument("--no-interleave", action="store_true", help="Disable robustness interleaving")
    ap.add_argument("--no-encrypt", action="store_true", help="Disable AES encryption")
    args = ap.parse_args()

    cover = Path("data") / "original" / "sample.wav"
    if not cover.exists():
        print("Cover file not found:", cover)
        return 2

    out_dir = _new_fig_dir()

    energy_percentile = float(args.energy_percentile)
    secret_message = args.message
    passphrase = args.passphrase
    encrypt = not args.no_encrypt
    robust_repeat = int(args.robust_repeat)
    robust_interleave = not args.no_interleave

    cover_path = str(cover)
    ep_label = str(int(energy_percentile)) if energy_percentile.is_integer() else str(energy_percentile).replace(".", "p")
    stego_path = str(Path("data") / "stego" / f"stego_case_e{ep_label}.wav")

    key_bytes = _derive_aes_key_bytes(passphrase, 16)
    plaintext = secret_message.encode("utf-8")

    # Predict payload length exactly (AES-CBC stores IV || ciphertext)
    if encrypt:
        ciphertext = aes_encrypt(plaintext, key_bytes)
        payload_bytes = ciphertext
    else:
        payload_bytes = plaintext
    # Account for robustness layer (if enabled)
    if robust_repeat > 1 or not robust_interleave:
        from .robust_payload import encode_payload

        payload_bytes = encode_payload(payload_bytes, key=key_bytes, repeat=robust_repeat, interleave=robust_interleave)

    bits_used_total = 64 + len(payload_bytes) * 8

    print("=" * 60)
    print(f"Simulation Case (energy_percentile = {energy_percentile})")
    print("=" * 60)
    print(f"Cover WAV: {cover_path}")
    print(f"Output stego WAV: {stego_path}")
    print(f"Figures directory: {out_dir}")
    print("\n[Embedding Inputs]")
    print(f"Secret message (UTF-8): {secret_message}")
    print(f"Secret message length: {len(plaintext)} bytes")
    print("Encryption:", "ENABLED (AES-CBC + PKCS#7)" if encrypt else "DISABLED")
    print("Key-based random embedding: ENABLED (SHA-256 seeded ordering)")
    print(f"Energy-adaptive embedding: ENABLED (energy_percentile={energy_percentile})")
    if robust_repeat > 1:
        print(f"Robustness layer: ENABLED (repeat={robust_repeat}, interleave={robust_interleave})")
    else:
        print("Robustness layer: DISABLED")

    embed_adaptive_keyed(
        cover_wav_path=cover_path,
        plaintext=plaintext,
        out_wav_path=stego_path,
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=energy_percentile,
        encrypt=encrypt,
        robust_repeat=robust_repeat,
        robust_interleave=robust_interleave,
    )

    stats = compute_sample_change_stats(cover_path, stego_path)
    snr_db = compute_snr_db(cover_path, stego_path)
    ber_lsb = compute_lsb_ber(cover_path, stego_path)

    print("\n[Payload Accounting]")
    if encrypt:
        print(f"Ciphertext length (IV + CT): {len(aes_encrypt(plaintext, key_bytes))} bytes")
    else:
        print(f"Plaintext payload length: {len(plaintext)} bytes")
    if robust_repeat > 1 or not robust_interleave:
        print(f"Robust-encoded payload length: {len(payload_bytes)} bytes")
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
        decrypt=encrypt,
        robust_repeat=robust_repeat,
        robust_interleave=robust_interleave,
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
        save_path=str(out_dir / f"case_e{ep_label}_waveform.png"),
        report_stats=False,
    )
    plot_snr_and_noise(
        cover_path,
        stego_path,
        save_path=str(out_dir / f"case_e{ep_label}_snr_noise.png"),
        report_stats=False,
    )
    plot_spectrogram_comparison(
        cover_path,
        stego_path,
        save_path=str(out_dir / f"case_e{ep_label}_spectrogram.png"),
        show_difference=True,
        report_stats=False,
    )
    plot_bit_difference_heatmap(
        cover_path,
        stego_path,
        save_path=str(out_dir / f"case_e{ep_label}_lsb_heatmap.png"),
        report_stats=False,
    )

    print("\n[Saved Figures]")
    print("-", out_dir / f"case_e{ep_label}_waveform.png")
    print("-", out_dir / f"case_e{ep_label}_snr_noise.png")
    print("-", out_dir / f"case_e{ep_label}_spectrogram.png")
    print("-", out_dir / f"case_e{ep_label}_lsb_heatmap.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
