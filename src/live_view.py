import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import sounddevice as sd
import matplotlib.pyplot as plt
from scipy.signal import spectrogram


def _read_wav_mono_int16(path: str):
    data, sr = sf.read(path, dtype='int16')
    if data.ndim == 2:
        data = data[:, 0]
    return data.astype(np.int16), sr


def _compute_spec(data: np.ndarray, sr: int, nperseg: int, noverlap: int):
    x = data.astype(np.float32)
    f, t, S = spectrogram(x, fs=sr, nperseg=nperseg, noverlap=noverlap)
    S_db = 10.0 * np.log10(S + 1e-12)
    return f, t, S_db


def play_with_live_spectrogram(
    stego_wav: str,
    cover_wav: str | None = None,
    nperseg: int = 1024,
    noverlap: int = 512,
    compare: bool = False,
):
    data, sr = _read_wav_mono_int16(stego_wav)
    duration = data.shape[0] / sr

    # Compute spectrogram(s)
    f_s, t_s, S_s = _compute_spec(data, sr, nperseg, noverlap)
    if compare and cover_wav:
        cov, _ = _read_wav_mono_int16(cover_wav)
        f_c, t_c, S_c = _compute_spec(cov, sr, nperseg, noverlap)
        vmin = min(S_s.min(), S_c.min())
        vmax = max(S_s.max(), S_c.max())
    else:
        vmin, vmax = S_s.min(), S_s.max()

    # Prepare figure
    if compare and cover_wav:
        fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
        im0 = ax[0].pcolormesh(t_c, f_c, S_c, shading='gouraud', cmap='magma', vmin=vmin, vmax=vmax)
        ax[0].set_title('Original')
        ax[0].set_xlabel('Time [s]')
        ax[0].set_ylabel('Frequency [Hz]')
        im1 = ax[1].pcolormesh(t_s, f_s, S_s, shading='gouraud', cmap='magma', vmin=vmin, vmax=vmax)
        ax[1].set_title('Stego (live cursor)')
        ax[1].set_xlabel('Time [s]')
        line_c = ax[0].axvline(0.0, color='cyan', lw=1.0)
        line_s = ax[1].axvline(0.0, color='cyan', lw=1.0)
        fig.colorbar(im1, ax=ax.ravel().tolist(), shrink=0.85, label='dB')
    else:
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        im = ax.pcolormesh(t_s, f_s, S_s, shading='gouraud', cmap='magma', vmin=vmin, vmax=vmax)
        ax.set_title('Stego Spectrogram (live cursor)')
        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Frequency [Hz]')
        line_s = ax.axvline(0.0, color='cyan', lw=1.0)
        fig.colorbar(im, ax=ax, shrink=0.9, label='dB')

    fig.tight_layout()

    # Playback setup
    sd.stop()
    # Normalize to float32 in [-1,1] for playback
    y = (data.astype(np.float32)) / 32768.0
    start_time = None

    def _update_frame(_):
        nonlocal start_time
        if start_time is None:
            return line_s,
        elapsed = time.perf_counter() - start_time
        x = max(0.0, min(elapsed, duration))
        if compare and cover_wav:
            line_c.set_xdata([x, x])
            line_s.set_xdata([x, x])
            return line_c, line_s
        else:
            line_s.set_xdata([x, x])
            return line_s,

    # Use matplotlib timer for updates (~30 fps)
    timer = fig.canvas.new_timer(interval=33)
    timer.add_callback(_update_frame, None)

    def _on_close(event):
        sd.stop()

    fig.canvas.mpl_connect('close_event', _on_close)

    # Start playback slightly after showing the window to avoid backend delays
    def _start_playback():
        nonlocal start_time
        sd.play(y, sr, blocking=False)
        start_time = time.perf_counter()
        timer.start()

    fig.canvas.mpl_connect('draw_event', lambda evt: None)
    # Kick off playback after window is drawn
    fig.canvas.manager.window.after(100, _start_playback) if hasattr(fig.canvas.manager, 'window') else _start_playback()

    plt.show()


def main():
    ap = argparse.ArgumentParser(description='Live spectrogram while playing audio')
    ap.add_argument('--stego', type=Path, required=True, help='Path to stego WAV')
    ap.add_argument('--cover', type=Path, help='Path to original WAV (optional, for side-by-side)')
    ap.add_argument('--nperseg', type=int, default=1024)
    ap.add_argument('--noverlap', type=int, default=512)
    ap.add_argument('--compare', action='store_true', help='Show original vs stego side-by-side with live cursor')
    args = ap.parse_args()

    play_with_live_spectrogram(
        stego_wav=str(args.stego),
        cover_wav=str(args.cover) if args.cover else None,
        nperseg=args.nperseg,
        noverlap=args.noverlap,
        compare=bool(args.compare and args.cover),
    )


if __name__ == '__main__':
    main()
