import spidev
import time


# Lots of inspiration and some code shamelessly taken from: https://github.com/charkster/GD25Q32C
# Thanks!


class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class flashChip:
    spi = None
    CMD_Read_Identification = 0x9F  # (MID7-M0) (JDID15-JDID8) (JDID7-JDID0)		(continuous)
    CMD_Read_Data = 0x03  # A23-A16  A15-A8   A7-A0   (D7-D0) (Next byte) (continuous)
    CMD_Read_Data_4 = 0x13  # A32-A17 A23-A16  A15-A8   A7-A0   (D7-D0) (Next byte) (continuous)

    KnownGoodIDs = [
        (0xEF, 0x6018, "Winbond", "W25Q128JW", 1.8, 20, 4 * 1024, 4096),
        (0xC2, 0x2019, "Macronix", "MX25L25645G", 3.3, 20, 4 * 1024, 4096),
    ]

    def __init__(self, spi_device=0, spi_channel=0, max_speed_hz=1000000, debug=False):  # 1MHz
        self.spi = spidev.SpiDev(spi_device, spi_channel)
        self.spi.max_speed_hz = max_speed_hz
        self.debug = debug
        self.maxTransfer = 512

    def checkPart(self):
        self.chipID = self.getDeviceID()
        for good in self.KnownGoodIDs:
            if good[0] == self.chipID[0] and good[1] == self.chipID[1]:
                self.chip = AttrDict()
                self.chip.Maker = good[2]
                self.chip.Model = good[3]
                self.chip.Voltage = good[4]
                self.chip.EraseCmd = good[5]
                self.chip.EraseSize = good[6]
                self.chip.BlockCount = good[7]
                return True
        print("Chip not found in known list. Aborting.")
        return False

    def getChip(self):
        if "chip" in self.__dict__:
            return self.chip
        return None

    def getDeviceID(self, debug=False):
        if debug or self.debug:
            print("----> manufacturer_device_id called <----")
        list_of_bytes = self.spi.xfer2([self.CMD_Read_Identification] + [0x00] * 3)
        return (list_of_bytes[1], list_of_bytes[2] << 8 | list_of_bytes[3])

    def readData(self, address=0x000000, num_bytes=1, debug=False):
        if debug or self.debug:
            print("----> read_data called <----")
            print("Address is 0x{:06x}".format(address))

        result = []
        while num_bytes > 0:
            xferBytes = num_bytes
            if xferBytes > self.maxTransfer:
                xferBytes = self.maxTransfer
            print("Reading", xferBytes, "bytes from:", hex(address))
            add_bytes_fourth = (address >> 24) & 0xFF
            add_byte_upper = (address >> 16) & 0xFF
            add_byte_mid = (address >> 8) & 0xFF
            add_byte_lower = (address) & 0xFF

            addrBytes = 3
            if address > 0xFFFFFF:
                addrBytes = 4
                list_of_bytes = self.spi.xfer2(
                    [
                        self.CMD_Read_Data_4,
                        add_bytes_fourth,
                        add_byte_upper,
                        add_byte_mid,
                        add_byte_lower,
                    ]
                    + [0x00] * xferBytes
                )
            else:
                list_of_bytes = self.spi.xfer2(
                    [self.CMD_Read_Data, add_byte_upper, add_byte_mid, add_byte_lower] + [0x00] * xferBytes
                )

            if debug or self.debug:
                print(list_of_bytes[addrBytes + 1 :])
            result.append(list_of_bytes[addrBytes + 1 :])
            num_bytes -= xferBytes
            address += xferBytes
        return result
