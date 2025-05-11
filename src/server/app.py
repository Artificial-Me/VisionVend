import stripe
from paho.mqtt import client as mqtt_client
import yaml
import os
import hmac
import hashlib
import logging
from pywebpush import webpush, WebPushException
import logging
import threading
import time
import re
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import datetime
from collections import Counter
import aiosqlite
import json
import asyncio

def send_notification(payload):
    logging.info(f"[Dummy] send_notification called with: {payload}")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

# Load environment variables from .env EARLY
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(level=logging.INFO)

# Load config
CONFIG_FILE_PATH = "config/config.yaml" 
with open(CONFIG_FILE_PATH, "r") as f:
    config = yaml.safe_load(f)

stripe.api_key = os.getenv("STRIPE_API_KEY") or config["stripe"]["api_key"]
mqtt_broker = config["mqtt"]["broker"]
mqtt_port = config["mqtt"]["port"]
mqtt_client_id = config["mqtt"]["client_id"]
unlock_topic = config["mqtt"]["unlock_topic"]
status_topic = config["mqtt"]["status_topic"]
door_topic = config["mqtt"]["door_topic"]
hmac_secret = config["mqtt"]["hmac_secret"]

# --- Google Sheets Integration START ---
# Get Google Sheet ID from env, or parse from share link
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
if not SHEET_ID:
    share_link = os.getenv("GOOGLE_SHEET_SHARE_LINK")
    if share_link:
        match = re.search(r"/d/([\w-]+)", share_link)
        if match:
            SHEET_ID = match.group(1)
if not SHEET_ID:
    logging.warning("GOOGLE_SHEET_ID or GOOGLE_SHEET_SHARE_LINK not set. Google Sheets integration will be disabled.")
    GSHEET_ENABLED = False
else:
    GSHEET_ENABLED = True

SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")
if GSHEET_ENABLED and not SERVICE_ACCOUNT_PATH:
    logging.warning("SERVICE_ACCOUNT_PATH not set. Google Sheets integration will be disabled.")
    GSHEET_ENABLED = False

GS = None
SHEET = None
PROD_TAB = None
SALES_TAB = None

if GSHEET_ENABLED:
    try:
        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        CREDS = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=SCOPES)
        GS = gspread.authorize(CREDS)
        SHEET = GS.open_by_key(SHEET_ID)
        PROD_TAB = SHEET.worksheet("Products")
        SALES_TAB = SHEET.worksheet("SalesLog")
        logging.info("Successfully connected to Google Sheets.")
    except Exception as e:
        logging.error(f"Failed to initialize Google Sheets client: {e}. Disabling GSheet integration.")
        GSHEET_ENABLED = False

def products_to_config():
    global config 
    if not GSHEET_ENABLED or not PROD_TAB:
        logging.warning("Google Sheets not enabled or Product Tab not available. Skipping products_to_config.")
        return

    logging.info("Attempting to sync products from Google Sheets...")
    try:
        rows = PROD_TAB.get_all_values()[1:]  
        inv = {}
        for sku, name, price, weight, *_ in rows:
            if not sku:  
                continue
            try:
                inv[sku] = {
                    "price": float(price),
                    "weight": float(weight),
                    "tolerance": config.get("inventory", {}).get(sku, {}).get("tolerance", 5) 
                }
            except ValueError:
                logging.warning(f"Bad numeric value in Google Sheet row with SKU={sku}; skipped")

        config["inventory"] = inv
        
        with open(CONFIG_FILE_PATH, "w") as f:
            yaml.dump(config, f, sort_keys=False) 
        
        logging.info(f"config.yaml updated with inventory from Google Sheets ({len(inv)} SKUs)")
    except Exception as e:
        logging.error(f"Error in products_to_config: {e}")

def periodic_sync(interval=30):
    while True:
        products_to_config()
        time.sleep(interval)

def append_sale_row(sku: str, qty: int, tx_id: str):
    if not GSHEET_ENABLED or not SALES_TAB:
        logging.warning("Google Sheets not enabled or Sales Tab not available. Skipping append_sale_row.")
        return
    try:
        now_iso = datetime.datetime.utcnow().isoformat(" ", timespec="seconds")
        SALES_TAB.append_row([now_iso, sku, -abs(qty), tx_id], value_input_option="USER_ENTERED")
        logging.info(f"Appended sale to Google Sheet: TX_ID={tx_id}, SKU={sku}, QTY={-abs(qty)}")
    except Exception as e:
        logging.error(f"Error in append_sale_row: {e}")

