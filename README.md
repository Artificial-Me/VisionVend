![Logo](assets/logo.png)

# VisionVend
Smart Vending 


### Key Points
- Research suggests object detection models can track products removed from vending machines, with high accuracy (up to 99.15% in some studies).
- It seems likely that Stripe integration can automate debit/credit card, NFC, and RFID payments, ensuring secure transactions after product detection.
- The evidence leans toward 5G SIM cards providing reliable data connections for real-time communication with your HQ server.
- Implementation may involve challenges like model training, payment security, and connectivity, requiring thorough testing.

#### Project and Task List Overview
Building a smart vending machine prototype involves several steps, from designing the enclosure to integrating hardware and software. Below is a simplified breakdown to help you map out every aspect, including a hardware list with purchase links.

#### Hardware List
Here’s the list of components needed, with links to purchase them:

| Component                  | Description                                   | Link                                                                 |
|--------------------------------|---------------------------------------------------|--------------------------------------------------------------------------|
| Raspberry Pi 4 Model B         | Main processing unit for the vending machine.    | Raspberry Pi 4 Model B |
| Raspberry Pi Camera Module V2  | For capturing video for object detection.        | Raspberry Pi Camera Module V2 |
| Sixfab 5G Development Kit      | Provides 5G connectivity via USB.                | Sixfab 5G Development Kit |
| Stripe Reader S700             | Bluetooth payment reader for contactless payments.| Stripe Reader S700              |
| 12V DC Solenoid Lock           | For locking/unlocking the vending machine door.  | 12V DC Solenoid Lock |
| 4-Channel 5V Relay Module      | To control the solenoid lock with Raspberry Pi.  | 4-Channel Relay Module |
| 7" HDMI Touchscreen (Optional) | For user interface and interaction.              | 7" HDMI Touchscreen |
| Power Supply for Raspberry Pi  | To power the Raspberry Pi.                       | Raspberry Pi Power Supply |
| Wooden or MDF Cabinet          | Enclosure for the vending machine.               | Available at local hardware stores or online (e.g., IKEA or Amazon).    |

#### Project Tasks
Follow these steps to build your prototype:

1. Design and Build Enclosure: Decide on size, source materials like wood or MDF, cut and assemble, and install a door with a solenoid lock.
2. Set Up Raspberry Pi: Install Raspberry Pi OS, configure Wi-Fi or 5G connectivity, and install software like GStreamer for video streaming.
3. Integrate Camera: Connect the camera, configure settings, and set up streaming to your server.
4. Integrate Payment Reader: Pair the Stripe Reader S700 via Bluetooth, set up Stripe’s SDK, and develop the payment flow.
5. Integrate Locking Mechanism: Connect a relay module to control the solenoid lock based on server commands.
6. Set Up Display (Optional): Add a touchscreen for user interaction, showing payment status.
7. Set Up Connectivity: Insert the 5G SIM card, configure the modem, and test internet connection.
8. Develop Server-Side Software: Set up your server for video processing, object detection, Stripe integration, and command sending.
9. Testing: Test video streaming, payment processing, and locking mechanism functionality.
10. Integration and Deployment: Assemble all components, ensure seamless operation, and test with users.

This plan covers all aspects, ensuring you can build and test your prototype effectively.

---

### Comprehensive Implementation of Smart Vending Machine Prototype

This note provides a detailed overview of building a smart vending machine prototype, where the vending machine serves as a point of interaction, with all computational workload (including machine learning and AI for object detection) handled remotely on a server. The system will lock or unlock based on payment acceptance via debit/credit card, NFC, or RFID, and customers will only be charged if they remove a product, with communication facilitated by a 5G SIM card. The discussion is informed by recent research and industry practices, ensuring a thorough understanding for technical and business stakeholders.

