import pandas as pd
import time
from anomaly_detector import AnomalyDetector

detector = AnomalyDetector()
start = time.time()
print("Reading CSV...")
df = pd.read_csv("data/login_history.csv")
print(f"Read CSV in {time.time() - start:.3f}s. Rows: {len(df)}")

start = time.time()
detector.build_user_baselines(df)
print(f"Built user baselines in {time.time() - start:.3f}s")

start = time.time()
# Profile prepare_training_features
df_sorted = df.sort_values(by="timestamp").copy()
prev_logins = {}
features_data = []

print("Starting loop...")
loop_start = time.time()
for idx, row in df_sorted.iterrows():
    if idx % 500 == 0:
        print(f"Processed {idx} rows in {time.time() - loop_start:.3f}s")
        loop_start = time.time()
    feats = detector.calculate_record_features(row, detector.user_baselines, prev_logins)
    features_data.append(feats)
    if row["login_status"] == "success":
        prev_logins[row["username"]] = {
            "coords": (float(row["latitude"]), float(row["longitude"])),
            "time": row["timestamp"]
        }
print(f"Loop finished in {time.time() - start:.3f}s")
