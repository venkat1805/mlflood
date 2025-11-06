# 🚀 Step-by-Step Implementation Guide

## Current State → Goal: Practical Implementation Steps

This guide provides concrete, actionable steps to transform your baseline system into the full flood detection and early warning framework.

---

## 🎯 PHASE 1: Data Infrastructure (START HERE)

### Step 1.1: Set Up Database

**Why**: Store historical data, real-time observations, and enable efficient queries

**Action Items**:

1. **Choose Database**
   - **Option A (Quick Start)**: SQLite - No setup needed, file-based
   - **Option B (Production)**: PostgreSQL - Better for concurrent access

2. **Create Database Schema**

   Create file: `app/database.py`
   ```python
   from sqlalchemy import create_engine, Column, Float, Integer, String, DateTime, Boolean
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import sessionmaker
   from datetime import datetime
   
   Base = declarative_base()
   
   class RainfallObservation(Base):
       __tablename__ = "rainfall_observations"
       id = Column(Integer, primary_key=True)
       timestamp = Column(DateTime, default=datetime.utcnow)
       location = Column(String)  # Ward name or coordinates
       lat = Column(Float)
       lon = Column(Float)
       rain_mm = Column(Float)
       rain_sum_1h = Column(Float)
       rain_sum_3h = Column(Float)
       rain_sum_6h = Column(Float)
       rain_sum_12h = Column(Float)
       rain_sum_24h = Column(Float)
       rain_max_3h = Column(Float)
       rain_max_6h = Column(Float)
       humidity_pct = Column(Float)
       temp_c = Column(Float)
       flooded = Column(Boolean)  # Ground truth if available
   
   class WardRisk(Base):
       __tablename__ = "ward_risks"
       id = Column(Integer, primary_key=True)
       ward_id = Column(Integer, unique=True)
       ward_name = Column(String)
       lat = Column(Float)
       lon = Column(Float)
       risk_score = Column(Float)
       last_updated = Column(DateTime, default=datetime.utcnow)
   
   # SQLite setup
   engine = create_engine("sqlite:///flood_data.db")
   SessionLocal = sessionmaker(bind=engine)
   
   def init_db():
       Base.metadata.create_all(engine)
   ```

3. **Migrate Existing CSV to Database**

   Create file: `scripts/migrate_csv_to_db.py`
   ```python
   import pandas as pd
   from app.database import SessionLocal, RainfallObservation, init_db
   from datetime import datetime
   
   def migrate_csv():
       init_db()
       db = SessionLocal()
       
       # Read existing CSV
       df = pd.read_csv("data/sample_chennai_like_rainfall.csv")
       
       # Add default coordinates (Chennai center) if not in CSV
       for _, row in df.iterrows():
           obs = RainfallObservation(
               timestamp=datetime.now(),  # Or parse from CSV if available
               location="Chennai",
               lat=13.0827,  # Default Chennai coordinates
               lon=80.2707,
               rain_mm=row['rain_mm'],
               rain_sum_1h=row['rain_sum_1h'],
               rain_sum_3h=row['rain_sum_3h'],
               rain_sum_6h=row['rain_sum_6h'],
               rain_sum_12h=row['rain_sum_12h'],
               rain_sum_24h=row['rain_sum_24h'],
               rain_max_3h=row['rain_max_3h'],
               rain_max_6h=row['rain_max_6h'],
               humidity_pct=row['humidity_pct'],
               temp_c=row['temp_c'],
               flooded=bool(row['flooded'])
           )
           db.add(obs)
       
       db.commit()
       db.close()
       print("✅ Data migrated to database")
   
   if __name__ == "__main__":
       migrate_csv()
   ```

**Test**: Run migration script and verify data in database

---

### Step 1.2: Weather API Integration

**Why**: Get real-time weather data instead of manual input

**Action Items**:

1. **Sign up for Weather API**
   - **OpenWeatherMap**: https://openweathermap.org/api (Free tier: 60 calls/min)
   - **WeatherAPI.com**: https://www.weatherapi.com/ (Free tier: 1M calls/month)
   - Get API key

