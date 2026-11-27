#!/usr/bin/env python3
"""Step 1: can the Pi talk to the ESP32?  (Wheels do NOT move.)

Run on the Pi:   cd ~/404RobotNotFound-robotics/pi && python3 scripts/test_01_serial_ping.py

PASS if: it prints the firmware version, 5 PONG times, and distance
readings that change when you move your hand in front of the ultrasonic sensor.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so "import robot" works

from robot.config import load_config
from robot.logsetup import setup_logging
from robot.ports import find_esp32_port
from robot.serial_link import LinkError, SerialLink


def main() -> int:
    config = load_config()
    config["serial"]["port"] = find_esp32_port(config["serial"]["port"])  # finds COM5 / ttyUSB0 by itself
    setup_logging(config)

    try:
        with SerialLink.from_config(config) as link:
            print(f"Connected. Firmware: {link.firmware_version}")

            print("\nPinging 5 times:")
            for i in range(5):
                rtt = link.ping()
                print(f"  ping {i + 1}: " + (f"{rtt * 1000:.1f} ms" if rtt else "NO ANSWER"))
                time.sleep(0.2)

            print("\nDistance for 5 s (wave your hand in front of the sensor):")
            end = time.monotonic() + 5
            while time.monotonic() < end:
                cm, age = link.distance()
                shown = "no echo" if cm == -1 else f"{cm} cm"
                print(f"  {shown:>8}   (reading is {age * 1000:.0f} ms old)" if cm is not None else "  no reading yet")
                time.sleep(0.5)
    except LinkError as e:
        print(f"\nFAIL: {e}")
        print("Check: USB cable, `ls -l /dev/serial/by-id/`, and serial.port in config.yaml.")
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
