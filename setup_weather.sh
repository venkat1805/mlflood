#!/bin/bash
# Quick setup script for weather API key

echo "🌤️  Weather API Setup Helper"
echo "=============================="
echo ""
echo "This script will help you set up your OpenWeatherMap API key."
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to update it? (y/n): " update
    if [ "$update" != "y" ]; then
        echo "Exiting..."
        exit 0
    fi
fi

echo ""
echo "Step 1: Get your API key"
echo "------------------------"
echo "1. Visit: https://openweathermap.org/api"
echo "2. Sign up for a free account"
echo "3. Go to API keys section"
echo "4. Copy your API key"
echo ""
read -p "Press Enter when you have your API key..."

echo ""
echo "Step 2: Enter your API key"
echo "------------------------"
read -p "Paste your API key here: " api_key

if [ -z "$api_key" ]; then
    echo "❌ No API key provided. Exiting..."
    exit 1
fi

# Create .env file
cat > .env << EOF
WEATHER_API_KEY=$api_key
DATABASE_URL=sqlite:///flood_data.db
COLLECTION_INTERVAL_MINUTES=30
EOF

echo ""
echo "✅ .env file created!"
echo ""
echo "Step 3: Testing API key..."
echo "------------------------"

source venv/bin/activate
python scripts/test_weather_api.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Restart your server if it's running"
    echo "2. Real weather data will start flowing automatically"
    echo ""
else
    echo ""
    echo "⚠️  API key test failed. Please check:"
    echo "   - API key is correct"
    echo "   - Wait 2-10 minutes after signup (activation delay)"
    echo "   - Your account is verified"
fi

