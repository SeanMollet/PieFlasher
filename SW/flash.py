#!/usr/bin/env python3
import sys
import os
import shutil
import re
from utils import isfloat
from subprocess import check_output, CalledProcessError
from database import flashLogger

spiSpeeds = [
    500,
    1000,
    2000,
    4000,
    8000,
    12000,
    16000,
    20000,
    22000,
    24000,
    26000,
    28000,
    30000,
    32000,
]
currentSpiSpeed = 0
spiArgs = "linux_spi:dev=/dev/spidev0.0,spispeed={spispeed}"
flashrom = shutil.which("flashrom")


def log(logFile, data):
    try:
        with open(logFile, "a") as f:
            f.write(data)
    except Exception:
        print("Unable to log: ", data)
        pass


def resetSpeed():
    currentSpiSpeed = 0


def getSpeed():
    global currentSpiSpeed, spiSpeeds
    return str(spiSpeeds[currentSpiSpeed])


def decSpeed() -> bool:
    global currentSpiSpeed
    currentSpiSpeed -= 1
    if currentSpiSpeed < 0:
        currentSpiSpeed = 0
        return False
    return True


def incSpeed() -> bool:
    global currentSpiSpeed, spiSpeeds
    currentSpiSpeed += 1
    if currentSpiSpeed >= len(spiSpeeds):
        currentSpiSpeed = len(spiSpeeds) - 1
        return False
    return True


def getSpiArgs() -> bool:
    speed = spiSpeeds[currentSpiSpeed]
    return spiArgs.replace("{spispeed}", str(speed))


def scanChipTestSpeed(logFile: flashLogger) -> (str, int):
    global currentSpiSpeed
    # Start at the lowest
    resetSpeed()
    chip, size = scanChip(logFile)

    if len(chip) == 0 or size == 0:
        logFile.logData("Unable to detect chip at lowest speed. Aborting.")
        return ("", 0)

    # Now we know what it's supposed to be, so crank up the speed and see how it does
    newchip = chip
    newsize = size
    while newchip == chip and newsize == size and incSpeed():
        logFile.logData("Testing at speed:", getSpeed())
        newchip, newsize = scanChip(logFile)

    if newchip != chip or newsize != size:
        # Went too far
        decSpeed()
    logFile.logData("Using speed:", getSpeed())
    return (chip, size)


def scanChip(logFile: flashLogger) -> (str, int):
    chip = ""
    size = 0
    # Scan for the chip
    try:
        check_output([flashrom, "-p", getSpiArgs(), "-o", logFile.getPath(), "-a"])
    except CalledProcessError:
        pass

    content = logFile.getData()
    finds = re.findall('Found.*?"(.*?)" \((\d*) kB', content)
    if len(finds) > 0:
        # Always return the last match (since the logfile might have multiple scans)
        pos = len(finds) - 1
        chip = str(finds[pos][0]).strip()
        size = int(finds[pos][1])
    return (chip, size)


def flashImage(
    imageData, logFile: str, eraseMode: bool = False, chip: str = "", size: int = 0
) -> bool:
    if flashrom is None:
        log(logFile, "Flashrom not found. Aborting")
        return False
    if len(chip) == 0 or size == 0:
        chip, size = scanChip(logFile)

    if len(chip) == 0 or size == 0:
        print("No chip found or unable to read size, aborting.")
        return False

    # print("Using chip:",chip)

    try:
        if eraseMode:
            check_output(
                [
                    flashrom,
                    "-p",
                    getSpiArgs(),
                    "-o",
                    logFile,
                    "-a",
                    "-c",
                    chip,
                    "-E",
                    "-n",
                ]
            )
        else:
            check_output(
                [
                    flashrom,
                    "-p",
                    getSpiArgs(),
                    "-o",
                    logFile,
                    "-a",
                    "-c",
                    chip,
                    "-w",
                    "-",
                ],
                input=imageData,
            )
        return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or not (isfloat(sys.argv[1])):
        print("Identify attached chip and test SPI speeds")
        print("Usage: ./flash.py <voltage>")
        sys.exit(1)
    voltage = float(sys.argv[1])
    print("Using: " + str(voltage) + "V")
    import power
    from database import flashLogger

    logFile = flashLogger(None)

    result = power.setVoltage(voltage, True, True)
    if not result:
        print("Unable to set requested voltage. Aborting.")
        power.disablePower()
        sys.exit(1)
    power.enablePower()
    chip, size = scanChipTestSpeed(logFile)
    if len(chip) > 0:
        print("Found chip:", chip, "speed:", getSpeed())
    power.disablePower()
    logFile.shutdownLogging()
