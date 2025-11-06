# 🌤️ Quick Guide: Enable Real Weather Data

## Option 1: Enable Real Weather Data NOW (Recommended - 5 minutes)

### Step 1: Get Free API Key
1. Go to: https://openweathermap.org/api
2. Sign up for free account (no credit card needed)
3. Get your API key from the dashboard
4. Free tier: 60 calls/minute, 1,000,000 calls/month (plenty for our use)

### Step 2: Create .env File
```bash
# In project root directory
cat > .env << EOF
WEATHER_API_KEY=your_actual_api_key_here
EOF
```

### Step 3: Restart Server
```bash
# Stop current server (Ctrl+C)
# Start again
source venv/bin/activate
uvicorn app.main:app --reload
```

### Step 4: Verify It's Working
```bash
curl http://127.0.0.1:8000/health
# Check response - should show real data collection

curl http://127.0.0.1:8000/predict/realtime
# Should show real weather data (not mock)
```

**That's it!** Real weather data is now flowing. ✅

---

## Option 2: Enable Real Weather Data LATER

You can continue with Phase 2 using mock data, then enable real weather data anytime:

1. System works perfectly with mock data
2. All Phase 2 improvements will work
3. When ready, just add `.env` file and restart
4. No code changes needed - it's already built in!

---

## Recommendation

**Enable real weather data FIRST** because:
- ✅ Takes 5 minutes
- ✅ Improves Phase 2 model training quality
- ✅ Better anomaly detection patterns
- ✅ More realistic evaluation
- ✅ Immediate value

Then proceed with Phase 2 improvements using real data.

---

## Current Status

The system is **already configured** to use real weather data when available:
- ✅ Weather service checks for API key
- ✅ Falls back to mock if unavailable
- ✅ No code changes needed
- ✅ Just add the API key!

