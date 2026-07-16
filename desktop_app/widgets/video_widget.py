import os
import cv2
from PySide6.QtWidgets import QWidget, QFrame, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QImage, QPainterPath
from PySide6.QtCore import Qt, QPointF, Signal, QTimer

class VideoWidget(QWidget):
    # Tín hiệu báo khi tọa độ đa giác thay đổi
    polygons_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Danh sách tọa độ các đa giác (theo tỷ lệ phần trăm 0 - 100)
        self.polygons = {
            'car': [],
            'moto': [],
            'wrongway_down': [],
            'wrongway_up': []
        }
        
        # Trạng thái thiết lập đa giác
        self.is_drawing_mode = False
        self.active_drawing_key = 'car'  # Mặc định vẽ làn ô tô
        
        # Biến giữ ảnh hiện tại để hiển thị
        self.current_pixmap = None
        self.placeholder_text = "Vui lòng chọn nguồn video để bắt đầu"
        self.last_frame = None # Giữ frame OpenCV gốc khi tải video lên
        
        # Cấu hình màu sắc hiển thị cho các đa giác
        self.colors = {
            'car': {'stroke': QColor(56, 189, 248, 204), 'fill': QColor(56, 189, 248, 20), 'name': 'LÀN Ô TÔ'},
            'moto': {'stroke': QColor(16, 185, 129, 204), 'fill': QColor(16, 185, 129, 20), 'name': 'LÀN XE MÁY'},
            'wrongway_down': {'stroke': QColor(239, 68, 68, 204), 'fill': QColor(239, 68, 68, 30), 'name': 'WW XUỐNG'},
            'wrongway_up': {'stroke': QColor(245, 158, 11, 204), 'fill': QColor(245, 158, 11, 30), 'name': 'WW LÊN'}
        }
        
        # Nhấp nháy LED trạng thái khi LIVE
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink_status_led)
        self.led_on = True
        
        self.setMouseTracking(True)
        self.init_sub_widgets()

    def init_sub_widgets(self):
        # 1. Đèn LED trạng thái góc trên bên trái
        self.status_tag = QFrame(self)
        self.status_tag.setObjectName("statusTag")
        status_layout = QHBoxLayout(self.status_tag)
        status_layout.setContentsMargins(10, 6, 10, 6)
        status_layout.setSpacing(6)
        
        self.status_led = QFrame(self.status_tag)
        self.status_led.setFixedSize(8, 8)
        self.status_led.setStyleSheet("background-color: #71717a; border-radius: 4px;") # Xám mặc định
        
        self.status_text = QLabel("SẴN SÀNG", self.status_tag)
        self.status_text.setObjectName("statusTagText")
        
        status_layout.addWidget(self.status_led)
        status_layout.addWidget(self.status_text)
        self.status_tag.adjustSize()

        # 2. Panel chọn làn vẽ góc trên bên phải
        self.drawing_panel = QFrame(self)
        self.drawing_panel.setObjectName("drawingPanel")
        self.drawing_panel.hide()
        
        drawing_layout = QVBoxLayout(self.drawing_panel)
        drawing_layout.setContentsMargins(10, 10, 10, 10)
        drawing_layout.setSpacing(6)
        
        dp_title = QLabel("VẼ LÀN ĐƯỜNG", self.drawing_panel)
        dp_title.setObjectName("drawingPanelTitle")
        dp_title.setAlignment(Qt.AlignCenter)
        drawing_layout.addWidget(dp_title)
        
        self.draw_buttons = {}
        draw_types = [
            ('car', 'LÀN Ô TÔ'),
            ('moto', 'LÀN XE MÁY'),
            ('wrongway_down', 'WW XUỐNG'),
            ('wrongway_up', 'WW LÊN')
        ]
        for key, label in draw_types:
            btn = QPushButton(label, self.drawing_panel)
            btn.setObjectName("drawSelectBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self.set_active_drawing_key(k))
            drawing_layout.addWidget(btn)
            self.draw_buttons[key] = btn
        
        self.draw_buttons['car'].setChecked(True)
        
        self.btn_clear_poly = QPushButton("XÓA VẼ LẠI", self.drawing_panel)
        self.btn_clear_poly.setObjectName("toolbarDangerBtn")
        drawing_layout.addWidget(self.btn_clear_poly)
        
        self.drawing_panel.adjustSize()

        # 3. Thanh điều khiển nổi Glassmorphism ở đáy
        self.floating_toolbar = QFrame(self)
        self.floating_toolbar.setObjectName("floatingToolbar")
        self.floating_toolbar.hide()
        
        toolbar_layout = QHBoxLayout(self.floating_toolbar)
        toolbar_layout.setContentsMargins(6, 6, 6, 6)
        toolbar_layout.setSpacing(6)
        
        self.btn_select_video = QPushButton("Chọn nguồn", self.floating_toolbar)
        self.btn_select_video.setObjectName("toolbarBtn")
        toolbar_layout.addWidget(self.btn_select_video)
        
        self.sep1 = QFrame(self.floating_toolbar)
        self.sep1.setObjectName("toolbarSeparator")
        toolbar_layout.addWidget(self.sep1)
        
        self.btn_setup_lanes = QPushButton("Thiết lập làn", self.floating_toolbar)
        self.btn_setup_lanes.setObjectName("toolbarBtn")
        self.btn_setup_lanes.setCheckable(True)
        self.btn_setup_lanes.setEnabled(False)
        toolbar_layout.addWidget(self.btn_setup_lanes)
        
        self.sep2 = QFrame(self.floating_toolbar)
        self.sep2.setObjectName("toolbarSeparator")
        toolbar_layout.addWidget(self.sep2)
        
        self.btn_start = QPushButton("Bắt đầu phân tích", self.floating_toolbar)
        self.btn_start.setObjectName("toolbarPrimaryBtn")
        self.btn_start.setEnabled(False)
        toolbar_layout.addWidget(self.btn_start)
        
        self.btn_pause = QPushButton("Tạm dừng", self.floating_toolbar)
        self.btn_pause.setObjectName("toolbarSecondaryBtn")
        self.btn_pause.setEnabled(False)
        self.btn_pause.hide()
        toolbar_layout.addWidget(self.btn_pause)
        
        self.btn_stop = QPushButton("Dừng", self.floating_toolbar)
        self.btn_stop.setObjectName("toolbarDangerBtn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.hide()
        toolbar_layout.addWidget(self.btn_stop)
        
        self.floating_toolbar.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.status_tag.move(24, 24)
        self.drawing_panel.move(self.width() - self.drawing_panel.width() - 24, 24)
        
        tb_width = self.floating_toolbar.sizeHint().width()
        tb_height = self.floating_toolbar.sizeHint().height()
        self.floating_toolbar.resize(tb_width, tb_height)
        self.floating_toolbar.move((self.width() - tb_width) // 2, self.height() - tb_height - 24)

    def enterEvent(self, event):
        self.floating_toolbar.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_drawing_mode:
            self.floating_toolbar.hide()
        super().leaveEvent(event)

    def blink_status_led(self):
        self.led_on = not self.led_on
        if self.led_on:
            self.status_led.setStyleSheet("background-color: #10b981; border-radius: 4px;")
        else:
            self.status_led.setStyleSheet("background-color: rgba(16, 185, 129, 0.2); border-radius: 4px;")

    def update_status_tag(self, status_type):
        self.blink_timer.stop()
        if status_type == "live":
            self.status_led.setStyleSheet("background-color: #10b981; border-radius: 4px;")
            self.status_text.setText("LIVE STREAM")
            self.blink_timer.start(500)
        elif status_type == "setup":
            self.status_led.setStyleSheet("background-color: #f59e0b; border-radius: 4px;")
            self.status_text.setText("THIẾT LẬP")
        elif status_type == "halted":
            self.status_led.setStyleSheet("background-color: #ef4444; border-radius: 4px;")
            self.status_text.setText("ĐÃ TẠM DỪNG")
        elif status_type == "ready":
            self.status_led.setStyleSheet("background-color: #71717a; border-radius: 4px;")
            self.status_text.setText("SẴN SÀNG")
        self.status_tag.adjustSize()

    def set_drawing_mode(self, enabled):
        """Kích hoạt/tắt chế độ vẽ đa giác"""
        self.is_drawing_mode = enabled
        if enabled:
            self.drawing_panel.show()
            self.floating_toolbar.show()
            self.update_status_tag("setup")
        else:
            self.drawing_panel.hide()
            self.update_status_tag("ready" if not self.current_pixmap else "ready")
            # Nếu rời khỏi widget, ẩn toolbar
            if not self.underMouse():
                self.floating_toolbar.hide()
        self.update()

    def set_active_drawing_key(self, key):
        """Chọn loại vùng đang vẽ (car, moto, wrongway_down, wrongway_up)"""
        if key in self.polygons:
            self.active_drawing_key = key
            for k, btn in self.draw_buttons.items():
                btn.blockSignals(True)
                btn.setChecked(k == key)
                btn.blockSignals(False)
            self.update()

    def clear_active_polygon(self):
        """Xóa đa giác đang chọn để vẽ lại"""
        if self.active_drawing_key in self.polygons:
            self.polygons[self.active_drawing_key] = []
            self.polygons_changed.emit(self.polygons)
            self.update()

    def load_static_frame(self, video_path):
        """Đọc và hiển thị khung hình đầu tiên của video để người dùng vẽ đa giác"""
        if not os.path.exists(video_path):
            return
            
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                self.last_frame = frame.copy()
                self.update_frame_from_opencv(frame)
            cap.release()
        self.update_status_tag("ready")

    def update_frame(self, qimage):
        """Cập nhật khung hình từ luồng video xử lý của YOLO"""
        self.current_pixmap = QPixmap.fromImage(qimage)
        self.update()

    def update_frame_from_opencv(self, cv_frame):
        """Cập nhật khung hình từ mảng numpy OpenCV"""
        rgb_image = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self.update_frame(qimg)

    def mousePressEvent(self, event):
        """Bắt sự kiện click chuột để lấy tọa độ điểm của đa giác"""
        if not self.is_drawing_mode or event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        w_width = self.width()
        w_height = self.height()
        
        if w_width > 0 and w_height > 0:
            x_pct = (event.position().x() / w_width) * 100
            y_pct = (event.position().y() / w_height) * 100
            
            self.polygons[self.active_drawing_key].append([x_pct, y_pct])
            self.polygons_changed.emit(self.polygons)
            self.update()

    def paintEvent(self, event):
        """Vẽ khung hình video và đè các đường vẽ đa giác lên trên"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w_width = self.width()
        w_height = self.height()

        # Tạo góc bo tròn 32px (2rem) cho video area giống như web
        path = QPainterPath()
        path.addRoundedRect(0, 0, w_width, w_height, 32, 32)
        painter.setClipPath(path)

        # 1. Vẽ hình nền (Khung hình video hoặc Màu nền tối nếu chưa có video)
        if self.current_pixmap:
            scaled_pixmap = self.current_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (w_width - scaled_pixmap.width()) // 2
            y = (w_height - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            painter.fillRect(self.rect(), QColor(15, 15, 18)) # Zinc 900 đậm
            
            # Vẽ văn bản thông báo hướng dẫn ở trung tâm
            painter.setPen(QColor(113, 113, 122)) # Zinc 500
            font = painter.font()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self.placeholder_text)

        # 2. Vẽ các vùng đa giác
        for key, pts in self.polygons.items():
            if len(pts) == 0:
                continue

            color_cfg = self.colors[key]
            
            # Chuyển đổi tọa độ phần trăm sang pixel hiển thị
            pixel_pts = []
            for pt in pts:
                px = pt[0] * w_width / 100
                py = pt[1] * w_height / 100
                pixel_pts.append(QPointF(px, py))

            is_active = (self.is_drawing_mode and self.active_drawing_key == key)
            pen_width = 2 if is_active else 1
            
            # Nét vẽ đường viền
            pen = QPen(color_cfg['stroke'], pen_width)
            if self.is_drawing_mode:
                pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            
            # Tô màu nền nhẹ cho đa giác
            brush = QBrush(color_cfg['fill'])
            painter.setBrush(brush)
            
            # Vẽ đa giác
            if len(pixel_pts) >= 3:
                painter.drawPolygon(pixel_pts)
            elif len(pixel_pts) == 2:
                painter.drawLine(pixel_pts[0], pixel_pts[1])

            # Vẽ các chấm nhỏ tại mỗi điểm vẽ (chỉ trong chế độ thiết lập)
            if self.is_drawing_mode:
                painter.setBrush(QBrush(color_cfg['stroke']))
                painter.setPen(QPen(Qt.transparent))
                for pt in pixel_pts:
                    painter.drawEllipse(pt, 4, 4)

            # Vẽ tên nhãn đa giác tại vị trí điểm đầu tiên
            if len(pixel_pts) > 0:
                painter.setPen(QPen(color_cfg['stroke']))
                font = painter.font()
                font.setPointSize(8)
                font.setBold(True)
                font.setFamily("monospace")
                painter.setFont(font)
                label_y = pixel_pts[0].y() - 8 if pixel_pts[0].y() > 20 else pixel_pts[0].y() + 12
                painter.drawText(QPointF(pixel_pts[0].x(), label_y), color_cfg['name'])

        painter.end()
