#!/usr/bin/env python3
import sys
import os
import shutil
import re
from utils import isfloat
from subprocess import check_output, CalledProcessError
from database import flashLogger
from flash_chip import flashChip


class SpiFlash:

    def __init__(self):
        self.chipComms = flashChip()
        self.validated = False

    def CheckPart(self):
        self.validated = self.chipComms.checkPart()
        return self.validated

    def ChipID(self):
        if not self.validated:
            return False
        chip = self.chipComms.getChip()
        if chip:
            return chip
        else:
            print("Part not found")
            return False

    def FlashChip(self):
        if not self.validated:
            return False
        data = self.chipComms.readData(0x0, 256 * 1024)


if __name__ == "__main__":
    flash = SpiFlash()
    if not flash.CheckPart():
        sys.exit(-1)
    chip = flash.ChipID()
    print("Found:", chip.Maker, chip.Model)
    flash.FlashChip()
