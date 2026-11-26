// robot_body.ino — ESP32 firmware for the robot's body.
//
// Job: listen for commands from the Raspberry Pi over USB serial, drive the
// mecanum wheels, and report the ultrasonic distance. The protocol is in
// docs/protocol.md.
//
// SAFETY: every MOVE only lasts WATCHDOG_MS (300 ms). If the Pi goes quiet,
// crashes, or the cable falls out, the wheels stop on their own.
#include <Arduino.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include "config.h"
#include "motors.h"
#include "ultrasonic.h"

// --- incoming line buffer ---
static char lineBuf[MAX_LINE_LEN + 1];
static size_t lineLen = 0;
static bool lineTooLong = false;

// --- watchdog state ---
static unsigned long lastMoveMs = 0;
static bool motorsRunning = false;

// --- distance reporting ---
static unsigned long lastDistMs = 0;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Stop the wheels and forget the current MOVE.
static void safeStop() {
  motorsStop();
  motorsRunning = false;
}

// Read one number from a word like "0.30". Returns false if the word is not
// a valid number in -1.0..1.0. We are strict on purpose: if anything looks
// wrong, the robot stops.
static bool parseUnit(const char* word, float* out) {
  if (word == NULL) return false;
  char* end = NULL;
  float v = strtof(word, &end);
  if (end == word || *end != '\0') return false;  // not a number, or junk after it
  if (!isfinite(v)) return false;
  if (v < -1.0f || v > 1.0f) return false;
  *out = v;
  return true;
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

static void handleMove() {
  // strtok continues splitting the line handleLine() started on.
  float vx, vy, wz;
  bool ok = parseUnit(strtok(NULL, " "), &vx) &&
            parseUnit(strtok(NULL, " "), &vy) &&
            parseUnit(strtok(NULL, " "), &wz) &&
            strtok(NULL, " ") == NULL;  // no extra words allowed
  if (!ok) {
    safeStop();  // a confusing MOVE means STOP
    Serial.println("ERR bad_args MOVE");
    return;
  }
  motorsDrive(vx, vy, wz);
  motorsRunning = true;
  lastMoveMs = millis();
  Serial.println("ACK MOVE");
}

static void handleLine(char* line) {
  char* cmd = strtok(line, " ");
  if (cmd == NULL) return;  // empty line: ignore

  if (strcmp(cmd, "PING") == 0) {
    Serial.println("PONG");
  } else if (strcmp(cmd, "STOP") == 0) {
    safeStop();
    Serial.println("ACK STOP");
  } else if (strcmp(cmd, "MOVE") == 0) {
    handleMove();
  } else if (strcmp(cmd, "SERVO") == 0) {
    // Arm comes later, once we know the servo pins.
    Serial.println("ERR not_implemented SERVO");
  } else {
    Serial.print("ERR unknown_cmd ");
    Serial.println(cmd);
  }
}

// ---------------------------------------------------------------------------
// The three jobs the loop does over and over
// ---------------------------------------------------------------------------

// 1. Collect characters into lines and handle each full line.
static void readSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;

    if (c == '\n') {
      if (lineTooLong) {
        Serial.println("ERR line_too_long");
      } else {
        lineBuf[lineLen] = '\0';
        handleLine(lineBuf);
      }
      lineLen = 0;
      lineTooLong = false;
    } else if (lineLen < MAX_LINE_LEN) {
      lineBuf[lineLen++] = c;
    } else {
      lineTooLong = true;  // keep reading until '\n', then reject the line
    }
  }
}

// 2. Stop the wheels if the Pi has not sent a MOVE recently.
static void checkWatchdog() {
  if (motorsRunning && (millis() - lastMoveMs > WATCHDOG_MS)) {
    safeStop();
    Serial.println("WDT");
  }
}

// 3. Send the ultrasonic distance every DIST_PERIOD_MS.
static void reportDistance() {
  if (millis() - lastDistMs < DIST_PERIOD_MS) return;
  lastDistMs = millis();
  Serial.print("DIST ");
  Serial.println(ultrasonicReadCm());
}

// ---------------------------------------------------------------------------

void setup() {
  motorsBegin();  // first thing: make sure the wheels are stopped
  ultrasonicBegin();
  Serial.begin(SERIAL_BAUD);
  Serial.println("READY robot_body " FIRMWARE_VERSION);
}

void loop() {
  readSerial();
  checkWatchdog();
  reportDistance();
}
