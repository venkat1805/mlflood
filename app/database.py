"""
Database models and setup for Flood Management System
"""
from sqlalchemy import create_engine, Column, Float, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class RainfallObservation(Base):
    """Store historical and real-time rainfall observations"""
    __tablename__ = "rainfall_observations"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    location = Column(String, index=True)  # Ward name or location identifier
    lat = Column(Float)
    lon = Column(Float)
    
    # Rainfall features
    rain_mm = Column(Float)
    rain_sum_1h = Column(Float)
    rain_sum_3h = Column(Float)
    rain_sum_6h = Column(Float)
    rain_sum_12h = Column(Float)
    rain_sum_24h = Column(Float)
    rain_max_3h = Column(Float)
    rain_max_6h = Column(Float)
    
    # Weather features
    humidity_pct = Column(Float)
    temp_c = Column(Float)
    
    # Geographic features (can be null if not available)
    drainage_score = Column(Float, nullable=True)
    slope_pct = Column(Float, nullable=True)
    elevation_m = Column(Float, nullable=True)
    
    # Target variable (ground truth, if available)
    flooded = Column(Boolean, nullable=True)
    
    # Additional metadata
    source = Column(String, default="manual")  # 'manual', 'api', 'sensor'


class WardRisk(Base):
    """Store ward-level flood risk assessments"""
    __tablename__ = "ward_risks"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, unique=True, index=True)
    ward_name = Column(String, nullable=True)
    lat = Column(Float)
    lon = Column(Float)
    risk_score = Column(Float)  # 0.0 to 1.0
    risk_level = Column(String)  # 'low', 'moderate', 'high', 'critical'
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Additional metadata
    prediction_confidence = Column(Float, nullable=True)
    anomaly_detected = Column(Boolean, default=False)


class Alert(Base):
    """Store flood alerts and warnings"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    location = Column(String, index=True)
    lat = Column(Float)
    lon = Column(Float)
    ward_id = Column(Integer, nullable=True, index=True)
    
    risk_level = Column(String)  # 'low', 'moderate', 'high', 'critical'
    risk_score = Column(Float)
    message = Column(String)
    
    # Alert status
    is_active = Column(Boolean, default=True, index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Additional context
    anomaly_detected = Column(Boolean, default=False)
    forecast_hours = Column(Integer, nullable=True)  # Hours ahead forecast


# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///flood_data.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

