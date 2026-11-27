// Test 3: light strip (XY-MOS MOSFET on GPIO 22) and ACEBOTT LED module (GPIO 21).
// Runs the sequence below, waits 5 s, and repeats. Watch the lights and compare with the printed step.
const int STRIP_PIN = 22;
const int LED_PIN = 21;
const int PWM_FREQ_HZ = 1000;
const int PWM_BITS = 8;   // brightness 0-255

void step(const char *what, int strip, int led, int ms) {
  Serial.printf("  %-34s strip=%3d  led=%3d\n", what, strip, led);
  ledcWrite(STRIP_PIN, strip);
  ledcWrite(LED_PIN, led);
  delay(ms);
}

void setup() {
  Serial.begin(115200);
  ledcAttach(STRIP_PIN, PWM_FREQ_HZ, PWM_BITS);
  ledcAttach(LED_PIN, PWM_FREQ_HZ, PWM_BITS);
  ledcWrite(STRIP_PIN, 0);
  ledcWrite(LED_PIN, 0);
  delay(1500);
  Serial.println();
  Serial.println("=== Test 3: light strip (GPIO 22) and LED module (GPIO 21) ===");
}

void loop() {
  Serial.println("Strip:");
  step("full brightness (should be bright)", 255, 0, 2000);
  step("dim (should be clearly dimmer)", 60, 0, 2000);
  step("off", 0, 0, 1000);
  Serial.println("LED module:");
  step("on", 0, 255, 1000);
  step("off", 0, 0, 1000);
  Serial.println("  fading LED 0 -> 255 over 2 s");
  for (int b = 0; b <= 255; b += 5) { ledcWrite(LED_PIN, b); delay(40); }
  step("off", 0, 0, 1000);
  Serial.println("Both on together:");
  step("strip + LED full", 255, 255, 2000);
  step("all off (repeating in 5 s)", 0, 0, 5000);
}
