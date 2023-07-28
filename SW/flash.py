#!/usr/bin/env python3
import sys
import os
import shutil
import re
from subprocess import check_output, CalledProcessError

spiArgs = "linux_spi:dev=/dev/spidev0.0,spispeed=4000"
flashrom = shutil.which("flashrom")


def log(logFile, data):
    try:
        with open(logFile, "a") as f:
            f.write(data)
    except Exception:
        print("Unable to log: ", data)
        pass


def scanChip(logFile):
    chip = ""
    size = 0
    # Scan for the chip
    # This may return 1, but we just want the logfile anyway
    try:
        check_output([flashrom, "-p", spiArgs, "-o", logFile, "-a"])
    except CalledProcessError:
        pass

    with open(logFile, "r") as f:
        content = f.read()
        finds = re.findall('Found.*?"(.*?)" \((\d*) kB', content)
        if len(finds) > 0:
            chip = str(finds[0][0]).strip()
            size = int(finds[0][1])
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
                [flashrom, "-p", spiArgs, "-o", logFile, "-a", "-c", chip, "-E", "-n"]
            )
        else:
            check_output(
                [
                    flashrom,
                    "-p",
                    spiArgs,
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
