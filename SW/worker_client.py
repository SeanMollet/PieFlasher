#!/usr/bin/env python3
import socketio
import os
from typing import Callable
from utils import isfloat

sio = socketio.Client()
sio.connect("http://10.23.0.10:5000")
sio.emit("my_ping")
sio.emit("register", "Flasher_A")

fileUpdateFunction = None


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
    exit(0)


@sio.on("my_response")
def my_response(data):
    print("Data received:", data)


def setFileUpdate(updateFunction: Callable):
    global fileUpdateFunction
    fileUpdateFunction = updateFunction


def sendLogData(logFile, logData):
    sio.emit("loggingData", {"logFile": os.path.basename(logFile), "logData": logData})
