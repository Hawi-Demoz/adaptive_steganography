import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

from .keyed_adaptive import generate_order_indices
from .encrypt import aes_encrypt
from .metrics import compute_sample_change_stats


PREAMBLE = b"ASTG"


def _read_wav_mono_int16(path: str):
    data, sr = sf.read(path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]
    return data.astype(np.int16), sr


def _bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8)).astype(np.uint8)


def _compute_rms_per_frame(x: np.ndarray, frame_size: int, hop_size: int) -> tuple[np.ndarray, list[tuple[int, int]]]:
    n = x.shape[0]
    rms = []
    edges = []
    for s in range(0, n, hop_size):
        e = min(s + frame_size, n)
        if s >= e:
            break
        frame = x[s:e].astype(np.float32)
        val = float(np.sqrt(np.mean(frame * frame))) if frame.size else 0.0
        rms.append(val)
        edges.append((s, e))
    return np.array(rms, dtype=np.float32), edges


def _ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def _print_change_report(original_wav: str, stego_wav: str, label: str):
    stats = compute_sample_change_stats(original_wav, stego_wav)
    total = stats["samples_total"]
    changed = stats["samples_changed"]
    frac = stats["fraction_changed"] * 100.0 if total else 0.0
    print(f"[{label}] Sample change metrics:")
    print(f"  Samples changed: {changed} / {total} ({frac:.4f}%)")
    print(f"  LSB changed: {stats['lsb_changed']}")
    print(f"  Max abs diff: {stats['max_abs_diff']} LSB units")
    print(f"  SNR: {stats['snr_db']:.2f} dB")
    print(f"  BER (LSB): {stats['ber_lsb']:.6f}")


