#!/bin/bash

# Gemini Screenplay Studio - Distribute Script
# High Compatibility Version

echo "🎬 Preparing Screenplay Studio for distribution..."

# 1. Use the virtual environment
if [ -d ".venv" ]; then
    echo "🐍 Using virtual environment..."
    source .venv/bin/activate
fi

# 2. Build the executable
echo "🧹 Cleaning up old builds..."
# Kill any running instances of the app to prevent file locking
pkill -f GeminiScreenplayStudio || true
pkill -f studio.py || true
sleep 1
rm -rf dist build
mkdir -p dist


python3 -m PyInstaller --noconfirm --windowed \
    --name "GeminiScreenplayStudio" \
    --add-data "templates:templates" \
    --add-data "tools:tools" \
    --add-data ".env:.env" \
    --collect-all flask_socketio \
    --collect-all engineio \
    --collect-all socketio \
    --collect-all google.genai \
    --collect-all google.api_core \
    --hidden-import eventlet.hubs.epolls \
    --hidden-import eventlet.hubs.kqueue \
    --hidden-import eventlet.hubs.selects \
    --hidden-import dns.dnssec \
    --hidden-import="engineio.async_drivers.threading" \
    studio.py

echo "📄 copying instructions..."
cp INSTRUCTIONS.txt dist/

echo "✅ Build complete!"
echo "📍 The app and instructions are in the 'dist' folder."
