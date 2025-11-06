#!/usr/bin/env python3
"""
Setup script for Flood Management System
Installs dependencies and initializes database
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False

def main():
    print("🚀 Setting up Flood Management System\n")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Install dependencies
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing dependencies"
    ):
        print("\n⚠️  Warning: Some dependencies may have failed to install")
        print("   You can try manually: pip install -r requirements.txt")
    
    # Initialize database
    print("\n" + "=" * 50)
    print("📊 Initializing database...")
    
    try:
        from scripts.migrate_csv_to_db import main as migrate_main
        migrate_main()
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("\nYou can run the migration manually:")
        print("   python scripts/migrate_csv_to_db.py")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Set up your weather API key (optional but recommended):")
    print("   - Sign up at https://openweathermap.org/api")
    print("   - Create a .env file with: WEATHER_API_KEY=your_key")
    print("\n2. Start the API server:")
    print("   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
    print("\n3. Access the API documentation:")
    print("   http://127.0.0.1:8000/docs")
    print("\n4. Test the health endpoint:")
    print("   curl http://127.0.0.1:8000/health")

if __name__ == "__main__":
    main()

