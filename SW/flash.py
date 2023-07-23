#!/usr/bin/env python3
import sys
import os
import shutil
import re
from subprocess import check_output,CalledProcessError

def log(logFile,data):
    try:
        with open(logFile,"a") as f:
            f.write(data)
    except Exception:
        print("Unable to log: ",data)
        pass

def flashImage(imageData,logFile) -> bool:
    spiArgs = "linux_spi:dev=/dev/spidev0.0,spispeed=10000"
    flashrom = shutil.which("flashrom")

    if flashrom is None:
        log(logFile, "Flashrom not found. Aborting")
        return False

    chip = ""
    # Scan for the chip
    # This may return 1, but we just want the logfile anyway
    try:
        check_output([flashrom,"-p",spiArgs,"-o",logFile])
    except CalledProcessError:
        pass

    with open(logFile,"r") as f:
        content = f.read()
        finds = re.findall("Found.*?\"(.*?)\"",content)
        if len(finds) >0:
            finds = list(finds)
            chip = str(finds[0]).strip()
    if len(chip)==0:
        print("No chip found, aborting.")
        return False
    
    print("Using chip:",chip)

    try:
        check_output([flashrom,"-p",spiArgs,"-o",logFile,"-c",chip,"-w","-"],input=imageData)
    except Exception:
        pass

if __name__ == "__main__":
    with open("/home/sean/testImage.img", mode="rb") as flashFile:
        flashData = flashFile.read()
        flashImage(flashData,"/tmp/flashRun.log")