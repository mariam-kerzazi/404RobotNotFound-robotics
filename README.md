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
pi/                       Raspberry Pi code
  config.yaml               all Pi settings
  robot/                    one module per subsystem
    serial_link.py            talk to the ESP32
    protocol.py               build/read protocol lines
  scripts/                  hardware tests, run them in order
  tests/                    unit tests that run on any laptop (fake ESP32, no hardware)
```

## Setup

### Pi (Raspberry Pi OS Bookworm 64-bit)

```bash
sudo apt update
sudo apt install -y git python3-serial python3-yaml python3-pytest
sudo usermod -aG dialout $USER     # lets you open the serial port; log out and back in afterwards
git clone https://github.com/mariam-kerzazi/404RobotNotFound-robotics.git
cd 404RobotNotFound-robotics/pi
python3 -m pytest                  # unit tests, no hardware needed
```

We use apt packages instead of `pip install` because Bookworm blocks system-wide pip, and the camera
and Hailo libraries we add later also come from apt.

### ESP32

1. Install the Arduino IDE and the **esp32 by Espressif** board package.
2. Fill in the pins in `esp32/robot_body/config.h` and `motor_driver.cpp` from the ACEBOTT sample code,
   then set `PINS_CONFIRMED` to `1`. Until then the sketch stops on purpose with a "Pins not set yet" error.
3. Open `esp32/robot_body/robot_body.ino` and upload it.
4. Check it in the Serial Monitor (115200 baud, "Newline" line ending): you should see `READY` and then
   `DIST ...` lines. Type `PING` and you should get `PONG` back.

## Step-by-step tests on the real robot

Run from the `pi/` folder on the Pi. Find the serial port with `ls -l /dev/serial/by-id/` and put it in
`config.yaml` under `serial.port`.

| Step | Command | Wheels | Pass when |
|---|---|---|---|
| 1 | `python3 scripts/test_01_serial_ping.py` | don't move | firmware version shown, 5 PONGs, distance changes when you wave a hand |
| 2 | `python3 scripts/test_02_drive_forward.py` | **off the ground** | all 4 wheels spin forward ~1 s, then stop |
| 3 | `python3 scripts/test_03_watchdog.py` | **off the ground** | short twitch, `WDT` after about 300 ms |

Logs go to `pi/logs/robot.log`.

## Roadmap (one feature branch + PR each)

1. ✅ Serial protocol + drive forward test (`feature/serial-protocol`) — motor and ultrasonic pins still to fill in
2. Strafe/turn test and wheel direction check
3. Cliff sensor (VL53L0X, pointing down)
4. IMU (BNO055): driving straight and accurate turns
5. PIR motion sensor + LED underglow light states
6. Person detection: camera + YOLOv8 on the Hailo AI HAT+
7. Behavior engine (fail-safe > cliff > person > obstacle > wander)
8. Laptop override: manual drive + emergency stop over the network
9. Arm servos
10. RPLIDAR C1 (later)

## Workflow

Never push to `main`. Make a feature branch for each piece of work and open a pull request.
