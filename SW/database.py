import json
import sys
import os

# Why JSON?
# We could put this stuff in an actual db, SQLlite, MySQL, etc..
# But, there's really no need since it's an embedded tool.
# Being able to easily view/edit/copy the JSON is more valuable


if not os.path.isdir("data"):
    print("No data directory found! Aborting.")
    sys.exit(1)

dataPath = "data"
def loadConfiguration(name):
    if not os.path.isdir(self.dataPath):
        return None
    filename = name+".json"
    filePath = os.path.join(self.dataPath,filename)
    if not os.path.isfile(filePath):
        return None
    try:
        with open(filePath) as f:
            contents = f.read()
            obj = json.loads(contents)
            return obj
    except KeyboardInterrupt:
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
    except KeyboardInterrupt:
        pass
    return False     