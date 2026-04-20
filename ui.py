import sys
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg

# 匯入你寫好的資料庫管理類別
from db_manager import HealthDatabase

class HealthMonitorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("血氧與心率監測器")
        self.setGeometry(100, 100, 800, 600)

        # 初始化資料庫
        self.db = HealthDatabase()

        # 數據存儲（用於繪圖）
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
        title_label = QLabel("血氧與心率監測 (SQLite 整合版)")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title_label)

        # 當前數值顯示區域
        current_frame = QFrame()
        current_frame.setFrameShape(QFrame.Shape.StyledPanel)
        current_layout = QHBoxLayout(current_frame)

        self.heart_rate_label = QLabel("當前心率 (BPM): --")
        self.heart_rate_label.setStyleSheet("font-size: 16px; color: red; font-weight: bold;")
        current_layout.addWidget(self.heart_rate_label)

        self.spo2_label = QLabel("當前血氧 (%): --")
        self.spo2_label.setStyleSheet("font-size: 16px; color: blue; font-weight: bold;")
        current_layout.addWidget(self.spo2_label)

        layout.addWidget(current_frame)

        # 圖表區域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("即時趨勢圖", color="k", size="12pt")
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        
        # 設置標籤
        self.plot_widget.setLabel('left', '數值')
        self.plot_widget.setLabel('bottom', '時間 (秒)')

        # 創建兩個圖表線
        self.heart_rate_curve = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name='心率 (BPM)')
        self.spo2_curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='血氧 (%)')

        layout.addWidget(self.plot_widget)

        # 控制按鈕區域
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)

        self.start_button = QPushButton("開始監測")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_monitoring)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止監測")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.load_button = QPushButton("載入最近 60s 紀錄")
        self.load_button.setMinimumHeight(40)
        self.load_button.clicked.connect(self.load_history)
        button_layout.addWidget(self.load_button)

        layout.addWidget(button_frame)

    def update_data(self):
        if self.monitoring:
            # 這裡暫時模擬數據生成（未來會接第 5 位同學的演算法結果）
            hr = 70 + (time.time() % 15)  
            spo2 = 96 + (time.time() % 4)

            # --- 關鍵修改：將數據同步存入資料庫 ---
            # 這樣你的資料庫就不會是空的，且會經過 db_manager 的防呆檢查
            self.db.insert_record(hr, spo2)

            # 更新 UI 顯示
            current_time = time.time() - self.start_time
            self.heart_rate_data.append(hr)
            self.spo2_data.append(spo2)
            self.time_data.append(current_time)

            self.heart_rate_label.setText(f"當前心率 (BPM): {hr:.1f}")
            self.spo2_label.setText(f"當前血氧 (%): {spo2:.1f}")

            # 警報機制：血氧低於 95% 標籤變紅
            if spo2 < 95:
                self.spo2_label.setStyleSheet("font-size: 16px; color: red; font-weight: bold;")
            else:
                self.spo2_label.setStyleSheet("font-size: 16px; color: blue; font-weight: bold;")

            self.update_plot()

    def update_plot(self):
        self.heart_rate_curve.setData(self.time_data, self.heart_rate_data)
        self.spo2_curve.setData(self.time_data, self.spo2_data)

        if self.time_data:
            current_time = self.time_data[-1]
            start_time = max(0, current_time - self.scroll_window)
            self.plot_widget.setXRange(start_time, current_time, padding=0.02)

    def start_monitoring(self):
        self.monitoring = True
        self.start_time = time.time()
        # 清除舊繪圖緩存
        self.heart_rate_data = []
        self.spo2_data = []
        self.time_data = []
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.timer.start(1000) 

    def stop_monitoring(self):
        self.monitoring = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.timer.stop()

    def load_history(self):
        """從 SQLite 資料庫讀取最近的歷史數據"""
        try:
            # 呼叫你寫的資料庫讀取函數
            data = self.db.get_recent_data(seconds=60)
            
            hr_list = data.get('heart_rate', [])
            spo2_list = data.get('spo2', [])
            raw_timestamps = data.get('time', [])

            if not hr_list:
                print("資料庫內尚無數據")
                return

            # 將絕對時間戳轉為相對顯示時間（秒）
            start_t = raw_timestamps[0]
            self.time_data = [t - start_t for t in raw_timestamps]
            self.heart_rate_data = hr_list
            self.spo2_data = spo2_list
            
            self.update_plot()
            print(f"成功從資料庫載入 {len(hr_list)} 筆歷史紀錄")
        except Exception as e:
            print(f"載入失敗: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HealthMonitorUI()
    window.show()
    sys.exit(app.exec())