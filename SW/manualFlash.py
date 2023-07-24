#!/usr/bin/env python3
import sys
import os
from utils import isfloat
from power import setVoltage, maxPwrControlVoltage, disablePower, enablePower
from flash import flashImage
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
if not os.path.isfile(source):
    print("Source file:", source, "not found. Aborting")
    sys.exit(1)

# Voltages above 3.4 must be controlled with PS_EN, since the FET for Output turns on automatically.
# Can't go closed loop, but that's not really an issue with a 5V chip
if voltage < maxPwrControlVoltage():
    result = setVoltage(voltage, True, True)
    if not result:
        print("Unable to set requested voltage. Aborting.")
        disablePower()
        sys.exit(1)

logFile = getLogFileName()
print("Flashing", source, "Logging to", logFile)
print("Press enter to begin")
input()
enablePower()


with open(source, "rb") as imageFile:
    data = imageFile.read()
    result = flashImage(data, logFile)
    if result:
        print("Success")
    else:
        print("Error flashing, check logfile")

loggingComplete()
disablePower()
