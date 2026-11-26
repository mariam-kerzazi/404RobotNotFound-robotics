// motors.cpp — mecanum wheel math.
//
// A mecanum robot can move forward/back (vx), sideways (vy) and turn (wz)
// at the same time. Each wheel's speed is a mix of the three:
//
//   front-left  = vx - vy - wz        front-right = vx + vy + wz
//   rear-left   = vx + vy - wz        rear-right  = vx - vy + wz
//
// (vx forward, vy LEFT, wz counter-clockwise. This assumes the usual "X"
// roller pattern when you look at the robot from above.)
#include <Arduino.h>
#include "config.h"
#include "motors.h"
#include "motor_driver.h"

static void setWheel(int wheel, float speed) {
  // speed is -1.0..1.0 here
  if (WHEEL_INVERT[wheel]) speed = -speed;
  int pwm = (int)(speed * MAX_PWM);
  driverSetMotor(wheel, constrain(pwm, -MAX_PWM, MAX_PWM));
}

void motorsBegin() {
  driverBegin();
  motorsStop();
}

void motorsDrive(float vx, float vy, float wz) {
  float w[WHEEL_COUNT];
  w[WHEEL_FL] = vx - vy - wz;
  w[WHEEL_FR] = vx + vy + wz;
  w[WHEEL_RL] = vx + vy - wz;
  w[WHEEL_RR] = vx - vy + wz;

  // Mixing can give values above 1.0 (e.g. full forward + full turn).
  // If so, scale all four down together so the direction stays correct.
  float biggest = 1.0f;
  for (int i = 0; i < WHEEL_COUNT; i++) {
    biggest = max(biggest, fabsf(w[i]));
  }
  for (int i = 0; i < WHEEL_COUNT; i++) {
    setWheel(i, w[i] / biggest);
  }
}

void motorsStop() {
  for (int i = 0; i < WHEEL_COUNT; i++) {
    driverSetMotor(i, 0);
  }
}
