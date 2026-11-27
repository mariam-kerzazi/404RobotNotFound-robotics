// config.h — settings for the robot body (ESP32 on the ACEBOTT car shield).
//
// Everything you might need to change lives here, except the motor driver
// pins, which live in motor_driver.cpp because they depend on how the
// shield drives the motors.
#pragma once

// ---------------------------------------------------------------------------
// Serial link to the Raspberry Pi (see docs/protocol.md)
// ---------------------------------------------------------------------------
#define FIRMWARE_VERSION "0.2.0"
#define SERIAL_BAUD      115200
#define MAX_LINE_LEN     64      // longest command line we accept

// If no MOVE arrives for this long, stop all motors. Safety: keep it short.
#define WATCHDOG_MS      300

// How often we send "DIST <cm>" to the Pi.
#define DIST_PERIOD_MS   100

// How often we repeat "PIR <state>" and "LOCK ..." so the Pi always knows them,
// even if it connected after the last change.
#define STATE_PERIOD_MS  1000

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
// Pins — ACEBOTT ESP32 Car Shield V2 (QD001 V2 kit)
//
// Source: ACEBOTT's ACB_SmartCar_V2 Arduino library (TX_PIN 17 / RX_PIN 16),
// ultrasonic from ACEBOTT QD001 sample firmware (Ultrasonic.Init(13,14)) and
// the "Ultrasonic 5V 13 14 GND" label printed on the shield.
// Cross-checked against two independent QD001 projects.
// ---------------------------------------------------------------------------

// The V2 shield has its own motor-controller chip. The ESP32 talks to it over
// a second serial port (Serial2) at 9600 baud. See motor_driver.cpp.
#define MOTOR_UART_TX_PIN    17
#define MOTOR_UART_RX_PIN    16
#define MOTOR_UART_BAUD      9600

#define ULTRASONIC_TRIG_PIN  13
#define ULTRASONIC_ECHO_PIN  14

// ---------------------------------------------------------------------------
// PIR motion sensor and lights (team's wiring, 2026-11-26)
//
// GPIO 21/22 are the shield's I2C header. Test 1 (esp32/tests/test_01_i2c_scan)
// found no I2C devices and ACEBOTT's library doesn't use I2C, so we use them as
// plain outputs.
// ---------------------------------------------------------------------------
#define PIR_PIN              34      // HC-SR501 output (input-only pin)
#define STRIP_PIN            22      // XY-MOS MOSFET trigger -> light strip (UV stand-in)
#define LED_PIN              21      // ACEBOTT LED module, always follows the strip
#define LIGHT_PWM_FREQ_HZ    1000

#define PIR_WARMUP_MS        60000   // HC-SR501 needs about a minute after power-on
#define PIR_CLEAR_MS         30000   // no motion for this long = allowed to start again
