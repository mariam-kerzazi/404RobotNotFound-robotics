"""Status checks: what's connected, and is it healthy?

Each check returns a dict:
    {"name": "Pi camera", "state": "ok" | "warn" | "fail" | "info", "detail": "imx219 (Camera v2)"}

Most Pi checks run as ONE small bash script over SSH, so the whole check
takes a couple of seconds instead of one round trip per item.
"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import serial.tools.list_ports
import yaml

from settings import PI_CODE_DIR, REMOTE_PYTHON, REMOTE_REPO, REPO_DIR

# Let us import the robot's own serial code from pi/robot/.
sys.path.insert(0, str(PI_CODE_DIR))
from robot.serial_link import LinkError, SerialLink  # noqa: E402

CH340_VID = 0x1A86  # the USB chip on the ESP32 Max board


def item(name: str, state: str, detail: str) -> dict:
    return {"name": name, "state": state, "detail": detail}


def robot_config() -> dict:
    with open(PI_CODE_DIR / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Pi checks (one SSH round trip)
# ---------------------------------------------------------------------------

PI_STATUS_SCRIPT = r"""
echo "uptime	$(uptime -p)"
echo "throttled	$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)"
echo "temp	$(vcgencmd measure_temp 2>/dev/null | sed 's/temp=//; s/.C$//')"
echo "cameras	$(rpicam-hello --list-cameras 2>&1 | grep -oE '^ *[0-9]+ : [a-z0-9_]+' | sed 's/^ *//' | paste -sd ';')"
echo "webcam	$( [ -e "$WEBCAM" ] && echo yes || echo no )"
echo "hailo_pci	$(lspci 2>/dev/null | grep -i hailo | head -1)"
echo "hailo_dev	$(ls /dev/hailo0 2>/dev/null)"
echo "esp32	$(ls /dev/serial/by-id/ 2>/dev/null | paste -sd ';')"
echo "repo	$(git -C REPO log -1 --format='%h %s' 2>/dev/null)"
"""


def throttled_check(value: str) -> dict:
    """Explain `vcgencmd get_throttled` in plain English."""
    try:
        bits = int(value, 16)
    except ValueError:
        return item("Power", "warn", f"couldn't read throttle state ({value!r})")
    if bits & 0x1:
        return item("Power", "fail", "UNDER-VOLTAGE RIGHT NOW: power supply is too weak")
    if bits & 0x4:
        return item("Power", "fail", "Pi is being throttled right now")
    if bits & 0x50000:
        return item("Power", "warn",
                    f"under-voltage/throttling happened since boot ({value}). Laptop USB power is too weak; "
                    "use the 5V/5A supply for real runs")
    return item("Power", "ok", "power supply is fine")


def pi_checks(pi, webcam_path: str) -> List[dict]:
    script = f"WEBCAM='{webcam_path}'\n" + PI_STATUS_SCRIPT.replace("REPO", REMOTE_REPO)
    code, out, err = pi.run("bash -s", stdin_data=script, timeout=20)
    info = {}
    for line in out.splitlines():
        key, _, value = line.partition("\t")
        info[key] = value.strip()

    results = [item("Pi online", "ok", f"{pi.user}@{pi.host} via {pi.auth_method}, {info.get('uptime', '')}")]
    results.append(throttled_check(info.get("throttled", "")))

    try:
        temp = float(info.get("temp", ""))
        state = "ok" if temp < 70 else "warn" if temp < 80 else "fail"
        results.append(item("CPU temperature", state, f"{temp:.1f} °C"))
    except ValueError:
        results.append(item("CPU temperature", "warn", "couldn't read"))

    cams = info.get("cameras", "")
    if "imx219" in cams:
        results.append(item("Pi camera", "ok", "imx219 (Camera Module v2)"))
    elif cams:
        results.append(item("Pi camera", "ok", cams))
    else:
        results.append(item("Pi camera", "fail", "no camera found: check the ribbon cable"))

    if info.get("webcam") == "yes":
        results.append(item("USB webcam", "ok", "Logitech Brio 101 connected"))
    else:
        results.append(item("USB webcam", "fail", "not found: is it plugged into the Pi?"))

    if info.get("hailo_pci") and info.get("hailo_dev"):
        results.append(item("AI HAT (Hailo)", "ok", "detected and driver loaded"))
    elif info.get("hailo_pci"):
        results.append(item("AI HAT (Hailo)", "warn",
                            "hardware detected, software not installed (sudo apt install hailo-all, then reboot)"))
    else:
        results.append(item("AI HAT (Hailo)", "fail", "not detected on PCIe: check the HAT and ribbon"))

    results.append(code_version_check(info.get("repo", "")))
    results.append({"_esp32_on_pi": info.get("esp32", "")})  # used by run_all(), removed there
    return results


def code_version_check(pi_repo: str) -> dict:
    try:
        laptop = subprocess.run(["git", "-C", str(REPO_DIR), "log", "-1", "--format=%h"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        laptop = ""
    if not pi_repo:
        return item("Robot code on Pi", "warn", "repo not found on the Pi")
    pi_hash = pi_repo.split(" ")[0]
    if laptop and pi_hash == laptop:
        return item("Robot code on Pi", "ok", f"same as laptop: {pi_repo}")
    return item("Robot code on Pi", "info", f"Pi has {pi_repo}; laptop is at {laptop or '?'}")


# ---------------------------------------------------------------------------
# ESP32 (could be plugged into the laptop OR the Pi)
# ---------------------------------------------------------------------------

def laptop_esp32_port() -> Optional[str]:
    for p in serial.tools.list_ports.comports():
        if p.vid == CH340_VID:
            return p.device
    return None


def esp32_check_laptop(port: str) -> dict:
    try:
        with SerialLink(port, ready_timeout_s=3.0) as link:
            rtt = link.ping()
            time.sleep(0.3)  # give it time to send a DIST reading
            cm, _ = link.distance()
    except LinkError as e:
        return item("ESP32 link", "fail", f"on laptop {port}, not answering: {e}")
    rtt_txt = f"{rtt * 1000:.0f} ms" if rtt else "no PONG"
    dist = "no echo" if cm in (None, -1) else f"{cm} cm"
    return item("ESP32 link", "ok" if rtt else "warn",
                f"plugged into the LAPTOP ({port}). PING {rtt_txt}, ultrasonic {dist}")


ESP32_PI_SCRIPT = r"""
cd REPO/pi || exit 1
PY=PYTHON; [ -x "$PY" ] || PY=python3
"$PY" - <<'EOF'
import glob, sys, time
sys.path.insert(0, '.')
from robot.serial_link import SerialLink, LinkError
ports = sorted(glob.glob('/dev/serial/by-id/*'))
try:
    with SerialLink(ports[0], ready_timeout_s=4.0) as link:
        rtt = link.ping()
        time.sleep(0.3)
        cm, _ = link.distance()
        print(f"OK\t{ports[0]}\t{rtt}\t{cm}\t{link.firmware_version}")
