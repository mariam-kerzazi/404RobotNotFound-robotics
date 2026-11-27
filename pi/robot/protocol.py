"""Build and read the text lines exchanged with the ESP32.

This file has no hardware code, so it can be tested on any laptop.
The full protocol is described in docs/protocol.md.
"""
import math
from dataclasses import dataclass
from typing import Optional

MAX_LINE_LEN = 64


# ---------------------------------------------------------------------------
# Pi -> ESP32
# ---------------------------------------------------------------------------

def _unit(value: float, name: str) -> str:
    """Format a speed between -1 and 1 as text like '0.30'."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a real number, got {value}")
    value = max(-1.0, min(1.0, value))  # clamp to the allowed range
    return f"{round(value, 2) + 0.0:.2f}"  # "+ 0.0" turns -0.0 into 0.0


def encode_move(vx: float, vy: float, wz: float) -> bytes:
    """vx forward, vy left, wz counter-clockwise; each -1.0..1.0."""
    return f"MOVE {_unit(vx, 'vx')} {_unit(vy, 'vy')} {_unit(wz, 'wz')}\n".encode("ascii")


def encode_stop() -> bytes:
    return b"STOP\n"


def encode_ping() -> bytes:
    return b"PING\n"


def encode_light(level: int) -> bytes:
    """Light strip brightness 0..255 (the LED module follows it). 0 = off."""
    level = int(level)
    if not 0 <= level <= 255:
        raise ValueError(f"light level must be 0..255, got {level}")
    return f"LIGHT {level}\n".encode("ascii")


def encode_servo(servo_id: int, angle: int) -> bytes:
    if not 0 <= int(angle) <= 180:
        raise ValueError(f"servo angle must be 0..180, got {angle}")
    return f"SERVO {int(servo_id)} {int(angle)}\n".encode("ascii")


# ---------------------------------------------------------------------------
# ESP32 -> Pi
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Message:
    """One parsed line from the ESP32.

    kind is one of: READY, PONG, ACK, ERR, DIST, WDT, PIR, LOCK, UNKNOWN
    """
    kind: str
    value: Optional[int] = None  # DIST: cm (-1 = no echo), PIR: -1/0/1, LOCK: 0/1
    text: str = ""               # READY: version, ACK: command, ERR: code + detail,
                                 # LOCK: reason ("warmup"/"person"), UNKNOWN: whole line


def parse_line(line: str) -> Message:
    line = line.strip()
    head, _, rest = line.partition(" ")

    if head in ("PONG", "WDT") and not rest:
        return Message(head)
    if head in ("READY", "ACK", "ERR"):
        return Message(head, text=rest)
    if head == "DIST":
        try:
            return Message("DIST", value=int(rest))
        except ValueError:
            pass
    if head == "PIR" and rest in ("-1", "0", "1"):
        return Message("PIR", value=int(rest))
    if head == "LOCK":
        flag, _, reason = rest.partition(" ")
        if flag == "0" and not reason:
            return Message("LOCK", value=0)
        if flag == "1" and reason:
            return Message("LOCK", value=1, text=reason)
    return Message("UNKNOWN", text=line)
