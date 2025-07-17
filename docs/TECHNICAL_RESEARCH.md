# Technical Research and Validation Steps for VisionVend

My goal is to build a comprehensive document outlining the technical research and validation steps for the VisionVend retrofit kit. This plan integrates insights from the finalized Bill of Materials (BOM), optimization analysis, and build plan to ensure the system meets performance, reliability, and runtime requirements.

## Safety Precautions

* Always disconnect power before connecting or disconnecting components.
* Handle electronic components with anti-static precautions.
* Ensure secure mounting of test hardware to prevent falls or damage.
* When testing in live environments (like active refrigerators), be aware of potential condensation and temperature extremes.
* Follow all standard electrical safety guidelines when working with power supplies and batteries.

## 1. Computer Vision Model Benchmarking Protocol

### Objective

To determine the optimal configuration of Computer Vision (CV) models (specifically D-FINE variants, ByteTrack, DeepSORT, or combinations) for deployment on the Raspberry Pi 5, evaluating performance across critical metrics: accuracy, inference speed (Frames Per Second - FPS), and power consumption, to ensure the selected configuration meets system requirements and contributes to the one-week battery runtime target.

### Test Setup

* **Hardware:**
  * One VisionVend Raspberry Pi 5 (8GB RAM) unit, configured as per the finalized BOM, installed within its designed enclosure (ensuring active cooling is functioning).
  * Dual Raspberry Pi Camera Module 3 (Wide/Standard variants, matching intended field installation).
  * Calibrated power supply for RPi 5 (5.1V/5A USB-C PSU).
  * Precision DC power meter or high-resolution current shunt and voltage logger connected inline with the RPi 5 power input to measure instantaneous and average power draw.
  * Test rig simulating the intended display case shelving, capable of holding various product types.
  * Controlled lighting setup (dimmable lights, potentially mimicking typical store lighting, including variations).
  * Reference system for ground truth (e.g., manual counting, pre-annotated videos).
* **Software:**
  * Raspberry Pi OS (64-bit) with necessary libraries (OpenCV, TensorFlow Lite, PyTorch Mobile, or other framework dependencies).
  * Selected CV models (D-FINE variants, ByteTrack, DeepSORT, other candidates like YOLO variants).
  * Custom test script/application to run CV inference on video streams or image sequences.
  * Logging tools for recording inference time per frame, detection/tracking results, and system metrics (CPU/GPU load, temperature).
  * Data acquisition system connected to the power meter/logger for concurrent power consumption recording.
  * Ground truth data for accuracy evaluation.

### Methodology

1. **Prepare Test Environment:** Set up the test rig to mimic the shelving depth and configuration of target display cases. Place reference markers if needed for consistent camera positioning and scale.
2. **Install and Configure:** Install Raspberry Pi OS, necessary software, and CV models on the RPi 5. Connect the dual cameras and ensure they are correctly configured and calibrated (e.g., for perspective correction if needed).
3. **Setup Power Monitoring:** Connect the power meter/logger to monitor the RPi 5 power consumption specifically during the CV processing phase.
4. **Create Test Datasets:**
   * Record video sequences or capture sets of images within the controlled test setup using the VisionVend camera configuration.
   * Datasets should represent diverse scenarios:
     * Varying lighting conditions (bright, dim, mixed).
     * Different product types (varied shapes, sizes, colors, packaging reflectivity).
     * Varying item densities (full shelves, sparse shelves, single items).
     * Simulated customer interactions (door open/close, items being taken, potential partial occlusions).
   * Create corresponding ground truth annotations for each dataset (item locations, identities, counts) for accuracy measurement.
5. **Develop Benchmarking Script:** Write a script or application that:
   * Loads a specified CV model configuration.
   * Processes the test video sequences or image sets.
   * Logs the inference time for each frame or image.
   * Logs the detected objects, bounding boxes, and tracking IDs (if applicable).
   * Integrates with the power monitoring system to record power draw during processing.
6. **Execute Benchmarking:** For each candidate CV model/combination:
   * Run the benchmarking script on each test dataset multiple times to account for variability.
   * Ensure the RPi 5 is running the test exclusively to get accurate performance metrics.
   * Allow the RPi 5 temperature to stabilize before running performance tests.
7. **Collect Data:** Gather logs of inference times, detection/tracking outputs, and concurrent power consumption measurements.
8. **Analyze Data:**
   * **Accuracy:** Compare detection/tracking outputs against the ground truth datasets. Calculate precision, recall, F1-score, and Mean Average Precision (mAP). Assess performance for different product types and conditions.
   * **Speed (FPS):** Calculate the average frames processed per second during active CV inference. Note variation across datasets.
   * **Power Consumption:** Calculate the average power draw (Watts) and energy consumption (Watt-hours) specifically during the CV inference process. Measure idle power consumption as well for context.