2. **Create Weather Service**

   Create file: `app/services/weather_service.py`
   ```python
   import requests
   import os
   from datetime import datetime, timedelta
   from typing import Dict, Optional
   import time
   
   class WeatherService:
       def __init__(self, api_key: str):
           self.api_key = api_key
           self.base_url = "https://api.openweathermap.org/data/2.5"
           self.cache = {}  # Simple in-memory cache
           self.cache_ttl = 900  # 15 minutes
       
       def get_current_weather(self, lat: float, lon: float) -> Dict:
           """Get current weather for Chennai coordinates"""
           cache_key = f"{lat}_{lon}_{int(time.time() / self.cache_ttl)}"
           
           if cache_key in self.cache:
               return self.cache[cache_key]
           
           url = f"{self.base_url}/weather"
           params = {
               "lat": lat,
               "lon": lon,
               "appid": self.api_key,
               "units": "metric"
           }
           
           response = requests.get(url, params=params)
           response.raise_for_status()
           data = response.json()
           
           result = {
               "temp_c": data["main"]["temp"],
               "humidity_pct": data["main"]["humidity"],
               "rain_mm": data.get("rain", {}).get("1h", 0)  # Rain in last hour
           }
           
           self.cache[cache_key] = result
           return result
       
       def get_forecast(self, lat: float, lon: float, hours: int = 24) -> Dict:
           """Get weather forecast"""
           url = f"{self.base_url}/forecast"
           params = {
               "lat": lat,
               "lon": lon,
               "appid": self.api_key,
               "units": "metric"
           }
           
           response = requests.get(url, params=params)
           response.raise_for_status()
           data = response.json()
           
           # Process forecast data
           forecasts = []
           for item in data["list"][:hours//3]:  # 3-hour intervals
               forecasts.append({
                   "timestamp": item["dt_txt"],
                   "temp_c": item["main"]["temp"],
                   "humidity_pct": item["main"]["humidity"],
                   "rain_mm": item.get("rain", {}).get("3h", 0)
               })
           
           return {"forecasts": forecasts}
   ```

3. **Update Requirements**

   Add to `requirements.txt`:
   ```
   sqlalchemy==2.0.23
   requests==2.31.0
   apscheduler==3.10.4  # For scheduled tasks
   ```

4. **Create Background Data Collector**

   Create file: `app/services/data_collector.py`
   ```python
   from apscheduler.schedulers.background import BackgroundScheduler
   from app.services.weather_service import WeatherService
   from app.database import SessionLocal, RainfallObservation
   from datetime import datetime, timedelta
   import os
   
   class DataCollector:
       def __init__(self):
           self.weather_service = WeatherService(api_key=os.getenv("WEATHER_API_KEY"))
           self.chennai_coords = {"lat": 13.0827, "lon": 80.2707}
           self.scheduler = BackgroundScheduler()
       
       def collect_weather_data(self):
           """Collect current weather and store in database"""
           db = SessionLocal()
           try:
               weather = self.weather_service.get_current_weather(
                   self.chennai_coords["lat"],
                   self.chennai_coords["lon"]
               )
               
               # Calculate rolling sums (simplified - in production, query historical)
               obs = RainfallObservation(
                   timestamp=datetime.now(),
                   location="Chennai",
                   lat=self.chennai_coords["lat"],
                   lon=self.chennai_coords["lon"],
                   rain_mm=weather["rain_mm"],
                   rain_sum_1h=weather["rain_mm"],  # Simplified
                   humidity_pct=weather["humidity_pct"],
                   temp_c=weather["temp_c"]
               )
               
               db.add(obs)
               db.commit()
               print(f"✅ Collected weather data at {datetime.now()}")
           except Exception as e:
               print(f"❌ Error collecting data: {e}")
               db.rollback()
           finally:
               db.close()
       
       def start(self):
           """Start scheduled data collection"""
           # Collect every 30 minutes
           self.scheduler.add_job(
               self.collect_weather_data,
               'interval',
               minutes=30,
               id='weather_collection'
           )
           self.scheduler.start()
           print("🔄 Data collector started (30 min intervals)")
       
       def stop(self):
           self.scheduler.shutdown()
   ```

5. **Integrate into Main App**

   Update `app/main.py`:
   ```python
   from app.services.data_collector import DataCollector
   
   # At startup
   collector = DataCollector()
   collector.start()
   
   # At shutdown
   @app.on_event("shutdown")
   def shutdown_event():
       collector.stop()
   ```

**Test**: Start API, verify data collection in database

---

### Step 1.3: Enhanced API Endpoints

**Why**: Support real-time data queries and historical analysis

**Action Items**:

