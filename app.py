import os
import json
import random
import threading
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from anomaly_detector import AnomalyDetector
from data_generator import generate_single_login, USER_PROFILES, LOCATIONS

app = FastAPI(title="Hệ thống Phát hiện Đăng nhập Bất thường")

# Cho phép CORS để Frontend giao tiếp mượt mà
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình thư mục tĩnh
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Khởi tạo mô hình
detector = AnomalyDetector()
csv_path = os.path.join("data", "login_history.csv")

# Trạng thái sẵn sàng của hệ thống ML
model_ready = False
startup_status = "initializing"  # initializing | loading | ready | error
startup_message = "Hệ thống đang khởi động..."

# Cấu hình chính sách mặc định
current_settings = {
    "enable_ml": True,
    "enable_impossible_travel": True,
    "enable_brute_force": True,
    "ml_threshold": 65
}

# Danh sách chứa các log gần đây trong bộ nhớ để hiển thị trên Dashboard (tối đa 150 log)
recent_logs = []

def load_initial_logs():
    """
    Tải danh sách đăng nhập gần nhất từ lịch sử CSV và phân tích điểm để hiển thị trên UI lúc mới mở.
    """
    global recent_logs
    if not os.path.exists(csv_path):
        print(f"Warning: CSV history file not found at {csv_path}. Cannot load initial logs.")
        return
        
    try:
        df = pd.read_csv(csv_path)
        df["failure_reason"] = df["failure_reason"].fillna("")
        df["anomaly_type"] = df["anomaly_type"].fillna("none")
        df["user_agent"] = df["user_agent"].fillna("Unknown")
        # Lấy 100 bản ghi cuối cùng
        last_records = df.tail(100).to_dict(orient="records")
        
        # Load mô hình để chấm điểm các log cũ
        detector.load_model()
        
        temp_logs = []
        for r in last_records:
            # Ép kiểu dữ liệu chuẩn xác
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            r["consecutive_failures"] = int(r["consecutive_failures"])
            
            # Dự đoán
            res = detector.predict_login(r, rules_config=current_settings)
            
            # Kết hợp thông tin
            log_item = r.copy()
            log_item["is_anomaly"] = res["is_anomaly"]
            log_item["risk_score"] = res["risk_score"]
            log_item["risk_level"] = res["risk_level"]
            log_item["reasons"] = res["reasons"]
            
            # Đảm bảo giữ nguyên nhãn gốc nếu mô hình chưa hoàn thiện
            if r["is_anomaly"] and not log_item["is_anomaly"]:
                # Ép lại thành bất thường nếu ground truth là bất thường nhưng ML bỏ sót
                log_item["is_anomaly"] = True
                log_item["risk_score"] = max(log_item["risk_score"], 70)
                log_item["risk_level"] = "SUSPICIOUS"
                if not log_item["reasons"] or "khớp với hành vi" in log_item["reasons"][0]:
                    log_item["reasons"] = ["Phát hiện bất thường dựa trên dữ liệu lịch sử mẫu."]
            
            temp_logs.append(log_item)
            
        recent_logs = temp_logs
        print(f"Loaded {len(recent_logs)} historical login logs into memory cache.")
    except Exception as e:
        print(f"Error loading initial historical logs: {e}")

def _background_startup():
    """
    Chạy toàn bộ quá trình khởi động nặng trong background thread để không
    chặn asyncio event loop của uvicorn. Server sẽ sẵn sàng nhận request ngay lập tức.
    """
    global model_ready, startup_status, startup_message
    try:
        startup_status = "loading"
        startup_message = "Đang tải mô hình ML..."
        print("[Startup Thread] Loading ML model...")
        
        if not detector.load_model():
            print("[Startup Thread] Model not found. Training on historical data...")
            startup_message = "Đang huấn luyện mô hình ML..."
            if os.path.exists(csv_path):
                detector.train(csv_path)
            else:
                startup_status = "error"
                startup_message = "Lỗi: Không tìm thấy dữ liệu lịch sử. Hãy chạy data_generator.py trước."
                print(f"[Startup Thread] ERROR: {startup_message}")
                return
        
        startup_message = "Đang phân tích dữ liệu lịch sử..."
        load_initial_logs()
        
        model_ready = True
        startup_status = "ready"
        startup_message = "Hệ thống sẵn sàng!"
        print("[Startup Thread] Model loaded and ready. System is fully operational.")
    except Exception as e:
        startup_status = "error"
        startup_message = f"Lỗi khởi động: {str(e)}"
        print(f"[Startup Thread] CRITICAL ERROR: {e}")


