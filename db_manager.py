# -*-coding:utf-8-*-
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
                user_id TEXT NOT NULL,         -- 💡 新增：用來區分 'A', 'B', 'C'
                timestamp REAL NOT NULL,
                heart_rate REAL NOT NULL,
                spo2 REAL NOT NULL,
                is_valid BOOLEAN NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def insert_record(self, heart_rate, spo2, user_id="A"):
        """
        寫入單筆感測數據 (向下相容版本)
        ui.py 與測試依然可以用 db.insert_record(hr, spo2) 呼叫，預設寫入 "A"
        多人切換時可以用 db.insert_record(hr, spo2, user_id="B") 呼叫
        """
        is_valid = True
        
        # 1. 防呆過濾：檢查數據是否在人類合理的生理範圍內
        if not (30 <= heart_rate <= 220):
            is_valid = False
            logging.warning(f"異常心率攔截: User={user_id}, HR={heart_rate}")
            
        if not (50 <= spo2 <= 100):
            is_valid = False
            logging.warning(f"異常血氧攔截: User={user_id}, SpO2={spo2}")

        # 2. 寫入資料庫
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        current_time = time.time()
        
        cursor.execute('''
            INSERT INTO health_records (user_id, timestamp, heart_rate, spo2, is_valid)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, current_time, heart_rate, spo2, is_valid))
        
        conn.commit()
        conn.close()
        
        # 3. 正常日誌記錄
        if is_valid:
            logging.info(f"成功寫入使用者 [{user_id}] 紀錄: HR={heart_rate}, SpO2={spo2}")
            print(f"[DB LOG] 成功寫入使用者 [{user_id}] 紀錄: HR={heart_rate}, SpO2={spo2}")
        else:
            print(f"[警告] 攔截到異常數據，已標記為無效！(User={user_id}, HR={heart_rate}, SpO2={spo2})")

    def get_user_recent_data(self, user_id="A", seconds=60):
        """
        💡 完美對接 web_server.py 的命名！
        讀取特定使用者最近 N 秒的有效數據
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        time_threshold = time.time() - seconds
        
        cursor.execute('''
            SELECT timestamp, heart_rate, spo2 
            FROM health_records 
            WHERE user_id = ? AND timestamp >= ? AND is_valid = 1
            ORDER BY timestamp ASC
        ''', (user_id, time_threshold,))
        
        records = cursor.fetchall()
        conn.close()
        
        result = {
            "user_id": user_id,
            "heart_rate": [r[1] for r in records],
            "spo2": [r[2] for r in records],
            "time": [r[0] for r in records] 
        }
        return result

    def get_recent_data(self, seconds=60):
        """
        💡 保留原有的無 user_id 版本方法，防止其他未預期的模組調用出錯
        預設直接撈取全體或預設使用者 'A'
        """
        return self.get_user_recent_data(user_id="A", seconds=seconds)

    def clear_all_data(self):
        """💡 核心新功能：一鍵格式化（刪除所有歷史記憶）"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 刪除資料表內所有資料
        cursor.execute('DELETE FROM health_records')
        
        # 將自動遞增的 id 計算器歸零
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="health_records"')
        
        conn.commit()
        conn.close()
        print("\n⚠️ [DB WARNING] 資料庫已成功格式化！所有使用者紀錄已清空。")


# ==== 測試區塊 ====
if __name__ == "__main__":
    db = HealthDatabase()
    
    # 模擬演算法寫入數據（正確傳入 user_id 'A' 與 'B'）
    print("模擬寫入數據中...")
    db.insert_record(75.5, 98.2, "A")
    time.sleep(0.5)
    db.insert_record(82.0, 99.5, "B")  # 寫入不同人
    time.sleep(0.5)
    db.insert_record(76.0, 99.0, "A")
    
    # 寫入一筆異常數據，會自動被標記為 is_valid=False
    db.insert_record(300.0, 40.0, "A")
    
    # 模擬前端同學讀取 A 使用者數據
    print("\n前端讀取最近 60 秒 使用者 A 的數據:")
    recent_data_A = db.get_user_recent_data(user_id="A")
    print(recent_data_A)
    
    # 模擬前端同學讀取 B 使用者數據
    print("\n前端讀取最近 60 秒 使用者 B 的數據:")
    recent_data_B = db.get_user_recent_data(user_id="B")
    print(recent_data_B)