1. **Add Historical Data Endpoint**

   Add to `app/main.py`:
   ```python
   from app.database import SessionLocal, RainfallObservation
   from datetime import datetime, timedelta
   
   @app.get("/api/historical")
   def get_historical_data(
       hours: int = 24,
       location: str = None
   ):
       """Get historical rainfall observations"""
       db = SessionLocal()
       try:
           since = datetime.now() - timedelta(hours=hours)
           query = db.query(RainfallObservation).filter(
               RainfallObservation.timestamp >= since
           )
           
           if location:
               query = query.filter(RainfallObservation.location == location)
           
           observations = query.all()
           return [
               {
                   "timestamp": obs.timestamp.isoformat(),
                   "location": obs.location,
                   "lat": obs.lat,
                   "lon": obs.lon,
                   "rain_mm": obs.rain_mm,
                   "temp_c": obs.temp_c,
                   "humidity_pct": obs.humidity_pct,
                   "flooded": obs.flooded
               }
               for obs in observations
           ]
       finally:
           db.close()
   ```

2. **Update Prediction to Use Real-time Data**

   Add to `app/main.py`:
   ```python
   from app.services.weather_service import WeatherService
   from app.database import SessionLocal, RainfallObservation
   
   weather_service = WeatherService(api_key=os.getenv("WEATHER_API_KEY"))
   
   @app.post("/predict/realtime")
   def predict_realtime(lat: float = 13.0827, lon: float = 80.2707):
       """Predict flood risk using real-time weather data"""
       # Get current weather
       weather = weather_service.get_current_weather(lat, lon)
       
       # Get recent observations for rolling sums
       db = SessionLocal()
       try:
           recent = db.query(RainfallObservation).filter(
               RainfallObservation.timestamp >= datetime.now() - timedelta(hours=24)
           ).order_by(RainfallObservation.timestamp.desc()).all()
           
           # Calculate rolling sums (simplified)
           rain_sum_1h = sum([r.rain_mm for r in recent[:2]])  # Last 2 observations
           rain_sum_3h = sum([r.rain_mm for r in recent[:6]])
           # ... calculate other sums
           
           # Get geographic features (from database or static data)
           # For now, use defaults
           input_data = InputData(
               rain_mm=weather["rain_mm"],
               rain_sum_1h=rain_sum_1h,
               rain_sum_3h=rain_sum_3h,
               rain_sum_6h=rain_sum_6h,
               rain_sum_12h=rain_sum_12h,
               rain_sum_24h=rain_sum_24h,
               rain_max_3h=max([r.rain_mm for r in recent[:6]] or [0]),
               rain_max_6h=max([r.rain_mm for r in recent[:12]] or [0]),
               drainage_score=0.5,  # Get from database
               slope_pct=2.0,  # Get from database
               elevation_m=30.0,  # Get from database
               humidity_pct=weather["humidity_pct"],
               temp_c=weather["temp_c"]
           )
           
           return predict(input_data)
       finally:
           db.close()
   ```

**Test**: Call new endpoints and verify responses

---

## 🎯 PHASE 2: ML Enhancement (Next Priority)

### Step 2.1: Model Improvement

**Action Items**:

1. **Enhanced Feature Engineering**

   Create file: `src/feature_engineering.py`
   ```python
   import pandas as pd
   from datetime import datetime
   
   def add_temporal_features(df):
       """Add time-based features"""
       if 'timestamp' in df.columns:
           df['timestamp'] = pd.to_datetime(df['timestamp'])
           df['hour'] = df['timestamp'].dt.hour
           df['day_of_year'] = df['timestamp'].dt.dayofyear
           df['is_monsoon'] = df['timestamp'].dt.month.isin([6, 7, 8, 9, 10, 11])
       return df
   
   def add_interaction_features(df):
       """Add feature interactions"""
       df['rain_intensity'] = df['rain_mm'] * df['rain_sum_3h']
       df['drainage_effectiveness'] = df['drainage_score'] * (1 - df['slope_pct'] / 100)
       return df
   ```

2. **Try Better Models**

   Update `src/train_baseline.py`:
   ```python
   from xgboost import XGBClassifier
   from sklearn.model_selection import cross_val_score, GridSearchCV
   
   # Try XGBoost
   xgb_model = XGBClassifier(
       n_estimators=200,
       max_depth=6,
       learning_rate=0.1,
       random_state=42
   )
   
   # Hyperparameter tuning
   param_grid = {
       'n_estimators': [100, 200, 300],
       'max_depth': [4, 6, 8],
       'learning_rate': [0.01, 0.1, 0.2]
   }
   
   grid_search = GridSearchCV(xgb_model, param_grid, cv=5, scoring='roc_auc')
   grid_search.fit(X, y)
   
   best_model = grid_search.best_estimator_
   print(f"Best params: {grid_search.best_params_}")
   print(f"Best score: {grid_search.best_score_}")
   ```

---

### Step 2.2: Anomaly Detection

