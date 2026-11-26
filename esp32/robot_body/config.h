// config.h — settings for the robot body (ESP32 on the ACEBOTT car shield).
//
// Everything you might need to change lives here, except the motor driver
// pins, which live in motor_driver.cpp because they depend on how the
// shield drives the motors.
#pragma once

// ---------------------------------------------------------------------------
// Serial link to the Raspberry Pi (see docs/protocol.md)
// ---------------------------------------------------------------------------
#define FIRMWARE_VERSION "0.1.0"
#define SERIAL_BAUD      115200
#define MAX_LINE_LEN     64      // longest command line we accept

// If no MOVE arrives for this long, stop all motors. Safety: keep it short.
#define WATCHDOG_MS      300

// How often we send "DIST <cm>" to the Pi.
#define DIST_PERIOD_MS   100

// ---------------------------------------------------------------------------
// Motors
// ---------------------------------------------------------------------------
// Highest PWM value we ever send to a motor (0..255). MOVE 1.0 maps to this.
// Start low; raise it once everything is tested.
#define MAX_PWM          200

// Wheel numbering used everywhere in this firmware.
enum Wheel { WHEEL_FL = 0, WHEEL_FR = 1, WHEEL_RL = 2, WHEEL_RR = 3, WHEEL_COUNT = 4 };

// If a wheel spins backward when it should go forward, set its entry to true.
// Order: front-left, front-right, rear-left, rear-right.
static const bool WHEEL_INVERT[WHEEL_COUNT] = { false, false, false, false };

// ---------------------------------------------------------------------------
// Ultrasonic sensor pins — TODO: copy these from the ACEBOTT sample code.
// We do NOT guess pin numbers. The build stops here until they are filled in.
// ---------------------------------------------------------------------------
#define ULTRASONIC_TRIG_PIN  -1   // TODO
#define ULTRASONIC_ECHO_PIN  -1   // TODO

// Change to 1 once the pins above (and in motor_driver.cpp) are confirmed.
#define PINS_CONFIRMED 0

#if !PINS_CONFIRMED
#error "Pins not set yet: fill in config.h and motor_driver.cpp from the ACEBOTT sample code, then set PINS_CONFIRMED to 1."
#endif
