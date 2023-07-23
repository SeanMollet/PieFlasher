import json
import sys
import os

# Why JSON?
# We could put this stuff in an actual db, SQLlite, MySQL, etc..
# But, there's really no need since it's an embedded tool.
# Being able to easily view/edit/copy the JSON is more valuable


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

confDir = os.path.join(dataPath,"config")
result = testDir(confDir)
if not result:
    print("No config directory found! Aborting.")
    sys.exit(1)

logDir = os.path.join(dataPath,"logs")
result = testDir(logDir)
if not result:
    print("No log directory found! Aborting.")
    sys.exit(1)

imageDir = os.path.join(dataPath,"images")
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
    if not os.path.isdir(dataPath):
        return None
    filename = name+".json"
    filePath = os.path.join(dataPath,filename)
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
    
def saveConfiguration(name,data) -> bool:
    if not os.path.isdir(dataPath):
        return False
    filename = name+".json"
    filePath = os.path.join(dataPath,filename)
    try:
        with open(filePath,"w") as f:
            contents = json.dumps(data)
            f.write(contents)
            return True
    except Exception:
        pass
    return False     