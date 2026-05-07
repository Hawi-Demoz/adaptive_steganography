"""Optional ML extension for detectability prediction.

This module is intentionally additive: it does not modify the existing
embedding/extraction implementation. It uses the current embed pipeline to
generate stego files, then learns a regression model that predicts a
normalized detectability score.
"""

from __future__ import annotations

import csv
import hashlib
import pickle
from dataclasses import dataclass
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from .embed import embed_adaptive_keyed


@dataclass(frozen=True)
class EmbeddingStrategy:
    """Embedding configuration used for candidate strategy selection."""

    key_text: str
    energy_percentile: float
    frame_size: int = 1024
    hop_size: int = 512
    encrypt: bool = True


def _derive_key_bytes(key_text: str, key_len: int = 16) -> bytes:
    digest = hashlib.sha256(key_text.encode("utf-8")).digest()
    return digest[:key_len]


def _read_wav_mono_float32(path: str) -> tuple[np.ndarray, int]:
    y, sr = librosa.load(path, sr=None, mono=True)
    return y.astype(np.float32), int(sr)


def extract_audio_features(audio_path: str) -> dict[str, float]:
    """Extract beginner-friendly features from one audio file.

    Features:
    - 13 MFCC means
    - Spectral centroid mean
    - Zero crossing rate mean
    - RMS mean
    """

    y, sr = _read_wav_mono_float32(audio_path)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y)
    rms = librosa.feature.rms(y=y)

    out: dict[str, float] = {}
    for i in range(13):
        out[f"mfcc_{i + 1}_mean"] = float(np.mean(mfcc[i]))
    out["spectral_centroid_mean"] = float(np.mean(centroid))
    out["zcr_mean"] = float(np.mean(zcr))
    out["rms_mean"] = float(np.mean(rms))
    return out


def compute_mse(original_wav: str, stego_wav: str) -> float:
    """Compute MSE between original and stego waveforms."""

    x, _ = _read_wav_mono_float32(original_wav)
    y, _ = _read_wav_mono_float32(stego_wav)
    n = min(x.size, y.size)
    if n == 0:
        return 0.0
    x = x[:n]
    y = y[:n]
    return float(np.mean((x - y) ** 2))


def normalize_scores(scores: list[float] | np.ndarray) -> np.ndarray:
    """Min-max normalize a score vector to [0, 1]."""

    arr = np.asarray(scores, dtype=np.float64)
    if arr.size == 0:
        return arr.astype(np.float32)
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    if mx - mn < 1e-12:
        return np.zeros_like(arr, dtype=np.float32)
    norm = (arr - mn) / (mx - mn)
    return norm.astype(np.float32)


def generate_dataset(
    cover_wav: str,
    output_dir: str,
    payloads: list[bytes],
    energy_percentiles: list[float],
    key_texts: list[str],
    encrypt: bool = True,
    frame_size: int = 1024,
    hop_size: int = 512,
) -> Path:
    """Generate stego variants and write features + detectability score CSV.

    Detectability score is MSE(original, stego), then normalized to [0, 1].
    Variations are created by combining multiple energy levels and key strings.
    Different keys produce different embedding positions; energy controls strength
    of preference for high-energy regions.
    """

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stego_dir = out_dir / "stego_samples"
    stego_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | int | str]] = []
    raw_mse: list[float] = []

    idx = 0
    for payload_idx, payload in enumerate(payloads):
        for energy in energy_percentiles:
            for key_text in key_texts:
                idx += 1
                stego_path = stego_dir / f"sample_{idx:04d}_p{payload_idx}_e{int(energy)}.wav"

                embed_adaptive_keyed(
                    cover_wav_path=cover_wav,
                    plaintext=payload,
                    out_wav_path=str(stego_path),
                    user_key=_derive_key_bytes(key_text, 16),
                    frame_size=frame_size,
                    hop_size=hop_size,
                    energy_percentile=energy,
                    encrypt=encrypt,
                )

                features = extract_audio_features(str(stego_path))
                mse = compute_mse(cover_wav, str(stego_path))

                row: dict[str, float | int | str] = {
                    "sample_id": idx,
                    "stego_path": str(stego_path),
                    "payload_len": len(payload),
                    "energy_percentile": float(energy),
                    "key_text": key_text,
                    "mse": float(mse),
                }
                row.update(features)
                rows.append(row)
                raw_mse.append(mse)

    norm_scores = normalize_scores(raw_mse)
    for i, score in enumerate(norm_scores):
        rows[i]["detectability_score"] = float(score)

    dataset_csv = out_dir / "detectability_dataset.csv"
    if not rows:
        raise ValueError("Dataset generation produced no rows. Check input lists.")

    fieldnames = list(rows[0].keys())
    with dataset_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return dataset_csv


