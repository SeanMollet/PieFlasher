#!/usr/bin/env python3
import sys
import os
import shutil
import re
from utils import isfloat
from subprocess import check_output, CalledProcessError
from flash_chip import flashChip
from database import flashLogger, getconfig


class SpiFlash:

    def __init__(self, logger: flashLogger):
        self.chipComms = flashChip()
        self.validated = False
        self.chip = False
        self.logger = logger

    def CheckPart(self):
        self.validated = self.chipComms.checkPart()
        return self.validated

    def ChipID(self):
        if not self.validated:
            return False
        chip = self.chipComms.getChip()
        if chip:
            self.logger.logData("Found chip:", chip.Maker, chip.Model)
            self.chip = chip
            return chip
        else:
            print("Part not found")
            return False

    def EraseChip(self):
        if not self.validated or not self.chip:
            self.logger.logData("Chip not initialized")
            return False
        result = self.chipComms.ChipErase()
        return result

    def FlashChip(self, FlashData):
        if not self.validated or not self.chip:
            self.logger.logData("Chip not initialized")
            return False
        if len(FlashData) == 0:
            self.logger.logData("No flashdata given!")
            return False
        # Break it up into erase sector blocks
        blockCount = len(FlashData) // self.chip.EraseSize
        if (len(FlashData) % self.chip.EraseSize) > 0:
            blockCount += 1
        flashBlocks = []
        for i in range(blockCount):
            end = (i + 1) * self.chip.EraseSize
            if end > len(FlashData):
                end = len(FlashData)
            flashBlocks.append(list(FlashData[i * self.chip.EraseSize : end]))

        self.logger.logData("Split input into ", len(flashBlocks), " blocks")
        result = True
        failures = 0
        for i in range(len(flashBlocks)):
            if failures > 50:
                self.logger.logData("Error limit exceeded, aborting")
                return False
            mustFlash = False
            currentData = self.chipComms.readData(i * self.chip.EraseSize, self.chip.EraseSize)
            if len(currentData) != self.chip.EraseSize:
                mustFlash = True
            if not mustFlash:
                for j in range(len(currentData)):
                    if currentData[j] != flashBlocks[i][j]:
                        mustFlash = True
                        break
            if mustFlash:
                address = i * self.chip.EraseSize
                self.logger.logData("Erasing block:", i)
                erase = self.chipComms.sectorErase(address)
                if not erase:
                    self.logger.logData("Error erasing block:", i)
                    result = False
                    continue
                self.logger.logData("Writing block:", i)
                flash = self.chipComms.writeData(address, flashBlocks[i])
                if not flash:
                    self.logger.logData("Error flashing block:", i)
                    result = False
                    continue
                currentData = self.chipComms.readData(address, len(flashBlocks[i]))
                if len(currentData) != len(flashBlocks[i]):
                    self.logger.logData(
                        "Re-read gave a different length. Expected:", len(flashBlocks[i]), " Got:", len(currentData)
                    )
                    result = False
                for j in range(len(currentData)):
                    if currentData[j] != flashBlocks[i][j]:
                        self.logger.logData("Found mis-write in block: ", i, " Location:", j)
                        result = False
                        # Retry this block
                        i -= 1
                        failures += 1
                        break
            else:
                self.logger.logData("Skipping block:", i)
        return result


if __name__ == "__main__":
    logger = flashLogger(None, None, None, True)
    flash = SpiFlash(logger)
    if not flash.CheckPart():
        sys.exit(-1)
    chip = flash.ChipID()
    # flash.EraseChip()
    fileData = []
    with open("/home/sean/u-boot.img", mode="rb") as input:
        fileData = input.read()

    flash.FlashChip(fileData)
