
![VisionVend Logo](assets/logo.png)
=======
<!-- Logo -->
<p align="center">
  <img src="assets/logo.png" alt="VisionVend" width="600"/>
</p>

<h1 align="center">VisionVend</h1>

<p align="center">
  Enterprise-grade smart-vending platform for unattended retail
</p>

<p align="center">
  <a href="https://github.com/Artificial-Me/VisionVend/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/Artificial-Me/VisionVend/ci.yml?branch=main&label=CI&logo=github" alt="CI Status">
  </a>
  <a href="https://github.com/Artificial-Me/VisionVend/releases">
    <img src="https://img.shields.io/github/v/release/Artificial-Me/VisionVend?logo=semantic-release" alt="Latest Release">
  </a>
  <a href="https://codecov.io/gh/Artificial-Me/VisionVend">
    <img src="https://img.shields.io/codecov/c/github/Artificial-Me/VisionVend?logo=codecov" alt="Coverage">
  </a>
  <a href="https://hub.docker.com/r/visionvend/api">
    <img src="https://img.shields.io/docker/pulls/visionvend/api?color=2496ED&logo=docker" alt="Docker Pulls">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/Artificial-Me/VisionVend" alt="License">
  </a>
</p>


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

Python 3 · FastAPI · Stripe · MQTT · Prometheus · Grafana · PostgreSQL · Docker · Kubernetes

---

## Platform Architecture – High-Level

```mermaid
graph TD
  subgraph "Edge Device (Fridge)"
    RPi["Raspberry Pi 4"] --> CV["RT-DETR + DeepSORT"]
    RPi --> MQTTpub{{"MQTT Broker"}}
    CV --> DBedge["SQLite cache"]
    ESP["ESP32-S3 Controller"] -->|I²C / GPIO| Door["Mag-Lock"]
    ESP --> Sensors["Door & Load Cells"]
  end

  subgraph "Cloud"
    API["FastAPI API"] --> PG[(PostgreSQL)]
    API --> Stripe["Stripe Payments"]
    API --> Prometheus["Prometheus"]
    API --> MQ["RabbitMQ"]
    Prometheus --> Grafana["Grafana Dashboards"]
    SheetsSync["Google Sheets Sync"] --> PG
  end

  %% Connections
  MQTTpub -- "TLS + HMAC" --> API
  SheetsSync -- REST --> API
```

---

## Payment Workflow – Sequence

```mermaid
sequenceDiagram
    participant User as "User"
    participant Machine as "Vending Machine"
    participant Stripe as "Stripe"

    %% Initial Tap
    User->>Machine: NFC tap / QR scan
    Note right of Machine: Create PaymentIntent (amount=$1 hold)

    Machine->>Stripe: POST /payment_intents
    Stripe-->>Machine: client_secret

    %% Authorisation
    Machine->>User: Display authorise screen
    User->>Machine: Confirm on phone
    Machine->>Stripe: Confirm PaymentIntent
    Stripe-->>Machine: success

    %% Shopping
    Machine->>User: Unlock door
    User->>Machine: Take items

    %% Capture
    Machine->>Stripe: POST /capture (final_amount)
    Stripe-->>Machine: receipt_url

    Machine->>User: Show receipt
```

---

## Getting Started

### 1 · Run the full stack with Docker Compose

```bash
git clone https://github.com/Artificial-Me/VisionVend.git
cd VisionVend
cp .env.example .env          # fill in secrets (Stripe, JWT, etc.)
docker compose up -d
```

Access:

• API: <http://localhost:8000/docs>  
• Grafana: <http://localhost:3000> (admin / _your password_)  
• Prometheus: <http://localhost:9090>

### 2 · Edge-device bootstrap (Raspberry Pi)

```bash
# On Pi OS 64-bit Bookworm
curl -sSfL https://get.visionvend.sh | bash
sudo systemctl enable --now visionvend-edge
```

The installer:

1. Flashes the latest VisionVend-Edge image  
2. Configures Wi-Fi / LTE  
3. Registers the machine with the cloud  

---

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/unlock` | POST | JWT / API-Key | Pre-authorise & unlock door |
| `/save-payment` | POST | JWT | Attach Stripe payment method |
| `/metrics` | GET | none | Prometheus metrics |
| `/health` | GET | none | Liveness & readiness |

Example – `/unlock`

```bash
curl -X POST https://api.visionvend.com/unlock \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id":"txn_1234"}'
```

---

## Contributing

We ❤️ PRs!

1. Fork → feature branch (`feat/…`)  
2. `make pre-commit` (Black, isort, flake8, mypy)  
3. Add/adjust tests → `pytest -q`  
4. Open PR, fill template, link issue  
5. One reviewer + passing CI = merge 🎉  

---

## License

Released under the **MIT License** – see [`LICENSE`](LICENSE).
© 2025 VisionVend Inc.
