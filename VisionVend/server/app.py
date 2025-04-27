from flask import Flask, jsonify, request
import stripe
from paho.mqtt import client as mqtt_client
import yaml
import os
import hmac
import hashlib
import logging
from webpush import send_notification

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

stripe.api_key = config["stripe"]["api_key"]
mqtt_broker = config["mqtt"]["broker"]
mqtt_port = config["mqtt"]["port"]
mqtt_client_id = config["mqtt"]["client_id"]
unlock_topic = config["mqtt"]["unlock_topic"]
status_topic = config["mqtt"]["status_topic"]
door_topic = config["mqtt"]["door_topic"]
hmac_secret = config["mqtt"]["hmac_secret"]

# MQTT client setup
mqtt_client = mqtt_client.Client(mqtt_client_id)
mqtt_client.connect(mqtt_broker, mqtt_port)

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
            mqtt_client.publish(status_topic, f"{transaction_id}:{','.join(items) if items else 'No items'}:${total if items else 0:.2f}")

mqtt_client.on_message = on_message
mqtt_client.subscribe(door_topic)

# Flask routes
@app.route("/unlock", methods=["POST"])
def unlock():
    transaction_id = request.json.get("id", os.urandom(16).hex())
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
        mqtt_client.publish(unlock_topic, f"{payload}|{hmac_val}")
        return jsonify({"status": "success", "transaction_id": transaction_id})
    except stripe.error.StripeError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(host=config["server"]["host"], port=config["server"]["port"], debug=False)
