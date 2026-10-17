import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math

# Định nghĩa các địa điểm và dải IP tương ứng
LOCATIONS = {
    "Hanoi": {"lat": 21.0285, "lon": 105.8542, "country": "Vietnam", "ip_prefixes": ["113.190", "1.53", "118.70"]},
    "Ho Chi Minh City": {"lat": 10.8231, "lon": 106.6297, "country": "Vietnam", "ip_prefixes": ["14.161", "171.244", "222.252"]},
    "Da Nang": {"lat": 16.0544, "lon": 108.2022, "country": "Vietnam", "ip_prefixes": ["27.72", "115.75", "119.17"]},
    "Can Tho": {"lat": 10.0452, "lon": 105.7469, "country": "Vietnam", "ip_prefixes": ["115.79", "116.109", "171.250"]},
    "New York": {"lat": 40.7128, "lon": -74.0060, "country": "United States", "ip_prefixes": ["100.1", "104.244", "108.160"]},
    "Moscow": {"lat": 55.7558, "lon": 37.6173, "country": "Russia", "ip_prefixes": ["185.120", "178.219", "95.105"]},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503, "country": "Japan", "ip_prefixes": ["122.211", "210.140", "133.24"]},
    "London": {"lat": 51.5074, "lon": -0.1278, "country": "United Kingdom", "ip_prefixes": ["82.165", "86.12", "195.92"]}
}

USER_AGENTS = {
    "Windows/Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Windows/Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "macOS/Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "macOS/Chrome": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Linux/Firefox": "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "iOS/Safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/605.1.15",
    "Android/Chrome": "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36"
}

