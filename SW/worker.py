#!/usr/bin/env python3
from i2c import lockI2C, i2cAdc
import gpio
import time
from pathlib import Path
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, Image, ImageDraw
from enum import Enum


class State(Enum):
    STARTUP = 0
    IDLE = 1
    ERASING = 2
    FLASHING = 3
    ERROR = 4


oledFontPath = str(Path(__file__).resolve().parent.joinpath("fonts", "FreePixel.ttf"))
oledFont = ImageFont.truetype(oledFontPath, 16)

currentState = State.STARTUP
currentProgress = 50
currentFile = ""
currentVoltageTarget = 0.0


def show_display(device):
    global currentState, currentProgress, currentFile, currentVoltageTarget, oledFont

    if currentState == State.STARTUP:
        pieImagePath = str(
            Path(__file__).resolve().parent.joinpath("images", "PieSlice.png")
        )

        pieImage = Image.open(pieImagePath).convert("RGBA")
        background = Image.new("RGBA", device.size, "black")

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

    with canvas(device) as draw:
        if len(currentFile) == 0:
            dispFile = "No File"
        else:
            dispFile = currentFile
        draw.text((0, 0), dispFile, font=oledFont, fill="white")

        if device.height >= 64:
            draw.text(
                (0, 14),
                str(round(adc.getVoltage(), 2))
                + "V / "
                + str(round(currentVoltageTarget, 2))
                + "V",
                font=oledFont,
                fill="white",
            )
            status = ""
            if currentState == State.IDLE:
                status = "Idle"
            elif currentState == State.ERASING:
                status = "Erasing " + str(currentProgress) + "%"
            elif currentState == State.FLASHING:
                status = "Flashing " + str(currentProgress) + "%"
            elif currentState == State.Error:
                status = "Error"

            draw.text((0, 28), status, font=oledFont, fill="white")
            draw.rectangle((0, 42, 127, 63), fill="black", outline="white")

            progressWidth = 127 * (currentProgress / 100)
            draw.rectangle((0, 42, progressWidth, 63), fill="white", outline="white")
            # draw.text((0, 42), "PieFlasher", font=font2, fill="white")


def main():
    global imageChanged, imageCount, currentState
    startupOver = time.time() + 2

    while True:
        if currentState == State.STARTUP and time.time() > startupOver:
            currentState = State.FLASHING

        show_display(device)

        time.sleep(0.2)


if __name__ == "__main__":
    try:
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial)
        adc = i2cAdc()
        main()
    except KeyboardInterrupt:
        pass