def plot_waveform_comparison(
    original_wav: str,
    stego_wav: str,
    num_samples: int = 5000,
    save_path: Optional[str] = None,
    report_stats: bool = False,
):
    x, _ = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(num_samples, x.size, y.size)
    idx = np.arange(n)
    # Normalize to [-1, 1] in float for correct LSB-level visualization
    xf = x[:n].astype(np.float64) / 32768.0
    yf = y[:n].astype(np.float64) / 32768.0
    diff_sig = yf - xf
    diff_lsb = diff_sig * 32768.0

    # changed positions (any difference) and LSB-changed positions
    diff = (x[:n] != y[:n])
    lsb_changed = ((x[:n] ^ y[:n]) & 1) != 0

    fig, ax = plt.subplots(4, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
    fig.suptitle(f"Waveform Comparison\nCover: {Path(original_wav).name} | Stego: {Path(stego_wav).name}")
    if fig.canvas.manager is not None:
        try:
            fig.canvas.manager.set_window_title("Waveform Comparison")
        except Exception:
            pass
    ax[0].plot(idx, xf, label='Original (normalized)', lw=1)
    ax[0].plot(idx, yf, label='Stego (normalized)', lw=1, alpha=0.7)
    if np.any(diff):
        ax[0].scatter(idx[diff], yf[diff], s=10, c='crimson', label='Modified samples')
    ax[0].set_title('Waveform: Original vs Stego (normalized)')
    ax[0].legend(loc='upper right')

    ax[1].plot(idx, diff_lsb, lw=1, color='slateblue')
    if np.any(lsb_changed):
        ax[1].scatter(idx[lsb_changed], diff_lsb[lsb_changed], s=10, c='orange', label='LSB changed')
        ax[1].legend(loc='upper right')
    ax[1].set_title('Difference (Stego - Original) in LSB units')
    ax[1].set_ylabel('Amplitude difference (LSB units)')

    # Zoomed difference view for low-level LSB noise
    ax[2].plot(idx, diff_lsb, lw=1, color='dimgray')
    ax[2].set_title('Difference (zoomed, LSB units)')
    ax[2].set_ylabel('Amplitude difference (LSB units)')
    ax[2].set_ylim(-1.5, 1.5)
    ax[1].set_xlabel('Sample index')
    ax[2].set_xlabel('Sample index')

    # Histogram of LSB differences
    ax[3].hist(diff_lsb, bins=[-1.5, -0.5, 0.5, 1.5], color='gray', edgecolor='black')
    ax[3].set_title('Histogram of LSB differences')
    ax[3].set_xlabel('LSB difference value')
    ax[3].set_ylabel('Count')

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()

    if report_stats:
        _print_change_report(original_wav, stego_wav, label="Waveform")


def plot_spectrogram_comparison(
    original_wav: str,
    stego_wav: str,
    nperseg: int = 1024,
    noverlap: int = 512,
    save_path: Optional[str] = None,
    show_difference: bool = True,
    report_stats: bool = False,
):
    x, sr = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    x = x.astype(np.float64)
    y = y.astype(np.float64)
    peak = max(np.max(np.abs(x)), np.max(np.abs(y)), 1e-12)
    x = x / peak
    y = y / peak
    noise = y - x
    f1, t1, Sx = spectrogram(x, fs=sr, nperseg=nperseg, noverlap=noverlap)
    f2, t2, Sy = spectrogram(y, fs=sr, nperseg=nperseg, noverlap=noverlap)
    if show_difference:
        f3, t3, Sn = spectrogram(noise, fs=sr, nperseg=nperseg, noverlap=noverlap)

    Sx_db = 10 * np.log10(Sx + 1e-12)
    Sy_db = 10 * np.log10(Sy + 1e-12)
    vmin = min(Sx_db.min(), Sy_db.min())
    vmax = max(Sx_db.max(), Sy_db.max())

    if show_difference:
        fig, ax = plt.subplots(1, 3, figsize=(16, 4), sharey=True, constrained_layout=True)
    else:
        fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey=True, constrained_layout=True)
    fig.suptitle(
        f"Spectrogram Comparison\nCover: {Path(original_wav).name} | Stego: {Path(stego_wav).name}"
    )
    if fig.canvas.manager is not None:
        try:
            fig.canvas.manager.set_window_title("Spectrogram Comparison")
        except Exception:
            pass
    im0 = ax[0].pcolormesh(t1, f1, Sx_db, shading='gouraud', cmap='magma', vmin=vmin, vmax=vmax)
    ax[0].set_title('Original Spectrogram')
    ax[0].set_xlabel('Time [s]')
    ax[0].set_ylabel('Frequency [Hz]')
    im1 = ax[1].pcolormesh(t2, f2, Sy_db, shading='gouraud', cmap='magma', vmin=vmin, vmax=vmax)
    ax[1].set_title('Stego Spectrogram')
    ax[1].set_xlabel('Time [s]')
    if show_difference:
        Sn_db = 10 * np.log10(Sn + 1e-12)
        # The embedded noise is typically extremely low-level. Use a fixed window
        # so small differences don't get hidden by auto-ranging.
        n_vmax = 0.0
        n_vmin = -120.0
        im2 = ax[2].pcolormesh(t3, f3, Sn_db, shading='gouraud', cmap='viridis', vmin=n_vmin, vmax=n_vmax)
        ax[2].set_title('Noise Spectrogram (Stego - Cover)')
        ax[2].set_xlabel('Time [s]')
        fig.colorbar(im1, ax=[ax[0], ax[1]], shrink=0.8, label='dB (signal)')
        fig.colorbar(im2, ax=ax[2], shrink=0.8, label='dB (noise)')
    else:
        fig.colorbar(im1, ax=ax.ravel().tolist(), shrink=0.8, label='dB')
    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()

    if report_stats:
        _print_change_report(original_wav, stego_wav, label="Spectrogram")


