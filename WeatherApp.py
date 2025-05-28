import tkinter as tk
import sqlite3
import joblib
from datetime import datetime
from flask import Flask, request, jsonify
import threading

# Load mô hình và encoder
model = joblib.load("weather_classifier.pkl")
label_encoder = joblib.load("weather_label_encoder.pkl")

# Flask app
app = Flask(__name__)

# Biến toàn cục lưu dữ liệu từ ESP32
sensor_data = {"temperature": None, "humidity": None, "pressure": None, "gas": None}

@app.route("/weather", methods=["POST"])
def receive_weather_data():
    global sensor_data
    try:
        data = request.get_json()
        print("Dữ liệu nhận được:", data)  # Thêm để debug
        sensor_data["temperature"] = float(data.get("temperature"))
        sensor_data["humidity"] = float(data.get("humidity"))
        sensor_data["pressure"] = float(data.get("pressure"))
        sensor_data["gas"] = float(data.get("gas"))
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Lỗi nhận dữ liệu: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# Chạy Flask server trong luồng riêng
def run_flask():
    app.run(host="0.0.0.0", port=5000)

# ===================== DATABASE =====================
conn = sqlite3.connect("weather_data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    weather_label TEXT,
    gas REAL
)
""")
conn.commit()

# ===================== XỬ LÝ DỰ BÁO =====================
def forecast_weather(temp, hum, pres):
    if temp is None or hum is None or pres is None:
        return "🤷 Không xác định"
    
    now = datetime.now()
    hour = now.hour
    day = now.day
    month = now.month

    features = [[temp, hum, pres, hour, day, month]]
    prediction = model.predict(features)
    label = label_encoder.inverse_transform(prediction)[0]

    emoji = {
        "mua": "🌧 Có thể có mưa",
        "nang": "☀️ Trời nắng đẹp",
        "on_dinh": "⛅ Thời tiết ổn định"
    }
    return emoji.get(label, "🤷 Không xác định")

# ===================== SENSOR & DATABASE =====================
def update_data():
    temp = sensor_data["temperature"]
    hum = sensor_data["humidity"]
    pres = sensor_data["pressure"]
    gas = sensor_data["gas"]

    if temp is None or hum is None or pres is None:
        label_temp.config(text="Nhiệt độ: Chưa có dữ liệu")
        label_hum.config(text="Độ ẩm: Chưa có dữ liệu")
        label_pres.config(text="Áp suất: Chưa có dữ liệu")
        label_forecast.config(text="Dự báo: Chưa có dữ liệu")
        return

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    weather_label = forecast_weather(temp, hum, pres)

    # Cập nhật GUI
    label_temp.config(text=f"Nhiệt độ: {temp}°C")
    label_hum.config(text=f"Độ ẩm: {hum}%")
    label_pres.config(text=f"Áp suất: {pres} hPa")
    label_time.config(text=f"Lúc: {time_now}")
    label_forecast.config(text=f"Dự báo: {weather_label}")

    # Lưu vào database
    cursor.execute("""
        INSERT INTO weather_data (timestamp, temperature, humidity, pressure, weather_label, gas)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (time_now, temp, hum, pres, weather_label.split()[0], gas))
    conn.commit()

# ===================== GUI =====================
root = tk.Tk()
root.title("Máy dự báo thời tiết (BME680)")
root.geometry("320x270")
root.resizable(False, False)

label_temp = tk.Label(root, text="Nhiệt độ: --°C", font=("Arial", 14))
label_temp.pack(pady=5)

label_hum = tk.Label(root, text="Độ ẩm: --%", font=("Arial", 14))
label_hum.pack(pady=5)

label_pres = tk.Label(root, text="Áp suất: -- hPa", font=("Arial", 14))
label_pres.pack(pady=5)

label_time = tk.Label(root, text="Lúc: --:--:--", font=("Arial", 12))
label_time.pack(pady=5)

label_forecast = tk.Label(root, text="Dự báo: --", font=("Arial", 13, "italic"), fg="blue")
label_forecast.pack(pady=5)

btn_update = tk.Button(root, text="Cập nhật dữ liệu", command=update_data)
btn_update.pack(pady=10)

# Chạy Flask server trong luồng riêng
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# Tự động cập nhật GUI mỗi 10 giây
def auto_update():
    update_data()
    root.after(10000, auto_update)

root.after(10000, auto_update)

root.mainloop()

# Đóng DB sau khi thoát
conn.close()