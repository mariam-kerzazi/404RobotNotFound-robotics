#!/usr/bin/env python3
"""Robot console: try out what the robot can do, by typing commands.

Run on the laptop (ESP32 on USB):   cd pi && python main.py
Run on the Pi:                      cd ~/404RobotNotFound-robotics/pi && python3 main.py
In VS Code: Run and Debug -> "Robot: main program" (or press F5).

The ESP32 port is found automatically. Use --port COM5 to choose it yourself.

Safety (all enforced by the ESP32 itself, not just this program):
- PIR sees motion -> wheels stop and lights (UV stand-in) go off, locked until 30 s of no motion.
- Wheels stop by themselves if MOVE isn't repeated every 300 ms.
- Leaving this program (quit, Ctrl+C or an error) stops the wheels and turns the lights off.

Later this file becomes the robot's self-driving program; for now it's a hands-on console.
"""
import argparse
import logging
import sys
import time

from robot.config import load_config
from robot.logsetup import setup_logging
from robot.ports import find_esp32_port
from robot.serial_link import LinkError, SerialLink

HELP = """
Commands:
  status              everything the robot knows right now (just Enter does this too)
  on | off            lights (UV stand-in) full on / off; the LED module follows
  light <0-255>       lights at a brightness
  ping                round-trip time to the ESP32
  watch [seconds]     live status every 0.5 s (default 10 s; Ctrl+C stops early)
  drive <dir> [sec]   wheels, dir = forward back left right turnleft turnright (default 1 s)
                      needs the 18650 batteries; wheels off the ground the first time!
  stop                stop the wheels
  help                this list
  quit                lights off, wheels stopped, exit
""".strip()

# (vx forward, vy left, wz counter-clockwise) for each drive direction
DIRECTIONS = {
    "forward": (1, 0, 0), "back": (-1, 0, 0),
    "left": (0, 1, 0), "right": (0, -1, 0),
    "turnleft": (0, 0, 1), "turnright": (0, 0, -1),
}


