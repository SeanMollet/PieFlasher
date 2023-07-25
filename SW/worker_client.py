#!/usr/bin/env python3
import socketio
import os
import threading
from time import sleep
from typing import Callable
from utils import isfloat


sio = socketio.Client()
sio.connect("http://10.23.0.10:5000")


@sio.on("my_pong")
def my_pong():
    print("[  SERVER] Received a pong")


@sio.on("newFile")
def newFile(fileData):
    global fileUpdateFunction
    print("[  SERVER] New file requested:", fileData)
    if (
        "name" in fileData
        and "voltage" in fileData
        and isfloat(fileData["voltage"])
        and fileUpdateFunction is not None
    ):
        fileUpdateFunction(fileData["name"], float(fileData["voltage"]))


@sio.on("ConnectedResponse")
def serverConnected():
    print("[  SERVER] Server connected")


@sio.on("shutdown")
def shutdown():
    print("Shutting down")
    sio.disconnect()
    global pingThreadContinue, pingThread
    pingThreadContinue = False
    if pingThread is not None:
        pingThread.join()
    exit(0)


@sio.on("my_response")
def my_response(data):
    print("Data received:", data)


def sendPeriodicPing():
    global pingThreadContinue
    loopCount = 0
    while pingThreadContinue:
        if sio.connected and loopCount > 100:
            sio.emit("my_ping")
            loopCount = 0
        sleep(0.1)
        loopCount += 1


def setFileUpdate(updateFunction: Callable):
    global fileUpdateFunction
    fileUpdateFunction = updateFunction


def sendLogData(logFile, logData):
    sio.emit("loggingData", {"logFile": os.path.basename(logFile), "logData": logData})


pingThreadContinue = True
pingThread = threading.Thread(target=sendPeriodicPing)
pingThread.start()

sio.emit("register", "Flasher_A")

fileUpdateFunction = None
