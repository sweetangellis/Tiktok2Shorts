#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TikTok to YouTube Shorts Automation System
Main application entry point

This script initializes the application, checks for dependencies,
sets up logging, and launches the main GUI window.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

# PySide6 imports - correctly separated by module
from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PySide6.QtGui import QPixmap  # QPixmap is in QtGui, not QtWidgets
from PySide6.QtCore import Qt, QTimer

# Internal imports
from config import Config
from database.db_manager import DatabaseManager
from gui.main_window import MainWindow

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("application.log"),
        logging.StreamHandler()
    ]
)

# Create a named logger for our application
logger = logging.getLogger("TikTok2YouTube")

def setup_directories():
    """
    Create all necessary directories for the application if they don't exist.
    This ensures the application has the proper folder structure before starting.
    """
    # These directories will be used by the application for various functions
    dirs = [
        "./videos",              # Downloaded TikTok videos
        "./videos/thumbnails",   # Video thumbnails
        "./videos/processed",    # Processed videos ready for upload
        "./watermarks",          # Watermark images for different channels
        "./output"               # Final output videos
    ]
    
    # Create each directory if it doesn't exist
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def check_dependencies():
    """
    Check if all required external dependencies are installed and available.
    
    The application requires external tools like FFmpeg and yt-dlp to function.
    This function verifies they are properly installed and can be executed.
    
    Returns:
        bool: True if all dependencies are available, False otherwise
    """
    dependencies = {
        "ffmpeg": "FFmpeg for video processing",
        "yt-dlp": "yt-dlp for TikTok video downloading"
    }
    
    missing = []
    
    for cmd, desc in dependencies.items():
        try:
            # Try to run the command with a simple check option
            if cmd == "ffmpeg":
                test_arg = "-version"
            else:
                test_arg = "--version"
                
            result = subprocess.run(
                [cmd, test_arg], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=False  # Don't raise an exception on non-zero return code
            )
            
            if result.returncode != 0:
                missing.append(f"{cmd} ({desc})")
                logger.warning(f"Dependency check for {cmd} failed with return code {result.returncode}")
        except FileNotFoundError:
            missing.append(f"{cmd} ({desc})")
            logger.warning(f"Dependency {cmd} not found in PATH")
    
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        return False
    
    logger.info("All dependencies successfully verified")
    return True

def main():
    """
    Main application entry point.
    
    This function initializes the application, creates the GUI,
    and starts the main event loop.
    """
    # Setup directories first to ensure proper structure
    setup_directories()
    
    # Load configuration from file
    logger.info("Loading application configuration")
    config = Config()
    
    # Create Qt application instance
    app = QApplication(sys.argv)
    app.setApplicationName("TikTok to YouTube Automation")
    app.setStyle("Fusion")  # Use Fusion style for consistent appearance
    
    # Create splash screen to show while loading
    splash_pixmap = QPixmap(400, 200)
    splash_pixmap.fill(Qt.white)
    splash = QSplashScreen(splash_pixmap)
    splash.showMessage("Loading TikTok to YouTube Automation...", 
                      Qt.AlignCenter | Qt.AlignBottom, Qt.black)
    splash.show()
    app.processEvents()  # Process events to ensure splash screen is displayed
    
    # Initialize database manager
    logger.info("Initializing database")
    db = DatabaseManager()
    
    # Create main window
    logger.info("Creating main application window")
    window = MainWindow(config)
    
    # Close splash screen and show main window after a short delay
    QTimer.singleShot(1500, splash.close)
    QTimer.singleShot(1500, window.show)
    
    # Execute application event loop
    logger.info("Application startup complete")
    return app.exec()

if __name__ == "__main__":
    try:
        # Check dependencies before starting
        if not check_dependencies():
            # We still allow the app to start even if dependencies are missing,
            # but log a warning
            logger.warning("Starting application with missing dependencies - some features may not work")
        
        # Start the application and get the exit code
        exit_code = main()
        sys.exit(exit_code)
        
    except Exception as e:
        # Log the exception with full traceback
        logger.exception(f"Fatal error during application startup: {e}")
        
        # Show error dialog to user if possible
        try:
            # Only show error dialog if QApplication has been created
            if QApplication.instance():
                QMessageBox.critical(None, "Fatal Error", 
                                  f"An unexpected error occurred:\n\n{str(e)}\n\n"
                                  f"Please check application.log for details.")
        except Exception:
            # If showing the error dialog fails, at least print to console
            print(f"FATAL ERROR: {str(e)}")
            print("See application.log for details")