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
import html
import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from operator import itemgetter

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
def status(result=""):
    return render_template("status.html", result=result)


@app.route("/liveLog/<host>")
def liveLog(host):
    pass


@app.route("/viewLog/<host>/<path>")
def viewLog(host, path):
    host = secure_filename(host)
    path = secure_filename(path)
    logPath = os.path.join("data", "logs", host, path)
    logData = ""
    with open(logPath, "r") as logFile:
        logData = logFile.read()
    return render_template("viewlog.html", logData=logData, logName=path)


# def logsHost(host):
#     flashers = None
#     global clients
#     flashers = []
#     keys = list(clients.keys())
#     keys.sort()
#     for client in keys:
#         flasher = clients[client]
#         if "Timestamp" in flasher:
#             lastSeen = time.time() - flasher["Timestamp"]
#             if lastSeen > 60:
#                 continue
#             flasher["LastSeen"] = str(int(lastSeen)) + " Seconds ago"
#         if "Filename" in flasher and len(flasher["Filename"]) == 0:
#             flasher["Filename"] = "No file"
#         flashers.append(flasher)
#     return render_template("hostlogs.html", flashers=flashers)


@app.route("/logs/")
@app.route("/logs/<host>")
def logsHost(host=""):
    if len(host) == 0:
        flashers = None
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
        return render_template("logs.html", flashers=flashers)
    else:
        logfiles = []
        host = secure_filename(host)
        logFilesPath = os.path.join("data", "logs", host)
        if os.path.isdir(logFilesPath):
            files = os.listdir(logFilesPath)
            for file in files:
                if file.endswith(".log"):
                    status = os.stat(Path(logFilesPath, file))
                    logfile = {
                        "Hostname": host,
                        "File": file,
                        "Size": status.st_size,
                        "Timestamp": str(
                            datetime.datetime.fromtimestamp(status.st_mtime)
                        )[:-7],
                    }
                    logfiles.append(logfile)
        logfiles.sort(key=itemgetter("File"), reverse=True)
        return render_template("hostlogs.html", logfiles=logfiles)


@app.route("/logs/")
def logs():
    flashers = None
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
    return render_template("logs.html", flashers=flashers)


@app.route("/upload/")
def upload():
    return render_template("upload.html")


@app.route("/flash/", methods=["POST"])
def flashSelected():
    if (
        "filename" not in request.form
        or "voltage" not in request.form
        or len(request.form["filename"]) == 0
        or len(request.form["voltage"]) == 0
    ):
        return configure()

    filename = html.escape(request.form["filename"])
    voltage = html.escape(request.form["voltage"])
    return render_template("flash.html", filename=filename, voltage=voltage)


@app.route("/verifiedflash/", methods=["POST"])
def verifiedFlashSelected():
    global socketio
    if (
        "filename" not in request.form
        or "voltage" not in request.form
        or len(request.form["filename"]) == 0
        or len(request.form["voltage"]) == 0
    ):
        return configure()

    filename = html.escape(request.form["filename"])
    voltage = html.escape(request.form["voltage"])

    fileData = {"name": filename, "voltage": voltage}
    socketio.emit("newFile", fileData, namespace="/")

    return status("Selected:" + filename + " @ " + voltage + "V")


@app.route("/configure/")
def configure():
    allFiles = os.listdir(filesPath)
    viewFiles = []
    for file in allFiles:
        if ".data.json" in file:
            try:
                with open(Path(filesPath, file), "r") as dataFile:
                    contents = dataFile.read()
                    viewFiles.append(json.loads(contents))
            except Exception as E:
                print("Error loading files:", E)
    return render_template("configure.html", files=viewFiles)


@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/images/<path:path>")
def send_image(path):
    return send_from_directory("images", path)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory("images", "favicon.ico")


@app.route("/loadFile/<name>")
def getFile(name):
    print("Attempting to download file:", name)
    # We do this when saving, so this shouldn't have any ill effects
    name = secure_filename(name)
    fullPath = Path(filesPath, name)
    if os.path.isfile(fullPath):
        return send_file(fullPath)
    return "What are you doing? Users aren't supposed to be here."


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

    # Don't overwrite files, append a numeric suffix
    file_suffix = 2
    ori_filename = filename
    while True:
        fullPath = os.path.join(filesPath, filename)
        if os.path.isfile(fullPath):
            path = Path(ori_filename)
            filename = path.stem + "-" + str(file_suffix) + path.suffix
            file_suffix += 1
        else:
            break

    file.save(fullPath)

    fileData = {
        "filename": filename,
        "voltage": request.form["voltage"],
        "desc": request.form["desc"],
        "size": os.stat(fullPath).st_size,
        "uploaded": str(datetime.datetime.now()),
    }

    fullDataPath = os.path.join(filesPath, filename + ".data.json")
    with open(fullDataPath, "w") as dataFile:
        dataFile.write(json.dumps(fileData, indent=4))

    print("Saved file to:", fullPath, " data to:", fullDataPath)
    return render_template("upload.html", result="Saved uploaded file: " + filename)


@socketio.event
def newFileSelected(fileData):
    print("Selecting new file:", fileData)
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


@socketio.event
def joinStatus(message):
    print("Client joined Status room")
    join_room("Status")


@socketio.event
def leaveStatus(message):
    print("Client left Status room")
    leave_room("Status")


@socketio.on("loggingData")
def loggingData(data=None):
    if (
        data is not None
        and "Hostname" in data
        and len(data["Hostname"]) > 0
        and "logFile" in data
        and "logData" in data
    ):
        hostname = data["Hostname"]
        session["hostName"] = hostname
        # print(hostname, "logged to", data["logFile"], data["logData"])
        # Update client data and send it to the WS room if anyone is listening
        updateClient(hostname, data["logFile"])
        emit("loggingData", data, to=hostname + "Logging")
        # Save it
        path = Path("data", "logs", hostname)
        if not os.path.isdir(path):
            path.mkdir(parents=True)
        logPath = os.path.join(path, data["logFile"])
        with open(logPath, "a") as logFile:
            logFile.write(data["logData"])


@socketio.on("statusData")
def statusData(data=None):
    # print("Status received:", data)
    if (
        data is not None
        and "Hostname" in data
        and "Status" in data
        and len(data["Hostname"]) > 0
    ):
        hostname = data["Hostname"]
        session["hostName"] = hostname
        # We don't keep status messages, just pass them along if there's a client listening
        # print("Client:", hostname, "Status:", data)
        updateClient(hostname, None, data)
        data["IP"] = request.remote_addr
        emit("statusData", data, to="Status")


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
