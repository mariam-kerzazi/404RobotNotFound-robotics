// motors.h — turns MOVE commands (vx, vy, wz) into four wheel speeds.
#pragma once

void motorsBegin();                            // set up and stop
void motorsDrive(float vx, float vy, float wz); // each -1.0..1.0, see docs/protocol.md
void motorsStop();
