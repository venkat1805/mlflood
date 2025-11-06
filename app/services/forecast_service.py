"""
Time-series forecasting service for rainfall prediction
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class ForecastService:
    """Service for forecasting rainfall and flood risk"""
    
    def __init__(self):
        self.rainfall_model = None
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train_simple_forecast(self, historical_data: pd.DataFrame):
        """
        Train simple linear regression model for rainfall forecasting
        
        Args:
            historical_data: DataFrame with timestamp and rain_mm columns
        """
        if len(historical_data) < 24:  # Need at least 24 hours of data
            print("⚠️  Not enough data for forecasting (need at least 24 hours)")
            return
        
        # Sort by timestamp
        df = historical_data.sort_values('timestamp').copy()
        
        # Create features: hour, day_of_year, lag features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['rain_lag_1h'] = df['rain_mm'].shift(1).fillna(0)
        df['rain_lag_3h'] = df['rain_mm'].shift(3).fillna(0)
        df['rain_avg_6h'] = df['rain_mm'].rolling(6, min_periods=1).mean()
        
        # Prepare training data
        X = df[['hour', 'day_of_year', 'rain_lag_1h', 'rain_lag_3h', 'rain_avg_6h']].values
        y = df['rain_mm'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.rainfall_model = LinearRegression()
        self.rainfall_model.fit(X_scaled, y)
        self.is_trained = True
        
        print(f"✅ Forecast model trained on {len(df)} samples")
    
    def forecast_rainfall(self, current_data: Dict, hours_ahead: int = 24) -> List[Dict]:
        """
        Forecast rainfall for next N hours
        
        Args:
            current_data: Current weather/rainfall data
            hours_ahead: Number of hours to forecast
        
        Returns:
            List of forecast dictionaries
        """
        if not self.is_trained:
            # Return simple persistence forecast
            return self._persistence_forecast(current_data, hours_ahead)
        
        forecasts = []
        now = datetime.now()
        
        # Use current data as starting point
        last_rain = current_data.get('rain_mm', 0)
        rain_history = [last_rain]
        
        for hour in range(1, hours_ahead + 1):
            forecast_time = now + timedelta(hours=hour)
            
            # Prepare features
            hour_of_day = forecast_time.hour
            day_of_year = forecast_time.timetuple().tm_yday
            
            # Use recent history for lags
            rain_lag_1h = rain_history[-1] if len(rain_history) >= 1 else last_rain
            rain_lag_3h = rain_history[-3] if len(rain_history) >= 3 else last_rain
            rain_avg_6h = np.mean(rain_history[-6:]) if len(rain_history) >= 6 else last_rain
            
            features = np.array([[
                hour_of_day,
                day_of_year,
                rain_lag_1h,
                rain_lag_3h,
                rain_avg_6h
            ]])
            
            # Scale and predict
            features_scaled = self.scaler.transform(features)
            predicted_rain = max(0, self.rainfall_model.predict(features_scaled)[0])  # No negative rain
            
            # Update history
            rain_history.append(predicted_rain)
            
            forecasts.append({
                "timestamp": forecast_time.isoformat(),
                "hours_ahead": hour,
                "rainfall_mm": round(float(predicted_rain), 2),
                "confidence": "medium"  # Simple model, medium confidence
            })
        
        return forecasts
    
    def _persistence_forecast(self, current_data: Dict, hours_ahead: int) -> List[Dict]:
        """Simple persistence forecast (assume current conditions continue)"""
        now = datetime.now()
        current_rain = current_data.get('rain_mm', 0)
        
        forecasts = []
        for hour in range(1, hours_ahead + 1):
            forecast_time = now + timedelta(hours=hour)
            forecasts.append({
                "timestamp": forecast_time.isoformat(),
                "hours_ahead": hour,
                "rainfall_mm": round(float(current_rain), 2),
                "confidence": "low",
                "method": "persistence"
            })
        
        return forecasts
    
    def forecast_flood_risk(self, rainfall_forecast: List[Dict], current_conditions: Dict) -> List[Dict]:
        """
        Forecast flood risk based on rainfall forecast
        
        Args:
            rainfall_forecast: List of rainfall forecasts
            current_conditions: Current weather/geographic conditions
        
        Returns:
            List of flood risk forecasts
        """
        risk_forecasts = []
        
        # Calculate cumulative rainfall over forecast period
        cumulative_rain = 0
        
        for forecast in rainfall_forecast:
            cumulative_rain += forecast['rainfall_mm']
            
            # Simple risk calculation based on cumulative rain
            # This is a simplified version - in production, use the ML model
            if cumulative_rain > 100:
                risk_level = "critical"
                risk_score = 0.9
            elif cumulative_rain > 50:
                risk_level = "high"
                risk_score = 0.7
            elif cumulative_rain > 25:
                risk_level = "moderate"
                risk_score = 0.5
            else:
                risk_level = "low"
                risk_score = 0.3
            
            risk_forecasts.append({
                "timestamp": forecast["timestamp"],
                "hours_ahead": forecast["hours_ahead"],
                "cumulative_rainfall_mm": round(cumulative_rain, 2),
                "risk_level": risk_level,
                "risk_score": risk_score,
                "rainfall_mm": forecast["rainfall_mm"]
            })
        
        return risk_forecasts
    
    def get_trend_analysis(self, historical_data: pd.DataFrame, hours: int = 24) -> Dict:
        """
        Analyze rainfall trends
        
        Args:
            historical_data: Historical rainfall data
            hours: Number of hours to analyze
        
        Returns:
            Dictionary with trend analysis
        """
        if len(historical_data) < 2:
            return {"trend": "unknown", "change_rate": 0}
        
        df = historical_data.sort_values('timestamp').tail(hours)
        
        if len(df) < 2:
            return {"trend": "unknown", "change_rate": 0}
        
        recent_avg = df['rain_mm'].tail(6).mean()
        older_avg = df['rain_mm'].head(len(df) - 6).mean() if len(df) > 6 else df['rain_mm'].iloc[0]
        
        change_rate = ((recent_avg - older_avg) / (older_avg + 0.1)) * 100
        
        if change_rate > 20:
            trend = "increasing"
        elif change_rate < -20:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "change_rate": round(change_rate, 2),
            "recent_average": round(recent_avg, 2),
            "older_average": round(older_avg, 2)
        }

