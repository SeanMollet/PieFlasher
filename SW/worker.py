#!/usr/bin/env python3
import time
import sys
import os
import progressbar
import threading
import worker_client
import signal
from i2c import lockI2C, i2cAdc
from gpio import pi_gpio
from power import setVoltage, maxPwrControlVoltage, disablePower, enablePower
from flash import flashImage, scanChip
from database import getLogFileName, loggingComplete
from utils import isfloat
from pathlib import Path
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, Image, ImageDraw
from enum import Enum

State = Enum(
    "State",
    [
        "STARTUP",
        "IDLE",
        "LAUNCHING",
        "READING",
        "ERASING",
        "FLASHING",
        "VERIFYING",
        "ERROR",
    ],
)

oledFontPath = str(Path(__file__).resolve().parent.joinpath("fonts", "FreePixel.ttf"))
oledFont = ImageFont.truetype(oledFontPath, 16)

gpio = pi_gpio()

currentState = State.STARTUP
currentProgress = 0
currentFile = ""
currentEraseMode = False
currentVoltage = 0.0
currentVoltageTarget = 0.0
fileScrollPos = 0
fileScrollBack = False


def updateCurrentFile(fileName, voltage):
    global currentFile, currentVoltageTarget
    currentFile = fileName
    currentVoltageTarget = voltage


worker_client.setFileUpdate(updateCurrentFile)


def show_display(device):
    global currentState, currentProgress, currentFile, currentVoltage, currentVoltageTarget, oledFont, fileScrollPos, fileScrollBack

    background = Image.new("RGBA", device.size, "black")

    currentVoltage = adc.getVoltage()
    if currentState == State.STARTUP:
        pieImagePath = str(
            Path(__file__).resolve().parent.joinpath("images", "PieSlice.png")
        )

        pieImage = Image.open(pieImagePath).convert("RGBA")

        scale = device.height / pieImage.size[1] * 0.8
        newSize = (int(pieImage.size[0] * scale), int(device.height * 0.8))
        img = pieImage.resize(newSize)
        background.paste(img, (0, 10))

        draw = ImageDraw.Draw(background)
        draw.text((48, 0), "PieFlasher", font=oledFont, fill="white")
        draw.text((92, 14), "v0.1", font=oledFont, fill="white")

        # Lock the I2C so voltage monitoring, etc.. doesn't use it
        lockI2C(lambda: device.display(background.convert(device.mode)))
        return

    draw = ImageDraw.Draw(background)
    if len(currentFile) == 0:
        dispFile = "No File"
    else:
        dispFile = os.path.basename(currentFile)

    draw.text((0 - fileScrollPos, 0), dispFile, font=oledFont, fill="white")

    # Get the size of the text and adjust scroll for the next pass if we need to
    fileWidth = draw.textlength(dispFile, oledFont)
    if fileWidth > device.width:
        overage = fileWidth - device.width
        if fileScrollPos >= overage:
            fileScrollBack = True
        if fileScrollPos <= 0:
            fileScrollBack = False
        if fileScrollBack:
            # Pause at the end
            if fileScrollPos > (overage - 0.5):
                fileScrollPos -= 0.1
            else:
                fileScrollPos -= 4
        else:
            # Pause at the start
            if fileScrollPos < 1:
                fileScrollPos += 0.1
            else:
                fileScrollPos += 4
    else:
        fileScrollPos = 0

    draw.text(
        (0, 14),
        str(round(currentVoltage, 2))
        + "V / "
        + str(round(currentVoltageTarget, 2))
        + "V",
        font=oledFont,
        fill="white",
    )
    status = ""
    if currentState == State.IDLE:
        status = "Idle"
    elif currentState == State.LAUNCHING:
        status = "Starting up"
    elif currentState == State.READING:
        status = "Reading"
    elif currentState == State.ERASING:
        status = "Erasing " + str(currentProgress) + "%"
    elif currentState == State.FLASHING:
        status = "Flashing " + str(currentProgress) + "%"
    elif currentState == State.VERIFYING:
        status = "Verifying"
    elif currentState == State.Error:
        status = "Error"

    draw.text((0, 28), status, font=oledFont, fill="white")
    draw.rectangle((0, 44, 127, 63), fill="black", outline="white")

    progressWidth = 127 * (currentProgress / 100)
    draw.rectangle((0, 44, progressWidth, 63), fill="white", outline="white")

    lockI2C(lambda: device.display(background.convert(device.mode)))


