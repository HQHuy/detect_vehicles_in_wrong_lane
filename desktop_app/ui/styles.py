# Bộ giao diện QSS Brutalist & Glassmorphism cho ứng dụng Desktop PySide6
# Thiết kế đồng bộ hoàn toàn với phiên bản Web (Dark Mode, chữ số khổng lồ, nút bấm tối giản)

DARK_STYLE = """
QMainWindow {
    background-color: #09090b; /* Zinc 950 */
}

QWidget {
    color: #f4f4f5; /* Zinc 100 */
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}

/* Các Panel chính */
QFrame#leftPanel {
    background-color: transparent;
    border: none;
}

QFrame#rightPanel {
    background-color: transparent;
    border: none;
    border-left: 1px solid #18181b; /* Zinc 900 border phân tách */
}

/* Tiêu đề ứng dụng và các phân vùng */
QLabel#appTitle {
    font-size: 20px;
    font-weight: 500;
    color: #f4f4f5;
    letter-spacing: -0.05em;
}

QLabel#appTitleDot {
    font-size: 20px;
    font-weight: bold;
    color: #52525b; /* Zinc 600 */
}

QLabel#sectionTitle {
    font-size: 11px;
    font-weight: bold;
    color: #71717a; /* Zinc 500 */
    text-transform: uppercase;
    letter-spacing: 0.15em;
}

/* Thống kê Brutalist (Dòng số liệu phân tách bằng viền mỏng) */
QFrame#statItem {
    background-color: transparent;
    border: none;
    border-bottom: 1px solid #18181b;
    padding-bottom: 24px;
    margin-bottom: 12px;
}

QLabel#statLabel {
    font-size: 11px;
    font-weight: 600;
    color: #71717a; /* Zinc 500 */
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

QLabel#statLabelSuffix {
    font-size: 10px;
    font-weight: normal;
    color: #52525b; /* Zinc 600 */
}

QLabel#statNumber {
    font-size: 72px; /* Số khổng lồ */
    font-weight: 500;
    font-family: monospace, Courier, "Courier New";
    color: #f4f4f5; /* Zinc 100 */
    margin: 0px;
    padding: 0px;
}

/* Nút Halt Analysis tối giản ở cột phải */
QPushButton#haltBtn {
    background-color: transparent;
    border: 1px solid #27272a; /* Zinc 800 */
    border-radius: 16px;
    color: #a1a1aa; /* Zinc 400 */
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
    text-align: left;
}

QPushButton#haltBtn:hover {
    color: #f87171; /* Rose 400 */
    border-color: rgba(248, 113, 113, 0.4);
    background-color: rgba(248, 113, 113, 0.05);
}

QPushButton#haltBtn:pressed {
    background-color: rgba(248, 113, 113, 0.1);
}

QPushButton#haltBtn:disabled {
    color: #3f3f46;
    border-color: #18181b;
}

/* Thanh điều khiển nổi Glassmorphism ở đáy video */
QFrame#floatingToolbar {
    background-color: rgba(9, 9, 11, 0.85); /* Zinc 950 với opacity */
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
}

/* Nút bấm trong thanh điều khiển mờ */
QPushButton#toolbarBtn {
    background-color: transparent;
    border: none;
    border-radius: 18px;
    color: #d4d4d8; /* Zinc 300 */
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton#toolbarBtn:hover {
    color: #ffffff;
    background-color: rgba(255, 255, 255, 0.08);
}

QPushButton#toolbarBtn:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}

QPushButton#toolbarBtn:checked {
    background-color: rgba(255, 255, 255, 0.1);
    color: #ffffff;
}

QPushButton#toolbarBtn:disabled {
    color: #52525b;
}

/* Nút chạy (Play/Start) nổi bật */
QPushButton#toolbarPrimaryBtn {
    background-color: #10b981; /* Emerald 500 */
    border: none;
    border-radius: 18px;
    color: #ffffff;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton#toolbarPrimaryBtn:hover {
    background-color: #34d399; /* Emerald 400 */
}

QPushButton#toolbarPrimaryBtn:pressed {
    background-color: #059669;
}

QPushButton#toolbarPrimaryBtn:disabled {
    background-color: rgba(16, 185, 129, 0.2);
    color: rgba(255, 255, 255, 0.4);
}

/* Nút phụ trong Toolbar (ví dụ nút vẽ hoàn thành) */
QPushButton#toolbarSecondaryBtn {
    background-color: #27272a; /* Zinc 800 */
    border: 1px solid #3f3f46;
    border-radius: 18px;
    color: #ffffff;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton#toolbarSecondaryBtn:hover {
    background-color: #3f3f46;
}

/* Nút xóa đa giác đang vẽ */
QPushButton#toolbarDangerBtn {
    background-color: rgba(239, 68, 68, 0.15); /* Red 500 với opacity */
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 18px;
    color: #f87171; /* Red 400 */
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton#toolbarDangerBtn:hover {
    background-color: rgba(239, 68, 68, 0.25);
}

/* Thanh phân cách dọc trong Toolbar */
QFrame#toolbarSeparator {
    background-color: #27272a; /* Zinc 800 */
    max-width: 1px;
    min-width: 1px;
}

/* Dropdown chọn làn đường vẽ */
QComboBox#toolbarCombo {
    background-color: #18181b; /* Zinc 900 */
    border: 1px solid #27272a;
    border-radius: 14px;
    padding: 6px 12px;
    color: #d4d4d8;
    font-weight: 500;
}

QComboBox#toolbarCombo:hover {
    border-color: #3f3f46;
}

QComboBox#toolbarCombo QAbstractItemView {
    background-color: #18181b;
    border: 1px solid #27272a;
    selection-background-color: #27272a;
    selection-color: #ffffff;
}

/* Đầu mối xuất file CSV ở Header */
QPushButton#exportCsvBtn {
    background-color: transparent;
    border: none;
    color: #a1a1aa; /* Zinc 400 */
    font-weight: 500;
}

QPushButton#exportCsvBtn:hover {
    color: #34d399; /* Emerald 400 */
}

QPushButton#exportCsvBtn:disabled {
    color: #3f3f46;
}

/* Đèn LED trạng thái góc trên bên trái video */
QFrame#statusTag {
    background-color: rgba(9, 9, 11, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
}

QLabel#statusTagText {
    font-size: 10px;
    font-weight: bold;
    color: #d4d4d8;
    letter-spacing: 0.1em;
    font-family: monospace;
}

/* Thanh điều hướng vẽ đa giác phụ góc trên bên phải */
QFrame#drawingPanel {
    background-color: rgba(9, 9, 11, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
}

QLabel#drawingPanelTitle {
    font-size: 10px;
    font-weight: bold;
    color: #71717a;
    letter-spacing: 0.1em;
    font-family: monospace;
}

/* Các nút bấm chọn làn vẽ */
QPushButton#drawSelectBtn {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #71717a;
    font-family: monospace;
    font-size: 11px;
    padding: 6px 12px;
    text-align: left;
}

QPushButton#drawSelectBtn:hover {
    color: #d4d4d8;
}

QPushButton#drawSelectBtn:checked {
    background-color: #18181b;
    border-color: #27272a;
    color: #ffffff;
}

/* Cuộn ngang captures log */
QScrollArea#capturesScrollArea {
    border: none;
    background-color: transparent;
}

/* Thẻ ảnh vi phạm cận cảnh */
QFrame#violationCard {
    background-color: #09090b; /* Zinc 950 */
    border: 1px solid #18181b; /* Zinc 900 border */
    border-radius: 16px;
}

QFrame#violationCard:hover {
    border-color: #ef4444; /* Viền đỏ khi hover */
}

/* Thanh cuộn ngang */
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 4px;
}

QScrollBar::handle:horizontal {
    background: #18181b;
    border-radius: 2px;
    min-width: 40px;
}

QScrollBar::handle:horizontal:hover {
    background: #27272a;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QStatusBar {
    background-color: #09090b;
    color: #3f3f46;
    font-size: 10px;
    font-family: monospace;
    border-top: 1px solid #18181b;
}
"""
