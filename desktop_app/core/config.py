import os

# Đường dẫn gốc của dự án (new_UI_for_DATN/)
CORE_DIR = os.path.dirname(os.path.abspath(__file__)) # desktop_app/core/
APP_DIR = os.path.dirname(CORE_DIR) # desktop_app/
ROOT_DIR = os.path.dirname(APP_DIR) # new_UI_for_DATN/

# Đường dẫn tới thư mục chứa model YOLO dùng chung
MODEL_DIR = os.path.join(ROOT_DIR, "model")
BEST_ONNX_PATH = os.path.join(MODEL_DIR, "best.onnx")
BEST_PT_PATH = os.path.join(MODEL_DIR, "best.pt")

# Đường dẫn tới cơ sở dữ liệu SQLite dùng chung của Backend
DB_PATH = os.path.join(ROOT_DIR, "backend", "db", "traffic_logs.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Đường dẫn tới thư mục lưu ảnh chụp vi phạm của Backend (để dùng chung dữ liệu ảnh)
CAPTURES_DIR = os.path.join(ROOT_DIR, "backend", "static", "captures")

# Tạo các thư mục nếu chưa tồn tại
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(CAPTURES_DIR, exist_ok=True)
