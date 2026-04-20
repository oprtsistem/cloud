import json
import random

def generate_fake_health_data(seconds=60):
    heart_rate_list = []
    spo2_list = []
    time_list = []

    for t in range(seconds):
        # 模擬心率：在 70 到 85 之間跳動
        hr = round(random.uniform(70.0, 85.0), 1)
        # 模擬血氧：在 95 到 100 之間跳動
        spo2 = round(random.uniform(95.0, 100.0), 1)
        
        heart_rate_list.append(hr)
        spo2_list.append(spo2)
        time_list.append(t)

    # 組合成前端 UI 預期的字典格式
    data = {
        "heart_rate": heart_rate_list,
        "spo2": spo2_list,
        "time": time_list
    }

    # 輸出成 JSON 檔案
    with open('health_data.json', 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"成功生成 {seconds} 筆假數據，已儲存至 health_data.json！")

if __name__ == "__main__":
    generate_fake_health_data()