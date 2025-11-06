"""
Migration script to import existing CSV data into database
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime, timedelta
from app.database import SessionLocal, RainfallObservation, WardRisk, init_db
from app.config import DATA_PATH, WARD_RISK_PATH

def migrate_rainfall_data():
    """Migrate sample_chennai_like_rainfall.csv to database"""
    print("📊 Migrating rainfall data...")
    
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_count = db.query(RainfallObservation).count()
        if existing_count > 0:
            print(f"⚠️  Database already contains {existing_count} observations")
            response = input("Do you want to continue and add more? (y/n): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                return
        
        # Read CSV
        if not DATA_PATH.exists():
            print(f"❌ Data file not found: {DATA_PATH}")
            return
        
        df = pd.read_csv(DATA_PATH)
        print(f"📖 Read {len(df)} rows from CSV")
        
        # Default Chennai coordinates
        default_lat = 13.0827
        default_lon = 80.2707
        
        # Create observations
        batch_size = 100
        total_added = 0
        
        # Start from a week ago and distribute data over time
        base_time = datetime.now() - timedelta(days=7)
        
        for idx, row in df.iterrows():
            # Distribute timestamps over the past week
            timestamp = base_time + timedelta(
                hours=idx % 168,  # Distribute over 7 days
                minutes=(idx * 5) % 60
            )
            
            obs = RainfallObservation(
                timestamp=timestamp,
                location="Chennai",
                lat=default_lat,
                lon=default_lon,
                rain_mm=row['rain_mm'],
                rain_sum_1h=row['rain_sum_1h'],
                rain_sum_3h=row['rain_sum_3h'],
                rain_sum_6h=row['rain_sum_6h'],
                rain_sum_12h=row['rain_sum_12h'],
                rain_sum_24h=row['rain_sum_24h'],
                rain_max_3h=row['rain_max_3h'],
                rain_max_6h=row['rain_max_6h'],
                drainage_score=row.get('drainage_score'),
                slope_pct=row.get('slope_pct'),
                elevation_m=row.get('elevation_m'),
                humidity_pct=row['humidity_pct'],
                temp_c=row['temp_c'],
                flooded=bool(row['flooded']) if 'flooded' in row else None,
                source="csv_migration"
            )
            db.add(obs)
            total_added += 1
            
            # Commit in batches
            if total_added % batch_size == 0:
                db.commit()
                print(f"  ✅ Added {total_added} observations...")
        
        db.commit()
        print(f"✅ Successfully migrated {total_added} rainfall observations")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error migrating rainfall data: {e}")
        raise
    finally:
        db.close()


def migrate_ward_risk_data():
    """Migrate risk_by_ward.csv to database"""
    print("\n📊 Migrating ward risk data...")
    
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_count = db.query(WardRisk).count()
        if existing_count > 0:
            print(f"⚠️  Database already contains {existing_count} ward risks")
            response = input("Do you want to continue and update? (y/n): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                return
            # Clear existing data
            db.query(WardRisk).delete()
        
        # Read CSV
        if not WARD_RISK_PATH.exists():
            print(f"⚠️  Ward risk file not found: {WARD_RISK_PATH}")
            print("   Skipping ward risk migration")
            return
        
        df = pd.read_csv(WARD_RISK_PATH)
        print(f"📖 Read {len(df)} wards from CSV")
        
        # Determine risk level based on risk score
        def get_risk_level(score):
            if score < 0.3:
                return "low"
            elif score < 0.6:
                return "moderate"
            elif score < 0.8:
                return "high"
            else:
                return "critical"
        
        for _, row in df.iterrows():
            ward = WardRisk(
                ward_id=int(row['ward_id']),
                ward_name=f"Ward {int(row['ward_id'])}",
                lat=row['ward_lat'],
                lon=row['ward_lon'],
                risk_score=row['risk'],
                risk_level=get_risk_level(row['risk']),
                last_updated=datetime.now()
            )
            db.add(ward)
        
        db.commit()
        print(f"✅ Successfully migrated {len(df)} ward risks")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error migrating ward risk data: {e}")
        raise
    finally:
        db.close()


def main():
    """Main migration function"""
    print("🚀 Starting database migration...\n")
    
    # Initialize database (create tables)
    init_db()
    
    # Migrate data
    migrate_rainfall_data()
    migrate_ward_risk_data()
    
    print("\n✅ Migration complete!")
    
    # Show summary
    db = SessionLocal()
    try:
        obs_count = db.query(RainfallObservation).count()
        ward_count = db.query(WardRisk).count()
        print(f"\n📊 Database Summary:")
        print(f"   Rainfall Observations: {obs_count}")
        print(f"   Ward Risks: {ward_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

