# Pi ↔ ESP32 serial protocol (v1)

The Raspberry Pi 5 (brain) talks to the ESP32 (body) over **USB serial at 115200 baud**.

## Basics

- Plain ASCII text, **one message per line**, ending in `\n` (a `\r` before it is ignored).
- Words are separated by single spaces.
- A line is at most **64 characters**. Longer lines are thrown away and answered with `ERR line_too_long`.
- Numbers use a dot as the decimal point (`0.30`, not `0,30`).

## Pi → ESP32 (commands)

| Command | Meaning | Reply |
|---|---|---|
| `PING` | "Are you there?" | `PONG` |
| `MOVE vx vy wz` | Drive. Each value is a fraction of max speed, from `-1.00` to `1.00`. | `ACK MOVE` |
| `STOP` | Stop all wheels now. | `ACK STOP` |
| `SERVO id angle` | Move arm servo `id` to `angle` degrees (0–180). *Not implemented yet.* | `ACK SERVO` (later) |

### MOVE directions (robot's point of view)

- `vx` > 0 → forward, < 0 → backward
- `vy` > 0 → strafe **left**, < 0 → strafe right
- `wz` > 0 → turn **counter-clockwise** (left), < 0 → clockwise (right)

Examples:

```
MOVE 0.30 0.00 0.00    forward at 30 %
MOVE 0.00 -0.30 0.00   strafe right at 30 %
MOVE 0.00 0.00 0.25    spin left on the spot
MOVE 0.00 0.00 0.00    hold still (same as STOP, but counts as a fresh MOVE)
```

## ESP32 → Pi (messages)

| Message | Meaning |
|---|---|
| `READY robot_body <version>` | Sent once after the ESP32 boots. |
| `PONG` | Reply to `PING`. |
| `ACK <command>` | The command was understood and done. |
| `ERR <code> [detail]` | Something was wrong. Codes: `bad_args`, `unknown_cmd`, `line_too_long`, `not_implemented`. |
| `DIST <cm>` | Ultrasonic distance in whole centimetres, sent about 10 times per second. `-1` means no echo (nothing in range, or a sensor problem). |
| `WDT` | The watchdog stopped the motors (see below). |

## Safety rules (the ESP32 enforces these by itself)

1. **Every MOVE lasts at most 300 ms.** If no new `MOVE` arrives within 300 ms, the ESP32 stops all
   motors and sends `WDT` once. So the Pi must repeat `MOVE` about 10 times per second for as long as it
   wants to keep driving.
   - `PING` does **not** keep the wheels turning. That's on purpose: if the Pi's decision code freezes
     but some other part still sends pings, the robot still stops.
2. **A bad MOVE means stop.** If a `MOVE` line is malformed or out of range, the ESP32 stops the
   motors *and* replies `ERR bad_args MOVE`.
3. **Boot = stopped.** The motors are off at power-on and after every reset.

## Notes for the Pi side

- Opening the serial port usually **resets the ESP32** (the DTR line does this). Wait for `READY`
  before sending commands. If `READY` never arrives, send `PING` and accept a `PONG` instead.
- Treat the link as **dead** if nothing at all (not even `DIST`) has arrived for 500 ms.
