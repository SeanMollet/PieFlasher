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
def my_event(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit("my_response", {"data": message["data"], "count": session["receive_count"]})


@socketio.event
def my_broadcast_event(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    emit(
        "my_response",
        {"data": message["data"], "count": session["receive_count"]},
        broadcast=True,
    )


@socketio.on("my event")
def test_message(message):
    emit("my response", {"data": message["data"]})


@socketio.on("my broadcast event")
def test_message(message):
    emit("my response", {"data": message["data"]}, broadcast=True)


@socketio.on("connect")
def test_connect():
    emit("my response", {"data": "Connected"})


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected")


@socketio.event
def my_ping():
    emit("my_pong")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0")
