"""
Weather API service for fetching real-time weather data
"""
import requests
import os
import time
from datetime import datetime
from typing import Dict, Optional, List
from app.config import WEATHER_API_KEY, CHENNAI_LAT, CHENNAI_LON, WEATHER_CACHE_TTL_SECONDS


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or WEATHER_API_KEY
        if not self.api_key:
            print("⚠️  Warning: WEATHER_API_KEY not set. Weather features will be limited.")
        
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.cache: Dict[str, tuple] = {}  # (data, timestamp)
        self.cache_ttl = WEATHER_CACHE_TTL_SECONDS
    
    def _get_cache_key(self, lat: float, lon: float, endpoint: str) -> str:
        """Generate cache key"""
        return f"{endpoint}_{lat}_{lon}_{int(time.time() / self.cache_ttl)}"
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and still valid"""
        if cache_key not in self.cache:
            return False
        data, cached_time = self.cache[cache_key]
        return (time.time() - cached_time) < self.cache_ttl
    
    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached data"""
        if self._is_cached(cache_key):
            return self.cache[cache_key][0]
        return None
    
    def _cache_data(self, cache_key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[cache_key] = (data, time.time())
    
    def get_current_weather(self, lat: float = CHENNAI_LAT, lon: float = CHENNAI_LON) -> Dict:
        """
        Get current weather for given coordinates
        
        Returns:
            Dict with temp_c, humidity_pct, rain_mm, etc.
        """
        if not self.api_key:
            # Return mock data if API key not available
            return {
                "temp_c": 28.0,
                "humidity_pct": 75.0,
                "rain_mm": 0.0,
                "source": "mock"
            }
        
        cache_key = self._get_cache_key(lat, lon, "current")
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = {
                "temp_c": data["main"]["temp"],
                "humidity_pct": data["main"]["humidity"],
                "pressure": data["main"].get("pressure", 0),
                "wind_speed": data.get("wind", {}).get("speed", 0),
                "rain_mm": data.get("rain", {}).get("1h", 0.0),  # Rain in last hour
                "description": data["weather"][0]["description"] if data.get("weather") else "",
                "timestamp": datetime.now().isoformat(),
                "source": "api"
            }
            
            self._cache_data(cache_key, result)
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Error fetching weather data: {e}")
            # Return mock data on error
            return {
                "temp_c": 28.0,
                "humidity_pct": 75.0,
                "rain_mm": 0.0,
                "source": "error_fallback"
            }
    
    def get_forecast(self, lat: float = CHENNAI_LAT, lon: float = CHENNAI_LON, hours: int = 24) -> Dict:
        """
        Get weather forecast for next N hours
        
        Args:
            lat: Latitude
            lon: Longitude
            hours: Number of hours to forecast (max 120)
        
        Returns:
            Dict with forecasts list
        """
        if not self.api_key:
            return {"forecasts": [], "source": "mock"}
        
        cache_key = self._get_cache_key(lat, lon, f"forecast_{hours}")
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.base_url}/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process forecast data (3-hour intervals)
            forecasts = []
            max_items = min(hours // 3, len(data.get("list", [])))
            
            for item in data.get("list", [])[:max_items]:
                forecasts.append({
                    "timestamp": item["dt_txt"],
                    "datetime": datetime.fromtimestamp(item["dt"]).isoformat(),
                    "temp_c": item["main"]["temp"],
                    "humidity_pct": item["main"]["humidity"],
                    "rain_mm": item.get("rain", {}).get("3h", 0.0),  # Rain in 3-hour period
                    "description": item["weather"][0]["description"] if item.get("weather") else ""
                })
            
            result = {
                "forecasts": forecasts,
                "source": "api",
                "location": data.get("city", {}).get("name", "Unknown")
            }
            
            self._cache_data(cache_key, result)
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Error fetching forecast: {e}")
            return {"forecasts": [], "source": "error"}
    
    def get_historical_rainfall(self, lat: float, lon: float, days: int = 7) -> List[Dict]:
        """
        Get historical rainfall data (if available)
        Note: OpenWeatherMap free tier doesn't include historical data
        This would require a paid subscription or alternative data source
        """
        # Placeholder - would need paid API or alternative source
        return []

