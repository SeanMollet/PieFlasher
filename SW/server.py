#!/usr/bin/env python3
from flask import (
    Flask,
    render_template,
    session,
    request,
    send_from_directory,
    send_file,
    redirect,
)
from werkzeug.utils import secure_filename
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room,
    close_room,
    rooms,
)
import os
import time
import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)
filesPath = Path("data", "files")
if not os.path.isdir(filesPath):
    filesPath.mkdir(parents=True)
clients = {}


@app.route("/websocket_test.html")
def websocket_test():
    return render_template("websocket_test.html")


@app.route("/")
def index():
    return status()


@app.route("/status/")
def status():
    global clients
    flashers = []
    keys = list(clients.keys())
    keys.sort()
    for client in keys:
        flasher = clients[client]
        if "Timestamp" in flasher:
            lastSeen = time.time() - flasher["Timestamp"]
            if lastSeen > 60:
                continue
            flasher["LastSeen"] = str(int(lastSeen)) + " Seconds ago"
        if "Filename" in flasher and len(flasher["Filename"]) == 0:
            flasher["Filename"] = "No file"

        flashers.append(flasher)
    return render_template("status.html", flashers=flashers)


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
    if "file" not in request.files:
        return render_template("upload.html", result="No file given!")
    file = request.files["file"]
    if file.filename == "":
        return render_template("upload.html", result="Empty filename given!")
    if not ("voltage" in request.form and "desc" in request.form):
        print("")
    filename = secure_filename(file.filename)
    fileData = {
        "filename": filename,
        "voltage": request.form["voltage"],
        "desc": request.form["desc"],
        "uploaded": str(datetime.datetime.now()),
    }

    # Don't overwrite files, append a numeric suffix
    file_suffix = 2
    ori_filename = filename
    while True:
        fullPath = os.path.join(filesPath, filename)
        if os.path.isfile(fullPath):
            path = Path(ori_filename)
            filename = path.stem + "(" + str(file_suffix) + ")" + path.suffix
            file_suffix += 1
        else:
            break

    file.save(fullPath)

    fullDataPath = os.path.join(filesPath, filename + ".data.json")
    with open(fullDataPath, "w") as dataFile:
        dataFile.write(json.dumps(fileData, indent=4))

    print("Saved file to:", fullPath, " data to:", fullDataPath)
    return render_template("upload.html", result="Saved uploaded file: " + filename)


@socketio.event
def newFileSelected(fileData):
    emit("newFile", fileData, broadcast=True)


@socketio.event
def register(hostName):
    session["hostName"] = hostName
    updateClient(hostName)
    print("Client:", hostName, "registered")


@socketio.on("disconnect")
def test_disconnect():
    hostname = session.get("hostName", "")
    print("Client:", hostname, "disconnected")


@socketio.on("shutdown_request")
def shutdown_request():
    print("Shutdown requested, shutting down clients")
    emit("shutdown", None, broadcast=True)


@socketio.on("reboot_request")
def reboot_request():
    print("Reboot requested, rebooting clients")
    emit("reboot", None, broadcast=True)


@socketio.event
def joinLogging(message):
    join_room(message["client"] + "Logging")


@socketio.event
def leaveLogging(message):
    leave_room(message["client"] + "Logging")


@socketio.on("loggingData")
def loggingData(data):
    if data is not None:
        hostname = session.get("hostName", "")
        if "logFile" in data and "logData" in data:
            print(hostname, "logged to", data["logFile"], data["logData"])
            if len(hostname) > 0:
                # Update client data and send it to the WS room if anyone is listening
                updateClient(hostname, data["logFile"])
                emit("loggingData", data, to=hostname + "Logging")
            else:
                hostname = "Unknown"
            # Save it
            path = Path("data", "logs", hostname)
            if not os.path.isdir(path):
                path.mkdir(parents=True)
            logPath = os.path.join(path, data["logFile"])
            with open(logPath, "a") as logFile:
                logFile.write(data["logData"])
        elif "Status" in data and len(hostname) > 0:
            # We don't keep status messages, just pass them along if there's a client listening
            if "Hostname" in data:
                session["hostName"] = data["Hostname"]
            print("Client:", hostname, "Status:", data)
            updateClient(hostname, None, data)
            emit("loggingData", data, to=hostname + "Logging")


@socketio.event
def my_ping():
    # Update their records since they pinged again
    hostName = session.get("hostName", "")
    if len(hostName) > 0:
        updateClient(hostName)
    emit("my_pong")


def updateClient(hostName: str, recentLogFile: str = "", recentStatus: dict = None):
    global clients
    if len(hostName) == 0:
        return

    if hostName not in clients:
        clients[hostName] = {
            "IP": request.remote_addr,
            "Hostname": hostName,
            "Timestamp": time.time(),
        }
    else:
        clients[hostName]["IP"] = request.remote_addr
        clients[hostName]["Timestamp"] = time.time()
    if recentLogFile is not None and len(recentLogFile) > 0:
        clients[hostName]["RecentLog"] = recentLogFile
    if recentStatus is not None:
        clients[hostName]["RecentStatus"] = recentStatus


if __name__ == "__main__":
    fileTempPath = TemporaryDirectory()
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["UPLOAD_FOLDER"] = fileTempPath
    # 256 MB should be more than enough
    app.config["MAX_CONTENT_PATH"] = 256 * 1024 * 1024
    socketio.run(app, host="0.0.0.0")