def plot_energy_analysis(audio_wav: str, frame_size: int = 1024, hop_size: int = 512, p_low: float = 33.0, p_high: float = 66.0, save_path: Optional[str] = None):
    x, sr = _read_wav_mono_int16(audio_wav)
    rms, edges = _compute_rms_per_frame(x, frame_size, hop_size)
    thr_low = np.percentile(rms, p_low)
    thr_high = np.percentile(rms, p_high)
    levels = np.zeros_like(rms, dtype=np.int32)
    levels[rms >= thr_low] = 1
    levels[rms >= thr_high] = 2

    t = np.arange(len(rms)) * (hop_size / float(sr))
    fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
    ax[0].plot(t, rms, label='RMS/frame')
    ax[0].axhline(thr_low, color='orange', ls='--', label=f'{p_low}th pct')
    ax[0].axhline(thr_high, color='red', ls='--', label=f'{p_high}th pct')
    ax[0].set_title('Energy (RMS) per frame')
    ax[0].legend(loc='upper right')

    # Show assignment: 0=skip, 1=1-bit, 2=2-bit (visual intent)
    colors = np.array(['#cccccc', '#66bb6a', '#ef5350'])
    ax[1].bar(t, np.maximum(0.2, levels), width=(hop_size/44100.0), color=colors[levels], align='edge')
    ax[1].set_title('Adaptive embedding plan (0-bit skip, 1-bit, 2-bit)')
    ax[1].set_xlabel('Time [s]')

    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


def plot_random_positions(audio_wav: str, key_str: str, count: int = 5000, frame_size: int = 1024, hop_size: int = 512, energy_percentile: float = 20.0, save_path: Optional[str] = None):
    key_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()[:16]
    order = generate_order_indices(audio_wav, key=key_bytes, frame_size=frame_size, hop_size=hop_size, energy_percentile=energy_percentile)
    n = min(count, order.size)
    sel = order[:n]

    fig, ax = plt.subplots(figsize=(10, 3), constrained_layout=True)
    ax.scatter(np.arange(n), sel, s=3, alpha=0.7)
    ax.set_title(f'Key-based random embedding positions (first {n})')
    ax.set_xlabel('Order index (rank)')
    ax.set_ylabel('Sample position')
    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


def plot_snr_and_noise(
    original_wav: str,
    stego_wav: str,
    save_path: Optional[str] = None,
    num_samples: int = 10000,
    report_stats: bool = False,
):
    x, _ = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(num_samples, x.size, y.size)
    x_f = x[:n].astype(np.float64)
    y_f = y[:n].astype(np.float64)
    peak = max(np.max(np.abs(x_f)), np.max(np.abs(y_f)), 1e-12)
    x_f /= peak
    y_f /= peak
    noise = y_f - x_f
    p_sig = np.mean(x_f * x_f) + 1e-12
    p_noise = np.mean(noise * noise) + 1e-12
    snr_db = 10.0 * np.log10(p_sig / p_noise)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    fig.suptitle(f"SNR & Noise\nCover: {Path(original_wav).name} | Stego: {Path(stego_wav).name}")
    if fig.canvas.manager is not None:
        try:
            fig.canvas.manager.set_window_title("SNR & Noise")
        except Exception:
            pass
    ax[0].hist(noise, bins=51, color='slateblue', alpha=0.8)
    ax[0].set_title(f'Noise histogram (SNR ~ {snr_db:.2f} dB)')
    ax[0].set_xlabel('Amplitude difference')
    ax[0].set_ylabel('Count')
    ax[1].plot(noise, lw=0.8)
    ax[1].set_title('Noise (time domain)')
    ax[1].set_xlabel('Sample index')
    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()

    if report_stats:
        _print_change_report(original_wav, stego_wav, label="SNR & Noise")


def _build_embedded_bits(plaintext: bytes, key_bytes: bytes) -> np.ndarray:
    payload = aes_encrypt(plaintext, key_bytes)
    length_bytes = len(payload).to_bytes(4, 'big')
    full = PREAMBLE + length_bytes + payload
    return _bytes_to_bits(full)


