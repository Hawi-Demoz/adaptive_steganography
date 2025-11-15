from pathlib import Path
import hashlib

from src.visualize import (
    plot_waveform_comparison,
    plot_spectrogram_comparison,
    plot_energy_analysis,
    plot_random_positions,
    plot_snr_and_noise,
    plot_ber_vs_awgn,
    plot_bit_difference_heatmap,
)
from src.embed import embed_adaptive_keyed


def main():
    root = Path(__file__).parent.parent
    cover = root / 'data' / 'original' / 'file_example_WAV_1MG.wav'
    stego = root / 'data' / 'stego' / 'stego.wav'
    figs = root / 'figures'
    figs.mkdir(exist_ok=True)

    key_str = 'viz-demo-key'
    key_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()[:16]
    message = b'Visualization demo message.'

    # Ensure we have a fresh stego file
    embed_adaptive_keyed(str(cover), message, str(stego), key_bytes, energy_percentile=20.0)

    # Generate figures
    plot_waveform_comparison(str(cover), str(stego), num_samples=3000, save_path=str(figs / 'waveform_comparison.png'))
    plot_spectrogram_comparison(str(cover), str(stego), save_path=str(figs / 'spectrogram_comparison.png'))
    plot_energy_analysis(str(cover), save_path=str(figs / 'energy_analysis.png'))
    plot_random_positions(str(cover), key_str=key_str, count=4000, save_path=str(figs / 'random_positions.png'))
    plot_snr_and_noise(str(cover), str(stego), save_path=str(figs / 'snr_and_noise.png'))
    plot_bit_difference_heatmap(str(cover), str(stego), save_path=str(figs / 'bit_difference_heatmap.png'))
    plot_ber_vs_awgn(str(cover), message, key_str, snr_db_list=[60, 50, 40, 35, 30], save_path=str(figs / 'ber_vs_awgn.png'))

    print('Figures written to', figs)


if __name__ == '__main__':
    main()
