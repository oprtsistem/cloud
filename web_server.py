"""
web_server.py — 健康監測系統 Web Server
"""

import argparse
import logging
import sys
import time

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from db_manager import HealthDatabase


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


def create_app(db_path: str) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False  

 
    CORS(app, origins=CORS_ORIGINS)

    # 初始化 HealthDatabase
    db = None
    try:
        db = HealthDatabase(db_name=db_path)
        logger.info(f"HealthDatabase 初始化成功：{db_path}")
    except Exception as e:
        logger.error(f"HealthDatabase 初始化失敗：{e}")

    # --- 網頁介面 ---
    @app.route("/", methods=["GET"])
    def serve_index():
        return render_template("index.html")

    # --- 接收感測器資料的 POST API ---
    @app.route("/api/upload", methods=["POST"])
    def upload_data():
        if db is None:
            return jsonify({"error": "資料庫連線失敗"}), 500

        # 抓取前端或 Postman 傳過來的 JSON 資料
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "沒收到資料"}), 400

        # 解析心率跟血氧
        heart_rate = data.get("heart_rate")
        spo2 = data.get("spo2")

        # 檢查欄位有沒有漏掉
        if heart_rate is None or spo2 is None:
            return jsonify({"status": "error", "message": "欄位不完整"}), 400

        try:
           
            db.insert_record(heart_rate, spo2)
            
            return jsonify({
                "status": "success",
                "message": "資料成功寫入資料庫"
            }), 200
            
        except Exception as e:
            logger.error(f"upload_data 寫入失敗: {e}")
            return jsonify({"error": "資料庫寫入失敗"}), 500

    # --- 歷史數據 API ---
    @app.route("/api/data", methods=["GET"])
    def get_data():
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
            data = db.get_recent_data(seconds=seconds)
            data["count"] = len(data["heart_rate"])
            return jsonify(data), 200
        except Exception as e:
            logger.error(f"get_data 資料庫讀取失敗：{e}")
            return jsonify({"error": "資料庫讀取失敗"}), 500

    # --- 最新數據 API ---
    @app.route("/api/latest", methods=["GET"])
    def get_latest():
        if db is None:
            return jsonify({"error": "資料庫連線失敗"}), 500

        try:
            data = db.get_recent_data(seconds=60)

            if not data["heart_rate"]:
                return jsonify({
                    "heart_rate": None,
                    "spo2": None,
                    "timestamp": None,
                    "status": "no_data",
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
            }), 200

        except Exception as e:
            logger.error(f"get_latest 資料庫讀取失敗：{e}")
            return jsonify({"error": "資料庫讀取失敗"}), 500

    # --- 健康檢查 API ---
    @app.route("/api/health", methods=["GET"])
    def health_check():
        ts = time.time()

        if db is None:
            return jsonify({
                "status": "degraded",
                "db": "disconnected",
                "timestamp": ts,
            }), 200

        try:
            import sqlite3
            conn = sqlite3.connect(db.db_name)
            conn.execute("SELECT 1")
            conn.close()
            return jsonify({
                "status": "ok",
                "db": "connected",
                "timestamp": ts,
            }), 200
        except Exception as e:
            logger.error(f"health_check 資料庫連線失敗：{e}")
            return jsonify({
                "status": "degraded",
                "db": "disconnected",
                "timestamp": ts,
            }), 200

    return app


# --- 主程式進入點 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="健康監測系統 Web Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="主機位址")
    parser.add_argument("--port", type=int, default=5000, help="埠號")
    parser.add_argument("--db", type=str, default="health_data.db", help="資料庫路徑")

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