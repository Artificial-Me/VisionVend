import stripe
from paho.mqtt import client as mqtt_client
import yaml
import os
import hmac
import hashlib
import logging
from pywebpush import webpush, WebPushException
import logging

def send_notification(payload):
    logging.info(f"[Dummy] send_notification called with: {payload}")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

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
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

stripe.api_key = os.getenv("STRIPE_API_KEY") or config["stripe"]["api_key"]
mqtt_broker = config["mqtt"]["broker"]
mqtt_port = config["mqtt"]["port"]
mqtt_client_id = config["mqtt"]["client_id"]
unlock_topic = config["mqtt"]["unlock_topic"]
status_topic = config["mqtt"]["status_topic"]
door_topic = config["mqtt"]["door_topic"]
hmac_secret = config["mqtt"]["hmac_secret"]

# MQTT client setup
mqtt = mqtt_client.Client(mqtt_client_id)
mqtt.connect(mqtt_broker, mqtt_port)

# Transaction tracking
transaction_intent = {}
transaction_items = {}

# Validate MQTT payload
def validate_hmac(payload, received_hmac):
    computed_hmac = hmac.new(hmac_secret.encode(), payload, hashlib.sha256).hexdigest()
    return computed_hmac == received_hmac

# MQTT callback
def on_message(client, userdata, msg):
    if msg.topic == door_topic:
        payload, received_hmac = msg.payload.decode().split("|")
        if validate_hmac(payload, received_hmac):
            transaction_id, items_str, delta_mass = payload.split(":")
            items = items_str.split(",") if items_str else []
            delta_mass = float(delta_mass)
            payment_intent_id = transaction_intent.get(transaction_id)
            total = sum(config["inventory"].get(item, {"price": 0})["price"] for item in items)
            if items and payment_intent_id:
                total_cents = int(total * 100)
                stripe.PaymentIntent.modify(payment_intent_id, amount=max(total_cents, 100))
                stripe.PaymentIntent.capture(payment_intent_id)
                transaction_items[transaction_id] = items
                send_notification({"title": "Receipt", "body": f"Items: {', '.join(items)}, Total: ${total:.2f}"})
            elif payment_intent_id:
                stripe.PaymentIntent.cancel(payment_intent_id)
                send_notification({"title": "No Charge", "body": "No items removed"})
            mqtt.publish(status_topic, f"{transaction_id}:{','.join(items) if items else 'No items'}:${total if items else 0:.2f}")

mqtt.on_message = on_message
mqtt.subscribe(door_topic)

class UnlockRequest(BaseModel):
    id: str = None

@app.post("/unlock")
async def unlock(request: Request):
    body = await request.json()
    transaction_id = body.get("id") or os.urandom(16).hex()
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=100,
            currency="usd",
            automatic_payment_methods={"enabled": True},
            capture_method="manual",
        )
        transaction_intent[transaction_id] = payment_intent.id
        payload = f"unlock:{transaction_id}"
        hmac_val = hmac.new(hmac_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        mqtt.publish(unlock_topic, f"{payload}|{hmac_val}")
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
        # For demo: create a new customer each time (in production, use authenticated user info)
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
