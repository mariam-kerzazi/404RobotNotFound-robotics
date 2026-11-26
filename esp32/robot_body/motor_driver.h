// motor_driver.h — the ONLY place that knows how the shield drives motors.
//
// The rest of the firmware calls these two functions and never talks to the
// motors directly. If the shield ever changes, only motor_driver.cpp changes.
#pragma once

// Set up the motor pins. Motors must be stopped when this returns.
void driverBegin();

// Drive one wheel. wheel = WHEEL_FL..WHEEL_RR, pwm = -255..255
// (negative = backward, 0 = stop).
void driverSetMotor(int wheel, int pwm);
