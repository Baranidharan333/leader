from st3215 import ST3215
import socket
import network
import time
import _thread
import struct
import sys
from machine import Pin


import network

wlan = network.WLAN(network.STA_IF)

try:
    wlan.config(hostname="leader2")
except:
    pass

print("WiFi OK" if wlan.isconnected() else "WiFi NOT connected")

if wlan.isconnected():
    print("IP:", wlan.ifconfig()[0])

# Start web server...
servo = ST3215(
    uart_id=2,
    tx_pin=17,
    rx_pin=16,
    baudrate=1000000
)

CENTER = 2048

# ==========================
# UDP TELEMETRY THREAD
# ==========================

UDP_HOST = "0.0.0.0"      # follower PC hostname or mDNS name
UDP_PORT = 5005

telemetry_host = UDP_HOST
telemetry_mode = "udp"  # "udp" or "serial"
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_addr = socket.getaddrinfo(telemetry_host, UDP_PORT)[0][-1]
servo_lock = _thread.allocate_lock()
period_us = 20000  # 50 Hz
SERVO_IDS = tuple(range(1, 17))
SERVO_COUNT = len(SERVO_IDS)
TELEMETRY_FMT = "<" + ("H" * SERVO_COUNT) + "BBB"
telemetry_stop = False

# Buttons (GPIO pins can be changed to match your wiring)
btn1 = Pin(25, Pin.IN, Pin.PULL_DOWN)
btn2 = Pin(26, Pin.IN, Pin.PULL_DOWN)
btn3 = Pin(27, Pin.IN, Pin.PULL_DOWN)

def set_telemetry_target(host, mode):
    global telemetry_host, telemetry_mode, udp_addr

    new_addr = udp_addr

    if mode == "udp":
        new_addr = socket.getaddrinfo(host, UDP_PORT)[0][-1]

    telemetry_host = host
    telemetry_mode = mode
    udp_addr = new_addr
    print("Telemetry config:", telemetry_mode, telemetry_host)

def build_binary_packet(positions, b1, b2, b3):
    values = []
    for sid in SERVO_IDS:
        pos = positions.get(sid) if positions is not None else None
        if pos is None:
            pos = 0xFFFF
        values.append(pos)

    values.append(b1)
    values.append(b2)
    values.append(b3)
    return struct.pack(TELEMETRY_FMT, *values)

def send_serial_binary(data):
    try:
        out = sys.stdout.buffer
        out.write(data)
        return
    except:
        pass

    try:
        sys.stdout.write(data)
        return
    except TypeError:
        try:
            sys.stdout.write(data.decode("latin1"))
        except Exception as e:
            print("Serial send ERROR:", e)

def stop_telemetry():
    global telemetry_stop
    telemetry_stop = True

def telemetry_task():
    global udp

    try:
        while not telemetry_stop:
            loop_start = time.ticks_us()
            servo_lock.acquire()
            try:
                try:
                    positions = servo.ReadPositions(SERVO_IDS)
                except Exception as e:
                    print("Sync read ERROR:", e)
                    positions = None
            finally:
                servo_lock.release()

            # Read button states and append to packet
            try:
                b1 = btn1.value()
                b2 = btn2.value()
                b3 = btn3.value()
            except Exception as e:
                print("Buttons read ERROR:", e)
                b1 = b2 = b3 = 0

            if telemetry_mode == "udp":
                try:
                    packet = build_binary_packet(positions, b1, b2, b3)
                    udp.sendto(packet, udp_addr)
                except Exception as e:
                    print("UDP send ERROR:", e)
            elif telemetry_mode == "serial":
                try:
                    packet = build_binary_packet(positions, b1, b2, b3)
                    send_serial_binary(packet)
                except Exception as e:
                    print("Serial send ERROR:", e)

            elapsed = time.ticks_diff(time.ticks_us(), loop_start)
            if elapsed < period_us:
                time.sleep_us(period_us - elapsed)
    finally:
        try:
            udp.close()
        except:
            pass
        print("Telemetry thread stopped")

_thread.start_new_thread(telemetry_task, ())
print("UDP thread started")

def define_middle(sts_id):
    try:
        return servo.DefineMiddle(sts_id)
    except:
        return None

html = open("index.html").read()

def render_html():
    return html.replace("__UDP_HOST__", telemetry_host).replace("__TELEMETRY_MODE__", telemetry_mode)

addr = socket.getaddrinfo("0.0.0.0",80)[0][-1]

s=socket.socket()
s.bind(addr)
s.listen(1)

print("Web Server Ready")

try:
    while True:

        cl,addr=s.accept()

        req = cl.recv(1024)

        if not req:
            cl.close()
            continue

        req = req.decode()

        try:
            line = req.split("\r\n")[0]
            path = line.split(" ")[1]
        except:
            cl.close()
            continue

        print(path)
        if path == "/favicon.ico":
            cl.send("HTTP/1.1 204 No Content\r\n\r\n")
            cl.close()
            continue
        response=render_html()

        if path.startswith("/config"):
            query = ""
            if "?" in path:
                query = path.split("?", 1)[1]

            new_host = telemetry_host
            new_mode = telemetry_mode

            for item in query.split("&"):
                if "=" not in item:
                    continue
                key, value = item.split("=", 1)
                if key == "host" and value:
                    new_host = value
                elif key == "mode" and value in ("udp", "serial"):
                    new_mode = value

            try:
                set_telemetry_target(new_host, new_mode)
                response = "Telemetry updated: {} / {}".format(telemetry_mode, telemetry_host)
            except Exception as e:
                response = "Config ERROR: {}".format(e)

        elif path=="/enableall":

            for i in range(1,17):
                try:
                    servo_lock.acquire()
                    servo.StartServo(i)
                except Exception as e:
                    print("StartServo", i, "ERROR:", e)
                finally:
                    servo_lock.release()

            response="Torque Enabled"

        elif path=="/disableall":

            for i in range(1,17):
                try:
                    servo_lock.acquire()
                    servo.StopServo(i)
                except Exception as e:
                    print("StopServo", i, "ERROR:", e)
                finally:
                    servo_lock.release()

            response="Torque Disabled"

        elif path=="/sethome":

            for i in range(1,17):
                try:
                    servo_lock.acquire()
                    define_middle(i)
                except Exception as e:
                    print("DefineMiddle", i, "ERROR:", e)
                finally:
                    servo_lock.release()

            response="Home position set for all servos"

        elif path=="/gohome":

            for i in range(1,17):
                try:
                    servo_lock.acquire()
                    servo.MoveTo(i, CENTER)
                except Exception as e:
                    print("MoveTo", i, "ERROR:", e)
                finally:
                    servo_lock.release()

            response="All servos moved home"

        if path=="/":

            cl.send("HTTP/1.1 200 OK\r\n")
            cl.send("Content-Type:text/html\r\n\r\n")
            cl.send(response)

        else:

            cl.send("HTTP/1.1 200 OK\r\n")
            cl.send("Content-Type:text/plain\r\n\r\n")
            cl.send(response)

        cl.close()
except KeyboardInterrupt:
    print("Shutting down")
finally:
    stop_telemetry()
