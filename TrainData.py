import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
from imblearn.over_sampling import SMOTE
import joblib
from datetime import datetime
import xgboost as xgb
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Đọc dữ liệu
try:
    data = pd.read_csv('E:\\Weather\\open-meteo-10.88N106.75E33m.csv')
    logging.info(f"Số dòng ban đầu: {len(data)}")
except Exception as e:
    logging.error(f"Lỗi khi đọc dữ liệu: {e}")
    raise

# Ánh xạ các mã thời tiết mưa/dông thành lớp 50
def map_weather_code(code):
    rain_codes = [61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    return 50 if code in rain_codes else code

data['weather_code'] = data['weather_code (wmo code)'].apply(map_weather_code)

# Tạo đặc trưng trễ
for lag in range(1, 4):
    data[f'temperature_lag_{lag}'] = data['temperature_2m (C)'].shift(lag)
    data[f'humidity_lag_{lag}'] = data['relative_humidity_2m (%)'].shift(lag)
    data[f'pressure_lag_{lag}'] = data['surface_pressure (hPa)'].shift(lag)

# Tạo đặc trưng thời gian
data['time'] = pd.to_datetime(data['time'])
data['hour'] = data['time'].dt.hour
data['day_of_week'] = data['time'].dt.dayofweek
data['month'] = data['time'].dt.month

# Tạo đặc trưng tương tác
data['temp_humidity_interaction'] = data['temperature_2m (C)'] * data['relative_humidity_2m (%)']
data['temp_pressure_interaction'] = data['temperature_2m (C)'] * data['surface_pressure (hPa)']

# Loại bỏ các dòng có NaN
data = data.dropna()
logging.info(f"Số dòng sau khi bỏ NaN: {len(data)}")

# Kiểm tra phân bố lớp
logging.info(f"Phân bố lớp weather_code:\n{data['weather_code'].value_counts()}")

# Loại bỏ các lớp có ít hơn 5 mẫu
min_samples = 5
class_counts = data['weather_code'].value_counts()
valid_classes = class_counts[class_counts >= min_samples].index
data = data[data['weather_code'].isin(valid_classes)]
logging.info(f"Số dòng sau khi loại bỏ lớp hiếm: {len(data)}")

# Chọn đặc trưng và nhãn
features = ['temperature_2m (C)', 'relative_humidity_2m (%)', 'surface_pressure (hPa)',
            'hour', 'day_of_week', 'month', 'temp_humidity_interaction', 'temp_pressure_interaction'] + \
           [f'temperature_lag_{i}' for i in range(1, 4)] + \
           [f'humidity_lag_{i}' for i in range(1, 4)] + \
           [f'pressure_lag_{i}' for i in range(1, 4)]
X = data[features]
y = data['weather_code']

# Mã hóa nhãn
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
logging.info(f"Nhãn sau khi mã hóa: {np.unique(y_encoded)}")

# Chia dữ liệu
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
logging.info(f"Số mẫu tập kiểm tra: {len(X_test)}")
logging.info(f"Số mẫu mỗi lớp trong tập kiểm tra:\n{pd.Series(y_test).value_counts()}")

# Chuẩn hóa dữ liệu
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Áp dụng SMOTE
smote = SMOTE(sampling_strategy='auto', random_state=42, k_neighbors=3)
try:
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train)
    logging.info("SMOTE thành công")
except ValueError as e:
    logging.error(f"Lỗi SMOTE: {e}")
    X_train_resampled, y_train_resampled = X_train_scaled, y_train

# Tìm kiếm siêu tham số cho RandomForest
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5],
    'min_samples_leaf': [1, 2]
}
rf = RandomForestClassifier(random_state=42, class_weight='balanced')
grid_search = GridSearchCV(rf, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
grid_search.fit(X_train_resampled, y_train_resampled)

# Mô hình tốt nhất từ GridSearch
best_rf = grid_search.best_estimator_
logging.info(f"Siêu tham số tốt nhất: {grid_search.best_params_}")

# Huấn luyện mô hình XGBoost
xgb_model = xgb.XGBClassifier(random_state=42, objective='multi:softmax', eval_metric='mlogloss')
xgb_model.fit(X_train_resampled, y_train_resampled)

# Dự đoán và đánh giá RandomForest
y_pred_rf = best_rf.predict(X_test_scaled)
y_pred_rf_decoded = label_encoder.inverse_transform(y_pred_rf)
y_test_decoded = label_encoder.inverse_transform(y_test)
logging.info(f"Độ chính xác RandomForest: {accuracy_score(y_test, y_pred_rf)}")
logging.info(f"Báo cáo phân loại RandomForest:\n{classification_report(y_test_decoded, y_pred_rf_decoded)}")

# Dự đoán và đánh giá XGBoost
y_pred_xgb = xgb_model.predict(X_test_scaled)
y_pred_xgb_decoded = label_encoder.inverse_transform(y_pred_xgb)
logging.info(f"Độ chính xác XGBoost: {accuracy_score(y_test, y_pred_xgb)}")
logging.info(f"Báo cáo phân loại XGBoost:\n{classification_report(y_test_decoded, y_pred_xgb_decoded)}")

# Lưu mô hình và scaler tốt nhất
if accuracy_score(y_test, y_pred_rf) > accuracy_score(y_test, y_pred_xgb):
    joblib.dump(best_rf, 'E:\\Weather\\weather_model.pkl')
    logging.info("Lưu mô hình RandomForest.")
else:
    joblib.dump(xgb_model, 'E:\\Weather\\weather_model.pkl')
    logging.info("Lưu mô hình XGBoost.")
joblib.dump(scaler, 'E:\\Weather\\scaler.pkl')
joblib.dump(label_encoder, 'E:\\Weather\\label_encoder.pkl')
logging.info("Scaler và LabelEncoder đã được lưu.")

# In ra độ quan trọng của đặc trưng (RandomForest)
feature_importance = pd.DataFrame({
    'feature': features,
    'importance': best_rf.feature_importances_
}).sort_values(by='importance', ascending=False)
logging.info(f"Độ quan trọng của đặc trưng:\n{feature_importance}")