import os
import json
from pathlib import Path
SIM = os.getenv("SIMULATE", "0") == "1"

if SIM:
    # ───── fake hardware ─────
    from VisionVend.raspberry_pi.mock_hw import DummyPin as Pin, DummyADC as ADC, DummyHX711 as HX711
    import cv2                                     # we will use your laptop webcam
    GPIO = type("GPIO", (), {"input":lambda *_:0, "setup":lambda *_:None,
                             "setmode":lambda *_:None, "BCM":None, "cleanup":lambda :None,
                             "IN": 0, "OUT": 1, "PUD_UP": 0})
    
    # Stub for picamera2
    class Picamera2:
        def __init__(self, *args, **kwargs): pass
        def create_video_configuration(self, **kwargs): return {}
        def configure(self, *args, **kwargs): pass
        def set_controls(self, *args, **kwargs): pass
    
    camera1 = cv2.VideoCapture(0)
    camera2 = cv2.VideoCapture(0)                  # same cam twice is fine for logic tests
    
    # Stub for libcamera
    class controls:
        pass

else:
    # ───── real Pi imports ─────
    import cv2
    import picamera2
    from libcamera import controls
    from transformers import DetrImageProcessor, DetrForObjectDetection
    import torch
    import RPi.GPIO as GPIO

import time
import yaml
import logging

logging.basicConfig(level=logging.INFO)

# Load config
CONFIG_FILE_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(CONFIG_FILE_PATH, "r") as f:
    config = yaml.safe_load(f)

# GPIO setup
PIR_PIN = 17
SIGNAL_PIN = 18  # From ESP32
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SIGNAL_PIN, GPIO.IN)

# Camera setup (for normal operation)
camera1 = picamera2.Picamera2(0)
camera2 = picamera2.Picamera2(1)
camera_config = camera1.create_video_configuration(
    main={"size": tuple(config["camera"]["resolution"]), "format": "RGB888"}
)
camera1.configure(camera_config)
camera2.configure(camera_config)
camera1.set_controls({"FrameRate": config["camera"]["framerate"]})
camera2.set_controls({"FrameRate": config["camera"]["framerate"]})

# --- Auto-labeling (dual-cam, async) ---
import asyncio
from VisionVend.raspberry_pi.capture import capture_frames
from VisionVend.raspberry_pi.tracker import track_and_save

RESTOCK_PIN = config["training"]["autolabel"]["restock_pin"]
LED_PIN = config["training"]["autolabel"]["led_pin"]
LED_GREEN = tuple(config["training"]["autolabel"]["led_green"])
LED_RED = tuple(config["training"]["autolabel"]["led_red"])
CAM_IDS = config["training"]["autolabel"]["cam_ids"]
TIMEOUT = config["training"]["autolabel"]["timeout_sec"]

GPIO.setup(RESTOCK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

# Helper: Set RGB LED (assuming simple GPIO or PWM control)
def set_led(color):
    # Dummy implementation: replace with actual RGB LED logic
    # For now, just print
    print(f"LED set to: {color}")

async def autolabel_workflow(sku):
    set_led((0,0,255))  # Blue: in progress
    stop_event = asyncio.Event()
    frame_queues = [asyncio.Queue() for _ in CAM_IDS]
    log_queue = asyncio.Queue()
    tasks = []
    
    for i, cam_id in enumerate(CAM_IDS):
        tasks.append(asyncio.create_task(capture_frames(cam_id, frame_queues[i], stop_event, log_queue)))
        tasks.append(asyncio.create_task(track_and_save(cam_id, frame_queues[i], stop_event, sku, log_queue)))
    
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=TIMEOUT)
        set_led(LED_GREEN)
        print("Auto-label success!")
        return True
    except asyncio.TimeoutError:
        stop_event.set()
        set_led(LED_RED)
        print("Auto-label timed out.")
        return False
    finally:
        # Proper cleanup
        for task in tasks:
            task.cancel()


# ML setup
processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")
model.eval()

# Video storage
os.makedirs(config["camera"]["storage_path"], exist_ok=True)

# Detect objects
def detect_objects(frame):
    inputs = processor(images=frame, return_tensors="pt")
    outputs = model(**inputs)
    target_sizes = torch.tensor([frame.shape[:2]])
    results = processor.post_process_object_detection(outputs, target_sizes=target_sizes)[0]
    detected_objects = []
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        if score > 0.7 and model.config.id2label[label.item()] in config["inventory"]:
            detected_objects.append(model.config.id2label[label.item()])
    return detected_objects

# Main loop
def main():
    transaction_id = None
    initial_inventory = set()
    video_writer = None
    while True:
        if GPIO.input(PIR_PIN) or GPIO.input(SIGNAL_PIN):  # Motion or unlock signal
            camera1.start()
            camera2.start()
            if GPIO.input(SIGNAL_PIN):  # Unlock triggered
                transaction_id = str(time.time())
                video_path = f"{config['camera']['storage_path']}/{transaction_id}.h264"
                video_writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'X264'), 
                                              config["camera"]["framerate"], config["camera"]["resolution"])
                frame1 = camera1.capture_array()
                initial_inventory = set(detect_objects(frame1))
            frame1 = camera1.capture_array()
            frame2 = camera2.capture_array()
            if video_writer:
                video_writer.write(frame1)  # Save primary camera feed
            if not GPIO.input(SIGNAL_PIN) and transaction_id:  # Door closed
                final_inventory = set(detect_objects(frame1))
                removed_items = list(initial_inventory - final_inventory)
                video_writer.release()
                camera1.stop()
                camera2.stop()
                return transaction_id, removed_items
            time.sleep(0.1)
        else:
            time.sleep(0.5)

try:
    while True:
        transaction_id, removed_items = main()
        # Signal ESP32 with results (via GPIO or serial, simplified here)
        logging.info(f"Transaction {transaction_id}: Removed {removed_items}")
except KeyboardInterrupt:
    camera1.stop()
    camera2.stop()
    GPIO.cleanup()
