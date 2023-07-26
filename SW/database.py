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

logComplete = False
logThread = None
logOutput = None

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


dataPath = "data"

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
    return {"Server": "http://10.23.0.10:5000"}


def getConfigFilePath():
    return os.path.join(dataPath, "config")


def saveConfig():
    global loadedConfig
    configFilePath = getConfigFilePath()
    try:
        with open(configFilePath, "w") as configFile:
            data = json.dumps(loadedConfig)
            configFile.write(data)
    except IOError:
        print("Error writing configuration to:", configFilePath)


def loadConfig():
    global loadedConfig
    configFilePath = getConfigFilePath()
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
        loadConfig()
    if key in loadedConfig:
        return loadedConfig[key]
    return ""


def getLogFileName(updateFunc: Callable) -> str:
    filename = datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3] + ".log"
    logFilePath = os.path.join(logDir, filename)
    logComplete = False
    printLogFileData(logFilePath, updateFunc)
    return logFilePath


def loggingComplete():
    global logComplete
    logComplete = True
    if logThread is not None:
        logThread.join()


def followFile(thefile) -> str:
    global logComplete
    while True:
        line = thefile.read(100)
        if line:
            yield line
        else:
            # This should finish reading the file and not close until we've been told to AND read everything
            if logComplete:
                yield None
            sleep(0.1)


def logReader(logFile: str, updateFunc: Callable) -> None:
    readParser = re.compile(r"Reading old flash chip contents")
    verifyParser = re.compile(r"Verifying flash")
    doneParser = re.compile(r"Erase/write done")
    posParser = re.compile(r"0x[0-9a-f]*-(0x[0-9a-f]*):([EWS])")
    # Wait for the file to be created
    # print("Waiting for log file", logFile)
    limit = 10 * 300
    checks = 0
    while checks < limit:
        if os.path.isfile(logFile):
            break
        checks += 1
        sleep(0.1)

    if checks >= limit:
        print("Timed out waiting for logfile")
        return

    # print("Found log file, opening")
    with open(logFile, "r") as logfile:
        os.set_blocking(logfile.fileno(), False)
        loglines = followFile(logfile)
        for line in loglines:
            # Follow sends us a None when we're done
            if line is None:
                # print("Got an empty line.")
                return
            if logOutput is not None:
                logOutput(logFile, line)
            # Done
            values = doneParser.findall(line)
            if values:
                # print("Found a done.")
                updateFunc(100, "D")
                return
            # Reading
            values = readParser.findall(line)
            if values:
                # print("Found a read:" + line)
                updateFunc(0, "R")
                continue
            # Verifying
            values = verifyParser.findall(line)
            if values:
                # print("Found a verify:" + line)
                updateFunc(0, "V")
                continue

            # Flashing or Erasing + address
            values = posParser.findall(line)
            if len(values) > 0:
                if updateFunc is not None:
                    val = values[len(values) - 1]
                    pos = int(val[0].replace("0x", ""), 16)
                    mode = "W"
                    if val[1] == "E":
                        mode = "E"
                    updateFunc(pos, mode)
            # print(line, end="")
            # print("Received:", len(line), "bytes:", line)


def printLogFileData(logFile: str, updateFunc: Callable) -> None:
    logThread = threading.Thread(target=logReader, args=[logFile, updateFunc])
    logThread.start()


def setLogOutput(logOutputter: Callable):
    global logOutput
    logOutput = logOutputter
