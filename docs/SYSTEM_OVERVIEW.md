**System Overview**

**Key Features**

* **Battery-Powered**: Small Li-Po batteries (500mAh for controller, 2000mAh for cameras) with USB-C charging, eliminating 12V rail dependency.
* **Dual-Camera Object Detection**: Two Raspberry Pi Camera Module 3 units, processed locally on a Raspberry Pi 4 using Hugging Face DETR, with videos stored on an SD card for training.
* **Weight Sensors as Redundancy**: Four load cells (HX711) provide backup inventory tracking, reducing errors from similar-weight items.
* **Passive NFC/QR Interface**: NTAG 215 or QR code sticker launches a PWA for unlock and payment, requiring only one tap/scan.
* **Low-Cost LTE**: SIM7080G CAT-M/NB-IoT module (~$22) for payment confirmations, minimizing data usage.
* **Delayed Payment Capture**: Stripe Payment Intent pre-authorizes on tap, captures only after door closure if items are removed.
* **Fail-Secure Lock**: 12V mag-lock with supercapacitor for re-locking during power loss.
* **Robust Feedback**: OLED, RGB LED, and buzzer for clear status updates.
* **Simple Installation**: Adhesive mounting, no case modifications, ideal for fridges/freezers.

---

**Improvements Over Previous Designs**

1. **Battery Power for Simplicity**:
   * **Solution**: Small Li-Po batteries (500mAh for ESP32-S3, 2000mAh for Raspberry Pi 4) with TP4056 USB-C chargers, providing ~12–24 hours of operation per charge.
   * **Benefit**: Eliminates 12V rail integration, making installation plug-and-play for customers who prefer minimal setup (e.g., no electrician needed for fridges/freezers).
2. **Local Object Detection**:
   * **Solution**: Raspberry Pi 4 (4GB) runs Hugging Face DETR locally, processing dual-camera feeds in real-time, storing videos on a 32GB SD card for later analysis/training.
   * **Benefit**: Removes latency from streaming to the cloud, reduces data costs, and enables offline operation except for payment confirmations.
3. **Dual-Camera + Weight Redundancy**:
   * **Solution**: Two Camera Module 3 units for robust object detection, backed by load cells to catch errors (e.g., similar-weight items like a 355g cola vs. 350g soda).
   * **Benefit**: Ensures high accuracy without sole reliance on weight sensors, addressing your concern about error-proneness.
4. **Cost-Effective LTE**:
   * **Solution**: SIM7080G CAT-M/NB-IoT module (**$22) for low-bandwidth payment confirmations (**1KB per transaction), avoiding the $460 5G hub.
   * **Benefit**: Reduces recurring data costs to ~$2–$5/month (or less with pay-per-use plans), sufficient for Stripe API calls.
5. **Enhanced Error Handling**:
   * **Solution**: Cross-reference camera and weight data to flag discrepancies, storing flagged videos for manual review or ML retraining.
   * **Benefit**: Minimizes false positives/negatives, improving reliability for similar-weight SKUs.
6. **Freezer Compatibility**:
   * **Solution**: Use low-temperature-rated Li-Po batteries, conformal coating, and anti-fog lenses for cameras to operate at -20°C.
   * **Benefit**: Ensures reliability in fridges/freezers without hardware modifications.

---

**Process Flow and Logic**

**1. Idle State**

* **Display Case**: Locked (fail-secure mag-lock unpowered).
* **ESP32-S3**: Deep sleep, waking every 250ms to check Hall sensor (door status) and LTE keep-alive.
* **Raspberry Pi 4**: Low-power mode, cameras off, monitoring PIR sensor for motion.
* **Load Cells**: Powered off.
* **Feedback**: OLED off or dim (“Tap to Unlock”), RGB LED off.
* **Power**: ~20µA (ESP32), ~100mA idle (Pi 4), from 500mAh/2000mAh Li-Po batteries.

**2. Customer Approaches**

* **Trigger**: Sees “Tap Phone Here” NFC tag (NTAG 215) or QR code sticker.
* **Action**: Taps phone (iOS 15+, Android 12+) or scans QR, launching PWA.
* **PWA**:
  * **First-time: Sign-in, Stripe payment setup (stored).**
  * **Returning: Loads instantly, no clicks.**
  * **Sends HTTPS **/unlock?id=abc123** to server via LTE.**
* **Feedback**: OLED: “Tap to Unlock,” RGB LED: Green (optional VL53L1X ToF sensor brightens on approach).

**3. Unlock Request**

* **Server**:
  * **Verifies customer (JWT/session).**
  * **Creates Stripe Payment Intent (**amount=100**, **capture_method='manual'**, **automatic_payment_methods** enabled).**
  * **Publishes MQTT **case/123/cmd: unlock:abc123** with HMAC-SHA256.**
* **ESP32-S3**:
  * **Validates HMAC, powers MOSFET to unlock mag-lock.**
  * **Signals Raspberry Pi 4 to capture baseline inventory (cameras + load cells).**
* **Feedback**:
  * **OLED: “Door Unlocked”**
  * **RGB LED: Flashes blue**
  * **Buzzer: Chirps**
  * **Optional voice (DFPlayer Mini): “Door is now unlocked”**

**4. Customer Accesses Case**

* **Door Open**: Mag-lock energized until door closes or 10-second timeout.
* **Inventory Monitoring**:
  * **Cameras: Record video to SD card, process real-time with DETR on Pi 4.**
  * **Load Cells: Sample weight at 80Hz.**
* **Timeout**: If door open >10 seconds, lock re-engages, OLED: “Tap Again,” LED: Red.

**5. Customer Removes Items**

* **Detection**:
  * **Cameras: DETR identifies removed items (e.g., cola, chips).**
  * **Load Cells: Track Δmass (e.g., 355g for cola).**
  * **Cross-reference: Flag discrepancies (e.g., camera detects cola, weight suggests chips).**
* **Storage**: Video saved to SD card with timestamp and transaction ID.

**6. Door Closes**

* **Detection**: Hall sensor triggers on closure.
* **Re-Locking**: MOSFET de-energized, lock engages (supercapacitor ensures power).
* **Inventory Finalization**:
  * **Cameras: Capture final frame, confirm removed items via DETR.**
  * **Load Cells: Record final weight, calculate Δmass.**
  * **Resolution: Use camera data as primary, weight as backup; flag discrepancies for SD card review.**
* **Server Processing**:
  * **ESP32 sends Δmass and transaction ID via LTE/MQTT.**
  * **Pi 4 sends detected items (if discrepancy, includes snapshot).**
  * **Server:**
    * **Maps items to prices (e.g., cola: $2).**
    * **If no items removed: Cancel Payment Intent.**
    * **If items removed: Modify amount, capture payment.**
    * **Sends Web Push receipt to PWA.**
* **Feedback**:
  * **OLED: “No Charge” or “Items: [list], Total: $[amount]”**
  * **RGB LED: Blue (0.5s), then off**
  * **Buzzer: Chirps**
  * **PWA: Displays receipt**

**7. Error Handling**

* **Payment Failure**: PWA/OLED: “Try Another Card,” LED: Red.
* **Inventory Discrepancy**: Flag video for review, use weight data as fallback.
* **Power Loss**: Supercapacitor ensures re-locking and MQTT send.
* **Network Failure**: Buffer MQTT messages, retry when LTE reconnects.
