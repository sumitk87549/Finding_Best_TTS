#!/bin/bash

# Test script for Sooktam2 TTS
echo "🎙️  Testing Sooktam2 TTS Generator"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    exit 1
fi

# Check if input file exists
if [ ! -f "sooktam2_test.txt" ]; then
    echo "❌ Test file sooktam2_test.txt not found"
    exit 1
fi

echo "📦 Installing requirements..."
pip install -r requirements.txt

echo ""
echo "🚀 Running Sooktam2 TTS with mixed Hinglish text..."
echo ""

# Run the TTS script
python3 sooktam2_tts.py sooktam2_test.txt --output sooktam2_demo.wav --language mixed

echo ""
echo "✅ Test completed!"
echo "📁 Check the generated audio file: sooktam2_demo.wav"
