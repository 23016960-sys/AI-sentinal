# AI Sentinel - Hệ thống phát hiện đăng nhập bất thường

AI Sentinel là một ứng dụng demo giám sát đăng nhập, dùng kết hợp Machine Learning và các luật bảo mật để phát hiện các hành vi bất thường như đăng nhập từ vị trí lạ, thiết bị lạ, brute force hoặc "impossible travel".

Ứng dụng gồm backend FastAPI, mô hình Isolation Forest của scikit-learn, dữ liệu lịch sử dạng CSV và giao diện dashboard web để quan sát log, bản đồ, biểu đồ, thử nghiệm sự kiện đăng nhập và huấn luyện lại mô hình.

## Ý chính cần nắm

### 1. Luồng hoạt động tổng thể

1. `data_generator.py` sinh dữ liệu lịch sử đăng nhập vào `data/login_history.csv`.
2. `anomaly_detector.py` đọc dữ liệu, xây dựng baseline hành vi cho từng user và huấn luyện mô hình Isolation Forest.
3. `app.py` khởi chạy FastAPI, load hoặc train model, sau đó phục vụ API và giao diện web.
4. Frontend trong `templates/index.html`, `static/css/style.css`, `static/js/app.js` gọi API để hiển thị dashboard, mô phỏng đăng nhập và cấu hình chính sách phát hiện.

### 2. Cách hệ thống phát hiện bất thường

Hệ thống dùng mô hình lai:

- Machine Learning: Isolation Forest học các mẫu đăng nhập bình thường dựa trên đặc trưng đã chuẩn hóa.
- Rule-based: các luật rõ ràng được áp dụng trực tiếp cho những tình huống nguy hiểm.

Các đặc trưng chính được đưa vào mô hình:

- `dist_from_centroid`: khoảng cách từ vị trí đăng nhập tới vị trí thường lệ của user.
- `travel_speed`: vận tốc di chuyển ước tính giữa hai lần đăng nhập.
- `is_new_os`: hệ điều hành mới so với lịch sử của user.
- `is_new_browser`: trình duyệt mới so với lịch sử của user.
- `hour_sin`, `hour_cos`: biểu diễn chu kỳ giờ đăng nhập trong ngày.
- `day_of_week`: ngày trong tuần.
- `consecutive_failures`: số lần đăng nhập sai liên tiếp.
- `is_failed`: trạng thái đăng nhập thất bại hay thành công.

Các luật bảo mật nổi bật:

- Brute force: nếu `consecutive_failures >= 5`, hệ thống đánh dấu mức `CRITICAL`.
- Impossible travel: nếu vận tốc di chuyển lớn hơn 800 km/h và vị trí cách xa baseline, hệ thống đánh dấu mức `CRITICAL`.
- ML threshold: nếu điểm rủi ro từ mô hình vượt ngưỡng cấu hình, hệ thống đánh dấu bất thường.

Kết quả phân tích trả về gồm:

- `is_anomaly`: có bất thường hay không.
- `risk_score`: điểm rủi ro từ 0 đến 100.
- `risk_level`: `LOW`, `SUSPICIOUS` hoặc `CRITICAL`.
- `reasons`: giải thích vì sao sự kiện bị đánh dấu.
- `features`: các đặc trưng đã tính toán.

### 3. Giao diện web

Giao diện chính có 3 phần:

- Dashboard: xem tổng lượt đăng nhập, số bất thường, chỉ số rủi ro, thiết bị, bản đồ vị trí đăng nhập, biểu đồ hệ điều hành và bảng log gần đây.
- Playground: nhập thủ công một sự kiện đăng nhập để xem hệ thống chấm điểm và giải thích.
- Cấu hình & mô hình: bật/tắt ML, bật/tắt luật impossible travel, bật/tắt luật brute force, chỉnh ngưỡng ML và huấn luyện lại mô hình.

## Cấu trúc dự án

```text
.
├── app.py                    # FastAPI backend, API endpoints, startup model, cache recent logs
├── anomaly_detector.py       # Feature engineering, user baseline, train/load/predict model
├── data_generator.py         # Sinh dữ liệu đăng nhập mẫu và các kịch bản bất thường
├── profile_features.py       # Script profiling bước trích xuất đặc trưng
├── profile_prepare.py        # Script profiling bước chuẩn bị dữ liệu
├── profile_train.py          # Script profiling bước huấn luyện
├── data/
│   └── login_history.csv     # Dữ liệu lịch sử đăng nhập
├── models/
│   ├── isolation_forest.joblib
│   ├── scaler.joblib
│   └── user_baselines.joblib
├── templates/
│   └── index.html            # Trang dashboard chính
├── static/
│   ├── css/style.css         # Giao diện
│   └── js/app.js             # Logic gọi API, map, chart, playground
└── README.md
```

