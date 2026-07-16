import cv2
import numpy as np
import os
import threading
import queue
from datetime import datetime
from ultralytics import YOLO

from app.db.database import SessionLocal
from app.db.models import ViolationLog

class ModelService:
    def __init__(self):
        from app.core.config import MODEL_DIR
        self.weights_path = os.path.join(MODEL_DIR, "best.onnx")
        
        if not os.path.exists(self.weights_path):
            self.weights_path = os.path.join(MODEL_DIR, "best.pt") 
            
        self.model = YOLO(self.weights_path)
        
        self.conf_thresh = 0.5
        self.iou_thresh = 0.45
        self.img_size = 640
        self.max_detect = 300
        self.line_width = 2
        
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_dir = os.path.join(self.base_dir, "static", "outputs")
        self.log_dir = os.path.join(self.base_dir, "static", "logs")
        self.capture_dir = os.path.join(self.base_dir, "static", "captures")
        
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.capture_dir, exist_ok=True)
        
        # Background worker cho việc ghi log vào Database
        self.db_queue = queue.Queue()
        self.db_worker_thread = threading.Thread(target=self._db_worker, daemon=True)
        self.db_worker_thread.start()

    def _db_worker(self):
        """Worker chạy ngầm để ghi dữ liệu vi phạm vào database, tránh block luồng xử lý video."""
        while True:
            log_data = self.db_queue.get()
            if log_data is None:  # Sentinel value to stop
                break
            
            db = SessionLocal()
            try:
                log = ViolationLog(**log_data)
                db.add(log)
                db.commit()
            except Exception as e:
                pass
            finally:
                db.close()
            
            self.db_queue.task_done()

    def generate_frames_worker(self, session_id: str, session_data: dict, timestamp: str, q: queue.Queue):
        video_path = session_data["video_path"]
        poly_data = session_data["polygons"]

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            session_data["is_running"] = False
            session_data["finished"] = True
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        def scale_poly(poly):
            if not poly or len(poly) < 3: return None
            return np.array([[int(p[0] * width / 100), int(p[1] * height / 100)] for p in poly], np.int32)

        # Cấu hình đa giác từ request Frontend
        surveillance_mode = poly_data.get('mode', 0)
        lane_car = poly_data.get('car', [])
        lane_moto = poly_data.get('moto', [])
        wrongway_down_zone = poly_data.get('wrongway_down', [])
        wrongway_up_zone = poly_data.get('wrongway_up', [])
        
        LANE_CAR_BUS_TRUCK = scale_poly(lane_car)
        LANE_MOTO = scale_poly(lane_moto)
        WW_DOWN_ZONE = scale_poly(wrongway_down_zone)
        WW_UP_ZONE = scale_poly(wrongway_up_zone)

        track_history = {}
        violator_info = {}  # {obj_id_int: (event_name, label_suffix)}
        violation_counts = session_data["stats"]
        captures_list = session_data["captures"]

        while cap.isOpened() and session_data["is_running"]:
            if session_data.get("is_paused", False):
                import time
                time.sleep(0.5)
                # Reload polygons if updated
                poly_data = session_data["polygons"]
                surveillance_mode = poly_data.get('mode', 0)
                LANE_CAR_BUS_TRUCK = scale_poly(poly_data.get('car', []))
                LANE_MOTO = scale_poly(poly_data.get('moto', []))
                WW_DOWN_ZONE = scale_poly(poly_data.get('wrongway_down', []))
                WW_UP_ZONE = scale_poly(poly_data.get('wrongway_up', []))
                continue

            ret, frame = cap.read()
            if not ret:
                break
                
            results = self.model.track(
                source=frame, conf=self.conf_thresh, iou=self.iou_thresh, imgsz=self.img_size,
                max_det=self.max_detect, tracker="bytetrack.yaml", persist=True, verbose=False
            )
            
            annotated_frame = frame.copy()

            # Xử lý Logic Box
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                clss = results[0].boxes.cls.cpu().numpy()
                ids = results[0].boxes.id.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()

                for box, cls, obj_id, conf in zip(boxes, clss, ids, confs):
                    x1, y1, x2, y2 = map(int, box)
                    class_id = int(cls)
                    name = self.model.names[class_id].lower()
                    obj_id_int = int(obj_id)
                    
                    bottom_center = (int((x1 + x2) / 2), int(y2))
                    is_violation = False
                    event_name = ""
                    label_text = f"ID:{obj_id_int} {name} {conf:.2f}"
                    base_label_suffix = ""
                    if obj_id_int in violator_info:
                        is_violation = True
                        event_name, base_label_suffix = violator_info[obj_id_int]
                        label_text += " " + base_label_suffix
                    else:
                        # LOGIC SAI LÀN
                        if surveillance_mode in [0, 2]:
                            if LANE_CAR_BUS_TRUCK is not None and LANE_MOTO is not None:
                                in_car_lane = cv2.pointPolygonTest(LANE_CAR_BUS_TRUCK, bottom_center, False) >= 0
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
                                        
                        # LOGIC NGƯỢC CHIỀU
                        if surveillance_mode in [1, 2] and not is_violation:
                            if WW_DOWN_ZONE is not None and cv2.pointPolygonTest(WW_DOWN_ZONE, bottom_center, False) >= 0:
                                if obj_id_int in track_history and len(track_history[obj_id_int]) >= 5:
                                    prev_y = int(track_history[obj_id_int][0])
                                    # Trong Down Zone (làn đi xuống), nếu đi LÊN (prev_y - y2 > 5) là NGƯỢC CHIỀU
                                    if prev_y - int(y2) > 5: 
                                        is_violation = True
                                        event_name = "Nguoc Chieu"
                                        base_label_suffix = "[NGUOC CHIEU]"
                                        label_text += " " + base_label_suffix
                                        
                            elif WW_UP_ZONE is not None and cv2.pointPolygonTest(WW_UP_ZONE, bottom_center, False) >= 0:
                                if obj_id_int in track_history and len(track_history[obj_id_int]) >= 5:
                                    prev_y = int(track_history[obj_id_int][0])
                                    # Trong Up Zone (làn đi lên), nếu đi XUỐNG (y2 - prev_y > 5) là NGƯỢC CHIỀU
                                    if int(y2) - prev_y > 5:
                                        is_violation = True
                                        event_name = "Nguoc Chieu"
                                        base_label_suffix = "[NGUOC CHIEU]"
                                        label_text += " " + base_label_suffix

                    if obj_id_int not in track_history:
                        track_history[obj_id_int] = []
                    track_history[obj_id_int].append(int(y2))
                    if len(track_history[obj_id_int]) > 15:
                        track_history[obj_id_int].pop(0)

                    # THEO YÊU CẦU: Chỉ vẽ box và tracker cho xe VI PHẠM
                    if is_violation:
                        bbox_color = (0, 0, 255) # Đỏ vi phạm
                        
                        if obj_id_int not in violator_info:
                            violator_info[obj_id_int] = (event_name, base_label_suffix)
                            if name in violation_counts:
                                violation_counts[name] += 1
                                
                            capture_name = f"cap_{timestamp}_{obj_id_int}_{datetime.now().strftime('%H%M%S')}.jpg"
                            capture_url = f"http://localhost:8000/static/captures/{capture_name}"
                            
                            # Đẩy data vào queue để background worker ghi vào DB
                            self.db_queue.put({
                                "session_id": session_id,
                                "vehicle_id": obj_id_int,
                                "vehicle_type": name,
                                "event_type": event_name,
                                "capture_url": capture_url
                            })
                            
                            try:
                                capture_path = os.path.join(self.capture_dir, capture_name)
                                h_frm, w_frm = frame.shape[:2]
                                cx1, cy1 = max(0, x1 - 10), max(0, y1 - 10)
                                cx2, cy2 = min(w_frm, x2 + 10), min(h_frm, y2 + 10)
                                car_img = frame[cy1:cy2, cx1:cx2]
                                cv2.imwrite(capture_path, car_img)
                                captures_list.insert(0, {
                                    "id": obj_id_int, 
                                    "type": name,
                                    "event": event_name, 
                                    "time": datetime.now().strftime('%H:%M:%S'),
                                    "image_url": capture_url
                                })
                            except Exception as e:
                                pass
                                
                        # Chỉ khi is_violation = True ta mới vẽ Border (Bounding Box đỏ)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), bbox_color, self.line_width)
                        cv2.circle(annotated_frame, bottom_center, radius=5, color=(0, 0, 255), thickness=-1)
                        (w, h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + w, y1), bbox_color, -1)
                        cv2.putText(annotated_frame, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Ghi Frame đã vẽ vào MJPEG stream queue
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if ret:
                q.put(buffer.tobytes())

        # Giải phóng bộ nhớ
        cap.release()
        session_data["is_running"] = False
        session_data["finished"] = True

    def generate_frames(self, session_id: str, session_data: dict, timestamp: str):
        session_data["is_running"] = True
        q = queue.Queue(maxsize=30)
        
        worker = threading.Thread(target=self.generate_frames_worker, args=(session_id, session_data, timestamp, q))
        worker.daemon = True
        worker.start()

        while session_data["is_running"] or not q.empty():
            try:
                frame_bytes = q.get(timeout=1.0)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except queue.Empty:
                if session_data.get("finished", False):
                    break
        
        worker.join(timeout=1.0)
