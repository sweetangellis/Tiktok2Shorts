from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDateTimeEdit, QLineEdit,
    QFormLayout, QGroupBox, QCheckBox, QComboBox, QMessageBox, 
    QProgressBar, QCalendarWidget, QDialog, QListWidget, QInputDialog
)
from PySide6.QtCore import Qt, QDateTime, Signal
import os
import time

class ScheduleDialog(QDialog):
    """Dialog for scheduling uploads"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Upload")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Calendar for date selection
        self.calendar = QCalendarWidget()
        layout.addWidget(self.calendar)
        
        # Time selection
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time:"))
        
        self.time_edit = QDateTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setDateTime(QDateTime.currentDateTime())
        time_layout.addWidget(self.time_edit)
        
        layout.addLayout(time_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def get_schedule(self):
        """Get the selected schedule date and time"""
        date = self.calendar.selectedDate()
        time = self.time_edit.time()
        
        qdt = QDateTime(date, time)
        return qdt.toString("yyyy-MM-dd HH:mm:ss")

class ChannelDialog(QDialog):
    """Dialog for selecting a YouTube channel"""
    
    def __init__(self, channels, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select YouTube Channel")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Channel list
        self.channel_list = QListWidget()
        for channel_id, channel_info in channels.items():
            self.channel_list.addItem(channel_info["name"])
            # Store channel ID as item data
            self.channel_list.item(self.channel_list.count() - 1).setData(Qt.UserRole, channel_id)
        
        layout.addWidget(self.channel_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def get_selected_channel(self):
        """Get the selected channel ID and name"""
        selected_items = self.channel_list.selectedItems()
        if not selected_items:
            return None, None
            
        channel_name = selected_items[0].text()
        channel_id = selected_items[0].data(Qt.UserRole)
        
        return channel_id, channel_name

class UploadTab(QWidget):
    """
    Tab for YouTube upload management.
    Provides interface for scheduling and monitoring uploads.
    """
    
    def __init__(self, config):
        """
        Initialize the upload tab.
        
        Args:
            config: Application configuration manager
        """
        super().__init__()
        self.config = config
        self.upload_queue = []
        self.init_ui()
    
    def init_ui(self):
        """Set up the user interface for the upload tab"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "This tab will allow you to manage YouTube uploads.\n"
            "YouTube API integration will be implemented in a future version."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(info_label)
        
        # Upload queue
        queue_group = QGroupBox("Upload Queue")
        queue_layout = QVBoxLayout(queue_group)
        
        # Queue table
        self.queue_table = QTableWidget(0, 5)  # rows, columns
        self.queue_table.setHorizontalHeaderLabels(["Video", "Channel", "Status", "Schedule", "Actions"])
        self.queue_table.setColumnWidth(0, 250)  # Video
        self.queue_table.setColumnWidth(1, 150)  # Channel
        self.queue_table.setColumnWidth(2, 100)  # Status
        self.queue_table.setColumnWidth(3, 150)  # Schedule
        self.queue_table.setColumnWidth(4, 150)  # Actions
        queue_layout.addWidget(self.queue_table)
        
        # Queue buttons
        buttons_layout = QHBoxLayout()
        
        self.upload_all_btn = QPushButton("Upload All Now")
        self.upload_all_btn.clicked.connect(self.upload_all)
        buttons_layout.addWidget(self.upload_all_btn)
        
        self.clear_queue_btn = QPushButton("Clear Completed")
        self.clear_queue_btn.clicked.connect(self.clear_completed)
        buttons_layout.addWidget(self.clear_queue_btn)
        
        queue_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(queue_group)
        
        # Channel management
        channel_group = QGroupBox("YouTube Channels")
        channel_layout = QVBoxLayout(channel_group)
        
        # Channel table
        self.channel_table = QTableWidget(0, 3)  # rows, columns
        self.channel_table.setHorizontalHeaderLabels(["Channel", "Videos", "Status"])
        self.channel_table.setColumnWidth(0, 250)  # Channel
        self.channel_table.setColumnWidth(1, 100)  # Videos
        self.channel_table.setColumnWidth(2, 150)  # Status
        channel_layout.addWidget(self.channel_table)
        
        # Channel buttons
        channel_buttons = QHBoxLayout()
        
        self.add_channel_btn = QPushButton("Add Channel")
        self.add_channel_btn.clicked.connect(self.add_channel)
        channel_buttons.addWidget(self.add_channel_btn)
        
        self.remove_channel_btn = QPushButton("Remove Channel")
        self.remove_channel_btn.clicked.connect(self.remove_channel)
        channel_buttons.addWidget(self.remove_channel_btn)
        
        self.auth_channel_btn = QPushButton("Authenticate")
        self.auth_channel_btn.clicked.connect(self.authenticate_channel)
        channel_buttons.addWidget(self.auth_channel_btn)
        
        channel_layout.addLayout(channel_buttons)
        
        main_layout.addWidget(channel_group)
        
        # Schedule management
        schedule_group = QGroupBox("Upload Schedule")
        schedule_layout = QVBoxLayout(schedule_group)
        
        # Schedule info text
        schedule_info = QLabel(
            "Automated upload scheduling will be implemented in a future version.\n"
            "This will allow you to set specific upload times for each channel."
        )
        schedule_info.setWordWrap(True)
        schedule_layout.addWidget(schedule_info)
        
        # Schedule settings (will be implemented later)
        
        main_layout.addWidget(schedule_group)
        
        # Initialize the channel table
        self.update_channel_table()
        
        # Initialize the upload queue
        self.update_queue_table()
    
    def add_to_queue(self, video_path, title=""):
        """
        Add a video to the upload queue.
        Called when metadata is complete.
        
        Args:
            video_path: Path to the video file
            title: Video title (optional)
        """
        # Check if the video exists
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "File Not Found", f"Video file not found: {video_path}")
            return
        
        # Select channel for upload
        channels = self.config.get("channels", {})
        if not channels:
            QMessageBox.warning(
                self,
                "No Channels Configured",
                "Please add YouTube channels before uploading videos."
            )
            return
            
        dialog = ChannelDialog(channels, self)
        if dialog.exec() != QDialog.Accepted:
            return
            
        channel_id, channel_name = dialog.get_selected_channel()
        if not channel_id:
            return
        
        # Schedule the upload
        schedule_dialog = ScheduleDialog(self)
        if schedule_dialog.exec() != QDialog.Accepted:
            # Default to "now" if cancelled
            schedule_time = "Now"
        else:
            schedule_time = schedule_dialog.get_schedule()
        
        # Add to queue
        self.upload_queue.append({
            "video_path": video_path,
            "title": title,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "status": "Queued",
            "schedule": schedule_time
        })
        
        # Update the queue display
        self.update_queue_table()
        
        QMessageBox.information(
            self,
            "Added to Queue",
            f"Video \"{title}\" has been added to the upload queue for channel {channel_name}."
        )
    
    def update_queue_table(self):
        """Update the upload queue table display"""
        # Clear the table
        self.queue_table.setRowCount(0)
        
        # Add videos to table
        for i, item in enumerate(self.upload_queue):
            self.queue_table.insertRow(i)
            
            # Video filename
            filename = os.path.basename(item["video_path"])
            title_item = QTableWidgetItem(item["title"] or filename)
            self.queue_table.setItem(i, 0, title_item)
            
            # Channel
            self.queue_table.setItem(i, 1, QTableWidgetItem(item["channel_name"]))
            
            # Status
            self.queue_table.setItem(i, 2, QTableWidgetItem(item["status"]))
            
            # Schedule
            self.queue_table.setItem(i, 3, QTableWidgetItem(str(item["schedule"])))
            
            # Actions buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            if item["status"] == "Queued":
                upload_btn = QPushButton("Upload Now")
                upload_btn.clicked.connect(lambda _, idx=i: self.upload_item(idx))
                actions_layout.addWidget(upload_btn)
                
                remove_btn = QPushButton("Remove")
                remove_btn.clicked.connect(lambda _, idx=i: self.remove_item(idx))
                actions_layout.addWidget(remove_btn)
            elif item["status"] == "Uploading":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(lambda _, idx=i: self.cancel_upload(idx))
                actions_layout.addWidget(cancel_btn)
            elif item["status"] == "Completed":
                view_btn = QPushButton("View Online")
                view_btn.clicked.connect(lambda _, idx=i: self.view_online(idx))
                actions_layout.addWidget(view_btn)
            elif item["status"] == "Failed":
                retry_btn = QPushButton("Retry")
                retry_btn.clicked.connect(lambda _, idx=i: self.retry_upload(idx))
                actions_layout.addWidget(retry_btn)
            
            self.queue_table.setCellWidget(i, 4, actions_widget)
    
    def update_channel_table(self):
        """Update the channel table display"""
        # Clear the table
        self.channel_table.setRowCount(0)
        
        # Get channels from config
        channels = self.config.get("channels", {})
        
        # Add channels to table
        for i, (channel_id, channel_info) in enumerate(channels.items()):
            self.channel_table.insertRow(i)
            
            # Channel name
            self.channel_table.setItem(i, 0, QTableWidgetItem(channel_info["name"]))
            
            # Video count (placeholder)
            self.channel_table.setItem(i, 1, QTableWidgetItem("0"))
            
            # Status (placeholder)
            self.channel_table.setItem(i, 2, QTableWidgetItem("Not Authenticated"))
    
    def add_channel(self):
        """Add a new YouTube channel"""
        # In a real implementation, this would use OAuth2 to authenticate
        # and get the channel ID and name
        # For now, just use a simple dialog to get channel details
        
        # Simple dialog for channel name
        channel_name, ok = QInputDialog.getText(
            self,
            "Add YouTube Channel",
            "Enter channel name:"
        )
        
        if ok and channel_name:
            # Generate a placeholder channel ID
            channel_id = f"channel_{int(time.time())}"
            
            # Add to config
            self.config.add_channel(channel_id, channel_name)
            
            # Update table
            self.update_channel_table()
    
    def remove_channel(self):
        """Remove a YouTube channel"""
        # Get selected channel
        selected_items = self.channel_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a channel to remove.")
            return
            
        channel_name = selected_items[0].text()
        
        # Find channel ID
        channel_id = None
        for cid, info in self.config.get("channels", {}).items():
            if info["name"] == channel_name:
                channel_id = cid
                break
                
        if not channel_id:
            return
        
        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Remove Channel",
            f"Are you sure you want to remove the channel \"{channel_name}\"?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from config
            self.config.remove_channel(channel_id)
            
            # Update table
            self.update_channel_table()
    
    def authenticate_channel(self):
        """Authenticate a YouTube channel"""
        QMessageBox.information(
            self,
            "Not Implemented",
            "YouTube authentication will be implemented in a future version."
        )
    
    def upload_item(self, index):
        """Upload a specific queue item"""
        if index < 0 or index >= len(self.upload_queue):
            return
            
        # Simulate upload process
        item = self.upload_queue[index]
        item["status"] = "Simulating Upload"
        self.update_queue_table()
        
        # In a real implementation, this would use the YouTube API
        QMessageBox.information(
            self,
            "Upload Simulation",
            f"Upload simulation for \"{item['title']}\" to channel {item['channel_name']}.\n\n"
            f"In the final implementation, this will use the YouTube API to upload the video."
        )
        
        # Update status
        item["status"] = "Completed"
        self.update_queue_table()
    
    def upload_all(self):
        """Upload all queued videos"""
        queued_items = [item for item in self.upload_queue if item["status"] == "Queued"]
        if not queued_items:
            QMessageBox.information(self, "No Videos", "No videos in the upload queue.")
            return
            
        # Confirm upload
        reply = QMessageBox.question(
            self,
            "Upload All",
            f"Are you sure you want to upload {len(queued_items)} videos now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Upload each item
            for i, item in enumerate(self.upload_queue):
                if item["status"] == "Queued":
                    self.upload_item(i)
    
    def remove_item(self, index):
        """Remove an item from the queue"""
        if index < 0 or index >= len(self.upload_queue):
            return
            
        # Remove the item
        self.upload_queue.pop(index)
        self.update_queue_table()
    
    def cancel_upload(self, index):
        """Cancel an ongoing upload"""
        QMessageBox.information(
            self,
            "Not Implemented",
            "Upload cancellation will be implemented in a future version."
        )
    
    def retry_upload(self, index):
        """Retry a failed upload"""
        if index < 0 or index >= len(self.upload_queue):
            return
            
        # Reset status
        self.upload_queue[index]["status"] = "Queued"
        self.update_queue_table()
        
        # Retry upload
        self.upload_item(index)
    
    def view_online(self, index):
        """View an uploaded video online"""
        QMessageBox.information(
            self,
            "Not Implemented",
            "Viewing videos online will be implemented in a future version."
        )
    
    def clear_completed(self):
        """Clear completed uploads from the queue"""
        # Filter out completed items
        self.upload_queue = [item for item in self.upload_queue if item["status"] != "Completed"]
        self.update_queue_table()
        
        QMessageBox.information(self, "Queue Cleared", "Completed uploads have been cleared from the queue.")