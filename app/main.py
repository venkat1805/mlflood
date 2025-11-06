from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
import joblib
import os

from app.database import get_db, init_db, RainfallObservation, WardRisk, Alert
from app.config import MODEL_PATH, DATA_PATH, RISK_THRESHOLDS
from app.services.weather_service import WeatherService
from app.services.data_collector import DataCollector
from app.services.anomaly_detector import AnomalyDetector, train_anomaly_detector
from app.services.forecast_service import ForecastService
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.feature_engineering import engineer_features

app = FastAPI(
    title="Flood Early Warning API",
    description="AI-driven flood detection and early warning system for Chennai",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
try:
    frontend_path = Path(__file__).parent.parent / "frontend"
    if frontend_path.exists():
        app.mount("/map", StaticFiles(directory=str(frontend_path), html=True), name="map")
        print("✅ Frontend mounted at /map")
except Exception as e:
    print(f"⚠️  Warning: Could not mount frontend: {e}")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    print("✅ Database initialized")

# Load model
try:
    pkg = joblib.load(MODEL_PATH)
    model, features = pkg["model"], pkg["features"]
    print(f"✅ Model loaded: {len(features)} features")
except Exception as e:
    print(f"⚠️  Warning: Could not load model: {e}")
    model, features = None, []

# Initialize services
weather_service = WeatherService()
data_collector = DataCollector(weather_service)

# Initialize anomaly detector
anomaly_detector = None
try:
    anomaly_detector = train_anomaly_detector()
    if anomaly_detector:
        print("✅ Anomaly detector initialized")
except Exception as e:
    print(f"⚠️  Warning: Could not initialize anomaly detector: {e}")

# Initialize forecast service
forecast_service = ForecastService()
try:
    # Train forecast service on historical data
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        observations = db.query(RainfallObservation).filter(
            RainfallObservation.timestamp >= datetime.now() - timedelta(days=7)
        ).order_by(RainfallObservation.timestamp).all()
        
        if len(observations) >= 24:
            df_forecast = pd.DataFrame([{
                'timestamp': obs.timestamp,
                'rain_mm': obs.rain_mm
            } for obs in observations])
            forecast_service.train_simple_forecast(df_forecast)
            print("✅ Forecast service initialized")
        else:
            print("⚠️  Not enough data for forecast training")
    finally:
        db.close()
except Exception as e:
    print(f"⚠️  Warning: Could not initialize forecast service: {e}")

# Start data collector (collects weather data every 30 minutes)
try:
    data_collector.start()
except Exception as e:
    print(f"⚠️  Warning: Could not start data collector: {e}")

# Shutdown event
@app.on_event("shutdown")
def shutdown_event():
    data_collector.stop()
    print("🛑 Services stopped")

# Schema for prediction input
class InputData(BaseModel):
    rain_mm: float
    rain_sum_1h: float
    rain_sum_3h: float
    rain_sum_6h: float
    rain_sum_12h: float
    rain_sum_24h: float
    rain_max_3h: float
    rain_max_6h: float
    drainage_score: float
    slope_pct: float
    elevation_m: float
    humidity_pct: float
    temp_c: float

def get_risk_level(risk_score: float) -> str:
    """Convert risk score to risk level"""
    if risk_score < RISK_THRESHOLDS["moderate"]:
        return "low"
    elif risk_score < RISK_THRESHOLDS["high"]:
        return "moderate"
    elif risk_score < RISK_THRESHOLDS["critical"]:
        return "high"
    else:
        return "critical"


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model_loaded": model is not None and os.path.exists(MODEL_PATH),
        "database_connected": True,
        "data_collector_running": data_collector.is_running,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict")
def predict(data: InputData):
    df = pd.DataFrame([data.dict()])
    proba = model.predict_proba(df[features].values)[:, 1][0]
    return {"flood_risk_probability": round(float(proba), 4)}

@app.get("/ward_risk")
def ward_risk(db: Session = Depends(get_db)):
    """Get ward-level flood risk from database"""
    try:
        wards = db.query(WardRisk).all()
        return [
            {
                "ward_id": ward.ward_id,
                "ward_name": ward.ward_name,
                "lat": ward.lat,
                "lon": ward.lon,
                "risk": ward.risk_score,
                "risk_level": ward.risk_level,
                "last_updated": ward.last_updated.isoformat() if ward.last_updated else None
            }
            for ward in wards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ward risks: {str(e)}")


@app.get("/api/historical")
def get_historical_data(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db)
):
    """Get historical rainfall observations"""
    try:
        since = datetime.now() - timedelta(hours=hours)
        query = db.query(RainfallObservation).filter(
            RainfallObservation.timestamp >= since
        )
        
        if location:
            query = query.filter(RainfallObservation.location == location)
        
        observations = query.order_by(RainfallObservation.timestamp.desc()).limit(1000).all()
        
        return [
            {
                "timestamp": obs.timestamp.isoformat(),
                "location": obs.location,
                "lat": obs.lat,
                "lon": obs.lon,
                "rain_mm": obs.rain_mm,
                "rain_sum_1h": obs.rain_sum_1h,
                "rain_sum_3h": obs.rain_sum_3h,
                "rain_sum_24h": obs.rain_sum_24h,
                "temp_c": obs.temp_c,
                "humidity_pct": obs.humidity_pct,
                "flooded": obs.flooded,
                "source": obs.source
            }
            for obs in observations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching historical data: {str(e)}")


@app.post("/predict/realtime")
def predict_realtime(
    lat: float = Query(13.0827, description="Latitude"),
    lon: float = Query(80.2707, description="Longitude"),
    db: Session = Depends(get_db)
):
    """Predict flood risk using real-time weather data"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Get current weather
        weather = weather_service.get_current_weather(lat, lon)
        
        # Get recent observations for rolling sums
        now = datetime.now()
        recent_obs = db.query(RainfallObservation).filter(
            RainfallObservation.timestamp >= now - timedelta(hours=24),
            RainfallObservation.lat == lat,
            RainfallObservation.lon == lon
        ).order_by(RainfallObservation.timestamp.desc()).all()
        
        # Calculate rolling sums
        rain_values_1h = [obs.rain_mm for obs in recent_obs if 
                         (now - obs.timestamp).total_seconds() <= 3600]
        rain_values_3h = [obs.rain_mm for obs in recent_obs if 
                         (now - obs.timestamp).total_seconds() <= 10800]
        rain_values_6h = [obs.rain_mm for obs in recent_obs if 
                         (now - obs.timestamp).total_seconds() <= 21600]
        rain_values_12h = [obs.rain_mm for obs in recent_obs if 
                           (now - obs.timestamp).total_seconds() <= 43200]
        rain_values_24h = [obs.rain_mm for obs in recent_obs]
        
        rain_sum_1h = sum(rain_values_1h) + weather["rain_mm"]
        rain_sum_3h = sum(rain_values_3h) + weather["rain_mm"]
        rain_sum_6h = sum(rain_values_6h) + weather["rain_mm"]
        rain_sum_12h = sum(rain_values_12h) + weather["rain_mm"]
        rain_sum_24h = sum(rain_values_24h) + weather["rain_mm"]
        rain_max_3h = max(rain_values_3h + [weather["rain_mm"]], default=0)
        rain_max_6h = max(rain_values_6h + [weather["rain_mm"]], default=0)
        
        # Default geographic features (should be fetched from database in production)
        # For now, use averages from training data
        input_data = InputData(
            rain_mm=weather["rain_mm"],
            rain_sum_1h=rain_sum_1h,
            rain_sum_3h=rain_sum_3h,
            rain_sum_6h=rain_sum_6h,
            rain_sum_12h=rain_sum_12h,
            rain_sum_24h=rain_sum_24h,
            rain_max_3h=rain_max_3h,
            rain_max_6h=rain_max_6h,
            drainage_score=0.5,  # TODO: Get from database
            slope_pct=2.0,  # TODO: Get from database
            elevation_m=30.0,  # TODO: Get from database
            humidity_pct=weather["humidity_pct"],
            temp_c=weather["temp_c"]
        )
        
        # Convert to DataFrame and apply feature engineering
        df_input = pd.DataFrame([input_data.dict()])
        df_engineered = engineer_features(df_input, include_lags=False)
        
        # Ensure we only use features that the model expects
        available_features = [f for f in features if f in df_engineered.columns]
        missing_features = [f for f in features if f not in df_engineered.columns]
        
        if missing_features:
            # Fill missing features with defaults
            for feat in missing_features:
                df_engineered[feat] = 0
        
        # Make prediction
        df = df_engineered[features] if len(features) == len(df_engineered.columns) else df_engineered[available_features]
        proba = model.predict_proba(df.values)[:, 1][0]
        risk_score = round(float(proba), 4)
        risk_level = get_risk_level(risk_score)
        
        result = {
            "flood_risk_probability": risk_score,
            "risk_level": risk_level,
            "location": {"lat": lat, "lon": lon},
            "current_weather": {
                "temp_c": weather["temp_c"],
                "humidity_pct": weather["humidity_pct"],
                "rain_mm": weather["rain_mm"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add anomaly detection if available
        if anomaly_detector and anomaly_detector.is_fitted:
            anomaly_data = {
                "rain_mm": weather["rain_mm"],
                "rain_sum_3h": rain_sum_3h,
                "rain_sum_24h": rain_sum_24h,
                "rain_max_3h": rain_max_3h,
                "rain_trend": (rain_sum_3h - rain_sum_12h) / (rain_sum_12h + 1) if rain_sum_12h > 0 else 0
            }
            anomaly_result = anomaly_detector.detect(anomaly_data)
            result["anomaly_detection"] = anomaly_result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error making prediction: {str(e)}")


@app.get("/api/forecast")
def get_forecast(
    lat: float = Query(13.0827, description="Latitude"),
    lon: float = Query(80.2707, description="Longitude"),
    hours: int = Query(24, ge=3, le=120, description="Hours to forecast")
):
    """Get weather forecast from external API"""
    try:
        forecast = weather_service.get_forecast(lat, lon, hours)
        return forecast
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching forecast: {str(e)}")


@app.get("/api/forecast/rainfall")
def forecast_rainfall(
    hours: int = Query(24, ge=1, le=72, description="Hours ahead to forecast"),
    db: Session = Depends(get_db)
):
    """Forecast rainfall using time-series model"""
    try:
        # Get current weather
        weather = weather_service.get_current_weather()
        
        # Get recent observations for context
        now = datetime.now()
        recent_obs = db.query(RainfallObservation).filter(
            RainfallObservation.timestamp >= now - timedelta(hours=24)
        ).order_by(RainfallObservation.timestamp).all()
        
        current_data = {
            "rain_mm": weather["rain_mm"],
            "rain_sum_3h": sum([obs.rain_mm for obs in recent_obs[-3:]]) if recent_obs else weather["rain_mm"],
            "rain_sum_24h": sum([obs.rain_mm for obs in recent_obs]) if recent_obs else weather["rain_mm"]
        }
        
        # Generate forecast
        rainfall_forecast = forecast_service.forecast_rainfall(current_data, hours)
        
        return {
            "forecast": rainfall_forecast,
            "current_conditions": current_data,
            "method": "time_series" if forecast_service.is_trained else "persistence"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating forecast: {str(e)}")


@app.get("/api/forecast/flood_risk")
def forecast_flood_risk(
    hours: int = Query(24, ge=1, le=72, description="Hours ahead to forecast"),
    lat: float = Query(13.0827, description="Latitude"),
    lon: float = Query(80.2707, description="Longitude"),
    db: Session = Depends(get_db)
):
    """Forecast flood risk based on rainfall forecast"""
    try:
        # Get current weather
        weather = weather_service.get_current_weather(lat, lon)
        
        # Get recent observations
        now = datetime.now()
        recent_obs = db.query(RainfallObservation).filter(
            RainfallObservation.timestamp >= now - timedelta(hours=24)
        ).order_by(RainfallObservation.timestamp).all()
        
        current_data = {
            "rain_mm": weather["rain_mm"],
            "rain_sum_3h": sum([obs.rain_mm for obs in recent_obs[-3:]]) if recent_obs else weather["rain_mm"],
            "rain_sum_24h": sum([obs.rain_mm for obs in recent_obs]) if recent_obs else weather["rain_mm"]
        }
        
        # Get rainfall forecast
        rainfall_forecast = forecast_service.forecast_rainfall(current_data, hours)
        
        # Forecast flood risk
        risk_forecast = forecast_service.forecast_flood_risk(rainfall_forecast, current_data)
        
        # Get trend analysis
        if recent_obs:
            df_trend = pd.DataFrame([{
                'timestamp': obs.timestamp,
                'rain_mm': obs.rain_mm
            } for obs in recent_obs])
            trend = forecast_service.get_trend_analysis(df_trend)
        else:
            trend = {"trend": "unknown", "change_rate": 0}
        
        return {
            "risk_forecast": risk_forecast,
            "rainfall_forecast": rainfall_forecast,
            "trend_analysis": trend,
            "location": {"lat": lat, "lon": lon},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error forecasting flood risk: {str(e)}")


@app.post("/api/collect")
def manual_collect():
    """Manually trigger data collection"""
    try:
        data_collector.collect_now()
        return {"status": "Data collection triggered", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting data: {str(e)}")


@app.post("/api/anomaly/detect")
def detect_anomaly(
    rain_mm: float = Query(..., description="Current rainfall (mm)"),
    rain_sum_3h: float = Query(..., description="Rainfall sum 3h (mm)"),
    rain_sum_24h: float = Query(..., description="Rainfall sum 24h (mm)"),
    rain_max_3h: float = Query(..., description="Max rainfall 3h (mm)")
):
    """Detect anomalies in rainfall patterns"""
    if not anomaly_detector or not anomaly_detector.is_fitted:
        raise HTTPException(status_code=503, detail="Anomaly detector not available")
    
    try:
        anomaly_data = {
            "rain_mm": rain_mm,
            "rain_sum_3h": rain_sum_3h,
            "rain_sum_24h": rain_sum_24h,
            "rain_max_3h": rain_max_3h,
            "rain_trend": 0  # Can be calculated if needed
        }
        
        result = anomaly_detector.detect(anomaly_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting anomaly: {str(e)}")


@app.get("/api/risk_at_location")
def get_risk_at_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    db: Session = Depends(get_db)
):
    """Get flood risk at a specific location"""
    try:
        # Find nearest ward
        wards = db.query(WardRisk).all()
        
        if not wards:
            raise HTTPException(status_code=404, detail="No ward data available")
        
        # Calculate distance to each ward and find nearest
        import math
        min_distance = float('inf')
        nearest_ward = None
        
        for ward in wards:
            # Haversine distance calculation
            R = 6371  # Earth radius in km
            lat1, lon1 = math.radians(lat), math.radians(lon)
            lat2, lon2 = math.radians(ward.lat), math.radians(ward.lon)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = R * c
            
            if distance < min_distance:
                min_distance = distance
                nearest_ward = ward
        
        # Get current weather for prediction
        weather = weather_service.get_current_weather(lat, lon)
        
        # Use nearest ward's risk as base, adjust based on distance
        base_risk = nearest_ward.risk_score if nearest_ward else 0.5
        
        # Interpolate risk based on distance (closer = more similar risk)
        # Simple inverse distance weighting
        if min_distance < 1.0:  # Within 1km
            risk_score = base_risk
        else:
            # Reduce risk similarity with distance
            weight = 1 / (1 + min_distance)
            risk_score = base_risk * weight + 0.3 * (1 - weight)  # Default to low risk if far
        
        risk_level = get_risk_level(risk_score)
        
        return {
            "location": {"lat": lat, "lon": lon},
            "nearest_ward": {
                "ward_id": nearest_ward.ward_id if nearest_ward else None,
                "ward_name": nearest_ward.ward_name if nearest_ward else None,
                "distance_km": round(min_distance, 2)
            },
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "current_weather": {
                "temp_c": weather["temp_c"],
                "humidity_pct": weather["humidity_pct"],
                "rain_mm": weather["rain_mm"]
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating risk: {str(e)}")


@app.get("/api/flood_prone_areas")
def get_flood_prone_areas(
    risk_threshold: float = Query(0.6, ge=0.0, le=1.0, description="Minimum risk score"),
    db: Session = Depends(get_db)
):
    """Get list of flood-prone areas (wards with high risk)"""
    try:
        wards = db.query(WardRisk).filter(
            WardRisk.risk_score >= risk_threshold
        ).order_by(WardRisk.risk_score.desc()).all()
        
        return [
            {
                "ward_id": ward.ward_id,
                "ward_name": ward.ward_name,
                "lat": ward.lat,
                "lon": ward.lon,
                "risk_score": ward.risk_score,
                "risk_level": ward.risk_level,
                "last_updated": ward.last_updated.isoformat() if ward.last_updated else None
            }
            for ward in wards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching flood-prone areas: {str(e)}")


@app.get("/api/risk_map")
def get_risk_map(db: Session = Depends(get_db)):
    """Get GeoJSON data for map visualization"""
    try:
        wards = db.query(WardRisk).all()
        
        # Create GeoJSON FeatureCollection
        features = []
        for ward in wards:
            # Create a simple point feature (can be enhanced with actual boundaries)
            feature = {
                "type": "Feature",
                "properties": {
                    "ward_id": ward.ward_id,
                    "ward_name": ward.ward_name,
                    "risk_score": ward.risk_score,
                    "risk_level": ward.risk_level,
                    "last_updated": ward.last_updated.isoformat() if ward.last_updated else None
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [ward.lon, ward.lat]  # GeoJSON uses [lon, lat]
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return geojson
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating GeoJSON: {str(e)}")

@app.post("/retrain")
def retrain(db: Session = Depends(get_db)):
    """Retrain model using data from database"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Get training data from database
        observations = db.query(RainfallObservation).filter(
            RainfallObservation.flooded.isnot(None)
        ).all()
        
        if len(observations) < 10:
            # Fallback to CSV if not enough data in DB
            df = pd.read_csv(DATA_PATH)
        else:
            # Convert observations to DataFrame
            data = []
            for obs in observations:
                data.append({
                    'rain_mm': obs.rain_mm,
                    'rain_sum_1h': obs.rain_sum_1h,
                    'rain_sum_3h': obs.rain_sum_3h,
                    'rain_sum_6h': obs.rain_sum_6h,
                    'rain_sum_12h': obs.rain_sum_12h,
                    'rain_sum_24h': obs.rain_sum_24h,
                    'rain_max_3h': obs.rain_max_3h,
                    'rain_max_6h': obs.rain_max_6h,
                    'drainage_score': obs.drainage_score or 0.5,
                    'slope_pct': obs.slope_pct or 2.0,
                    'elevation_m': obs.elevation_m or 30.0,
                    'humidity_pct': obs.humidity_pct,
                    'temp_c': obs.temp_c,
                    'flooded': int(obs.flooded) if obs.flooded else 0
                })
            df = pd.DataFrame(data)
        
        X = df[features]
        y = df["flooded"]
        model.fit(X, y)
        joblib.dump({"model": model, "features": features}, MODEL_PATH)
        
        return {
            "status": "Model retrained successfully",
            "training_samples": len(df),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retraining model: {str(e)}")
