import time
from anomaly_detector import AnomalyDetector

detector = AnomalyDetector()
start = time.time()
print("Starting training...")
results = detector.train("data/login_history.csv")
print(f"Training completed in {time.time() - start:.3f}s")
print("Results:", results)
