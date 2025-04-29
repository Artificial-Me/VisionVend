"""
mock_purchase.py
Logs mock-purchase transactions (SKU, user, timestamp) to a .txt file for prototyping on any platform.
Usage:
    python -m VisionVend.raspberry_pi.mock_purchase --sku cola --user testuser
"""
import argparse
import datetime
from pathlib import Path

LOG_PATH = Path("/sd/mock_transactions.txt")

def log_transaction(sku, user):
    now = datetime.datetime.now().isoformat()
    entry = f"{now}\t{user}\t{sku}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(entry)
    print(f"Logged mock-purchase: {entry.strip()}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sku", required=True, help="Product SKU")
    ap.add_argument("--user", required=True, help="User identifier")
    args = ap.parse_args()
    log_transaction(args.sku, args.user)
