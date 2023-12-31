#!/usr/bin/env python3
import socketio
import os
import threading
import platform
from time import sleep
from typing import Callable
from utils import isfloat
from database import getconfig

latestStatus = None
hostName = platform.uname()[1]
rebootFunc = None
shutdownFunc = None
fileUpdateFunction = None
server = getconfig("Server")

connectThread = None
continueConnect = True
sio = socketio.Client()


def connectThreadWorker():
    global latestStatus
    print("[  SERVER] Connecting to:", server)
    while not sio.connected and continueConnect:
        try:
            sio.connect(server)
            print("[  SERVER] Connected to server:", server)
            sio.emit("register", hostName)
        except socketio.exceptions.ConnectionError:
            pass
        sleep(0.2)


def startup():
    connectThread = threading.Thread(target=connectThreadWorker)
    connectThread.start()


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


@sio.on("connect")
def serverConnected():
    print("[  SERVER] Server connected")
    # In case the server restarted, send it our most recent status
    try:
        sio.emit("register", hostName)
        if latestStatus is not None:
            sio.emit("loggingData", latestStatus)
    except Exception as E:
        print("BARF", E)
        pass


@sio.on("shutdown")
def shutdown():
    print("Shutting down system")
    global latestStatus
    if latestStatus is not None:
        latestStatus["Status"] = "Shutting down"
        sio.emit("statusData", latestStatus)
    sleep(0.2)
    disconnect()
    if shutdownFunc is not None:
        shutdownFunc()


@sio.on("reboot")
def reboot():
    print("Rebooting system")
    global latestStatus
    if latestStatus is not None:
        latestStatus["Status"] = "Rebooting"
        sio.emit("statusData", latestStatus)
    sleep(0.2)
    sio.disconnect()
    global rebootFunc
    if rebootFunc is not None:
        rebootFunc()


def disconnect():
    sio.disconnect()
    global pingThreadContinue, pingThread, shutdownFunc, continueConnect, connectThread
    pingThreadContinue = False
    if pingThread is not None:
        pingThread.join()
    continueConnect = False
    if connectThread is not None:
        connectThread.join()


def startPing():
    global pingThreadContinue, pingThread
    pingThreadContinue = True
    pingThread = threading.Thread(target=sendPeriodicPing)
    pingThread.start()


def sendPeriodicPing():
    global pingThreadContinue, latestStatus
    loopCount = 0
    while pingThreadContinue:
        if sio.connected and loopCount > 100:
            sio.emit("statusData", latestStatus)
            loopCount = 0
        sleep(0.1)
        loopCount += 1


def setFileUpdate(updateFunction: Callable):
    global fileUpdateFunction
    fileUpdateFunction = updateFunction


def setReboot(rebootFunction: Callable):
    global rebootFunc
    rebootFunc = rebootFunction


def setShutdown(shutdownFunction: Callable):
    global shutdownFunc
    shutdownFunc = shutdownFunction


def sendLogData(logFile, logData):
    global hostName
    sio.emit(
        "loggingData",
        {
            "Hostname": hostName,
            "logFile": os.path.basename(logFile),
            "logData": logData,
        },
    )


def sendStatus(
    status: str,
    lastResult: str,
    filename: str,
    progress: float,
    voltage: float,
    targetVoltage: float,
):
    global latestStatus, hostName
    # This either worked or it didn't, if it didn't, we don't care
    try:
        newStatus = {
            "Hostname": hostName,
            "Status": status,
            "LastResult": lastResult,
            "Filename": filename,
            "Progress": progress,
            "Voltage": round(voltage, 2),
            "TargetVoltage": round(targetVoltage, 2),
        }

        if newStatus != latestStatus:
            latestStatus = newStatus
            sio.emit("statusData", latestStatus)
    except Exception:
        pass


def getServer():
    return server


startPing()
