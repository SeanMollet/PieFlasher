#!/usr/bin/env python3
import os
import time
import re
from pathlib import Path
from luma.core.render import canvas
from luma.core import cmdline, error
from PIL import ImageFont


def show_display(device):
    # use custom font
    font_path = str(Path(__file__).resolve().parent.joinpath("fonts", "FreePixel.ttf"))
    font2 = ImageFont.truetype(font_path, 16)

    with canvas(device) as draw:
        draw.text((0, 0), "PieFlasher", font=font2, fill="white")
        draw.text((0, 14), "File:", font=font2, fill="white")

        if device.height >= 64:
            draw.text((0, 28), "Voltage", font=font2, fill="white")
            draw.text((0, 42), "Status", font=font2, fill="white")


def display_settings(device, args):
    """
    Display a short summary of the settings.

    :rtype: str
    """
    iface = ""
    display_types = cmdline.get_display_types()
    if args.display not in display_types["emulator"]:
        iface = f"Interface: {args.interface}\n"

    lib_name = cmdline.get_library_for_display_type(args.display)
    if lib_name is not None:
        lib_version = cmdline.get_library_version(lib_name)
    else:
        lib_name = lib_version = "unknown"

    import luma.core

    version = f"luma.{lib_name} {lib_version} (luma.core {luma.core.__version__})"

    return f'Version: {version}\nDisplay: {args.display}\n{iface}Dimensions: {device.width} x {device.height}\n{"-" * 60}'


def get_device():
    parser = cmdline.create_parser(description="luma.examples arguments")
    args = parser.parse_args([])
    try:
        device = cmdline.create_device(args)
        print(display_settings(device, args))
        return device

    except error.Error as e:
        return None


def main():
    while True:
        show_display(device)
        time.sleep(60)


if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
