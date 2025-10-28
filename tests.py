# tests.py
from embed import embed_lsb
from extract import extract_lsb
from adaptive_mask import compute_energy_mask
# If you have encrypt, import and use it
# from encrypt import aes_encrypt, aes_decrypt

def demo_basic():
    cover = "../data/original/sample.wav"   # put a WAV here (16-bit)
    out = "../data/stego/stego.wav"
    message = b"Hello Hawi! This is a secret."
    # compute map using adaptive energy masking
    mask = compute_energy_mask(cover, frame_size=2048, hop_size=1024, percentile=55)
    # embed
    embed_lsb(cover, message, out, embed_map=mask)
    # extract
    recovered = extract_lsb(out, max_payload_bytes=200)
    print("Recovered:", recovered)

if __name__ == "__main__":
    demo_basic()