except LinkError as e:
    print(f"FAIL\t{ports[0]}\t{e}")
EOF
"""


def esp32_check_pi(pi) -> dict:
    script = ESP32_PI_SCRIPT.replace("REPO", REMOTE_REPO).replace("PYTHON", REMOTE_PYTHON)
    _, out, _ = pi.run("bash -s", stdin_data=script, timeout=20)
    parts = out.strip().splitlines()[-1].split("\t") if out.strip() else ["FAIL", "?", "no output"]
    if parts[0] != "OK":
        return item("ESP32 link", "fail", f"on the Pi, not answering: {parts[-1]}")
    _, port, rtt, cm, fw = parts
    rtt_txt = f"{float(rtt) * 1000:.0f} ms" if rtt != "None" else "no PONG"
    dist = "no echo" if cm in ("None", "-1") else f"{cm} cm"
    return item("ESP32 link", "ok", f"plugged into the Pi. Firmware {fw}, PING {rtt_txt}, ultrasonic {dist}")


# ---------------------------------------------------------------------------

def run_all(pi) -> List[dict]:
    webcam = robot_config().get("camera", {}).get("usb_device") or "/dev/null/none"

    # The laptop ESP32 check and the Pi checks don't depend on each other: run both at once.
    with ThreadPoolExecutor(max_workers=2) as pool:
        laptop_port = laptop_esp32_port()
        laptop_future = pool.submit(esp32_check_laptop, laptop_port) if laptop_port else None
        try:
            if not pi.is_connected():
                pi.connect()
            pi_results = pi_checks(pi, webcam)
        except Exception as e:
            pi_results = [item("Pi online", "fail", str(e)), {"_esp32_on_pi": ""}]

    esp32_on_pi = pi_results.pop()["_esp32_on_pi"]
    if laptop_future:
        esp32 = laptop_future.result()
    elif esp32_on_pi and pi.is_connected():
        esp32 = esp32_check_pi(pi)
    else:
        esp32 = item("ESP32 link", "fail", "not plugged into the laptop or the Pi")
    return pi_results + [esp32]
