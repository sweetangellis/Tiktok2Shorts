import json
import os
from pathlib import Path

class Config:
    """Configuration manager for the application"""
    
    # Default configuration with sensible presets
    DEFAULT_CONFIG = {
        "ffmpeg_path": "ffmpeg",  # Default assumes FFmpeg is in PATH
        "videos_dir": "./videos",
        "output_dir": "./output",
        "watermarks_dir": "./watermarks",
        "processing": {
            # Visual enhancements
            "color_saturation": 1.2,    # Default color saturation
            "brightness": 1.1,          # Default brightness adjustment
            "zoom_pulse": 1.05,         # Opening zoom pulse effect
            "denoise_strength": 3,      # Temporal denoising (0-10)
            "sharpness": 1.5,           # Sharpening filter strength
            
            # Branding elements
            "watermark_opacity": 0.8,   # Watermark transparency
            
            # Content protection
            "speed_randomization": 0.05, # Random speed variation at end
            "zoom_factor": 1.02,        # Subtle zoom for content protection
            "pixel_shift": 1,           # Pixel shifting
            
            # Output settings
            "audio_normalization": True, # Professional audio normalization
            "crf": 23,                  # Quality (lower is better, 18-28 typical range)
            "bitrate": "2M",            # Video bitrate
            "threads": 4                # Multi-threading support
        },
        "channels": {},  # Will store channel-specific settings
        "telegram": {
            "api_id": "",
            "api_hash": "",
            "bot_token": "",
            "chat_id": ""
        }
    }
    
    def __init__(self, config_file="config.json"):
        """Initialize the configuration manager"""
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config
            config = self.DEFAULT_CONFIG.copy()
            self.save_config(config)
            return config
    
    def save_config(self, config=None):
        """Save current configuration to file"""
        if config is None:
            config = self.config
            
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get configuration value by key
        
        Supports dot notation for nested keys, e.g. 'processing.color_saturation'
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key, value):
        """Set configuration value by key
        
        Supports dot notation for nested keys, e.g. 'processing.color_saturation'
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the correct level
        for i, k in enumerate(keys[:-1]):
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save the updated config
        self.save_config()
        
    def add_channel(self, channel_id, channel_name, watermark_path=None):
        """Add a YouTube channel to the configuration"""
        if "channels" not in self.config:
            self.config["channels"] = {}
            
        self.config["channels"][channel_id] = {
            "name": channel_name,
            "watermark": watermark_path,
            "upload_schedule": {
                "enabled": False,
                "time": "12:00",
                "days": ["Monday", "Wednesday", "Friday"]
            }
        }
        
        self.save_config()
        print(f"Added channel: {channel_name}")
        
    def remove_channel(self, channel_id):
        """Remove a YouTube channel from the configuration"""
        if "channels" in self.config and channel_id in self.config["channels"]:
            channel_name = self.config["channels"][channel_id]["name"]
            del self.config["channels"][channel_id]
            self.save_config()
            print(f"Removed channel: {channel_name}")