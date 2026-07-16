import cv2
import numpy as np
import os
import sqlite3
import time
from datetime import datetime
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from ultralytics import YOLO

from desktop_app.core.config import BEST_PT_PATH, BEST_ONNX_PATH, DB_PATH, CAPTURES_DIR

class ModelWorker(QThread):
    # Các tín hiệu (signals) để gửi dữ liệu về giao diện chính (GUI)
    frame_processed = Signal(QImage)
    violation_detected = Signal(dict)
    stats_updated = Signal(dict)
    status_message = Signal(str)
    finished = Signal()

    def __init__(self, video_path, polygons, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.polygons = polygons  # dict chứa: mode, car, moto, wrongway_down, wrongway_up
        self.session_id = f"desktop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Các cờ điều khiển luồng
        self.is_running = True
        self.is_paused = False
        
        # Cấu hình phát hiện
        self.conf_thresh = 0.5
        self.iou_thresh = 0.45
        self.img_size = 640
        
        # Trạng thái thống kê và lịch sử tracking
        self.stats = {'car': 0, 'moto': 0, 'bus': 0, 'truck': 0, 'motorcycle': 0}
        self.violator_info = {}  # {obj_id_int: (event_name, label_suffix)}
        self.track_history = {}  # {obj_id_int: [y_coordinates]}
        
        # Kiểm tra xem file model nào khả dụng (PT ưu tiên hơn ONNX nếu có)
        self.weights_path = BEST_ONNX_PATH
        if not os.path.exists(self.weights_path):
            self.weights_path = BEST_PT_PATH

    def stop(self):
        self.is_running = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def update_polygons(self, new_polygons):
        """Cập nhật tọa độ vùng giám sát khi đang chạy"""
        self.polygons = new_polygons

    def log_violation_to_db(self, vehicle_id, vehicle_type, event_type, capture_url):
        """Ghi nhận lỗi vi phạm trực tiếp vào cơ sở dữ liệu SQLite dùng chung"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Đảm bảo bảng tồn tại phòng trường hợp backend chưa được chạy lần nào
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS violation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(255),
                    vehicle_id INTEGER,
                    vehicle_type VARCHAR(255),
                    event_type VARCHAR(255),
                    capture_url VARCHAR(255)
                )
            """)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            cursor.execute(
                """
                INSERT INTO violation_logs (timestamp, session_id, vehicle_id, vehicle_type, event_type, capture_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (now_str, self.session_id, vehicle_id, vehicle_type, event_type, capture_url)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Lỗi ghi nhận vi phạm vào SQLite: {e}")

    def run(self):
        self.status_message.emit("Đang nạp Model YOLO...")
        if not os.path.exists(self.weights_path):
            self.status_message.emit(f"Không tìm thấy file model weights tại: {self.weights_path}")
            self.finished.emit()
            return

        try:
            model = YOLO(self.weights_path)
            self.status_message.emit("Nạp Model thành công! Đang mở video...")
        except Exception as e:
            self.status_message.emit(f"Lỗi nạp Model: {str(e)}")
            self.finished.emit()
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.status_message.emit("Không thể mở tệp video.")
            self.finished.emit()
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.status_message.emit(f"Đang xử lý video ({width}x{height})...")

        # Hàm tỷ lệ đa giác theo kích thước thực của khung hình video
        def scale_poly(poly):
            if not poly or len(poly) < 3: return None
            return np.array([[int(p[0] * width / 100), int(p[1] * height / 100)] for p in poly], np.int32)

        while cap.isOpened() and self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue

            ret, frame = cap.read()
            if not ret:
                break

            # Lấy thông tin các đa giác hiện tại
            surveillance_mode = self.polygons.get('mode', 0)
            LANE_CAR = scale_poly(self.polygons.get('car', []))
            LANE_MOTO = scale_poly(self.polygons.get('moto', []))
            WW_DOWN_ZONE = scale_poly(self.polygons.get('wrongway_down', []))
            WW_UP_ZONE = scale_poly(self.polygons.get('wrongway_up', []))

            # Chạy YOLO tracking
            results = model.track(
                source=frame, conf=self.conf_thresh, iou=self.iou_thresh, imgsz=self.img_size,
                max_det=300, tracker="bytetrack.yaml", persist=True, verbose=False
            )

            annotated_frame = frame.copy()

            # Vẽ các vùng đa giác giám sát lên khung hình
            # Xanh dương nét đứt/mỏng cho ô tô, xanh lá cho xe máy, vàng/cam cho đi ngược chiều
            if LANE_CAR is not None:
                cv2.polylines(annotated_frame, [LANE_CAR], isClosed=True, color=(255, 0, 0), thickness=2)
                cv2.putText(annotated_frame, "Lan O To", tuple(LANE_CAR[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            if LANE_MOTO is not None:
                cv2.polylines(annotated_frame, [LANE_MOTO], isClosed=True, color=(0, 255, 0), thickness=2)
                cv2.putText(annotated_frame, "Lan Xe May", tuple(LANE_MOTO[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            if WW_DOWN_ZONE is not None:
                cv2.polylines(annotated_frame, [WW_DOWN_ZONE], isClosed=True, color=(0, 165, 255), thickness=2) # Orange
                cv2.putText(annotated_frame, "Nguoc Chieu (Xuong)", tuple(WW_DOWN_ZONE[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
            if WW_UP_ZONE is not None:
                cv2.polylines(annotated_frame, [WW_UP_ZONE], isClosed=True, color=(0, 255, 255), thickness=2) # Yellow
                cv2.putText(annotated_frame, "Nguoc Chieu (Len)", tuple(WW_UP_ZONE[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # Xử lý Logic Box phát hiện xe vi phạm
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                clss = results[0].boxes.cls.cpu().numpy()
                ids = results[0].boxes.id.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()

                for box, cls, obj_id, conf in zip(boxes, clss, ids, confs):
                    x1, y1, x2, y2 = map(int, box)
                    class_id = int(cls)
                    name = model.names[class_id].lower()
                    obj_id_int = int(obj_id)

                    bottom_center = (int((x1 + x2) / 2), int(y2))
                    is_violation = False
                    event_name = ""
                    label_text = f"ID:{obj_id_int} {name} {conf:.2f}"
                    base_label_suffix = ""

                    if obj_id_int in self.violator_info:
                        is_violation = True
                        event_name, base_label_suffix = self.violator_info[obj_id_int]
                        label_text += " " + base_label_suffix
                    else:
                        # 1. LOGIC SAI LÀN ĐƯỜNG
                        if surveillance_mode in [0, 2]:
                            if LANE_CAR is not None and LANE_MOTO is not None:
                                in_car_lane = cv2.pointPolygonTest(LANE_CAR, bottom_center, False) >= 0
                                in_moto_lane = cv2.pointPolygonTest(LANE_MOTO, bottom_center, False) >= 0

                                if name in ['moto', 'motorcycle']:
                                    if in_car_lane and not in_moto_lane:
                                        is_violation = True
                                        event_name = "Sai Lan"
                                        base_label_suffix = "[VI PHAM]"
                                        label_text += " " + base_label_suffix
                                elif name in ['car', 'bus', 'truck']:
                                    if in_moto_lane and not in_car_lane:
                                        is_violation = True
                                        event_name = "Sai Lan"
                                        base_label_suffix = "[VI PHAM]"
                                        label_text += " " + base_label_suffix

                        # 2. LOGIC ĐI NGƯỢC CHIỀU
                        if surveillance_mode in [1, 2] and not is_violation:
                            if WW_DOWN_ZONE is not None and cv2.pointPolygonTest(WW_DOWN_ZONE, bottom_center, False) >= 0:
                                if obj_id_int in self.track_history and len(self.track_history[obj_id_int]) >= 5:
                                    prev_y = int(self.track_history[obj_id_int][0])
                                    # Trong Down Zone (làn đi xuống), nếu đi LÊN (prev_y - y2 > 5) là NGƯỢC CHIỀU
                                    if prev_y - int(y2) > 5:
                                        is_violation = True
                                        event_name = "Nguoc Chieu"
                                        base_label_suffix = "[NGUOC CHIEU]"
                                        label_text += " " + base_label_suffix

                            elif WW_UP_ZONE is not None and cv2.pointPolygonTest(WW_UP_ZONE, bottom_center, False) >= 0:
                                if obj_id_int in self.track_history and len(self.track_history[obj_id_int]) >= 5:
                                    prev_y = int(self.track_history[obj_id_int][0])
                                    # Trong Up Zone (làn đi lên), nếu đi XUỐNG (y2 - prev_y > 5) là NGƯỢC CHIỀU
                                    if int(y2) - prev_y > 5:
                                        is_violation = True
                                        event_name = "Nguoc Chieu"
                                        base_label_suffix = "[NGUOC CHIEU]"
                                        label_text += " " + base_label_suffix

                    # Cập nhật lịch sử di chuyển
                    if obj_id_int not in self.track_history:
                        self.track_history[obj_id_int] = []
                    self.track_history[obj_id_int].append(int(y2))
                    if len(self.track_history[obj_id_int]) > 15:
                        self.track_history[obj_id_int].pop(0)

                    # Vẽ khung hình và xử lý khi phát hiện xe vi phạm
                    if is_violation:
                        bbox_color = (0, 0, 255) # Màu đỏ cảnh báo vi phạm
                        
                        if obj_id_int not in self.violator_info:
                            self.violator_info[obj_id_int] = (event_name, base_label_suffix)
                            # Cập nhật thống kê
                            if name in self.stats:
                                self.stats[name] += 1
                            else:
                                self.stats[name] = 1
                            self.stats_updated.emit(self.stats)

                            # Chụp ảnh cận cảnh khu vực xe vi phạm
                            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                            capture_name = f"cap_desktop_{timestamp_str}_{obj_id_int}.jpg"
                            capture_path = os.path.join(CAPTURES_DIR, capture_name)

                            try:
                                h_frm, w_frm = frame.shape[:2]
                                cx1, cy1 = max(0, x1 - 15), max(0, y1 - 15)
                                cx2, cy2 = min(w_frm, x2 + 15), min(h_frm, y2 + 15)
                                car_img = frame[cy1:cy2, cx1:cx2]
                                cv2.imwrite(capture_path, car_img)
                            except Exception as e:
                                print(f"Lỗi cắt ảnh xe vi phạm: {e}")

                            # Tạo đường dẫn URL cho ảnh (tương thích cấu trúc server backend tĩnh)
                            capture_url = f"http://localhost:8000/static/captures/{capture_name}"

                            # Ghi nhận vào SQLite DB
                            self.log_violation_to_db(obj_id_int, name, event_name, capture_url)

                            # Gửi tín hiệu báo lỗi vi phạm mới về Main Window UI
                            self.violation_detected.emit({
                                "id": obj_id_int,
                                "type": name,
                                "event": event_name,
                                "time": datetime.now().strftime('%H:%M:%S'),
                                "image_path": capture_path, # Truy cập trực tiếp file nội bộ
                                "image_url": capture_url
                            })

                        # Vẽ hình hộp đỏ khoanh vùng xe vi phạm
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), bbox_color, 2)
                        cv2.circle(annotated_frame, bottom_center, radius=5, color=(0, 0, 255), thickness=-1)
                        
                        # Vẽ nền chữ
                        (w, h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                        cv2.rectangle(annotated_frame, (x1, y1 - 20), (x1 + w, y1), bbox_color, -1)
                        cv2.putText(annotated_frame, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Chuyển đổi khung hình sang định dạng hiển thị QImage của Qt
            rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            
            # Gửi khung hình về giao diện chính
            self.frame_processed.emit(qt_image)
            
            # Giới hạn tốc độ đọc/xử lý xấp xỉ tốc độ khung hình (khoảng 30fps)
            time.sleep(0.01)

        cap.release()
        self.status_message.emit("Đã hoàn thành hoặc dừng xử lý video.")
        self.finished.emit()
