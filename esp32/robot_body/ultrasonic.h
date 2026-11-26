// ultrasonic.h — HC-SR04-style distance sensor on the front of the robot.
#pragma once

void ultrasonicBegin();

// Distance in whole centimetres, or -1 if there was no echo.
// Takes at most ~25 ms (the echo timeout).
int ultrasonicReadCm();
