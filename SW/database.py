import json
import sys
import os
import threading
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


def getLogFileName() -> str:
    filename = datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3] + ".log"
    logFilePath = os.path.join(logDir, filename)
    logComplete = False
    printLogFileData(logFilePath)
    return logFilePath


def loggingComplete():
    global logComplete
    logComplete = True
    if logThread is not None:
        logThread.join()


def followFile(thefile) -> str:
    global logComplete
    while True:
        line = thefile.read()
        if not line:
            if logComplete:
                yield None
            sleep(0.1)
            continue
        yield line


def logReader(logFile: str) -> None:
    # Wait for the file to be created
    print("Waiting for log file", logFile)
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

    print("Found log file, opening")
    with open(logFile, "r") as logfile:
        loglines = followFile(logfile)
        for line in loglines:
            # Follow sends us a None when we're done
            if line is None:
                return
            print(line, end="")


def printLogFileData(logFile: str) -> None:
    logThread = threading.Thread(target=logReader, args=[logFile])
    logThread.start()
