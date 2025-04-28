**Software Architecture**

**Edge**

* **Raspberry Pi 4** (Python 3.9+):
  * **Runs Hugging Face DETR (**facebook/detr-resnet-50**) for real-time object detection.**
  * **Records video to 32GB SD card (~24hr capacity at 720p, 30fps).**
  * **Interfaces with ESP32-S3 via GPIO for unlock/door signals.**
  * **Libraries: OpenCV, Picamera2, Transformers, Torch.**
* **ESP32-S3** (MicroPython 1.21):
  * **~400 lines: HX711 driver, MQTT (LTE), lock FSM, feedback (OLED, LED, buzzer).**
  * **OTA updates weekly via HTTPS.**
  * **JSON MQTT payloads (e.g., **{"door":"closed","mass":355.2,"vcc":3.7}**).**
* **SIM7080G**: Sends ~1KB payment confirmations via LTE.

**Cloud**

* **FastAPI Server**:
  * **Routes: **/unlock** (PWA), **/door-closed** (MQTT).**
  * **Stripe API: Payment Intent creation/modification/capture.**
  * **Web Push: Receipts to PWA.**
* **MQTT Broker**: Mosquitto, TLS 1.3, HMAC-SHA256 payloads.
* **AWS Lambda** (optional): Processes flagged snapshots for retraining.

**PWA**

* **Framework**: React, ~100KB.
* **Features**: Sign-in, Stripe setup, unlock, receipt display.
* **Web Push**: Notifies charges/no-charge status.

---

**1. Configuration (**config/config.yaml**)**

**yaml**

```yaml
# Wi-Fi and MQTT settings
wifi:
ssid:"your_wifi_ssid"
password:"your_wifi_password"
mqtt:
broker:"your_mqtt_broker_ip"
port:1883
client_id:"retail_system"
unlock_topic:"case/123/cmd"
status_topic:"case/123/status"
door_topic:"case/123/door"
hmac_secret:"your_hmac_secret"

# LTE settings
lte:
apn:"your_apn"

# Stripe API
stripe:
api_key:"sk_test_your_stripe_api_key"

# Server settings
server:
host:"0.0.0.0"
port:5000
url:"http://your_server_ip:5000"

# Camera settings
camera:
resolution:[1280,720]
framerate:30
storage_path:"/sd/videos"

# Hardware pins (ESP32-S3)
pins:
mosfet:26
hall_sensor:27
hx711_sck:14
hx711_dt:15
oled_sda:19
oled_scl:18
neopixel:23
buzzer:25
tof_sda:21
tof_scl:22
pi_signal:16

# Inventory mapping
inventory:
cola:{weight:355,tolerance:5,price:2.00}
chips:{weight:70,tolerance:4,price:1.50}

# Lock settings
lock:
timeout:10

# Feedback settings
feedback:
languages:["en","es"]
```

**2. Server Code (**server/app.py**)**

**Handles PWA unlock and payment confirmations via LTE.**

**python**

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import stripe
from paho.mqtt import client as mqtt_client
import yaml
import os
import hmac
import hashlib
import logging
from webpush import send_notification

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Enable CORS for all origins (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

stripe.api_key = config["stripe"]["api_key"]
mqtt_broker = config["mqtt"]["broker"]
mqtt_port = config["mqtt"]["port"]
mqtt_client_id = config["mqtt"]["client_id"]
unlock_topic = config["mqtt"]["unlock_topic"]
status_topic = config["mqtt"]["status_topic"]
door_topic = config["mqtt"]["door_topic"]
hmac_secret = config["mqtt"]["hmac_secret"]

mqtt = mqtt_client.Client(mqtt_client_id)
mqtt.connect(mqtt_broker, mqtt_port)

transaction_intent = {}
transaction_items = {}

class UnlockRequest(BaseModel):
    id: str = None

@app.post("/unlock")
async def unlock(request: UnlockRequest):
    transaction_id = request.id or os.urandom(16).hex()
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=100,
            currency="usd",
            payment_method_types=["card"]
        )
        transaction_intent[transaction_id] = payment_intent.id
        payload = f"unlock:{transaction_id}"
        hmac_val = hmac.new(hmac_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        mqtt.publish(unlock_topic, f"{payload}|{hmac_val}")
        return {"status": "success", "transaction_id": transaction_id}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Add other FastAPI endpoints and MQTT handling as needed
```

**3. Raspberry Pi 4 Code (**raspberry_pi/main.py**)**

**Handles local object detection and video storage.**

**python**

```python
import cv2
import picamera2
from libcamera import controls
from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
import RPi.GPIO as GPIO
import time
import yaml
import os
import logging

logging.basicConfig(level=logging.INFO)

# Load config
withopen("config/config.yaml","r")as f:
    config = yaml.safe_load(f)

# GPIO setup
PIR_PIN =17
SIGNAL_PIN =18# From ESP32
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SIGNAL_PIN, GPIO.IN)

