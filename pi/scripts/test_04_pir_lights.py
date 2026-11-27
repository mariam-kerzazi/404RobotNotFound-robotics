#!/usr/bin/env python3
"""Step 4: PIR safety lock and lights.  (Wheels do NOT move.)

The lights stand in for UV, so a person nearby must switch them off.

Run on the Pi:      cd ~/404RobotNotFound-robotics/pi && python3 scripts/test_04_pir_lights.py
Run on the laptop:  cd pi && python scripts/test_04_pir_lights.py --port COM5

What happens:
  1. Waits until the ESP32 unlocks (PIR warm-up 60 s, then 30 s with no motion).
     Stay out of the PIR's view.
  2. Turns the lights on. Check that the strip and the LED module light up.
  3. Asks you to wave at the PIR. The ESP32 must lock and turn the lights off by itself.
  4. Tries to turn the lights on again. The ESP32 must refuse ("ERR locked person").

PASS if every step prints OK.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so "import robot" works

from robot.config import load_config
from robot.logsetup import setup_logging
from robot.serial_link import LinkError, SerialLink

UNLOCK_WAIT_S = 240   # warm-up (60 s) + quiet time (30 s), with plenty of room for motion
WAVE_WAIT_S = 60


def wait_until(condition, seconds, show=None):
    """Check condition() every 0.2 s for up to `seconds`. Returns True if it became true."""
    end = time.monotonic() + seconds
    last_shown = 0.0
    while time.monotonic() < end:
        if condition():
            return True
        if show and time.monotonic() - last_shown >= 5:
            last_shown = time.monotonic()
            show()
        time.sleep(0.2)
    return condition()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="serial port, e.g. COM5 (default: serial.port in config.yaml)")
    args = parser.parse_args()

    config = load_config()
    if args.port:
        config["serial"]["port"] = args.port
    setup_logging(config)

    ok = True
    try:
        with SerialLink.from_config(config) as link:
            print(f"Connected. Firmware: {link.firmware_version or '(no READY seen)'}")
            wait_until(lambda: link.lock_reason() is not None, 3)

            print("\n1. Waiting for the ESP32 to unlock. Stay out of the PIR's view...")
            unlocked = wait_until(
                lambda: not link.is_locked(), UNLOCK_WAIT_S,
                show=lambda: print(f"   still locked ({link.lock_reason()}), PIR={link.pir()}"),
            )
            if not unlocked:
                print(f"FAIL: still locked after {UNLOCK_WAIT_S} s (PIR={link.pir()}). "
                      "Is something moving in view, or is the PIR's Time knob turned up?")
                return 1
            print("   OK: unlocked")

            print("\n2. Lights ON for 3 s: the strip (MOSFET board LED) and the LED module should light up.")
            link.light(255)
            time.sleep(3)
            if link.last_error:
                print(f"   FAIL: ESP32 said {link.last_error}")
                ok = False
            else:
                print("   OK: ESP32 accepted LIGHT 255")

            print(f"\n3. Now WAVE at the PIR (waiting up to {WAVE_WAIT_S} s)...")
            if wait_until(lambda: link.lock_reason() == "person", WAVE_WAIT_S):
                print("   OK: person seen, ESP32 locked. The lights should be OFF now.")
            else:
                print("   FAIL: no motion seen")
                return 1

            print("\n4. Trying to turn the lights back on while locked...")
            link.last_error = None
            link.light(255)
            time.sleep(0.5)
            if link.last_error == "locked person":
                print("   OK: refused (ERR locked person), lights stay off")
            else:
                print(f"   FAIL: expected 'locked person', got {link.last_error!r}")
                ok = False
            link.light(0)
    except LinkError as e:
        print(f"\nFAIL: {e}")
        print("Check: USB cable, `ls -l /dev/serial/by-id/`, and serial.port in config.yaml (or --port).")
        return 1

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
