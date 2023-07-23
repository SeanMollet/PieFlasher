#!/usr/bin/env python3
from smbus2 import SMBus, i2c_msg
from typing import Optional
from time import sleep
from threading import Thread, Lock

mutex = Lock()

global bus
bus = SMBus(1)

class i2cPot:
    def __init__(self) -> None:
        global bus
        self.bus = bus 

        self.addr = 0x2f
        #Check if it's alive
        result = self.bus.read_byte(self.addr)
        print("Current pot value:",str(int(result))+"/127")
    
    def getPot(self) -> Optional[int]:
        with mutex:
            try:
                result = self.bus.read_byte(self.addr)
                return int(result)
            except KeyboardInterrupt:
                pass
            return None
    def setPot(self,value) -> None:
        with mutex:
            try:
                if value <0:
                    value =0
                if value > 127:
                    value = 127

                self.bus.write_byte(self.addr,value)
            except KeyboardInterrupt:
                pass

class i2cAdc:
    def __init__(self) -> None:
        global bus
        self.bus = bus 

        self.addr = 0x4d
        #Check if it's alive
    
        validate = self.getVoltage()
        if validate is not None:
            print("Voltage reading:",validate)
    
    def getVoltage(self) -> Optional[float]:
        with mutex:
            try:
                query = i2c_msg.read(self.addr,2)
                self.bus.i2c_rdwr(query)
                result = list(query)
                if len(result)==2:
                    value = (int(result[0] & 0x0f) << 6) | (int(result[1] & 0xFC) >> 2)
                    value = float(value) / 1023 * 5
                    return value
            except KeyboardInterrupt:
                pass
            return None

if __name__ == "__main__":
    print("Initializing i2c adc")
    adc = i2c_adc()

    print("Initializing i2c pot")
    pot = i2c_pot()

    from gpio import pi_gpio
    gpio = pi_gpio()

    print("Enabling power supply")
    gpio.setPsEn(True)
    sleep(.1)

    print("Current voltage:",round(adc.getVoltage(),2))

    print("Adjusting PS to minimum")
    pot.setPot(127)
    sleep(.1)

    print("Current voltage:",round(adc.getVoltage(),2))

    print("Adjusting PS to maximum")
    pot.setPot(0)
    sleep(.1)
    print("Current voltage:",round(adc.getVoltage(),2))    

    print("Adjusting PS back to minimum and disabling")
    pot.setPot(127)
    gpio.setPsEn(False)
    gpio.setPwrEn(False)



