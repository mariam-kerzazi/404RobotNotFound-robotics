#include <Arduino.h>
#include "config.h"
#include "lights.h"

static uint8_t currentLevel = 0;

void lightsBegin() {
  // Drive both pins LOW straight away so the lights (UV stand-in) start OFF.
  pinMode(STRIP_PIN, OUTPUT); digitalWrite(STRIP_PIN, LOW);
  pinMode(LED_PIN, OUTPUT);   digitalWrite(LED_PIN, LOW);
  ledcAttach(STRIP_PIN, LIGHT_PWM_FREQ_HZ, 8);  // 8 bits = brightness 0..255
  ledcAttach(LED_PIN, LIGHT_PWM_FREQ_HZ, 8);
  lightsOff();
}

void lightsSet(uint8_t level) {
  currentLevel = level;
  ledcWrite(STRIP_PIN, level);
  ledcWrite(LED_PIN, level);   // the LED module follows the strip
}

void lightsOff() { lightsSet(0); }

uint8_t lightsLevel() { return currentLevel; }
