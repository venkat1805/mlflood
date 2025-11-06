# 🌊 Flood Early Warning API

AI-driven flood detection and early warning system for Chennai, combining historical rainfall records, hydrological observations, and live weather information to estimate flood likelihood.

## ✨ Features

- **Real-time Weather Integration**: Automatic collection of live weather data
- **Historical Data Management**: Database-backed storage of rainfall observations
- **Flood Risk Prediction**: ML-powered flood probability estimation
- **Ward-level Risk Assessment**: Geographic risk distribution
- **Forecast Trends**: Weather forecasting for proactive planning
- **RESTful API**: Comprehensive API for all features

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or use the setup script:

```bash
python setup.py
```

### 2. Initialize Database

Migrate existing CSV data to database:

```bash
python scripts/migrate_csv_to_db.py
```

### 3. (Optional) Set Up Weather API

For real-time weather data, sign up at [OpenWeatherMap](https://openweathermap.org/api) and create a `.env` file:

```bash
WEATHER_API_KEY=your_api_key_here
```

The system will work without an API key but will use mock data.

### 4. Start the API Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Access API Documentation

Open your browser to: http://127.0.0.1:8000/docs

## 📡 API Endpoints

### Core Endpoints

- **GET** `/health` - Check API and model status
- **POST** `/predict` - Predict flood risk (manual input)
- **POST** `/predict/realtime` - Predict flood risk using real-time weather data
- **GET** `/ward_risk` - Get ward-level flood risk assessments
- **POST** `/retrain` - Retrain model with latest data

### Data Endpoints

- **GET** `/api/historical` - Get historical rainfall observations
  - Query params: `hours` (1-168), `location` (optional)
- **GET** `/api/forecast` - Get weather forecast
  - Query params: `lat`, `lon`, `hours` (3-120)
- **POST** `/api/collect` - Manually trigger data collection

## 🗄️ Database Schema

The system uses SQLite (default) or PostgreSQL with the following tables:

- **rainfall_observations**: Historical and real-time weather data
- **ward_risks**: Ward-level risk assessments
- **alerts**: Flood alerts and warnings (for future use)

## 🔧 Configuration

Create a `.env` file in the project root:

```env
WEATHER_API_KEY=your_key_here
DATABASE_URL=sqlite:///flood_data.db
COLLECTION_INTERVAL_MINUTES=30
```

## 📊 Data Collection

The system automatically collects weather data every 30 minutes (configurable). Data is stored in the database and used for:

- Real-time flood risk predictions
- Historical trend analysis
- Model retraining

## 🎯 Risk Levels

- **LOW**: 0.0 - 0.3 (Minimal risk)
- **MODERATE**: 0.3 - 0.6 (Caution advised)
- **HIGH**: 0.6 - 0.8 (Significant risk)
- **CRITICAL**: 0.8 - 1.0 (Immediate action required)

## 🏗️ Project Structure

```
flood_management_project/
├── app/
│   ├── main.py              # FastAPI application
│   ├── database.py           # Database models and setup
│   ├── config.py             # Configuration settings
│   └── services/
│       ├── weather_service.py    # Weather API integration
│       └── data_collector.py     # Background data collection
├── scripts/
│   └── migrate_csv_to_db.py  # Database migration script
├── data/                     # Training data
├── models/                   # ML models
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🔄 Next Steps

See `ROADMAP.md` and `IMPLEMENTATION_GUIDE.md` for:
- Phase 2: ML model improvements
- Phase 3: Geospatial visualization
- Phase 4: Interactive dashboard
- Phase 5: Alert system

## 📝 Notes

- The system works without a weather API key but will use mock data
- Database is automatically initialized on first API startup
- Model retraining uses data from database if available, falls back to CSV
- All timestamps are in UTC

## 🐛 Troubleshooting

**Database errors**: Make sure you've run the migration script first
**Weather API errors**: Check your API key or use mock data mode
**Model not loading**: Ensure `models/baseline_random_forest.pkl` exists

## 📄 License

[Your License Here]
# mlflood
