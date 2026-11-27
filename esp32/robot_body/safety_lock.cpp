#include <Arduino.h>
#include "config.h"
#include "safety_lock.h"

static LockReason reason = LOCK_WARMUP;
static bool warmedUp = false;
static int pir = -1;
static unsigned long bootMs = 0;
static unsigned long lastMotionMs = 0;

void safetyBegin() {
  pinMode(PIR_PIN, INPUT);   // GPIO 34 is input-only, no pull resistors; the PIR drives it
  bootMs = millis();
  lastMotionMs = bootMs;
  reason = LOCK_WARMUP;
  warmedUp = false;
  pir = -1;
}

bool safetyUpdate() {
  unsigned long now = millis();

  if (!warmedUp) {
    if (now - bootMs < PIR_WARMUP_MS) return false;  // still warming up: stay locked
    warmedUp = true;
    lastMotionMs = now;   // the 30 s quiet time starts when warm-up ends
  }

  pir = (digitalRead(PIR_PIN) == HIGH) ? 1 : 0;

  if (pir == 1) {
    lastMotionMs = now;
    bool justLocked = (reason != LOCK_PERSON);
    reason = LOCK_PERSON;
    return justLocked;     // true once per detection: caller stops everything
  }

  if (reason != LOCK_NONE && now - lastMotionMs >= PIR_CLEAR_MS) {
    reason = LOCK_NONE;    // 30 s with no motion: allowed to start again
  }
  return false;
}

bool safetyLocked() { return reason != LOCK_NONE; }
LockReason safetyReason() { return reason; }

const char* safetyReasonName() {
  switch (reason) {
    case LOCK_WARMUP: return "warmup";
    case LOCK_PERSON: return "person";
    default:          return "none";
  }
}

int pirState() { return pir; }