#### Background and Context
The concept of smart vending machines has evolved significantly, driven by advancements in artificial intelligence, payment processing, and connectivity. The system described involves offloading all computational tasks to a remote server, with the vending machine acting as a simple interface for customer interaction and physical control (locking/unlocking). Customers will be charged only if they remove a product, aligning with trends in automated retail where convenience, security, and real-time management are paramount.

#### System Architecture and Components

##### Vending Machine Hardware
The vending machine needs the following hardware components, based on research and available DIY projects:
- Raspberry Pi 4 Model B: Chosen for its processing power and connectivity options, including built-in Wi-Fi and Bluetooth, suitable for streaming video and handling payment processing. Raspberry Pi 4 Model B.
- Raspberry Pi Camera Module V2: For capturing video for object detection, designed specifically for Raspberry Pi, providing clear images for streaming. Raspberry Pi Camera Module V2.
- Sixfab 5G Development Kit: Provides 5G connectivity via USB, ensuring low-latency, high-speed communication with the server. This kit includes a modem, antenna, and enclosure, compatible with Raspberry Pi. Sixfab 5G Development Kit.
- Stripe Reader S700: A Bluetooth payment reader for accepting contactless payments (debit/credit cards, NFC, RFID), compatible with Raspberry Pi via Bluetooth. Stripe Reader S700.
- 12V DC Solenoid Lock: For locking/unlocking the vending machine door, controlled via a relay module. 12V DC Solenoid Lock.
- 4-Channel 5V Relay Module: To control the solenoid lock with Raspberry Pi’s GPIO, ensuring safe switching of 12V power. 4-Channel Relay Module.
- 7" HDMI Touchscreen (Optional): For user interface, showing payment status and product information, enhancing user experience. 7" HDMI Touchscreen.
- Power Supply for Raspberry Pi: Official power supply to ensure reliable operation. Raspberry Pi Power Supply.
- Wooden or MDF Cabinet: Enclosure for the vending machine, custom-built for the prototype, ensuring space for all components and a door for product access. Available at local hardware stores or online (e.g., IKEA or Amazon).

##### Remote Server Setup
The server will handle all computational workload, including:
- Object Detection: Using a model like YOLO (You Only Look Once), known for its speed and accuracy in real-time object detection. Research from ResearchGate (Fast Detection of Objects Using a YOLOv3 Network for a Vending Machine | Request PDF) shows YOLOv3 achieving high accuracy for vending machine applications, while a 2024 IEEE paper (BP-YOLO: A Real-Time Product Detection and Shopping Behaviors Recognition Model for Intelligent Unmanned Vending Machine | IEEE Journals & Magazine) introduces BP-YOLO, integrating optimized YOLOv7 for complex scenarios. The model must be trained on images of specific products, potentially using datasets like those from the Frontiers paper (Frontiers | Research on Product Detection and Recognition Methods for Intelligent Vending Machines), which used Faster R-CNN and achieved good performance.
- Payment Processing: Integration with Stripe for handling payment authorization and capture. Stripe’s API supports authorizing payments first (reserving funds) and capturing later, aligning with the requirement to charge only after product removal. Stripe Payments | Features and Process.
- Communication: Receiving video feeds from the vending machine via 5G, processing them for object detection, and sending commands back (e.g., to lock or unlock). The server must handle multiple vending machines, ensuring scalability.
- Database: To store transaction data, inventory levels, and machine status for remote management, similar to systems like Vending on Track (Vending on Track), which uses Amazon AWS for robust cloud management.

#### Workflow and Payment Flow
The system operates as follows, ensuring customers are only charged if they remove a product:

1. Customer Initiates Transaction:
   - The customer presents their payment method (debit/credit card, NFC, or RFID) to the Stripe Reader S700.
   - The vending machine sends the payment details to the server via the 5G connection.

2. Payment Authorization:
   - The server authorizes the payment with Stripe for a specific amount (e.g., the cost of the product or a maximum amount). This reserves the funds but does not charge yet.
   - If authorization is successful, the server sends a command to the vending machine to unlock the solenoid lock.

