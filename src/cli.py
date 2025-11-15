import argparse
import hashlib
from pathlib import Path

from .embed import embed_adaptive_keyed
from .extract import extract_adaptive_keyed
from .metrics import compute_snr_db


def _derive_aes_key_bytes(key_str: str, key_len: int = 16) -> bytes:
    # Derive AES key bytes from user string via SHA-256
    h = hashlib.sha256(key_str.encode('utf-8')).digest()
    return h[:key_len]


def cmd_embed(args: argparse.Namespace):
    cover = str(args.cover)
    out = str(args.out)
    key_bytes = _derive_aes_key_bytes(args.key, 16)
    if args.msg is not None:
        plaintext = args.msg.encode('utf-8')
    else:
        plaintext = Path(args.msg_file).read_bytes()

    embed_adaptive_keyed(
        cover_wav_path=cover,
        plaintext=plaintext,
        out_wav_path=out,
        user_key=key_bytes,
        frame_size=args.frame_size,
        hop_size=args.hop_size,
        energy_percentile=args.energy_percentile,
        encrypt=not args.no_encrypt,
    )

    if args.snr_against:
        snr = compute_snr_db(cover, out)
        print(f"SNR: {snr:.2f} dB")


def cmd_extract(args: argparse.Namespace):
    stego = str(args.stego)
    key_bytes = _derive_aes_key_bytes(args.key, 16)
    payload = extract_adaptive_keyed(
        stego_wav_path=stego,
        user_key=key_bytes,
        frame_size=args.frame_size,
        hop_size=args.hop_size,
        energy_percentile=args.energy_percentile,
        decrypt=not args.no_decrypt,
    )
    if payload is None:
        print("Extraction failed.")
        return
    if args.out_text:
        # try decoding utf-8
        try:
            print(payload.decode('utf-8'))
        except Exception:
            print(payload)
    elif args.out_file:
        Path(args.out_file).write_bytes(payload)
        print(f"Wrote output to {args.out_file}")


def main():
    p = argparse.ArgumentParser(description="Adaptive & Keyed Audio Steganography")
    sub = p.add_subparsers(dest='cmd', required=True)

    pe = sub.add_parser('embed', help='Embed a message into WAV')
    pe.add_argument('--cover', required=True, type=Path)
    pe.add_argument('--out', required=True, type=Path)
    pe.add_argument('--key', required=True, help='User key (string)')
    gmsg = pe.add_mutually_exclusive_group(required=True)
    gmsg.add_argument('--msg', type=str, help='Message text to embed')
    gmsg.add_argument('--msg-file', type=Path, help='Path to file whose bytes to embed')
    pe.add_argument('--frame-size', type=int, default=1024)
    pe.add_argument('--hop-size', type=int, default=512)
    pe.add_argument('--energy-percentile', type=float, default=0.0)
    pe.add_argument('--no-encrypt', action='store_true', help='Disable AES encryption')
    pe.add_argument('--snr-against', action='store_true', help='Print SNR vs cover after embedding')
    pe.set_defaults(func=cmd_embed)

    px = sub.add_parser('extract', help='Extract a message from WAV')
    px.add_argument('--stego', required=True, type=Path)
    px.add_argument('--key', required=True, help='User key (string)')
    px.add_argument('--frame-size', type=int, default=1024)
    px.add_argument('--hop-size', type=int, default=512)
    px.add_argument('--energy-percentile', type=float, default=0.0)
    px.add_argument('--no-decrypt', action='store_true', help='Disable AES decryption')
    outg = px.add_mutually_exclusive_group()
    outg.add_argument('--out-text', action='store_true', help='Print recovered text to stdout')
    outg.add_argument('--out-file', type=Path, help='Write recovered bytes to file')
    px.set_defaults(func=cmd_extract)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
