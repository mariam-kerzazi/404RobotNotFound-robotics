// safety_lock.h — the PIR sensor and the "person nearby" lock.
//
// The lights stand in for UV, which must never shine on a person. So:
// - While the PIR warms up (first 60 s) we can't trust it: LOCKED.
// - Motion seen: LOCKED. The caller stops the wheels and turns the lights off.
// - Unlocked only after PIR_CLEAR_MS (30 s) with no motion at all.
// Unlocking does NOT turn anything back on; the Pi has to send commands again.
#pragma once

enum LockReason { LOCK_NONE = 0, LOCK_WARMUP, LOCK_PERSON };

void safetyBegin();
// Call every loop. Returns true when motion has just been seen (caller stops everything).
bool safetyUpdate();
bool safetyLocked();
LockReason safetyReason();
const char* safetyReasonName();
int pirState();   // -1 = warming up, 0 = no motion, 1 = motion
