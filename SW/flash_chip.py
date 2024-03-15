import spidev
import time
from database import flashLogger, getconfig

# Lots of inspiration and some code shamelessly taken from: https://github.com/charkster/GD25Q32C
# Thanks!


class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class flashChip:
    spi = None
    CMD_Write_Enable = 0x06
    CMD_Write_Disable = 0x04
    CMD_Read_Status_Register_1 = 0x05  # (S7-S0)                                       (continuous)
    CMD_Read_Status_Register_2 = 0x35  # (S15-S8)                                      (continuous)
    CMD_Read_Status_Register_3 = 0x15  # (S23-S16)                                     (continuous)
    CMD_Write_Status_Register_1 = 0x01  # (S7-S0)
    CMD_Write_Status_Register_2 = 0x31  # (S15-S8)
    CMD_Write_Status_Register_3 = 0x11  # (S23-S16)
    CMD_Read_Identification = 0x9F  # (MID7-M0) (JDID15-JDID8) (JDID7-JDID0)        (continuous)
    CMD_Read_Data = 0x03  # A23-A16  A15-A8   A7-A0   (D7-D0) (Next byte) (continuous)
    CMD_Read_Data_4 = 0x13  # A31-A17 A23-A16  A15-A8   A7-A0   (D7-D0) (Next byte) (continuous)
    CMD_Sector_Erase = 0x20  # A23-A16  A15-A8   A7-A0
    CMD_Sector_Erase_4 = 0x21  # A31-A17 A23-A16  A15-A8   A7-A0
    CMD_Chip_Erase = 0x60  # <<-- command 0xC7 can also be used <<
    CMD_Page_Program = 0x02  # A23-A16  A15-A8   A7-A0   (D7-D0) (Next byte)    (continuous)
    CMD_Page_Program_4 = 0x12  # A31-A17 A23-A16  A15-A8   A7-A0   (D7-D0) (Next byte)    (continuous)
    KnownGoodIDs = [
        (0xEF, 0x6018, "Winbond", "W25Q128JW", 1.8, 20, 4 * 1024, 4096),
        (0xC2, 0x2019, "Macronix", "MX25L25645G", 3.3, 20, 4 * 1024, 4096),
    ]

    def __init__(self, spi_device=0, spi_channel=0, max_speed_hz=(1000 * 1000), debug=False):
        self.spi = spidev.SpiDev(spi_device, spi_channel)
        self.spi.max_speed_hz = max_speed_hz
        self.debug = debug
        self.maxTransfer = 2048
        self.max_speed_hz = max_speed_hz

    def getSpeed(self):
        return self.max_speed_hz

    def setSpeed(self, max_speed_hz: int):
        self.max_speed_hz = max_speed_hz
        self.spi.max_speed_hz = max_speed_hz
        return True

    def defaultSpeed(self):
        self.spi.max_speed_hz = self.max_speed_hz

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
        print("Chip not found in known list. Aborting. ID:", self.chipID)
        return False

    def getChip(self):
        if "chip" in self.__dict__:
            return self.chip
        return None

    def getDeviceID(self, debug=False):
        self.spi.max_speed_hz = 50000
        if debug or self.debug:
            print("----> manufacturer_device_id called <----")
        list_of_bytes = self.spi.xfer2([self.CMD_Read_Identification] + [0x00] * 3)
        self.defaultSpeed()
        return (list_of_bytes[1], list_of_bytes[2] << 8 | list_of_bytes[3])

    # Bit   7   6   5   4   3   2   1   0
    #     SRP0 BP4 BP3 BP2 BP1 BP0 WEL WIP
    def readStatusRegister1(self, debug=False):
        if debug or self.debug:
            print("----> read_status_register_1 called <----")
        list_of_bytes = self.spi.xfer2([self.CMD_Read_Status_Register_1, 0x00])
        return list_of_bytes[1]

    def checkWipAndWel(self, num_attempts=10, timestep=0.001, expected_status=0x00, debug=False):
        if debug or self.debug:
            print("---->check_wip_and_wel called <----")
        attempts = 50
        while attempts > 0:
            time.sleep(timestep)
            if (self.readStatusRegister1() & 0x03) == expected_status:
                break
            else:
                attempts -= 1
        if attempts == 0:
            print("ERROR WIP and WEL not at expected values after 10 attempts")
            return False
        else:
            if debug or self.debug:
                print("Number of attempts is {:d}".format(attempts))
            return True

    def readData(self, address=0x000000, num_bytes=1, debug=False):
        if debug or self.debug:
            print("----> read_data called <----")
            print("Address is 0x{:06x}".format(address))

        result = []
        while num_bytes > 0:
            xferBytes = num_bytes
            if xferBytes > self.maxTransfer:
                xferBytes = self.maxTransfer
            if debug or self.debug:
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
            result += list_of_bytes[addrBytes + 1 :]
            num_bytes -= xferBytes
            address += xferBytes
        return result

    def writeEnable(self, debug=False):
        if debug or self.debug:
            print("----> write_enable called <----")
        self.spi.xfer2([self.CMD_Write_Enable])
        if (self.readStatusRegister1() & 0x03) == 0x02:
            if debug or self.debug:
                print("SUCCESSFUL write_enable")
            return True
        else:
            print("ERROR, did not see WIP clear and WEL set from write_enable")
            return False

    def writeDisable(self, debug=False):
        if debug or self.debug:
            print("----> write_disable called <----")
        self.spi.xfer2([self.CMD_Write_Disable])
        if self.checkWipAndWel(expected_status=0x00, debug=debug):
            if debug or self.debug:
                print("SUCCESSFUL write_disable")
            return True
        else:
            print("ERROR, did not see WIP and WEL clear from write_disable")
            return False

    def sectorErase(self, address=0x000000, debug=False):
        if debug or self.debug:
            print("----> sector_erase called <----")
            print("Address is 0x{:06x}".format(address))
        self.writeEnable(debug=debug)

        add_bytes_fourth = (address >> 24) & 0xFF
        add_byte_upper = (address >> 16) & 0xFF
        add_byte_mid = (address >> 8) & 0xFF
        add_byte_lower = (address) & 0xFF

        if address > 0xFFFFFF:
            self.spi.xfer2([self.CMD_Sector_Erase_4, add_bytes_fourth, add_byte_upper, add_byte_mid, add_byte_lower])
        else:
            self.spi.xfer2([self.CMD_Sector_Erase, add_byte_upper, add_byte_mid, add_byte_lower])
        if self.checkWipAndWel(timestep=0.01, expected_status=0x00, debug=debug):
            if debug or self.debug:
                print("SUCCESSFUL sector erase")
            return True
        else:
            print("ERROR, did not see WIP and WEL clear after sector erase")
            return False

    # typical time is 7s
    def ChipErase(self, debug=False):
        if debug or self.debug:
            print("----> chip_erase called <----")
        self.writeEnable(debug=debug)
        self.spi.xfer2([self.CMD_Chip_Erase])
        if self.checkWipAndWel(timestep=2.0, expected_status=0x00, debug=debug):
            if debug or self.debug:
                print("SUCCESSFUL chip erase")
            return True
        else:
            print("ERROR, did not see WIP and WEL clear after chip erase")
            return False

    # typical time is 0.6ms
    def writeData(self, address=0x000000, page_bytes=[], debug=False):
        if debug or self.debug:
            print("----> program_page called <----")
            print("Address is 0x{:06x}".format(address))
            print(page_bytes)
        result = False
        while len(page_bytes) > 0:
            writeLen = len(page_bytes)
            if writeLen > 256:
                writeLen = 256
            writeData = list(page_bytes[0:writeLen])
            if self.writeEnable():
                add_bytes_fourth = (address >> 24) & 0xFF
                add_byte_upper = (address >> 16) & 0xFF
                add_byte_mid = (address >> 8) & 0xFF
                add_byte_lower = (address) & 0xFF
                if address > 0xFFFFFF:
                    self.spi.xfer2(
                        [self.CMD_Page_Program_4, add_bytes_fourth, add_byte_upper, add_byte_mid, add_byte_lower]
                        + writeData
                    )
                else:
                    self.spi.xfer2([self.CMD_Page_Program, add_byte_upper, add_byte_mid, add_byte_lower] + writeData)
                if self.checkWipAndWel(timestep=0.0001, expected_status=0x00, debug=debug):
                    if debug or self.debug:
                        print("SUCCESSFUL page program")
                    result = True
                else:
                    print("ERROR, did not see WIP and WEL clear after page_program")
                    result = False
                self.writeDisable()
            page_bytes = page_bytes[writeLen:]
            address += writeLen
        return result
