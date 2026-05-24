"""Quick API embed/extract roundtrip test."""
import hashlib
import requests
from pathlib import Path

BASE = "http://127.0.0.1:5000"
ROOT = Path(__file__).resolve().parent.parent

covers = list(ROOT.glob("**/*.wav"))
covers = [p for p in covers if "stego_" not in p.name and "uploads" not in str(p)]
if not covers:
    raise SystemExit("No cover wav found")
cover = covers[0]
print("Cover:", cover)

password = "testkey123"
message = "api roundtrip message"

with cover.open("rb") as f:
    embed_resp = requests.post(
        f"{BASE}/api/embed",
        files={"cover": (cover.name, f, "audio/wav")},
        data={
            "message": message,
            "password": password,
            "encrypt": "true",
            "energy_percentile": "20",
            "robust_repeat": "1",
        },
        timeout=60,
    )
print("Embed status:", embed_resp.status_code, embed_resp.text[:300])
embed_resp.raise_for_status()
stego_name = embed_resp.json()["stego_filename"]

extract_resp = requests.post(
    f"{BASE}/api/extract",
    data={
        "stego_filename": stego_name,
        "password": password,
        "encrypt": "true",
        "energy_percentile": "20",
        "robust_repeat": "1",
    },
    timeout=60,
)
print("Extract status:", extract_resp.status_code, extract_resp.text)

# Session registry entry check
files = requests.get(f"{BASE}/api/session/files", timeout=10).json()
entry = next((x for x in files if x["stego_filename"] == stego_name), None)
print("Registry entry:", entry)

# Extract using registry params
if entry:
    extract2 = requests.post(
        f"{BASE}/api/extract",
        data={
            "stego_filename": stego_name,
            "password": password,
            "encrypt": "true" if entry.get("encrypt") else "false",
            "energy_percentile": str(entry.get("energy_percentile", 0)),
            "robust_repeat": str(entry.get("robust_repeat", 1)),
        },
        timeout=60,
    )
    print("Extract via registry params:", extract2.status_code, extract2.text)