class Console:
    def __init__(self, link: SerialLink, speed: float):
        self.link = link
        self.speed = speed
        self.light_level = 0
        self.drive_confirmed = False

    # ---------------------------------------------------------------- display

    def status_line(self) -> str:
        cm, age = self.link.distance()
        dist = "no reading" if cm is None else ("no echo" if cm == -1 else f"{cm} cm")
        pir = {None: "?", -1: "warming up", 0: "quiet", 1: "MOTION"}[self.link.pir()]
        reason = self.link.lock_reason()
        lock = "unknown (treat as locked)" if reason is None else (f"LOCKED ({reason})" if reason else "unlocked")
        return f"distance {dist:>9} | PIR {pir:<10} | {lock:<17} | lights {self.light_level}"

    def show_status(self) -> None:
        link = self.link
        print(f"  ESP32      {'connected' if link.is_alive() else 'NOT ANSWERING'}"
              f" on {link.port}, firmware {link.firmware_version or '(no READY seen)'}")
        print(f"  now        {self.status_line()}")
        print(f"  watchdog   stopped the wheels {link.watchdog_count} time(s)")
        if link.restart_count:
            print(f"  restarts   ESP32 rebooted {link.restart_count} time(s) while connected (power dip?)")
        if link.last_error:
            print(f"  last error {link.last_error}")
        if link.is_locked():
            print("  (while locked the ESP32 refuses lights and driving; it unlocks after 30 s with no motion)")

    def watch(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        try:
            while time.monotonic() < end:
                print("  " + self.status_line())
                time.sleep(0.5)
        except KeyboardInterrupt:
            print()

    # ---------------------------------------------------------------- actions

    def set_lights(self, level: int) -> None:
        self.link.last_error = None
        self.link.light(level)
        time.sleep(0.2)  # give the ESP32 time to answer
        if self.link.last_error:
            print(f"  refused: {self.link.last_error}")
            self.light_level = 0
        else:
            self.light_level = level
            print(f"  lights {level}")

    def drive(self, direction: str, seconds: float) -> None:
        if direction not in DIRECTIONS:
            print(f"  unknown direction; use one of: {' '.join(DIRECTIONS)}")
            return
        if not 0 < seconds <= 3:
            print("  keep it between 0 and 3 seconds")
            return
        if self.link.is_locked():
            print(f"  locked ({self.link.lock_reason()}): the ESP32 won't drive yet")
            return
        if not self.drive_confirmed:
            answer = input("  Wheels off the ground (or floor clear)? Type y: ")
            if answer.strip().lower() != "y":
                print("  cancelled")
                return
            self.drive_confirmed = True
        vx, vy, wz = (self.speed * v for v in DIRECTIONS[direction])
        self.link.last_error = None
        print(f"  {direction} at {self.speed:.2f} for {seconds:.1f} s (Ctrl+C stops)")
        self.link.move_for(vx, vy, wz, seconds)
        if self.link.last_error:
            print(f"  ESP32 said: {self.link.last_error}")

    # ---------------------------------------------------------------- loop

    def run(self) -> None:
        print(HELP)
        print()
        self.show_status()
        while True:
            try:
                words = input("\nrobot> ").strip().lower().split()
            except EOFError:
                return
            cmd, args = (words[0], words[1:]) if words else ("status", [])
            try:
                if cmd in ("quit", "exit", "q"):
                    return
                elif cmd == "status":
                    self.show_status()
                elif cmd == "help":
                    print(HELP)
                elif cmd == "on":
                    self.set_lights(255)
                elif cmd == "off":
                    self.set_lights(0)
                elif cmd == "light" and len(args) == 1:
                    self.set_lights(int(args[0]))
                elif cmd == "ping":
                    rtt = self.link.ping()
                    print(f"  PONG in {rtt * 1000:.1f} ms" if rtt is not None else "  no answer")
                elif cmd == "watch":
                    self.watch(float(args[0]) if args else 10)
                elif cmd == "drive" and args:
                    self.drive(args[0], float(args[1]) if len(args) > 1 else 1.0)
                elif cmd == "stop":
                    self.link.stop()
                    print("  stopped")
                else:
                    print("  don't know that one; type help")
            except ValueError as e:
                print(f"  bad value: {e}")
            except LinkError as e:
                print(f"  link problem: {e} (wheels stop by themselves)")
            except KeyboardInterrupt:
                self.link.stop()
                print("\n  stopped (Ctrl+C again at the prompt to quit)")


def main() -> int:
    config = load_config()
    parser = argparse.ArgumentParser(description="Robot console")
    parser.add_argument("--port", help="serial port, e.g. COM5 or /dev/ttyUSB0 (default: find it)")
    parser.add_argument("--verbose", action="store_true", help="show every log message on screen")
    args = parser.parse_args()

    setup_logging(config)
    if not args.verbose:
        # Keep the console readable: details still go to logs/robot.log.
        logging.getLogger().handlers[1].setLevel(logging.WARNING)

    port = args.port or find_esp32_port(config["serial"]["port"])
    if not port:
        print("Can't find the ESP32. Is its USB cable plugged in? (Or give --port.)")
        return 1
    config["serial"]["port"] = port

    print(f"Connecting to the ESP32 on {port}...")
    try:
        with SerialLink.from_config(config) as link:
            time.sleep(1.2)  # let the first PIR / LOCK / DIST messages arrive
            console = Console(link, speed=config["drive"]["test_speed"])
            try:
                console.run()
            finally:
                try:
                    link.light(0)  # UV stand-in off whenever we leave
                except LinkError:
                    pass
    except LinkError as e:
        print(f"ESP32 problem: {e}")
        print("Is another program using the port (Arduino serial monitor, a test script)?")
        return 1
    except KeyboardInterrupt:
        pass
    print("Bye: wheels stopped, lights off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