### Evaluation Criteria

* **Accuracy Threshold:** Define minimum acceptable levels for precision, recall, and mAP for reliable inventory tracking (e.g., 90% mAP for target product categories).
* **Speed Requirement:** Define minimum required FPS for near real-time monitoring (e.g., 5-10 FPS during active scanning periods). Faster is better for responsiveness, but balanced against power/accuracy.
* **Power Efficiency:** Evaluate power draw (Watts) and energy consumption per inference or per unit of processing time. Models with lower power consumption for acceptable accuracy/speed are preferred, especially considering the battery runtime goal.
* **Trade-offs:** Assess the balance between accuracy, speed, and power. Identify the model configuration that best meets the minimum performance requirements while minimizing power consumption. Consider the computational load on the RPi 5 and potential for thermal throttling.
* **Model Complexity & Size:** Evaluate the disk space and memory footprint of the models, as this impacts deployment and update complexity.

The model(s) achieving the best overall balance against these criteria will be selected for integration into the system software.

## 2. Hardware Component Stress Testing Procedures

### Objective

To verify the long-term reliability, durability, and performance of critical hardware components (Battery System, Magnetic Lock, Raspberry Pi 5 Thermal Performance, Sensors) under demanding and extended operational conditions, simulating real-world usage and environmental factors.

### Battery System (Primary Focus: One-Week Runtime Validation)

* **Objective:** To validate if the chosen battery solution can power the full system (RPi 5, ESP32, cameras, modem, sensors, occasional lock/display activation) for a minimum of one week under a simulated, realistic duty cycle, and to assess charging performance and battery health degradation over time.
* **Procedure:**
  1. **Power Profiling (Prerequisite):** First, conduct detailed power profiling of the **entire** system (with selected CV models and power management firmware implemented) across various states: RPi 5 idle, RPi 5 active CV, RPi 5 deep sleep/low power, ESP32 idle/sleep, ESP32 active (sensors, communication), cellular modem active TX/RX, lock activation, display activation.
  2. **Simulate Realistic Usage:** Based on profiling and expected field use, define a 24-hour or multi-day power consumption cycle that includes periods of low activity (night), moderate activity (sensing, periodic checks), and high activity (door openings, CV scans, network communication). Example cycle: 16 hours low power, 6 hours moderate activity, 2 hours high activity including CV and communications, interspersed lock activations.
  3. **Battery Configuration:** Assemble the proposed battery pack (e.g., 18650 array with BMS) and connect it to the system's power input. Ensure all power paths (RPi 5, ESP32, peripherals) are drawing power from this battery.
  4. **Runtime Test:** Fully charge the battery. Disconnect external power (simulating no wall power/solar). Run the system through the simulated realistic usage cycle continuously. Log the battery voltage, current draw, and estimated remaining capacity over time. Record the total runtime until the system shuts down or reaches a defined low-voltage threshold. Repeat this test multiple times.
  5. **Charging Efficiency Test (with and without solar):**
     * **Wall Power:** Fully discharge the battery (to a safe level). Connect the standard wall power supply. Measure the time taken to fully recharge the battery and the total energy input vs. energy stored (efficiency).
     * **Solar Power (Optional):** If solar charging is included, conduct the runtime test again but with the solar panel connected under controlled, simulated sunlight conditions (e.g., using a solar simulator or during consistent sunny periods). Monitor battery voltage/current and solar charging current. Assess if the solar input slows down discharge or contributes to charging during the cycle. Repeat under partially cloudy conditions.
  6. **Cycle Life Testing:** Subject the battery pack to multiple charge/discharge cycles (simulating daily or weekly cycles depending on the target lifespan). Periodically measure the total capacity the battery can hold and the time it takes to discharge under a standard load to assess degradation.
* **Metrics:**
  * Actual runtime achieved per test cycle.
  * Average and peak power consumption during different operational states.
  * Total energy consumption per 24-hour simulated cycle.
  * Time to recharge from wall power/solar.
  * Charging efficiency (Energy Stored / Energy Input).
  * Battery capacity fade over charge/discharge cycles.
  * Battery voltage profiles during discharge (identifying steep drop-offs).
  * Performance of power management strategies (time spent in low-power states).

### Magnetic Lock Mechanism

