"""
Configuration settings for Flood Management System
"""
import os
from pathlib import Path

# Base directory (app/config.py -> app/ -> project root)
BASE_DIR = Path(__file__).parent.parent

# API Keys
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
MAP_API_KEY = os.getenv("MAP_API_KEY", "")  # For future map services

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/flood_data.db")

# Model paths
MODEL_PATH = BASE_DIR / "models" / "baseline_random_forest.pkl"
DATA_PATH = BASE_DIR / "data" / "sample_chennai_like_rainfall.csv"
WARD_RISK_PATH = BASE_DIR / "risk_by_ward.csv"

# Data Collection Settings
COLLECTION_INTERVAL_MINUTES = int(os.getenv("COLLECTION_INTERVAL_MINUTES", "30"))
WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL", "900"))  # 15 minutes

# Chennai Coordinates (default location)
CHENNAI_LAT = 13.0827
CHENNAI_LON = 80.2707

# Risk Level Thresholds
RISK_THRESHOLDS = {
    "low": 0.0,
    "moderate": 0.3,
    "high": 0.6,
    "critical": 0.8
}

# API Settings
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

