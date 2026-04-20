import sqlite3
import time
import logging

# 設定系統日誌 
logging.basicConfig(
    filename='health_monitor.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HealthDatabase:
    def __init__(self, db_name="health_data.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """初始化資料庫與資料表"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        # 建立資料表 (如果不存在的話)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                heart_rate REAL NOT NULL,
                spo2 REAL NOT NULL,
                is_valid BOOLEAN NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def insert_record(self, heart_rate, spo2):
        """寫入單筆感測數據 (包含防呆邏輯)"""
        is_valid = True
        
        # 1. 防呆過濾：檢查數據是否在人類合理的生理範圍內
        if not (30 <= heart_rate <= 220):
            is_valid = False
            logging.warning(f"異常心率攔截: HR={heart_rate}")
            
        if not (50 <= spo2 <= 100):
            is_valid = False
            logging.warning(f"異常血氧攔截: SpO2={spo2}")

        # 2. 寫入資料庫
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        current_time = time.time()
        
        cursor.execute('''
            INSERT INTO health_records (timestamp, heart_rate, spo2, is_valid)
            VALUES (?, ?, ?, ?)
        ''', (current_time, heart_rate, spo2, is_valid))
        
        conn.commit()
        conn.close()
        
        # 3. 正常日誌記錄
        if is_valid:
            logging.info(f"成功寫入: HR={heart_rate}, SpO2={spo2}")
            print(f"[DB LOG] 寫入成功: HR={heart_rate}, SpO2={spo2}")
        else:
            print(f"[警告] 攔截到異常數據，已標記為無效！(HR={heart_rate}, SpO2={spo2})")

    def get_recent_data(self, seconds=60):
        """讀取最近 N 秒的有效數據 (給前端同學呼叫的)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        time_threshold = time.time() - seconds
        
        # 只撈取 is_valid 為 True (有效) 的數據
        cursor.execute('''
            SELECT timestamp, heart_rate, spo2 
            FROM health_records 
            WHERE timestamp >= ? AND is_valid = 1
            ORDER BY timestamp ASC
        ''', (time_threshold,))
        
        records = cursor.fetchall()
        conn.close()
        
        # 轉成前端 UI 預期的字典格式
        result = {
            "heart_rate": [r[1] for r in records],
            "spo2": [r[2] for r in records],
            "time": [r[0] for r in records] 
        }
        return result

# ==== 測試區塊 ====
if __name__ == "__main__":
    db = HealthDatabase()
    
    # 模擬演算法同學寫入數據
    print("模擬寫入數據中...")
    db.insert_record(75.5, 98.2)
    time.sleep(1)
    db.insert_record(76.0, 99.0)
    
    # 寫入一筆因為手指拿開導致的無效異常數據 (is_valid=False)
    db.insert_record(300.0, 40.0, is_valid=False) 
    
    # 模擬前端同學讀取數據
    print("\n前端讀取最近 60 秒的數據:")
    recent_data = db.get_recent_data()
    print(recent_data)
   