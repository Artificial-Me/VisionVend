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
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Wi-Fi/LTE setup (LTE via SIM7080G)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config["wifi"]["ssid"], config["wifi"]["password"])
while not wlan.isconnected():
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
oled = SSD1306_I2C(128, 64, I2C(1, scl=Pin(config["pins"]["oled_scl"]), sda=Pin(config["pins"]["oled_sda"])))
neopixel = NeoPixel(Pin(config["pins"]["neopixel"], Pin.OUT), 1)
buzzer = Pin(config["pins"]["buzzer"], Pin.OUT)
adc = ADC(Pin(config["pins"]["battery_adc"]))
adc.atten(ADC.ATTN_11DB)
pi_signal = Pin(config["pins"]["pi_signal"], Pin.OUT)

# Feedback functions
def set_led(color):
    colors = {"green": (0, 255, 0), "blue": (0, 0, 255), "red": (255, 0, 0), "off": (0, 0, 0)}
    neopixel[0] = colors.get(color, (0, 0, 0))
    neopixel.write()

def beep(duration=0.1):
    buzzer.value(1)
    time.sleep(duration)
    buzzer.value(0)

def display_message(message):
    oled.fill(0)
    for i, line in enumerate(message.split("\n")):
        oled.text(line, 0, i * 10)
    oled.show()

# Weight measurement
def read_weight():
    samples = [hx711.read() for _ in range(10)]
    return sum(samples) / len(samples)

# Battery monitoring
def read_voltage():
    raw = adc.read()
    voltage = (raw / 4095) * 3.3 * 2
    return voltage

# MQTT callback
def on_message(topic, msg):
    payload, received_hmac = msg.decode().split("|")
    if hmac.new(config["mqtt"]["hmac_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest() == received_hmac:
        if payload.startswith("unlock:"):
            transaction_id = payload.split(":")[1]
            baseline_weight = read_weight()
            pi_signal.value(1)  # Signal Pi to start
            mosfet.value(1)  # Unlock
            display_message("Door Unlocked")
            set_led("blue")
            beep()
            start_time = time.time()
            door_was_open = False
            while time.time() - start_time < config["lock"]["timeout"]:
                if not hall_sensor.value():  # Door open
                    door_was_open = True
                elif door_was_open and hall_sensor.value():  # Door closed
                    pi_signal.value(0)  # Signal Pi to stop
                    final_weight = read_weight()
                    delta_mass = baseline_weight - final_weight
                    # Get items from Pi (simplified, assume GPIO/serial)
                    removed_items = ["cola"]  # Placeholder
                    payload = f"{transaction_id}:{','.join(removed_items) if removed_items else ''}:{delta_mass}"
                    hmac_val = hmac.new(config["mqtt"]["hmac_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
                    mqtt_client.publish(config["mqtt"]["door_topic"], f"{payload}|{hmac_val}")
                    break
                time.sleep(0.1)
            mosfet.value(0)  # Lock
            pi_signal.value(0)
            if time.time() - start_time >= config["lock"]["timeout"]:
                payload = f"{transaction_id}::0"
                hmac_val = hmac.new(config["mqtt"]["hmac_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
                mqtt_client.publish(config["mqtt"]["door_topic"], f"{payload}|{hmac_val}")
        elif topic == config["mqtt"]["status_topic"].encode():
            transaction_id, items_total = payload.split(":")
            items, total = items_total.split("$")
            if items == "No items":
                display_message("No Charge")
            else:
                display_message(f"Items: {items}\nTotal: ${total}")
            set_led("off")
            beep()

mqtt_client.set_callback(on_message)
mqtt_client.subscribe(config["mqtt"]["unlock_topic"])
mqtt_client.subscribe(config["mqtt"]["status_topic"])

# Main loop
while True:
    mqtt_client.check_msg()
    door_open = not hall_sensor.value()
    voltage = read_voltage()
    mqtt_client.publish(config["mqtt"]["status_topic"], ujson.dumps({
        "door": "open" if door_open else "closed",
        "mass": [read_weight()],
        "vcc": voltage
    }))
    display_message("Tap to Unlock")
    set_led("off")
    time.sleep(0.25)
