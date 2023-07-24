#!/usr/bin/env python3
from smbus2 import SMBus, i2c_msg
from typing import Optional, Callable
from time import sleep
from threading import Thread, Lock

mutex = Lock()

global bus
bus = SMBus(1)


class i2cPot:
    def __init__(self) -> None:
        global bus
        self.bus = bus

        self.addr = 0x2F
        # Check if it's alive
        result = self.bus.read_byte(self.addr)
        print("Current pot value:", str(int(result)) + "/127")

    def getPot(self) -> Optional[int]:
        with mutex:
            try:
                result = self.bus.read_byte(self.addr)
                return int(result)
            except Exception:
                pass
            return None

    def setPot(self, value) -> bool:
        with mutex:
            try:
                if value < 0:
                    value = 0
                if value > 127:
                    value = 127

                self.bus.write_byte(self.addr, value)
                return True
            except Exception:
                pass
        return False


class i2cAdc:
    def __init__(self) -> None:
        global bus
        self.bus = bus

        self.addr = 0x4D
        # Check if it's alive

        validate = self.getVoltage()
        if validate is not None:
            print("Voltage reading:", round(validate, 2))

    def getVoltage(self) -> Optional[float]:
        with mutex:
            try:
                query = i2c_msg.read(self.addr, 2)
                self.bus.i2c_rdwr(query)
                result = list(query)
                if len(result) == 2:
                    value = (int(result[0] & 0x0F) << 6) | (int(result[1] & 0xFC) >> 2)
                    value = float(value) / 1023 * 5
                    return value
            except Exception:
                pass
            return None


# Provides a way to call a lambda while locking on the i2c mutex
# Handy for calling the display function from outside of here
def lockI2C(callFunc: Callable):
    with mutex:
        callFunc()


if __name__ == "__main__":
    print("Initializing i2c adc")
    adc = i2cAdc()

    print("Initializing i2c pot")
    pot = i2cPot()
