// status_led.h — the ESP32 board's blue LED shows the PIR safety state.
//
//   slow blink (1 s on / 1 s off)  PIR warming up, locked
//   solid ON                       PIR sees motion right now, locked
//   fast blink (4 per second)      no motion now, waiting out the 30 s, still locked
//   short flash every 2 s          clear: unlocked, robot may drive and light up
#pragma once

void statusLedBegin();
void statusLedUpdate();   // call every loop
