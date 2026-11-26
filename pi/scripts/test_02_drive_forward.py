#!/usr/bin/env python3
"""Step 2: drive forward for 1 second, then stop.

!!! Put the robot on a box with ALL FOUR WHEELS OFF THE GROUND the first time. !!!

Run on the Pi:   cd ~/404RobotNotFound-robotics/pi && python3 scripts/test_02_drive_forward.py
Options:         --speed 0.3   --seconds 1.0

PASS if: all four wheels spin "forward" for about 1 s and then stop.
If one wheel spins backward, set its entry in WHEEL_INVERT in
esp32/robot_body/config.h to true and re-upload the firmware.

Ctrl+C at any time stops the robot.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from robot.config import load_config
from robot.logsetup import setup_logging
from robot.serial_link import LinkError, SerialLink


def main() -> int:
    config = load_config()
    setup_logging(config)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--speed", type=float, default=config["drive"]["test_speed"])
    parser.add_argument("--seconds", type=float, default=1.0)
    args = parser.parse_args()

    if not 0 < args.speed <= 0.6:
        print("For this test keep --speed between 0 and 0.6.")
        return 1

    answer = input("Are all four wheels OFF the ground (or is the floor clear)? Type y: ")
    if answer.strip().lower() != "y":
        print("Cancelled.")
        return 1

    try:
        with SerialLink.from_config(config) as link:
            print(f"Driving forward at {args.speed:.2f} for {args.seconds:.1f} s...")
            link.move_for(args.speed, 0.0, 0.0, seconds=args.seconds)
            print("Stopped.")
            if link.watchdog_count:
                print(f"WARNING: the ESP32 watchdog fired {link.watchdog_count} time(s) — MOVE was sent too slowly.")
            if link.last_error:
                print(f"WARNING: ESP32 reported an error: {link.last_error}")
    except LinkError as e:
        print(f"\nFAIL: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nCtrl+C — robot stopped.")  # the `with` block already sent STOP
        return 1

    print("Did all four wheels spin forward and then stop? If yes: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
