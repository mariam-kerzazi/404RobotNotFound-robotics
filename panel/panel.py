"""404RobotNotFound control panel.

Run on the LAPTOP:
    & $env:USERPROFILE\\.venvs\\robot404\\Scripts\\Activate.ps1
    python panel/panel.py

It opens http://127.0.0.1:5050 in your browser. From there you can:
  - connect to the Pi (SSH key, or a password kept only in memory)
  - run status checks on the Pi, cameras, AI HAT and ESP32
  - run the unit tests on the laptop and on the Pi, with live output
  - take a camera snapshot and look for people in it

How it's built: Flask serves one HTML page (templates/index.html). The page's
JavaScript (static/panel.js) calls the /api/... routes below, which do the
real work in Python.
"""
import base64
import shlex
import subprocess
import sys
import threading
import time
import webbrowser

import cv2
import numpy as np
from flask import Flask, abort, jsonify, render_template, request

import checks
import detect
import jobs
from pi_ssh import PiConnection
from settings import (DEFAULT_HOST, DEFAULT_USER, PANEL_HOST, PANEL_PORT, PI_CODE_DIR,
                      REMOTE_PYTHON, REMOTE_REPO)

app = Flask(__name__)
pi = PiConnection(DEFAULT_HOST, DEFAULT_USER)


# ---------------------------------------------------------------------------
# Safety: only our own page may call the API
# ---------------------------------------------------------------------------
# A random website open in another tab could try to send requests to
# 127.0.0.1:5050. Browsers won't let other sites add custom headers without
# permission (which we never give), so requiring this header blocks them.

@app.before_request
def require_panel_header():
    if request.path.startswith("/api/") and request.headers.get("X-Robot-Panel") != "1":
        abort(403)


def ok(**data):
    return jsonify(ok=True, **data)


def fail(message: str, status: int = 400):
    return jsonify(ok=False, error=message), status


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Connection + password
# ---------------------------------------------------------------------------

def connection_state() -> dict:
    return {
        "host": pi.host,
        "user": pi.user,
        "connected": pi.is_connected(),
        "auth_method": pi.auth_method,
        "has_password": pi.has_password,  # True/False only, never the password itself
        "error": pi.last_error,
    }


@app.get("/api/connection")
def get_connection():
    return ok(**connection_state())


@app.post("/api/connection")
def post_connection():
    body = request.get_json(silent=True) or {}
    if body.get("password"):
        pi.set_password(body["password"])
    try:
        pi.connect(body.get("host"), body.get("user"))
    except Exception as e:
        return fail(str(e))
    return ok(**connection_state())


@app.post("/api/password/forget")
def forget_password():
    pi.forget_password()
    return ok(**connection_state())


# ---------------------------------------------------------------------------
# Status checks
# ---------------------------------------------------------------------------

@app.post("/api/status")
def status():
    start = time.monotonic()
    results = checks.run_all(pi)
    return ok(checks=results, took_s=round(time.monotonic() - start, 1), connection=connection_state())


# ---------------------------------------------------------------------------
# Unit tests (run as background jobs so output appears live)
# ---------------------------------------------------------------------------

def run_laptop_tests(add_line) -> int:
    add_line(f"$ python -m pytest -v   (in {PI_CODE_DIR})")
    proc = subprocess.Popen(
        [sys.executable, "-m", "pytest", "-v", "--color=no"],
        cwd=PI_CODE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding="utf-8", errors="replace",
    )
    for line in proc.stdout:
        add_line(line.rstrip("\n"))
    return proc.wait()


def run_pi_tests(add_line) -> int:
    command = f"cd {REMOTE_REPO}/pi && git log -1 --format='Pi code: %h %s' && {REMOTE_PYTHON} -m pytest -v --color=no"
    add_line(f"$ ssh {pi.user}@{pi.host} pytest -v")
    return pi.stream(command, add_line)


@app.post("/api/tests/<target>")
def start_tests(target):
    if target == "laptop":
        job = jobs.start("Unit tests on laptop", run_laptop_tests)
    elif target == "pi":
        job = jobs.start("Unit tests on Pi", run_pi_tests)
    else:
        return fail("unknown test target", 404)
    return ok(job_id=job.id)


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if job is None:
        return fail("no such job", 404)
    return ok(**job.snapshot(int(request.args.get("since", 0))))


# ---------------------------------------------------------------------------
# Camera snapshot (+ optional person detection)
# ---------------------------------------------------------------------------

# Degrees clockwise -> OpenCV rotation (for cameras mounted sideways).
ROTATIONS = {
    0: None,
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def capture_command(camera: str) -> str:
    if camera == "picam":
        # Pi Camera v2: take one photo and send the JPEG to stdout.
        return "rpicam-still -n -t 800 --width 1280 --height 960 -e jpg -o - 2>/dev/null"
    if camera == "webcam":
        device = checks.robot_config().get("camera", {}).get("usb_device")
        if not device:
            raise ValueError("camera.usb_device is not set in pi/config.yaml")
        # Skip the first 15 frames so the webcam's auto-exposure can settle.
        return (f"v4l2-ctl -d {shlex.quote(device)} "
                "--set-fmt-video=width=1280,height=720,pixelformat=MJPG "
                "--stream-mmap --stream-skip=15 --stream-count=1 --stream-to=- 2>/dev/null")
    raise ValueError(f"unknown camera {camera!r}")


@app.post("/api/snapshot")
def snapshot():
    body = request.get_json(silent=True) or {}
    camera = body.get("camera", "picam")
    want_detection = bool(body.get("detect"))
    rotation = int(body.get("rotate", 0))
    if rotation not in ROTATIONS:
        return fail("rotate must be 0, 90, 180 or 270")
    try:
        start = time.monotonic()
        code, data, _ = pi.run(capture_command(camera), timeout=20, binary=True)
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return fail(f"the camera didn't return a picture (exit code {code}). Is another program using it?")
        capture_s = time.monotonic() - start

        # Turn the picture upright first: the people detector only finds upright people.
        if ROTATIONS[rotation] is not None:
            image = cv2.rotate(image, ROTATIONS[rotation])

        boxes = []
        if want_detection:
            boxes = detect.detect_people(image)
            detect.draw_boxes(image, boxes)

        _, jpg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    except Exception as e:
        return fail(str(e))

    return ok(
        image="data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode("ascii"),
        width=image.shape[1], height=image.shape[0],
        capture_s=round(capture_s, 1),
        people=len(boxes) if want_detection else None,
        method=detect.METHOD_NAME if want_detection else None,
    )


# ---------------------------------------------------------------------------

def main():
    url = f"http://{PANEL_HOST}:{PANEL_PORT}"
    print(f"Robot panel running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    # Try connecting in the background so the page shows the Pi's state quickly.
    threading.Thread(target=lambda: _try_connect(), daemon=True).start()
    app.run(host=PANEL_HOST, port=PANEL_PORT, debug=False, threaded=True)


def _try_connect():
    try:
        pi.connect()
    except Exception:
        pass  # the page shows the error and lets you type a password


if __name__ == "__main__":
    main()
