import urllib.request
import hashlib
from pathlib import Path

URL = "https://raw.githubusercontent.com/the-solipsist/rbi-forex-reference-rates/main/rbi_forex_reference_rates_long.csv"
RAW_DIR = Path("data/raw/rbi_forex")
RAW_DIR.mkdir(parents=True, exist_ok=True)
DEST_FILE = RAW_DIR / "rbi_forex_reference_rates_long.csv"

def download_and_inspect():
    print(f"Downloading historical RBI forex dataset from:\n  {URL}")
    urllib.request.urlretrieve(URL, DEST_FILE)
    size = DEST_FILE.stat().st_size
    print(f"Saved to {DEST_FILE} ({size:,} bytes)")
    
    sha256 = hashlib.sha256(DEST_FILE.read_bytes()).hexdigest()
    print(f"SHA-256: {sha256}")
    
    with open(DEST_FILE, "r", encoding="utf-8") as f:
        lines = [f.readline().strip() for _ in range(15)]
    print("\nFirst 15 lines:")
    for line in lines:
        print(" ", line)

if __name__ == "__main__":
    download_and_inspect()

