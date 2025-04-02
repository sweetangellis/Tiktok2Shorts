from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit,
    QFormLayout, QGroupBox, QCheckBox, QSpinBox, QFileDialog, 
    QMessageBox, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, Signal
import os

class MetadataTab(QWidget):
    """
    Tab for generating and editing video metadata for YouTube uploads.
    Provides interface for AI-assisted metadata creation and optimization.
    """
    
    # Signals for inter-tab communication
    metadata_ready = Signal(str, str)  # (video_path, title)
    
    def __init__(self, config):
        """
        Initialize the metadata tab.
        
        Args:
            config: Application configuration manager
        """
        super().__init__()
        self.config = config
        self.videos = []  # List of videos with metadata
        self.init_ui()
    
    def init_ui(self):
        """Set up the user interface for the metadata tab"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "This tab will allow you to generate and edit metadata for YouTube uploads.\n"
            "AI-assisted metadata generation will be implemented in a future version."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(info_label)
        
        # Videos with metadata table
        videos_group = QGroupBox("Videos Ready for Metadata")
        videos_layout = QVBoxLayout(videos_group)
        
        self.videos_table = QTableWidget(0, 4)  # rows, columns
        self.videos_table.setHorizontalHeaderLabels(["Video", "Title", "Channel", "Actions"])
        self.videos_table.setColumnWidth(0, 250)  # Video
        self.videos_table.setColumnWidth(1, 300)  # Title
        self.videos_table.setColumnWidth(2, 150)  # Channel
        self.videos_table.setColumnWidth(3, 150)  # Actions
        videos_layout.addWidget(self.videos_table)
        
        main_layout.addWidget(videos_group)
        
        # Metadata editor
        editor_group = QGroupBox("Metadata Editor")
        editor_layout = QFormLayout(editor_group)
        
        # Video title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter video title...")
        editor_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter video description...")
        self.description_input.setMinimumHeight(100)
        editor_layout.addRow("Description:", self.description_input)
        
        # Tags
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Enter tags separated by commas...")
        editor_layout.addRow("Tags:", self.tags_input)
        
        # AI generation buttons
        buttons_layout = QHBoxLayout()
        
        self.generate_title_btn = QPushButton("Generate Title")
        self.generate_title_btn.setEnabled(False)  # Disabled for now
        buttons_layout.addWidget(self.generate_title_btn)
        
        self.generate_desc_btn = QPushButton("Generate Description")
        self.generate_desc_btn.setEnabled(False)  # Disabled for now
        buttons_layout.addWidget(self.generate_desc_btn)
        
        self.generate_tags_btn = QPushButton("Generate Tags")
        self.generate_tags_btn.setEnabled(False)  # Disabled for now
        buttons_layout.addWidget(self.generate_tags_btn)
        
        self.generate_all_btn = QPushButton("Generate All")
        self.generate_all_btn.setEnabled(False)  # Disabled for now
        buttons_layout.addWidget(self.generate_all_btn)
        
        editor_layout.addRow("AI Generation:", buttons_layout)
        
        # Save and Next buttons
        actions_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Metadata")
        self.save_btn.clicked.connect(self.save_metadata)
        actions_layout.addWidget(self.save_btn)
        
        self.next_btn = QPushButton("Next Step (Upload)")
        self.next_btn.clicked.connect(self.next_step)
        actions_layout.addWidget(self.next_btn)
        
        editor_layout.addRow("Actions:", actions_layout)
        
        main_layout.addWidget(editor_group)
        
        # Initialize the videos list
        self.update_videos_table()
    
    def add_video(self, video_path, title=""):
        """
        Add a video for metadata generation.
        Called when a video is processed.
        
        Args:
            video_path: Path to the video file
            title: Video title (optional)
        """
        # Check if the video exists
        if not os.path.exists(video_path):
            return
        
        # Check if video is already in the list
        for video in self.videos:
            if video["video_path"] == video_path:
                # Already exists, just update it
                video["title"] = title
                self.update_videos_table()
                return
        
        # Add to list
        self.videos.append({
            "video_path": video_path,
            "title": title,
            "description": "",
            "tags": "",
            "channel": "Default", # This would be updated with actual channel info
            "thumbnail": ""
        })
        
        # Update the table
        self.update_videos_table()
    
    def update_videos_table(self):
        """Update the videos table display"""
        # Clear the table
        self.videos_table.setRowCount(0)
        
        # Add videos to table
        for i, video in enumerate(self.videos):
            self.videos_table.insertRow(i)
            
            # Video filename
            filename = os.path.basename(video["video_path"])
            self.videos_table.setItem(i, 0, QTableWidgetItem(filename))
            
            # Title
            self.videos_table.setItem(i, 1, QTableWidgetItem(video["title"]))
            
            # Channel
            self.videos_table.setItem(i, 2, QTableWidgetItem(video["channel"]))
            
            # Actions button
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _, idx=i: self.edit_metadata(idx))
            actions_layout.addWidget(edit_btn)
            
            self.videos_table.setCellWidget(i, 3, actions_widget)
    
    def edit_metadata(self, index):
        """Edit metadata for a specific video"""
        if index < 0 or index >= len(self.videos):
            return
            
        # Get the video data
        video = self.videos[index]
        
        # Populate the form
        self.title_input.setText(video["title"])
        self.description_input.setText(video["description"])
        self.tags_input.setText(video["tags"])
        
        # Store the index of the video being edited
        self.current_edit_index = index
    
    def save_metadata(self):
        """Save the current metadata to the selected video"""
        if not hasattr(self, 'current_edit_index'):
            QMessageBox.warning(self, "No Video Selected", "Please select a video first.")
            return
            
        if self.current_edit_index < 0 or self.current_edit_index >= len(self.videos):
            return
            
        # Update the video data
        self.videos[self.current_edit_index]["title"] = self.title_input.text()
        self.videos[self.current_edit_index]["description"] = self.description_input.toPlainText()
        self.videos[self.current_edit_index]["tags"] = self.tags_input.text()
        
        # Update the table
        self.update_videos_table()
        
        QMessageBox.information(self, "Metadata Saved", "Metadata has been saved.")
    
    def next_step(self):
        """Move to the next step (upload tab)"""
        if not hasattr(self, 'current_edit_index'):
            QMessageBox.warning(self, "No Video Selected", "Please select a video first.")
            return
            
        if self.current_edit_index < 0 or self.current_edit_index >= len(self.videos):
            return
            
        # Save metadata
        self.save_metadata()
        
        # Emit signal to move to upload tab
        video = self.videos[self.current_edit_index]
        self.metadata_ready.emit(video["video_path"], video["title"])
        
        QMessageBox.information(
            self,
            "Ready for Upload",
            f"Video \"{video['title']}\" is ready for upload. Switching to Upload tab."
        )