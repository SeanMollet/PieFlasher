#!/usr/bin/env python3
import sys
import os
import progressbar
from utils import isfloat
from power import setVoltage, maxPwrControlVoltage, disablePower, enablePower
from flash import flashImage, scanChip
from database import getLogFileName, loggingComplete

if len(sys.argv) < 3:
    print("Usage: manualFlash.py <Filename> <Voltage>")
    sys.exit(1)


if not isfloat(sys.argv[2]):
    print("Invalid voltage given. Aborting")
    sys.exit(1)

voltage = float(sys.argv[2])
if voltage < 1.2:
    print("Minimum voltage is 1.2v. Aborting")
    sys.exit(1)
if voltage > 5.0:
    print("Maximum voltage is 5.0v. Aborting")
    sys.exit(1)

source = sys.argv[1]
eraseMode = False
if not os.path.isfile(source) and source != "erase":
    print("Source file:", source, "not found. Aborting")
    sys.exit(1)

fileSize = 0
if source == "erase":
    eraseMode = True
else:
    fileSize = os.path.getsize(source)

# Voltages above 3.4 must be controlled with PS_EN, since the FET for Output turns on automatically.
# Can't go closed loop, but that's not really an issue with a 5V chip
if voltage < maxPwrControlVoltage():
    result = setVoltage(voltage, True, True)
    if not result:
        print("Unable to set requested voltage. Aborting.")
        disablePower()
        sys.exit(1)

if eraseMode:
    print("Erasing, press enter to begin.")
else:
    print("Flashing", source, "press enter to begin.")

input()

enablePower()

widgets = [
    progressbar.Bar("*"),
    " (",
    progressbar.AdaptiveTransferSpeed(),
    " ",
    progressbar.AdaptiveETA(),
    ") ",
]
bar = progressbar.ProgressBar(
    prefix="{variables.task}",
    variables={"task": "--"},
    max_value=fileSize,
    widgets=widgets,
).start()
logFile = getLogFileName(lambda pos, mode: bar.update(pos, task=mode))

result = None
if eraseMode:
    chip, size = scanChip(logFile)
    # Have to re-set this based on the chip size since we don't have a file
    bar.max_value = size * 1024
    result = flashImage(None, logFile, True, chip, size)
else:
    with open(source, "rb") as imageFile:
        data = imageFile.read()
        result = flashImage(data, logFile, False)
if result:
    print("Success")
else:
    print("Error performing operation, check logfile")

loggingComplete()
disablePower()
