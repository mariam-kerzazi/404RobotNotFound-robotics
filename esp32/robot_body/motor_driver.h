// motor_driver.h — the ONLY place that knows how the shield drives motors.
//
// The rest of the firmware calls these two functions and never touches
// motor pins directly. When we know the shield's wiring (from the ACEBOTT
// sample code), only motor_driver.cpp needs to change.
#pragma once

// Set up the motor pins. Motors must be stopped when this returns.
void driverBegin();

// Drive one wheel. wheel = WHEEL_FL..WHEEL_RR, pwm = -255..255
// (negative = backward, 0 = stop).
void driverSetMotor(int wheel, int pwm);
