#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// Thông tin WiFi
const char* ssid = "Nyuuu";
const char* wifi_password = "2345678910";

// Thông tin MQTT HiveMQ Cloud
const char* mqtt_server = "95bf14db43eb40e2a7a61637a84f6417.s1.eu.hivemq.cloud";
const int mqtt_port = 8883;
const char* mqtt_user = "nghia111";
const char* mqtt_password = "Password123";

const char* mqtt_topic = "esp32/bme680/data";

// Khởi tạo client TLS
WiFiClientSecure espClient;
PubSubClient client(espClient);

// Khởi tạo cảm biến BME680
Adafruit_BME680 bme;

// Hàm kết nối lại MQTT
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32_BME680_Client", mqtt_user, mqtt_password)) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(9600);
  delay(1000);

  // Khởi tạo BME680 I2C địa chỉ 0x76 (hoặc 0x77 tùy cảm biến)
  if (!bme.begin()) {
    Serial.println("Could not find a valid BME680 sensor, check wiring!");
    while (1);
  }

  // Cấu hình BME680
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setGasHeater(320, 150); // 320°C trong 150 ms

  // Kết nối WiFi
  WiFi.begin(ssid, wifi_password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected!");

  espClient.setInsecure();

  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  if (bme.performReading()) {
    // Tạo chuỗi JSON gửi dữ liệu
    String payload = "{";
    payload += "\"temperature\":" + String(bme.temperature, 2) + ",";
    payload += "\"humidity\":" + String(bme.humidity, 2) + ",";
    payload += "\"pressure\":" + String(bme.pressure / 100.0, 2) + ",";
    payload += "\"gas_resistance\":" + String(bme.gas_resistance);
    payload += "}";

    Serial.println("Publishing data: " + payload);
    client.publish(mqtt_topic, payload.c_str());
  } else {
    Serial.println("Failed to perform reading from BME680");
  }

  delay(10000); // Gửi dữ liệu mỗi 10 giây
}
