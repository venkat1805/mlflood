#!/usr/bin/env python3
"""
Helper script to test weather API key
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(str(project_root / ".env"))

from app.services.weather_service import WeatherService
from app.config import CHENNAI_LAT, CHENNAI_LON

def test_weather_api():
    """Test if weather API key is working"""
    api_key = os.getenv("WEATHER_API_KEY", "")
    
    if not api_key or api_key == "your_openweathermap_api_key_here":
        print("❌ Weather API key not set!")
        print("\nTo set it up:")
        print("1. Get free API key from: https://openweathermap.org/api")
        print("2. Create .env file in project root:")
        print("   WEATHER_API_KEY=your_actual_key_here")
        print("3. Run this script again")
        return False
    
    print(f"🔑 Testing API key: {api_key[:10]}...")
    
    try:
        service = WeatherService(api_key=api_key)
        weather = service.get_current_weather(CHENNAI_LAT, CHENNAI_LON)
        
        if weather.get("source") == "mock":
            print("❌ API key not working - still using mock data")
            print("   Check if your API key is correct")
            return False
        
        print("✅ API key is working!")
        print(f"\n📊 Current Weather for Chennai:")
        print(f"   Temperature: {weather['temp_c']}°C")
        print(f"   Humidity: {weather['humidity_pct']}%")
        print(f"   Rainfall (last hour): {weather['rain_mm']}mm")
        print(f"   Source: {weather.get('source', 'api')}")
        
        # Test forecast
        print("\n📈 Testing forecast...")
        forecast = service.get_forecast(CHENNAI_LAT, CHENNAI_LON, hours=24)
        if forecast.get("source") != "mock":
            print(f"✅ Forecast working! ({len(forecast.get('forecasts', []))} data points)")
        else:
            print("⚠️  Forecast returning mock data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

if __name__ == "__main__":
    success = test_weather_api()
    sys.exit(0 if success else 1)