# Cấu hình người dùng mẫu (User Profiles)
USER_PROFILES = {
    "nguyen_van_a": {
        "home_city": "Hanoi",
        "allowed_cities": ["Hanoi", "Ho Chi Minh City"],  # Thỉnh thoảng đi công tác
        "typical_hours": [(8, 12), (13, 18)],            # Làm việc giờ hành chính
        "devices": ["Windows/Chrome", "Android/Chrome"],
        "failure_rate": 0.02
    },
    "tran_thi_b": {
        "home_city": "Ho Chi Minh City",
        "allowed_cities": ["Ho Chi Minh City", "Can Tho"],
        "typical_hours": [(9, 12), (14, 18), (20, 23)],  # Hoạt động cả buổi tối
        "devices": ["macOS/Safari", "iOS/Safari", "macOS/Chrome"],
        "failure_rate": 0.03
    },
    "le_hoang_c": {
        "home_city": "Da Nang",
        "allowed_cities": ["Da Nang"],
        "typical_hours": [(19, 24), (0, 3)],             # Cú đêm (chuyên hoạt động ban đêm)
        "devices": ["Linux/Firefox"],
        "failure_rate": 0.01
    },
    "pham_minh_d": {
        "home_city": "Can Tho",
        "allowed_cities": ["Can Tho", "Ho Chi Minh City"],
        "typical_hours": [(7, 11), (13, 17)],             # Giờ làm việc sớm
        "devices": ["Windows/Edge"],
        "failure_rate": 0.04
    },
    "security_audit": {
        "home_city": "Hanoi",
        "allowed_cities": ["Hanoi"],
        "typical_hours": [(8, 18)],
        "devices": ["Windows/Chrome"],
        "failure_rate": 0.005
    }
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách địa lý (km) giữa 2 tọa độ GPS sử dụng công thức Haversine
    """
    R = 6371.0 # Bán kính Trái đất tính bằng km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def generate_random_ip(prefixes):
    prefix = random.choice(prefixes)
    return f"{prefix}.{random.randint(1, 254)}.{random.randint(1, 254)}"

def parse_user_agent(ua_name):
    # Trích xuất hệ điều hành và trình duyệt từ tên mô tả
    parts = ua_name.split('/')
    return parts[0], parts[1]

def generate_timestamp(days_back, hour_ranges):
    # Lấy ngày mục tiêu
    target_date = datetime.now() - timedelta(days=days_back)
    
    # Chọn một khung giờ ngẫu nhiên
    start_h, end_h = random.choice(hour_ranges)
    
    if end_h < start_h: # Khung giờ qua đêm (ví dụ 20 -> 3)
        hours = list(range(start_h, 24)) + list(range(0, end_h + 1))
        hour = random.choice(hours)
    else:
        hour = random.randint(start_h, end_h - 1)
        
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return target_date.replace(hour=hour, minute=minute, second=second, microsecond=0)

def generate_single_login(username, is_anomaly=False, anomaly_type="none", specific_time=None, prev_login=None):
    profile = USER_PROFILES[username]
    
    # Mặc định thông số bình thường
    city = profile["home_city"]
    if not is_anomaly and len(profile["allowed_cities"]) > 1 and random.random() < 0.15:
        city = random.choice(profile["allowed_cities"])
        
    loc_info = LOCATIONS[city]
    # Thêm nhiễu nhẹ cho tọa độ để không bị trùng lặp khít 1 điểm
    lat = loc_info["lat"] + random.uniform(-0.05, 0.05)
    lon = loc_info["lon"] + random.uniform(-0.05, 0.05)
    country = loc_info["country"]
    ip = generate_random_ip(loc_info["ip_prefixes"])
    
    ua_name = random.choice(profile["devices"])
    user_agent = USER_AGENTS[ua_name]
    os_name, browser_name = parse_user_agent(ua_name)
    
    status = "success"
    failure_reason = ""
    consecutive_failures = 0
    
    # Chọn thời gian đăng nhập
    if specific_time:
        login_time = specific_time
    else:
        # Ngẫu nhiên trong vòng 30 ngày qua
        days_back = random.randint(0, 30)
        login_time = generate_timestamp(days_back, profile["typical_hours"])
        
    # Tạo ngẫu nhiên thất bại thông thường (gõ sai mật khẩu)
    if not is_anomaly and random.random() < profile["failure_rate"]:
        status = "failed"
        failure_reason = random.choice(["invalid_password", "caps_lock_on"])
        if random.random() < 0.2:
            consecutive_failures = 1
            
    # Áp dụng các kịch bản bất thường nếu is_anomaly=True
    if is_anomaly:
        if anomaly_type == "unusual_location":
            # Đăng nhập từ một quốc gia khác hoàn toàn
            foreign_cities = [c for c in LOCATIONS.keys() if c not in profile["allowed_cities"] and LOCATIONS[c]["country"] != "Vietnam"]
            city = random.choice(foreign_cities)
            loc_info = LOCATIONS[city]
            lat = loc_info["lat"] + random.uniform(-0.05, 0.05)
            lon = loc_info["lon"] + random.uniform(-0.05, 0.05)
            country = loc_info["country"]
            ip = generate_random_ip(loc_info["ip_prefixes"])
            
        elif anomaly_type == "unusual_time":
            # Đăng nhập vào giờ bất thường (ví dụ: 3 AM cho user bình thường)
            all_hours = set(range(24))
            typical_hours_set = set()
            for start, end in profile["typical_hours"]:
                if end < start:
                    typical_hours_set.update(list(range(start, 24)) + list(range(0, end)))
                else:
                    typical_hours_set.update(range(start, end))
            atypical_hours = list(all_hours - typical_hours_set)
            
            if atypical_hours:
                unusual_hour = random.choice(atypical_hours)
                login_time = login_time.replace(hour=unusual_hour, minute=random.randint(0, 59))
            else:
                login_time = login_time.replace(hour=3, minute=random.randint(0, 59)) # Mặc định 3h sáng
                
        elif anomaly_type == "new_device":
            # Sử dụng hệ điều hành/trình duyệt hoàn toàn khác
            all_ua_names = list(USER_AGENTS.keys())
            stranger_uas = [ua for ua in all_ua_names if ua not in profile["devices"]]
            ua_name = random.choice(stranger_uas)
            user_agent = USER_AGENTS[ua_name]
            os_name, browser_name = parse_user_agent(ua_name)
            
        elif anomaly_type == "brute_force":
            # Tạo chuỗi nhiều lần thất bại liên tiếp rồi mới thành công (hoặc thất bại tiếp)
            consecutive_failures = random.randint(5, 10)
            status = "failed"
            failure_reason = "invalid_password"
            # Thường brute force đi kèm IP lạ
            foreign_cities = [c for c in LOCATIONS.keys() if c != profile["home_city"]]
            city = random.choice(foreign_cities)
            loc_info = LOCATIONS[city]
            lat = loc_info["lat"] + random.uniform(-0.02, 0.02)
            lon = loc_info["lon"] + random.uniform(-0.02, 0.02)
            country = loc_info["country"]
            ip = generate_random_ip(loc_info["ip_prefixes"])
            
        elif anomaly_type == "impossible_travel":
            # Cần thông tin đăng nhập trước đó để tạo mâu thuẫn
            if prev_login:
                # Đăng nhập cách lần trước 10 phút nhưng ở khoảng cách rất xa (ví dụ New York vs Hanoi)
                prev_time = datetime.strptime(prev_login["timestamp"], "%Y-%m-%d %H:%M:%S")
                # Chọn thời gian đăng nhập mới sau lần trước 10 phút
                login_time = prev_time + timedelta(minutes=random.randint(5, 20))
                
                # Điểm đăng nhập mới là New York hoặc Moscow (rất xa Hà Nội/TP.HCM)
                current_home = profile["home_city"]
                far_cities = ["New York", "Moscow", "Tokyo", "London"]
                city = random.choice(far_cities)
                loc_info = LOCATIONS[city]
                lat = loc_info["lat"] + random.uniform(-0.05, 0.05)
                lon = loc_info["lon"] + random.uniform(-0.05, 0.05)
                country = loc_info["country"]
                ip = generate_random_ip(loc_info["ip_prefixes"])
            else:
                # Fallback nếu không có login trước đó: đổi thành unusual_location
                anomaly_type = "unusual_location"
                foreign_cities = [c for c in LOCATIONS.keys() if c not in profile["allowed_cities"]]
                city = random.choice(foreign_cities)
                loc_info = LOCATIONS[city]
                lat = loc_info["lat"]
                lon = loc_info["lon"]
                country = loc_info["country"]
                ip = generate_random_ip(loc_info["ip_prefixes"])

    return {
        "timestamp": login_time.strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,
        "ip_address": ip,
        "latitude": lat,
        "longitude": lon,
        "city": city,
        "country": country,
        "user_agent": user_agent,
        "device_os": os_name,
        "device_browser": browser_name,
        "login_status": status,
        "failure_reason": failure_reason,
        "consecutive_failures": consecutive_failures,
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type
    }

def generate_dataset(num_records=3000, anomaly_ratio=0.03):
    """
    Sinh toàn bộ dataset lưu trữ lịch sử đăng nhập.
    Tập dữ liệu sẽ chứa khoảng 97% dữ liệu bình thường, và 3% dữ liệu bất thường đại diện cho các cuộc tấn công.
    """
    data = []
    
    # 1. Sinh dữ liệu bình thường cho các người dùng
    num_anomalies = int(num_records * anomaly_ratio)
    num_normals = num_records - num_anomalies
    
    # Sinh dữ liệu bình thường, sắp xếp theo thời gian (giảm dần từ hiện tại về quá khứ)
    current_time = datetime.now()
    
    users = list(USER_PROFILES.keys())
    
    for _ in range(num_normals):
        username = random.choice(users)
        record = generate_single_login(username, is_anomaly=False, anomaly_type="none")
        data.append(record)
        
    # 2. Sinh dữ liệu bất thường xen kẽ
    anomaly_types = ["unusual_location", "unusual_time", "new_device", "brute_force", "impossible_travel"]
    
    # Để giả lập impossible travel, ta cần lấy 1 record bình thường của user, rồi tạo 1 record bất thường ngay sau đó
    for _ in range(num_anomalies):
        username = random.choice(users)
        anom_type = random.choice(anomaly_types)
        
        prev_login = None
        if anom_type == "impossible_travel":
            # Tìm xem có record nào trước đó của user này chưa
            user_records = [r for r in data if r["username"] == username and not r["is_anomaly"]]
            if user_records:
                prev_login = random.choice(user_records)
                
        record = generate_single_login(username, is_anomaly=True, anomaly_type=anom_type, prev_login=prev_login)
        data.append(record)
        
    # Chuyển thành DataFrame và sắp xếp theo thời gian tăng dần để dễ huấn luyện theo chuỗi thời gian
    df = pd.DataFrame(data)
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp_dt").drop(columns=["timestamp_dt"])
    
    # Cập nhật trường consecutive_failures: giả lập các lần đăng nhập lỗi liên tiếp thực sự trước khi có dòng log
    # (Đã xử lý lúc sinh bản ghi cho đơn giản)
    
    return df

def init_data_dir():
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)

if __name__ == "__main__":
    init_data_dir()
    csv_path = os.path.join("data", "login_history.csv")
    print("Đang khởi tạo cấu trúc thư mục và sinh dữ liệu lịch sử đăng nhập...")
    df = generate_dataset(3000, 0.03)
    df.to_csv(csv_path, index=False)
    print(f"Đã tạo dữ liệu thành công tại {csv_path} với {len(df)} bản ghi.")
    print(f"Số bản ghi bình thường: {len(df[df['is_anomaly'] == False])}")
    print(f"Số bản ghi bất thường: {len(df[df['is_anomaly'] == True])}")
    print("\nThống kê các loại bất thường:")
    print(df[df['is_anomaly'] == True]['anomaly_type'].value_counts())