## Công nghệ sử dụng

- Python
- FastAPI
- Uvicorn
- Pandas, NumPy
- scikit-learn
- Joblib
- HTML, CSS, JavaScript
- Leaflet.js cho bản đồ
- Chart.js cho biểu đồ

## Cài đặt

Tạo môi trường ảo nếu cần:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Cài thư viện:

```powershell
pip install fastapi uvicorn pandas numpy scikit-learn joblib
```

## Chạy dự án

### 1. Sinh dữ liệu mẫu

Chạy lệnh này nếu chưa có `data/login_history.csv` hoặc muốn tạo lại dữ liệu:

```powershell
python data_generator.py
```

Script sẽ tạo khoảng 3000 bản ghi đăng nhập, gồm dữ liệu bình thường và một tỷ lệ nhỏ dữ liệu bất thường.

### 2. Huấn luyện mô hình

Có thể huấn luyện trực tiếp bằng:

```powershell
python anomaly_detector.py
```

Hoặc chỉ cần chạy server. Khi khởi động, `app.py` sẽ cố load model trong `models/`; nếu chưa có model và đã có CSV, hệ thống sẽ tự huấn luyện.

### 3. Khởi chạy server

```powershell
python -m uvicorn app:app --reload
```

Mở trình duyệt tại:

```text
http://127.0.0.1:8000
```

## API chính

### `GET /`

Trả về giao diện dashboard.

### `GET /api/status`

Trả về trạng thái sẵn sàng của hệ thống ML.

### `GET /api/logs?limit=100`

Lấy danh sách log đăng nhập gần đây.

### `GET /api/stats`

Lấy số liệu tổng hợp cho dashboard: tổng login, số bất thường, risk index, thiết bị, phân bố OS/browser, dữ liệu bản đồ và biểu đồ hoạt động.

### `POST /api/predict`

Chấm điểm một sự kiện đăng nhập mới.

Ví dụ payload:

```json
{
  "username": "nguyen_van_a",
  "ip_address": "113.190.23.104",
  "latitude": 21.0285,
  "longitude": 105.8542,
  "city": "Hanoi",
  "country": "Vietnam",
  "device_os": "Windows",
  "device_browser": "Chrome",
  "login_status": "success",
  "consecutive_failures": 0,
  "user_agent": "Manual Entry/Playground"
}
```

### `POST /api/simulate`

Sinh một sự kiện đăng nhập giả lập và chấm điểm ngay.

Ví dụ payload:

```json
{
  "anomaly_type": "impossible_travel"
}
```

Các giá trị thường dùng:

- `random`
- `none`
- `unusual_location`
- `unusual_time`
- `new_device`
- `brute_force`
- `impossible_travel`

### `POST /api/train`

Huấn luyện lại mô hình từ `data/login_history.csv`.

Ví dụ:

```json
{
  "contamination": 0.03
}
```

### `GET /api/settings`

Lấy cấu hình detection hiện tại.

### `POST /api/settings`

Cập nhật cấu hình detection.

Ví dụ:

```json
{
  "enable_ml": true,
  "enable_impossible_travel": true,
  "enable_brute_force": true,
  "ml_threshold": 65
}
```

## Dữ liệu mẫu

`data_generator.py` định nghĩa 5 user mẫu:

- `nguyen_van_a`
- `tran_thi_b`
- `le_hoang_c`
- `pham_minh_d`
- `security_audit`

Mỗi user có thành phố thường dùng, khung giờ hoạt động, thiết bị quen thuộc và tỷ lệ đăng nhập sai riêng. Các kịch bản bất thường được sinh gồm vị trí lạ, giờ lạ, thiết bị lạ, brute force và impossible travel.

## Lưu ý khi phát triển

- File hiện tại không có `requirements.txt`, nên README liệt kê lệnh cài thư viện trực tiếp.
- Frontend dùng CDN cho Leaflet, Chart.js và Google Fonts, vì vậy cần có mạng để tải đầy đủ giao diện bản đồ/biểu đồ khi chạy lần đầu.
- Một số file nguồn hiện có dấu hiệu bị lỗi encoding ở phần text/comment tiếng Việt. README này đã được ghi lại bằng UTF-8 để dễ đọc hơn.
- Dữ liệu mới từ `/api/predict` và `/api/simulate` được append vào `data/login_history.csv`.
- `recent_logs` chỉ là cache trong RAM, tối đa 150 log gần nhất; khi restart server, app sẽ nạp lại khoảng 100 bản ghi cuối từ CSV.
