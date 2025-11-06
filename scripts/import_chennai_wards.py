"""
Script to import real Chennai ward data
This is a template - customize based on your data source
"""
import pandas as pd
from app.database import SessionLocal, WardRisk
from app.config import RISK_THRESHOLDS
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


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


def import_chennai_wards_from_csv(csv_path: str):
    """
    Import Chennai wards from CSV file
    
    Expected CSV format:
    ward_id,ward_name,lat,lon,risk_score (optional)
    """
    db = SessionLocal()
    try:
        df = pd.read_csv(csv_path)
        
        print(f"📊 Importing {len(df)} wards...")
        
        for _, row in df.iterrows():
            # Calculate risk if not provided (using model prediction or default)
            risk_score = row.get('risk_score', 0.3)  # Default to moderate-low
            
            ward = WardRisk(
                ward_id=int(row['ward_id']),
                ward_name=row.get('ward_name', f"Ward {int(row['ward_id'])}"),
                lat=float(row['lat']),
                lon=float(row['lon']),
                risk_score=float(risk_score),
                risk_level=get_risk_level(float(risk_score)),
                last_updated=datetime.now()
            )
            
            # Check if exists, update or create
            existing = db.query(WardRisk).filter(WardRisk.ward_id == ward.ward_id).first()
            if existing:
                existing.ward_name = ward.ward_name
                existing.lat = ward.lat
                existing.lon = ward.lon
                existing.risk_score = ward.risk_score
                existing.risk_level = ward.risk_level
                existing.last_updated = datetime.now()
            else:
                db.add(ward)
        
        db.commit()
        print(f"✅ Successfully imported/updated {len(df)} wards")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error importing wards: {e}")
        raise
    finally:
        db.close()


def import_from_chennai_corporation_api():
    """
    Template for importing from Chennai Corporation API
    Customize based on actual API available
    """
    # TODO: Implement based on Chennai Corporation API
    # Example structure:
    # 1. Fetch ward boundaries from API
    # 2. Extract center coordinates
    # 3. Calculate initial risk scores
    # 4. Import to database
    pass


def calculate_risk_from_model(ward_id: int, lat: float, lon: float):
    """
    Calculate risk score for a ward using the ML model
    This can be used to initialize risk scores for new wards
    """
    # TODO: Use the prediction model to calculate initial risk
    # This requires current weather data and geographic features
    pass


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python import_chennai_wards.py <csv_file>")
        print("\nCSV format:")
        print("ward_id,ward_name,lat,lon,risk_score")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_chennai_wards_from_csv(csv_file)