* **Objective:** To test the mechanical and electrical endurance of the magnetic lock mechanism and validate the supercapacitor's ability to power the lock for a sufficient duration during main power interruptions (fail-secure operation).
* **Procedure:**
  1. **Endurance Cycling:** Set up a test rig that cycles the magnetic lock between locked and unlocked states. Simulate the physical force or mechanism (e.g., push/pull arm) that would open/close the door. Run the lock through a high number of cycles (e.g., 100,000 cycles or more) to test mechanical wear and electrical component lifespan. Monitor for failures in locking, unlocking, or excessive heat.
  2. **Holding Force Test:** Using a force gauge, measure the holding force of the magnetic lock when energized to ensure it meets specifications and can securely hold the display case door.
  3. **Fail-Secure Test with Supercapacitor:**
     * Charge the supercapacitor through the system's power circuit.
     * Energize the magnetic lock (locked state).
     * Simulate a sudden main power interruption.
     * Immediately measure the voltage across the supercapacitor and the power draw of the lock.
     * Record how long the lock remains energized and maintains sufficient holding force before disengaging (or losing significant force). Test with varying initial supercapacitor charge levels (e.g., 100%, 80%, 50%).
     * Attempt to trigger an unlock command during the supercapacitor discharge phase to verify behavior.
* **Metrics:**
  * Number of lock/unlock cycles completed before failure.
  * Reliability of engaging and disengaging the lock mechanism.
  * Maximum holding force achieved.
  * Supercapacitor hold-up time (duration the lock remains energized) under simulated power interruption.
  * Voltage decay curve of the supercapacitor during discharge with lock load.
  * Consistency of fail-secure operation across multiple tests.

### Raspberry Pi 5 Thermal Performance

* **Objective:** To ensure the Raspberry Pi 5 operates within safe temperature limits when enclosed and under sustained high load, preventing performance degradation (thermal throttling) or hardware damage across a range of potential ambient temperatures the unit might experience.
* **Procedure:**
  1. **Enclosure Simulation:** Place the RPi 5 (with its active cooler) inside a test enclosure that mimics the size and ventilation characteristics of the final VisionVend housing.
  2. **Load Generation:** Run demanding software on the RPi 5 that simulates sustained high CPU and GPU load, representative of continuous or frequent CV processing (e.g., a loop running object detection on a video stream, using stress-ng).
  3. **Temperature Monitoring:** Continuously monitor the RPi 5 CPU core temperature and the internal temperature of the enclosure using thermal sensors or software (e.g.,
     vcgencmd measure_temp
     ).
  4. **Ambient Temperature Variation:** Conduct tests at different controlled ambient temperatures:
     * Typical indoor room temperature (~20-25°C).
     * Refrigerated temperature (~4-8°C), simulating placement in a standard fridge. Note potential condensation issues.
     * Warmer temperature (~30-35°C or higher), simulating warmer outdoor conditions or less efficient cooling environments.
  5. **Sustained Load Test:** Run the high-load scenario for an extended period (e.g., several hours) at each ambient temperature to observe temperature stability and identify thermal throttling events.
* **Metrics:**
  * Maximum CPU core temperature reached.
  * Maximum internal enclosure temperature reached.
  * Frequency and severity of thermal throttling events (indicated by CPU clock speed reduction).
  * System stability during sustained load (no crashes or unexpected shutdowns).
  * Observation of condensation within the enclosure at low temperatures.

### Other Components

* **Objective:** To verify the stability and long-term performance of other critical sensors and peripherals.
* **Considerations:**
  * **Load Cells/HX711:** Long-term stability of weight readings over time and temperature fluctuations. Potential drift and need for re-calibration. Test accuracy with known weights after exposure to temperature cycles and humidity.
  * **Hall Sensors:** Durability and consistency of state detection (open/closed) over many cycles and exposure to cold/moisture.
  * **OLED Display:** Longevity and visibility in varying light conditions and temperatures.
  * **Cellular Modem:** Long-term connectivity stability and signal strength in different test locations. Power consumption consistency.
  * **Wiring and Connectors:** Verify connections remain secure under vibration (e.g., door slams) and temperature changes.

## 3. Comprehensive Field Testing Protocol

### Objective

To evaluate the overall performance, reliability, and usability of the fully assembled VisionVend retrofit kit in realistic, uncontrolled operational scenarios across diverse environments and display case types, identifying potential issues before widespread deployment.

### Scope

* **Test Sites:** Select a diverse range of real-world locations, such as:
  * Different store types (e.g., convenience store, grocery store).
  * Varied environmental conditions (indoor air-conditioned, indoor without climate control, potentially controlled outdoor placement if applicable).
  * Locations with varying cellular and Wi-Fi signal strengths.
