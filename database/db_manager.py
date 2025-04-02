import sqlite3
import os
import json
from datetime import datetime

class DatabaseManager:
    """
    Manages database operations for the application.
    
    This class handles all database interactions, providing a clean interface
    for storing and retrieving video information, processing status, and metadata.
    It uses SQLite for simplicity and portability.
    """
    
    def __init__(self, db_file="videos.db"):
        """
        Initialize the database manager with the specified database file.
        
        Args:
            db_file: Path to the SQLite database file (default: videos.db)
        """
        self.db_file = db_file
        self._create_tables_if_needed()
    
    def _create_tables_if_needed(self):
        """
        Create database tables if they don't exist.
        This sets up the initial database schema.
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Videos table - stores basic information about each video
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            title TEXT,
            source_url TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            channel_id TEXT,
            status TEXT DEFAULT 'downloaded',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Metadata table - stores generated metadata for YouTube uploads
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            video_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            tags TEXT,
            thumbnail_path TEXT,
            category_id INTEGER,
            privacy_status TEXT DEFAULT 'private',
            publish_at TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        ''')
        
        # Processing table - stores processing information and settings
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processing (
            video_id INTEGER PRIMARY KEY,
            processed_filepath TEXT,
            processing_date TIMESTAMP,
            settings TEXT,  -- JSON string of processing settings
            duration_seconds REAL,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        ''')
        
        # Upload table - stores upload information
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            video_id INTEGER PRIMARY KEY,
            youtube_video_id TEXT,
            youtube_url TEXT,
            scheduled_time TIMESTAMP,
            uploaded_time TIMESTAMP,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"Database initialized: {self.db_file}")
    
    def add_video(self, filepath, title=None, source_url=None, channel_id=None):
        """
        Add a new video to the database.
        
        Args:
            filepath: Full path to the video file
            title: Video title (optional)
            source_url: Original TikTok URL (optional)
            channel_id: YouTube channel ID (optional)
            
        Returns:
            video_id: ID of the newly added video
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Video file not found: {filepath}")
        
        filename = os.path.basename(filepath)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if video already exists
        cursor.execute(
            "SELECT id FROM videos WHERE filepath = ?", 
            (filepath,)
        )
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing[0]  # Return existing video ID
        
        # Insert new video
        cursor.execute(
            "INSERT INTO videos (filename, filepath, title, source_url, channel_id, status) VALUES (?, ?, ?, ?, ?, ?)",
            (filename, filepath, title, source_url, channel_id, "downloaded")
        )
        
        video_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"Added video to database: {filename} (ID: {video_id})")
        return video_id
    
    def update_video_status(self, video_id, status):
        """
        Update the status of a video.
        
        Args:
            video_id: ID of the video to update
            status: New status (e.g., 'downloaded', 'processing', 'processed', 'uploading', 'uploaded', 'failed')
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            (status, video_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_video_by_id(self, video_id):
        """
        Get video information by ID.
        
        Args:
            video_id: ID of the video
            
        Returns:
            dict: Video information or None if not found
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        
        return None
    
    def get_videos_by_status(self, status):
        """
        Get all videos with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            list: List of video dictionaries
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM videos WHERE status = ?", (status,))
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_videos(self):
        """
        Get all videos from the database.
        
        Returns:
            list: List of video dictionaries
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM videos ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_processing_info(self, video_id, processed_filepath, settings=None):
        """
        Add processing information for a video.
        
        Args:
            video_id: ID of the video
            processed_filepath: Path to the processed video file
            settings: Dictionary of processing settings (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Convert settings dict to JSON string
        settings_json = json.dumps(settings) if settings else None
        
        # Check if processing entry already exists
        cursor.execute("SELECT video_id FROM processing WHERE video_id = ?", (video_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute(
                """
                UPDATE processing SET 
                    processed_filepath = ?, 
                    settings = ?, 
                    processing_date = CURRENT_TIMESTAMP,
                    status = 'completed'
                WHERE video_id = ?
                """,
                (processed_filepath, settings_json, video_id)
            )
        else:
            # Insert new entry
            cursor.execute(
                """
                INSERT INTO processing (
                    video_id, processed_filepath, settings, 
                    processing_date, status
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'completed')
                """,
                (video_id, processed_filepath, settings_json)
            )
        
        # Update video status
        cursor.execute(
            "UPDATE videos SET status = 'processed' WHERE id = ?",
            (video_id,)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def add_metadata(self, video_id, title, description=None, tags=None, 
                    thumbnail_path=None, category_id=None, privacy_status='private'):
        """
        Add or update metadata for a video.
        
        Args:
            video_id: ID of the video
            title: Video title
            description: Video description (optional)
            tags: Comma-separated tags (optional)
            thumbnail_path: Path to thumbnail image (optional)
            category_id: YouTube category ID (optional)
            privacy_status: Privacy status (default: 'private')
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if metadata already exists
        cursor.execute("SELECT video_id FROM metadata WHERE video_id = ?", (video_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute(
                """
                UPDATE metadata SET 
                    title = ?, 
                    description = ?, 
                    tags = ?,
                    thumbnail_path = ?,
                    category_id = ?,
                    privacy_status = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE video_id = ?
                """,
                (title, description, tags, thumbnail_path, category_id, privacy_status, video_id)
            )
        else:
            # Insert new entry
            cursor.execute(
                """
                INSERT INTO metadata (
                    video_id, title, description, tags,
                    thumbnail_path, category_id, privacy_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (video_id, title, description, tags, thumbnail_path, category_id, privacy_status)
            )
        
        # Update video status
        cursor.execute(
            "UPDATE videos SET status = 'metadata_ready' WHERE id = ?",
            (video_id,)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def schedule_upload(self, video_id, scheduled_time=None, youtube_channel_id=None):
        """
        Schedule a video for upload.
        
        Args:
            video_id: ID of the video
            scheduled_time: Scheduled upload time (optional)
            youtube_channel_id: YouTube channel ID (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if upload already scheduled
        cursor.execute("SELECT video_id FROM uploads WHERE video_id = ?", (video_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute(
                """
                UPDATE uploads SET 
                    scheduled_time = ?,
                    status = 'scheduled'
                WHERE video_id = ?
                """,
                (scheduled_time, video_id)
            )
        else:
            # Insert new entry
            cursor.execute(
                """
                INSERT INTO uploads (
                    video_id, scheduled_time, status
                ) VALUES (?, ?, 'scheduled')
                """,
                (video_id, scheduled_time)
            )
        
        # Update video channel if provided
        if youtube_channel_id:
            cursor.execute(
                "UPDATE videos SET channel_id = ? WHERE id = ?",
                (youtube_channel_id, video_id)
            )
        
        # Update video status
        cursor.execute(
            "UPDATE videos SET status = 'scheduled' WHERE id = ?",
            (video_id,)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def record_upload(self, video_id, youtube_video_id, youtube_url):
        """
        Record successful video upload.
        
        Args:
            video_id: ID of the video
            youtube_video_id: YouTube video ID
            youtube_url: YouTube video URL
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE uploads SET 
                youtube_video_id = ?,
                youtube_url = ?,
                uploaded_time = CURRENT_TIMESTAMP,
                status = 'uploaded'
            WHERE video_id = ?
            """,
            (youtube_video_id, youtube_url, video_id)
        )
        
        # Update video status
        cursor.execute(
            "UPDATE videos SET status = 'uploaded' WHERE id = ?",
            (video_id,)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def record_upload_failure(self, video_id, error_message):
        """
        Record failed video upload.
        
        Args:
            video_id: ID of the video
            error_message: Error message
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE uploads SET 
                error_message = ?,
                status = 'failed'
            WHERE video_id = ?
            """,
            (error_message, video_id)
        )
        
        # Update video status
        cursor.execute(
            "UPDATE videos SET status = 'upload_failed' WHERE id = ?",
            (video_id,)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_videos_ready_for_upload(self):
        """
        Get videos that are ready for uploading.
        
        Returns:
            list: List of video dictionaries with metadata
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT v.*, m.title as meta_title, m.description, m.tags, m.thumbnail_path, 
                   m.privacy_status, p.processed_filepath
            FROM videos v
            LEFT JOIN metadata m ON v.id = m.video_id
            LEFT JOIN processing p ON v.id = p.video_id
            WHERE v.status = 'metadata_ready'
            """
        )
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_scheduled_uploads(self):
        """
        Get videos scheduled for upload.
        
        Returns:
            list: List of video dictionaries with metadata and upload schedule
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT v.*, m.title as meta_title, m.description, m.tags, m.thumbnail_path, 
                   m.privacy_status, p.processed_filepath, u.scheduled_time
            FROM videos v
            LEFT JOIN metadata m ON v.id = m.video_id
            LEFT JOIN processing p ON v.id = p.video_id
            LEFT JOIN uploads u ON v.id = u.video_id
            WHERE v.status = 'scheduled'
            """
        )
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_video(self, video_id):
        """
        Delete a video and all related information from the database.
        
        Args:
            video_id: ID of the video
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # Delete related records first (foreign key constraints)
            for table in ['metadata', 'processing', 'uploads']:
                cursor.execute(f"DELETE FROM {table} WHERE video_id = ?", (video_id,))
            
            # Delete video record
            cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting video: {e}")
            conn.rollback()
            conn.close()
            return False