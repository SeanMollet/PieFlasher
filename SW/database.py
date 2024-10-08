import json
import sys
import os
import threading
import select
import re
from typing import Callable
from datetime import datetime
from time import sleep
from pathlib import Path

# Why JSON?
# We could put this stuff in an actual db, SQLlite, MySQL, etc..
# But, there's really no need since it's an embedded tool.
# Being able to easily view/edit/copy the JSON is more valuable

loadedConfig = None


def testDir(path) -> bool:
    if not os.path.isdir(path):
        try:
            os.mkdir(path)
        except (FileNotFoundError, FileExistsError):
            pass

    if not os.path.isdir(path):
        return False
    return True


dataPath = os.path.join(Path.home(), "PieFlasherData")

result = testDir(dataPath)
if not result:
    print("No data directory found! Aborting.")
    sys.exit(1)

confDir = os.path.join(dataPath, "config")
result = testDir(confDir)
if not result:
    print("No config directory found! Aborting.")
    sys.exit(1)

logDir = os.path.join(dataPath, "logs")
result = testDir(logDir)
if not result:
    print("No log directory found! Aborting.")
    sys.exit(1)

imageDir = os.path.join(dataPath, "images")
result = testDir(imageDir)
if not result:
    print("No images directory found! Aborting.")
    sys.exit(1)

if not os.path.isdir(confDir):
    try:
        os.mkdir(confDir)
    except (FileNotFoundError, FileExistsError):
        pass

if not os.path.isdir(confDir):
    print("No config directory found! Aborting.")
    sys.exit(1)


def getDefaultConfig():
    return {"Server": "http://10.23.0.10:5000", "Rotation": 0, "VoltageRegulatorAdjustment": 0, "Ftdi": False}


def getConfigFilePath():
    return os.path.join(dataPath, "config", "configuration.json")


def saveConfig():
    global loadedConfig
    configFilePath = getConfigFilePath()
    print("Saving configuration to:", os.path.abspath(configFilePath))
    try:
        with open(configFilePath, "w") as configFile:
            data = json.dumps(loadedConfig)
            configFile.write(data)
    except IOError:
        print("Error writing configuration to:", configFilePath)


def loadConfig():
    global loadedConfig
    configFilePath = getConfigFilePath()
    print("Loading configuration from:", os.path.abspath(configFilePath))
    if os.path.isfile(configFilePath):
        with open(configFilePath, "r") as configFile:
            data = configFile.read()
            newConfig = json.loads(data)
            if newConfig:
                loadedConfig = newConfig
    else:
        # Create a default configuration
        loadedConfig = getDefaultConfig()
        saveConfig()


def getconfig(key: str):
    global loadedConfig
    if loadedConfig is None:
        print("Loading configuration")
        loadConfig()
    if key in loadedConfig:
        return loadedConfig[key]
    else:
        default = getDefaultConfig()
        if key in default:
            print("Setting default value for missing config option:", key)
            loadedConfig[key] = default[key]
            saveConfig()
            return loadedConfig[key]
    return ""


class flashLogger:
    def __init__(
        self,
        updateFunc: Callable,
        logOutput: Callable = None,
        eraseFailed: Callable = None,
        consoleOnly: bool = False,
        openFileEveryTime: bool = False,
    ) -> None:
        self.logComplete = False
        self.filename = datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3] + ".log"
        self.logFilePath = os.path.join(logDir, self.filename)
        self.logComplete = False
        self.updateFunc = updateFunc
        self.logOutput = logOutput
        self.eraseFailedFunc = eraseFailed
        self.consoleLog = consoleOnly
        self.openFileEveryTime = openFileEveryTime
        if not (openFileEveryTime):
            self.outputFile = open(self.logFilePath, "a")
        else:
            self.outputFile = None

    def __del__(self):
        if self.outputFile:
            self.outputFile.close()
        pass

    def getFilename(self):
        return os.path.basename(self.logFilePath)

    def getPath(self):
        return self.logFilePath

    def loggingComplete(self):
        self.logComplete = True

    def shutdownLogging(self):
        self.logComplete = True
        if self.logThread is not None:
            self.logThread.join()

    def logData(self, *args):
        data = "".join(map(str, args)) + "\n"
        if self.consoleLog:
            print(data, end="")
        else:
            if self.openFileEveryTime:
                with open(self.logFilePath, "a") as f:
                    f.write(data)
            else:
                self.outputFile.write(data)

    def getData(self) -> str:
        try:
            with open(self.logFilePath, "r") as f:
                content = f.read()
                return content
        except IOError:
            pass
        return ""

    def followFile(self, thefile) -> str:
        while True:
            line = thefile.read(1200)
            if line:
                yield line
            else:
                # This should finish reading the file and not close until we've been told to AND read everything
                if self.logComplete:
                    yield None
                sleep(0.1)

    def updateReadPos(self, pos):
        if self.updateFunc:
            self.updateFunc(pos, "R")

    def updateErasePos(self, pos):
        if self.updateFunc:
            self.updateFunc(pos, "E")

    def updateFlashPos(self, pos):
        if self.updateFunc:
            self.updateFunc(pos, "W")

    def updateFlashComplete(self):
        if self.updateFunc:
            self.updateFunc(100, "D")

    def logReader(self) -> None:
        readParser = re.compile(r"Reading old flash chip contents")
        verifyParser = re.compile(r"Verifying flash")
        doneParser = re.compile(r"Erase/write done")
        posParser = re.compile(r"0x[0-9a-f]*-(0x[0-9a-f]*):([EWS]+)")
        eraseFailed = re.compile(r"ERASE FAILED")
        # Wait for the file to be created
        # print("Waiting for log file", logFile)
        limit = 10 * 300
        checks = 0
        while checks < limit and not self.logComplete:
            if os.path.isfile(self.logFilePath):
                break
            checks += 1
            sleep(0.1)

        if checks >= limit:
            print("Timed out waiting for logfile")
            return

        # print("Found log file, opening")
        with open(self.logFilePath, "r") as logfile:
            os.set_blocking(logfile.fileno(), False)
            loglines = self.followFile(logfile)
            for line in loglines:
                # Follow sends us a None when we're done
                if line is None:
                    # print("Got an empty line.")
                    return
                if self.logOutput is not None:
                    self.logOutput(self.filename, line)
                if self.updateFunc is None:
                    continue
                # Erase failed
                values = eraseFailed.findall(line)
                if values and self.eraseFailedFunc:
                    self.eraseFailedFunc()
                # Done
                values = doneParser.findall(line)
                if values:
                    # print("Found a done.")
                    if self.updateFunc:
                        self.updateFunc(100, "D")
                    return
                # Reading
                values = readParser.findall(line)
                if values:
                    # print("Found a read:" + line)
                    if self.updateFunc:
                        self.updateFunc(0, "R")
                    continue
                # Verifying
                values = verifyParser.findall(line)
                if values:
                    # print("Found a verify:" + line)
                    if self.updateFunc:
                        self.updateFunc(0, "V")
                    continue

                # Flashing or Erasing + address
                values = posParser.findall(line)
                if len(values) > 0:
                    if self.updateFunc is not None:
                        val = values[len(values) - 1]
                        pos = int(val[0].replace("0x", ""), 16)
                        mode = "W"
                        # Erase + Flash comes out as EW, this will only catch solo Erase
                        if val[1] == "E":
                            mode = "E"
                        elif val[1] == "EW":
                            mode = "W"
                        self.updateFunc(pos, mode)
                # print(line, end="")
                # print("Received:", len(line), "bytes:", line)
