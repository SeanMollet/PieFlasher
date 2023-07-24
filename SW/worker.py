#!/usr/bin/env python3
import sys
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


currentState = State.STARTUP
currentProgress = 0
currentFile = ""
currentVoltage = 0.0
currentVoltageTarget = 0.0


def show_display(device):
    # use custom font
    font_path = str(Path(__file__).resolve().parent.joinpath("fonts", "FreePixel.ttf"))
    font2 = ImageFont.truetype(font_path, 16)

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
        draw.text((48, 0), "PieFlasher", font=font2, fill="white")
        draw.text((92, 14), "v0.1", font=font2, fill="white")

        device.display(background.convert(device.mode))

        return

    with canvas(device) as draw:
        draw.text((0, 0), "PieFlasher", font=font2, fill="white")
        if len(currentFile) == 0:
            dispFile = "No File"
        else:
            dispFile = currentFile
        draw.text((0, 14), dispFile, font=font2, fill="white")

        if device.height >= 64:
            draw.text(
                (0, 28),
                str(round(currentVoltage, 2))
                + "V / "
                + str(round(currentVoltageTarget, 2))
                + "V",
                font=font2,
                fill="white",
            )
            status = ""
            if currentState == State.IDLE:
                status = "Idle"
            elif currentState == State.ERASING:
                status = "Erasing"
            elif currentState == State.FLASHING:
                status = "Flashing"
            elif currentState == State.Error:
                status = "Error"

            draw.text((0, 42), status, font=font2, fill="white")


def main():
    while True:
        show_display(device)
        time.sleep(60)


if __name__ == "__main__":
    try:
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial)
        main()
    except KeyboardInterrupt:
        pass
