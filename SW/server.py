#!/usr/bin/env python3
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
import os
from pathlib import Path

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")


@socketio.event
def newFileSelected(fileData):
    emit("newFile", fileData, broadcast=True)


@socketio.event
def register(hostName):
    session["hostName"] = hostName
    print("Client", hostName, "connected")


@socketio.on("connect")
def test_connect():
    emit("ConnectedResponse", None)


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected")


@socketio.on("shutdown_request")
def shutdown_request():
    print("Shutdown requested, shutting down clients")
    emit("shutdown", None, broadcast=True)


@socketio.on("loggingData")
def loggingData(data):
    if data is not None and "logFile" in data and "logData" in data:
        hostname = session.get("hostName", "")
        print(hostname, "logged to", data["logFile"], data["logData"])
        if len(hostname) > 0:
            path = Path("data/logs", hostname)
            if not os.path.isdir(path):
                path.mkdir(parents=True)
            logPath = os.path.join(path, data["logFile"])
        else:
            logPath = os.path.join("data/logs", data["logFile"])
        with open(logPath, "a") as logFile:
            logFile.write(data["logData"])


@socketio.event
def my_ping():
    emit("my_pong")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0")
