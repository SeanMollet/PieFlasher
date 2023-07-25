#!/usr/bin/env python3
import socketio
import os
import threading
from time import sleep
from typing import Callable
from utils import isfloat


latestStatus = None
hostName = "Flasher_A"
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
    # In case the server restarted, send it our most recent status
    if latestStatus is not None:
        if sio.connected:
            try:
                sio.emit("loggingData", latestStatus)
            except Exception:
                pass


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


def sendStatus(
    status: str, filename: str, progress: float, voltage: float, targetVoltage: float
):
    global latestStatus, hostName
    # This either worked or it didn't, if it didn't, we don't care
    try:
        latestStatus = {
            "Hostname": hostName,
            "Status": status,
            "Filename": filename,
            "Progress": progress,
            "Voltage": voltage,
            "TargetVoltage": targetVoltage,
        }

        sio.emit("loggingData", latestStatus)
    except Exception:
        pass


pingThreadContinue = True
pingThread = threading.Thread(target=sendPeriodicPing)
pingThread.start()

sio.emit("register", hostName)

fileUpdateFunction = None