# --- Google Sheets Integration END ---

# --- SQLite Database Integration START ---
DATABASE_URL = "transactions.db" # Will be created in the same directory as app.py
DB_CONN = None

async def get_db_connection():
    global DB_CONN
    if DB_CONN is None:
        DB_CONN = await aiosqlite.connect(DATABASE_URL)
        DB_CONN.row_factory = aiosqlite.Row # Access columns by name
    return DB_CONN

async def init_db():
    db = await get_db_connection()
    await db.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        payment_intent_id TEXT NOT NULL,
        items_json TEXT,                     -- Store items as a JSON string
        status TEXT NOT NULL,                -- e.g., 'pending_items', 'captured', 'cancelled', 'error'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    await db.execute("""
    CREATE TRIGGER IF NOT EXISTS update_transactions_updated_at
    AFTER UPDATE ON transactions
    FOR EACH ROW
    BEGIN
        UPDATE transactions SET updated_at = CURRENT_TIMESTAMP WHERE transaction_id = OLD.transaction_id;
    END;
    """)
    await db.commit()
    logging.info("Database initialized and 'transactions' table ensured.")

async def close_db_connection():
    global DB_CONN
    if DB_CONN:
        await DB_CONN.close()
        DB_CONN = None
        logging.info("Database connection closed.")

# --- SQLite Database Integration END ---

# MQTT client setup
mqtt = mqtt_client.Client(mqtt_client_id)
mqtt.connect(mqtt_broker, mqtt_port)

# Validate MQTT payload
def validate_hmac(payload, received_hmac):
    computed_hmac = hmac.new(hmac_secret.encode(), payload, hashlib.sha256).hexdigest()
    return computed_hmac == received_hmac

# MQTT message handling
async def process_mqtt_message(payload_str: str, mqtt_client_ref):
    # This function contains the async logic previously in on_message
    transaction_id, items_str, delta_mass_str = payload_str.split(":") # payload_str is already validated
    items = items_str.split(",") if items_str else []
    items = [item.strip() for item in items if item.strip()]
    # delta_mass = float(delta_mass_str) # Not used directly in this logic path after split

    db = await get_db_connection()
    transaction_record = None
    try:
        async with db.execute("SELECT payment_intent_id, status FROM transactions WHERE transaction_id = ?", (transaction_id,)) as cursor:
            transaction_record = await cursor.fetchone()
    except Exception as e:
        logging.error(f"Error fetching transaction {transaction_id} from DB: {e}")
        # Consider how to signal error back if needed, as this is fire-and-forget
        return

    if not transaction_record:
        logging.warning(f"Transaction {transaction_id} not found in database. Ignoring message.")
        return

    payment_intent_id = transaction_record["payment_intent_id"]
    current_status = transaction_record["status"]

    if current_status != 'pending_items':
        logging.warning(f"Transaction {transaction_id} already processed or in unexpected state: {current_status}. Ignoring.")
        return

    # Ensure config is accessible; it's global so it should be fine.
    total = sum(config.get("inventory", {}).get(item, {"price": 0})["price"] for item in items)
    items_json = json.dumps(items)
    new_status = ''

    try:
        if items and payment_intent_id:
            total_cents = int(total * 100)
            stripe.PaymentIntent.modify(payment_intent_id, amount=max(total_cents, 50))
            stripe.PaymentIntent.capture(payment_intent_id)
            send_notification({"title": "Receipt", "body": f"Items: {', '.join(items)}, Total: ${total:.2f}"})
            new_status = 'captured'
            if GSHEET_ENABLED:
                item_counts = Counter(items)
                for sku_item, qty_removed in item_counts.items():
                    append_sale_row(sku_item, qty_removed, transaction_id) # append_sale_row is synchronous
        elif payment_intent_id:
            stripe.PaymentIntent.cancel(payment_intent_id)
            send_notification({"title": "No Charge", "body": "No items removed"})
            new_status = 'cancelled'
        else:
            logging.error(f"No payment_intent_id for transaction {transaction_id} during processing.")
            new_status = 'error_no_intent_id'
        
        await db.execute("UPDATE transactions SET status = ?, items_json = ? WHERE transaction_id = ?", 
                         (new_status, items_json, transaction_id))
        await db.commit()
        logging.info(f"Transaction {transaction_id} status updated to {new_status}.")

    except stripe.error.StripeError as e:
        logging.error(f"Stripe error for transaction {transaction_id}: {e}")
        new_status = 'error_stripe'
        try:
            await db.execute("UPDATE transactions SET status = ?, items_json = ? WHERE transaction_id = ?", 
                             (new_status, items_json, transaction_id))
            await db.commit()
        except Exception as db_err:
            logging.error(f"Failed to update transaction {transaction_id} status to {new_status} after Stripe error: {db_err}")
    except Exception as e:
        logging.error(f"General error processing transaction {transaction_id}: {e}")
        new_status = 'error_general'
        try:
            await db.execute("UPDATE transactions SET status = ?, items_json = ? WHERE transaction_id = ?", 
                             (new_status, items_json, transaction_id))
            await db.commit()
        except Exception as db_err:
            logging.error(f"Failed to update transaction {transaction_id} status to {new_status} after general error: {db_err}")
    finally:
        # Publish status via MQTT client passed as reference
        if new_status.startswith('error'):
            mqtt_client_ref.publish(status_topic, f"{transaction_id}:ERROR")
        elif new_status == 'captured':
            mqtt_client_ref.publish(status_topic, f"{transaction_id}:CAPTURED:{total:.2f}")
        elif new_status == 'cancelled':
            mqtt_client_ref.publish(status_topic, f"{transaction_id}:CANCELLED")

