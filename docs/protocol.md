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
| `STOP` | Stop all wheels now. (Lights stay as they are.) | `ACK STOP` |
| `LIGHT level` | Light strip brightness, `0`–`255` (`0` = off). The LED module always copies the strip. Refused while locked, except `LIGHT 0`. | `ACK LIGHT` |
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
| `ERR <code> [detail]` | Something was wrong. Codes: `bad_args`, `unknown_cmd`, `line_too_long`, `not_implemented`, `locked` (detail = `warmup` or `person`). |
| `DIST <cm>` | Ultrasonic distance in whole centimetres, sent about 10 times per second. `-1` means no echo (nothing in range, or a sensor problem). |
| `WDT` | The watchdog stopped the motors (see below). |
| `PIR <state>` | PIR motion sensor: `1` motion, `0` no motion, `-1` still warming up. Sent when it changes and once a second. |
| `LOCK 1 <reason>` / `LOCK 0` | The safety lock (see rule 4). Reason `warmup` or `person`. Sent when it changes and once a second. |

## Safety rules (the ESP32 enforces these by itself)

1. **Every MOVE lasts at most 300 ms.** If no new `MOVE` arrives within 300 ms, the ESP32 stops all
   motors and sends `WDT` once. So the Pi must repeat `MOVE` about 10 times per second for as long as it
   wants to keep driving.
   - `PING` does **not** keep the wheels turning. That's on purpose: if the Pi's decision code freezes
     but some other part still sends pings, the robot still stops.
2. **A bad MOVE means stop.** If a `MOVE` line is malformed or out of range, the ESP32 stops the
   motors *and* replies `ERR bad_args MOVE`.
3. **Boot = stopped.** The motors and lights are off at power-on and after every reset.
4. **Person nearby = everything off.** The lights stand in for UV, which must never shine on a person.
   The PIR (HC-SR501 on GPIO 34) watches the robot's blind spot behind it.
   - When it sees motion, the ESP32 itself stops the wheels, turns the lights off, and sends
     `PIR 1` and `LOCK 1 person`. It doesn't wait for the Pi.
   - While locked, `MOVE` and `LIGHT` (above 0) are refused with `ERR locked <reason>`.
   - It unlocks after **30 s with no motion** (`LOCK 0`). Unlocking turns nothing back on: the Pi
     must send `LIGHT` and `MOVE` again.
   - After boot the PIR needs 60 s to warm up, so the ESP32 starts locked (`LOCK 1 warmup`) and can
     unlock about 90 s after power-on.
   - Known limitation: the PIR can also fire while the robot itself is driving. For now we accept the
     extra stops.

## Notes for the Pi side

- Opening the serial port usually **resets the ESP32** (the DTR line does this). Wait for `READY`
  before sending commands. If `READY` never arrives, send `PING` and accept a `PONG` instead.
- Treat the link as **dead** if nothing at all (not even `DIST`) has arrived for 500 ms.
