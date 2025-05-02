
"""
helper.py  – keeps Google-Sheet ⇄ fridge config.yaml in sync
             and records every sale coming from the fridge
"""

import time, threading, yaml, datetime, os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import re

# Load environment variables from .env
load_dotenv()


# ──────────── 1.  SET THESE CONSTANTS FROM ENV ────────────
CONFIG_YAML_PATH = "../config/config.yaml" # where your fridge code reads prices/weights

# Get Google Sheet ID from env, or parse from share link
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
if not SHEET_ID:
    share_link = os.environ.get("GOOGLE_SHEET_SHARE_LINK")
    if share_link:
        match = re.search(r"/d/([\w-]+)", share_link)
        if match:
            SHEET_ID = match.group(1)
if not SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID or a valid GOOGLE_SHEET_SHARE_LINK must be set in the .env file.")

SERVICE_ACCOUNT_PATH = os.environ.get("SERVICE_ACCOUNT_PATH")
if not SERVICE_ACCOUNT_PATH:
    raise RuntimeError("SERVICE_ACCOUNT_PATH must be set in the .env file.")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=SCOPES)
GS = gspread.authorize(CREDS)
SHEET = GS.open_by_key(SHEET_ID)
PROD_TAB = SHEET.worksheet("Products")
SALES_TAB = SHEET.worksheet("SalesLog")

app = FastAPI()

# -----------------------------------------------------
def products_to_config():
    """
    Reads Products tab and writes a compact YAML block
    inventory:
      cola:  {price: 2.0, weight: 355, tolerance: 5}
      chips: {price: 1.5, weight: 70,  tolerance: 4}
    """
    rows = PROD_TAB.get_all_values()[1:]  # skip header
    inv = {}
    for sku, name, price, weight, *_ in rows:
        if not sku:  # ignore blank lines
            continue
        try:
            inv[sku] = {
                "price": float(price),
                "weight": float(weight),
                "tolerance": 5  # hard-coded or add a column
            }
        except ValueError:
            print(f"⚠️  bad numeric value in row with SKU={sku}; skipped")

    data = {"inventory": inv}
    with open(CONFIG_YAML_PATH, "w") as f:
        yaml.dump(data, f)

    print(f"✅ config.yaml updated ({len(inv)} SKUs)")

# -----------------------------------------------------
def periodic_sync(interval=30):
    while True:
        try:
            products_to_config()
        except Exception as e:
            print("Sync error →", e)
        time.sleep(interval)

# -----------------------------------------------------
def append_sale_row(sku: str, qty: int, tx_id: str):
    """
    Append (-qty) to SalesLog. Google-Sheet formulas update stock automatically.
    """
    now_iso = datetime.datetime.utcnow().isoformat(" ", timespec="seconds")
    SALES_TAB.append_row([now_iso, sku, -abs(qty), tx_id], value_input_option="USER_ENTERED")

# -----------------------------------------------------
from pydantic import BaseModel
from typing import List, Optional

class TransactionItem(BaseModel):
    sku: str
    qty: int

class TransactionRequest(BaseModel):
    transaction_id: Optional[str] = "NA"
    items: List[TransactionItem] = []

@app.post("/transaction")
async def transaction_endpoint(payload: TransactionRequest):
    tx_id = payload.transaction_id or "NA"
    items = payload.items or []
    for item in items:
        sku = item.sku
        qty = int(item.qty)
        if sku and qty:
            append_sale_row(sku, qty, tx_id)
    print(f"🛒 logged transaction {tx_id}: {items}")
    return {"status": "ok", "items_logged": len(items)}

# -----------------------------------------------------
if __name__ == "__main__":
    # start background thread that refreshes config.yaml every 30 s
    threading.Thread(target=periodic_sync, daemon=True).start()
    # Start FastAPI server using uvicorn
    uvicorn.run("helper:app", host="0.0.0.0", port=5001, reload=False)
