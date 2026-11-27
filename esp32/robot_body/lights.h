// lights.h — the light strip (UV stand-in) on a MOSFET, plus the ACEBOTT LED module.
// The LED module always copies the strip: strip on = LED on, strip off = LED off.
#pragma once
#include <stdint.h>

void lightsBegin();              // call first in setup(): both lights OFF
void lightsSet(uint8_t level);   // 0 = off, 255 = full brightness
void lightsOff();
uint8_t lightsLevel();
