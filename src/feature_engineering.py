"""
Enhanced feature engineering for flood prediction model
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based features to the dataset
    
    Features added:
    - hour: Hour of day (0-23)
    - day_of_year: Day of year (1-365)
    - is_monsoon: Boolean flag for monsoon season (Jun-Nov)
    - month: Month (1-12)
    """
    df = df.copy()
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['month'] = df['timestamp'].dt.month
        df['is_monsoon'] = df['timestamp'].dt.month.isin([6, 7, 8, 9, 10, 11]).astype(int)
    else:
        # If no timestamp, add defaults (can be improved with actual timestamps)
        df['hour'] = 12  # Default to noon
        df['day_of_year'] = 180  # Default to mid-year
        df['month'] = 7  # Default to July (monsoon)
        df['is_monsoon'] = 1
    
    return df


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add feature interactions that may be predictive
    
    Features added:
    - rain_intensity: rain_mm * rain_sum_3h (intensity measure)
    - drainage_effectiveness: drainage_score * (1 - slope_pct/100)
    - temp_humidity_interaction: temp_c * humidity_pct
    - cumulative_risk: rain_sum_24h * (1 - drainage_score)
    """
    df = df.copy()
    
    # Rainfall intensity (current rain * recent accumulation)
    df['rain_intensity'] = df['rain_mm'] * df['rain_sum_3h']
    
    # Drainage effectiveness (better drainage + flatter terrain = better)
    df['drainage_effectiveness'] = df['drainage_score'] * (1 - df['slope_pct'] / 100)
    
    # Temperature-humidity interaction (high temp + high humidity = more evaporation issues)
    df['temp_humidity_interaction'] = df['temp_c'] * df['humidity_pct']
    
    # Cumulative risk (high rain + poor drainage)
    df['cumulative_risk'] = df['rain_sum_24h'] * (1 - df['drainage_score'])
    
    # Elevation impact (lower elevation = higher risk, normalized)
    df['elevation_risk'] = (100 - df['elevation_m']) / 100
    
    return df


def add_statistical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add statistical features from rainfall data
    
    Features added:
    - rain_std_24h: Standard deviation of rainfall (variability)
    - rain_trend: Trend in rainfall (increasing/decreasing)
    """
    df = df.copy()
    
    # Rainfall variability (higher variability might indicate storms)
    # Using rolling window if we have time series, otherwise use current values
    df['rain_variability'] = df[['rain_sum_1h', 'rain_sum_3h', 'rain_sum_6h']].std(axis=1)
    
    # Rainfall trend (is it increasing?)
    # Compare recent vs older rainfall
    df['rain_trend'] = (df['rain_sum_3h'] - df['rain_sum_12h']) / (df['rain_sum_12h'] + 1)
    
    # Max to average ratio (spike detection)
    df['rain_spike'] = df['rain_max_3h'] / (df['rain_sum_3h'] / 3 + 0.1)
    
    return df


def add_lag_features(df: pd.DataFrame, lag_hours: list = [1, 3, 6]) -> pd.DataFrame:
    """
    Add lag features (previous values)
    
    Note: This requires time-series data with timestamps
    For now, we'll create synthetic lag features based on current values
    """
    df = df.copy()
    
    # If we have timestamp and sorted data, create real lags
    # Otherwise, use current values as proxy (simplified)
    if 'timestamp' in df.columns and df['timestamp'].dtype == 'datetime64[ns]':
        df = df.sort_values('timestamp')
        for lag in lag_hours:
            df[f'rain_mm_lag_{lag}h'] = df['rain_mm'].shift(lag)
            df[f'rain_mm_lag_{lag}h'] = df[f'rain_mm_lag_{lag}h'].fillna(df['rain_mm'])
    else:
        # Simplified: use current rain_mm as proxy for lag
        for lag in lag_hours:
            df[f'rain_mm_lag_{lag}h'] = df['rain_mm']
    
    return df


def engineer_features(df: pd.DataFrame, include_lags: bool = False) -> pd.DataFrame:
    """
    Main function to apply all feature engineering
    
    Args:
        df: Input DataFrame
        include_lags: Whether to include lag features (requires sorted time series)
    
    Returns:
        DataFrame with all engineered features
    """
    df = df.copy()
    
    # Add temporal features
    df = add_temporal_features(df)
    
    # Add interaction features
    df = add_interaction_features(df)
    
    # Add statistical features
    df = add_statistical_features(df)
    
    # Add lag features (optional)
    if include_lags:
        df = add_lag_features(df)
    
    # Handle any NaN values
    df = df.fillna(0)
    
    # Replace infinities
    df = df.replace([np.inf, -np.inf], 0)
    
    return df


def get_feature_importance(model, feature_names):
    """
    Extract feature importance from trained model
    
    Returns:
        DataFrame with features and their importance scores
    """
    if hasattr(model, 'feature_importances_'):
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        return importance_df
    return None

