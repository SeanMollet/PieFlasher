import spidev


class SPIComms:
    def __init__(self, spi_device=0, spi_channel=0, max_speed_hz=(1000 * 1000), debug=False):
        self.spi = spidev.SpiDev(spi_device, spi_channel)
        self.spi.max_speed_hz = max_speed_hz

    def selfPowered(self):
        return False

    def xfer2(self, data):
        return self.spi.xfer2(data)

    def _set_speed(self, speed: int):
        self.spi.max_speed_hz = speed

    def _get_speed(self):
        return self.spi.max_speed_hz

    def _del_speed(self):
        pass

    def get_max_xfer(self):
        return 2048

    max_speed_hz = property(_get_speed, _set_speed, _del_speed, "SPI Speed")
