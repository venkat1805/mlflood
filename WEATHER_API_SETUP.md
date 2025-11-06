# 🌤️ Weather API Setup - Quick Start Guide

## Step 1: Get Your Free API Key (2 minutes)

1. **Go to**: https://openweathermap.org/api
2. **Click**: "Sign Up" button (top right)
3. **Create account**:
   - Choose a username
   - Enter your email
   - Create a password
   - Accept terms
4. **Verify email** (check your inbox)
5. **Login** to your account
6. **Navigate to**: "API keys" section (in your account dashboard)
7. **Copy** your API key (it's a long string of letters and numbers)

**Note**: Free tier includes:
- ✅ 60 API calls per minute
- ✅ 1,000,000 calls per month
- ✅ Current weather data
- ✅ 5-day forecast
- ✅ Perfect for our project!

---

## Step 2: Add API Key to Project

Once you have your API key, create a `.env` file in the project root:

```bash
# In project root directory
cat > .env << 'EOF'
WEATHER_API_KEY=your_actual_api_key_here
EOF
```

**Replace** `your_actual_api_key_here` with your actual API key from Step 1.

---

## Step 3: Test the API Key

Run the test script:

```bash
source venv/bin/activate
python scripts/test_weather_api.py
```

You should see:
- ✅ API key is working!
- Current weather data for Chennai
- Forecast data

---

## Step 4: Restart Server

If the server is running, restart it to load the new API key:

```bash
# Stop server (Ctrl+C)
# Start again
uvicorn app.main:app --reload
```

---

## Step 5: Verify It's Working

Test the API:

```bash
# Check health endpoint
curl http://127.0.0.1:8000/health

# Test real-time prediction (should show real weather data)
curl -X POST "http://127.0.0.1:8000/predict/realtime?lat=13.0827&lon=80.2707"
```

The response should show real weather data (not mock data).

---

## Troubleshooting

**Problem**: Still seeing mock data
- **Solution**: Make sure `.env` file is in project root (same directory as `app/`)
- **Solution**: Restart the server after creating `.env`
- **Solution**: Check API key is correct (run test script)

**Problem**: API key not working
- **Solution**: Wait a few minutes after signup (API key activation can take 2-10 minutes)
- **Solution**: Check you copied the entire key (no spaces)
- **Solution**: Verify your account is activated

**Problem**: Rate limit errors
- **Solution**: Free tier allows 60 calls/minute - should be plenty
- **Solution**: Our caching reduces API calls significantly

---

## What Happens Next?

Once the API key is working:
1. ✅ Real weather data will be collected every 30 minutes
2. ✅ Forecasts will use real data
3. ✅ Predictions will be based on actual weather
4. ✅ Ready for Phase 2 improvements!

---

**Ready?** Get your API key and let me know when you have it! 🚀
