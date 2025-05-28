<!-- Logo -->
<p align="center">
  <img src="assets/logo.png" alt="VisionVend" width="300"/>
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

---

## 🔥 At-a-Glance

|                 |                                                                                              |
|-----------------|----------------------------------------------------------------------------------------------|
| **Purpose**     | Retrofit any fridge, freezer, or glass display case into a fully autonomous point-of-sale.   |
| **Core Stack**  | FastAPI • PostgreSQL • Stripe • MQTT • RabbitMQ • Prometheus • Grafana                        |
| **Edge HW**     | Raspberry Pi 4/5 + dual HQ cameras • ESP32-S3 controller • Fail-secure mag-lock              |
| **Security**    | End-to-end TLS, JWT auth, HMAC-signed MQTT, rate-limiting, SEPA/PCI DSS compliant workflows  |
| **Scalability** | Containerised micro-services, horizontal auto-scaling, multi-region Stripe & MQTT clusters   |

---

## Table of Contents

1. [Key Features](#key-features)  
2. [Platform Architecture](#platform-architecture)  
3. [Quick Start](#quick-start)  
4. [Local Development](#local-development)  
5. [API Reference](#api-reference)  
6. [Security Hardening](#security-hardening)  
7. [Monitoring & Observability](#monitoring--observability)  
8. [Deployment Guide](#deployment-guide)  
9. [Troubleshooting](#troubleshooting)  
10. [Contributing](#contributing)  
11. [License](#license)

---

## Key Features

- **Computer Vision Inventory** – Dual-camera **RT-DETR** detection with DeepSORT tracking  
- **Just-Walk-Out Flow** – Pre-authorise, unlock, track removals, capture final amount only if items were taken  
- **Edge Resilience** – Works offline; syncs transactions when connectivity returns  
- **Secure Payments** – Stripe Payment Intent workflow, Apple Pay / Google Pay ready  
- **Google Sheets Ops** – Non-technical owners manage SKUs, pricing & stock in one spreadsheet  
- **Over-the-Air Updates** – Blue-green Docker image rollout or K8s rolling updates  
- **Enterprise Monitoring** – Prometheus metrics, Grafana dashboards, multi-channel alerting (Slack/email/SMS)  
- **Open API 3** – Auto-generated docs and SDKs for rapid integration  

---

## Platform Architecture

```mermaid
graph TD
  subgraph Edge Device (Fridge)
    RPi[🖥️ Raspberry Pi 4] --> CV[📷 RT-DETR + DeepSORT]
    RPi --> MQTTpub{{MQTT Broker}}
    CV --> DBedge[(SQLite cache)]
    ESP[ESP32-S3] -->|I²C/GPIO| Door(🔒 Mag-Lock)
    ESP --> Sensors(👀 Door & HX711)
  end

  subgraph Cloud
    API[🌐 FastAPI] --> PG[(PostgreSQL)]
    API --> Stripe[💳 Stripe]
    API --> Prom{Prometheus}
    API --> MQ[📣 RabbitMQ]
    Prom --> Grafana[📊 Grafana]
    Helpers[🔗 Google Sheets Sync] --> PG
  end

  MQTTpub -- TLS + HMAC --> API
  Helpers -- REST --> API
```

*Full low-level sequence diagrams available under [`docs/architecture`](docs/).*

---

## Quick Start

### 1 · Run the full stack with Docker Compose

```bash
git clone https://github.com/Artificial-Me/VisionVend.git
cd VisionVend
cp .env.example .env          # fill in secrets (Stripe, JWT, etc.)
docker compose -f docker-compose.yml up -d
```

Access:  
• API: <http://localhost:8000/docs>  
• Grafana: <http://localhost:3000> (admin / *your password*)  
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

## Local Development

```bash
# install deps using UV (10× faster pip)
uv pip install -r requirements.txt -r requirements-dev.txt
# run dev server with hot-reload
uvicorn VisionVend.server.app:app --reload
# run unit + integration tests
pytest -q --cov
```

> **Pi-specific packages** (`picamera2`, `RPi.GPIO`) are **NOT** in `requirements.txt` to keep CI multi-arch images slim.

---

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/unlock` | POST | JWT / API-Key | Pre-auth & unlock door |
| `/save-payment` | POST | JWT | Attach a Stripe payment method |
| `/metrics` | GET | none | Prometheus metrics |
| `/health` | GET | none | Liveness & readiness |

Example – `/unlock`

```bash
curl -X POST https://api.visionvend.com/unlock \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id":"txn_1234"}'
```

Response:

```json
{
  "status": "success",
  "transaction_id": "txn_1234",
  "client_secret": "pi_abc_secret_xyz"
}
```

Full OpenAPI 3 docs at `/docs` and `/redoc`.

---

## Security Hardening

| Layer | Measures |
|-------|----------|
| API   | JWT auth, API-key header, rate-limiting, OWASP headers |
| MQTT  | TLS 1.3, per-message HMAC, ACL topics |
| Data  | At-rest encryption (PG AES-256, S3 SSE-KMS) |
| PCI   | Stripe SAQ A – no card data touches servers |
| Edge  | dm-verity RO rootfs, secure-boot capable, autoupdates |

> Annual third-party pentests; SBOM & CVE scanning in CI.

---

## Monitoring & Observability

- **Prometheus** – request counts, latency, hardware sensors, edge fps  
- **Grafana** – ready-made dashboards /alerts.json  
- **AlertManager** – Slack, email, PagerDuty routes  
- **Structured JSON Logs** – ELK / Loki compatible  
- **Health Checks** – `/health` deep checks DB, Redis, Stripe, cameras  

---

## Deployment Guide

| Target | Reference Docs |
|--------|----------------|
| **Docker Compose** | [`docker-compose.yml`](docker-compose.yml) – laptop / single-node PoC |
| **Kubernetes**     | `k8s/` manifest – HA multi-zone clusters |
| **AWS ECS Fargate**| Terraform module under `infra/` |
| **BalenaCloud**    | Edge fleet OTA for Raspberry Pi |

### Rolling Upgrade (K8s)

```bash
# build & push image (CI does this)
docker buildx bake release
# bump tag
sed -i "s/:latest/:$(git rev-parse --short HEAD)/" k8s/deployment.yaml
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deploy/visionvend
```

---

## Troubleshooting

| Symptom | Checklist |
|---------|-----------|
| Door won’t unlock | • MQTT broker reachable? • HMAC secret mismatch • Edge device RTC correct |
| Payment fails | • Stripe keys valid • Webhook signing secret correct • Customer’s card 3-DS? |
| Camera FPS low | • GPU mem split ≥128 MB • RT-DETR model quantised • Burr-brown USB camera hub? |
| Inventory mismatch | • Re-run `capture --calibrate` • Clean lenses • Check `hand_iou_max` in config |

`docker compose logs -f api edge mqtt` is your friend.

---

## Contributing

We :heart: PRs!  
1. Fork → feature branch (`feat/…`)  
2. `make pre-commit` (Black, isort, flake8, mypy)  
3. Add/adjust tests → `pytest -q`  
4. Open PR, fill template, link issue  
5. One reviewer + passing CI = merge & :tada:

Code style: **Black + isort + mypy strict**  
Commit style: **Conventional Commits**  
Changelog: auto-generated at release.

---

## License

Released under the **MIT License** – see [`LICENSE`](LICENSE).

© 2025 VisionVend Inc. All trademarks belong to their respective owners.