def on_message(client, userdata, msg):
    if msg.topic == door_topic:
        payload, received_hmac = msg.payload.decode().split("|")
        if validate_hmac(payload, received_hmac):
            # payload is "transaction_id:items_str:delta_mass"
            # Schedule the async processing part
            asyncio.create_task(process_mqtt_message(payload, client)) # Pass client for publishing status
        else:
            logging.warning(f"Invalid HMAC for message on {door_topic}: {msg.payload.decode()}")

mqtt.on_message = on_message
mqtt.subscribe(door_topic)

class UnlockRequest(BaseModel):
    id: str = None

@app.on_event("startup")
async def startup_event():
    if GSHEET_ENABLED:
        # Initial sync on startup
        products_to_config() 
        # Start background thread for periodic sync
        sync_thread = threading.Thread(target=periodic_sync, daemon=True)
        sync_thread.start()
        logging.info("Periodic Google Sheets sync thread started.")
    else:
        logging.warning("Google Sheets integration is disabled. Periodic sync will not run.")
    
    # Initialize Database
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    # Close Database Connection
    await close_db_connection()
    logging.info("Application shutdown: MQTT client disconnected, DB connection closed.")

@app.post("/unlock")
async def unlock(request: Request):
    body = await request.json()
    transaction_id = body.get("id") if body and body.get("id") else os.urandom(16).hex()
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=100,  # Smallest pre-auth amount, will be adjusted
            currency="usd",
            payment_method_types=["card_present"], # Assuming card_present for tap
            capture_method="manual",
            metadata={"transaction_id": transaction_id} # Link Stripe PI to our ID
        )
        db = await get_db_connection()
        await db.execute("INSERT INTO transactions (transaction_id, payment_intent_id, status) VALUES (?, ?, ?)", 
                         (transaction_id, payment_intent.id, 'pending_items'))
        await db.commit()
        logging.info(f"Transaction {transaction_id} created in DB with PaymentIntent {payment_intent.id}")

        # Prepare and send MQTT message to unlock door
        message_to_sign = f"{transaction_id}:{payment_intent.id}"
        hmac_val = hmac.new(hmac_secret.encode(), message_to_sign.encode(), hashlib.sha256).hexdigest()
        mqtt.publish(unlock_topic, f"{message_to_sign}|{hmac_val}")
        return {"status": "success", "transaction_id": transaction_id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail={"status": "error", "message": str(e)})

# Save payment method endpoint
@app.post("/save-payment")
async def save_payment(request: Request):
    try:
        data = await request.json()
        payment_method_id = data.get("paymentMethodId")
        if not payment_method_id:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Missing paymentMethodId"})
        customer = stripe.Customer.create()
        stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
        stripe.Customer.modify(customer.id, invoice_settings={"default_payment_method": payment_method_id})
        return {"status": "success", "customer_id": customer.id}
    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {e}")
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error"})

# To run: uvicorn app:app --host 0.0.0.0 --port 5000 --reload