# Camera setup
camera1 = picamera2.Picamera2(0)
camera2 = picamera2.Picamera2(1)
camera_config = camera1.create_video_configuration(
    main={"size":tuple(config["camera"]["resolution"]),"format":"RGB888"}
)
camera1.configure(camera_config)
camera2.configure(camera_config)
camera1.set_controls({"FrameRate": config["camera"]["framerate"]})
camera2.set_controls({"FrameRate": config["camera"]["framerate"]})

# ML setup
processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")
model.eval()

# Video storage
os.makedirs(config["camera"]["storage_path"], exist_ok=True)

# Detect objects
defdetect_objects(frame):
    inputs = processor(images=frame, return_tensors="pt")
    outputs = model(**inputs)
    target_sizes = torch.tensor([frame.shape[:2]])
    results = processor.post_process_object_detection(outputs, target_sizes=target_sizes)[0]
    detected_objects =[]
for score, label, box inzip(results["scores"], results["labels"], results["boxes"]):
if score >0.7and model.config.id2label[label.item()]in config["inventory"]:
            detected_objects.append(model.config.id2label[label.item()])
return detected_objects

# Main loop
defmain():
    transaction_id =None
    initial_inventory =set()
    video_writer =None
whileTrue:
if GPIO.input(PIR_PIN)or GPIO.input(SIGNAL_PIN):# Motion or unlock signal
            camera1.start()
            camera2.start()
if GPIO.input(SIGNAL_PIN):# Unlock triggered
                transaction_id =str(time.time())
                video_path =f"{config['camera']['storage_path']}/{transaction_id}.h264"
                video_writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'X264'), config["camera"]["framerate"], config["camera"]["resolution"])
                frame1 = camera1.capture_array()
                initial_inventory =set(detect_objects(frame1))
            frame1 = camera1.capture_array()
            frame2 = camera2.capture_array()
if video_writer:
                video_writer.write(frame1)# Save primary camera feed
ifnot GPIO.input(SIGNAL_PIN)and transaction_id:# Door closed
                final_inventory =set(detect_objects(frame1))
                removed_items =list(initial_inventory - final_inventory)
                video_writer.release()
                camera1.stop()
                camera2.stop()
return transaction_id, removed_items
            time.sleep(0.1)
else:
            time.sleep(0.5)

try:
whileTrue:
        transaction_id, removed_items = main()
# Signal ESP32 with results (via GPIO or serial, simplified here)
        logging.info(f"Transaction {transaction_id}: Removed {removed_items}")
except KeyboardInterrupt:
    camera1.stop()
    camera2.stop()
    GPIO.cleanup()
```

**4. ESP32-S3 Code (**esp32_s3/main.py**)**

**Controls lock, weight, feedback, and LTE.**

**python**

```python
from machine import Pin, I2C, ADC
import time
import network
import ujson
from umqtt.simple import MQTTClient
import yaml
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from hx711 import HX711
import hmac
import hashlib

# Load config
withopen("config/config.yaml","r")as f:
    config = yaml.safe_load(f)

# Wi-Fi/LTE setup (LTE via SIM7080G)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config["wifi"]["ssid"], config["wifi"]["password"])
whilenot wlan.isconnected():
    time.sleep(1)

# MQTT setup
mqtt_client = MQTTClient(config["mqtt"]["client_id"]+"_controller", config["mqtt"]["broker"], config["mqtt"]["port"])
mqtt_client.connect()

# Hardware setup
mosfet = Pin(config["pins"]["mosfet"], Pin.OUT)
hall_sensor = Pin(config["pins"]["hall_sensor"], Pin.IN, Pin.PULL_UP)
hx711_sck = Pin(config["pins"]["hx711_sck"], Pin.OUT)
hx711_dt = Pin(config["pins"]["hx711_dt"], Pin.IN)
hx711 = HX711(hx711_sck, hx711_dt)
oled = SSD1306_I2C(128,64, I2C(1, scl=Pin(config["pins"]["oled_scl"]), sda=Pin(config["pins"]["oled_sda"])))
neopixel = NeoPixel(Pin(config["pins"]["neopixel"], Pin.OUT),1)
buzzer = Pin(config["pins"]["buzzer"], Pin.OUT)
adc = ADC(Pin(config["pins"]["battery_adc"]))
adc.atten(ADC.ATTN_11DB)
pi_signal = Pin(config["pins"]["pi_signal"], Pin.OUT)

