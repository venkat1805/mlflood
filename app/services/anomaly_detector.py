"""
Anomaly detection service for unusual rainfall patterns
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import joblib
from pathlib import Path

from app.database import SessionLocal, RainfallObservation


class AnomalyDetector:
    """Detect unusual rainfall patterns that may indicate flood risk"""
    
    def __init__(self, contamination: float = 0.1):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = [
            'rain_mm',
            'rain_sum_3h',
            'rain_sum_24h',
            'rain_max_3h',
            'rain_trend'
        ]
    
    def fit(self, historical_data: pd.DataFrame):
        """
        Train anomaly detector on historical data
        
        Args:
            historical_data: DataFrame with rainfall observations
        """
        # Extract features
        features_df = historical_data[self.feature_names].copy()
        
        # Handle missing values
        features_df = features_df.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(features_df)
        
        # Train model
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        print(f"✅ Anomaly detector trained on {len(features_df)} samples")
    
    def detect(self, current_data: Dict) -> Dict:
        """
        Detect if current data is anomalous
        
        Args:
            current_data: Dictionary with current weather/rainfall data
        
        Returns:
            Dictionary with anomaly detection results
        """
        if not self.is_fitted:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "severity": "unknown",
                "message": "Anomaly detector not trained"
            }
        
        # Extract features
        features = np.array([[
            current_data.get('rain_mm', 0),
            current_data.get('rain_sum_3h', 0),
            current_data.get('rain_sum_24h', 0),
            current_data.get('rain_max_3h', 0),
            current_data.get('rain_trend', 0)
        ]])
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict anomaly
        anomaly_score = self.model.score_samples(features_scaled)[0]
        is_anomaly = self.model.predict(features_scaled)[0] == -1
        
        # Determine severity
        if is_anomaly:
            if anomaly_score < -0.5:
                severity = "critical"
                message = "Extreme anomaly detected - unusual rainfall pattern"
            elif anomaly_score < -0.3:
                severity = "high"
                message = "Significant anomaly detected - unusual rainfall pattern"
            else:
                severity = "moderate"
                message = "Moderate anomaly detected - unusual rainfall pattern"
        else:
            severity = "low"
            message = "Normal rainfall pattern"
        
        return {
            "anomaly_score": float(anomaly_score),
            "is_anomaly": bool(is_anomaly),
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def detect_sudden_spike(self, current_rain: float, recent_avg: float, threshold: float = 2.0) -> Dict:
        """
        Detect sudden spike in rainfall
        
        Args:
            current_rain: Current rainfall (mm)
            recent_avg: Average rainfall in recent period (mm)
            threshold: Multiplier threshold for spike detection
        
        Returns:
            Dictionary with spike detection results
        """
        if recent_avg == 0:
            recent_avg = 0.1  # Avoid division by zero
        
        ratio = current_rain / recent_avg
        
        is_spike = ratio >= threshold
        
        return {
            "is_spike": is_spike,
            "spike_ratio": float(ratio),
            "current_rain": float(current_rain),
            "recent_avg": float(recent_avg),
            "threshold": threshold,
            "severity": "high" if ratio >= threshold * 2 else "moderate" if is_spike else "low"
        }
    
    def save(self, path: Path):
        """Save trained model"""
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names
        }, path)
        print(f"✅ Anomaly detector saved to {path}")
    
    def load(self, path: Path):
        """Load trained model"""
        data = joblib.load(path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.is_fitted = data["is_fitted"]
        self.feature_names = data["feature_names"]
        print(f"✅ Anomaly detector loaded from {path}")


def train_anomaly_detector(db_session=None, min_samples: int = 100):
    """
    Train anomaly detector on historical data
    
    Args:
        db_session: Database session (optional)
        min_samples: Minimum samples required for training
    """
    detector = AnomalyDetector()
    
    if db_session:
        # Get data from database
        observations = db_session.query(RainfallObservation).filter(
            RainfallObservation.timestamp >= datetime.now() - timedelta(days=30)
        ).all()
        
        if len(observations) < min_samples:
            print(f"⚠️  Not enough data for training ({len(observations)} < {min_samples})")
            return None
        
        # Convert to DataFrame
        data = []
        for obs in observations:
            data.append({
                'rain_mm': obs.rain_mm,
                'rain_sum_3h': obs.rain_sum_3h,
                'rain_sum_24h': obs.rain_sum_24h,
                'rain_max_3h': obs.rain_max_3h,
                'rain_trend': (obs.rain_sum_3h - obs.rain_sum_12h) / (obs.rain_sum_12h + 1) if obs.rain_sum_12h else 0
            })
        df = pd.DataFrame(data)
    else:
        # Use CSV data
        from app.config import DATA_PATH
        df = pd.read_csv(DATA_PATH)
        df['rain_trend'] = (df['rain_sum_3h'] - df['rain_sum_12h']) / (df['rain_sum_12h'] + 1)
    
    detector.fit(df)
    return detector

