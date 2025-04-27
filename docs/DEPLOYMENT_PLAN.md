**Deployment Plan**

1. **Prototype**:
   * **Build one unit with Pi 4, dual cameras, ESP32-S3, LTE, and batteries.**
   * **Test in a fridge/freezer, mapping SKUs to weights and training DETR.**
2. **Validation**:
   * **Monitor detection accuracy (target <0.5% false positives).**
   * **Collect SD card videos for ML retraining if needed.**
3. **Scale**:
   * **Deploy to multiple cases with adhesive mounting.**
   * **Use OTA updates for firmware maintenance.**
   * **Train staff on battery recharging (USB-C, ~4hr).**
4. **Future Enhancements**:
   * **Add VL53L1X ToF or DFPlayer Mini based on feedback.**
   * **Develop store app for BLE unlock and loyalty.**
