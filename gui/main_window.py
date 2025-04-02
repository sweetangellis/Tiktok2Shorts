from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLabel,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QDialog, 
    QVBoxLayout, QPushButton, QFileDialog
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, QSize

# Import all our tab classes
from gui.process_tab import ProcessTab
from gui.download_tab import DownloadTab
from gui.metadata_tab import MetadataTab
from gui.upload_tab import UploadTab

import logging
import os
logger = logging.getLogger("TikTok2YouTube.MainWindow")

class AboutDialog(QDialog):
    """Custom About dialog with more information and styling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TikTok to YouTube Shorts Automation")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # Application title
        title_label = QLabel("TikTok to YouTube Shorts Automation")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Version info
        version_label = QLabel("Version 1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel(
            "This application automates the process of downloading TikTok videos, "
            "processing them with enhancements, adding appropriate metadata, "
            "and uploading them to YouTube as Shorts."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Features list
        features_label = QLabel(
            "<b>Key Features:</b><br>"
            "• Download TikTok videos directly or via Telegram bot<br>"
            "• Process videos with multiple enhancement options<br>"
            "• Add channel branding and content protection<br>"
            "• Generate YouTube-optimized metadata<br>"
            "• Schedule and manage YouTube uploads<br>"
            "• Track video performance across channels"
        )
        features_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(features_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class MainWindow(QMainWindow):
    """
    Main application window that hosts the tab interface and 
    coordinates between different components of the application.
    """
    
    def __init__(self, config):
        super().__init__()
        
        # Store configuration reference
        self.config = config
        
        # Set up window properties
        self.setWindowTitle("TikTok to YouTube Shorts Automation")
        self.setMinimumSize(1000, 700)  # Set a reasonable minimum size
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Create tabs
        self.create_tabs()
        
        # Create menu bar with full functionality
        self.create_menu()
        
        # Set up inter-tab communication
        self.connect_tab_signals()
        
        logger.info("Main window initialized with all tabs")
    
    def create_tabs(self):
        """Create and initialize all application tabs"""
        # Download tab
        self.download_tab = DownloadTab(self.config)
        self.tab_widget.addTab(self.download_tab, "Download")
        
        # Process tab
        self.process_tab = ProcessTab(self.config)
        self.tab_widget.addTab(self.process_tab, "Process")
        
        # Metadata tab
        self.metadata_tab = MetadataTab(self.config)
        self.tab_widget.addTab(self.metadata_tab, "Metadata")
        
        # Upload tab
        self.upload_tab = UploadTab(self.config)
        self.tab_widget.addTab(self.upload_tab, "Upload")
    
    def connect_tab_signals(self):
        """Connect signals between tabs to enable workflow"""
        # From Download to Process
        self.download_tab.video_downloaded.connect(self.process_tab.add_video)
        
        # From Process to Metadata
        self.process_tab.video_processed.connect(self.metadata_tab.add_video)
        
        # From Metadata to Upload
        self.metadata_tab.metadata_ready.connect(self.upload_tab.add_to_queue)
    
    def create_menu(self):
        """Create application menu with full functionality"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Add video action
        add_video_action = QAction("&Add Video File...", self)
        add_video_action.setShortcut("Ctrl+O")
        add_video_action.triggered.connect(self.add_video_file)
        file_menu.addAction(add_video_action)
        
        # Open videos directory action
        open_videos_action = QAction("Open &Videos Directory", self)
        open_videos_action.triggered.connect(self.open_videos_directory)
        file_menu.addAction(open_videos_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        # Process all videos action
        process_all_action = QAction("Process &All Videos", self)
        process_all_action.triggered.connect(self.process_tab.process_all)
        tools_menu.addAction(process_all_action)
        
        # Upload all videos action
        upload_all_action = QAction("&Upload All Videos", self)
        upload_all_action.triggered.connect(self.upload_tab.upload_all)
        tools_menu.addAction(upload_all_action)
        
        tools_menu.addSeparator()
        
        # Settings action (placeholder for future implementation)
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        # Documentation action
        docs_action = QAction("&Documentation", self)
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)
        
        # About action
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def add_video_file(self):
        """Open file dialog to add a video file directly to the workflow"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self,
            "Select Video Files",
            self.config.get("videos_dir", "./videos"),
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if not file_paths:
            return
            
        # Add each selected file to the process tab
        for file_path in file_paths:
            # Get filename as default title
            title = os.path.basename(file_path)
            
            # Send to process tab
            self.process_tab.add_video(file_path, title)
            
        # Switch to process tab
        self.tab_widget.setCurrentWidget(self.process_tab)
        
        # Show notification
        self.status_label.setText(f"Added {len(file_paths)} video(s) to processing queue")
        QTimer.singleShot(5000, lambda: self.status_label.setText("Ready"))
    
    def open_videos_directory(self):
        """Open the videos directory in the file explorer"""
        videos_dir = self.config.get("videos_dir", "./videos")
        
        if not os.path.exists(videos_dir):
            os.makedirs(videos_dir, exist_ok=True)
            
        # Open directory in file explorer
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(videos_dir))
    
    def show_settings(self):
        """Show application settings dialog (placeholder)"""
        QMessageBox.information(
            self,
            "Settings",
            "The settings dialog will be implemented in a future version."
        )
    
    def show_documentation(self):
        """Show application documentation (placeholder)"""
        QMessageBox.information(
            self,
            "Documentation",
            "The documentation will be available in a future version.\n\n"
            "For now, please refer to the README.md file in the project directory."
        )
    
    def show_about(self):
        """Show about dialog with information about the application"""
        about_dialog = AboutDialog(self)
        about_dialog.exec()