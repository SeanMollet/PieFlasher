from pyftdi import spi
from time import sleep


class SPIComms:
    def __init__(self, spi_device=0, spi_channel=0, max_speed_hz=(4 * 1000 * 1000), debug=False):
        self.ftdi = spi.SpiController()
        self.ftdi.configure("ftdi://ftdi:232h/" + str(spi_device + 1))
        self.spi = self.ftdi.get_port(cs=0, freq=max_speed_hz, mode=0)

        self.gpio = self.ftdi.get_gpio()
        self.gpio.set_direction(0xF0, 0xF0)
        self.set_flash_gpio()

    def selfPowered(self):
        return True

    def set_flash_gpio(self):
        self.gpio.write(0xF0)

    def clr_flash_gpio(self):
        self.gpio.write(0x0)

    def __del__(self):
        if self.ftdi:
            self.ftdi.close()

    def xfer2(self, data):
        return self.spi.exchange(data, duplex=True)

    def _set_speed(self, speed: int):
        self.spi.set_frequency(speed)

    def _get_speed(self):
        return self.spi.frequency

    def _del_speed(self):
        pass

    def get_max_xfer(self):
        return 256

    max_speed_hz = property(_get_speed, _set_speed, _del_speed, "SPI Speed")


if __name__ == "__main__":
    spi = SPIComms()
    while True:
        print("Setting GPIO")
        spi.set_flash_gpio()
        print("Current value:", hex(spi.get_gpio()))
        sleep(2)
        print("Clearing GPIO")
        spi.clr_flash_gpio()
        sleep(2)
