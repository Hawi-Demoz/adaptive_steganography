"""Parameter sweep experiments for the thesis simulation section.

Runs a small grid over:
- energy_percentile (content adaptivity strength)
- secret message length

Outputs:
- figures/run_YYYYMMDD_HHMMSS/sweep_results.csv
- figures/run_YYYYMMDD_HHMMSS/sweep_results.md
- waveform/noise plots per case

This is intentionally non-interactive for repeatable documentation.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from .embed import embed_adaptive_keyed
from .extract import extract_adaptive_keyed
from .metrics import compute_ber, compute_sample_change_stats
from .visualize import plot_snr_and_noise, plot_waveform_comparison


FRAME_SIZE = 1024
HOP_SIZE = 512


@dataclass(frozen=True)
class SweepCase:
    energy_percentile: float
    message_len_bytes: int


@dataclass
class SweepResult:
    energy_percentile: float
    message_len_bytes: int
    encrypt: bool
    bits_used_total: int
    samples_total: int
    samples_changed: int
    fraction_changed: float
    snr_db: float
    max_abs_diff_lsb: int
    extraction_ok: bool
    payload_bit_ber: float | None
    # Localization metric: fraction of modified samples that fall in top-energy frames.
    frac_mod_in_top_energy_frames: float


def _new_fig_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    figs_dir = Path("figures") / f"run_{stamp}"
    figs_dir.mkdir(parents=True, exist_ok=True)
    return figs_dir


def _read_wav_mono_int16(path: str) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype="int16")
    if data.ndim == 2:
        data = data[:, 0]
    return data.astype(np.int16), int(sr)


def _bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8)).astype(np.uint8)


def _rms_per_frame(x: np.ndarray, frame_size: int, hop_size: int) -> np.ndarray:
    n = x.shape[0]
    rms = []
    for start in range(0, n, hop_size):
        end = min(start + frame_size, n)
        if start >= end:
            break
        frame = x[start:end].astype(np.float32)
        rms.append(float(np.sqrt(np.mean(frame * frame))) if frame.size else 0.0)
    return np.asarray(rms, dtype=np.float32)


def _frac_modifications_in_top_energy_frames(
    cover: np.ndarray,
    modified_mask: np.ndarray,
    sr: int,
    frame_size: int,
    hop_size: int,
    top_energy_percent: float = 20.0,
) -> float:
    """How localized the embedding is to high-energy frames.

    We compute frame RMS on LSB-cleared cover and measure what fraction of modified
    samples fall into the highest-energy frames.

    This captures the *distribution* effect of `energy_percentile`, not just the
    global noise power (which mostly depends on payload length).
    """

    if cover.size == 0 or modified_mask.size == 0:
        return 0.0

    cover_energy = (cover.astype(np.int32) & ~1).astype(np.int16)
    rms = _rms_per_frame(cover_energy.astype(np.float32), frame_size, hop_size)
    if rms.size == 0:
        return 0.0

    thr = np.percentile(rms, 100.0 - top_energy_percent)

    # Map samples -> frame index (floor division by hop). This matches the frame walk.
    sample_frame = (np.arange(cover.size) // hop_size).astype(np.int64)
    sample_frame = np.clip(sample_frame, 0, rms.size - 1)

    mod_idx = np.where(modified_mask)[0]
    if mod_idx.size == 0:
        return 0.0

    mod_frames = sample_frame[mod_idx]
    mod_rms = rms[mod_frames]
    return float(np.mean(mod_rms >= thr))


def _payload_ber(original: bytes, extracted: bytes | None) -> float | None:
    if extracted is None:
        return None
    a = _bytes_to_bits(original)
    b = _bytes_to_bits(extracted)
    n = min(a.size, b.size)
    if n == 0:
        return 0.0
    return compute_ber(a[:n], b[:n])


def run_case(
    cover_wav: str,
    out_dir: Path,
    key_bytes: bytes,
    case: SweepCase,
    encrypt: bool,
    rng: np.random.Generator,
) -> SweepResult:
    msg = rng.integers(0, 256, size=case.message_len_bytes, dtype=np.uint8).tobytes()

    stego_path = out_dir / f"stego_e{int(case.energy_percentile)}_len{case.message_len_bytes}_enc{int(encrypt)}.wav"

    embed_adaptive_keyed(
        cover_wav_path=cover_wav,
        plaintext=msg,
        out_wav_path=str(stego_path),
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=case.energy_percentile,
        encrypt=encrypt,
    )

    stats = compute_sample_change_stats(cover_wav, str(stego_path))

    # Compare arrays to build a modification mask (where LSB flipped)
    cover, sr = _read_wav_mono_int16(cover_wav)
    stego, _ = _read_wav_mono_int16(str(stego_path))
    n = min(cover.size, stego.size)
    cover = cover[:n]
    stego = stego[:n]
    modified_mask = (((cover ^ stego) & 1) != 0)

    frac_in_top = _frac_modifications_in_top_energy_frames(
        cover=cover,
        modified_mask=modified_mask,
        sr=sr,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        top_energy_percent=20.0,
    )

    extracted = extract_adaptive_keyed(
        stego_wav_path=str(stego_path),
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=case.energy_percentile,
        decrypt=encrypt,
    )
    extraction_ok = extracted == msg
    ber_payload = _payload_ber(msg, extracted)

    # Header is fixed 64 bits; payload size depends on encrypt
    payload_len = len(msg) if not encrypt else None  # not used for bits_used
    # For bits used, recompute with the same AES that embed uses.
    # We avoid importing aes_encrypt here to keep logic centralized in embed.
    # Empirically: ciphertext length = 16 (IV) + padded_len.
    if encrypt:
        # AES-CBC w/ PKCS#7 padding: padded to 16-byte blocks
        padded = ((len(msg) // 16) + 1) * 16
        payload_len_bytes = 16 + padded
    else:
        payload_len_bytes = len(msg)

    bits_used_total = 64 + payload_len_bytes * 8

    # Plots per case
    plot_waveform_comparison(
        cover_wav,
        str(stego_path),
        num_samples=5000,
        save_path=str(out_dir / f"waveform_e{int(case.energy_percentile)}_len{case.message_len_bytes}_enc{int(encrypt)}.png"),
        report_stats=False,
    )
    plot_snr_and_noise(
        cover_wav,
        str(stego_path),
        save_path=str(out_dir / f"snr_noise_e{int(case.energy_percentile)}_len{case.message_len_bytes}_enc{int(encrypt)}.png"),
        report_stats=False,
    )

    return SweepResult(
        energy_percentile=case.energy_percentile,
        message_len_bytes=case.message_len_bytes,
        encrypt=encrypt,
        bits_used_total=bits_used_total,
        samples_total=int(stats["samples_total"]),
        samples_changed=int(stats["samples_changed"]),
        fraction_changed=float(stats["fraction_changed"]),
        snr_db=float(stats["snr_db"]),
        max_abs_diff_lsb=int(stats["max_abs_diff"]),
        extraction_ok=bool(extraction_ok),
        payload_bit_ber=ber_payload,
        frac_mod_in_top_energy_frames=float(frac_in_top),
    )


def _write_csv(path: Path, rows: list[SweepResult]) -> None:
    if not rows:
        return
    fieldnames = list(asdict(rows[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def _write_markdown_table(path: Path, rows: list[SweepResult]) -> None:
    if not rows:
        return

    headers = [
        "energy_percentile",
        "message_len_bytes",
        "encrypt",
        "bits_used_total",
        "fraction_changed",
        "snr_db",
        "frac_mod_in_top_energy_frames",
        "extraction_ok",
        "payload_bit_ber",
    ]

    def fmt(v, k: str) -> str:
        if isinstance(v, float):
            if k in {"fraction_changed", "frac_mod_in_top_energy_frames"}:
                return f"{v*100:.3f}%"
            if k == "snr_db":
                return f"{v:.2f}"
            return f"{v:.6f}"
        return str(v)

    with path.open("w", encoding="utf-8") as f:
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
        for r in rows:
            d = asdict(r)
            f.write("| " + " | ".join(fmt(d[h], h) for h in headers) + " |\n")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    cover = root / "data" / "original" / "sample.wav"
    if not cover.exists():
        print("Cover file not found:", cover)
        return 2

    out_dir = _new_fig_dir()

    # Deterministic key and message bytes for repeatability
    key_str = "thesis-sweep-key"
    key_bytes = hashlib.sha256(key_str.encode("utf-8")).digest()[:16]

    rng = np.random.default_rng(20260126)

    cases = [
        SweepCase(energy_percentile=0.0, message_len_bytes=16),
        SweepCase(energy_percentile=0.0, message_len_bytes=256),
        SweepCase(energy_percentile=0.0, message_len_bytes=2048),
        SweepCase(energy_percentile=20.0, message_len_bytes=16),
        SweepCase(energy_percentile=20.0, message_len_bytes=256),
        SweepCase(energy_percentile=20.0, message_len_bytes=2048),
        SweepCase(energy_percentile=40.0, message_len_bytes=16),
        SweepCase(energy_percentile=40.0, message_len_bytes=256),
        SweepCase(energy_percentile=40.0, message_len_bytes=2048),
    ]

    results: list[SweepResult] = []

    # Main sweep: no encryption to isolate length/adaptivity effects
    for case in cases:
        print(f"\n=== Case: energy_percentile={case.energy_percentile}, len={case.message_len_bytes}, encrypt=False ===")
        results.append(run_case(str(cover), out_dir, key_bytes, case, encrypt=False, rng=rng))

    # One encrypted reference case (long payload) to demonstrate ciphertext overhead + randomness
    enc_case = SweepCase(energy_percentile=20.0, message_len_bytes=256)
    print(f"\n=== Case: energy_percentile={enc_case.energy_percentile}, len={enc_case.message_len_bytes}, encrypt=True ===")
    results.append(run_case(str(cover), out_dir, key_bytes, enc_case, encrypt=True, rng=rng))

    _write_csv(out_dir / "sweep_results.csv", results)
    _write_markdown_table(out_dir / "sweep_results.md", results)

    print("\nWrote:")
    print(" -", out_dir / "sweep_results.csv")
    print(" -", out_dir / "sweep_results.md")
    print(" - plots in", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
