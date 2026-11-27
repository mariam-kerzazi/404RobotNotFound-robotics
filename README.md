# 404RobotNotFound-robotics

A small indoor mecanum robot that drives itself.

- **Raspberry Pi 5** (the brain, Python): vision on the AI HAT+ (Hailo-8L), sensors, decisions.
- **ESP32 on the ACEBOTT car shield** (the body, Arduino C++): wheels, arm servos, ultrasonic sensor.
- The ESP32 plugs into a Pi USB port. They talk over USB serial with the plain-text protocol in
  [docs/protocol.md](docs/protocol.md).

**Safety rule:** whenever something fails or is uncertain, the robot STOPS. The ESP32 stops its own
wheels if the Pi goes quiet for 300 ms.

## Layout

```
docs/protocol.md          Pi <-> ESP32 message format
esp32/robot_body/         ESP32 firmware (open this folder in the Arduino IDE)
  robot_body.ino            main loop: serial commands, watchdog, distance reports
  config.h                  pins, speeds, watchdog time
  motors.cpp                mecanum wheel math
  motor_driver.cpp          shield-specific motor code (TODO: from ACEBOTT sample code)
  ultrasonic.cpp            HC-SR04 reading
  lights.cpp                light strip + LED module
  safety_lock.cpp           PIR: stop everything when a person is near
esp32/tests/              one small sketch per part (I2C scan, PIR, lights)
pi/                       Raspberry Pi code
  config.yaml               all Pi settings
  robot/                    one module per subsystem
    serial_link.py            talk to the ESP32
    protocol.py               build/read protocol lines
  scripts/                  hardware tests, run them in order
  tests/                    unit tests that run on any laptop (fake ESP32, no hardware)
```

## Setup

### Laptop (Windows)

The virtual environment lives **outside** the OneDrive folder, so OneDrive doesn't try to sync
thousands of library files.

```powershell
python -m venv $env:USERPROFILE\.venvs\robot404
& $env:USERPROFILE\.venvs\robot404\Scripts\Activate.ps1
pip install -r requirements-laptop.txt
cd pi; python -m pytest            # 22 tests, no hardware needed
python scripts/check_webcam.py --index 1 --show    # USB webcam (index 0 is usually the built-in one)
```

If PowerShell refuses to run `Activate.ps1`, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

To program the ESP32 from the laptop, also install the **Arduino IDE 2** (or `winget install ArduinoSA.CLI`)
and the **CH340 USB driver** if Windows doesn't show a COM port when the ESP32 is plugged in.

### Pi (`ssh pi@robot1.local`, Raspberry Pi OS "trixie" 64-bit, Python 3.13)

```bash
sudo apt update
sudo apt install -y python3-opencv i2c-tools hailo-all   # hailo-all = AI HAT+ driver + tools; reboot after
git clone -b feature/serial-protocol https://github.com/mariam-kerzazi/404RobotNotFound-robotics.git
python3 -m venv --system-site-packages ~/.venvs/robot404  # can still use apt packages (picamera2, Hailo, lgpio)
~/.venvs/robot404/bin/pip install pytest
source ~/.venvs/robot404/bin/activate
cd 404RobotNotFound-robotics/pi && python -m pytest       # unit tests, no hardware needed
```

Already set on robot1: the `pi` user is in the `dialout`, `i2c` and `gpio` groups, and I2C is on.
Hardware libraries (picamera2, OpenCV, Hailo, lgpio) come from apt, not pip, which is why the venv
uses `--system-site-packages`.

### ESP32

Pins are set for the **ACEBOTT ESP32 Car Shield V2** (QD001 V2 kit), taken from ACEBOTT's
`ACB_SmartCar_V2` library and QD001 sample code:

