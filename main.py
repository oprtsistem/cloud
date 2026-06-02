import time
import numpy as np
from max30102 import MAX30102


# =========================
# Red / IR -> BPM
# =========================
def calculate_bpm(ir_values, sample_rate):
    if len(ir_values) < sample_rate * 5:
        return None

    ir = np.array(ir_values)
    ir_signal = ir - np.mean(ir)

    threshold = np.mean(ir_signal) + 0.5 * np.std(ir_signal)

    peaks = []

    for i in range(1, len(ir_signal) - 1):
        if ir_signal[i] > ir_signal[i - 1] and ir_signal[i] > ir_signal[i + 1]:
            if ir_signal[i] > threshold:
                peaks.append(i)

    if len(peaks) < 2:
        return None

    intervals = []

    for i in range(1, len(peaks)):
        interval = (peaks[i] - peaks[i - 1]) / sample_rate

        # 合理心跳範圍：約 40~150 BPM
        if 0.4 <= interval <= 1.5:
            intervals.append(interval)

    if len(intervals) == 0:
        return None

    avg_interval = np.mean(intervals)
    bpm = 60 / avg_interval

    return bpm


# =========================
# Red / IR -> SpO2
# =========================
def calculate_spo2(red_values, ir_values):
    if len(red_values) < 50 or len(ir_values) < 50:
        return None

    red = np.array(red_values)
    ir = np.array(ir_values)

    dc_red = np.mean(red)
    dc_ir = np.mean(ir)

    ac_red = np.max(red) - np.min(red)
    ac_ir = np.max(ir) - np.min(ir)

    if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
        return None

    r = (ac_red / dc_red) / (ac_ir / dc_ir)

    spo2 = 110 - 25 * r

    # 限制在合理範圍
    spo2 = max(0, min(100, spo2))

    return spo2


try:
    m = MAX30102(channel=4, address=0x57)
    print("MAX30102 初始化成功！")
    print("請將手指輕輕放在感測器上...")

    red_buffer = []
    ir_buffer = []

    sample_rate = 20          # time.sleep(0.05) 約等於每秒 20 筆
    window_seconds = 10       # 使用最近 10 秒資料
    max_len = sample_rate * window_seconds

    while True:
        red, ir = m.read_fifo()

        if red is not None and ir is not None:
            if red > 10000 and ir > 10000:
                red_buffer.append(red)
                ir_buffer.append(ir)

                red_buffer = red_buffer[-max_len:]
                ir_buffer = ir_buffer[-max_len:]

                bpm = calculate_bpm(ir_buffer, sample_rate)
                spo2 = calculate_spo2(red_buffer, ir_buffer)

                if bpm is not None and spo2 is not None:
                    print(
                        f"紅光: {red} | 紅外線: {ir} | "
                        f"心率: {bpm:.1f} BPM | 血氧: {spo2:.1f}%"
                    )
                else:
                    print(f"紅光: {red} | 紅外線: {ir} | 計算中...")
            else:
                print("等待手指...", end="\r")

        time.sleep(0.05)

except Exception as e:
    print(f"錯誤: {e}")