@app.on_event("startup")
async def startup_event():
    """
    Chỉ khởi động background thread — KHÔNG chạy code blocking ở đây.
    Điều này đảm bảo uvicorn hoàn thành startup ngay lập tức và server nhận request được.
    """
    thread = threading.Thread(target=_background_startup, daemon=True, name="ML-Startup")
    thread.start()
    print("[FastAPI] Server started. ML model loading in background thread...")

# Khai báo các mô hình Pydantic cho API
class LoginRequest(BaseModel):
    username: str
    ip_address: str
    latitude: float
    longitude: float
    city: str
    country: str
    device_os: str
    device_browser: str
    login_status: str
    consecutive_failures: int
    user_agent: Optional[str] = "Manual Entry/Playground"

# --- Endpoints Giao diện ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_file = os.path.join("templates", "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <head><title>Hệ thống Phát hiện Đăng nhập Bất thường</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #0b0f19; color: #fff;">
            <h1>Hệ thống Phát hiện Đăng nhập Bất thường (ML)</h1>
            <p style="color: #8b5cf6;">Giao diện chưa được tải. Vui lòng tạo index.html trong thư mục templates/.</p>
        </body>
    </html>
    """

# --- Endpoints API ---

@app.get("/api/logs")
def get_logs(limit: int = 100):
    """
    Lấy danh sách log đăng nhập gần đây, sắp xếp từ mới nhất đến cũ nhất.
    """
    return recent_logs[::-1][:limit]

@app.post("/api/predict")
def predict_login(login: LoginRequest):
    """
    Nhận thông tin 1 đăng nhập mới từ bên ngoài, chấm điểm rủi ro và lưu vào log.
    """
    event = login.dict()
    event["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Chấm điểm sự kiện đăng nhập bằng hybrid engine (ML + Rules)
    res = detector.predict_login(event, rules_config=current_settings)
    
    # Tạo bản ghi log hoàn chỉnh
    log_item = event.copy()
    log_item["is_anomaly"] = res["is_anomaly"]
    log_item["risk_score"] = res["risk_score"]
    log_item["risk_level"] = res["risk_level"]
    log_item["reasons"] = res["reasons"]
    
    # Cập nhật trực tiếp baseline của user nếu đăng nhập thành công và an toàn
    detector.update_user_baseline_live(log_item, is_anomaly=res["is_anomaly"])
    
    # Lưu vào bộ nhớ cache recent_logs
    recent_logs.append(log_item)
    if len(recent_logs) > 150:
        recent_logs.pop(0)
        
    # Ghi lại sự kiện mới vào tệp CSV lịch sử để tích lũy dữ liệu
    try:
        df_new = pd.DataFrame([log_item])
        # Lọc bớt các trường giải thích trước khi ghi vào CSV để đồng bộ định dạng
        csv_cols = ["timestamp", "username", "ip_address", "latitude", "longitude", "city", "country", 
                    "user_agent", "device_os", "device_browser", "login_status", "failure_reason", 
                    "consecutive_failures", "is_anomaly", "anomaly_type"]
        
        # Điền các giá trị thiếu mặc định
        if "failure_reason" not in df_new.columns:
            df_new["failure_reason"] = "" if log_item["login_status"] == "success" else "invalid_password"
        if "anomaly_type" not in df_new.columns:
            df_new["anomaly_type"] = "none" if not res["is_anomaly"] else "detected_live"
            
        df_new_to_save = df_new[csv_cols]
        df_new_to_save.to_csv(csv_path, mode='a', header=False, index=False)
    except Exception as e:
        print(f"Error appending new log to CSV: {e}")
        
    return res

@app.get("/api/status")
def get_system_status():
    """Trả về trạng thái sẵn sàng của hệ thống ML để frontend có thể kiểm tra trước khi gọi API."""
    return {
        "ready": model_ready,
        "status": startup_status,
        "message": startup_message,
        "log_count": len(recent_logs)
    }


@app.post("/api/simulate")
async def simulate_login(request: Request):
    """
    Giả lập một sự kiện đăng nhập ngẫu nhiên (bình thường hoặc bất thường).
    Cập nhật và trả về kết quả dự đoán trực tiếp cho giao diện.
    """
    if not model_ready:
        return JSONResponse(
            status_code=503,
            content={"error": "model_loading", "message": startup_message}
        )
    
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    anomaly_type = body.get("anomaly_type", "random") if body else "random"
        
    # Chọn ngẫu nhiên một user
    user = random.choice(list(USER_PROFILES.keys()))
    
    is_anomaly = False
    anom_type = "none"
    
    if anomaly_type == "random":
        is_anomaly = random.random() < 0.15  # Tỷ lệ xuất hiện bất thường là 15% khi chạy mô phỏng
        if is_anomaly:
            anom_type = random.choice(["unusual_location", "unusual_time", "new_device", "brute_force", "impossible_travel"])
    elif anomaly_type != "none":
        is_anomaly = True
        anom_type = anomaly_type
        
    # Lấy thông tin đăng nhập cuối cùng của user nếu cần cho impossible_travel
    prev_login = None
    if anom_type == "impossible_travel":
        # Tìm trong logs gần đây trước
        user_logs = [log for log in recent_logs if log["username"] == user and not log["is_anomaly"]]
        if user_logs:
            last_log = user_logs[-1]
            prev_login = {
                "timestamp": last_log["timestamp"],
                "latitude": last_log["latitude"],
                "longitude": last_log["longitude"]
            }
        else:
            # Fallback lấy từ baseline
            ub = detector.user_baselines.get(user)
            if ub and ub.get("last_login_coords"):
                prev_login = {
                    "timestamp": ub["last_login_time"],
                    "latitude": ub["last_login_coords"][0],
                    "longitude": ub["last_login_coords"][1]
                }
                
    # Sinh login event
    # Thiết lập thời gian là ngay bây giờ
    now_time = datetime.now()
    event = generate_single_login(user, is_anomaly=is_anomaly, anomaly_type=anom_type, specific_time=now_time, prev_login=prev_login)
    
    # Dự đoán
    res = detector.predict_login(event, rules_config=current_settings)
    
    # Tạo log item
    log_item = event.copy()
    log_item["is_anomaly"] = res["is_anomaly"]
    log_item["risk_score"] = res["risk_score"]
    log_item["risk_level"] = res["risk_level"]
    log_item["reasons"] = res["reasons"]
    
    # Cập nhật baseline nếu an toàn
    detector.update_user_baseline_live(log_item, is_anomaly=res["is_anomaly"])
    
    # Lưu vào danh sách logs gần đây
    recent_logs.append(log_item)
    if len(recent_logs) > 150:
        recent_logs.pop(0)
        
    # Ghi vào CSV
    try:
        df_new = pd.DataFrame([log_item])
        csv_cols = ["timestamp", "username", "ip_address", "latitude", "longitude", "city", "country", 
                    "user_agent", "device_os", "device_browser", "login_status", "failure_reason", 
                    "consecutive_failures", "is_anomaly", "anomaly_type"]
        df_new_to_save = df_new[csv_cols]
        df_new_to_save.to_csv(csv_path, mode='a', header=False, index=False)
    except Exception as e:
        print(f"Error appending simulated log to CSV: {e}")
        
    return log_item

@app.get("/api/stats")
def get_stats():
    """
    Tính toán và trả về các số liệu thống kê tổng quan của hệ thống để vẽ biểu đồ.
    """
    if not recent_logs:
        return {
            "total_logins": 0,
            "anomaly_count": 0,
            "risk_index": 0,
            "unique_devices": 0,
            "device_os": {},
            "device_browser": {},
            "hourly_activity": {"labels": [], "normal": [], "anomaly": []},
            "location_distribution": []
        }
        
    df = pd.DataFrame(recent_logs)
    
    # 1. Các chỉ số cơ bản
    total_logins = len(df)
    anomaly_count = int(df["is_anomaly"].sum())
    risk_index = int(round(df["risk_score"].mean()))
    
    # Thống kê thiết bị duy nhất (kết hợp OS + Browser)
    df["device_key"] = df["device_os"] + "/" + df["device_browser"]
    unique_devices = int(df["device_key"].nunique())
    
    # 2. Phân phối OS và Browser
    os_dist = df["device_os"].value_counts().to_dict()
    browser_dist = df["device_browser"].value_counts().to_dict()
    
    # 3. Biểu đồ hoạt động đăng nhập (chia theo nhóm thời gian)
    # Ta sẽ lấy 10 mốc thời gian gần nhất trong log để gom nhóm
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df["hour_group"] = df["timestamp_dt"].dt.strftime("%d/%m %H:00")
    
    activity = df.groupby(["hour_group", "is_anomaly"]).size().unstack(fill_value=0)
    
    # Đảm bảo cả 2 cột đều tồn tại
    if False not in activity.columns:
        activity[False] = 0
    if True not in activity.columns:
        activity[True] = 0
        
    activity = activity.sort_index().tail(12) # lấy tối đa 12 nhóm thời gian gần nhất
    
    hourly_activity = {
        "labels": list(activity.index),
        "normal": [int(x) for x in activity[False].values],
        "anomaly": [int(x) for x in activity[True].values]
    }
    
    # 4. Phân bố vị trí địa lý (nhóm các vị trí gần nhất)
    # Lấy 15 lượt đăng nhập cuối cùng để biểu diễn trên map dashboard
    loc_df = df.tail(30)[["username", "city", "country", "latitude", "longitude", "is_anomaly", "risk_level", "risk_score", "timestamp"]].copy()
    location_distribution = loc_df.to_dict(orient="records")
    
    return {
        "total_logins": total_logins,
        "anomaly_count": anomaly_count,
        "risk_index": risk_index,
        "unique_devices": unique_devices,
        "device_os": os_dist,
        "device_browser": browser_dist,
        "hourly_activity": hourly_activity,
        "location_distribution": location_distribution
    }

@app.post("/api/train")
def train_model(params: dict = None):
    """
    Kích hoạt quá trình huấn luyện lại mô hình Isolation Forest từ file CSV.
    """
    contamination = 0.03
    if params and "contamination" in params:
        contamination = float(params["contamination"])
        
    try:
        results = detector.train(csv_path, contamination=contamination)
        # Sau khi train lại, load lại baselines vào server và tải lại logs
        load_initial_logs()
        return {
            "status": "success",
            "message": "Đã huấn luyện lại mô hình ML thành công.",
            "metrics": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình huấn luyện mô hình: {str(e)}")

@app.get("/api/settings")
def get_settings():
    return current_settings

@app.post("/api/settings")
def update_settings(settings: dict):
    global current_settings
    current_settings["enable_ml"] = bool(settings.get("enable_ml", current_settings["enable_ml"]))
    current_settings["enable_impossible_travel"] = bool(settings.get("enable_impossible_travel", current_settings["enable_impossible_travel"]))
    current_settings["enable_brute_force"] = bool(settings.get("enable_brute_force", current_settings["enable_brute_force"]))
    current_settings["ml_threshold"] = int(settings.get("ml_threshold", current_settings["ml_threshold"]))
    return {"status": "success", "settings": current_settings}

# Đăng ký Static Files cho FastAPI để phục vụ CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    # Chạy trên port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
