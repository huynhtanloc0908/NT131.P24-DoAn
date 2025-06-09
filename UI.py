import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from PIL import Image, ImageTk
import logging
from datetime import datetime
import os

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def display_forecasts():
    try:
        conn = sqlite3.connect('weather_data.db')
        cursor = conn.cursor()
        logging.info("Kết nối SQLite thành công")
    except Exception as e:
        logging.error(f"Lỗi kết nối SQLite: {e}")
        messagebox.showerror("Lỗi", f"Không thể kết nối đến cơ sở dữ liệu: {e}")
        return

    try:
        cursor.execute('SELECT timestamp, temperature, humidity, pressure, weather_description, icon_file FROM forecast_history ORDER BY id DESC LIMIT 24')
        forecasts = cursor.fetchall()
        logging.info(f"Đã lấy {len(forecasts)} dự báo từ forecast_history")
    except Exception as e:
        logging.error(f"Lỗi truy vấn dữ liệu: {e}")
        messagebox.showerror("Lỗi", f"Không thể truy vấn dữ liệu: {e}")
        conn.close()
        return
    finally:
        conn.close()

    root = tk.Tk()
    root.title("Lịch Sử Dự Báo Thời Tiết")
    root.geometry("500x740")
    root.configure(bg="#E3F2FD")

    # Header
    title_frame = tk.Frame(root, bg="#E3F2FD")
    title_frame.pack(pady=10)

    tk.Label(title_frame, text="Lịch Sử Dự Báo 24 Giờ", font=("Helvetica", 20, "bold"), bg="#E3F2FD", fg="#0D47A1").pack()
    tk.Label(title_frame, text=datetime.now().strftime("Ngày: %Y-%m-%d"), font=("Helvetica", 11, "italic"), bg="#E3F2FD", fg="#424242").pack(pady=2)

    tk.Button(title_frame, text="🔄 Làm mới", command=lambda: [root.destroy(), display_forecasts()],
              font=("Helvetica", 10), bg="#1976D2", fg="white", relief="flat", padx=10, pady=5).pack(pady=4)

    # Scrollable area
    canvas = tk.Canvas(root, bg="#E3F2FD", highlightthickness=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#E3F2FD")

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Hỗ trợ cuộn chuột
    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    # Danh sách tham chiếu icon để tránh bị xóa
    photo_refs = []

    if not forecasts:
        tk.Label(scrollable_frame, text="Không có dữ liệu dự báo.\nVui lòng chạy predict.py trước!",
                 font=("Helvetica", 14), bg="#E3F2FD", fg="#D32F2F").pack(pady=20)
    else:
        for forecast in reversed(forecasts):
            timestamp, temperature, humidity, pressure, description, icon_file = forecast
        
            container = tk.Frame(scrollable_frame, bg="#FFFFFF", bd=1, relief="solid")
            container.pack(fill="x", padx=90, pady=12)

            inner = tk.Frame(container, bg="#FFFFFF")
            inner.pack(fill="x", padx=10, pady=10)

            info_frame = tk.Frame(inner, bg="#FFFFFF")
            info_frame.pack(side="left", fill="both", expand=True)

            tk.Label(info_frame, text=f"🕒 {timestamp}", font=("Helvetica", 13, "bold"), bg="#FFFFFF", fg="#0D47A1").pack(anchor="w", pady=(0, 6))
            tk.Label(info_frame, text=f"🌡️ Nhiệt độ: {temperature:.1f}°C", font=("Helvetica", 10), bg="#FFFFFF").pack(anchor="w")
            tk.Label(info_frame, text=f"💧 Độ ẩm: {humidity:.1f}%", font=("Helvetica", 10), bg="#FFFFFF").pack(anchor="w")
            tk.Label(info_frame, text=f"🌬️ Áp suất: {pressure:.1f} hPa", font=("Helvetica", 10), bg="#FFFFFF").pack(anchor="w")
            tk.Label(info_frame, text=f"🔍 Dự báo: {description}", font=("Helvetica", 11, "bold"), fg="#2E7D32", bg="#FFFFFF").pack(anchor="w", pady=4)

            # Hiển thị icon nếu có
            icon_frame = tk.Frame(inner, bg="#FFFFFF")
            icon_frame.pack(side="right", padx=10)
            icon_path = os.path.join("D:/NT131.P24-DoAn/icons", icon_file)
            try:
                if os.path.exists(icon_path):
                    image = Image.open(icon_path).resize((60, 60), Image.Resampling.LANCZOS)
                    icon_photo = ImageTk.PhotoImage(image)
                    tk.Label(icon_frame, image=icon_photo, bg="#FFFFFF").pack()
                    photo_refs.append(icon_photo)
                else:
                    raise FileNotFoundError("Không tìm thấy file icon.")
            except Exception as e:
                logging.warning(f"Không thể tải icon {icon_file}: {e}")
                tk.Label(icon_frame, text="(không có biểu tượng)", bg="#FFFFFF", fg="gray").pack()

    root.mainloop()
    logging.info("UI đã đóng.")

if __name__ == "__main__":
    display_forecasts()
