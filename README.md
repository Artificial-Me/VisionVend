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

   **Note:** On Raspberry Pi OS, install `picamera2` manually:
   ```bash
   sudo apt install python3-picamera2
   ```
   Do NOT add `picamera2` to requirements.txt. This package is only available on Raspberry Pi OS.

3. Configure environment variables and settings:
   - Copy or edit `config/config.yaml` with your Stripe and MQTT credentials.
   - (Optional) Set environment variable `STRIPE_API_KEY` for Stripe integration.

### Running the Server

From the `VisionVend/server` directory, start the FastAPI server with:

```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

---

## Ultra-fast product training (dual-cam, hand-aware, frictionless)

### Cross-platform prototyping (Windows/Mac/Linux)

You can use VisionVend's dataset creation and mock-purchase logging on any OS, even without a Raspberry Pi or hardware. This is ideal for prototyping with GoPro or webcam footage.

#### 1. Auto-label your GoPro or webcam video

- Run the auto-labeler on a video file:
  
  ```bash
  python -m VisionVend.raspberry_pi.video_autolabel --sku cola --video path/to/video.mp4 --every 5
  ```
  - `--sku` is the product name.
  - `--video` is your recorded video file (e.g., from GoPro).
  - `--every` processes every Nth frame (default: 5).

- Labeled images and YOLO-format labels will appear in your configured dataset directory.

#### 2. Log mock-purchases (no Stripe, no hardware required)

- Log a mock-purchase (e.g., when you "remove" an item from your fridge):
  
  ```bash
  python -m VisionVend.raspberry_pi.mock_purchase --sku cola --user testuser
  ```
  - This appends a line to `/sd/mock_transactions.txt` with the timestamp, user, and SKU.

You can now build datasets and simulate purchases entirely on your laptop or desktop!

---

VisionVend now supports a frictionless, robust workflow for owners/operators to add new products and keep the model up-to-date with minimal effort.

### How to train the system on a new product

1. **Add SKU row:** Open the Google Sheet and insert a new row with SKU, price, and weight.
2. **Restock capture:** Open the fridge door, press the blue RESTOCK-TRAIN button. Hold ONE product under the opening (top/bottom camera views) for ~5 seconds until the light flashes green.
3. **Retrain:** When you've added 2-3 new items, press "Retrain" in the dashboard, or wait for the nightly automatic retrain (runs if ≥60 new frames are available).

- The Pi captures ~120 dual-view images per SKU, with the hand automatically cropped out of the bounding box using MediaPipe.
- All hardware and capture parameters are configurable in `config/config.yaml` under the `training` section.
- The system writes logs to `/sd/autolabel_log.jsonl` for troubleshooting and auditing.

#### Calibration (optional)
- Run the `capture.py` calibration mode to auto-tune background subtraction and hand detection for your lighting.
- All thresholds (area, hand IoU, stable frames, timeouts, LED pins/colors, etc.) are set in the config file.

#### Troubleshooting
- **No green flash:** Check hand-IoU threshold, ensure product is visible to both cameras.
- **Not enough frames:** Increase `stable_frames` or lower `min_area` in the config.
- **LED stays red:** Inspect `/sd/autolabel_log.jsonl` for error messages.

See `VisionVend/raspberry_pi/capture.py` and `VisionVend/raspberry_pi/tracker.py` for implementation details.

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
