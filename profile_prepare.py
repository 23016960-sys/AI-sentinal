import pandas as pd
import time
from anomaly_detector import AnomalyDetector

detector = AnomalyDetector()
df = pd.read_csv("data/login_history.csv")
detector.build_user_baselines(df)

start = time.time()
print("Calling prepare_training_features...")
X = detector.prepare_training_features(df)
print(f"prepare_training_features completed in {time.time() - start:.3f}s. Shape: {X.shape}")

print("Scaling data...")
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X[detector.features_list])
print("Scaling completed.")

print("Training Isolation Forest...")
from sklearn.ensemble import IsolationForest
model = IsolationForest(
    n_estimators=150,
    contamination=0.03,
    random_state=42,
    bootstrap=True,
    n_jobs=-1
)
model.fit(X_scaled)
print("Isolation Forest training completed.")
