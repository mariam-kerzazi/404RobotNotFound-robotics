// ultrasonic.cpp — read the HC-SR04-style sensor.
//
// How it works: send a 10 µs pulse on TRIG, then time how long ECHO stays
// HIGH. Sound travels about 1 cm every 29 µs, and it has to go there and
// back, so distance_cm = echo_time_us / 58.
#include <Arduino.h>
#include "config.h"
#include "ultrasonic.h"

// 25 000 µs ≈ 4.3 m. Longer than the sensor's real range, so if we wait this
// long there is nothing in front of us (or the sensor is unplugged).
static const unsigned long ECHO_TIMEOUT_US = 25000;

void ultrasonicBegin() {
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
}

int ultrasonicReadCm() {
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

  unsigned long echoUs = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (echoUs == 0) {
    return -1;  // no echo
  }
  return (int)(echoUs / 58);
}
