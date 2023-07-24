#!/usr/bin/env python3
import socketio

sio = socketio.Client()
sio.connect("http://10.23.0.5")

sio.emit("my_ping")


@sio.on("my_pong")
def my_pong(data):
    print("Received a pong:", data)

    sio.disconnect()
    exit(0)
