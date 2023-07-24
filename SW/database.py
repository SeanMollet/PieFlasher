import json
import sys
import os
import threading
import select
import re
from typing import Callable
from datetime import datetime
from time import sleep

# Why JSON?
# We could put this stuff in an actual db, SQLlite, MySQL, etc..
# But, there's really no need since it's an embedded tool.
# Being able to easily view/edit/copy the JSON is more valuable

logComplete = False
logThread = None


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


def loadConfiguration(name):
    if not os.path.isdir(confDir):
        return None
    filename = name + ".json"
    filePath = os.path.join(confDir, filename)
    if not os.path.isfile(filePath):
        return None
    try:
        with open(filePath) as f:
            contents = f.read()
            obj = json.loads(contents)
            return obj
    except Exception:
        pass
    return None


def saveConfiguration(name, data) -> bool:
    if not os.path.isdir(confDir):
        return False
    filename = name + ".json"
    filePath = os.path.join(confDir, filename)
    try:
        with open(filePath, "w") as f:
            contents = json.dumps(data)
            f.write(contents)
            return True
    except Exception:
        pass
    return False


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
        if not line:
            if logComplete:
                yield None
            sleep(0.1)
            continue
        yield line


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
