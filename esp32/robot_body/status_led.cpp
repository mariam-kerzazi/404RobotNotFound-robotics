#include <Arduino.h>
#include "config.h"
#include "safety_lock.h"
#include "status_led.h"

void statusLedBegin() {
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);
}

void statusLedUpdate() {
  unsigned long t = millis();
  bool on;
  if (safetyReason() == LOCK_WARMUP) {
    on = (t % 2000) < 1000;          // slow blink
  } else if (pirState() == 1) {
    on = true;                       // motion right now
  } else if (safetyLocked()) {
    on = (t % 250) < 125;            // fast blink: counting down the 30 s
  } else {
    on = (t % 2000) < 100;           // short flash: all clear
  }
  digitalWrite(STATUS_LED_PIN, on ? HIGH : LOW);
}
