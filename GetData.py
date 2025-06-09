import paho.mqtt.client as mqtt
import sqlite3
import json
import ssl
import pytz
from datetime import datetime

# Lấy giờ hiện tại theo giờ Việt Nam
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# Kết nối SQLite
conn = sqlite3.connect('weather_data.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature REAL,
        humidity REAL,
        pressure REAL,  -- Lưu áp suất mức biển
        timestamp DATETIME
    )
''')
conn.commit()

# Hàm tính áp suất mức biển
def calculate_sea_level_pressure(pressure, temperature, height=1000):
    # Chuyển đổi nhiệt độ sang Kelvin
    T = temperature + 273.15
    # Công thức tính áp suất mức biển theo chuẩn WMO
    SLP = pressure * (1 - (0.0065 * height) / T) ** (-5.257)
    return SLP

# Callback khi nhận message
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        temp = data.get('temperature')
        humid = data.get('humidity')
        press = data.get('pressure')

        # Lấy thời gian hiện tại theo giờ Việt Nam
        vn_time = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')

        # Tính áp suất mức biển
        slp = calculate_sea_level_pressure(press, temp, height=10)

        print(f"Received at {vn_time}: Temp={temp}°C, Humidity={humid}%, Raw Pressure={press} hPa, SLP={slp:.2f} hPa")

        # Lưu áp suất mức biển vào database
        cursor.execute('''
            INSERT INTO sensor_data (temperature, humidity, pressure, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (temp, humid, slp, vn_time))
        conn.commit()

    except Exception as e:
        print("Error processing message:", e)

# Thông tin MQTT broker
broker = "95bf14db43eb40e2a7a61637a84f6417.s1.eu.hivemq.cloud"
port = 8883
topic = "esp32/bme680/data"

# Thông tin đăng nhập
username = "nghia111"
password = "Password123"

# Cấu hình MQTT client
client = mqtt.Client()
client.username_pw_set(username=username, password=password)

# Cấu hình TLS
client.tls_set(cert_reqs=ssl.CERT_NONE)        # Nếu broker không yêu cầu xác thực CA
client.tls_insecure_set(True)                  # Chấp nhận chứng chỉ tự ký (nếu có)

client.on_message = on_message
client.connect(broker, port, 60)
client.subscribe(topic)

print("Kết nối MQTT TLS với xác thực tài khoản...")

client.loop_forever()