def load_dataset(dataset_csv: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load features and labels from dataset CSV."""

    feature_names: list[str] = []
    x_rows: list[list[float]] = []
    y_vals: list[float] = []

    with Path(dataset_csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not feature_names:
                feature_names = [
                    name
                    for name in row.keys()
                    if name.startswith("mfcc_")
                    or name in {"spectral_centroid_mean", "zcr_mean", "rms_mean"}
                ]

            x_rows.append([float(row[name]) for name in feature_names])
            y_vals.append(float(row["detectability_score"]))

    if not x_rows:
        raise ValueError(f"Dataset is empty: {dataset_csv}")

    return np.asarray(x_rows, dtype=np.float32), np.asarray(y_vals, dtype=np.float32), feature_names


def train_regression_model(
    x: np.ndarray,
    y: np.ndarray,
    model_type: str = "random_forest",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, object]:
    """Train regression model and return evaluation artifacts."""

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=random_state
    )

    if model_type == "linear":
        model = LinearRegression()
    else:
        model = RandomForestRegressor(
            n_estimators=200,
            random_state=random_state,
            n_jobs=-1,
        )

    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)
    mae = float(mean_absolute_error(y_test, y_pred))

    return {
        "model": model,
        "mae": mae,
        "y_test": y_test,
        "y_pred": y_pred,
    }


def save_prediction_visualization(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_path: str,
    title: str = "Predicted vs Actual Detectability (ML)",
) -> Path:
    """Save a compact visual report for regression quality.

    The figure contains:
    - scatter plot (actual vs predicted) with an ideal y=x line
    - residual histogram for quick error distribution inspection
    """

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    y_true_f = np.asarray(y_true, dtype=np.float32)
    y_pred_f = np.asarray(y_pred, dtype=np.float32)
    residual = y_pred_f - y_true_f

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)

    # Left: predicted vs actual scatter with ideal line
    ax0 = axes[0]
    ax0.scatter(y_true_f, y_pred_f, s=36, alpha=0.75, color="#1f77b4", edgecolors="none")
    lo = float(min(np.min(y_true_f), np.min(y_pred_f), 0.0))
    hi = float(max(np.max(y_true_f), np.max(y_pred_f), 1.0))
    ax0.plot([lo, hi], [lo, hi], linestyle="--", linewidth=1.5, color="#d62728", label="Ideal")
    ax0.set_title("Predicted vs Actual")
    ax0.set_xlabel("Actual detectability")
    ax0.set_ylabel("Predicted detectability")
    ax0.grid(alpha=0.25)
    ax0.legend(loc="best")

    # Right: residual distribution
    ax1 = axes[1]
    ax1.hist(residual, bins=20, color="#2ca02c", alpha=0.85)
    ax1.axvline(0.0, linestyle="--", linewidth=1.5, color="#d62728")
    ax1.set_title("Residual Distribution")
    ax1.set_xlabel("Prediction error (pred - actual)")
    ax1.set_ylabel("Count")
    ax1.grid(alpha=0.25)

    fig.suptitle(title)
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def save_model(model: object, feature_names: list[str], output_path: str) -> Path:
    """Save model and feature order with pickle."""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "feature_names": feature_names}
    with out.open("wb") as f:
        pickle.dump(payload, f)
    return out


def load_model(model_path: str) -> tuple[object, list[str]]:
    """Load model and feature order."""

    with Path(model_path).open("rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["feature_names"]


def predict_detectability_from_audio(model_path: str, stego_wav: str) -> float:
    """Predict normalized detectability score [0, 1] for one stego file."""

    model, feature_names = load_model(model_path)
    feat = extract_audio_features(stego_wav)
    x = np.asarray([[float(feat[name]) for name in feature_names]], dtype=np.float32)
    pred = float(model.predict(x)[0])
    return float(np.clip(pred, 0.0, 1.0))


def embed_and_predict_detectability(
    cover_wav: str,
    payload: bytes,
    out_wav: str,
    model_path: str,
    strategy: EmbeddingStrategy,
) -> float:
    """Embed payload with one strategy and return predicted detectability."""

    embed_adaptive_keyed(
        cover_wav_path=cover_wav,
        plaintext=payload,
        out_wav_path=out_wav,
        user_key=_derive_key_bytes(strategy.key_text, 16),
        frame_size=strategy.frame_size,
        hop_size=strategy.hop_size,
        energy_percentile=strategy.energy_percentile,
        encrypt=strategy.encrypt,
    )
    return predict_detectability_from_audio(model_path=model_path, stego_wav=out_wav)


def choose_least_detectable_strategy(
    cover_wav: str,
    payload: bytes,
    model_path: str,
    output_dir: str,
    strategies: list[EmbeddingStrategy],
) -> dict[str, object]:
    """Try candidate strategies and return the one with lowest predicted score."""

    if not strategies:
        raise ValueError("At least one strategy is required.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[dict[str, object]] = []
    for i, strategy in enumerate(strategies, start=1):
        stego_path = out_dir / f"candidate_{i:03d}.wav"
        pred = embed_and_predict_detectability(
            cover_wav=cover_wav,
            payload=payload,
            out_wav=str(stego_path),
            model_path=model_path,
            strategy=strategy,
        )
        candidates.append(
            {
                "strategy": strategy,
                "stego_path": str(stego_path),
                "predicted_detectability": float(pred),
            }
        )

    best = min(candidates, key=lambda item: float(item["predicted_detectability"]))
    return {
        "best": best,
        "all_candidates": candidates,
    }
