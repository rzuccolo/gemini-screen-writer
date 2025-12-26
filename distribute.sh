#!/bin/bash

# Gemini Screenplay Studio - Distribute Script
# This script helps package the app for non-programmers.

echo "🎬 Preparing Screenplay Studio for distribution..."

# 1. Use the virtual environment
if [ -d ".venv" ]; then
    echo "🐍 Using virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No .venv found. Attempting with system python..."
fi

# 2. Ensure PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "📦 PyInstaller not found. Installing..."
    python3 -m pip install pyinstaller
fi

# 3. Build the executable
echo "🏗️ Building standalone executable..."

python3 -m PyInstaller --noconfirm --onefile --windowed \
    --name "GeminiScreenplayStudio" \
    --add-data "templates:templates" \
    --add-data "tools:tools" \
    --collect-all flask_socketio \
    --collect-all google.genai \
    studio.py

echo "✅ Build complete! Check the 'dist' folder for 'GeminiScreenplayStudio'."
echo "📝 Note: Send your friend the 'dist/GeminiScreenplayStudio' file."
