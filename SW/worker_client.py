#!/usr/bin/env python3
import socketio

sio = socketio.Client()
sio.connect("http://10.23.0.10:5000")

sio.emit("my_ping")


@sio.on("my_pong")
def my_pong():
    print("Received a pong")

    # sio.disconnect()
    # exit(0)


@sio.on("newFile")
def newFile(fileName):
    print("New file received:", fileName)


@sio.on("shutdown")
def shutdown():
    print("Shutting down")
    sio.disconnect()
    exit(0)


@sio.on("my_response")
def my_response(data):
    print("Data received:", data)
