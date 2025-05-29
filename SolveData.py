
import pandas as pd
import numpy as np
import joblib
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import logging
import sqlite3
import pytz
from PIL import Image, ImageTk
# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tải mô hình, scaler và label encoder
try:
    model = joblib.load('E:\\Weather\\weather_model.pkl')
    scaler = joblib.load('E:\\Weather\\scaler.pkl')
    label_encoder = joblib.load('E:\\Weather\\label_encoder.pkl')
    logging.info("Đã tải mô hình, scaler và label encoder thành công")
except Exception as e:
    logging.error(f"Lỗi khi tải mô hình/scaler/label encoder: {e}")
    raise

# Đọc dữ liệu lịch sử từ CSV
try:
    data = pd.read_csv('E:\\Weather\\open-meteo-10.88N106.75E33m.csv')
    logging.info(f"Đã đọc dữ liệu lịch sử, số dòng: {len(data)}")
except Exception as e:
    logging.error(f"Lỗi khi đọc dữ liệu: {e}")
    raise

# Ánh xạ mã thời tiết
def map_weather_code(code):
    rain_codes = [61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    return 50 if code in rain_codes else code

data['weather_code'] = data['weather_code (wmo code)'].apply(map_weather_code)

# Tạo đặc trưng trễ
for lag in range(1, 4):
    data[f'temperature_lag_{lag}'] = data['temperature_2m (C)'].shift(lag)
    data[f'humidity_lag_{lag}'] = data['relative_humidity_2m (%)'].shift(lag)
    data[f'pressure_lag_{lag}'] = data['surface_pressure (hPa)'].shift(lag)

# Loại bỏ các dòng có NaN
data = data.dropna()
logging.info(f"Số dòng sau khi bỏ NaN: {len(data)}")

# Kết nối tới SQLite database
db_file = 'weather_data.db'
try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    logging.info("Đã kết nối thành công tới database SQLite")
except Exception as e:
    logging.error(f"Lỗi khi kết nối tới database: {e}")
    raise

# Kiểm tra xem bảng sensor_data có dữ liệu không
cursor.execute("SELECT COUNT(*) FROM sensor_data")
count = cursor.fetchone()[0]
if count < 4:
    logging.error(f"Bảng sensor_data không đủ dữ liệu (cần ít nhất 4 dòng). Số dòng hiện tại: {count}")
    messagebox.showerror("Lỗi", "Bảng sensor_data không đủ dữ liệu (cần ít nhất 4 dòng).")
    conn.close()
    raise Exception("Bảng sensor_data không đủ dữ liệu")

# Lấy 4 dòng gần nhất từ bảng sensor_data để làm dữ liệu
cursor.execute('SELECT temperature, humidity, pressure, timestamp FROM sensor_data ORDER BY id DESC LIMIT 4')
rows = cursor.fetchall()
if len(rows) < 4:
    logging.error("Không đủ 4 dòng dữ liệu trong sensor_data")
    messagebox.showerror("Lỗi", "Không đủ 4 dòng dữ liệu trong sensor_data")
    conn.close()
    raise Exception("Không đủ 4 dòng dữ liệu")

# Dữ liệu trễ (lag) từ 3 dòng trước dòng hiện tại
custom_lags = {
    'temperature_lag_1': rows[3][0],  # Dòng thứ hai
    'temperature_lag_2': rows[2][0],  # Dòng thứ ba
    'temperature_lag_3': rows[1][0],  # Dòng thứ tư
    'humidity_lag_1': rows[3][1],
    'humidity_lag_2': rows[2][1],
    'humidity_lag_3': rows[1][1],
    'pressure_lag_1': rows[3][2],
    'pressure_lag_2': rows[2][2],
    'pressure_lag_3': rows[1][2]
}
logging.info(f"Dữ liệu trễ từ database: {custom_lags}")

# Lấy dữ liệu hiện tại (dòng cuối cùng từ sensor_data)
current_row = rows[0]
current_data = {
    'temperature_2m (C)': current_row[0],
    'relative_humidity_2m (%)': current_row[1],
    'surface_pressure (hPa)': current_row[2]
}
current_timestamp = current_row[3]
logging.info(f"Dữ liệu hiện tại từ database: {current_data}, Timestamp: {current_timestamp}")

# Đóng kết nối database
conn.close()

# Lấy thời gian từ current_timestamp
# Chuyển đổi current_timestamp thành đối tượng datetime
current_time = datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S')
hour = 15
day_of_week = 2
month = 5
# Tạo đặc trưng tương tác
temp_humidity_interaction = current_data['temperature_2m (C)'] * current_data['relative_humidity_2m (%)']
temp_pressure_interaction = current_data['temperature_2m (C)'] * current_data['surface_pressure (hPa)']

# Kết hợp dữ liệu hiện tại và các đặc trưng
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

# Tạo DataFrame với danh sách đặc trưng khớp với huấn luyện
feature_names = ['temperature_2m (C)', 'relative_humidity_2m (%)', 'surface_pressure (hPa)',
                 'hour', 'day_of_week', 'month', 'temp_humidity_interaction', 'temp_pressure_interaction'] + \
                [f'temperature_lag_{i}' for i in range(1, 4)] + \
                [f'humidity_lag_{i}' for i in range(1, 4)] + \
                [f'pressure_lag_{i}' for i in range(1, 4)]
input_data = pd.DataFrame([features], columns=feature_names)

# Chuẩn hóa và dự đoán
try:
    input_scaled = scaler.transform(input_data)
    probabilities = model.predict_proba(input_scaled)[0]  # Lấy xác suất cho từng lớp
    prediction_encoded = model.predict(input_scaled)[0]
    prediction = label_encoder.inverse_transform([prediction_encoded])[0]
    logging.info(f"Xác suất dự đoán cho từng lớp: {dict(zip(label_encoder.classes_, probabilities))}")
    logging.info(f"Dự đoán mã thời tiết: {prediction}")
except Exception as e:
    logging.error(f"Lỗi khi dự đoán: {e}")
    messagebox.showerror("Lỗi", f"Không thể dự đoán: {e}")
    raise

# Mô tả thời tiết và ánh xạ icon
weather_map = {
    0: ("Trời quang", "sunny.png"),
    1: ("Chủ yếu quang", "partly_cloudy.png"),
    2: ("Mây rải rác", "partly_cloudy.png"),
    3: ("Trời Nhiều mây", "cloudy.png"),
    45: ("Sương mù", "fog.png"),
    50: ("Mưa hoặc dông", "rain.png")
}
weather_description, icon_file = weather_map.get(int(prediction), ("Không xác định", "unknown.png"))

# Giao diện đẹp hơn với icon
root = tk.Tk()
root.title("Dự Báo Thời Tiết")
root.geometry("400x500")  # Điều chỉnh kích thước để hài hòa
root.configure(bg="#E0F7FA")  # Màu nền xanh nhạt hơn, giống giao diện bạn cung cấp

# Tiêu đề
title_label = tk.Label(root, text="Dự Báo Thời Tiết", font=("Arial", 24, "bold"), bg="#E0F7FA", fg="#0288D1")
title_label.pack(pady=10)

# Frame chứa thông tin
info_frame = tk.Frame(root, bg="#E0F7FA")
info_frame.pack(pady=15)

# Hiển thị thời gian
time_label = tk.Label(info_frame, text=f"Thời gian: {current_timestamp}", font=("Arial", 12), bg="#E0F7FA", fg="#424242")
time_label.pack(pady=5)

# Hiển thị nhiệt độ
temp_label = tk.Label(info_frame, text=f"Nhiệt độ: {current_data['temperature_2m (C)']}°C", font=("Arial", 12), bg="#E0F7FA", fg="#424242")
temp_label.pack(pady=5)

# Hiển thị độ ẩm
humidity_label = tk.Label(info_frame, text=f"Độ ẩm: {current_data['relative_humidity_2m (%)']}%", font=("Arial", 12), bg="#E0F7FA", fg="#424242")
humidity_label.pack(pady=5)

# Hiển thị áp suất
pressure_label = tk.Label(info_frame, text=f"Áp suất: {current_data['surface_pressure (hPa)']} hPa", font=("Arial", 12), bg="#E0F7FA", fg="#424242")
pressure_label.pack(pady=5)

# Frame chứa dự báo thời tiết
weather_frame = tk.Frame(root, bg="#FFFFFF", padx=20, pady=20)
weather_frame.pack(pady=20, expand=True)

# Tải và hiển thị icon
try:
    icon_path = f"E:\\Weather\\icons\\{icon_file}"
    icon_image = Image.open(icon_path).resize((100, 100), Image.Resampling.LANCZOS)  # Tăng kích thước icon
    icon_photo = ImageTk.PhotoImage(icon_image)
    icon_label = tk.Label(weather_frame, image=icon_photo, bg="#FFFFFF")
    icon_label.image = icon_photo  # Giữ tham chiếu để tránh GC
    icon_label.pack(pady=10)
except Exception as e:
    logging.error(f"Lỗi khi tải icon: {e}")
    icon_label = tk.Label(weather_frame, text="Icon không tải được", bg="#FFFFFF", fg="#D32F2F")
    icon_label.pack(pady=10)

# Hiển thị mô tả thời tiết
weather_text = tk.Label(weather_frame, text=f"Dự báo: {weather_description}", font=("Arial", 18, "bold"), bg="#FFFFFF", fg="#2E7D32")
weather_text.pack(pady=10)

# Hàm tự động đóng UI sau 10 giây
def auto_close():
    root.after(10000, root.quit)  # 10000ms = 10 giây

# Gọi hàm tự động đóng khi UI khởi động
auto_close()

root.mainloop()
print("UI đã đóng.")