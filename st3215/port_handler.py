from machine import UART
import time

from .values import *


class PortHandler:

    def __init__(
        self,
        uart_id=2,
        tx_pin=17,
        rx_pin=16,
        baudrate=DEFAULT_BAUDRATE
    ):
        self.is_open = False
        self.baudrate = baudrate

        self.packet_start_time = 0
        self.packet_timeout = 0
        self.tx_time_per_byte = 0

        self.is_using = False

        self.uart_id = uart_id
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin

        self.uart = None

    def openPort(self):
        return self.setupPort()

    def closePort(self):
        if self.uart:
            self.uart.deinit()
            self.uart = None

        self.is_open = False

    def clearPort(self):
        if self.uart:
            while self.uart.any():
                self.uart.read()

    def setPortName(self, port_name):
        pass

    def getPortName(self):
        return "UART{}".format(self.uart_id)

    def getBaudRate(self):
        return self.baudrate

    def getBytesAvailable(self):
        if self.uart:
            return self.uart.any()
        return 0

    def readPort(self, length):
        if not self.uart:
            return []

        data = self.uart.read(length)

        if data is None:
            return []

        return list(data)

    def writePort(self, packet):
        if not self.uart:
            return 0

        return self.uart.write(bytes(packet))

    def setPacketTimeout(self, packet_length):
        self.packet_start_time = self.getCurrentTime()

        self.packet_timeout = (
            (self.tx_time_per_byte * packet_length)
            + (self.tx_time_per_byte * 3)
            + LATENCY_TIMER
        )

    def setPacketTimeoutMillis(self, msec):
        self.packet_start_time = self.getCurrentTime()
        self.packet_timeout = msec

    def isPacketTimeout(self):
        if self.getTimeSinceStart() > self.packet_timeout:
            self.packet_timeout = 0
            return True

        return False

    def getCurrentTime(self):
        return time.ticks_ms()

    def getTimeSinceStart(self):
        return time.ticks_diff(
            time.ticks_ms(),
            self.packet_start_time
        )

    def setupPort(self):

        if self.is_open:
            self.closePort()

        self.uart = UART(
            self.uart_id,
            baudrate=self.baudrate,
            bits=8,
            parity=None,
            stop=1,
            tx=self.tx_pin,
            rx=self.rx_pin,
            timeout=20
        )

        self.is_open = True

        self.clearPort()

        self.tx_time_per_byte = (
            (1000.0 / self.baudrate) * 10.0
        )

        return True