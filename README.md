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
- Stripe (payment processing)
- MQTT (hardware communication)
- Paho MQTT, PyWebPush, YAML, HMAC, and related libraries

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Hardware: Compatible vending machine/display case with MQTT support

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/VisionVend.git
   cd VisionVend
   ```

2. Install dependencies using [uv](https://docs.astral.sh/uv/getting-started/installation/):
   ```bash
   uv pip install -r VisionVend/server/requirements.txt
   ```

3. Configure environment variables and settings:
   - Copy or edit `config/config.yaml` with your Stripe and MQTT credentials.
   - (Optional) Set environment variable `STRIPE_API_KEY` for Stripe integration.

### Running the Server

From the `VisionVend/server` directory, start the FastAPI server with:

```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

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
