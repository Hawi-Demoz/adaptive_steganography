"""Optional CLI for ML-based detectability prediction.

This CLI is separate from the main steganography CLI to avoid changing any
existing outputs or workflows.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .detectability_ml import (
    EmbeddingStrategy,
    choose_least_detectable_strategy,
    generate_dataset,
    load_dataset,
    save_prediction_visualization,
    save_model,
    train_regression_model,
)


def _payloads_from_args(payload_text: str, count: int, min_len: int, max_len: int) -> list[bytes]:
    base = payload_text.encode("utf-8")
    payloads: list[bytes] = []
    if count <= 1:
        return [base[:max(min_len, 1)]]

    lengths = []
    step = max(1, (max_len - min_len) // max(1, count - 1))
    curr = min_len
    for _ in range(count):
        lengths.append(curr)
        curr = min(curr + step, max_len)

    for length in lengths:
        reps = (length // max(1, len(base))) + 1
        payload = (base * reps)[:length]
        payloads.append(payload)

    return payloads


def _cmd_build_dataset(args: argparse.Namespace) -> None:
    payloads = _payloads_from_args(
        payload_text=args.payload_text,
        count=args.payload_count,
        min_len=args.payload_min_len,
        max_len=args.payload_max_len,
    )
    energies = [float(x.strip()) for x in args.energy_percentiles.split(",") if x.strip()]
    keys = [x.strip() for x in args.keys.split(",") if x.strip()]

    dataset_csv = generate_dataset(
        cover_wav=str(args.cover),
        output_dir=str(args.output_dir),
        payloads=payloads,
        energy_percentiles=energies,
        key_texts=keys,
        encrypt=not args.no_encrypt,
        frame_size=args.frame_size,
        hop_size=args.hop_size,
    )
    print(f"Dataset written to: {dataset_csv}")


def _cmd_train(args: argparse.Namespace) -> None:
    x, y, feature_names = load_dataset(str(args.dataset_csv))
    result = train_regression_model(
        x=x,
        y=y,
        model_type=args.model_type,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    model_path = save_model(result["model"], feature_names, str(args.model_out))
    plot_path = Path(args.model_out).with_name(Path(args.model_out).stem + "_predicted_vs_actual.png")
    saved_plot = save_prediction_visualization(
        y_true=result["y_test"],
        y_pred=result["y_pred"],
        output_path=str(plot_path),
    )

    print(f"Model saved to: {model_path}")
    print(f"Prediction plot saved to: {saved_plot}")
    print(f"MAE: {result['mae']:.6f}")

    y_test = result["y_test"]
    y_pred = result["y_pred"]
    preview_n = min(10, len(y_test))
    print("\nPredicted vs Actual (first rows):")
    for i in range(preview_n):
        print(f"  idx={i:02d}  predicted={float(y_pred[i]):.4f}  actual={float(y_test[i]):.4f}")


def _cmd_choose_strategy(args: argparse.Namespace) -> None:
    payload = args.payload_text.encode("utf-8")

    energies = [float(x.strip()) for x in args.energy_percentiles.split(",") if x.strip()]
    keys = [x.strip() for x in args.keys.split(",") if x.strip()]

    strategies: list[EmbeddingStrategy] = []
    for key_text in keys:
        for energy in energies:
            strategies.append(
                EmbeddingStrategy(
                    key_text=key_text,
                    energy_percentile=energy,
                    frame_size=args.frame_size,
                    hop_size=args.hop_size,
                    encrypt=not args.no_encrypt,
                )
            )

    result = choose_least_detectable_strategy(
        cover_wav=str(args.cover),
        payload=payload,
        model_path=str(args.model_path),
        output_dir=str(args.output_dir),
        strategies=strategies,
    )

    best = result["best"]
    best_strategy = best["strategy"]

    print("Best strategy found:")
    print(f"  stego_path: {best['stego_path']}")
    print(f"  predicted_detectability: {float(best['predicted_detectability']):.4f}")
    print(f"  key_text: {best_strategy.key_text}")
    print(f"  energy_percentile: {best_strategy.energy_percentile}")

    print("\nAll candidates:")
    for item in result["all_candidates"]:
        st = item["strategy"]
        print(
            "  "
            f"path={item['stego_path']}  "
            f"pred={float(item['predicted_detectability']):.4f}  "
            f"key={st.key_text}  "
            f"energy={st.energy_percentile}"
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Optional ML detectability CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("build-dataset", help="Generate stego samples and feature dataset")
    pd.add_argument("--cover", required=True, type=Path)
    pd.add_argument("--output-dir", required=True, type=Path)
    pd.add_argument("--payload-text", type=str, default="secret-message")
    pd.add_argument("--payload-count", type=int, default=6)
    pd.add_argument("--payload-min-len", type=int, default=16)
    pd.add_argument("--payload-max-len", type=int, default=512)
    pd.add_argument("--energy-percentiles", type=str, default="0,20,40")
    pd.add_argument("--keys", type=str, default="k1,k2,k3")
    pd.add_argument("--frame-size", type=int, default=1024)
    pd.add_argument("--hop-size", type=int, default=512)
    pd.add_argument("--no-encrypt", action="store_true")
    pd.set_defaults(func=_cmd_build_dataset)

    pt = sub.add_parser("train", help="Train detectability regression model")
    pt.add_argument("--dataset-csv", required=True, type=Path)
    pt.add_argument("--model-out", required=True, type=Path)
    pt.add_argument("--model-type", choices=["random_forest", "linear"], default="random_forest")
    pt.add_argument("--test-size", type=float, default=0.2)
    pt.add_argument("--random-state", type=int, default=42)
    pt.set_defaults(func=_cmd_train)

    pc = sub.add_parser("choose-strategy", help="Try multiple strategies and pick least detectable")
    pc.add_argument("--cover", required=True, type=Path)
    pc.add_argument("--model-path", required=True, type=Path)
    pc.add_argument("--output-dir", required=True, type=Path)
    pc.add_argument("--payload-text", required=True, type=str)
    pc.add_argument("--energy-percentiles", type=str, default="0,20,40")
    pc.add_argument("--keys", type=str, default="k1,k2,k3")
    pc.add_argument("--frame-size", type=int, default=1024)
    pc.add_argument("--hop-size", type=int, default=512)
    pc.add_argument("--no-encrypt", action="store_true")
    pc.set_defaults(func=_cmd_choose_strategy)

    return p


def main() -> int:
    # Keep cwd stable when launched from different locations.
    os.chdir(Path(__file__).resolve().parent.parent)
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
