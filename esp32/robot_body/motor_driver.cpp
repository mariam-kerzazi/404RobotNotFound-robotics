// motor_driver.cpp — low-level motor control for the ACEBOTT ESP32 Car Shield V2.
//
// The V2 shield does NOT drive the motors from ESP32 pins directly. It has a
// small motor-controller chip, and the ESP32 sends it one 5-byte packet per
// motor over Serial2 (TX = GPIO17, 9600 baud):
//
//     [motor 1..4] [direction 1 or 2] [speed 0..100] '\r' '\n'
//
// This is the same format ACEBOTT's own ACB_SmartCar_V2 library sends. We use
// the ESP32's hardware serial port instead of SoftwareSerial (more reliable).
//
// Motor numbers on the shield (worked out from the library's strafe and turn
// patterns, and confirmed by another QD001 project):
//     M1 = front-left    M3 = front-right
//     M2 = rear-left     M4 = rear-right
#include <Arduino.h>
#include "config.h"
#include "motor_driver.h"

// Our wheel order (config.h) -> the shield's motor number.
static const uint8_t SHIELD_MOTOR[WHEEL_COUNT] = {
  1,  // WHEEL_FL
  3,  // WHEEL_FR
  2,  // WHEEL_RL
  4,  // WHEEL_RR
};

static void sendMotorPacket(uint8_t motor, int pwm) {
  // The right-side motors (3 and 4) are mounted mirrored, so ACEBOTT flips
  // their direction code. Positive pwm = wheel rolls forward on every motor.
  uint8_t dir;
  if (motor == 1 || motor == 2) {
    dir = pwm > 0 ? 1 : 2;
  } else {
    dir = pwm > 0 ? 2 : 1;
  }

  // The shield takes 0..100, not 0..255.
  uint8_t speed = (uint8_t)map(abs(pwm), 0, 255, 0, 100);

  // ACEBOTT's library never sends the value 40 (it replaces it with 0). We
  // don't know why, so we also avoid it, but use 41 so the wheel keeps turning.
  if (speed == 40) speed = 41;

  uint8_t packet[5] = { motor, dir, speed, '\r', '\n' };
  Serial2.write(packet, sizeof(packet));
}

void driverBegin() {
  Serial2.begin(MOTOR_UART_BAUD, SERIAL_8N1, MOTOR_UART_RX_PIN, MOTOR_UART_TX_PIN);
  for (int w = 0; w < WHEEL_COUNT; w++) {
    driverSetMotor(w, 0);
  }
}

void driverSetMotor(int wheel, int pwm) {
  if (wheel < 0 || wheel >= WHEEL_COUNT) return;
  sendMotorPacket(SHIELD_MOTOR[wheel], constrain(pwm, -255, 255));
}
