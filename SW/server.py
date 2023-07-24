#!/usr/bin/env python3
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")


@socketio.event
def newFileSelected(fileData):
    emit("newFile", fileData, broadcast=True)


@socketio.on("connect")
def test_connect():
    emit("ConnectedResponse", {"data": "Connected"})


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected")


@socketio.event
def my_ping():
    emit("my_pong")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0")
