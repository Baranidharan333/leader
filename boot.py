import network
import webrepl
import time
from machine import Pin

SSID = "PHY_AI"
PASSWORD = "PHY_AI@IHR"

# Onboard LED (GPIO2 on most ESP32 boards)
led = Pin(2, Pin.OUT)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Set hostname
try:
    wlan.config(hostname="leader2")
    print("Hostname: leader2")
except Exception as e:
    print("Hostname Error:", e)

# Connect WiFi
wlan.connect(SSID, PASSWORD)

print("Connecting to WiFi...")

# Blink while connecting
while not wlan.isconnected():
    led.on()
    time.sleep(0.2)

    led.off()
    time.sleep(0.2)

# Connected
led.on()

print("Connected!")
print("Hostname: leader2")
print("IP:", wlan.ifconfig()[0])

# Start WebREPL
webrepl.start()

print("WebREPL Started")
print("WebREPL URL: ws://leader2.local:8266")