// motor_driver.cpp — low-level motor control for the ACEBOTT car shield.
//
// TODO: fill this in from the ACEBOTT QD001 sample code.
// We do not know yet whether the shield uses one PWM + direction pin per
// motor, a shift register, or a motor driver chip on I2C, so this file is
// left empty on purpose instead of guessing.
//
// What each function must do:
//   driverBegin()          set pin modes / start the driver, all motors OFF.
//   driverSetMotor(w, p)   wheel w (WHEEL_FL..WHEEL_RR), power p in -255..255.
//                          p > 0 forward, p < 0 backward, p == 0 stop.
#include <Arduino.h>
#include "config.h"
#include "motor_driver.h"

void driverBegin() {
  // TODO: from ACEBOTT sample code.
}

void driverSetMotor(int wheel, int pwm) {
  // TODO: from ACEBOTT sample code.
  (void)wheel;
  (void)pwm;
}