**Action Items**:

1. **Create Anomaly Detector**

   Create file: `app/services/anomaly_detector.py`
   ```python
   from sklearn.ensemble import IsolationForest
   import numpy as np
   import pandas as pd
   
   class AnomalyDetector:
       def __init__(self):
           self.model = IsolationForest(contamination=0.1, random_state=42)
           self.is_fitted = False
       
       def fit(self, historical_data: pd.DataFrame):
           """Train on historical data"""
           features = ['rain_mm', 'rain_sum_3h', 'rain_sum_24h']
           X = historical_data[features].values
           self.model.fit(X)
           self.is_fitted = True
       
       def detect(self, current_data: dict) -> dict:
           """Detect if current data is anomalous"""
           if not self.is_fitted:
               return {"anomaly_score": 0, "is_anomaly": False}
           
           features = np.array([[
               current_data['rain_mm'],
               current_data.get('rain_sum_3h', 0),
               current_data.get('rain_sum_24h', 0)
           ]])
           
           anomaly_score = self.model.score_samples(features)[0]
           is_anomaly = self.model.predict(features)[0] == -1
           
           return {
               "anomaly_score": float(anomaly_score),
               "is_anomaly": bool(is_anomaly),
               "severity": "high" if is_anomaly and anomaly_score < -0.5 else "low"
           }
   ```

2. **Integrate with Prediction**

   Update `app/main.py`:
   ```python
   from app.services.anomaly_detector import AnomalyDetector
   
   anomaly_detector = AnomalyDetector()
   # Load historical data and fit on startup
   
   @app.post("/predict/realtime")
   def predict_realtime(...):
       # ... existing prediction code ...
       
       prediction = predict(input_data)
       anomaly = anomaly_detector.detect({
           'rain_mm': weather['rain_mm'],
           'rain_sum_3h': rain_sum_3h,
           'rain_sum_24h': rain_sum_24h
       })
       
       return {
           **prediction,
           "anomaly_detected": anomaly["is_anomaly"],
           "anomaly_severity": anomaly["severity"]
       }
   ```

---

## 🎯 PHASE 3: Geospatial & Frontend (After ML is solid)

### Step 3.1: Map Integration

**Quick Start Option**: Use Leaflet.js (free, no API key needed)

1. **Create Simple HTML Dashboard**

   Create file: `frontend/index.html`:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
       <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
   </head>
   <body>
       <div id="map" style="height: 600px;"></div>
       <script>
           // Initialize map centered on Chennai
           var map = L.map('map').setView([13.0827, 80.2707], 11);
           L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
           
           // Fetch ward risk data
           fetch('http://localhost:8000/ward_risk')
               .then(r => r.json())
               .then(data => {
                   data.forEach(ward => {
                       var color = ward.risk < 0.3 ? 'green' : 
                                   ward.risk < 0.6 ? 'yellow' : 
                                   ward.risk < 0.8 ? 'orange' : 'red';
                       L.circleMarker([ward.ward_lat, ward.ward_lon], {
                           radius: 10,
                           fillColor: color,
                           color: 'black',
                           weight: 1
                       }).addTo(map)
                       .bindPopup(`Ward ${ward.ward_id}: Risk ${ward.risk}`);
                   });
               });
       </script>
   </body>
   </html>
   ```

---

## 📝 Configuration File

Create `config.py` for easy configuration:

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///flood_data.db")
    
    # Model
    MODEL_PATH = "models/baseline_random_forest.pkl"
    
    # Data Collection
    COLLECTION_INTERVAL_MINUTES = 30
    
    # Chennai Coordinates
    CHENNAI_LAT = 13.0827
    CHENNAI_LON = 80.2707
```

Create `.env` file:
```
WEATHER_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///flood_data.db
```

---

## ✅ Checklist: Phase 1 Completion

- [ ] Database set up and schema created
- [ ] Existing CSV data migrated to database
- [ ] Weather API service implemented
- [ ] Background data collector running
- [ ] Historical data endpoint working
- [ ] Real-time prediction endpoint working
- [ ] Data collection tested and verified

**Once Phase 1 is complete, move to Phase 2 (ML Enhancement)**

---

## 🚨 Important Notes

1. **Start Small**: Implement one feature at a time, test thoroughly
2. **Use Environment Variables**: Never hardcode API keys
3. **Error Handling**: Always wrap API calls in try-except
4. **Testing**: Test each component independently before integrating
5. **Documentation**: Update README as you add features

---

**Next Steps**: Begin with Step 1.1 (Database Setup) and work through Phase 1 systematically.

