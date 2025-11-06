
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
from pathlib import Path

DATA_PATH = Path("data/sample_chennai_like_rainfall.csv")
MODEL_PATH = Path("models/baseline_random_forest.pkl")

df = pd.read_csv(DATA_PATH)
X = df.drop(columns=["flooded"])
y = df["flooded"]

model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42, class_weight="balanced")
model.fit(X, y)

joblib.dump({"model": model, "features": list(X.columns)}, MODEL_PATH)
print(f"✅ Model retrained and saved to {MODEL_PATH}")
