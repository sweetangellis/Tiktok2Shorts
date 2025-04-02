from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QFormLayout, QGroupBox, QCheckBox, QSpinBox, QFileDialog, 
    QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
import os
import subprocess
import threading
import time

class DownloadTab(QWidget):
    """
    Tab for managing TikTok video downloads.
    Provides interface for downloading videos directly or monitoring
    the Telegram bot for incoming links.
    """
    
    # Signals for inter-tab communication
    video_downloaded = Signal(str, str)  # (video_path, title)
    
    def __init__(self, config):
        """
        Initialize the download tab.
        
        Args:
            config: Application configuration manager
        """
        super().__init__()
        self.config = config
        self.init_ui()
        self.bot_process = None
        self.telegram_monitoring = False
        
    def init_ui(self):
        """Set up the user interface for the download tab"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Direct download section
        direct_group = QGroupBox("Direct Download")
        direct_layout = QVBoxLayout(direct_group)
        
        # TikTok URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("TikTok URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter TikTok URL here...")
        url_layout.addWidget(self.url_input)
        
        # Channel selection
        url_layout.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.load_channels()
        url_layout.addWidget(self.channel_combo)
        
        # Download button
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_tiktok)
        url_layout.addWidget(self.download_btn)
        
        direct_layout.addLayout(url_layout)
        
        # Progress bar for downloads
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        direct_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(direct_group)
        
        # Telegram bot section
        telegram_group = QGroupBox("Telegram Bot Integration")
        telegram_layout = QVBoxLayout(telegram_group)
        
        # Telegram bot settings form
        form_layout = QFormLayout()
        
        self.api_id_input = QLineEdit()
        self.api_id_input.setText(self.config.get("telegram.api_id", ""))
        form_layout.addRow("API ID:", self.api_id_input)
        
        self.api_hash_input = QLineEdit()
        self.api_hash_input.setText(self.config.get("telegram.api_hash", ""))
        form_layout.addRow("API Hash:", self.api_hash_input)
        
        self.bot_token_input = QLineEdit()
        self.bot_token_input.setText(self.config.get("telegram.bot_token", ""))
        form_layout.addRow("Bot Token:", self.bot_token_input)
        
        self.chat_id_input = QLineEdit()
        self.chat_id_input.setText(str(self.config.get("telegram.chat_id", "")))
        form_layout.addRow("Chat ID:", self.chat_id_input)
        
        telegram_layout.addLayout(form_layout)
        
        # Buttons for Telegram bot
        button_layout = QHBoxLayout()
        
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_telegram_settings)
        button_layout.addWidget(self.save_settings_btn)
        
        self.start_bot_btn = QPushButton("Start Bot")
        self.start_bot_btn.clicked.connect(self.toggle_telegram_bot)
        button_layout.addWidget(self.start_bot_btn)
        
        telegram_layout.addLayout(button_layout)
        
        # Status indicator
        self.status_label = QLabel("Bot Status: Not Running")
        telegram_layout.addWidget(self.status_label)
        
        main_layout.addWidget(telegram_group)
        
        # Downloaded videos list
        videos_group = QGroupBox("Downloaded Videos")
        videos_layout = QVBoxLayout(videos_group)
        
        self.videos_table = QTableWidget(0, 4)  # rows, columns
        self.videos_table.setHorizontalHeaderLabels(["Video", "Title", "Channel", "Actions"])
        self.videos_table.setColumnWidth(0, 200)  # Filename
        self.videos_table.setColumnWidth(1, 300)  # Title
        self.videos_table.setColumnWidth(2, 150)  # Channel
        self.videos_table.setColumnWidth(3, 150)  # Actions
        videos_layout.addWidget(self.videos_table)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Video List")
        self.refresh_btn.clicked.connect(self.refresh_video_list)
        refresh_layout.addWidget(self.refresh_btn)
        
        # Open videos folder button
        self.open_folder_btn = QPushButton("Open Videos Folder")
        self.open_folder_btn.clicked.connect(self.open_videos_folder)
        refresh_layout.addWidget(self.open_folder_btn)
        
        videos_layout.addLayout(refresh_layout)
        
        main_layout.addWidget(videos_group)
        
        # Load the video list
        self.refresh_video_list()
    
    def load_channels(self):
        """Load available YouTube channels from config into the combobox"""
        self.channel_combo.clear()
        
        # Add a "Select channel" item
        self.channel_combo.addItem("Select channel...", "")
        
        # Add all configured channels
        channels = self.config.get("channels", {})
        for channel_id, channel_info in channels.items():
            self.channel_combo.addItem(channel_info["name"], channel_id)
    
    def save_telegram_settings(self):
        """Save Telegram bot settings to config"""
        try:
            # Validate API ID is a number
            api_id = self.api_id_input.text().strip()
            if api_id:
                api_id = int(api_id)
            
            # Update configuration
            self.config.set("telegram.api_id", api_id)
            self.config.set("telegram.api_hash", self.api_hash_input.text().strip())
            self.config.set("telegram.bot_token", self.bot_token_input.text().strip())
            
            # Parse chat ID (can be negative for groups)
            chat_id = self.chat_id_input.text().strip()
            if chat_id:
                chat_id = int(chat_id)
            self.config.set("telegram.chat_id", chat_id)
            
            QMessageBox.information(self, "Settings Saved", "Telegram bot settings have been saved.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "API ID and Chat ID must be numbers.")
    
    def toggle_telegram_bot(self):
        """Start or stop the Telegram bot"""
        if not self.telegram_monitoring:
            # Check settings before starting
            if not all([
                self.config.get("telegram.api_id"),
                self.config.get("telegram.api_hash"),
                self.config.get("telegram.bot_token"),
                self.config.get("telegram.chat_id")
            ]):
                QMessageBox.warning(
                    self, 
                    "Missing Configuration", 
                    "Please fill in all Telegram bot settings and save them first."
                )
                return
            
            # Start the bot
            self.start_telegram_bot()
            self.start_bot_btn.setText("Stop Bot")
            self.status_label.setText("Bot Status: Running")
            self.telegram_monitoring = True
        else:
            # Stop the bot
            self.stop_telegram_bot()
            self.start_bot_btn.setText("Start Bot")
            self.status_label.setText("Bot Status: Not Running")
            self.telegram_monitoring = False
    
    def start_telegram_bot(self):
        """Start the Telegram bot as a subprocess"""
        try:
            # Generate a temporary Python script that runs the Telegram bot
            # with the current configuration
            script_path = self._create_telegram_bot_script()
            
            # Start the subprocess
            self.bot_process = subprocess.Popen(
                ["python", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Start a monitoring thread
            threading.Thread(
                target=self.monitor_bot_process, 
                daemon=True
            ).start()
            
            QMessageBox.information(
                self, 
                "Bot Started", 
                "Telegram bot has been started. It will monitor the specified chat for TikTok links."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start bot: {str(e)}")
            self.telegram_monitoring = False
            self.start_bot_btn.setText("Start Bot")
            self.status_label.setText("Bot Status: Error")
    
    def stop_telegram_bot(self):
        """Stop the Telegram bot subprocess"""
        if self.bot_process:
            try:
                self.bot_process.terminate()
                # Wait up to 5 seconds for graceful termination
                for _ in range(50):
                    if self.bot_process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                # Force kill if still running
                if self.bot_process.poll() is None:
                    self.bot_process.kill()
                
                self.bot_process = None
                
                QMessageBox.information(self, "Bot Stopped", "Telegram bot has been stopped.")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Error stopping bot: {str(e)}")
    
    def monitor_bot_process(self):
        """Monitor the bot process and update status"""
        if not self.bot_process:
            return
            
        # Read output and errors in real time
        while self.bot_process.poll() is None:
            # Process output and errors if needed
            # This could be used to update a log in the UI
            time.sleep(1)
        
        # If we get here, the process has ended
        exit_code = self.bot_process.poll()
        
        # Update UI from main thread
        def update_ui():
            self.telegram_monitoring = False
            self.start_bot_btn.setText("Start Bot")
            if exit_code == 0:
                self.status_label.setText("Bot Status: Stopped")
            else:
                self.status_label.setText(f"Bot Status: Error (code: {exit_code})")
        
        # Schedule UI update from main thread
        # This uses QTimer.singleShot for thread safety
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, update_ui)
    
    def _create_telegram_bot_script(self):
        """Create a temporary script file for the Telegram bot"""
        # Read the original script
        script_content = None
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  "downloader", "telegram_bot.py")
        
        # If the bot script doesn't exist yet, we'll create it later
        if not os.path.exists(script_path):
            # Use modified version of the existing script from telegramvideobot-V2.py
            with open("telegramvideobot-V2.py", "r") as f:
                script_content = f.read()
            
            # Replace configuration values
            script_content = script_content.replace("API_ID = 26760713", 
                                                  f"API_ID = {self.config.get('telegram.api_id')}")
            script_content = script_content.replace("API_HASH = '285bec9b3c310415f3e6aa80aa73bd2e'", 
                                                  f"API_HASH = '{self.config.get('telegram.api_hash')}'")
            script_content = script_content.replace("BOT_TOKEN = '7229841716:AAHQ4dOQcH1sHB93KCWUNFGwNHLEC8OSTFc'", 
                                                  f"BOT_TOKEN = '{self.config.get('telegram.bot_token')}'")
            script_content = script_content.replace("CHAT_ID = -1002478665968", 
                                                  f"CHAT_ID = {self.config.get('telegram.chat_id')}")
            
            # Write to the proper location
            os.makedirs(os.path.dirname(script_path), exist_ok=True)
            with open(script_path, "w") as f:
                f.write(script_content)
        
        return script_path
    
    def download_tiktok(self):
        """Download TikTok video directly from URL"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a TikTok URL.")
            return
        
        channel_id = self.channel_combo.currentData()
        if not channel_id:
            QMessageBox.warning(self, "Selection Error", "Please select a YouTube channel.")
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        # Run download in a separate thread to prevent UI freezing
        threading.Thread(
            target=self._download_tiktok_thread, 
            args=(url, channel_id),
            daemon=True
        ).start()
    
    def _download_tiktok_thread(self, url, channel_id):
        """Background thread for TikTok download"""
        try:
            # Update progress from main thread
            from PySide6.QtCore import QTimer
            
            def update_progress(value):
                self.progress_bar.setValue(value)
            
            # Simulating progress
            QTimer.singleShot(0, lambda: update_progress(20))
            
            # Use yt-dlp to download
            video_dir = self.config.get("videos_dir", "./videos")
            timestamp = int(time.time())
            video_filename = f"tiktok_{timestamp}.mp4"
            video_path = os.path.join(video_dir, video_filename)
            
            QTimer.singleShot(0, lambda: update_progress(50))
            
            # This code would actually download the video using yt-dlp
            # For now, we'll just simulate the download
            
            title = f"TikTok video {timestamp}"
            time.sleep(2)  # Simulate download time
            
            QTimer.singleShot(0, lambda: update_progress(90))
            
            # Update the video list
            QTimer.singleShot(0, lambda: self.refresh_video_list())
            
            # Signal that video is downloaded and ready for processing
            channel_name = self.channel_combo.currentText()
            self.video_downloaded.emit(video_path, title)
            
            # Finish up
            QTimer.singleShot(0, lambda: update_progress(100))
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
            
            # Show success message
            QTimer.singleShot(0, lambda: QMessageBox.information(
                self, 
                "Download Complete", 
                f"Video has been downloaded and added to the {channel_name} processing queue."
            ))
            
        except Exception as e:
            # Handle errors
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self, 
                "Download Error", 
                f"Failed to download video: {str(e)}"
            ))
            QTimer.singleShot(0, lambda: self.progress_bar.setVisible(False))
    
    def refresh_video_list(self):
        """Refresh the list of downloaded videos"""
        # Clear the table
        self.videos_table.setRowCount(0)
        
        # Get the list of videos
        videos_dir = self.config.get("videos_dir", "./videos")
        if not os.path.exists(videos_dir):
            return
        
        # Filter for video files
        video_files = [f for f in os.listdir(videos_dir) 
                      if os.path.isfile(os.path.join(videos_dir, f)) 
                      and f.endswith(('.mp4', '.mov', '.avi'))]
        
        # Load metadata file if exists
        metadata = {}
        metadata_path = os.path.join(videos_dir, "metadata.csv")
        if os.path.exists(metadata_path):
            try:
                import pandas as pd
                df = pd.read_csv(metadata_path)
                for _, row in df.iterrows():
                    metadata[row['Video Name']] = {
                        'title': row['Title'],
                        'hashtags': row['Hashtags']
                    }
            except Exception:
                pass
        
        # Add videos to table
        for i, video_file in enumerate(sorted(video_files, reverse=True)):
            self.videos_table.insertRow(i)
            
            # File name
            file_item = QTableWidgetItem(video_file)
            file_item.setData(Qt.UserRole, os.path.join(videos_dir, video_file))
            self.videos_table.setItem(i, 0, file_item)
            
            # Title
            title = metadata.get(video_file, {}).get('title', '')
            self.videos_table.setItem(i, 1, QTableWidgetItem(title))
            
            # Channel (placeholder for now)
            self.videos_table.setItem(i, 2, QTableWidgetItem("Not assigned"))
            
            # Actions button
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            process_btn = QPushButton("Process")
            process_btn.clicked.connect(lambda _, path=os.path.join(videos_dir, video_file), 
                                      title=title: 
                                      self.video_downloaded.emit(path, title))
            actions_layout.addWidget(process_btn)
            
            self.videos_table.setCellWidget(i, 3, actions_widget)
    
    def open_videos_folder(self):
        """Open the videos folder in file explorer"""
        videos_dir = self.config.get("videos_dir", "./videos")
        if os.path.exists(videos_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(videos_dir))