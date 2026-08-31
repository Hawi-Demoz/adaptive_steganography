"""Dashboard-grade matplotlib visualizations for the web analytics UI.

All plots use real cover/stego audio data and existing processing utilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
from scipy.signal import spectrogram

from .metrics import compute_sample_change_stats, compute_snr_db, compute_lsb_ber
from .visualize import _compute_rms_per_frame, _ensure_dir, _read_wav_mono_int16

# Custom cyber-themed colormaps matching the web UI
cmap_cyber = LinearSegmentedColormap.from_list(
    "cyber_spectrogram", ["#151515", "#083344", "#06B6D4", "#E2F1FF"]
)
cmap_cyber_diff = LinearSegmentedColormap.from_list(
    "cyber_difference", ["#151515", "#581C87", "#BD53ED", "#F3E8FF"]
)


def _style_figure(fig, title: str, subtitle: str = ""):
    fig.patch.set_facecolor("#0A0A0A")
    full = title if not subtitle else f"{title}\n{subtitle}"
    fig.suptitle(full, color="#A8B8D0", fontsize=13, fontweight="semibold")
    for ax in fig.get_axes():
        ax.set_facecolor("#151515")
        ax.tick_params(colors="#888888", labelsize=8, pad=4)
        for spine in ax.spines.values():
            spine.set_color("#262626")
            spine.set_linewidth(1.0)
        ax.title.set_color("#F0F0F0")
        ax.xaxis.label.set_color("#888888")
        ax.yaxis.label.set_color("#888888")
        # Ensure proper padding to avoid clipping
        ax.xaxis.labelpad = 6
        ax.yaxis.labelpad = 6


def plot_dashboard_waveform(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    num_samples: int = 8000,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(num_samples, x.size, y.size)
    idx = np.arange(n)
    xf = x[:n].astype(np.float32) / 32768.0
    yf = y[:n].astype(np.float32) / 32768.0
    diff = x[:n] != y[:n]
    lsb_changed = ((x[:n] ^ y[:n]) & 1) != 0

    fig = plt.figure(figsize=(14, 8), constrained_layout=True)
    gs = GridSpec(2, 2, figure=fig, height_ratios=[1.1, 1.0], width_ratios=[1.2, 1.0])

    # Subplot 1: Waveform Overlay
    ax_main = fig.add_subplot(gs[0, 0])
    ax_main.plot(idx, xf, color="#888888", lw=0.9, alpha=0.85, label="Cover")
    ax_main.plot(idx, yf, color="#06B6D4", lw=0.8, alpha=0.75, label="Stego")
    if np.any(diff):
        ax_main.scatter(idx[diff], yf[diff], s=6, c="#BD53ED", alpha=0.55, label="Modified")
    ax_main.set_title("Waveform Overlay")
    ax_main.set_ylabel("Amplitude")
    ax_main.legend(loc="upper left", fontsize=8, facecolor="#151515", edgecolor="#262626")

    # Subplot 2: Zoom Hotspot
    ax_inset = fig.add_subplot(gs[0, 1])
    if np.any(lsb_changed):
        win = 400
        kernel = np.ones(win, dtype=np.float32)
        density = np.convolve(lsb_changed.astype(np.float32), kernel, mode="same")
        center = int(np.argmax(density))
        s = max(0, center - win // 2)
        e = min(n, s + win)
        sl = slice(s, e)
        ax_inset.plot(idx[sl], xf[sl], color="#888888", lw=1.1, label="Cover")
        ax_inset.plot(idx[sl], yf[sl], color="#06B6D4", lw=1.0, alpha=0.85, label="Stego")
        if np.any(lsb_changed[sl]):
            ax_inset.scatter(idx[sl][lsb_changed[sl]], yf[sl][lsb_changed[sl]], s=12, c="#BD53ED", label="Flip")
    ax_inset.set_title("Zoom: LSB Hotspot")
    ax_inset.set_ylabel("Amplitude")
    ax_inset.set_xlabel("Sample index")

    # Subplot 3: Sample Difference (LSB)
    ax_diff = fig.add_subplot(gs[1, 0])
    diff_lsb = (yf - xf) * 32768.0
    ax_diff.fill_between(idx, diff_lsb, 0, where=lsb_changed, color="#BD53ED", alpha=0.2)
    ax_diff.plot(idx, diff_lsb, color="#06B6D4", lw=0.7)
    ax_diff.set_ylim(-1.5, 1.5)
    ax_diff.set_title("Sample Difference (LSB units)")
    ax_diff.set_ylabel("Δ LSB")
    ax_diff.set_xlabel("Sample index")

    # Subplot 4: Difference Histogram
    ax_hist = fig.add_subplot(gs[1, 1])
    ax_hist.hist(diff_lsb, bins=[-1.5, -0.5, 0.5, 1.5], color="#BD53ED", edgecolor="#262626", rwidth=0.7)
    ax_hist.set_title("Difference Histogram")
    ax_hist.set_xlabel("LSB delta")
    ax_hist.set_ylabel("Count")

    stats = compute_sample_change_stats(original_wav, stego_wav)
    _style_figure(
        fig,
        "Waveform Forensic Analysis",
        f"SNR {stats['snr_db']:.2f} dB | LSB changes {stats['lsb_changed']:,}",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_spectrogram(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    nperseg: int = 1024,
    noverlap: int = 768,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    x = x.astype(np.float32)
    y = y.astype(np.float32)
    peak = max(np.max(np.abs(x)), np.max(np.abs(y)), 1e-12)
    x /= peak
    y /= peak
    noise = y - x

    f1, t1, Sx = spectrogram(x, fs=sr, nperseg=nperseg, noverlap=noverlap)
    f2, t2, Sy = spectrogram(y, fs=sr, nperseg=nperseg, noverlap=noverlap)
    f3, t3, Sn = spectrogram(noise, fs=sr, nperseg=nperseg, noverlap=noverlap)

    Sx_db = 10 * np.log10(Sx + 1e-12); del Sx
    Sy_db = 10 * np.log10(Sy + 1e-12); del Sy
    Sn_db = 10 * np.log10(Sn + 1e-12); del Sn
    vmin = min(Sx_db.min(), Sy_db.min())
    vmax = max(Sx_db.max(), Sy_db.max())

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    titles = ["Cover Spectrogram", "Stego Spectrogram", "Difference Layer (Stego − Cover)"]
    data = [Sx_db, Sy_db, Sn_db]
    cmaps = [cmap_cyber, cmap_cyber, cmap_cyber_diff]
    vmins = [vmin, vmin, -90]
    vmaxs = [vmax, vmax, 0]

    for ax, arr, title, cmap, lo, hi in zip(axes, data, titles, cmaps, vmins, vmaxs):
        im = ax.pcolormesh(t2 if title != titles[0] else t1, f1, arr, shading="gouraud", cmap=cmap, vmin=lo, vmax=hi)
        ax.set_title(title)
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Frequency [Hz]")
        cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.03)
        cb.ax.tick_params(labelsize=7, colors="#888888")
        cb.set_label("dB", color="#888888", fontsize=8, labelpad=4)
        cb.outline.set_edgecolor("#262626")

    _style_figure(
        fig,
        "Spectrogram Comparison",
        f"Cover: {Path(original_wav).name} | Stego: {Path(stego_wav).name}",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_heatmap(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    block: int = 1024,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(x.size, y.size)
    lsb_changed = (((x[:n] & 1) != (y[:n] & 1)).astype(np.uint8))

    m = (n // block) * block
    mat = lsb_changed[:m].reshape(-1, block) if m > 0 else lsb_changed.reshape(1, -1)
    time_axis = np.arange(mat.shape[0]) * (block / float(sr))

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), constrained_layout=True, height_ratios=[3, 1])
    im = axes[0].imshow(mat, aspect="auto", cmap=cmap_cyber_diff, interpolation="nearest", vmin=0, vmax=1)
    axes[0].set_title("LSB Modification Heatmap")
    axes[0].set_ylabel("Time block")
    axes[0].set_xlabel("Sample within block")
    cb = fig.colorbar(im, ax=axes[0], shrink=0.8, pad=0.03)
    cb.ax.tick_params(labelsize=7, colors="#888888")
    cb.set_label("LSB flip", color="#888888", fontsize=8, labelpad=4)
    cb.outline.set_edgecolor("#262626")

    row_density = mat.mean(axis=1)
    axes[1].fill_between(time_axis, row_density, color="#BD53ED", alpha=0.25)
    axes[1].plot(time_axis, row_density, color="#06B6D4", lw=1.2)
    axes[1].set_title("Temporal LSB Modification Density")
    axes[1].set_xlabel("Time [s]")
    axes[1].set_ylabel("Flip rate")
    axes[1].set_ylim(0, max(0.05, row_density.max() * 1.15))

    stats = compute_sample_change_stats(original_wav, stego_wav)
    _style_figure(
        fig,
        "LSB Modification Heatmap",
        f"{stats['lsb_changed']:,} LSB flips | {stats['fraction_changed'] * 100:.4f}% samples touched",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_energy_profile(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    energy_percentile: float = 0.0,
    frame_size: int = 1024,
    hop_size: int = 512,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(x.size, y.size)

    data_energy = (x[:n].astype(np.int32) & ~1).astype(np.int16)
    rms, edges = _compute_rms_per_frame(data_energy, frame_size, hop_size)
    scores = rms.copy()
    if scores.size and scores.max() - scores.min() > 1e-12:
        scores = (scores - scores.min()) / (scores.max() - scores.min())

    thr = float(np.percentile(scores, energy_percentile)) if energy_percentile > 0 and scores.size else 0.0
    preferred = scores >= thr if energy_percentile > 0 else np.ones_like(scores, dtype=bool)

    lsb_changed = ((x[:n] ^ y[:n]) & 1) != 0
    frame_lsb = np.zeros(len(edges), dtype=np.float32)
    for i, (s, e) in enumerate(edges):
        frame_lsb[i] = float(lsb_changed[s:e].mean()) if e > s else 0.0

    t = np.arange(len(rms)) * (hop_size / float(sr))

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True, constrained_layout=True)

    axes[0].plot(t, rms, color="#A8B8D0", lw=1.2, label="RMS / frame")
    if energy_percentile > 0:
        axes[0].axhline(float(np.percentile(rms, energy_percentile)), color="#BD53ED", ls="--", lw=1.2,
                        label=f"{energy_percentile:.0f}th percentile threshold")
    axes[0].fill_between(t, 0, rms.max() * 1.05, where=preferred, color="#06B6D4", alpha=0.12, label="Preferred embed region")
    axes[0].set_title("RMS Energy Profile")
    axes[0].set_ylabel("RMS")
    axes[0].legend(fontsize=8, facecolor="#151515", edgecolor="#262626")

    axes[1].bar(t, np.maximum(0.15, preferred.astype(float)), width=(hop_size / float(sr)) * 0.9,
                color=np.where(preferred, "#06B6D4", "#262626"), align="edge")
    axes[1].set_title("Energy-Adaptive Embedding Preference Map")
    axes[1].set_ylabel("Priority")
    axes[1].set_yticks([0, 1])
    axes[1].set_yticklabels(["Deprioritized", "Preferred"])

    axes[2].plot(t, frame_lsb, color="#BD53ED", lw=1.1)
    axes[2].fill_between(t, frame_lsb, color="#BD53ED", alpha=0.2)
    axes[2].set_title("Observed LSB Modification Density per Frame")
    axes[2].set_xlabel("Time [s]")
    axes[2].set_ylabel("Flip rate")

    _style_figure(
        fig,
        "Energy Profile Analysis",
        f"Capacity: {100 - energy_percentile:.0f}% | Cover: {Path(original_wav).name}",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_snr(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    num_samples: int = 12000,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(num_samples, x.size, y.size)
    xf = x[:n].astype(np.float32) / 32768.0
    yf = y[:n].astype(np.float32) / 32768.0
    noise = yf - xf
    snr_db = compute_snr_db(original_wav, stego_wav)

    fig = plt.figure(figsize=(14, 7), constrained_layout=True)
    gs = GridSpec(2, 2, figure=fig, height_ratios=[1.2, 1])

    ax_gauge = fig.add_subplot(gs[0, 0])
    ax_gauge.axis("off")
    ax_gauge.set_box_aspect(0.6)
    quality = "Excellent" if snr_db >= 60 else "Strong" if snr_db >= 40 else "Moderate" if snr_db >= 20 else "Low"
    color = "#06B6D4" if snr_db >= 60 else "#A8B8D0" if snr_db >= 40 else "#BD53ED" if snr_db >= 20 else "#F43F5E"
    box = FancyBboxPatch((0.08, 0.15), 0.84, 0.7, boxstyle="round,pad=0.03", linewidth=1.5,
                         edgecolor=color, facecolor="#151515")
    ax_gauge.add_patch(box)
    ax_gauge.text(0.5, 0.62, f"{snr_db:.2f} dB", ha="center", va="center", fontsize=28, color=color, fontweight="bold")
    ax_gauge.text(0.5, 0.35, f"Imperceptibility: {quality}", ha="center", va="center", fontsize=11, color="#888888")
    ax_gauge.set_xlim(0, 1)
    ax_gauge.set_ylim(0, 1)

    ax_sig = fig.add_subplot(gs[0, 1])
    idx = np.arange(min(3000, n))
    ax_sig.plot(idx, xf[: idx.size], color="#888888", lw=0.8, label="Cover signal")
    ax_sig.set_title("Cover Signal (normalized)")
    ax_sig.legend(fontsize=8, facecolor="#151515", edgecolor="#262626")

    ax_noise_hist = fig.add_subplot(gs[1, 0])
    ax_noise_hist.hist(noise, bins=60, color="#BD53ED", edgecolor="#262626", alpha=0.85)
    ax_noise_hist.set_title("Steganographic Noise Distribution")
    ax_noise_hist.set_xlabel("Amplitude residual")

    ax_noise_time = fig.add_subplot(gs[1, 1])
    ax_noise_time.plot(noise, color="#BD53ED", lw=0.6)
    ax_noise_time.set_title("Distortion Residual (time domain)")
    ax_noise_time.set_xlabel("Sample")

    stats = compute_sample_change_stats(original_wav, stego_wav)
    _style_figure(
        fig,
        "SNR & Distortion Analysis",
        f"Max |Δ| = {stats['max_abs_diff']} LSB | BER = {stats['ber_lsb']:.6f}",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_embedding_density(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    energy_percentile: float = 0.0,
    frame_size: int = 1024,
    hop_size: int = 512,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(x.size, y.size)
    lsb_changed = ((x[:n] ^ y[:n]) & 1) != 0

    data_energy = (x[:n].astype(np.int32) & ~1).astype(np.int16)
    rms, edges = _compute_rms_per_frame(data_energy, frame_size, hop_size)
    scores = rms.copy()
    if scores.size and scores.max() - scores.min() > 1e-12:
        scores = (scores - scores.min()) / (scores.max() - scores.min())
    thr = float(np.percentile(scores, energy_percentile)) if energy_percentile > 0 and scores.size else 0.0
    high_energy = scores >= thr

    frame_density = np.zeros(len(edges), dtype=np.float32)
    frame_high_share = np.zeros(len(edges), dtype=np.float32)
    for i, (s, e) in enumerate(edges):
        seg = lsb_changed[s:e]
        frame_density[i] = float(seg.mean()) if seg.size else 0.0
        if energy_percentile > 0:
            frame_high_share[i] = float(seg.mean()) if high_energy[i] else 0.0

    t = np.arange(len(edges)) * (hop_size / float(sr))
    positions = np.where(lsb_changed)[0]

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)

    axes[0, 0].scatter(positions / float(sr), np.ones_like(positions), s=1, c="#06B6D4", alpha=0.35)
    axes[0, 0].set_title("Payload Sample Positions (time axis)")
    axes[0, 0].set_xlabel("Time [s]")
    axes[0, 0].set_yticks([])

    axes[0, 1].plot(t, frame_density, color="#06B6D4", lw=1.2)
    axes[0, 1].fill_between(t, frame_density, color="#BD53ED", alpha=0.2)
    axes[0, 1].set_title("Embedding Density per Frame")
    axes[0, 1].set_xlabel("Time [s]")

    if energy_percentile > 0:
        axes[1, 0].bar(t, frame_high_share, width=(hop_size / float(sr)) * 0.85, color="#06B6D4", alpha=0.85)
        axes[1, 0].set_title("Concentration in High-Energy Frames")
    else:
        axes[1, 0].hist(positions / float(sr), bins=80, color="#BD53ED", edgecolor="#262626")
        axes[1, 0].set_title("Temporal Clustering of LSB Changes")
    axes[1, 0].set_xlabel("Time [s]")

    # 2D density: energy score vs modification presence per frame
    axes[1, 1].scatter(scores, frame_density, s=18, c=frame_density, cmap=cmap_cyber, alpha=0.85, edgecolors="none")
    axes[1, 1].set_xlabel("Normalized frame energy")
    axes[1, 1].set_ylabel("LSB flip rate")
    axes[1, 1].set_title("Adaptive Clustering: Energy vs Modification")

    _style_figure(
        fig,
        "Embedding Density Visualization",
        f"Energy percentile gate: {energy_percentile:.0f}%",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_lsb_analysis(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    block: int = 512,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(x.size, y.size)
    lsb_x = (x[:n] & 1).astype(np.uint8)
    lsb_y = (y[:n] & 1).astype(np.uint8)
    flipped = (lsb_x != lsb_y).astype(np.uint8)

    m = (n // block) * block
    mat = flipped[:m].reshape(-1, block) if m > 0 else flipped.reshape(1, -1)
    flip_rate = mat.mean(axis=1)
    t = np.arange(len(flip_rate)) * (block / float(sr))

    bit0_to_1 = ((lsb_x == 0) & (lsb_y == 1)).sum()
    bit1_to_0 = ((lsb_x == 1) & (lsb_y == 0)).sum()

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)

    axes[0, 0].imshow(mat, aspect="auto", cmap=cmap_cyber_diff, interpolation="nearest", vmin=0, vmax=1)
    axes[0, 0].set_title("LSB Bit Flip Map")
    axes[0, 0].set_ylabel("Block")
    axes[0, 0].set_xlabel("Sample in block")

    axes[0, 1].plot(t, flip_rate, color="#06B6D4", lw=1.1)
    axes[0, 1].fill_between(t, flip_rate, color="#06B6D4", alpha=0.15)
    axes[0, 1].set_title("LSB Flip Rate Over Time")
    axes[0, 1].set_xlabel("Time [s]")

    axes[1, 0].bar(["0 → 1", "1 → 0"], [bit0_to_1, bit1_to_0], color=["#06B6D4", "#BD53ED"], edgecolor="#262626")
    axes[1, 0].set_title("Directional LSB Transitions")

    axes[1, 1].hist(lsb_y[flipped.astype(bool)] if flipped.any() else lsb_y, bins=[-0.5, 0.5, 1.5],
                    color="#BD53ED", edgecolor="#262626", rwidth=0.7)
    axes[1, 1].set_title("Post-Embed LSB Value Distribution (changed samples)")
    axes[1, 1].set_xticks([0, 1])

    ber = compute_lsb_ber(original_wav, stego_wav)
    _style_figure(
        fig,
        "LSB Forensic Analysis",
        f"Global LSB BER: {ber:.6f} | Total flips: {int(flipped.sum()):,}",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()


def plot_dashboard_detectability(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    detectability_score: Optional[float] = None,
    score_source: str = "mse",
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(x.size, y.size)
    xf = x[:n].astype(np.float32) / 32768.0
    yf = y[:n].astype(np.float32) / 32768.0
    residual = yf - xf
    diff = xf.astype(np.float32) - yf.astype(np.float32)
    mse = float(np.mean(diff * diff))

    if detectability_score is None:
        # MSE-derived proxy in [0,1] — real measurement, not random
        detectability_score = float(np.clip(np.log10(mse + 1e-16) + 16.0, 0.0, 1.0))

    if detectability_score < 0.33:
        risk, risk_color = "LOW", "#06B6D4"
    elif detectability_score < 0.66:
        risk, risk_color = "MEDIUM", "#BD53ED"
    else:
        risk, risk_color = "HIGH", "#F43F5E"

    fig = plt.figure(figsize=(14, 7), constrained_layout=True)
    gs = GridSpec(2, 2, figure=fig)

    ax_gauge = fig.add_subplot(gs[0, 0])
    ax_gauge.axis("off")
    ax_gauge.set_box_aspect(0.6)
    ax_gauge.add_patch(FancyBboxPatch((0.06, 0.12), 0.88, 0.76, boxstyle="round,pad=0.03",
                                      linewidth=2, edgecolor=risk_color, facecolor="#151515"))
    ax_gauge.text(0.5, 0.68, f"{detectability_score:.3f}", ha="center", fontsize=26, color=risk_color, fontweight="bold")
    ax_gauge.text(0.5, 0.42, f"Risk: {risk}", ha="center", fontsize=14, color=risk_color)
    ax_gauge.text(0.5, 0.22, f"Source: {score_source}", ha="center", fontsize=9, color="#888888")
    ax_gauge.set_xlim(0, 1)
    ax_gauge.set_ylim(0, 1)

    ax_mse = fig.add_subplot(gs[0, 1])
    ax_mse.bar(["MSE"], [mse], color="#06B6D4", edgecolor="#262626")
    ax_mse.set_title("Cover/Stego Mean Squared Error")
    ax_mse.ticklabel_format(axis="y", style="scientific", scilimits=(-2, 2))

    ax_res = fig.add_subplot(gs[1, :])
    ax_res.plot(residual[: min(6000, n)], color="#BD53ED", lw=0.55)
    ax_res.fill_between(np.arange(min(6000, n)), residual[: min(6000, n)], color="#BD53ED", alpha=0.15)
    ax_res.set_title("Residual Waveform (Stego − Cover)")
    ax_res.set_xlabel("Sample")

    _style_figure(
        fig,
        "ML Detectability Assessment",
        f"MSE = {mse:.3e} | Normalized score from real waveform divergence",
    )

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        plt.show()