def main():
    global imageChanged, imageCount, currentState, currentFile, currentProgress, currentVoltage, currentVoltageTarget
    startupOver = time.time() + 2

    prevStartValue = True
    while True:
        if currentState == State.STARTUP and time.time() > startupOver:
            currentState = State.IDLE
            currentVoltage = adc.getVoltage()
            worker_client.sendStatus(
                "Idle",
                currentFile,
                currentProgress,
                currentVoltage,
                currentVoltageTarget,
            )

        curStartValue = gpio.getSigStart()
        if curStartValue == False and prevStartValue == True:
            if currentState == State.IDLE:
                currentState = State.LAUNCHING
                flashThread = threading.Thread(target=processFlash)
                flashThread.start()

        prevStartValue = curStartValue

        show_display(device)

        time.sleep(0.2)


def logdata(logFile, *args):
    data = "".join(map(str, args)) + "\n"
    worker_client.sendLogData(logFile, data)
    with open(logFile, "a") as f:
        f.write(data)


def processFlash():
    global currentState, currentProgress, currentFile, currentVoltageTarget, currentEraseMode

    fileSize = 0
    if os.path.isfile(currentFile):
        fileSize = os.path.getsize(currentFile)

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
    )

    def updateStatus(pos, mode):
        global currentProgress, currentState, currentFile, currentVoltage, currentVoltageTarget
        task = "Idle"
        if mode == "R":
            currentState = State.READING
            task = "Reading"
        elif mode == "W":
            currentState = State.FLASHING
            task = "Flashing"
        elif mode == "V":
            currentState = State.VERIFYING
            task = "Verifying"
        elif mode == "E":
            currentState = State.ERASING
            task = "Erasing"
        elif mode == "D":
            currentState = State.IDLE
            task = "Done"

        bar.update(pos, task=task)
        currentProgress = int((pos / fileSize) * 100)
        worker_client.sendStatus(
            task, currentFile, currentProgress, currentVoltage, currentVoltageTarget
        )

    logFile = getLogFileName(updateStatus)
    print("Logging to:", logFile)

    # Voltages above 3.4 must be controlled with PS_EN, since the FET for Output turns on automatically.
    # Can't go closed loop, but that's not really an issue with a 5V chip
    logdata(logFile, "Setting voltage to:" + str(currentVoltageTarget))
    if currentVoltageTarget < maxPwrControlVoltage():
        result = setVoltage(currentVoltageTarget, True, False)
        if not result:
            logdata(logFile, "Unable to set requested voltage. Aborting.")
            disablePower()
            currentState = State.ERROR
            return

    currentProgress = 0

    bar.start()

    enablePower()

    if currentEraseMode:
        logdata(logFile, "Launching erase command")
        chip, size = scanChip(logFile)
        fileSize = size * 1024
        bar.max_value = fileSize
    else:
        logdata(logFile, "Launching flash command for:", currentFile)

    result = None
    if currentEraseMode:
        result = flashImage(None, logFile, True, chip, size)
    else:
        if not os.path.isfile(currentFile):
            logdata(logFile, "File " + currentFile + " not found. Aborting flash.")
            result = False
        else:
            with open(currentFile, "rb") as imageFile:
                data = imageFile.read()
                result = flashImage(data, logFile, False)
    if result:
        logdata(logFile, "Success")
    else:
        logdata(logFile, "Error performing operation, check logfile")

    loggingComplete()
    disablePower()

    bar.finish()
    currentState = State.IDLE


def sigint_handler(signal, frame):
    print("Shutting down")
    worker_client.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "erase":
            currentEraseMode = True
        else:
            currentFile = sys.argv[1]

    if len(sys.argv) > 2 and isfloat(sys.argv[2]):
        currentVoltageTarget = float(sys.argv[2])
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial)
        adc = i2cAdc()
        main()
    except KeyboardInterrupt:
        sigint_handler()
