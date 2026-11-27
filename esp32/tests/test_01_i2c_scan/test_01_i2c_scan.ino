// Test 1: is anything on the ESP32's I2C bus (GPIO 21 = SDA, GPIO 22 = SCL)?
// If nothing answers, GPIO 21/22 are free to use for the LED module and the light strip.
// Open the serial monitor at 115200. Result is printed once; press the board's EN button to rerun.
#include <Wire.h>

const int SDA_PIN = 21;
const int SCL_PIN = 22;

// Read a pin with the internal pull-down on: HIGH means something outside pulls it up.
int idleLevel(int pin) {
  pinMode(pin, INPUT_PULLDOWN);
  delay(5);
  return digitalRead(pin);
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println();
  Serial.println("=== Test 1: I2C bus scan ===");

  // A real I2C bus has pull-up resistors, so both lines sit HIGH.
  int sda = idleLevel(SDA_PIN);
  int scl = idleLevel(SCL_PIN);
  Serial.printf("Idle level with pull-down: GPIO21=%d GPIO22=%d  (1 = pulled up from outside)\n", sda, scl);

  Wire.begin(SDA_PIN, SCL_PIN);
  int found = 0, errors = 0;
  for (int address = 1; address <= 126; address++) {
    Wire.beginTransmission(address);
    int result = Wire.endTransmission();   // 0 = device answered, 2 = no answer, other = bus error
    if (result == 0) {
      Serial.printf("  Device found at 0x%02X\n", address);
      found++;
    } else if (result != 2) {
      errors++;
    }
  }
  Wire.end();

  // Leave both pins LOW so the strip and LED end up off.
  pinMode(SDA_PIN, OUTPUT); digitalWrite(SDA_PIN, LOW);
  pinMode(SCL_PIN, OUTPUT); digitalWrite(SCL_PIN, LOW);

  Serial.printf("Devices found: %d, bus errors: %d\n", found, errors);
  if (found > 0) {
    Serial.println("FAIL: the I2C bus is in use. Do NOT use GPIO 21/22 for the LED and strip.");
  } else if (errors > 0) {
    // Something (like the LED module) holds a line LOW, so no I2C device could answer even if present.
    Serial.println("INCONCLUSIVE: the bus is blocked. Unplug everything from GPIO 21/22 except the I2C device and rerun.");
  } else {
    Serial.println("PASS: nothing on the I2C bus. GPIO 21/22 are free for the LED and strip.");
  }
}

void loop() {}
