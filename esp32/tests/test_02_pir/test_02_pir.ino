// Test 2: PIR motion sensor (HC-SR501) on GPIO 34.
// Waits 60 s for the sensor to warm up, then prints "PIR 1" / "PIR 0" every time it changes.
// GPIO 34 is input-only and has no internal pull resistors; the HC-SR501 drives the line itself.
const int PIR_PIN = 34;
const unsigned long WARMUP_MS = 60000;

int lastState = -1;
unsigned long lastCountdown = 0;
unsigned long lastChangeMs = 0;

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(4, OUTPUT); digitalWrite(4, LOW);     // keep the LED module and strip off during this test
  pinMode(33, OUTPUT); digitalWrite(33, LOW);
  delay(1500);
  Serial.println();
  Serial.println("=== Test 2: PIR on GPIO 34 ===");
  Serial.println("Warming up for 60 s. Stay out of view of the sensor.");
}

void loop() {
  unsigned long now = millis();

  if (now < WARMUP_MS) {
    if (now - lastCountdown >= 10000) {
      lastCountdown = now;
      Serial.printf("  warm-up: %lu s left (raw level now %d)\n", (WARMUP_MS - now) / 1000, digitalRead(PIR_PIN));
    }
    return;
  }

  int state = digitalRead(PIR_PIN);
  if (lastState == -1) {
    Serial.println("Ready. Wave your hand in front of the sensor, then stay still.");
    Serial.printf("PIR %d   (starting state)\n", state);
    lastState = state;
    lastChangeMs = now;
    return;
  }
  if (state != lastState) {
    Serial.printf("PIR %d   (previous state lasted %.1f s)\n", state, (now - lastChangeMs) / 1000.0);
    lastState = state;
    lastChangeMs = now;
  }
}
