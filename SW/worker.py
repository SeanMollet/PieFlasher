#!/usr/bin/env python3
import time
import requests
import sys
import os
import progressbar
import platform
import threading
import workerClient
import signal
from urllib.parse import urljoin
from tempfile import mkdtemp
from i2c import lockI2C, i2cAdc
from gpio import pi_gpio
from power import setVoltage, maxPwrControlVoltage, disablePower, enablePower
from flash import flashImage, scanChip
from database import flashLogger, getconfig
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
currentVoltage = 0.0
currentVoltageTarget = 0.0
fileScrollPos = 0
fileScrollBack = False
flashComplete = True
verifyReadMode = False


def downloadNewFile(fileName):
    global currentProgress, currentState, currentFile, currentFilePath, currentVoltage, currentVoltageTarget
    currentState = State.DOWNLOADING

    server = workerClient.getServer()
    if len(server) == 0:
        return
    fullUrl = urljoin(server, "loadFile/" + fileName)

    try:
        with requests.get(fullUrl, stream=True) as response:
            if response.status_code != 200:
                print(
                    "Received error response loading file:",
                    response.status_code,
                    "Aborting.",
                )
                return
            outputPath = Path(currentFilePath, fileName)
            with open(outputPath, "wb") as file:
                total_size = int(response.headers.get("Content-Length"))
                chunk_size = 256 * 1024
                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                    # calculate current percentage
                    currentProgress = (i * chunk_size / total_size) * 100
                    workerClient.sendStatus(
                        str(currentState.name).capitalize(),
                        currentFile,
                        currentProgress,
                        currentVoltage,
                        currentVoltageTarget,
                    )
                    file.write(chunk)

        # Delete the currentfile from tmpfs
        if len(currentFile) > 0 and currentFile != fileName:
            oldPath = Path(currentFilePath, currentFile)
            os.remove(oldPath)

        currentFile = fileName
        currentState = State.IDLE
        currentProgress = 0

        workerClient.sendStatus(
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
    while currentState != State.IDLE and currentState != State.ERROR:
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


def buttonCallback(channel):
    global currentState, flashThread
    if currentState == State.IDLE or currentState == State.ERROR:
        currentState = State.LAUNCHING
        flashThread = threading.Thread(target=processFlash)
        flashThread.start()


def main():
    global imageChanged, imageCount, currentState, currentFile, currentProgress, currentVoltage, currentVoltageTarget
    startupOver = time.time() + 2

    prevStartValue = True

    while True:
        if currentState == State.STARTUP and time.time() > startupOver:
            currentState = State.IDLE
            currentVoltage = adc.getVoltage()
            workerClient.sendStatus(
                str(currentState.name).capitalize(),
                currentFile,
                currentProgress,
                currentVoltage,
                currentVoltageTarget,
            )

        show_display(device)
        time.sleep(0.2)


def sendLogData(logFile, logData):
    workerClient.sendLogData(logFile, logData)


def processFlash():
    global currentState, currentProgress, currentFile, currentFilePath, currentVoltageTarget, flashComplete, verifyReadMode
    flashComplete = False

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

    # The new flashrom sends [READ] messages while in verify mode
    # This keeps us sending "Verify" and makes progress work
    verifyReadMode = False

    # There's a race condition here where the flash takes place so fast that we're out of the routine
    # Before we've read enough logfile to realize in the states
    def updateStatus(pos, mode):
        global currentProgress, currentState, currentFile, currentVoltage, currentVoltageTarget, flashComplete, verifyReadMode
        # Don't send the state if we've lost the race. Logs get sent elsewhere
        if flashComplete:
            return
        task = "Idle"
        if mode == "R" and not verifyReadMode:
            currentState = State.READING
            currentProgress = pos
            task = "Reading"
        elif mode == "W":
            currentState = State.FLASHING
            currentProgress = int((pos / fileSize) * 100)
            task = "Flashing"
        elif mode == "V" or (mode == "R" and verifyReadMode):
            verifyReadMode = True
            currentState = State.VERIFYING
            currentProgress = pos
            task = "Verifying"
        elif mode == "E":
            currentState = State.ERASING
            task = "Erasing"
        elif mode == "D":
            currentState = State.IDLE
            task = "Done"

        prevMode = mode
        bar.update(pos, task=task)
        workerClient.sendStatus(
            str(currentState.name).capitalize(),
            currentFile,
            currentProgress,
            currentVoltage,
            currentVoltageTarget,
        )

    logFile = flashLogger(updateStatus, sendLogData)
    print("Logging to:", logFile)

    # Voltages above 3.4 must be controlled with PS_EN, since the FET for Output turns on automatically.
    # Can't go closed loop, but that's not really an issue with a 5V chip
    logFile.logData("Setting voltage to:" + str(currentVoltageTarget))
    if currentVoltageTarget < maxPwrControlVoltage():
        result = setVoltage(currentVoltageTarget, True, False)
        if not result:
            logFile.logData("Unable to set requested voltage. Aborting.")
            disablePower()
            currentState = State.ERROR
            gpio.setSigBusy(True)
            gpio.holdSignal("SIG_NG", 1)
            return

    currentProgress = 0

    bar.start()

    enablePower()
    logFile.logData("Scanning chip")
    chip, size = scanChip(logFile.getPath())

    if currentFile == "erase":
        logFile.logData("Launching erase command")
        fileSize = size * 1024
        bar.max_value = fileSize
    else:
        logFile.logData("Launching flash command for:", currentFile)

    result = None
    if currentFile == "erase":
        result = flashImage(None, logFile.getPath(), True, chip, size)
    else:
        if not os.path.isfile(fullPath):
            logFile.logData("File " + currentFile + " not found. Aborting flash.")
            result = False
        else:
            with open(fullPath, "rb") as imageFile:
                data = imageFile.read()
                result = flashImage(data, logFile.getPath(), False, chip, size)
    if result:
        logFile.logData("Success")
    else:
        logFile.logData("Error performing operation, check logfile")

    flashComplete = True
    disablePower()

    bar.finish()
    currentProgress = 0
    logFile.loggingComplete()

    # This is down here so we don't tell the machine we're done until we've de-powered the chip
    if result:
        gpio.setSigBusy(True)
        gpio.holdSignal("SIG_OK", 1)
    else:
        gpio.setSigBusy(True)
        gpio.holdSignal("SIG_NG", 1)

    currentState = State.IDLE
    workerClient.sendStatus(
        str(currentState.name).capitalize(),
        currentFile,
        0,
        currentVoltage,
        currentVoltageTarget,
    )


def reboot():
    global currentState
    currentState = State.REBOOTING
    sleep(2)
    os.system("sudo reboot")


def systemShutdown():
    global currentState
    currentState = State.REBOOTING
    sleep(2)
    os.system("sudo poweroff")


def sigint_handler(signal, frame):
    print("Shutting down")
    workerClient.disconnect()
    sys.exit(0)


if __name__ == "__main__":
    workerClient.startup()
    workerClient.setFileUpdate(updateCurrentFile)
    workerClient.setReboot(reboot)
    workerClient.setShutdown(systemShutdown)

    if len(sys.argv) > 1:
        currentFile = sys.argv[1]

    if len(sys.argv) > 2 and isfloat(sys.argv[2]):
        currentVoltageTarget = float(sys.argv[2])
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        rotation = getconfig("Rotation")
        if rotation == 90:
            rotation = 1
        elif rotation == 180:
            rotation = 2
        elif rotation == 270:
            rotation = 3
        elif rotation is None:
            rotation = 0

        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial, rotate=rotation)
        adc = i2cAdc()
        gpio.callOnSigStart(buttonCallback)
        main()

    except KeyboardInterrupt:
        sigint_handler()
