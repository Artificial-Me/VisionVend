
**Hardware Stack**

| **Component**               | **Purpose**                             | **Specifications**              | **Cost (Adafruit/Other)**                                                                   | **Notes**                            |
| --------------------------------- | --------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Raspberry Pi 4 (4GB)**    | **ML, camera control**                  | **Quad-core, 4GB RAM, USB-C**   | **$45 (market)**                                                                            | **Runs DETR locally, stores videos** |
| **Camera Module 3 (x2)**    | **Object detection**                    | **12MP, 75° FOV**              | **$50 ($25 each, Adafruit ID: 5659, $22.50 with 10% discount)**                             | **Dual for redundancy**              |
| **ESP32-S3-DevKit-C-1**     | **Controller (lock, weight, feedback)** | **N16R8, 8MB PSRAM, Wi-Fi/BLE** | **$6.50 (market)**                                                                          | **Runs MicroPython**                 |
| **SIM7080G CAT-M/NB-IoT**   | **LTE for payments**                    | **Embedded antenna, low-power** | **$22 (market)**                                                | **~$2–$5/mo data** |                                            |
| **Load Cells (x4)**         | **Weight backup**                       | **50kg half-bridge, ±2g**      | **$3.20 ($0.80 each, market)**                                                              | **Supports ~20kg shelf**             |
| **HX711 ADC (x4)**          | **Weight measurement**                  | **24-bit, 80Hz**                | **$3.20 ($0.80 each, market)**                                                              | **Interfaces with ESP32**            |
| **Fail-Secure Mag-Lock**    | **Door security**                       | **12V, 300mA, 600lb**           | **$12 (market)**                                                                            | **Adhesive/screw mount**             |
| **Hall Sensor**             | **Door status**                         | **Magnetic**                    | **$0.30 (market)**                                                                          | **Simple, reliable**                 |
| **Mini MOSFET Board**       | **Lock control**                        | **Drives 12V lock**             | **$0.70 (market)**                                                                          | **ESP32 GPIO**                       |
| **NTAG 215 Sticker**        | **NFC interface**                       | **ISO 14443, 540 bytes**        | **$0.25 (Adafruit ID: 360, $0.23 with discount)**                                           | **Launches PWA**                     |
| **QR Code Sticker**         | **Backup interface**                    | **Vinyl**                       | **$0.10 (market)**                                                                          | **NFC alternative**                  |
| **OLED (SSD1306)**          | **Feedback**                            | **0.96" I2C, 128x64**           | **$14.95 (Adafruit ID: 326, $13.46 with discount)**                                         | **Accessibility**                    |
| **RGB LED (NeoPixel)**      | **Visual feedback**                     | **3-color, 8mm**                | **$0.80 (Adafruit ID: 1938, $0.72 with discount)**                                          | **Status indicator**                 |
| **Piezo Buzzer**            | **Audible feedback**                    | **Active, 5V**                  | **$1.50 (Adafruit ID: 1536, $1.35 with discount)**                                          | **Event chirps**                     |
| **Li-Po Battery (500mAh)**  | **ESP32 power**                         | **3.7V, TP4056 USB-C**          | **$6 (market)**                                                                             | **~24hr runtime**                    |
| **Li-Po Battery (2000mAh)** | **Pi 4 power**                          | **3.7V, TP4056 USB-C**          | **$12 (market)**                                                                            | **~12hr runtime**                    |
| **Supercapacitor**          | **Fail-secure backup**                  | **2.7F, 5.5V**                  | **$4 (market)**                                                                             | **10s lock/MQTT power**              |
| **32GB SD Card**            | **Video storage**                       | **Class 10, microSD**           | **$6 (market)**                                                                             | **Stores ~24hr video**               |
| **Optional: VL53L1X ToF**   | **Proximity wake**                      | **30cm, I2C**                   | **$8 (market)**                                                                             | **LED brightening**                  |
| **Optional: DFPlayer Mini** | **Voice prompts**                       | **MP3, microSD**                | **$8.95 (Adafruit ID: 805, $8.06 with discount)**                                           | **Accessibility**                    |
| **Mounting**                | **Retrofit**                            | **3M VHB, 3D-printed bracket**  | **$8 (market)**                                                                             | **No case mods**                     |

**Total BOM**:

* **Base (LTE, batteries)**: ~$197.21 (with Adafruit discounts).
* **With Optionals (ToF, DFPlayer)**: ~$213.27.
* **Retail/Assembly**: ~$200–$250 (markup, enclosure, labor).
* **Recurring Data**: ~$2–$5/mo (LTE for payments).

**Cost Comparison**:

* **Original: $1,059.74–$1,817.24.**
* **Previous Hybrid: $150–$250.**
* **New: ~$200–$250 (higher due to Pi 4, cameras, batteries, but no 5G hub).**

**Savings**:

* **Original: $1,059.74–$1,817.24 (5G hub, dual Pi Zero).**
* **Previous Hybrid: $150–$250 (no cameras, store power).**
* **New: $200–$250 (batteries, dual cameras, LTE).**