| What | Pins |
|---|---|
| Motors | Serial2 to the shield's motor chip: TX GPIO17, RX GPIO16, 9600 baud. M1 front-left, M2 rear-left, M3 front-right, M4 rear-right |
| Ultrasonic (the car's own sensor) | Trig GPIO13, Echo GPIO14 |
| PIR motion sensor (HC-SR501), watches behind the robot | GPIO34 (input only) |
| Light strip (UV stand-in) via XY-MOS MOSFET | GPIO22 (I2C header, SCL column) |
| ACEBOTT LED module (follows the strip) | GPIO21 (I2C header, SDA column) |
| Blue LED on the ESP32 board: PIR status | GPIO2. Slow blink = warming up, solid = motion now, fast blink = waiting out the 30 s, short flash every 2 s = clear |

No extra Arduino libraries are needed.

**Safety lock:** if the PIR sees motion, the ESP32 itself stops the wheels and turns the lights off,
and refuses to drive or light up until 30 s pass with no motion. It also starts locked for the PIR's
60 s warm-up. Details in [docs/protocol.md](docs/protocol.md).

**Single-part test sketches** in [esp32/tests/](esp32/tests/) (each replaces the robot firmware
until you upload `robot_body` again):

| Sketch | Checks | Pass when |
|---|---|---|
| `test_01_i2c_scan` | nothing else uses the I2C pins 21/22 | prints PASS (no devices) |
| `test_02_pir` | PIR on GPIO34 | after 60 s warm-up, `PIR 1` when you wave, `PIR 0` a few seconds after you stop |
| `test_03_lights` | strip on GPIO22, LED module on GPIO21 | strip bright, then clearly dimmer, then off; LED on, off, smooth fade |

**Upload from the laptop** (unplug the ESP32's USB cable from the Pi and plug it into the laptop):

```powershell
$cli = "$env:USERPROFILE\.arduino-tools\arduino-cli.exe"
& $cli board list                                   # find the COM port, e.g. COM5
& $cli compile --fqbn esp32:esp32:esp32 esp32/robot_body
& $cli upload  --fqbn esp32:esp32:esp32 -p COM5 esp32/robot_body
& $cli monitor -p COM5 -c baudrate=115200           # expect READY, then DIST lines; type PING -> PONG
```

Or use the Arduino IDE 2: open `esp32/robot_body/robot_body.ino`, board "ESP32 Dev Module", upload,
then Serial Monitor at 115200 with "Newline" line ending.

## Control panel (laptop)

A browser dashboard that runs on the laptop and talks to the Pi over SSH.

```powershell
& $env:USERPROFILE\.venvs\robot404\Scripts\Activate.ps1
pip install -r requirements-laptop.txt     # first time only (adds Flask + paramiko)
python panel/panel.py                      # opens http://127.0.0.1:5050
```

- **Connection:** logs in with the laptop's SSH key. A password is only needed if the key isn't set up.
  It's kept in memory until you close the panel (or press *Forget password*), never saved to disk.
- **Status:** Pi online, power/undervoltage, CPU temperature, Pi camera, webcam, AI HAT, robot code
  version on the Pi, and the ESP32 link (PING + ultrasonic). Works whether the ESP32 is plugged into
  the laptop or the Pi.
- **Unit tests:** runs `pi/tests` on the laptop or on the Pi, with live output.
- **Camera snapshot:** Pi camera or webcam, optional rotation, and basic person detection (OpenCV
  HOG on the laptop; it misses some people and sometimes boxes things that aren't people. The robot
  itself will use the AI HAT).

The panel only listens on `127.0.0.1`, so other computers on the network can't open it.
Code: [panel/](panel/) (`panel.py` = Flask routes, `checks.py` = status checks, `pi_ssh.py` = SSH,
`templates/` + `static/` = the page).

## Step-by-step tests on the real robot

Run from the `pi/` folder on the Pi. Find the serial port with `ls -l /dev/serial/by-id/` and put it in
`config.yaml` under `serial.port`.

| Step | Command | Wheels | Pass when |
|---|---|---|---|
| 1 | `python3 scripts/test_01_serial_ping.py` | don't move | firmware version shown, 5 PONGs, distance changes when you wave a hand |
| 2 | `python3 scripts/test_02_drive_forward.py` | **off the ground** | all 4 wheels spin forward ~1 s, then stop |
| 3 | `python3 scripts/test_03_watchdog.py` | **off the ground** | short twitch, `WDT` after about 300 ms |
| 4 | `python3 scripts/test_04_pir_lights.py` | don't move | unlocks after ~90 s, lights come on, waving at the PIR turns them off and they can't be turned back on |

On the laptop, add `--port COM5` to test 4.

Logs go to `pi/logs/robot.log`.

## Roadmap (one feature branch + PR each)

1. ✅ Serial protocol + drive forward test (`feature/serial-protocol`) — needs testing on the robot
2. Strafe/turn test and wheel direction check
3. Cliff sensor (VL53L0X, pointing down)
4. IMU (BNO055), optional: driving straight and accurate turns. Off by default (`imu_enabled` in config.yaml)
5. ✅ PIR safety lock + lights (on the ESP32) — firmware 0.2.0
6. Person detection: camera + YOLOv8 on the Hailo AI HAT+
7. Behavior engine (fail-safe > cliff > person > obstacle > wander)
8. Laptop override: manual drive + emergency stop over the network
9. Arm servos
10. RPLIDAR C1 (later)

## Workflow

Never push to `main`. Make a feature branch for each piece of work and open a pull request.
