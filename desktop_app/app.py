import os
import sys
import csv
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFrame, QLabel, QPushButton, QFileDialog, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtCore import Qt, Slot, QTimer

# Thay đổi sys.path để chạy độc lập hoặc import đúng thư mục desktop_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desktop_app.core.config import DB_PATH, CAPTURES_DIR
from desktop_app.core.model_worker import ModelWorker
from desktop_app.widgets.video_widget import VideoWidget
from desktop_app.ui.styles import DARK_STYLE

class ViolationCard(QFrame):
    """Thẻ ảnh vi phạm cận cảnh có hiệu ứng Hover đổi màu và Grayscale như Web"""
    def __init__(self, violation_data, parent=None):
        super().__init__(parent)
        self.setObjectName("violationCard")
        self.setMouseTracking(True)
        self.violation_data = violation_data
        
        # Đọc ảnh gốc
        self.original_pixmap = QPixmap(violation_data["image_path"])
        
        # Tạo ảnh dạng grayscale (đen trắng)
        if not self.original_pixmap.isNull():
            image = self.original_pixmap.toImage().convertToFormat(QImage.Format_Grayscale8)
            # Chuyển về dạng RGB888 để hiển thị mượt mà trên Qt
            image_rgb = image.convertToFormat(QImage.Format_RGB888)
            self.grayscale_pixmap = QPixmap.fromImage(image_rgb)
        else:
            self.grayscale_pixmap = QPixmap()

        self.init_ui()
        self.show_grayscale()

    def init_ui(self):
        # Thiết lập kích thước cố định aspect ratio tương tự web
        self.setFixedSize(180, 110)
        
        # Bố cục chính
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Container bọc ảnh để bo tròn và chèn đè lớp overlay gradient
        self.img_container = QWidget(self)
        self.img_container.setFixedSize(180, 110)
        self.img_container.setStyleSheet("background-color: #18181b; border-radius: 14px;")
        
        # Nhãn hiển thị hình ảnh
        self.img_label = QLabel(self.img_container)
        self.img_label.setGeometry(0, 0, 180, 110)
        self.img_label.setScaledContents(True)
        self.img_label.setStyleSheet("border-radius: 14px;")
        
        # Lớp overlay gradient phủ dưới đáy ảnh
        self.overlay = QFrame(self.img_container)
        self.overlay.setGeometry(0, 65, 180, 45)
        self.overlay.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0, 0, 0, 0), stop:1 rgba(9, 9, 11, 240));
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border: none;
            }
        """)
        
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(10, 4, 10, 4)
        overlay_layout.setSpacing(0)
        
        # Nhãn thời gian màu đỏ hồng
        self.time_label = QLabel(self.violation_data["time"], self.overlay)
        self.time_label.setStyleSheet("color: #f43f5e; font-size: 9px; font-family: monospace; font-weight: bold; background: transparent; border: none;")
        
        # Nhãn thông tin sự kiện
        event_str = f"{self.violation_data['event']} - {self.violation_data['type']}"
        self.event_label = QLabel(event_str.upper(), self.overlay)
        self.event_label.setStyleSheet("color: #f4f4f5; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        
        overlay_layout.addWidget(self.time_label)
        overlay_layout.addWidget(self.event_label)
        
        layout.addWidget(self.img_container)

    def show_grayscale(self):
        """Hiển thị ảnh đen trắng khi không hover"""
        if not self.grayscale_pixmap.isNull():
            self.img_label.setPixmap(self.grayscale_pixmap)
        else:
            self.img_label.setText("[Không có ảnh]")
            self.img_label.setStyleSheet("color: #52525b; font-size: 10px; border-radius: 14px;")

    def show_color(self):
        """Hiển thị ảnh màu gốc khi hover chuột vào"""
        if not self.original_pixmap.isNull():
            self.img_label.setPixmap(self.original_pixmap)
        else:
            self.img_label.setText("[Không có ảnh]")

    def enterEvent(self, event):
        self.show_color()
        # Thay đổi stylesheet viền ngoài của card sang viền đỏ
        self.setStyleSheet("QFrame#violationCard { border: 2px solid #ef4444; }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.show_grayscale()
        # Trả lại viền xám mặc định
        self.setStyleSheet("QFrame#violationCard { border: 1px solid #18181b; }")
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("TrafficAI - Giám sát giao thông thông minh")
        self.resize(1320, 800)
        self.setStyleSheet(DARK_STYLE)
        
        # Đường dẫn video đang chọn và luồng xử lý
        self.selected_video_path = None
        self.worker = None
        
        # Quản lý số đếm vi phạm cục bộ
        self.events_count = 0
        
        # Timer để nhấp nháy LED trạng thái ở Header
        self.header_led_timer = QTimer(self)
        self.header_led_timer.timeout.connect(self.blink_header_led)
        self.header_led_on = False
        
        self.init_ui()
        self.statusBar().showMessage("Sẵn sàng. Hãy nhấp 'Chọn nguồn' ở thanh điều khiển video để bắt đầu.")

    def init_ui(self):
        # Widget trung tâm
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Bố cục đứng ngoài cùng (Chứa Header ở trên, Main Grid ở dưới)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(24)
        
        # ==========================================
        # 1. HEADER (Top Navigation)
        # ==========================================
        header_frame = QFrame(central_widget)
        header_frame.setStyleSheet("background-color: transparent; border: none;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Cụm Logo & Đèn LED bên trái
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(10)
        
        self.header_led = QFrame(header_frame)
        self.header_led.setFixedSize(10, 10)
        self.header_led.setStyleSheet("background-color: #27272a; border-radius: 5px;") # LED xám
        logo_layout.addWidget(self.header_led)
        
        lbl_logo_main = QLabel("TrafficAI", header_frame)
        lbl_logo_main.setObjectName("appTitle")
        logo_layout.addWidget(lbl_logo_main)
        
        lbl_logo_dot = QLabel("_", header_frame)
        lbl_logo_dot.setObjectName("appTitleDot")
        logo_layout.addWidget(lbl_logo_dot)
        
        header_layout.addLayout(logo_layout)
        header_layout.addStretch()
        
        # Nút xuất CSV bên phải
        self.btn_export_csv = QPushButton("Xuất file CSV (Đang đợi)", header_frame)
        self.btn_export_csv.setObjectName("exportCsvBtn")
        self.btn_export_csv.setEnabled(False)
        self.btn_export_csv.clicked.connect(self.export_csv)
        header_layout.addWidget(self.btn_export_csv)
        
        root_layout.addWidget(header_frame)
        
        # ==========================================
        # 2. MAIN GRID LAYOUT (Cột Trái 70% & Cột Phải 30%)
        # ==========================================
        main_grid_layout = QHBoxLayout()
        main_grid_layout.setSpacing(32)
        
        # ------------------------------------------
        # CỘT TRÁI (Video và Lịch sử ảnh vi phạm)
        # ------------------------------------------
        left_panel = QFrame(central_widget)
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # Khung Video chính
        self.video_widget = VideoWidget(left_panel)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setMinimumHeight(450)
        
        # Kết nối sự kiện đa giác đổi
        self.video_widget.polygons_changed.connect(self.on_polygons_changed)
        
        # Kết nối sự kiện nút bấm trong VideoWidget (Floating Control Bar)
        self.video_widget.btn_select_video.clicked.connect(self.select_video)
        self.video_widget.btn_setup_lanes.clicked.connect(self.toggle_setup_mode)
        self.video_widget.btn_start.clicked.connect(self.start_analysis)
        self.video_widget.btn_pause.clicked.connect(self.pause_analysis)
        self.video_widget.btn_stop.clicked.connect(self.stop_analysis)
        self.video_widget.btn_clear_poly.clicked.connect(self.video_widget.clear_active_polygon)
        
        left_layout.addWidget(self.video_widget)
        
        # Khung lịch sử ảnh chụp vi phạm cận cảnh
        log_header_layout = QHBoxLayout()
        lbl_log_title = QLabel("ẢNH CHỤP VI PHẠM GẦN ĐÂY", left_panel)
        lbl_log_title.setObjectName("sectionTitle")
        log_header_layout.addWidget(lbl_log_title)
        
        log_header_layout.addStretch()
        
        self.lbl_events_count = QLabel("0 sự kiện", left_panel)
        self.lbl_events_count.setStyleSheet("color: #52525b; font-family: monospace; font-size: 11px;")
        log_header_layout.addWidget(self.lbl_events_count)
        
        left_layout.addLayout(log_header_layout)
        
        # Scroll area chứa ảnh trượt ngang
        self.scroll_area = QScrollArea(left_panel)
        self.scroll_area.setObjectName("capturesScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(128)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.scroll_horizontal_layout = QHBoxLayout(self.scroll_content)
        self.scroll_horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_horizontal_layout.setSpacing(16)
        self.scroll_horizontal_layout.setAlignment(Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.scroll_content)
        left_layout.addWidget(self.scroll_area)
        
        main_grid_layout.addWidget(left_panel, stretch=7)
        
        # ------------------------------------------
        # CỘT PHẢI (Thống kê Brutalist và Nút Halt)
        # ------------------------------------------
        right_panel = QFrame(central_widget)
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 3 khối thống kê Brutalist
        self.stat_widgets = {}
        self.create_brutalist_stat(right_layout, "CARS", "(LÀN 1)", "car")
        self.create_brutalist_stat(right_layout, "MOTORCYCLES", "(LÀN 2)", "moto")
        self.create_brutalist_stat(right_layout, "BUS & TRUCKS", "", "heavy")
        
        right_layout.addSpacing(32)
        
        # Nút Halt Analysis tối giản ở đáy
        self.btn_halt = QPushButton("Tạm dừng phân tích", right_panel)
        self.btn_halt.setObjectName("haltBtn")
        self.btn_halt.setEnabled(False)
        self.btn_halt.clicked.connect(self.pause_analysis)
        right_layout.addWidget(self.btn_halt)
        
        right_layout.addStretch()
        
        # Trạng thái kết nối DB
        self.db_status_label = QLabel(f"Database: {os.path.basename(DB_PATH)} (Đã kết nối)", right_panel)
        self.db_status_label.setStyleSheet("color: #10b981; font-family: monospace; font-size: 11px;")
        right_layout.addWidget(self.db_status_label)
        
        main_grid_layout.addWidget(right_panel, stretch=3)
        
        root_layout.addLayout(main_grid_layout)

    def create_brutalist_stat(self, layout, label_title, label_suffix, key):
        """Tạo dòng thống kê Brutalist tối giản số khổng lồ"""
        item_frame = QFrame(self)
        item_frame.setObjectName("statItem")
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(0, 0, 0, 16)
        item_layout.setSpacing(2)
        
        lbl_title_layout = QHBoxLayout()
        lbl_title = QLabel(label_title, item_frame)
        lbl_title.setObjectName("statLabel")
        lbl_title_layout.addWidget(lbl_title)
        
        if label_suffix:
            lbl_suff = QLabel(label_suffix, item_frame)
            lbl_suff.setObjectName("statLabelSuffix")
            lbl_title_layout.addWidget(lbl_suff)
            
        lbl_title_layout.addStretch()
        item_layout.addLayout(lbl_title_layout)
        
        lbl_num = QLabel("0", item_frame)
        lbl_num.setObjectName("statNumber")
        item_layout.addWidget(lbl_num)
        
        layout.addWidget(item_frame)
        self.stat_widgets[key] = lbl_num

    def blink_header_led(self):
        """Nhấp nháy LED tròn ở Header khi phân tích đang hoạt động"""
        if self.worker and self.worker.isRunning() and not self.worker.is_paused:
            self.header_led_on = not self.header_led_on
            if self.header_led_on:
                self.header_led.setStyleSheet("background-color: #10b981; border-radius: 5px;")
            else:
                self.header_led.setStyleSheet("background-color: rgba(16, 185, 129, 0.2); border-radius: 5px;")
        else:
            self.header_led_timer.stop()
            self.header_led.setStyleSheet("background-color: #27272a; border-radius: 5px;")

    # ==========================================
    # CÁC HÀM XỬ LÝ SỰ KIỆN (CALLBACKS)
    # ==========================================
    
    @Slot()
    def select_video(self):
        """Mở hộp thoại chọn video và thiết lập khung hình đầu tiên"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Tệp Video Giám Sát", "", "Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        if file_path:
            self.selected_video_path = file_path
            self.statusBar().showMessage(f"Đã nạp video: {os.path.basename(file_path)}")
            
            # Đọc khung hình đầu tiên để người dùng vẽ đa giác
            self.video_widget.placeholder_text = "Đang tải video..."
            self.video_widget.load_static_frame(file_path)
            
            # Kích hoạt nút vẽ đa giác và bắt đầu trên thanh điều khiển nổi
            self.video_widget.btn_setup_lanes.setEnabled(True)
            self.video_widget.btn_start.setEnabled(True)
            
            # Xóa sạch nhật ký ảnh vi phạm cũ
            self.clear_violation_logs_ui()
            
            # Reset bảng thống kê số liệu
            self.on_stats_updated({'car': 0, 'moto': 0, 'bus': 0, 'truck': 0, 'motorcycle': 0})
            self.btn_export_csv.setEnabled(False)
            self.btn_export_csv.setText("Xuất file CSV (Đang đợi)")

    @Slot(bool)
    def toggle_setup_mode(self, checked):
        """Kích hoạt hoặc tắt chế độ vẽ thiết lập làn đường"""
        self.video_widget.set_drawing_mode(checked)
        
        if checked:
            self.video_widget.btn_setup_lanes.setText("Hoàn thành vẽ")
            self.video_widget.btn_start.setEnabled(False)
        else:
            self.video_widget.btn_setup_lanes.setText("Thiết lập làn")
            self.video_widget.btn_start.setEnabled(True)

    @Slot(dict)
    def on_polygons_changed(self, polygons):
        """Đồng bộ đa giác mới sang worker nếu đang phân tích"""
        if self.worker and self.worker.isRunning():
            self.worker.update_polygons(polygons)

    @Slot()
    def start_analysis(self):
        """Bắt đầu chạy luồng phụ YOLO xử lý video"""
        if not self.selected_video_path:
            return
            
        polygons = self.video_widget.polygons
        
        # Khởi tạo ModelWorker
        self.worker = ModelWorker(self.selected_video_path, polygons, self)
        
        # Kết nối các tín hiệu truyền nhận từ worker
        self.worker.frame_processed.connect(self.video_widget.update_frame)
        self.worker.violation_detected.connect(self.on_violation_detected)
        self.worker.stats_updated.connect(self.on_stats_updated)
        self.worker.status_message.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.on_worker_finished)
        
        # Điều chỉnh hiển thị của các nút trong thanh điều khiển nổi
        self.video_widget.btn_start.hide()
        self.video_widget.btn_pause.show()
        self.video_widget.btn_pause.setEnabled(True)
        self.video_widget.btn_stop.show()
        self.video_widget.btn_stop.setEnabled(True)
        self.video_widget.btn_select_video.setEnabled(False)
        self.video_widget.btn_setup_lanes.setEnabled(False)
        self.video_widget.floating_toolbar.adjustSize()
        
        # Kích hoạt nút tạm dừng phân tích ở cột phải (Halt)
        self.btn_halt.setEnabled(True)
        self.btn_halt.setText("Tạm dừng phân tích")
        
        # Kích hoạt nhấp nháy LED trạng thái trên Header
        self.header_led_timer.start(500)
        self.video_widget.update_status_tag("live")
        
        # Chạy luồng
        self.worker.start()

    @Slot()
    def pause_analysis(self):
        """Tạm dừng hoặc tiếp tục chạy video phân tích"""
        if not self.worker:
            return
            
        if self.worker.is_paused:
            self.worker.resume()
            self.video_widget.btn_pause.setText("Tạm dừng")
            self.btn_halt.setText("Tạm dừng phân tích")
            self.statusBar().showMessage("Đang tiếp tục phân tích...")
            self.video_widget.update_status_tag("live")
            # Kích hoạt nhấp nháy LED
            self.header_led_timer.start(500)
        else:
            self.worker.pause()
            self.video_widget.btn_pause.setText("Tiếp tục")
            self.btn_halt.setText("Phân tích đang dừng")
            self.statusBar().showMessage("Đã tạm dừng phân tích. Bạn có thể thay đổi vẽ làn đường nếu cần.")
            self.video_widget.update_status_tag("halted")
            
            # Cho phép chỉnh sửa đa giác trong lúc tạm dừng
            self.video_widget.btn_setup_lanes.setEnabled(True)
            # Tắt nhấp nháy LED, đổi thành xám tối
            self.header_led_timer.stop()
            self.header_led.setStyleSheet("background-color: #27272a; border-radius: 5px;")

    @Slot()
    def stop_analysis(self):
        """Dừng phân tích video"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        self.on_worker_finished()

    @Slot()
    def on_worker_finished(self):
        """Xử lý sự kiện khi kết thúc luồng hoặc dừng phân tích"""
        # Cập nhật trạng thái các nút
        self.video_widget.btn_start.show()
        self.video_widget.btn_start.setEnabled(True)
        
        self.video_widget.btn_pause.hide()
        self.video_widget.btn_stop.hide()
        
        self.video_widget.btn_select_video.setEnabled(True)
        self.video_widget.btn_setup_lanes.setEnabled(True)
        self.video_widget.floating_toolbar.adjustSize()
        
        self.btn_halt.setEnabled(False)
        self.btn_halt.setText("Tạm dừng phân tích")
        
        # Tắt nháy LED trạng thái
        self.header_led_timer.stop()
        self.header_led.setStyleSheet("background-color: #27272a; border-radius: 5px;")
        self.video_widget.update_status_tag("ready")
        
        self.statusBar().showMessage("Đã kết thúc giám sát video.")
        
        # Cho phép xuất báo cáo CSV khi đã chạy xong
        if self.events_count > 0:
            self.btn_export_csv.setEnabled(True)
            self.btn_export_csv.setText("Tải file CSV")

    @Slot(dict)
    def on_violation_detected(self, violation_data):
        """Thêm một ViolationCard mới vào danh sách trượt ngang và tự động cuộn"""
        card = ViolationCard(violation_data, self.scroll_content)
        
        # Thêm thẻ vi phạm mới vào cuối layout
        self.scroll_horizontal_layout.addWidget(card)
        
        # Cập nhật số đếm sự kiện
        self.events_count += 1
        self.lbl_events_count.setText(f"{self.events_count} sự kiện")
        
        # Tự động cuộn sang bên phải cùng để xem ảnh mới nhất (giống hệt web)
        QTimer.singleShot(100, lambda: self.scroll_area.horizontalScrollBar().setValue(
            self.scroll_area.horizontalScrollBar().maximum()
        ))

    @Slot(dict)
    def on_stats_updated(self, stats):
        """Cập nhật các số liệu Brutalist khổng lồ ở cột phải"""
        moto_count = stats.get('moto', 0) + stats.get('motorcycle', 0)
        car_count = stats.get('car', 0)
        heavy_count = stats.get('bus', 0) + stats.get('truck', 0)
        
        self.stat_widgets['car'].setText(f"{car_count:,}")
        self.stat_widgets['moto'].setText(f"{moto_count:,}")
        self.stat_widgets['heavy'].setText(f"{heavy_count:,}")

    def export_csv(self):
        """Xuất file báo cáo CSV chứa danh sách lỗi vi phạm của phiên làm việc hiện tại"""
        if not self.worker:
            self.statusBar().showMessage("Chưa có phiên làm việc nào hoạt động!")
            return
            
        session_id = self.worker.session_id
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, vehicle_id, vehicle_type, event_type, capture_url FROM violation_logs WHERE session_id = ? ORDER BY id DESC", 
                (session_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                self.statusBar().showMessage("Không có dữ liệu vi phạm của phiên hiện tại để xuất!")
                return
                
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Lưu báo cáo vi phạm CSV", f"bao_cao_vi_pham_{session_id}.csv", "CSV Files (*.csv)"
            )
            if file_path:
                with open(file_path, mode='w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["STT", "Thời gian", "ID Xe", "Loại xe", "Hành vi vi phạm", "URL Ảnh vi phạm"])
                    for idx, r in enumerate(rows, 1):
                        writer.writerow([idx, r[1], r[2], r[3], r[4], r[5]])
                self.statusBar().showMessage(f"Đã xuất báo cáo CSV thành công tại: {os.path.basename(file_path)}")
        except Exception as e:
            self.statusBar().showMessage(f"Lỗi xuất file CSV: {e}")

    def clear_violation_logs_ui(self):
        """Xóa sạch toàn bộ ViolationCard trên giao diện"""
        while self.scroll_horizontal_layout.count():
            child = self.scroll_horizontal_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.events_count = 0
        self.lbl_events_count.setText("0 sự kiện")

    def closeEvent(self, event):
        """Dọn dẹp tiến trình phụ khi đóng ứng dụng"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