* **Display Case Types:** Deploy units in various upright display refrigerator/freezer/ambient display units that fall within the specified dimensions (60–80" H, 24–54" W, 24–36" D). Include single-door and double-door models, and those with different shelving materials or layouts.
* **Product Variation:** Test with a wide assortment of actual products that will be stocked in these units, including items with challenging packaging (reflective, transparent, irregular shapes, similar appearances).

### Methodology

1. **Deployment:** Install the VisionVend kits into selected display cases following the Build & Installation Plan. Ensure proper mounting of cameras, sensors, lock, and main unit. Connect to power and network (Wi-Fi or Cellular).
2. **Data Collection:** Implement robust data logging on each deployed unit, automatically recording:
   * System uptime and reboots.
   * Battery level and charging status.
   * Cellular signal strength and network connectivity status.
   * Door open/close events (duration, timestamps).
   * Computer vision events (scan times, items detected, counts, confidence scores).
   * Load cell readings and derived weight changes.
   * Inferred stock levels and inventory changes.
   * Transaction initiation and success/failure status (for mock transactions).
   * System temperatures (RPi CPU, enclosure internal).
   * Error logs and system warnings.
   * Capture selected images/video clips associated with key events (e.g., door open, potential restock/removal, detection failures) for later analysis (ensure privacy compliance).
   * Supplement automated logs with manual observations (e.g., lighting conditions, customer behavior, physical condition of the unit).
3. **Test Scenarios:** Execute defined test scenarios repeatedly over the field testing period (e.g., several weeks to months per site):
   * **Item Recognition Accuracy:** Monitor the system's ability to correctly identify and count various products under normal operation. Manually verify stock levels periodically against the system's reported inventory.
   * **Inventory Tracking:** Assess the system's ability to accurately track stock changes following simulated (or real, if applicable and safe) restock events and product removals. Evaluate the system's response to items being moved within the shelf, partial removals, or multiple items taken at once.
   * **Transaction Simulation:** Conduct mock transactions to test the system's workflow from door open to item removal, payment pre-authorization (if applicable), and final stock update. Track success rates and any associated errors.
   * **Door Lock Operation:** Verify the magnetic lock reliably engages and disengages with door open/close events. Test the fail-secure mechanism during simulated power loss at the site (controlled brownouts or switching off main power briefly).
   * **Connectivity Testing:** Monitor Wi-Fi and Cellular connectivity stability. Test system behavior during brief or prolonged network outages (data buffering, re-synchronization).
   * **Battery Performance In Situ:** Track the battery discharge rate under real-world load and environmental conditions. Verify if the one-week runtime is feasible or how frequently recharging is needed. Assess solar charging performance (if implemented) under actual sunlight.
   * **Environmental Robustness:** Observe system performance and component behavior in the specific environment (e.g., condensation in refrigerators/freezers, direct sunlight exposure if outdoors, temperature fluctuations). Check sensors and electronics for signs of moisture ingress or temperature-related issues.
   * **User Interaction (if PWA is part of scope):** If the PWA is used by field testers or employees, gather feedback on usability, responsiveness, and accuracy displays.

### Key Performance Indicators (KPIs)

* **Inventory Accuracy:** Percentage of items correctly identified and counted compared to manual audits (e.g., Shelf-Level Inventory Accuracy).
* **Transaction Success Rate:** Percentage of simulated transactions successfully processed from detection to inventory update.
* **Uptime:** Percentage of time the system is operational and reporting data, excluding planned maintenance.
* **CV Performance:** Average FPS during active scans, detection/tracking accuracy metrics (precision, recall, F1-score) under field conditions.
* **Power Consumption Patterns:** Average daily/weekly power draw, effectiveness of power-saving modes, actual battery runtime.
* **Connectivity Reliability:** Percentage of time the device has stable network connectivity.
* **Error Rate:** Frequency of software errors, hardware warnings, and sensor failures reported in logs.
* **Mean Time Between Failures (MTBF):** Average operating time between system failures requiring intervention.
* **Mean Time To Repair (MTTR):** Average time taken to diagnose and resolve a reported issue.
* **User-Reported Issues:** Number and nature of issues reported by anyone interacting with the system (if applicable).

Field testing is the ultimate validation step, providing crucial data on how the VisionVend kit performs in the intended environment and identifying practical challenges related to installation, operation, and maintenance. The results from this phase will guide final product refinements and deployment strategies.
