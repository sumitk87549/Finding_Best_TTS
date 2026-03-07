#!/usr/bin/env python3
"""
TTS Test Script for samudr-ai/svara-tts-v1-hindi-ft
Usage: 
    1. Start vLLM server:
       vllm serve samudr-ai/svara-tts-v1-hindi-ft --port 8000 --trust-remote-code --gpu-memory-utilization 0.85 --max-model-len 4096

    2. Run this script:
       python test_tts_model.py <text_file_path>
"""

import argparse
import os
import sys
import wave
from pathlib import Path

import requests


def parse_text_file(file_path):
    """Read and clean text from file."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    return text


def generate_tts(text, base_url="http://localhost:8000/v1", speaker_id="Hindi (Male)"):
    """Generate TTS audio using the Svara-TTS API."""
    url = f"{base_url}/tts"

    payload = {
        "input": text,
        "speaker_id": speaker_id,
        "speed": 1.0,
        "pitch": 1.0
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=300)
    response.raise_for_status()
    return response.content


def save_audio_bytes(audio_bytes, output_path):
    """Save audio bytes to WAV file."""
    with open(output_path, "wb") as f:
        f.write(audio_bytes)


def check_server_status(base_url="http://localhost:8000/v1"):
    """Check if vLLM server is running."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test TTS with samudr-ai/svara-tts-v1-hindi-ft model"
    )
    parser.add_argument(
        "text_file_path",
        type=str,
        help="Path to text file containing text to synthesize",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000/v1",
        help="Base URL of the vLLM server",
    )
    parser.add_argument(
        "--speaker-id",
        type=str,
        default="Hindi (Male)",
        help="Speaker ID for voice",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tts_output",
        help="Directory to save generated audio files",
    )
    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.text_file_path):
        print(f"Error: File not found: {args.text_file_path}")
        sys.exit(1)

    # Check server status
    print(f"Checking server at {args.base_url}...")
    if not check_server_status(args.base_url):
        print("Error: vLLM server is not running!")
        print("Please start the server first:")
        print("  vllm serve samudr-ai/svara-tts-v1-hindi-ft \\")
        print("    --port 8000 \\")
        print("    --trust-remote-code \\")
        print("    --gpu-memory-utilization 0.85 \\")
        print("    --max-model-len 4096")
        sys.exit(1)

    print("Server is running!")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read text
    text = parse_text_file(args.text_file_path)
    print(f"Text from {args.text_file_path}:")
    print(f"  {text[:100]}..." if len(text) > 100 else f"  {text}")
    print(f"  Character count: {len(text)}")
    print(f"  Speaker: {args.speaker_id}")

    # Generate audio
    print("Generating TTS audio...")
    audio_bytes = generate_tts(text, base_url=args.base_url, speaker_id=args.speaker_id)

    # Save audio
    input_basename = os.path.splitext(os.path.basename(args.text_file_path))[0]
    output_filename = f"{input_basename}_tts.wav"
    output_path = output_dir / output_filename
    save_audio_bytes(audio_bytes, str(output_path))

    print(f"Audio saved to: {output_path}")
    print(f"File size: {len(audio_bytes) / 1024:.2f} KB")


if __name__ == "__main__":
    main()
