#!/usr/bin/env python3
import time
import requests
import sys
import os
import progressbar
import platform
import threading
import worker_client
import signal
from urllib.parse import urljoin
from tempfile import mkdtemp
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
from time import sleep


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
        "REBOOTING",
        "DOWNLOADING",
    ],
)


oledFontPath = str(Path(__file__).resolve().parent.joinpath("fonts", "FreePixel.ttf"))
oledFont = ImageFont.truetype(oledFontPath, 16)

gpio = pi_gpio()

currentState = State.STARTUP
currentProgress = 0
currentFile = ""
currentFilePath = mkdtemp()
currentEraseMode = False
currentVoltage = 0.0
currentVoltageTarget = 0.0
fileScrollPos = 0
fileScrollBack = False


def downloadNewFile(fileName):
    global currentProgress, currentState, currentFile, currentFilePath, currentVoltage, currentVoltageTarget
    currentState = State.DOWNLOADING

    server = worker_client.getServer()
    if len(server) == 0:
        return
    fullUrl = urljoin(server, "loadFile/" + fileName)
    try:
        with requests.get(fullUrl, stream=True) as response:
            outputPath = Path(currentFilePath, fileName)
            with open(outputPath, "wb") as file:
                total_size = int(response.headers.get("Content-Length"))
                chunk_size = 4096
                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                    # calculate current percentage
                    currentProgress = (i * chunk_size / total_size) * 100
                    file.write(chunk)

        # Delete the currentfile from tmpfs
        if len(currentFile) > 0 and currentFile != fileName:
            oldPath = Path(currentFilePath, currentFile)
            os.remove(oldPath)

        currentFile = fileName
        currentState = State.IDLE
        currentProgress = 0

        worker_client.sendStatus(
            str(currentState.name).capitalize(),
            currentFile,
            currentProgress,
            currentVoltage,
            currentVoltageTarget,
        )
    except Exception as E:
        print("Failed to download:", fileName)
        print("Error is:", E)
        currentState = State.IDLE


def updateCurrentFile(fileName, voltage):
    global currentState, currentProgress, currentFile, currentVoltage, currentVoltageTarget
    while currentState != State.IDLE:
        print("Waiting for Idle before starting download")
        sleep(1)
    currentVoltageTarget = voltage
    downloadThread = threading.Thread(target=downloadNewFile, args=[fileName])
    downloadThread.start()


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
        "{:0.2f}".format(currentVoltage)
        + "V / "
        + "{:0.2f}".format(currentVoltageTarget)
        + "V",
        font=oledFont,
        fill="white",
    )
    status = ""
    if currentState == State.IDLE:
        status = "Idle " + platform.uname()[1]
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
    elif currentState == State.ERROR:
        status = "Error"
    elif currentState == State.REBOOTING:
        status = "Rebooting"
    elif currentState == State.DOWNLOADING:
        status = "Downloading"

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
                str(currentState.name).capitalize(),
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
    global currentState, currentProgress, currentFile, currentFilePath, currentVoltageTarget, currentEraseMode

    gpio.setSigBusy(False)

    fileSize = 0
    fullPath = Path(currentFilePath, currentFile)
    if os.path.isfile(fullPath):
        fileSize = os.path.getsize(fullPath)

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
            str(currentState.name).capitalize(),
            currentFile,
            currentProgress,
            currentVoltage,
            currentVoltageTarget,
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
            gpio.setSigBusy(True)
            gpio.holdSignal("SIG_NG", 1)
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
        if not os.path.isfile(fullPath):
            logdata(logFile, "File " + currentFile + " not found. Aborting flash.")
            result = False
        else:
            with open(fullPath, "rb") as imageFile:
                data = imageFile.read()
                result = flashImage(data, logFile, False)
    if result:
        logdata(logFile, "Success")
    else:
        logdata(logFile, "Error performing operation, check logfile")

    loggingComplete()
    disablePower()

    bar.finish()

    # This is down here so we don't tell the machine we're done until we've de-powered the chip
    if result:
        gpio.setSigBusy(True)
        gpio.holdSignal("SIG_OK", 1)
    else:
        gpio.setSigBusy(True)
        gpio.holdSignal("SIG_NG", 1)

    currentState = State.IDLE


def reboot():
    global currentState
    currentState = State.REBOOTING
    worker_client.shutdown()
    sleep(2)
    os.system("sudo reboot")


def sigint_handler(signal, frame):
    print("Shutting down")
    worker_client.shutdown()
    os.system("sudo poweroff")


if __name__ == "__main__":
    worker_client.setFileUpdate(updateCurrentFile)
    worker_client.setReboot(reboot)

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