def _extract_bits_from_signal(data: np.ndarray, indices: np.ndarray, bits_len: int) -> np.ndarray:
    sel = indices[:bits_len]
    return (data[sel] & 1).astype(np.uint8)


def plot_ber_vs_awgn(
    cover_wav: str,
    message: bytes,
    key_str: str,
    snr_db_list: Iterable[float] = (60, 50, 40, 30),
    frame_size: int = 1024,
    hop_size: int = 512,
    energy_percentile: float = 20.0,
    save_path: Optional[str] = None,
):
    # Prepare ordering and reference bits
    key_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()[:16]
    order = generate_order_indices(cover_wav, key=key_bytes, frame_size=frame_size, hop_size=hop_size, energy_percentile=energy_percentile)
    ref_bits = _build_embedded_bits(message, key_bytes)
    if ref_bits.size > order.size:
        raise ValueError("Message too large for this audio.")

    x, sr = _read_wav_mono_int16(cover_wav)
    x = x.copy()
    # Create stego baseline in-memory
    stego = x.copy()
    indices = order[:ref_bits.size]
    stego[indices] = (stego[indices] & ~1) | ref_bits.astype(np.int16)

    # Signal power for noise scaling
    s = stego.astype(np.float64)
    p_sig = np.mean(s * s) + 1e-12

    bers = []
    for target_snr in snr_db_list:
        # add AWGN at desired SNR
        snr_lin = 10 ** (target_snr / 10)
        p_noise = p_sig / snr_lin
        sigma = np.sqrt(p_noise)
        noise = np.random.default_rng(0).normal(0.0, sigma, size=stego.shape[0])
        y = s + noise
        y = np.clip(np.round(y), -32768, 32767).astype(np.int16)

        bits_noisy = _extract_bits_from_signal(y, order, ref_bits.size)
        ber = float(np.mean(bits_noisy != ref_bits))
        bers.append(ber)

    # Plot
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.plot(list(snr_db_list), bers, marker='o')
    ax.set_xlabel('Added AWGN SNR (dB)')
    ax.set_ylabel('Bit Error Rate')
    ax.set_title('BER vs AWGN SNR')
    ax.grid(True, ls='--', alpha=0.5)
    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


def plot_bit_difference_heatmap(
    original_wav: str,
    stego_wav: str,
    block: int = 2048,
    save_path: Optional[str] = None,
    report_stats: bool = False,
):
    x, _ = _read_wav_mono_int16(original_wav)
    y, _ = _read_wav_mono_int16(stego_wav)
    n = min(x.size, y.size)
    x = x[:n]
    y = y[:n]

    # LSB-only binary differences: 1 where embedding flipped LSB, else 0
    lsb_x = (x & 1).astype(np.uint8)
    lsb_y = (y & 1).astype(np.uint8)
    changed = (lsb_x != lsb_y).astype(np.uint8)

    # reshape to blocks
    m = (n // block) * block
    mat = changed[:m].reshape(-1, block)

    fig, ax = plt.subplots(figsize=(10, 3), constrained_layout=True)
    fig.suptitle(f"LSB Modification Heatmap\nCover: {Path(original_wav).name} | Stego: {Path(stego_wav).name}")
    if fig.canvas.manager is not None:
        try:
            fig.canvas.manager.set_window_title("LSB Modification Heatmap")
        except Exception:
            pass
    im = ax.imshow(mat, aspect='auto', cmap='Greys', interpolation='nearest', vmin=0, vmax=1)
    ax.set_title('LSB modification map (1 = LSB changed)')
    ax.set_xlabel('Sample within block')
    ax.set_ylabel('Block index')
    fig.colorbar(im, ax=ax, shrink=0.8, ticks=[0, 1])
    if save_path:
        _ensure_dir(Path(save_path))
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()

    if report_stats:
        _print_change_report(original_wav, stego_wav, label="LSB Heatmap")
