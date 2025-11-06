"""
Background data collector for automated weather data collection
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.weather_service import WeatherService
from app.database import SessionLocal, RainfallObservation
from app.config import (
    COLLECTION_INTERVAL_MINUTES,
    CHENNAI_LAT,
    CHENNAI_LON
)


class DataCollector:
    """Background service for collecting weather data at regular intervals"""
    
    def __init__(self, weather_service: Optional[WeatherService] = None):
        self.weather_service = weather_service or WeatherService()
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def collect_weather_data(self, lat: float = CHENNAI_LAT, lon: float = CHENNAI_LON):
        """
        Collect current weather data and store in database
        Calculates rolling sums from recent observations
        """
        db = SessionLocal()
        try:
            # Get current weather
            weather = self.weather_service.get_current_weather(lat, lon)
            
            if weather.get("source") == "error_fallback":
                print(f"⚠️  Skipping data collection - weather API error")
                return
            
            # Get recent observations to calculate rolling sums
            now = datetime.now()
            recent_obs = db.query(RainfallObservation).filter(
                RainfallObservation.timestamp >= now - timedelta(hours=24),
                RainfallObservation.lat == lat,
                RainfallObservation.lon == lon
            ).order_by(RainfallObservation.timestamp.desc()).all()
            
            # Calculate rolling sums
            # Group by hour for more accurate calculations
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
            
            # Create new observation
            observation = RainfallObservation(
                timestamp=datetime.now(),
                location="Chennai",
                lat=lat,
                lon=lon,
                rain_mm=weather["rain_mm"],
                rain_sum_1h=rain_sum_1h,
                rain_sum_3h=rain_sum_3h,
                rain_sum_6h=rain_sum_6h,
                rain_sum_12h=rain_sum_12h,
                rain_sum_24h=rain_sum_24h,
                rain_max_3h=rain_max_3h,
                rain_max_6h=rain_max_6h,
                humidity_pct=weather["humidity_pct"],
                temp_c=weather["temp_c"],
                source="api"
            )
            
            db.add(observation)
            db.commit()
            
            print(f"✅ Collected weather data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                  f"Rain: {weather['rain_mm']:.2f}mm, Temp: {weather['temp_c']:.1f}°C")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error collecting weather data: {e}")
        finally:
            db.close()
    
    def start(self, interval_minutes: Optional[int] = None):
        """Start scheduled data collection"""
        if self.is_running:
            print("⚠️  Data collector is already running")
            return
        
        interval = interval_minutes or COLLECTION_INTERVAL_MINUTES
        
        # Add job to scheduler
        self.scheduler.add_job(
            self.collect_weather_data,
            trigger=IntervalTrigger(minutes=interval),
            id='weather_collection',
            replace_existing=True,
            max_instances=1
        )
        
        self.scheduler.start()
        self.is_running = True
        
        print(f"🔄 Data collector started (collecting every {interval} minutes)")
        
        # Collect immediately on start
        try:
            self.collect_weather_data()
        except Exception as e:
            print(f"⚠️  Initial data collection failed: {e}")
    
    def stop(self):
        """Stop scheduled data collection"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        print("🛑 Data collector stopped")
    
    def collect_now(self):
        """Manually trigger data collection"""
        self.collect_weather_data()

