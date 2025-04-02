#!/bin/bash

# TikTok to YouTube Shorts Automation Setup Script
# This script installs all dependencies required for the application

echo "Setting up TikTok to YouTube Shorts Automation..."

# Create necessary directories if they don't exist
mkdir -p videos
mkdir -p videos/thumbnails
mkdir -p videos/processed
mkdir -p watermarks
mkdir -p output

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed. Installing Python 3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Create a virtual environment
if [ ! -d "venv" ]; then
    echo "Creating a virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install FFmpeg if not already installed
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is not installed. Installing FFmpeg..."
    sudo apt update
    sudo apt install -y ffmpeg
fi

# Install yt-dlp for TikTok video downloading
if ! command -v yt-dlp &> /dev/null; then
    echo "Installing yt-dlp for video downloading..."
    sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
    sudo chmod a+rx /usr/local/bin/yt-dlp
fi

# Create a basic config file if it doesn't exist
if [ ! -f "config.json" ]; then
    echo "Creating default configuration file..."
    cat > config.json << EOF
{
    "ffmpeg_path": "ffmpeg",
    "videos_dir": "./videos",
    "output_dir": "./output",
    "watermarks_dir": "./watermarks",
    "processing": {
        "color_saturation": 1.2,
        "brightness": 1.1,
        "zoom_pulse": 1.05,
        "denoise_strength": 3,
        "sharpness": 1.5,
        "watermark_opacity": 0.8,
        "speed_randomization": 0.05,
        "zoom_factor": 1.02,
        "pixel_shift": 1,
        "audio_normalization": true,
        "crf": 23,
        "bitrate": "2M",
        "threads": 4
    },
    "channels": {},
    "telegram": {
        "api_id": "",
        "api_hash": "",
        "bot_token": "",
        "chat_id": ""
    }
}
EOF
fi

echo "Setup complete! You can now run the application with: python3 main.py"
echo "For development, activate the virtual environment with: source venv/bin/activate"