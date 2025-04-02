import os
import re
import subprocess
import json
import csv
import asyncio
import pandas as pd
from datetime import datetime
from telethon import TelegramClient, events
from urllib.parse import urlparse

class TelegramDownloader:
    """
    TikTok downloader using Telegram bot integration.
    
    This class manages a Telegram bot that listens for TikTok links in a specified
    chat and downloads them using yt-dlp. It handles metadata extraction and
    provides a way to interact with the downloader from the application.
    """
    
    def __init__(self, config, callback=None):
        """
        Initialize the Telegram downloader.
        
        Args:
            config: Application configuration containing Telegram API credentials
            callback: Optional callback function to notify when videos are downloaded (video_path, title)
        """
        # Telegram API credentials
        self.api_id = config.get("telegram.api_id")
        self.api_hash = config.get("telegram.api_hash")
        self.bot_token = config.get("telegram.bot_token")
        self.chat_id = config.get("telegram.chat_id")
        
        # Directories
        self.videos_dir = config.get("videos_dir", "./videos")
        self.thumbnails_dir = os.path.join(self.videos_dir, "thumbnails")
        
        # Ensure directories exist
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        
        # Metadata file path
        self.metadata_csv = os.path.join(self.videos_dir, "metadata.csv")
        
        # Callback for notifying the application
        self.callback = callback
        
        # Client instance (to be initialized in start method)
        self.client = None
        self.running = False
    
    def initialize_metadata_file(self):
        """Initialize the metadata CSV file if it doesn't exist"""
        if not os.path.exists(self.metadata_csv):
            with open(self.metadata_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Video Name', 'Title', 'Hashtags', 'Thumbnail', 'Channel'])
            print(f"Created new metadata file at {self.metadata_csv}")
    
    def update_metadata(self, video_name, title, hashtags, thumbnail, channel=None):
        """
        Update metadata CSV with new video information.
        
        Args:
            video_name: Video filename
            title: Video title
            hashtags: Video hashtags
            thumbnail: Thumbnail filename
            channel: YouTube channel (optional)
        """
        try:
            # Check if the CSV file exists and is not empty
            if os.path.exists(self.metadata_csv) and os.path.getsize(self.metadata_csv) > 0:
                df = pd.read_csv(self.metadata_csv)
            else:
                # Create new DataFrame with appropriate columns
                df = pd.DataFrame(columns=['Video Name', 'Title', 'Hashtags', 'Thumbnail', 'Channel'])
            
            # Create a new row as a DataFrame
            new_row = pd.DataFrame({
                'Video Name': [video_name],
                'Title': [title],
                'Hashtags': [hashtags],
                'Thumbnail': [thumbnail],
                'Channel': [channel] if channel else [None]
            })
            
            # Append the new row using pd.concat()
            df = pd.concat([df, new_row], ignore_index=True)
            
            # Save back to CSV
            df.to_csv(self.metadata_csv, index=False)
            print(f"Updated metadata for {video_name}")
            
        except Exception as e:
            print(f"Error updating metadata: {e}")
    
    def download_tiktok(self, url, channel=None):
        """
        Download TikTok video using yt-dlp.
        
        Args:
            url: TikTok video URL
            channel: YouTube channel for this video (optional)
            
        Returns:
            video_path: Path to the downloaded video file or None if failed
        """
        try:
            print(f"Starting download for TikTok URL: {url}")
            
            # Generate unique filename using timestamp
            timestamp = int(datetime.now().timestamp() * 1000)
            video_filename = f"tiktok_{timestamp}.mp4"
            video_path = os.path.join(self.videos_dir, video_filename)
            thumbnail_filename = f"tiktok_{timestamp}.jpg"
            thumbnail_path = os.path.join(self.thumbnails_dir, thumbnail_filename)
            
            # Download video info first to get metadata
            info_cmd = [
                'yt-dlp', 
                '--dump-json',
                url
            ]
            
            result = subprocess.run(info_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error getting video info: {result.stderr}")
                return None
            
            # Parse video info
            video_info = json.loads(result.stdout)
            title = video_info.get('title', '').strip()
            description = video_info.get('description', '')
            
            # Extract hashtags from title and description
            hashtags = []
            for text in [title, description]:
                for tag in re.findall(r'#\w+', text):
                    if tag not in hashtags:
                        hashtags.append(tag)
            
            # Format hashtags for metadata
            hashtags_str = " ".join(hashtags) if hashtags else "#TikTok #Viral #Trending"
            
            # Clean up title (remove hashtags)
            for tag in hashtags:
                title = title.replace(tag, '').strip()
            
            if not title:
                title = "TikTok Video"
            
            # Download the video
            download_cmd = [
                'yt-dlp',
                '-o', video_path,
                '--write-thumbnail',
                '--convert-thumbnails', 'jpg',
                '--no-playlist',
                url
            ]
            
            download_result = subprocess.run(download_cmd, capture_output=True, text=True)
            if download_result.returncode != 0:
                print(f"Error downloading video: {download_result.stderr}")
                return None
            
            # Move the thumbnail to the right location
            thumb_source = f"{video_path}.jpg"
            if os.path.exists(thumb_source):
                with open(thumb_source, 'rb') as src_file, open(thumbnail_path, 'wb') as dst_file:
                    dst_file.write(src_file.read())
                os.remove(thumb_source)
                print(f"Thumbnail saved to {thumbnail_path}")
            
            # Update metadata CSV
            self.update_metadata(video_filename, title, hashtags_str, thumbnail_filename, channel)
            
            # If a callback was provided, notify the application
            if self.callback:
                self.callback(video_path, title)
            
            return video_path
        
        except Exception as e:
            print(f"Error downloading TikTok video: {e}")
            return None
    
    @staticmethod
    def is_tiktok_url(url):
        """
        Check if a URL is a TikTok URL.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the URL is a TikTok URL, False otherwise
        """
        tiktok_domains = [
            'tiktok.com', 
            'www.tiktok.com', 
            'm.tiktok.com',
            'vm.tiktok.com',
            'vt.tiktok.com'
        ]
        
        try:
            parsed = urlparse(url)
            return parsed.netloc in tiktok_domains
        except:
            return False
    
    async def handle_new_message(self, event):
        """
        Handle new messages in the Telegram chat.
        
        Args:
            event: Telegram event
        """
        message = event.message
        
        # Extract URLs from message
        urls = re.findall(r'https?://\S+', message.text or '')
        
        tiktok_urls = [url for url in urls if self.is_tiktok_url(url)]
        
        if not tiktok_urls:
            return
        
        for url in tiktok_urls:
            await event.respond(f"📥 Downloading TikTok video: {url}")
            
            # Prompt for channel selection (this would be implemented in a full version)
            # For now, we'll just download the video without a channel
            
            # Download the video using yt-dlp
            video_path = self.download_tiktok(url)
            
            if video_path:
                await event.respond(f"✅ Downloaded and added to queue: {os.path.basename(video_path)}")
            else:
                await event.respond("❌ Failed to download video. Please try a different link.")
    
    async def start_bot(self):
        """Start the Telegram bot and listen for messages"""
        print("Starting TikTok downloader bot...")
        print(f"Listening for TikTok links in Telegram chat ID: {self.chat_id}")
        
        # Initialize the metadata file
        self.initialize_metadata_file()
        
        # Initialize the client
        self.client = TelegramClient('tiktok_downloader_bot', api_id=self.api_id, api_hash=self.api_hash)
        
        # Start the client with the bot token
        await self.client.start(bot_token=self.bot_token)
        
        # Add event handler
        self.client.add_event_handler(self.handle_new_message, events.NewMessage(chats=self.chat_id))
        
        # Keep the client running
        print("Bot is running...")
        self.running = True
        
        # This will run until disconnected
        await self.client.run_until_disconnected()
    
    def start(self):
        """Start the bot in a separate thread (non-blocking)"""
        asyncio.run(self.start_bot())
    
    async def stop_bot(self):
        """Stop the Telegram bot"""
        if self.client:
            await self.client.disconnect()
            self.running = False
            print("Bot stopped")
    
    def stop(self):
        """Stop the bot (may be called from outside asyncio context)"""
        if self.running:
            # Create an event loop to disconnect
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.stop_bot())
            loop.close()

# Function to run the bot directly (for testing)
def run_telegram_bot(api_id, api_hash, bot_token, chat_id):
    """
    Run the Telegram bot directly (for testing).
    
    Args:
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        bot_token: Telegram Bot Token
        chat_id: Telegram Chat ID
    """
    class ConfigMock:
        def __init__(self, api_id, api_hash, bot_token, chat_id):
            self.config = {
                "telegram.api_id": api_id,
                "telegram.api_hash": api_hash,
                "telegram.bot_token": bot_token,
                "telegram.chat_id": chat_id,
                "videos_dir": "./videos"
            }
        
        def get(self, key, default=None):
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
                    
            return value
    
    config_mock = ConfigMock(api_id, api_hash, bot_token, chat_id)
    downloader = TelegramDownloader(config_mock)
    
    # Run the bot
    print("Starting bot directly...")
    downloader.start()

# When run directly, use the values from the script
if __name__ == "__main__":
    # Get the API credentials from environment variables or use defaults
    API_ID = os.environ.get("TELEGRAM_API_ID") or 26760713  # Replace with proper API ID
    API_HASH = os.environ.get("TELEGRAM_API_HASH") or '285bec9b3c310415f3e6aa80aa73bd2e'  # Replace with proper API Hash
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or '7229841716:AAHQ4dOQcH1sHB93KCWUNFGwNHLEC8OSTFc'  # Replace with proper Bot Token
    CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID") or -1002478665968)  # Replace with proper Chat ID
    
    run_telegram_bot(API_ID, API_HASH, BOT_TOKEN, CHAT_ID)