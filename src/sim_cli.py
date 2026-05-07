"""Interactive CLI simulation for Adaptive & Secure Audio Steganography."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np

from .embed import embed_adaptive_keyed
from .extract import extract_adaptive_keyed
from .encrypt import aes_encrypt
from .metrics import compute_ber, compute_lsb_ber, compute_snr_db, compute_sample_change_stats
from .visualize import (
    plot_bit_difference_heatmap,
    plot_snr_and_noise,
    plot_spectrogram_comparison,
    plot_waveform_comparison,
)


FRAME_SIZE = 1024
HOP_SIZE = 512

ADAPTIVITY_LEVELS = {
    "low": 0.0,
    "medium": 20.0,
    "high": 40.0,
}

LAST_ENERGY_PERCENTILE = ADAPTIVITY_LEVELS["medium"]
LAST_STEGO_PATH: str | None = None
LAST_COVER_PATH: str | None = None
LAST_FIG_DIR: str | None = None
LAST_ML_DATASET_PATH: str | None = None
LAST_ML_MODEL_PATH: str | None = None


def _new_fig_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    figs_dir = Path("figures") / f"run_{stamp}"
    figs_dir.mkdir(parents=True, exist_ok=True)
    return figs_dir


def _derive_aes_key_bytes(passphrase: str, key_len: int = 16) -> bytes:
    h = hashlib.sha256(passphrase.encode("utf-8")).digest()
    return h[:key_len]


def _bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8)).astype(np.uint8)


def _prompt(text: str) -> str:
    return input(text).strip()


def _prompt_yes_no(text: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    val = input(f"{text} {suffix}: ").strip().lower()
    if val == "":
        return default_yes
    return val in {"y", "yes"}


def _prompt_level() -> float:
    while True:
        val = _prompt("Energy adaptivity level (low / medium / high): ").lower()
        if val in ADAPTIVITY_LEVELS:
            return ADAPTIVITY_LEVELS[val]
        print("Invalid choice. Please type: low, medium, or high.")


def _prompt_level_with_default(default_percentile: float) -> float:
    inv = {v: k for k, v in ADAPTIVITY_LEVELS.items()}
    default_label = inv.get(default_percentile, "medium")
    while True:
        val = _prompt(
            f"Energy adaptivity level (low / medium / high) [default: {default_label}]: "
        ).lower()
        if val == "":
            return default_percentile
        if val in ADAPTIVITY_LEVELS:
            return ADAPTIVITY_LEVELS[val]
        print("Invalid choice. Please type: low, medium, or high.")


def _prompt_path(text: str, default_path: str | None = None) -> str:
    if default_path:
        resp = _prompt(f"{text} [default: {default_path}]: ")
        return resp or default_path
    return _prompt(text)


def _prompt_int_with_default(text: str, default_value: int) -> int:
    while True:
        val = _prompt(f"{text} [default: {default_value}]: ")
        if val == "":
            return default_value
        try:
            return int(val)
        except ValueError:
            print("Invalid integer. Try again.")


def _prompt_float_with_default(text: str, default_value: float) -> float:
    while True:
        val = _prompt(f"{text} [default: {default_value}]: ")
        if val == "":
            return default_value
        try:
            return float(val)
        except ValueError:
            print("Invalid number. Try again.")


def _prompt_existing_wav(text: str, default_path: str | None = None) -> str:
    while True:
        path_str = _prompt_path(text, default_path=default_path).strip().strip('"').strip("'")
        p = Path(path_str)
        candidates = [p]
        if not p.is_absolute():
            # Try relative to current working directory and project root
            candidates.append(Path.cwd() / p)
            project_root = Path(__file__).resolve().parent.parent
            candidates.append(project_root / p)
        for c in candidates:
            if c.exists() and c.is_file() and c.suffix.lower() == ".wav":
                return str(c)
        print("Invalid path. Please provide an existing .wav file.")


def _prompt_output_wav(text: str, default_path: str | None = None) -> str:
    while True:
        path_str = _prompt_path(text, default_path=default_path).strip().strip('"').strip("'")
        if "python" in path_str.lower() or "-m" in path_str.lower():
            print("Invalid output path. Please enter only a .wav file path.")
            continue
        p = Path(path_str)
        if p.suffix.lower() != ".wav":
            print("Invalid output path. The output file must end with .wav.")
            continue
        # Ensure parent directory exists
        if p.parent and not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)


def _print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def _load_ml_tools():
    """Import ML tools lazily so the base simulator can run without ML deps."""

    try:
        from .detectability_ml import (
            EmbeddingStrategy,
            choose_least_detectable_strategy,
            generate_dataset,
            load_dataset,
            save_prediction_visualization,
            save_model,
            train_regression_model,
        )
        return {
            "EmbeddingStrategy": EmbeddingStrategy,
            "choose_least_detectable_strategy": choose_least_detectable_strategy,
            "generate_dataset": generate_dataset,
            "load_dataset": load_dataset,
            "save_prediction_visualization": save_prediction_visualization,
            "save_model": save_model,
            "train_regression_model": train_regression_model,
        }
    except Exception as exc:
        print("\n[ML Error] Optional ML tools are unavailable.")
        print(f"Reason: {exc}")
        print("Install required packages in your venv (for example: librosa, scikit-learn).")
        return None


def _embed_flow():
    global LAST_ENERGY_PERCENTILE, LAST_STEGO_PATH, LAST_COVER_PATH
    _print_header("Embedding: Adaptive & Secure Audio Steganography")

    cover = _prompt_existing_wav("Enter cover audio file path: ")
    message = _prompt("Enter secret message (text): ")
    passphrase = _prompt("Enter embedding key / passphrase: ")
    encrypt = _prompt_yes_no("Enable AES encryption?", default_yes=True)
    energy_percentile = _prompt_level()
    LAST_ENERGY_PERCENTILE = energy_percentile

    default_out = str(Path("data") / "stego" / "stego.wav")
    out_path = _prompt_output_wav(
        "Enter output stego file path (e.g., data/stego/stego.wav)",
        default_path=default_out,
    )

    key_bytes = _derive_aes_key_bytes(passphrase, 16)

    print("\n[Status] AES encryption:", "ENABLED" if encrypt else "DISABLED")
    print("[Status] Key-based random embedding: ENABLED")
    print(
        "[Status] Energy-adaptive embedding: ENABLED",
        f"(level: {energy_percentile}th percentile)",
    )

    embed_adaptive_keyed(
        cover_wav_path=cover,
        plaintext=message.encode("utf-8"),
        out_wav_path=out_path,
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=energy_percentile,
        encrypt=encrypt,
    )

    LAST_STEGO_PATH = out_path
    LAST_COVER_PATH = cover

    # Report how many bits were used and expected flips
    embedded_len_bytes = len(aes_encrypt(message.encode("utf-8"), key_bytes)) if encrypt else len(message.encode("utf-8"))
    bits_used = 64 + embedded_len_bytes * 8
    stats = compute_sample_change_stats(cover, out_path)
    print("\n[Embedding Utilization]")
    print(f"Bits used (header + payload): {bits_used}")
    print(f"Estimated flips (~50% of used): {bits_used/2:.0f}")
    print(f"Actual flips: {stats['lsb_changed']} / {stats['samples_total']} ({stats['fraction_changed']*100:.4f}%)")

    snr = compute_snr_db(cover, out_path)

    # BER on recovered plaintext (0.0 means perfect extraction)
    extracted_plain = extract_adaptive_keyed(
        stego_wav_path=out_path,
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=energy_percentile,
        decrypt=True,
    )
    if extracted_plain is None:
        ber_payload = None
    else:
        bits_a = _bytes_to_bits(message.encode("utf-8"))
        bits_b = _bytes_to_bits(extracted_plain)
        min_len = min(bits_a.size, bits_b.size)
        ber_payload = compute_ber(bits_a[:min_len], bits_b[:min_len]) if min_len > 0 else 0.0

    # LSB-level BER between cover and stego (how many samples were flipped)
    ber_lsb = compute_lsb_ber(cover, out_path)

    print("\n[Output]")
    print(f"Stego file: {out_path}")
    print("\n[Performance Metrics]")
    print(f"Metrics cover: {cover}")
    print(f"SNR: {snr:.2f} dB")
    if ber_payload is None:
        print("Payload BER: unavailable (extraction failed)")
    else:
        print(f"Payload BER: {ber_payload:.6f}")
    print(f"LSB BER (cover vs stego): {ber_lsb:.6f}")


def _extract_flow():
    global LAST_ENERGY_PERCENTILE, LAST_STEGO_PATH, LAST_COVER_PATH, LAST_FIG_DIR
    _print_header("Extraction: Adaptive & Secure Audio Steganography")

    default_stego = str(Path("data") / "stego" / "stego.wav")
    while True:
        stego = _prompt_existing_wav("Enter stego audio file path", default_path=default_stego)
        p = Path(stego)
        if p.parent.name.lower() == "original":
            print("[Warning] You selected an original/cover file. Extraction requires a stego file.")
            if _prompt_yes_no("Continue anyway?", default_yes=False):
                break
            continue
        break
    passphrase = _prompt("Enter extraction key / passphrase: ")
    key_bytes = _derive_aes_key_bytes(passphrase, 16)
    energy_percentile = _prompt_level_with_default(LAST_ENERGY_PERCENTILE)
    LAST_ENERGY_PERCENTILE = energy_percentile

    payload = extract_adaptive_keyed(
        stego_wav_path=stego,
        user_key=key_bytes,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
        energy_percentile=energy_percentile,
        decrypt=True,
    )

    LAST_STEGO_PATH = stego

    print("\n[Status] AES decryption: ENABLED")
    print("[Status] Key-based random extraction: ENABLED")
    print(
        "[Status] Energy-adaptive extraction: ENABLED",
        f"(level: {energy_percentile}th percentile)",
    )

    if payload is None:
        print("\n[Output]")
        print("Extraction failed. Likely causes: wrong key or mismatched parameters.")
        return

    try:
        text = payload.decode("utf-8")
    except Exception:
        text = str(payload)

    print("\n[Output]")
    print(f"Secret message is = {text}")

    # Metrics before/after embedding
    cover_for_metrics = _prompt_existing_wav(
        "Enter original cover path for SNR/BER metrics",
        default_path=LAST_COVER_PATH or "data/original/sample.wav",
    )
    LAST_COVER_PATH = cover_for_metrics

    snr_before = compute_snr_db(cover_for_metrics, cover_for_metrics)
    snr_after = compute_snr_db(cover_for_metrics, stego)
    ber_before = compute_lsb_ber(cover_for_metrics, cover_for_metrics)
    ber_after = compute_lsb_ber(cover_for_metrics, stego)

    print("\n[Performance Metrics]")
    print("Before embedding (cover vs cover):")
    print(f"  SNR: {snr_before:.2f} dB")
    print(f"  BER: {ber_before:.6f}")
    print("After embedding (cover vs stego):")
    print(f"  SNR: {snr_after:.2f} dB")
    print(f"  BER: {ber_after:.6f}")

    # Optional comparison figures
    if _prompt_yes_no("Generate comparison figures?", default_yes=True):
        cover_path = _prompt_existing_wav(
            "Enter original cover path for comparison figures",
            default_path=LAST_COVER_PATH or "data/original/sample.wav",
        )
        LAST_COVER_PATH = cover_path
        figs_dir = _new_fig_dir()
        LAST_FIG_DIR = str(figs_dir)
        wf_path = figs_dir / "waveform_comparison.png"
        sp_path = figs_dir / "spectrogram_comparison.png"
        sn_path = figs_dir / "snr_and_noise.png"
        hm_path = figs_dir / "bit_difference_heatmap.png"

        plot_waveform_comparison(
            original_wav=cover_path,
            stego_wav=stego,
            save_path=str(wf_path),
            report_stats=True,
        )
        plot_spectrogram_comparison(
            original_wav=cover_path,
            stego_wav=stego,
            save_path=str(sp_path),
            report_stats=True,
        )
        plot_snr_and_noise(
            original_wav=cover_path,
            stego_wav=stego,
            save_path=str(sn_path),
            report_stats=True,
        )
        plot_bit_difference_heatmap(
            original_wav=cover_path,
            stego_wav=stego,
            save_path=str(hm_path),
            report_stats=True,
        )
        print("\n[Figures]")
        print(f"Saved comparison figures to: {figs_dir.resolve()}")
        for p in [wf_path, sp_path, sn_path, hm_path]:
            if p.exists():
                print(f"- {p.resolve()}")
            else:
                print(f"[Warning] Missing file: {p.resolve()}")

        # Display is handled via menu option 3


def _show_plots_flow():
    _print_header("Comparison Plots")
    if not LAST_STEGO_PATH:
        print("No stego file available. Please embed or extract first.")
        return
    cover_path = LAST_COVER_PATH
    if not cover_path:
        cover_path = _prompt_existing_wav(
            "Enter original cover path for comparison figures",
            default_path="data/original/sample.wav",
        )
    plot_waveform_comparison(
        original_wav=cover_path,
        stego_wav=LAST_STEGO_PATH,
        save_path=None,
        report_stats=True,
    )
    plot_spectrogram_comparison(
        original_wav=cover_path,
        stego_wav=LAST_STEGO_PATH,
        save_path=None,
        report_stats=True,
    )
    plot_snr_and_noise(
        original_wav=cover_path,
        stego_wav=LAST_STEGO_PATH,
        save_path=None,
        report_stats=True,
    )
    plot_bit_difference_heatmap(
        original_wav=cover_path,
        stego_wav=LAST_STEGO_PATH,
        save_path=None,
        report_stats=True,
    )


def _payloads_from_text(payload_text: str, count: int, min_len: int, max_len: int) -> list[bytes]:
    base = payload_text.encode("utf-8")
    if count <= 1:
        return [base[: max(min_len, 1)]]

    payloads: list[bytes] = []
    step = max(1, (max_len - min_len) // max(1, count - 1))
    curr = min_len
    lengths = []
    for _ in range(count):
        lengths.append(curr)
        curr = min(curr + step, max_len)

    for length in lengths:
        reps = (length // max(1, len(base))) + 1
        payloads.append((base * reps)[:length])
    return payloads


def _ml_build_dataset_flow():
    global LAST_COVER_PATH, LAST_ML_DATASET_PATH
    _print_header("ML: Build Detectability Dataset")

    ml = _load_ml_tools()
    if ml is None:
        return

    cover = _prompt_existing_wav(
        "Enter cover audio file path",
        default_path=LAST_COVER_PATH or str(Path("data") / "original" / "sample.wav"),
    )
    LAST_COVER_PATH = cover

    output_dir = _prompt_path("Output folder for ML artifacts", default_path=str(Path("data") / "ml"))
    payload_text = _prompt("Base payload text [default: secret-message]: ") or "secret-message"
    payload_count = _prompt_int_with_default("Number of payload variants", 6)
    payload_min_len = _prompt_int_with_default("Minimum payload length (bytes)", 16)
    payload_max_len = _prompt_int_with_default("Maximum payload length (bytes)", 512)
    energy_csv = _prompt("Energy percentiles comma list [default: 0,20,40]: ") or "0,20,40"
    keys_csv = _prompt("Keys comma list [default: k1,k2,k3]: ") or "k1,k2,k3"
    encrypt = _prompt_yes_no("Enable AES encryption for dataset generation?", default_yes=True)

    payloads = _payloads_from_text(payload_text, payload_count, payload_min_len, payload_max_len)
    energies = [float(x.strip()) for x in energy_csv.split(",") if x.strip()]
    keys = [x.strip() for x in keys_csv.split(",") if x.strip()]

    dataset_csv = ml["generate_dataset"](
        cover_wav=cover,
        output_dir=output_dir,
        payloads=payloads,
        energy_percentiles=energies,
        key_texts=keys,
        encrypt=encrypt,
        frame_size=FRAME_SIZE,
        hop_size=HOP_SIZE,
    )
    LAST_ML_DATASET_PATH = str(dataset_csv)

    print("\n[ML Output]")
    print(f"Dataset created: {dataset_csv}")


def _ml_train_flow():
    global LAST_ML_DATASET_PATH, LAST_ML_MODEL_PATH
    _print_header("ML: Train Detectability Model")

    ml = _load_ml_tools()
    if ml is None:
        return

    dataset_default = LAST_ML_DATASET_PATH or str(Path("data") / "ml" / "detectability_dataset.csv")
    dataset_csv = _prompt_path("Dataset CSV path", default_path=dataset_default)
    model_default = str(Path("data") / "ml" / "detectability_model.pkl")
    model_out = _prompt_path("Model output path", default_path=LAST_ML_MODEL_PATH or model_default)
    model_type = (_prompt("Model type (random_forest / linear) [default: random_forest]: ") or "random_forest").strip().lower()
    if model_type not in {"random_forest", "linear"}:
        print("Invalid model type. Falling back to random_forest.")
        model_type = "random_forest"
    test_size = _prompt_float_with_default("Test split ratio", 0.2)
    random_state = _prompt_int_with_default("Random seed", 42)

    x, y, feature_names = ml["load_dataset"](dataset_csv)
    result = ml["train_regression_model"](
        x=x,
        y=y,
        model_type=model_type,
        test_size=test_size,
        random_state=random_state,
    )
    out_path = ml["save_model"](result["model"], feature_names, model_out)
    plot_path = Path(model_out).with_name(Path(model_out).stem + "_predicted_vs_actual.png")
    saved_plot = ml["save_prediction_visualization"](
        y_true=result["y_test"],
        y_pred=result["y_pred"],
        output_path=str(plot_path),
    )
    LAST_ML_MODEL_PATH = str(out_path)

    y_test = result["y_test"]
    y_pred = result["y_pred"]
    preview_n = min(10, len(y_test))

    print("\n[ML Output]")
    print(f"Model saved: {out_path}")
    print(f"Prediction plot saved: {saved_plot}")
    print(f"MAE: {result['mae']:.6f}")
    print("Predicted vs Actual (first rows):")
    for i in range(preview_n):
        print(f"  idx={i:02d}  predicted={float(y_pred[i]):.4f}  actual={float(y_test[i]):.4f}")


def _ml_choose_strategy_flow():
    global LAST_COVER_PATH, LAST_ML_MODEL_PATH
    _print_header("ML: Choose Least Detectable Strategy")

    ml = _load_ml_tools()
    if ml is None:
        return

    cover = _prompt_existing_wav(
        "Enter cover audio file path",
        default_path=LAST_COVER_PATH or str(Path("data") / "original" / "sample.wav"),
    )
    LAST_COVER_PATH = cover

    model_default = LAST_ML_MODEL_PATH or str(Path("data") / "ml" / "detectability_model.pkl")
    model_path = _prompt_path("Model path", default_path=model_default)
    output_dir = _prompt_path("Candidate output folder", default_path=str(Path("data") / "ml" / "candidates"))
    payload_text = _prompt("Payload text to embed: ")
    energy_csv = _prompt("Energy percentiles comma list [default: 0,20,40]: ") or "0,20,40"
    keys_csv = _prompt("Keys comma list [default: k1,k2,k3]: ") or "k1,k2,k3"
    encrypt = _prompt_yes_no("Enable AES encryption for candidate generation?", default_yes=True)

    energies = [float(x.strip()) for x in energy_csv.split(",") if x.strip()]
    keys = [x.strip() for x in keys_csv.split(",") if x.strip()]

    EmbeddingStrategy = ml["EmbeddingStrategy"]
    strategies = []
    for key_text in keys:
        for energy in energies:
            strategies.append(
                EmbeddingStrategy(
                    key_text=key_text,
                    energy_percentile=energy,
                    frame_size=FRAME_SIZE,
                    hop_size=HOP_SIZE,
                    encrypt=encrypt,
                )
            )

    result = ml["choose_least_detectable_strategy"](
        cover_wav=cover,
        payload=payload_text.encode("utf-8"),
        model_path=model_path,
        output_dir=output_dir,
        strategies=strategies,
    )

    best = result["best"]
    best_strategy = best["strategy"]

    print("\n[ML Output]")
    print("Best strategy found:")
    print(f"  stego_path: {best['stego_path']}")
    print(f"  predicted_detectability: {float(best['predicted_detectability']):.4f}")
    print(f"  key_text: {best_strategy.key_text}")
    print(f"  energy_percentile: {best_strategy.energy_percentile}")

    print("All candidates:")
    for item in result["all_candidates"]:
        st = item["strategy"]
        print(
            "  "
            f"path={item['stego_path']}  "
            f"pred={float(item['predicted_detectability']):.4f}  "
            f"key={st.key_text}  "
            f"energy={st.energy_percentile}"
        )


def _ml_flow():
    while True:
        _print_header("ML Detectability Tools")
        print("1) Build dataset")
        print("2) Train regression model")
        print("3) Choose least detectable strategy")
        print("4) Back to main menu")
        choice = _prompt("Select an option (1/2/3/4): ").strip()

        if choice == "1":
            _ml_build_dataset_flow()
        elif choice == "2":
            _ml_train_flow()
        elif choice == "3":
            _ml_choose_strategy_flow()
        elif choice == "4":
            break
        else:
            print("Invalid selection. Please enter 1, 2, 3, or 4.")


def main():
    while True:
        _print_header("Adaptive & Secure Audio Steganography Simulation")
        print("1) Embed secret message")
        print("2) Extract secret message")
        print("3) Show comparison plots")
        print("4) Exit")
        print("5) ML detectability commands")
        print("Note: For correct extraction, match energy level used during embedding.")
        raw_choice = _prompt("Select an option (1/2/3/4/5): ")
        choice = raw_choice.strip()
        print(f"[Debug] Menu selection received: '{choice}'")

        if choice == "":
            print("Invalid selection. Please enter 1, 2, 3, 4, or 5.")
            continue

        if choice == "1":
            print("[Debug] Entering embed mode...")
            try:
                _embed_flow()
            except Exception as exc:
                print(f"[Error] Embedding failed: {exc}")
                raise
        elif choice == "2":
            print("[Debug] Entering extract mode...")
            try:
                _extract_flow()
            except Exception as exc:
                print(f"[Error] Extraction failed: {exc}")
                raise
        elif choice == "3":
            print("[Debug] Entering plot display mode...")
            _show_plots_flow()
        elif choice == "4":
            print("Exiting simulation.")
            break
        elif choice == "5":
            print("[Debug] Entering ML tools mode...")
            try:
                _ml_flow()
            except Exception as exc:
                print(f"[Error] ML workflow failed: {exc}")
                raise
        else:
            print("Invalid selection. Please enter 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()