3. Product Removal Detection:
   - The customer takes a product from the machine.
   - The camera captures video, which is streamed to the server in real-time.
   - The server runs the object detection model (e.g., YOLO) on the video feed to detect when a product is removed. Research suggests models like YOLOv3-TinyE can achieve up to 99.15% accuracy, as noted in a 2021 ResearchGate paper (A Design of Smart Unmanned Vending Machine for New Retail Based on Binocular Camera and Machine Vision).

4. Payment Capture:
   - Upon detection of product removal, the server captures the payment with Stripe for the exact amount of the taken product.
   - If the customer does not remove any product within a timeout period (e.g., 30 seconds), the server voids the authorization, ensuring no charge is made.

5. Locking Mechanism:
   - After the transaction is complete (or if no product is taken), the server can send a command to relock the vending machine, preparing it for the next customer.

This flow ensures that customers are only charged if they remove a product, aligning with the user’s requirement.

#### Performance Metrics and Comparison
To illustrate the technical differences, here’s a table comparing object detection approaches discussed:

| Model/System | Camera Setup       | Accuracy (mAP) | Inference Speed (ms/FPS) | Model Size (MB) | Training Data       |
|-------------------|-----------------------|--------------------|------------------------------|---------------------|-------------------------|
| YOLOv3-TinyE      | Binocular             | 99.15%             | 10.3 ms (fast)               | 80.3                | 18,000 images, 20 types |
| Abto Software     | Single Camera         | 87% (average)      | 13 FPS (real-time)           | Not specified       | Two 30s videos/class    |
| Faster R-CNN      | Not specified         | Good (varies)      | Slower than YOLO             | Larger              | Retail Product Checkout dataset |

This table highlights trade-offs between accuracy, speed, and hardware complexity, aiding in system design decisions.

#### Project Task List
The following detailed task list maps out every aspect of building the prototype, ensuring all hardware and software components are integrated:

1. Design and Build the Enclosure:
   - Determine dimensions based on product size and quantity (e.g., 4-6 products).
   - Source materials (wood, MDF, etc.) from local hardware stores or online (e.g., IKEA or Amazon).
   - Cut and assemble the cabinet, ensuring space for components.
   - Install a door with the solenoid lock mechanism, ensuring secure access.

2. Set Up Raspberry Pi:
   - Install Raspberry Pi OS, ensuring the latest version for compatibility.
   - Configure Wi-Fi or set up cellular connectivity using the Sixfab 5G Development Kit.
   - Install necessary software packages, including GStreamer for video streaming, FFmpeg for video processing, and the Stripe Terminal JavaScript SDK for payment processing.

3. Integrate Camera:
   - Connect the Raspberry Pi Camera Module V2 to the Raspberry Pi’s camera port.
   - Configure camera settings for optimal resolution and frame rate.
   - Set up video streaming to the server using GStreamer or FFmpeg, ensuring real-time transmission.

4. Integrate Payment Reader:
   - Pair the Stripe Reader S700 with the Raspberry Pi via Bluetooth, ensuring a stable connection.
   - Set up the Stripe Terminal JavaScript SDK on the Raspberry Pi, running a web server to handle payment processing.
   - Develop the payment flow: authorize payment when the card is inserted, capture when the server detects product removal.

5. Integrate Locking Mechanism:
   - Connect the 4-channel relay module to the Raspberry Pi’s GPIO pins, ensuring compatibility with 3.3V logic.
   - Connect the 12V DC solenoid lock to the relay module, ensuring safe power switching.
   - Write code on the Raspberry Pi to control the lock based on commands received from the server (e.g., unlock on payment authorization, lock after transaction).

6. Set Up Display (Optional):
   - Connect the 7" HDMI touchscreen to the Raspberry Pi, ensuring proper display settings.
   - Develop a user interface using Python or JavaScript to show payment status, product selection, and error messages, enhancing user experience.

