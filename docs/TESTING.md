**Testing and Validation Plan**

1. **Battery Performance**:
   * **Test 500mAh (ESP32) and 2000mAh (Pi 4) for ~12–24hr runtime.**
   * **Verify USB-C charging (TP4056) and supercapacitor backup (>10s).**
2. **Local Object Detection**:
   * **Validate DETR accuracy on Pi 4 for SKUs (e.g., cola, chips).**
   * **Test dual-camera coverage for no blind spots.**
   * **Confirm video storage (~24hr on 32GB SD).**
3. **Weight Redundancy**:
   * **Test load cells (±2g) with SKUs, cross-referencing with camera data.**
   * **Simulate similar-weight items (e.g., 355g vs. 350g) to ensure error detection.**
4. **NFC/QR Tap**:
   * **Test NTAG 215 with iOS 15+/Android 12+ for PWA launch (<2s).**
   * **Verify QR code as backup.**
5. **LTE Payments**:
   * **Confirm Stripe Payment Intent creation/capture via SIM7080G (~1KB/transaction).**
   * **Test offline buffering for network failures.**
6. **Lock and Door**:
   * **Validate mag-lock (600lb) and Hall sensor reliability.**
   * **Test 10-second timeout and re-locking.**
7. **Freezer Compatibility**:
   * **Test at -20°C with low-temp Li-Po, conformal coating, anti-fog lenses.**
   * **Ensure no case modifications are needed.**
8. **Feedback**:
   * **Verify OLED, LED, buzzer clarity in retail settings.**
   * **Test PWA receipt delivery via Web Push.**
