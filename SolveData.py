import pandas as pd
import numpy as np
import joblib
import logging
import sqlite3
from datetime import datetime
import schedule
import time

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tải mô hình
try:
    model = joblib.load(r'D:\NT131.P24-DoAn\weather_model.pkl')
    scaler = joblib.load(r'D:\NT131.P24-DoAn\scaler.pkl')
    label_encoder = joblib.load(r'D:\NT131.P24-DoAn\label_encoder.pkl')
    logging.info("Đã tải mô hình, scaler và label encoder thành công")
except Exception as e:
    logging.error(f"Lỗi khi tải mô hình/scaler/label encoder: {e}")
    raise

# Ánh xạ mã thời tiết
def map_weather_code(code):
    rain_codes = [61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    return 50 if code in rain_codes else code

# Hàm dự đoán thời tiết
def predict_weather(current_data, custom_lags, hour, day_of_week, month):
    temp_humidity_interaction = current_data['temperature_2m (C)'] * current_data['relative_humidity_2m (%)']
    temp_pressure_interaction = current_data['temperature_2m (C)'] * current_data['surface_pressure (hPa)']
    
    features = [
        current_data['temperature_2m (C)'],
        current_data['relative_humidity_2m (%)'],
        current_data['surface_pressure (hPa)'],
        hour,
        day_of_week,
        month,
        temp_humidity_interaction,
        temp_pressure_interaction,
        custom_lags['temperature_lag_1'],
        custom_lags['temperature_lag_2'],
        custom_lags['temperature_lag_3'],
        custom_lags['humidity_lag_1'],
        custom_lags['humidity_lag_2'],
        custom_lags['humidity_lag_3'],
        custom_lags['pressure_lag_1'],
        custom_lags['pressure_lag_2'],
        custom_lags['pressure_lag_3'],
    ]
    
    feature_names = ['temperature_2m (C)', 'relative_humidity_2m (%)', 'surface_pressure (hPa)',
                     'hour', 'day_of_week', 'month', 'temp_humidity_interaction', 'temp_pressure_interaction'] + \
                    [f'temperature_lag_{i}' for i in range(1, 4)] + \
                    [f'humidity_lag_{i}' for i in range(1, 4)] + \
                    [f'pressure_lag_{i}' for i in range(1, 4)]
    
    input_data = pd.DataFrame([features], columns=feature_names)
    input_scaled = scaler.transform(input_data)
    prediction_encoded = model.predict(input_scaled)[0]
    return label_encoder.inverse_transform([prediction_encoded])[0]

# Hàm xử lý dữ liệu và lưu dự báo
def process_weather_data():
    # Kết nối SQLite
    try:
        conn = sqlite3.connect('weather_data.db')
        cursor = conn.cursor()
        logging.info("Kết nối SQLite thành công")
    except Exception as e:
        logging.error(f"Lỗi kết nối SQLite: {e}")
        raise
    
    # Tạo bảng forecast_history nếu chưa tồn tại
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            weather_description TEXT,
            icon_file TEXT
        )
    ''')
    conn.commit()
    
    # Kiểm tra dữ liệu sensor_data
    cursor.execute("SELECT COUNT(*) FROM sensor_data")
    if cursor.fetchone()[0] < 4:
        logging.error("Không đủ 4 dòng dữ liệu trong sensor_data")
        conn.close()
        raise Exception("Không đủ dữ liệu")
    
    # Lấy 4 dòng mới nhất
    cursor.execute('SELECT temperature, humidity, pressure, timestamp FROM sensor_data ORDER BY id DESC LIMIT 4')
    rows = cursor.fetchall()
    
    # Dữ liệu trễ
    custom_lags = {
        'temperature_lag_1': rows[3][0],
        'temperature_lag_2': rows[2][0],
        'temperature_lag_3': rows[1][0],
        'humidity_lag_1': rows[3][1],
        'humidity_lag_2': rows[2][1],
        'humidity_lag_3': rows[1][1],
        'pressure_lag_1': rows[3][2],
        'pressure_lag_2': rows[2][2],
        'pressure_lag_3': rows[1][2]
    }
    
    # Dữ liệu hiện tại
    current_data = {
        'temperature_2m (C)': rows[0][0],
        'relative_humidity_2m (%)': rows[0][1],
        'surface_pressure (hPa)': rows[0][2]
    }
    current_timestamp = datetime.strptime(rows[0][3], '%Y-%m-%d %H:%M:%S')
    logging.info(f"Dữ liệu hiện tại: {current_data}, Thời gian: {current_timestamp}")
    
    # Ánh xạ thời tiết
    weather_map = {
        0: ("Trời quang", "sunny.png"),
        1: ("Chủ yếu quang", "partly_cloudy.png"),
        2: ("Mây rải rác", "partly_cloudy.png"),
        3: ("Trời Nhiều mây", "cloudy.png"),
        45: ("Sương mù", "fog.png"),
        50: ("Mưa hoặc dông", "rain.png")
    }
    
    # Dự báo
    hour = current_timestamp.hour
    day_of_week = current_timestamp.weekday()
    month = current_timestamp.month
    prediction = predict_weather(current_data, custom_lags, hour, day_of_week, month)
    weather_description, icon_file = weather_map.get(int(prediction), ("Không xác định", "unknown.png"))
    
    # Lưu dự báo vào forecast_history
    cursor.execute('''
        INSERT INTO forecast_history (timestamp, temperature, humidity, pressure, weather_description, icon_file)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        current_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        current_data['temperature_2m (C)'],
        current_data['relative_humidity_2m (%)'],
        current_data['surface_pressure (hPa)'],
        weather_description,
        icon_file
    ))
    conn.commit()
    logging.info("Đã lưu dự báo vào forecast_history")
    
    # Đóng kết nối
    conn.close()

# Lên lịch chạy mỗi giờ
schedule.every(10).seconds.do(process_weather_data)

# Chạy lần đầu
process_weather_data()

# Vòng lặp scheduler
while True:
    schedule.run_pending()
    time.sleep(60)