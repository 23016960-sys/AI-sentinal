import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import math
from data_generator import haversine_distance

class AnomalyDetector:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "isolation_forest.joblib")
        self.scaler_path = os.path.join(model_dir, "scaler.joblib")
        self.baselines_path = os.path.join(model_dir, "user_baselines.joblib")
        
        self.model = None
        self.scaler = None
        self.user_baselines = {}
        self.features_list = [
            "dist_from_centroid",
            "travel_speed",
            "is_new_os",
            "is_new_browser",
            "hour_sin",
            "hour_cos",
            "day_of_week",
            "consecutive_failures",
            "is_failed"
        ]

    def build_user_baselines(self, df):
        """
        Xây dựng cấu hình hành vi chuẩn (baseline) cho từng người dùng từ dữ liệu lịch sử bình thường.
        """
        # Lọc dữ liệu bình thường để xây dựng baseline
        df_normal = df[df["is_anomaly"] == False].copy()
        df_normal["timestamp_dt"] = pd.to_datetime(df_normal["timestamp"])
        df_normal = df_normal.sort_values(by="timestamp_dt")
        
        baselines = {}
        
        for username, group in df_normal.groupby("username"):
            # Tính tọa độ trung tâm (centroid)
            centroid_lat = group["latitude"].mean()
            centroid_lon = group["longitude"].mean()
            
            # Danh sách hệ điều hành và trình duyệt đã biết
            known_os = set(group["device_os"].unique())
            known_browsers = set(group["device_browser"].unique())
            
            # Lần đăng nhập cuối cùng (để phục vụ tính toán impossible travel)
            last_record = group.iloc[-1]
            last_login_coords = (float(last_record["latitude"]), float(last_record["longitude"]))
            last_login_time = last_record["timestamp_dt"].strftime("%Y-%m-%d %H:%M:%S")
            
            baselines[username] = {
                "centroid_lat": float(centroid_lat),
                "centroid_lon": float(centroid_lon),
                "known_os": list(known_os),
                "known_browsers": list(known_browsers),
                "last_login_coords": last_login_coords,
                "last_login_time": last_login_time
            }
            
        self.user_baselines = baselines
        return baselines

    def calculate_record_features(self, row, user_baselines, prev_login_dict=None):
        """
        Tính toán các đặc trưng (features) cho một dòng đăng nhập đơn lẻ dựa trên baseline của user.
        """
        username = row["username"]
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        timestamp = pd.to_datetime(row["timestamp"])
        os_name = row["device_os"]
        browser_name = row["device_browser"]
        status = row["login_status"]
        consecutive_failures = int(row["consecutive_failures"])
        
        # Mặc định nếu user mới chưa có baseline
        dist_from_centroid = 0.0
        travel_speed = 0.0
        is_new_os = 0
        is_new_browser = 0
        
        if username in user_baselines:
            ub = user_baselines[username]
            # 1. Khoảng cách tới centroid
            dist_from_centroid = haversine_distance(lat, lon, ub["centroid_lat"], ub["centroid_lon"])
            
            # 2. Thiết bị mới
            if os_name not in ub["known_os"]:
                is_new_os = 1
            if browser_name not in ub["known_browsers"]:
                is_new_browser = 1
                
            # 3. Vận tốc di chuyển (travel speed)
            # Lấy thông tin đăng nhập trước đó từ tham số truyền vào hoặc baseline
            prev_coords = None
            prev_time_str = None
            
            if prev_login_dict and username in prev_login_dict:
                prev_coords = prev_login_dict[username]["coords"]
                prev_time_str = prev_login_dict[username]["time"]
            elif ub["last_login_coords"] and ub["last_login_time"]:
                prev_coords = ub["last_login_coords"]
                prev_time_str = ub["last_login_time"]
                
            if prev_coords and prev_time_str:
                prev_time = pd.to_datetime(prev_time_str)
                time_diff = (timestamp - prev_time).total_seconds() / 3600.0 # đổi sang giờ
                
                if time_diff > 0:
                    distance = haversine_distance(lat, lon, prev_coords[0], prev_coords[1])
                    travel_speed = distance / time_diff
                else:
                    travel_speed = 0.0
        
        # 4. Đặc trưng thời gian
        hour_val = timestamp.hour + timestamp.minute / 60.0
        hour_sin = math.sin(2 * math.pi * hour_val / 24.0)
        hour_cos = math.cos(2 * math.pi * hour_val / 24.0)
        day_of_week = timestamp.dayofweek
        
        # 5. Trạng thái đăng nhập lỗi
        is_failed = 1 if status == "failed" else 0
        
        return {
            "dist_from_centroid": dist_from_centroid,
            "travel_speed": travel_speed,
            "is_new_os": is_new_os,
            "is_new_browser": is_new_browser,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "day_of_week": day_of_week,
            "consecutive_failures": consecutive_failures,
            "is_failed": is_failed
        }

    def prepare_training_features(self, df):
        """
        Trích xuất đặc trưng cho toàn bộ dataset để huấn luyện.
        """
        # Cần sắp xếp theo thời gian tăng dần để tính toán running travel speed chính xác
        df_sorted = df.sort_values(by="timestamp").copy()
        
        # Tạo bản đồ lưu lượt đăng nhập gần nhất của từng user khi duyệt qua dữ liệu
        prev_logins = {}
        features_data = []
        
        for idx, row in df_sorted.iterrows():
            username = row["username"]
            
            # Tính đặc trưng dựa trên trạng thái baselines hiện tại
            feats = self.calculate_record_features(row, self.user_baselines, prev_logins)
            features_data.append(feats)
            
            # Cập nhật thông tin đăng nhập gần nhất của user này (chỉ khi đăng nhập thành công để tránh hacker di chuyển IP ảo liên tục)
            if row["login_status"] == "success":
                prev_logins[username] = {
                    "coords": (float(row["latitude"]), float(row["longitude"])),
                    "time": row["timestamp"]
                }
                
        return pd.DataFrame(features_data)

    def train(self, csv_path, contamination=0.03):
        """
        Huấn luyện mô hình Isolation Forest từ dữ liệu lịch sử đăng nhập.
        """
        print(f"Reading training data from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # 1. Xây dựng baselines cho người dùng từ các lần đăng nhập bình thường
        print("Analyzing user baselines...")
        self.build_user_baselines(df)
        
        # 2. Chuẩn bị đặc trưng
        print("Extracting features...")
        X = self.prepare_training_features(df)
        
        # Lọc ra các dòng thuộc nhãn bình thường để huấn luyện mô hình (Semi-supervised approach)
        # Isolation Forest có thể tự lọc nhiễu, nhưng huấn luyện trên tập chủ yếu bình thường giúp mô hình nhạy bén hơn.
        df_normal_idx = df[df["is_anomaly"] == False].index
        X_train = X.iloc[df_normal_idx].copy()
        
        # 3. Huấn luyện Isolation Forest
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        
        print("Scaling data...")
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train[self.features_list])
        
        print("Training Isolation Forest model...")
        self.model = IsolationForest(
            n_estimators=150,
            contamination=contamination,
            random_state=42,
            bootstrap=True,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled)
        
        # Đo lường và tính toán scaler cho điểm rủi ro (risk score)
        # decision_function trả về giá trị âm cho bất thường và dương cho bình thường
        decisions_train = self.model.decision_function(X_train_scaled)
        self.min_decision = float(np.min(decisions_train))
        self.max_decision = float(np.max(decisions_train))
        
        # Lưu mô hình và cấu hình
        self.save_model()
        
        # Đánh giá nhanh trên toàn bộ tập dữ liệu (bao gồm cả dữ liệu bất thường)
        X_all_scaled = self.scaler.transform(X[self.features_list])
        preds = self.model.predict(X_all_scaled) # 1: normal, -1: anomaly
        df["ml_pred"] = preds
        df["ml_pred"] = df["ml_pred"].map({1: False, -1: True})
        
        # Thống kê hiệu năng mô hình
        from sklearn.metrics import classification_report, confusion_matrix
        print("\nML model classification report:")
        print(classification_report(df["is_anomaly"], df["ml_pred"]))
        
        cm = confusion_matrix(df["is_anomaly"], df["ml_pred"])
        
        # Tính toán Feature Importance (bằng cách tính sai lệch điểm quyết định khi xáo trộn từng đặc trưng)
        feature_importance = {}
        baseline_score = np.mean(self.model.decision_function(X_all_scaled))
        for feat in self.features_list:
            X_temp = X_all_scaled.copy()
            feat_idx = self.features_list.index(feat)
            np.random.shuffle(X_temp[:, feat_idx])
            shuffled_score = np.mean(self.model.decision_function(X_temp))
            # Độ sai lệch càng lớn tức đặc trưng đó càng quan trọng
            feature_importance[feat] = float(abs(baseline_score - shuffled_score))
            
        # Chuẩn hóa độ quan trọng về dạng phần trăm
        total_imp = sum(feature_importance.values())
        if total_imp > 0:
            feature_importance = {k: round((v / total_imp) * 100, 2) for k, v in feature_importance.items()}
            
        print("Feature importances (%):", feature_importance)
        
        return {
            "confusion_matrix": cm.tolist(),
            "feature_importance": feature_importance,
            "accuracy": float(np.mean(df["is_anomaly"] == df["ml_pred"])),
            "anomaly_rate": float(np.mean(df["ml_pred"]))
        }

    def save_model(self):
        os.makedirs(self.model_dir, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        
        # Lưu kèm thông số scale điểm quyết định
        baselines_data = {
            "baselines": self.user_baselines,
            "min_decision": getattr(self, "min_decision", -0.5),
            "max_decision": getattr(self, "max_decision", 0.5)
        }
        joblib.dump(baselines_data, self.baselines_path)
        print(f"Model saved successfully at {self.model_dir}/")

    def load_model(self):
        if not (os.path.exists(self.model_path) and os.path.exists(self.scaler_path) and os.path.exists(self.baselines_path)):
            return False
        
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            
            baselines_data = joblib.load(self.baselines_path)
            self.user_baselines = baselines_data["baselines"]
            self.min_decision = baselines_data["min_decision"]
            self.max_decision = baselines_data["max_decision"]
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def predict_login(self, login_event, rules_config=None):
        """
        Dự đoán mức độ bất thường của một sự kiện đăng nhập mới.
        Kích hoạt cơ chế kết hợp Heuristic Rules + Machine Learning.
        """
        if rules_config is None:
            rules_config = {
                "enable_ml": True,
                "enable_impossible_travel": True,
                "enable_brute_force": True,
                "ml_threshold": 65  # Ngưỡng Risk Score (0-100) để đánh dấu bất thường
            }
            
        username = login_event["username"]
        
        # Tải mô hình nếu chưa được tải
        if self.model is None:
            loaded = self.load_model()
            if not loaded:
                return {
                    "is_anomaly": False,
                    "risk_score": 0,
                    "risk_level": "UNKNOWN",
                    "reasons": ["Mô hình học máy chưa được huấn luyện."],
                    "features": {}
                }
                
        # 1. Trích xuất đặc trưng của sự kiện này
        feats = self.calculate_record_features(login_event, self.user_baselines)
        
        # 2. Kiểm tra các Quy tắc Bảo mật Cứng (Heuristic Rules) trước
        reasons = []
        is_anomaly = False
        risk_level = "LOW"
        risk_score = 10
        
        # Quy tắc 1: Phát hiện Brute-force / Tấn công dò mật khẩu
        if rules_config.get("enable_brute_force") and feats["consecutive_failures"] >= 5:
            is_anomaly = True
            risk_score = min(50 + feats["consecutive_failures"] * 8, 100)
            risk_level = "CRITICAL"
            reasons.append(f"Cảnh báo Brute-force: Phát hiện {feats['consecutive_failures']} lần đăng nhập lỗi liên tiếp.")
            
        # Quy tắc 2: Phát hiện Impossible Travel (Di chuyển bất khả thi)
        if rules_config.get("enable_impossible_travel") and feats["travel_speed"] > 800.0 and feats["dist_from_centroid"] > 100.0:
            is_anomaly = True
            risk_score = max(risk_score, 95)
            risk_level = "CRITICAL"
            reasons.append(f"Phát hiện di chuyển bất khả thi: Vận tốc tính toán giữa các lần đăng nhập đạt {feats['travel_speed']:.1f} km/h (Vượt ngưỡng phản cơ học 800 km/h).")

        # 3. Đánh giá bằng Học Máy (Isolation Forest)
        ml_anomaly = False
        ml_risk_score = 0
        
        if rules_config.get("enable_ml"):
            # Chuyển đặc trưng thành vector đầu vào
            feat_df = pd.DataFrame([feats])[self.features_list]
            feat_scaled = self.scaler.transform(feat_df)
            
            # Tính điểm quyết định
            decision_val = float(self.model.decision_function(feat_scaled)[0])
            
            # Scale điểm quyết định sang dạng Risk Score từ 0 đến 100
            # decision_val càng âm thì càng bất thường -> Risk Score càng cao
            # Sử dụng min_decision và max_decision đã lưu để scale tuyến tính nghịch
            range_val = self.max_decision - self.min_decision
            if range_val > 0:
                # Chuẩn hóa score về 0 -> 1 (0: an toàn nhất, 1: bất thường nhất)
                normalized_score = (self.max_decision - decision_val) / range_val
                # Điều hướng nhẹ bằng hàm sigmoid hoặc mũ để nhạy bén hơn ở cận bất thường
                ml_risk_score = int(min(max(normalized_score * 100, 0), 100))
            else:
                ml_risk_score = 50
                
            # Đánh giá xem có bất thường theo ML không dựa trên ngưỡng người dùng cấu hình
            ml_threshold = rules_config.get("ml_threshold", 65)
            if ml_risk_score >= ml_threshold:
                ml_anomaly = True
                
            # Phân tích nguyên nhân bất thường từ mô hình ML (giải thích đặc trưng đóng góp lớn nhất)
            if ml_anomaly and not is_anomaly:
                is_anomaly = True
                risk_score = max(risk_score, ml_risk_score)
                
                # Xác định các yếu tố bất thường dựa trên độ lệch so với thông thường
                if feats["dist_from_centroid"] > 200.0:
                    reasons.append(f"Vị trí đăng nhập xa thói quen lịch sử: Cách vị trí thường lệ {feats['dist_from_centroid']:.1f} km.")
                if feats["is_new_os"] == 1:
                    reasons.append(f"Hệ điều hành thiết bị mới lạ ({login_event.get('device_os')}).")
                if feats["is_new_browser"] == 1:
                    reasons.append(f"Trình duyệt mới lạ ({login_event.get('device_browser')}).")
                # Kiểm tra thời gian bất thường: so sánh sin/cos giờ hoặc đơn giản là giờ đêm
                timestamp_dt = pd.to_datetime(login_event["timestamp"])
                if username in self.user_baselines:
                    # Kiểm tra xem giờ đăng nhập có nằm trong typical hours không
                    hour = timestamp_dt.hour
                    in_typical = False
                    for start, end in self.user_baselines[username].get("typical_hours", [(8, 18)]):
                        if end < start: # Qua đêm
                            if hour >= start or hour < end:
                                in_typical = True
                        else:
                            if start <= hour < end:
                                in_typical = True
                    if not in_typical:
                        reasons.append(f"Thời gian đăng nhập lạ: Đăng nhập lúc {timestamp_dt.strftime('%H:%M')} không nằm trong khung giờ hoạt động thường ngày.")
                        
        # Đánh giá mức độ rủi ro tổng hợp
        if is_anomaly:
            if risk_score >= 85:
                risk_level = "CRITICAL"
            else:
                risk_level = "SUSPICIOUS"
        else:
            risk_score = max(risk_score, ml_risk_score)
            if risk_score >= 45:
                risk_level = "SUSPICIOUS"
            else:
                risk_level = "LOW"
                
        if not reasons:
            if is_anomaly:
                reasons.append("Phát hiện bất thường tổng hợp từ thuật toán Isolation Forest.")
            else:
                reasons.append("Hoạt động đăng nhập khớp với hành vi chuẩn của người dùng.")
                
        return {
            "is_anomaly": is_anomaly,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reasons": reasons,
            "features": {k: float(v) for k, v in feats.items()}
        }

    def update_user_baseline_live(self, login_event, is_anomaly=False):
        """
        Cập nhật trực tiếp baseline của người dùng sau một lượt đăng nhập thành công an toàn.
        Điều này giúp hệ thống học thích ứng (adaptive learning) theo thời gian.
        """
        username = login_event["username"]
        if login_event["login_status"] != "success" or is_anomaly:
            # Không cập nhật thói quen nếu đăng nhập lỗi hoặc bị phát hiện bất thường
            return
            
        lat = float(login_event["latitude"])
        lon = float(login_event["longitude"])
        os_name = login_event["device_os"]
        browser_name = login_event["device_browser"]
        timestamp = login_event["timestamp"]
        
        if username not in self.user_baselines:
            # Tạo mới baseline nếu là user hoàn toàn mới
            self.user_baselines[username] = {
                "centroid_lat": lat,
                "centroid_lon": lon,
                "known_os": [os_name],
                "known_browsers": [browser_name],
                "last_login_coords": (lat, lon),
                "last_login_time": timestamp,
                "typical_hours": [(8, 18)] # Mặc định
            }
        else:
            ub = self.user_baselines[username]
            # Cập nhật nhẹ tọa độ trung tâm (trọng số 0.95 cũ, 0.05 mới)
            ub["centroid_lat"] = ub["centroid_lat"] * 0.98 + lat * 0.02
            ub["centroid_lon"] = ub["centroid_lon"] * 0.98 + lon * 0.02
            
            # Thêm thiết bị mới vào danh sách thiết bị tin cậy nếu đăng nhập thành công an toàn
            if os_name not in ub["known_os"]:
                ub["known_os"].append(os_name)
            if browser_name not in ub["known_browsers"]:
                ub["known_browsers"].append(browser_name)
                
            # Cập nhật lần đăng nhập cuối cùng
            ub["last_login_coords"] = (lat, lon)
            ub["last_login_time"] = timestamp
            
        # Thỉnh thoảng lưu lại cấu hình baselines để đồng bộ
        # Để tránh ghi đĩa quá nhiều, ta sẽ lưu lại trong app.py khi cần thiết.

if __name__ == "__main__":
    # Test nhanh quá trình huấn luyện
    detector = AnomalyDetector()
    csv_path = os.path.join("data", "login_history.csv")
    if os.path.exists(csv_path):
        results = detector.train(csv_path)
        print("Test training completed.")
    else:
        print(f"Data not found at {csv_path}. Please run data_generator.py first.")
