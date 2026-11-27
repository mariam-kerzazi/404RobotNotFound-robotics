// Test 2b: how long does the PIR (GPIO 34) stay HIGH after one wave?
// Use it to set the HC-SR501 "Time" knob. Wave once after "Ready", then stay still.
const int PIR_PIN = 34;
unsigned long start = 0;
int last = LOW;

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  Serial.println("Warming up 60 s...");
  delay(60000);
  Serial.println("Ready - wave once, then stay still");
}

void loop() {
  int v = digitalRead(PIR_PIN);
  if (v == HIGH && last == LOW) { start = millis(); Serial.println("Motion!"); }
  if (v == LOW && last == HIGH) {
    Serial.printf("Stayed HIGH for %.1f s\n", (millis() - start) / 1000.0);
  }
  last = v;
}
