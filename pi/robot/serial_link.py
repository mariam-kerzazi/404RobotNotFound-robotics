"""Talk to the ESP32 (the robot's body) over USB serial.

Usage:

    with SerialLink.from_config(config) as link:
        link.move_for(0.3, 0.0, 0.0, seconds=1.0)   # forward for 1 s, then stop

Safety design:
- The ESP32 stops the wheels by itself if no MOVE arrives for 300 ms, so
  to keep driving you must call move() about 10 times a second (move_for()
  does this for you).
- move() refuses to send if the ESP32 has been silent for link_timeout_s
  and raises LinkError instead. Treat LinkError as "STOP, lights red".
- Leaving the `with` block (normally, by error, or by Ctrl+C) sends STOP.
"""
import logging
import threading
import time
from typing import Callable, Optional, Tuple

import serial

from robot import protocol

log = logging.getLogger(__name__)


class LinkError(RuntimeError):
    """The ESP32 is not answering. The robot must be treated as stopped."""


class SerialLink:
    def __init__(
        self,
        port: str,
        baud: int = 115200,
        ready_timeout_s: float = 5.0,
        link_timeout_s: float = 0.5,
        move_rate_hz: float = 10,
        serial_factory: Optional[Callable[[], object]] = None,
    ):
        self.port = port
        self.ready_timeout_s = ready_timeout_s
        self.link_timeout_s = link_timeout_s
        self.move_period_s = 1.0 / move_rate_hz
        # serial_factory lets the tests plug in a fake ESP32 instead of real hardware.
        self._serial_factory = serial_factory or (
            lambda: serial.Serial(port, baud, timeout=0.1)
        )

        self._ser = None
        self._write_lock = threading.Lock()
        self._reader: Optional[threading.Thread] = None
        self._running = False

        self._ready = threading.Event()
        self._pong = threading.Event()
        self._last_rx = 0.0
        self._distance_cm: Optional[int] = None
        self._distance_time = 0.0
        self._pir: Optional[int] = None      # -1 warming up, 0 quiet, 1 motion
        self._lock_reason: Optional[str] = None  # None = unknown, "" = unlocked

        # Things worth checking in tests and logs:
        self.firmware_version: Optional[str] = None
        self.watchdog_count = 0   # how many times the ESP32 stopped by itself
        self.restart_count = 0    # READY seen again after connecting = ESP32 rebooted
        self.last_error: Optional[str] = None

    @classmethod
    def from_config(cls, config: dict, **kwargs) -> "SerialLink":
        s = config["serial"]
        return cls(
            port=s["port"],
            baud=s.get("baud", 115200),
            ready_timeout_s=s.get("ready_timeout_s", 5.0),
            link_timeout_s=s.get("link_timeout_s", 0.5),
            move_rate_hz=s.get("move_rate_hz", 10),
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    def open(self) -> None:
        log.info("Opening serial port %s", self.port)
        try:
            self._ser = self._serial_factory()
        except (serial.SerialException, OSError) as e:
            raise LinkError(f"cannot open {self.port}: {e}") from e

        self._running = True
        self._reader = threading.Thread(target=self._read_loop, name="serial-reader", daemon=True)
        self._reader.start()

        # Opening the port usually resets the ESP32, so wait for READY.
        # If the board did not reset, it will never say READY, so we also try PING.
        deadline = time.monotonic() + self.ready_timeout_s
        while time.monotonic() < deadline:
            if self._ready.wait(timeout=0.5):
                log.info("ESP32 ready (firmware %s)", self.firmware_version)
                return
            if self.ping(timeout=0.3) is not None:
                log.info("ESP32 answered PING (no READY seen)")
                return

        self.close()
        raise LinkError(f"ESP32 on {self.port} did not answer within {self.ready_timeout_s} s")

    def close(self) -> None:
        if self._ser is None:
            return
        self.stop()
        self._running = False
        if self._reader is not None:
            self._reader.join(timeout=1.0)
        try:
            self._ser.close()
        except Exception:  # closing must never crash the program
            pass
        self._ser = None
        log.info("Serial link closed")

    def __enter__(self) -> "SerialLink":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def move(self, vx: float, vy: float, wz: float) -> None:
        """Drive for the next ~300 ms. Call again at least every 0.1 s to keep going."""
        if not self.is_alive():
            self.stop()
            raise LinkError("ESP32 link is down; refusing to MOVE")
        self._send(protocol.encode_move(vx, vy, wz))

    def stop(self) -> bool:
        """Ask the ESP32 to stop. Never raises. Returns True if the command was sent.

        Even if this fails, the ESP32 watchdog stops the wheels within 300 ms.
        """
        try:
            self._send(protocol.encode_stop())
            return True
        except LinkError as e:
            log.warning("Could not send STOP (%s); relying on ESP32 watchdog", e)
            return False

    def light(self, level: int) -> None:
        """Set the light strip (UV stand-in) 0..255; the LED module follows.

        The ESP32 refuses anything above 0 while it is locked (PIR warming up or
        a person seen in the last 30 s) and answers ERR locked.
        """
        self._send(protocol.encode_light(level))

    def ping(self, timeout: float = 0.5) -> Optional[float]:
        """Send PING. Returns the round-trip time in seconds, or None if no PONG."""
        self._pong.clear()
        start = time.monotonic()
        try:
            self._send(protocol.encode_ping())
        except LinkError:
            return None
        if self._pong.wait(timeout):
            return time.monotonic() - start
        return None

    def move_for(self, vx: float, vy: float, wz: float, seconds: float) -> None:
        """Drive for `seconds`, repeating MOVE so the watchdog stays happy, then STOP."""
        end = time.monotonic() + seconds
        try:
            while True:
                now = time.monotonic()
                if now >= end:
                    break
                self.move(vx, vy, wz)
                time.sleep(min(self.move_period_s, end - now))
        finally:
            self.stop()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        """True if the ESP32 sent something within the last link_timeout_s."""
        return (
            self._ser is not None
            and self._reader is not None
            and self._reader.is_alive()
            and time.monotonic() - self._last_rx < self.link_timeout_s
        )

    def distance(self) -> Tuple[Optional[int], Optional[float]]:
        """Latest ultrasonic reading: (centimetres or -1, age in seconds), or (None, None)."""
        if self._distance_cm is None:
            return None, None
        return self._distance_cm, time.monotonic() - self._distance_time

    def pir(self) -> Optional[int]:
        """PIR motion sensor: 1 = motion, 0 = quiet, -1 = warming up, None = not heard yet."""
        return self._pir

    def lock_reason(self) -> Optional[str]:
        """Why the ESP32 refuses MOVE/LIGHT: "warmup", "person", "" (not locked), or None (unknown).

        Treat None like locked.
        """
        return self._lock_reason

    def is_locked(self) -> bool:
        return self._lock_reason != ""

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _send(self, data: bytes) -> None:
        if self._ser is None:
            raise LinkError("serial port is not open")
        with self._write_lock:
            try:
                self._ser.write(data)
            except (serial.SerialException, OSError) as e:
                raise LinkError(f"write failed: {e}") from e
        log.debug("-> %s", data.decode("ascii").strip())

    def _read_loop(self) -> None:
        """Runs in the background: read lines from the ESP32 and remember what they say."""
        while self._running:
            try:
                raw = self._ser.readline()
            except (serial.SerialException, OSError) as e:
                log.error("Serial read failed, link is down: %s", e)
                break
            if not raw:
                continue  # timeout with nothing received
            self._handle(protocol.parse_line(raw.decode("ascii", errors="replace")))

    def _handle(self, msg: protocol.Message) -> None:
        self._last_rx = time.monotonic()

        if msg.kind == "DIST":
            self._distance_cm = msg.value
            self._distance_time = self._last_rx
        elif msg.kind == "PIR":
            if msg.value != self._pir:
                log.info("PIR %d", msg.value)
            self._pir = msg.value
        elif msg.kind == "LOCK":
            reason = msg.text if msg.value == 1 else ""
            if reason != self._lock_reason:
                if reason:
                    log.warning("ESP32 locked (%s): wheels stopped, lights off", reason)
                else:
                    log.info("ESP32 unlocked: no motion for 30 s")
            self._lock_reason = reason
        elif msg.kind == "PONG":
            self._pong.set()
        elif msg.kind == "READY":
            if self._ready.is_set():
                # The ESP32 rebooted while we were connected. Often this means
                # the motor battery sagged (brownout). Its motors are stopped now.
                self.restart_count += 1
                log.warning("ESP32 restarted unexpectedly (%d times so far)", self.restart_count)
            self.firmware_version = msg.text
            self._ready.set()
        elif msg.kind == "WDT":
            self.watchdog_count += 1
            log.warning("ESP32 watchdog stopped the motors (no MOVE for 300 ms)")
        elif msg.kind == "ERR":
            self.last_error = msg.text
            log.error("ESP32 error: %s", msg.text)
        elif msg.kind == "ACK":
            log.debug("<- ACK %s", msg.text)
        else:
            # Usually boot noise from the ESP32 right after reset; harmless.
            log.debug("<- unrecognised line: %r", msg.text)
