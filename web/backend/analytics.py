"""Analytics helpers for visualization dashboard API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np

from src.metrics import compute_lsb_ber, compute_sample_change_stats, compute_snr_db
from src.visualize import _compute_rms_per_frame
import soundfile as sf


def _compute_mse(cover_path: str, stego_path: str) -> float:
    x, _ = sf.read(cover_path, dtype="float32")
    y, _ = sf.read(stego_path, dtype="float32")
    if x.ndim == 2:
        x = x[:, 0]
    if y.ndim == 2:
        y = y[:, 0]
    n = min(x.size, y.size)
    if n == 0:
        return 0.0
    diff = x[:n].astype(np.float64) - y[:n].astype(np.float64)
    return float(np.mean(diff * diff))


def resolve_audio_path(filename: str, upload_folder: str, stego_folder: str) -> Optional[str]:
    if not filename:
        return None
    safe = os.path.basename(filename)
    for folder in (upload_folder, stego_folder):
        path = os.path.join(folder, safe)
        if os.path.exists(path):
            return path
    return None


def resolve_session_pair(
    cover_name: str,
    stego_name: str,
    upload_folder: str,
    stego_folder: str,
    registry: list[dict],
) -> tuple[Optional[str], Optional[str], Optional[dict]]:
    """Resolve cover/stego paths; enrich from session registry when possible."""
    session = next((e for e in registry if e.get("stego_filename") == stego_name), None)
    if session and not cover_name:
        cover_name = session.get("cover_filename") or session.get("original_name") or ""

    cover_path = resolve_audio_path(cover_name, upload_folder, stego_folder)
    stego_path = resolve_audio_path(stego_name, stego_folder, upload_folder)

    # Legacy registry stored original cover names — pick nearest cover upload by mtime
    if stego_path and not cover_path and cover_name and not cover_name.startswith("cover_"):
        stego_mtime = os.path.getmtime(stego_path)
        candidates = []
        for name in os.listdir(upload_folder):
            if name.startswith("cover_") and name.lower().endswith(".wav"):
                p = os.path.join(upload_folder, name)
                candidates.append((abs(os.path.getmtime(p) - stego_mtime), p))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            cover_path = candidates[0][1]

    return cover_path, stego_path, session


def _energy_localization(cover_path: str, stego_path: str, energy_percentile: float) -> float:
    x, _ = sf.read(cover_path, dtype="int16")
    y, _ = sf.read(stego_path, dtype="int16")
    if x.ndim == 2:
        x = x[:, 0]
    if y.ndim == 2:
        y = y[:, 0]
    n = min(x.shape[0], y.shape[0])
    if n == 0:
        return 0.0

    x = x[:n].astype(np.int16)
    y = y[:n].astype(np.int16)
    lsb_changed = ((x ^ y) & 1) != 0
    if not np.any(lsb_changed):
        return 0.0

    data_energy = (x.astype(np.int32) & ~1).astype(np.int16)
    rms, edges = _compute_rms_per_frame(data_energy, 1024, 512)
    if not rms.size:
        return 0.0

    scores = rms.astype(np.float64)
    if scores.max() - scores.min() > 1e-12:
        scores = (scores - scores.min()) / (scores.max() - scores.min())

    thr = float(np.percentile(scores, energy_percentile)) if energy_percentile > 0 else 0.0
    high_mask = np.zeros(n, dtype=bool)
    for score, (s, e) in zip(scores, edges):
        if energy_percentile <= 0 or score >= thr:
            high_mask[s:e] = True

    localized = int(np.sum(lsb_changed & high_mask))
    return float(localized) / float(int(np.sum(lsb_changed)))


def _detectability_from_mse(mse: float) -> tuple[float, str]:
    score = float(np.clip(np.log10(mse + 1e-16) + 16.0, 0.0, 1.0))
    if score < 0.33:
        risk = "LOW"
    elif score < 0.66:
        risk = "MEDIUM"
    else:
        risk = "HIGH"
    return score, risk


def build_analytics_summary(
    cover_path: str,
    stego_path: str,
    session: Optional[dict] = None,
) -> dict:
    stats = compute_sample_change_stats(cover_path, stego_path)
    snr_db = compute_snr_db(cover_path, stego_path)
    lsb_ber = compute_lsb_ber(cover_path, stego_path)
    mse = _compute_mse(cover_path, stego_path)
    detectability_score, detectability_risk = _detectability_from_mse(mse)

    energy_percentile = float(session.get("energy_percentile", 0.0)) if session else 0.0
    encrypt = bool(session.get("encrypt", False)) if session else False
    robust_repeat = int(session.get("robust_repeat", 1)) if session else 1

    samples_total = stats["samples_total"]
    lsb_changed = stats["lsb_changed"]
    capacity_usage = float(lsb_changed) / float(samples_total) if samples_total else 0.0
    energy_localization = _energy_localization(cover_path, stego_path, energy_percentile)

    stego_info = sf.info(stego_path)
    duration_sec = float(stego_info.frames) / float(stego_info.samplerate) if stego_info.samplerate else 0.0

    payload_bits_estimate = int(lsb_changed)
    payload_bytes_estimate = payload_bits_estimate // 8

    try:
        from src.detectability_ml import extract_audio_features
        audio_features = extract_audio_features(stego_path)
    except Exception:
        audio_features = None

    return {
        "stego_filename": os.path.basename(stego_path),
        "cover_filename": os.path.basename(cover_path),
        "original_name": session.get("original_name") if session else os.path.basename(cover_path),
        "snr_db": float(snr_db),
        "lsb_ber": float(lsb_ber),
        "payload_ber": session.get("payload_ber") if session and session.get("payload_ber") is not None else None,
        "mse": float(mse),
        "detectability_score": detectability_score,
        "detectability_risk": detectability_risk,
        "detectability_source": "mse_proxy",
        "capacity_usage": capacity_usage,
        "energy_localization": energy_localization,
        "embedding_bits": payload_bits_estimate,
        "payload_bytes_estimate": payload_bytes_estimate,
        "samples_total": samples_total,
        "lsb_changed": lsb_changed,
        "fraction_changed": stats["fraction_changed"],
        "max_abs_diff": stats["max_abs_diff"],
        "duration_sec": duration_sec,
        "encrypt": encrypt,
        "energy_percentile": energy_percentile,
        "robust_repeat": robust_repeat,
        "security_status": "ENCRYPTED" if encrypt else "PLAINTEXT",
        "audio_features": audio_features,
    }
