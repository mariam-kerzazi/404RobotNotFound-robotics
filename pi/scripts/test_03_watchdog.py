#!/usr/bin/env python3
"""Step 3: prove the ESP32 stops by itself when the Pi goes quiet.

!!! WHEELS OFF THE GROUND. !!!

The script sends ONE MOVE and then deliberately sends nothing else.
The ESP32 should stop the wheels about 0.3 s later and report WDT.

Run on the Pi:   cd ~/404RobotNotFound-robotics/pi && python3 scripts/test_03_watchdog.py

PASS if: the wheels give a short twitch (~0.3 s) and the script prints PASS.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from robot.config import load_config
from robot.logsetup import setup_logging
from robot.ports import find_esp32_port
from robot.serial_link import LinkError, SerialLink


def main() -> int:
    config = load_config()
    config["serial"]["port"] = find_esp32_port(config["serial"]["port"])  # finds COM5 / ttyUSB0 by itself
    setup_logging(config)

    answer = input("Are all four wheels OFF the ground? Type y: ")
    if answer.strip().lower() != "y":
        print("Cancelled.")
        return 1

    try:
        with SerialLink.from_config(config) as link:
            speed = config["drive"]["test_speed"]
            start = time.monotonic()
            link.move(speed, 0.0, 0.0)  # one MOVE, then silence
            while link.watchdog_count == 0 and time.monotonic() - start < 1.0:
                time.sleep(0.01)
            elapsed = time.monotonic() - start

            if link.watchdog_count == 0:
                print("FAIL: no WDT within 1 s. Did the wheels keep spinning? Check WATCHDOG_MS in the firmware.")
                return 1
            print(f"WDT received after {elapsed * 1000:.0f} ms (expected about 300 ms).")
    except LinkError as e:
        print(f"\nFAIL: {e}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
