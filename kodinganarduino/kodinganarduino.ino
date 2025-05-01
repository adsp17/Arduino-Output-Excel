#include <Wire.h>
#include <LCD-I2C.h>

LCD_I2C lcd(0x27, 16, 2); // Alamat I2C dan ukuran LCD

void setup() {
  Wire.begin();
  lcd.begin(&Wire);
  lcd.display();
  lcd.backlight();

  Serial.begin(115200); // Harus sesuai dengan baudrate Python
  while (!Serial); // Tunggu serial siap (untuk board tertentu)

  lcd.setCursor(0, 0);
  lcd.print("Menunggu data");
}

void loop() {
  if (Serial.available()) {
    String incomingText = Serial.readStringUntil('\n');
    incomingText.trim(); // Bersihkan whitespace

    if (incomingText.length() > 0) {
      Serial.print("Diterima: ");
      Serial.println(incomingText);

      lcd.clear();

      // Tampilkan hingga 32 karakter (2 baris x 16 kolom)
      if (incomingText.length() <= 16) {
        lcd.setCursor(0, 0);
        lcd.print(incomingText);
      } else {
        lcd.setCursor(0, 0);
        lcd.print(incomingText.substring(0, 16));
        lcd.setCursor(0, 1);
        lcd.print(incomingText.substring(16, 32)); // Potong maksimal 32 karakter
      }
    }
  }
}
