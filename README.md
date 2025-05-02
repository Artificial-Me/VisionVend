![VisionVend Logo](assets/logo-neonpunk_enhanced.jpeg)

# VisionVend

VisionVend is a Smart Vending Machine Hardware and Software service that lets owner/operators retrofit their product display cases, refrigerators, or freezers to allow unattended sales of their inventory.

## Features

- Retrofit existing display cases for unattended sales
- Remote unlocking and transaction management
- Secure payment processing via Stripe
- Inventory tracking and receipt notifications
- MQTT-based hardware integration for real-time communication
- REST API powered by FastAPI

## Tech Stack

- Python 3
- FastAPI (backend REST API)
- Stripe API (payment processing)
- MQTT (hardware communication)
- Paho MQTT, PyWebPush, YAML, HMAC, and related libraries

## API Endpoints

- `POST /unlock` — Initiate a transaction and unlock the vending machine.
- `POST /save-payment` — Save a payment method for a customer.

## Usage

1. Use the `/unlock` endpoint to start a transaction and unlock the case.
2. Remove items; the system calculates the total and charges via Stripe.
3. Receive notifications and receipts automatically.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE) (or specify your license here)
