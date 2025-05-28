import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
from datetime import datetime

# ===================== Kết nối và tạo bảng trong SQLite =====================
conn = sqlite3.connect("weather_data.db")
cursor = conn.cursor()

# Tạo bảng weather_data nếu chưa tồn tại
cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    weather_label TEXT
)
""")
conn.commit()

# ===================== Thêm dữ liệu mẫu (nếu chưa có) =====================
cursor.execute("SELECT COUNT(*) FROM weather_data")
if cursor.fetchone()[0] == 0:
    # Thêm dữ liệu mẫu
    sample_data = [
        ("2025-05-26 10:00:00", 25.0, 60.0, 1013.0, "on_dinh"),
        ("2025-05-26 11:00:00", 28.0, 85.0, 998.0, "mua"),
        ("2025-05-26 12:00:00", 30.0, 50.0, 1022.0, "nang")
    ]
    cursor.executemany("INSERT INTO weather_data (timestamp, temperature, humidity, pressure, weather_label) VALUES (?, ?, ?, ?, ?)", sample_data)
    conn.commit()

# ===================== Đọc dữ liệu từ SQLite =====================
df = pd.read_sql("SELECT * FROM weather_data", conn)
conn.close()

if df.empty:
    print("⚠️ Không có dữ liệu trong database.")
    exit()

# ===================== Gắn nhãn dự báo (tạm thời) =====================
def label_weather(row):
    if row['pressure'] < 1000 and row['humidity'] > 85:
        return "mua"
    elif row['pressure'] > 1020 and row['humidity'] < 60:
        return "nang"
    else:
        return "on_dinh"

df['weather_label'] = df.apply(label_weather, axis=1)

# ===================== Tiền xử lý =====================
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
df['day'] = df['timestamp'].dt.day
df['month'] = df['timestamp'].dt.month

# Lựa chọn đặc trưng
features = ['temperature', 'humidity', 'pressure', 'hour', 'day', 'month']
X = df[features]

# Gán nhãn số bằng LabelEncoder
le = LabelEncoder()
y = le.fit_transform(df['weather_label'])

# ===================== Huấn luyện mô hình =====================
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, y)

# ===================== Lưu mô hình và encoder =====================
joblib.dump(clf, "weather_classifier.pkl")
joblib.dump(le, "weather_label_encoder.pkl")

print("✅ Huấn luyện và lưu mô hình phân loại thời tiết thành công.")