7. Set Up Connectivity:
   - Insert a 5G SIM card into the Sixfab 5G Development Kit, ensuring it’s activated with a data plan.
   - Configure the modem to connect to the internet, following the manufacturer’s instructions.
   - Test connectivity to ensure reliable data transmission, especially for video streaming and command execution.

8. Develop Server-Side Software:
   - Set up a server (e.g., on AWS, Google Cloud, or local server) to receive the video stream from the Raspberry Pi.
   - Implement object detection using a model like YOLO, trained on images of your products, to detect when a product is removed.
   - Integrate with the Stripe API for payment processing, using the Payment Intents API to authorize and capture payments.
   - Send commands to the Raspberry Pi to lock/unlock the solenoid based on payment status and object detection results.

9. Testing:
   - Test video streaming and object detection accuracy, ensuring the server can detect product removal reliably.
   - Test payment processing with test cards provided by Stripe, verifying authorization and capture workflows.
   - Test the locking mechanism to ensure it locks and unlocks correctly based on server commands, simulating various scenarios.

10. Integration and Deployment:
    - Assemble all components into the enclosure, ensuring secure mounting and wiring.
    - Ensure all systems (camera, payment, lock, connectivity) work together seamlessly, testing end-to-end functionality.
    - Conduct final testing with simulated or real users, gathering feedback for improvements.

#### Challenges and Considerations
Implementation may face challenges, such as:
- Object Detection Accuracy: Ensuring the model can handle various lighting conditions, occlusions, and product diversity. Training on a robust dataset is crucial, as noted in the Frontiers paper, where AP (Small Area) and AP (Medium Area) performed poorly due to dataset limitations.
- Latency: Real-time video streaming and processing require low latency, especially for unlocking the machine after payment authorization. The 5G SIM card helps, but network disruptions must be handled by storing data locally and syncing later.
- Payment Security: Ensuring secure payment processing, which Stripe addresses with encryption and fraud detection tools like Radar. However, the system must protect against unauthorized access or tampering.
- Edge Cases: Handling scenarios like customers taking and putting back products (difficult to detect with object detection alone), network failures during critical steps, or incorrect detections. Testing is essential to mitigate these risks.

#### Scalability and User Experience
The system should be scalable to handle multiple vending machines, with the server managing concurrent video feeds and transactions. User experience can be enhanced with a touchscreen interface, allowing customers to see detected products and payment status, similar to systems described by HealthyYOU Vending (HealthyYOU Vending Machine Features).

#### Conclusion
Implementing a smart vending machine prototype with remote object detection, Stripe payment integration, and 5G connectivity is feasible, leveraging existing technologies and research. By combining high-accuracy object detection models, secure payment processing, and reliable connectivity, you can create a seamless, automated retail experience. Thorough testing and planning for challenges will ensure success, positioning your system as a leader in smart retail innovation.

---

### Key Citations
- Raspberry Pi 4 Model B Official Product Page
- Raspberry Pi Camera Module V2 Official Product Page
- Sixfab 5G Development Kit for Raspberry Pi
- Stripe Terminal Hardware Selection
- 12V DC Solenoid Lock on Amazon
- 4-Channel Relay Module on Amazon
- 7" HDMI Touchscreen for Raspberry Pi on Amazon
- Raspberry Pi Official Power Supply
- Fast Detection of Objects Using a YOLOv3 Network for a Vending Machine
- BP-YOLO: A Real-Time Product Detection and Shopping Behaviors Recognition Model for Intelligent Unmanned Vending Machine
- Research on Product Detection and Recognition Methods for Intelligent Vending Machines
- A Design of Smart Unmanned Vending Machine for New Retail Based on Binocular Camera and Machine Vision
- Stripe Payments Features and Process
- Vending on Track Cloud Management System
- HealthyYOU Vending Machine Features
