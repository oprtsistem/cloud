import time
import random
import threading
import requests
from db_manager import HealthDatabase

# 全域控制變數
is_running = True
current_user = "A"
FLASK_CONTROL_API = "http://127.0.0.1:5000/api/control"
db = HealthDatabase(db_name="health_data.db")

def background_sensor_loop():
    """ 💡 這個函式會在背景獨自運行，負責『被動、持續地量測與儲存數值』 """
    global is_running, current_user
    print("\n[系統資訊] 背景持續量測執行緒已啟動...")
    
    while is_running:
        try:
            # 1. 自動去問 Flask 目前全域設定是誰（確保跟網頁同步）
            try:
                response = requests.get(FLASK_CONTROL_API, timeout=1)
                if response.status_code == 200:
                    current_user = response.json().get("current_user", "A")
            except Exception:
                pass # Flask 若沒開則維持目前的 current_user

            # 2. 模擬 MAX30102 的實測合理數值
            hr = round(random.uniform(72.0, 78.0), 1)
            spo2 = round(random.uniform(96.5, 99.0), 1)
            
            # 3. 寫入資料庫
            db.insert_record(user_id=current_user, heart_rate=hr, spo2=spo2)
            
        except Exception as e:
            print(f"\n[錯誤] 寫入資料庫失敗: {e}")
            
        # 每秒量測一次
        time.sleep(1)

def main_control_panel():
    """ 💡 這個主功能負責『聆聽鍵盤指令』，程式再也不會卡死，隨時可切換或中斷！ """
    global is_running, current_user
    
    print("==================================================")
    print(" 🏥 多人血氧監測控制台 (已解除阻塞卡死問題)")
    print("==================================================")
    print(" 隨時在下方輸入指令並按 Enter：")
    print(" [ 1 ] 立即切換為 -> 使用者 A")
    print(" [ 2 ] 立即切換為 -> 使用者 B")
    print(" [ 3 ] 立即切換為 -> 使用者 C")
    print(" [ R ] 一鍵格式化所有資料庫記憶")
    print(" [ Q ] 安全中斷並關閉量測系統")
    print("==================================================")

    # 🚀 啟動背景持續量測執行緒
    sensor_thread = threading.Thread(target=background_sensor_loop, daemon=True)
    sensor_thread.start()

    while is_running:
        # 因為量測跑到背景去了，這裡的 input 再也不會卡住系統！
        cmd = input(f"\n【目前指派對象：{current_user}】請輸入指令: ").strip().upper()
        
        if cmd == '1':
            current_user = 'A'
            # 同步告知 Flask 伺服器
            try: requests.post(FLASK_CONTROL_API, json={"action": "switch", "user_id": "A"})
            except: pass
            print("🔄 成功切換！接下來的數值將持續記錄在：[ 使用者 A ]")
            
        elif cmd == '2':
            current_user = 'B'
            try: requests.post(FLASK_CONTROL_API, json={"action": "switch", "user_id": "B"})
            except: pass
            print("🔄 成功切換！接下來的數值將持續記錄在：[ 使用者 B ]")
            
        elif cmd == '3':
            current_user = 'C'
            try: requests.post(FLASK_CONTROL_API, json={"action": "switch", "user_id": "C"})
            except: pass
            print("🔄 成功切換！接下來的數值將持續記錄在：[ 使用者 C ]")
            
        elif cmd == 'R':
            confirm = input("❗ 確定要格式化所有使用者的記憶嗎？(Y/N): ").strip().upper()
            if confirm == 'Y':
                try:
                    requests.post(FLASK_CONTROL_API, json={"action": "clear"})
                    current_user = 'A'
                    print("⚠️ 資料庫已格式化清空！系統重置為使用者 A。")
                except:
                    db.clear_all_data()
                    current_user = 'A'
                    print("⚠️ 格式化成功 (本地重置)。")
                    
        elif cmd == 'Q':
            print("⏹️ 正在安全中斷系統...")
            is_running = False # 讓背景執行緒停止
            break
        else:
            print("❌ 無效指令，請輸入 1, 2, 3, R 或 Q。")

if __name__ == "__main__":
    main_control_panel()