#!/usr/bin/env python3
from flask import (
    Flask,
    render_template,
    session,
    request,
    send_from_directory,
    send_file,
)
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
import os
from pathlib import Path
from tempfile import TemporaryDirectory

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)
filesPath = "data/files"


@app.route("/websocket_test.html")
def websocket_test():
    return render_template("websocket_test.html")


@app.route("/")
def index():
    return render_template("status.html")


@app.route("/status/")
def status():
    return render_template("status.html")


@app.route("/logs/")
def logs():
    return render_template("logs.html")


@app.route("/upload/")
def upload():
    return render_template("upload.html")


@app.route("/configure/")
def configure():
    return render_template("configure.html")


@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/images/<path:path>")
def send_image(path):
    return send_from_directory("images", path)


@app.route("/files/<name>")
def getFile(name):
    print("Attempting to download file:", name)
    return "Here's the file!"


@app.route("/files/upload", methods=["POST"])
def postFile():
    print("Attemped to upload a file")
    f = request.files["file"]
    filename = secure_filename(f.filename)
    fullPath = os.path.join(filesPath, filename)
    f.save(fullPath)
    print("Saved file to:", fullPath)
    return ""


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
    fileTempPath = TemporaryDirectory()
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["UPLOAD_FOLDER"] = fileTempPath
    # 256 MB should be more than enough
    app.config["MAX_CONTENT_PATH"] = 256 * 1024 * 1024
    socketio.run(app, host="0.0.0.0")
