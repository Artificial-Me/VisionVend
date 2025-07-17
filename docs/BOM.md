# Bill of Materials

## Core Compute & Vision

- Raspberry Pi 4 (4 GB)**Purpose:** Run DETR locally, store video**Specs:** Quad-core, 4 GB RAM, USB-C**Cost:** ~$45 (market)
- Camera Module 3 ×2
  **Purpose:** Object detection, redundancy
  **Specs:** 12 MP, 75° FOV
  **Cost:** $25 each → $50 total (Adafruit 5659, $22.50 w/ 10 % discount)

## Microcontroller & Sensors

- ESP32-S3-DevKit-C-1 (N16R8)**Purpose:** Lock, weight, user feedback**Specs:** 8 MB PSRAM, Wi-Fi/BLE, MicroPython**Cost:** ~$6.50 (market)
- Load Cells ×4**Purpose:** Weight change confirmation**Specs:** 50 kg half-bridge, ±2 g resolution**Cost:** $0.80 each → $3.20 total (market)
- HX711 ADC ×4**Purpose:** 24-bit weight interface**Specs:** 24-bit, 80 Hz**Cost:** $0.80 each → $3.20 total (market)
- Hall-effect sensor
  **Purpose:** Door open/close state
  **Specs:** Magnetic, digital output
  **Cost:** ~$0.30 (market)

## Connectivity & Payment

- SIM7080G CAT-M/NB-IoT modem**Purpose:** LTE for out-of-band payments**Specs:** Embedded antenna, low-power**Cost:** ~$22 (market)**Recurring:** ~$2–$5/mo data
- NTAG 215 sticker**Purpose:** NFC tag to launch PWA**Specs:** ISO 14443, 540 bytes**Cost:** $0.23 (Adafruit 360, with 10 % discount)
- QR-code vinyl sticker
  **Purpose:** Backup phone interface
  **Cost:** ~$0.10 (market)

## Access Control

- Fail-secure magnetic lock**Purpose:** Door security**Specs:** 12 V, 300 mA, 600 lb holding force**Cost:** ~$12 (market)
- Mini MOSFET driver board
  **Purpose:** Switch 12 V lock from ESP32 GPIO
  **Cost:** ~$0.70 (market)

## User Feedback

- OLED 0.96" SSD1306**Purpose:** Visual status / accessibility**Specs:** 128 × 64, I²C**Cost:** $13.46 (Adafruit 326, with 10 % discount)
- NeoPixel 8 mm RGB LED**Purpose:** Color-coded status indicator**Cost:** $0.72 (Adafruit 1938, with 10 % discount)
- Piezo buzzer**Purpose:** Audible event chirps**Specs:** Active, 5 V**Cost:** $1.35 (Adafruit 1536, with 10 % discount)
- Optional DFPlayer Mini
  **Purpose:** MP3 voice prompts via microSD
  **Cost:** $8.06 (Adafruit 805, with 10 % discount)

## Power & Backup

- Li-Po 500 mAh (ESP32)**Specs:** 3.7 V, TP4056 USB-C charger**Cost:** ~$6 (market)**Runtime:** ~24 hr
- Li-Po 2000 mAh (Pi 4)**Specs:** 3.7 V, TP4056 USB-C charger**Cost:** ~$12 (market)**Runtime:** ~12 hr
- Supercapacitor 2.7 F 5.5 V
  **Purpose:** 10 s fail-secure lock / MQTT on power loss
  **Cost:** ~$4 (market)

## Storage & Extras

- 32 GB Class 10 microSD**Purpose:** Store ~24 hr compressed video**Cost:** ~$6 (market)
- Optional VL53L1X ToF sensor**Purpose:** Proximity wake & LED auto-brighten**Specs:** 30 cm I²C**Cost:** ~$8 (market)
- Mechanical mounting kit
  **Contents:** 3M VHB tape, 3-D-printed brackets
  **Cost:** ~$8 (market)

## Cost Summary

- **Base BOM (LTE, batteries):** ≈ $197.21 (with Adafruit discounts)
- **With optionals (ToF + DFPlayer):** ≈ $213.27
- **Retail / assembly markup:** ~$200–$250 (enclosure, labor)
- **Recurring LTE data:** ~$2–$5/mo
