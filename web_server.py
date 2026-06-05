"""
web_server.py — 多人健康監測系統 Web Server (支援 3 人切換與一鍵格式化)
"""

import argparse
import logging
import sys
import time

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from db_manager import HealthDatabase

# 設定日誌
logging.basicConfig(
    filename="health_monitor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CORS_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

# 💡 全域控制狀態：記錄目前是哪位使用者在進行「被動持續量測」，預設為 'A'
current_measuring_user = "A"

def create_app(db_path: str) -> Flask:
    app = Flask(__name__)
    CORS(app, origins=CORS_ORIGINS)

    # 初始化 HealthDatabase
    db = None
    try:
        db = HealthDatabase(db_name=db_path)
        logger.info(f"HealthDatabase 初始化成功：{db_path}")
    except Exception as e:
        logger.error(f"HealthDatabase 初始化失敗：{e}")

    # ------------------------------------------------------------------ #
    # 路由：/ — 提供網頁介面
    # ------------------------------------------------------------------ #
    @app.route("/", methods=["GET"])
    def serve_index():
        return render_template("index.html")

    # ------------------------------------------------------------------ #
    # 💡 [全新微服務] 路由：/api/control — 控制狀態機 (切換使用者與格式化)
    # ------------------------------------------------------------------ #
    @app.route("/api/control", methods=["GET", "POST"])
    def control_system():
        """
        GET: 查詢目前正在量測哪位使用者
        POST: 切換目前使用者 (1, 2, 3 -> A, B, C) 或一鍵格式化 (R)
        """
        global current_measuring_user
        
        if db is None:
            return jsonify({"error": "資料庫連線失敗"}), 500

        if request.method == "POST":
            req_data = request.get_json() or {}
            action = req_data.get("action") # 'switch' 或 'clear'
            
            if action == "switch":
                target_user = req_data.get("user_id") # 'A', 'B', 'C'
                if target_user in ["A", "B", "C"]:
                    current_measuring_user = target_user
                    logger.info(f"系統狀態切換：目前量測對象變更為使用者 {current_measuring_user}")
                    return jsonify({"status": "success", "current_user": current_measuring_user}), 200
                return jsonify({"error": "無效的使用者，必須為 A, B 或 C"}), 400
                
            elif action == "clear":
                try:
                    db.clear_all_data()
                    current_measuring_user = "A" # 格式化後歸位到 A
                    logger.warning("系統狀態重設：資料庫已清空並重置為使用者 A")
                    return jsonify({"status": "success", "message": "資料庫已成功格式化", "current_user": "A"}), 200
                except Exception as e:
                    return jsonify({"error": f"格式化失敗: {e}"}), 500
            
            return jsonify({"error": "未知的操作指令"}), 400

        # GET 請求：直接回傳當前狀態
        return jsonify({"current_user": current_measuring_user}), 200

    # ------------------------------------------------------------------ #
    # 路由：/api/data — 歷史數據 API (已修復 HTTP 500)
    # ------------------------------------------------------------------ #
    @app.route("/api/data", methods=["GET"])
    def get_data():
        global current_measuring_user
        
        seconds_str = request.args.get("seconds", "60")
        try:
            seconds = int(seconds_str)
        except (ValueError, TypeError):
            return jsonify({"error": "seconds 必須為正整數"}), 400

        if seconds <= 0 or seconds > 3600:
            return jsonify({"error": "seconds 必須介於 1 到 3600 之間"}), 400

        if db is None:
            return jsonify({"error": "資料庫連線失敗"}), 500

        try:
            # 💡 修正點：改呼叫 get_user_recent_data 並代入當前被指派的使用者
            data = db.get_user_recent_data(user_id=current_measuring_user, seconds=seconds)
            data["count"] = len(data["heart_rate"])
            data["current_user"] = current_measuring_user # 順便告訴前端現在是誰
            return jsonify(data), 200
        except Exception as e:
            logger.error(f"get_data 資料庫讀取失敗：{e}")
            return jsonify({"error": f"資料庫讀取失敗: {e}"}), 500

    # ------------------------------------------------------------------ #
    # 路由：/api/latest — 最新數據 API (已修復 HTTP 500)
    # ------------------------------------------------------------------ #
    @app.route("/api/latest", methods=["GET"])
    def get_latest():
        global current_measuring_user
        
        if db is None:
            return jsonify({"error": "資料庫連線失敗"}), 500

        try:
            # 💡 修正點：改呼叫 get_user_recent_data 並代入當前被指派的使用者
            data = db.get_user_recent_data(user_id=current_measuring_user, seconds=60)

            if not data["heart_rate"]:
                return jsonify({
                    "heart_rate": None,
                    "spo2": None,
                    "timestamp": None,
                    "status": "no_data",
                    "current_user": current_measuring_user
                }), 200

            hr = data["heart_rate"][-1]
            spo2 = data["spo2"][-1]
            ts = data["time"][-1]

            try:
                hr_val = float(hr)
                spo2_val = float(spo2)
                if spo2_val < 95 or hr_val < 60 or hr_val > 100:
                    status = "warning"
                else:
                    status = "normal"
            except (TypeError, ValueError):
                status = "warning"

            return jsonify({
                "heart_rate": hr,
                "spo2": spo2,
                "timestamp": ts,
                "status": status,
                "current_user": current_measuring_user
            }), 200

        except Exception as e:
            logger.error(f"get_latest 資料庫讀取失敗：{e}")
            return jsonify({"error": f"資料庫讀取失敗: {e}"}), 500

    # ------------------------------------------------------------------ #
    # 路由：/api/health — 健康檢查 API
    # ------------------------------------------------------------------ #
    @app.route("/api/health", methods=["GET"])
    def health_check():
        ts = time.time()
        if db is None:
            return jsonify({"status": "degraded", "db": "disconnected", "timestamp": ts}), 200

        try:
            import sqlite3
            conn = sqlite3.connect(db.db_name)
            conn.execute("SELECT 1")
            conn.close()
            return jsonify({"status": "ok", "db": "connected", "timestamp": ts}), 200
        except Exception as e:
            logger.error(f"health_check 資料庫連線失敗：{e}")
            return jsonify({"status": "degraded", "db": "disconnected", "timestamp": ts}), 200

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="健康監測系統 Web Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="綁定的主機位址")
    parser.add_argument("--port", type=int, default=5000, help="監聽的埠號")
    parser.add_argument("--db", type=str, default="health_data.db", help="SQLite 資料庫路徑")

    args = parser.parse_args()

    if not args.host or not args.host.strip():
        print("錯誤：--host 參數不可為空", file=sys.stderr)
        sys.exit(1)

    if not (1 <= args.port <= 65535):
        print(f"錯誤：--port 錯誤：{args.port}", file=sys.stderr)
        sys.exit(1)

    app = create_app(db_path=args.db)
    print(f"Web Server 啟動中：http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)