# Feedback functions
defset_led(color):
    colors ={"green":(0,255,0),"blue":(0,0,255),"red":(255,0,0),"off":(0,0,0)}
    neopixel[0]= colors.get(color,(0,0,0))
    neopixel.write()

defbeep(duration=0.1):
    buzzer.value(1)
    time.sleep(duration)
    buzzer.value(0)

defdisplay_message(message):
    oled.fill(0)
for i, line inenumerate(message.split("\n")):
        oled.text(line,0, i *10)
    oled.show()

# Weight measurement
defread_weight():
    samples =[hx711.read()for _ inrange(10)]
returnsum(samples)/len(samples)

# Battery monitoring
defread_voltage():
    raw = adc.read()
    voltage =(raw /4095)*3.3*2
return voltage

# MQTT callback
defon_message(topic, msg):
    payload, received_hmac = msg.decode().split("|")
if hmac.new(config["mqtt"]["hmac_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()== received_hmac:
if payload.startswith("unlock:"):
            transaction_id = payload.split(":")[1]
            baseline_weight = read_weight()
            pi_signal.value(1)# Signal Pi to start
            mosfet.value(1)# Unlock
            display_message("Door Unlocked")
            set_led("blue")
            beep()
            start_time = time.time()
            door_was_open =False
while time.time()- start_time < config["lock"]["timeout"]:
ifnot hall_sensor.value():# Door open
                    door_was_open =True
elif door_was_open and hall_sensor.value():# Door closed
                    pi_signal.value(0)# Signal Pi to stop
                    final_weight = read_weight()
                    delta_mass = baseline_weight - final_weight
# Get items from Pi (simplified, assume GPIO/serial)
                    removed_items =["cola"]# Placeholder
                    payload =f"{transaction_id}:{','.join(removed_items)if removed_items else''}:{delta_mass}"
                    hmac_val = hmac.new(config["mqtt"]["hmac_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
                    mqtt_client.publish(config["mqtt"]["door_topic"],f"{payload}|{hmac_val}")
break
                time.sleep(0.1)
            mosfet.value(0)# Lock
            pi_signal.value(0)
if time.time()- start_time >= config["lock"]["timeout"]:
                payload =f"{transaction_id}::0"
                hmac_val = hmac.new(config["mqtt"]["hmac_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
                mqtt_client.publish(config["mqtt"]["door_topic"],f"{payload}|{hmac_val}")
elif topic == config["mqtt"]["status_topic"].encode():
            transaction_id, items_total = payload.split(":")
            items, total = items_total.split("$")
if items =="No items":
                display_message("No Charge")
else:
                display_message(f"Items: {items}\nTotal: ${total}")
            set_led("off")
            beep()

mqtt_client.set_callback(on_message)
mqtt_client.subscribe(config["mqtt"]["unlock_topic"])
mqtt_client.subscribe(config["mqtt"]["status_topic"])

# Main loop
whileTrue:
    mqtt_client.check_msg()
    door_open =not hall_sensor.value()
    voltage = read_voltage()
    mqtt_client.publish(config["mqtt"]["status_topic"], ujson.dumps({
"door":"open"if door_open else"closed",
"mass":[read_weight()],
"vcc": voltage
}))
    display_message("Tap to Unlock")
    set_led("off")
    time.sleep(0.25)
```

**5. PWA (**pwa/index.html**)**

**Unchanged from previous, handling NFC/QR tap and payment.**

**html**

```html
<!DOCTYPEhtml>
<html>
<head>
<title>Retail Unlock</title>
<scriptsrc="https://js.stripe.com/v3/"></script>
<script>
const stripe =Stripe('pk_test_your_publishable_key');
asyncfunctionunlock(){
const response =awaitfetch('/unlock',{
method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({id:newDate().getTime().toString(16)})
});
const data =await response.json();
if(data.status ==='success'){
                document.getElementById('status').innerText ='Door Unlocked';
}else{
                document.getElementById('status').innerText ='Error: '+ data.message;
}
}
        window.onload=()=>{
if('NDEFReader'in window){
const reader =newNDEFReader();
                reader.scan().then(()=>{
                    reader.onreading=event=>{
unlock();
};
});
}
};
</script>
</head>
<body>
<h1>Tap to Unlock</h1>
<divid="status"></div>
</body>
</html>
```
