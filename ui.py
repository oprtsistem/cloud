import sys
import json
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg

class HealthMonitorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("血氧與心率監測器")
        self.setGeometry(100, 100, 800, 600)

        # 數據存儲
        self.heart_rate_data = []
        self.spo2_data = []
        self.time_data = []
        self.scroll_window = 60  # 滾動窗口大小（秒）

        # UI 元素
        self.init_ui()

        # 計時器用於更新數據
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.monitoring = False

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 標題
        title_label = QLabel("血氧與心率監測")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 當前數值顯示
        current_frame = QFrame()
        current_layout = QVBoxLayout(current_frame)

        self.heart_rate_label = QLabel("當前心率 (BPM): --")
        self.heart_rate_label.setStyleSheet("font-size: 14px;")
        current_layout.addWidget(self.heart_rate_label)

        self.spo2_label = QLabel("當前血氧 (%): --")
        self.spo2_label.setStyleSheet("font-size: 14px;")
        current_layout.addWidget(self.spo2_label)

        layout.addWidget(current_frame)

        # 圖表區域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("心率與血氧趨勢")
        self.plot_widget.setLabel('left', '數值')
        self.plot_widget.setLabel('bottom', '時間 (秒)')

        # 創建兩個圖表線
        self.heart_rate_curve = self.plot_widget.plot(pen='r', name='心率')
        self.spo2_curve = self.plot_widget.plot(pen='b', name='血氧')

        layout.addWidget(self.plot_widget)

        # 控制按鈕
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)

        self.start_button = QPushButton("開始監測")
        self.start_button.clicked.connect(self.start_monitoring)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止監測")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.load_button = QPushButton("載入歷史數據")
        self.load_button.clicked.connect(self.load_history)
        button_layout.addWidget(self.load_button)

        layout.addWidget(button_frame)

    def update_data(self):
        if self.monitoring:
            current_time = time.time()
            # 模擬心率和血氧數據
            hr = 70 + (time.time() % 10)  # 模擬變化
            spo2 = 98 + (time.time() % 2)  # 模擬變化

            self.heart_rate_data.append(hr)
            self.spo2_data.append(spo2)
            self.time_data.append(current_time - self.start_time)

            # 更新標籤
            self.heart_rate_label.setText(f"當前心率 (BPM): {hr:.1f}")
            self.spo2_label.setText(f"當前血氧 (%): {spo2:.1f}")

            # 更新圖表
            self.update_plot()

    def update_plot(self):
        # 更新圖表數據
        self.heart_rate_curve.setData(self.time_data, self.heart_rate_data)
        self.spo2_curve.setData(self.time_data, self.spo2_data)

        # 實現滾動效果：設置 X 軸範圍為最近的滾動窗口
        if self.time_data:
            current_time = self.time_data[-1]
            start_time = max(0, current_time - self.scroll_window)
            self.plot_widget.setXRange(start_time, current_time, padding=0.02)

    def start_monitoring(self):
        self.monitoring = True
        self.start_time = time.time()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.timer.start(1000)  # 每秒更新

    def stop_monitoring(self):
        self.monitoring = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.timer.stop()

    def load_history(self):
        # 模擬載入歷史數據
        try:
            with open('health_data.json', 'r') as f:
                data = json.load(f)
                self.heart_rate_data = data.get('heart_rate', [])
                self.spo2_data = data.get('spo2', [])
                self.time_data = data.get('time', [])
                self.update_plot()
        except FileNotFoundError:
            print("歷史數據文件不存在")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HealthMonitorUI()
    window.show()
    sys.exit(app.exec())