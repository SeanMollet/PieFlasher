#!/usr/bin/env python3
from i2c import i2cAdc, i2cPot
from gpio import pi_gpio
from time import sleep
import sys
from utils import isfloat
from database import flashLogger

gpio = pi_gpio()
adc = i2cAdc()
pot = i2cPot()

voltageAccuracyThreshold = 0.05


def maxPwrControlVoltage():
    return 3.4


def getPotForVoltage(target):
    FirstUsefulValue = 45
    Slope = 0.045977678
    return int((5 - target) / (Slope)) + FirstUsefulValue


# If your voltages aren't quite accurate, run this, delete the first rows that are all 5v
# Paste the rest into the excel sheet and update the slope and firstusefulvalue above
def calibrate():
    potRange = 127
    tests = []
    gpio.setPsEn(True)
    for x in range(5):
        print("Calibrating round", x, "of 5")
        test = {}
        for i in range(potRange):
            pot.setPot(i)
            sleep(0.1)
            test[i] = round(adc.getVoltage(), 2)
        tests.append(test)
    gpio.setPsEn(False)
    for i in range(potRange):
        avg = tests[0][i] + tests[1][i] + tests[2][i] + tests[3][i] + tests[4][i]
        avg = round(avg / 5, 2)
        print(i, avg, tests[0][i], tests[1][i], tests[2][i], tests[3][i], tests[4][i])


# Verify our voltage settings
def checkPS():
    gpio.setPsEn(True)
    gpio.setPwrEn(False)

    print("Power supply accuracy test")
    targets = [1.3, 1.6, 1.8, 2.0, 2.4, 2.8, 3.0, 3.1, 3.3, 3.6, 4.0]

    for target in targets:
        potValue = getPotForVoltage(target)
        pot.setPot(potValue)
        sleep(0.1)
        voltage = round(adc.getVoltage(), 2)
        print("Target:", target, "Act:", voltage, end="")
        if (
            target * (1 - voltageAccuracyThreshold)
            <= voltage
            <= target * (1 + voltageAccuracyThreshold)
        ):
            print(" OK")
        else:
            print(" Failed")

    gpio.setPsEn(False)


# Set the pot for a specific voltage
def setVoltage(
    target: float,
    validate: bool = True,
    output: bool = False,
    logger: flashLogger = None,
) -> bool:
    # Set the voltage to minimum and disable output before we turn it on
    if validate and target <= maxPwrControlVoltage():
        result = pot.setPot(127)
        gpio.setPwrEn(False)
        gpio.setPsEn(True)
        sleep(0.05)

    potValue = getPotForVoltage(target)
    result = pot.setPot(potValue)
    if not result:
        return False
    sleep(0.25)
    if validate and target <= maxPwrControlVoltage():
        voltage = round(adc.getVoltage(), 2)
        if output:
            if logger:
                logger.logData("Voltage:", voltage)
            else:
                print("Voltage:", voltage)
        if (
            target * (1 - voltageAccuracyThreshold)
            <= voltage
            <= target * (1 + voltageAccuracyThreshold)
        ):
            return True
        if logger:
            logger.logData(
                "Voltage inaccurate! Check calibration. Target:",
                target,
                "Actual:",
                voltage,
            )
        else:
            print(
                "Voltage inaccurate! Check calibration. Target:",
                target,
                "Actual:",
                voltage,
            )
        return False
    return True


def disablePower():
    gpio.setPwrEn(False)
    gpio.setPsEn(False)


def enablePower(logFile: flashLogger = None):
    gpio.setPsEn(True)
    gpio.setPwrEn(True)
    sleep(0.2)  # Make sure the supply is stable
    voltage = adc.getVoltage()
    if logFile:
        logFile.logData("Voltage before flashing:" + str(voltage))
    else:
        print("Voltage before flashing:" + str(voltage))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if isfloat(sys.argv[1]):
            setVoltage(float(sys.argv[1]), True, False)
            gpio.setPwrEn(True)
        elif sys.argv[1].lower() == "off":
            gpio.setPwrEn(False)
            gpio.setPsEn(False)
    else:
        print("Please remove any chips and press Enter to test power supply accuracy")
        print(
            "DON'T DO THIS WITH A CHIP ATTACHED, YOU MIGHT DAMAGE IT! Press CTRL+C to Cancel"
        )
        input()
        checkPS()
