from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSlider, QDoubleSpinBox,
    QFormLayout, QGroupBox, QCheckBox, QSpinBox, QFileDialog, 
    QMessageBox, QProgressBar, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
import os
import threading
import time

from processor.ffmpeg_handler import FFmpegHandler

class SliderWithSpinBox(QWidget):
    """
    A custom widget that combines a slider with a spin box for precise input.
    Supports both integer and float values.
    """
    
    valueChanged = Signal(object)  # int or float
    
    def __init__(self, min_val, max_val, default_val, step=1, decimals=0, parent=None):
        """
        Initialize the slider with spin box widget.
        
        Args:
            min_val: Minimum value
            max_val: Maximum value
            default_val: Default value
            step: Step size
            decimals: Number of decimal places (0 for integer slider)
            parent: Parent widget
        """
        super().__init__(parent)
        self.decimals = decimals
        self.use_float = decimals > 0
        self.multiplier = 10 ** decimals  # For converting float to int for slider
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(min_val * self.multiplier))
        self.slider.setMaximum(int(max_val * self.multiplier))
        self.slider.setValue(int(default_val * self.multiplier))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(int(step * self.multiplier))
        layout.addWidget(self.slider, 3)  # 3:1 ratio
        
        # Create spin box
        if self.use_float:
            self.spinbox = QDoubleSpinBox()
            self.spinbox.setDecimals(decimals)
            self.spinbox.setSingleStep(step)
        else:
            self.spinbox = QSpinBox()
            self.spinbox.setSingleStep(int(step))
            
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setValue(default_val)
        layout.addWidget(self.spinbox, 1)  # 3:1 ratio
        
        # Connect signals
        self.slider.valueChanged.connect(self._slider_changed)
        self.spinbox.valueChanged.connect(self._spinbox_changed)
    
    def _slider_changed(self, value):
        """Handle slider value change"""
        if self.use_float:
            value_to_set = value / self.multiplier
        else:
            value_to_set = value
            
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value_to_set)
        self.spinbox.blockSignals(False)
        
        self.valueChanged.emit(value_to_set)
    
    def _spinbox_changed(self, value):
        """Handle spin box value change"""
        slider_value = int(value * self.multiplier) if self.use_float else value
        
        self.slider.blockSignals(True)
        self.slider.setValue(slider_value)
        self.slider.blockSignals(False)
        
        self.valueChanged.emit(value)
    
    def value(self):
        """Get the current value"""
        return self.spinbox.value()
    
    def setValue(self, value):
        """Set the current value"""
        self.spinbox.setValue(value)

class ProcessTab(QWidget):
    """
    Tab for video processing settings and functionality.
    Provides controls for adjusting video processing parameters,
    applying effects, and managing the processing queue.
    """
    
    # Signals for inter-tab communication
    video_processed = Signal(str, str)  # (video_path, title)
    
    def __init__(self, config):
        """
        Initialize the process tab.
        
        Args:
            config: Application configuration manager
        """
        super().__init__()
        self.config = config
        self.ffmpeg = FFmpegHandler(config)
        self.processing_queue = []
        self.currently_processing = False
        self.init_ui()
    
    def init_ui(self):
        """Set up the user interface for the process tab"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create a scroll area for settings to handle many controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Processing Settings section
        settings_group = QGroupBox("Processing Settings")
        settings_layout = QFormLayout(settings_group)
        
        # Channel selection for watermark
        self.channel_combo = QComboBox()
        self.load_channels()
        settings_layout.addRow("Channel:", self.channel_combo)
        
        # Visual Enhancement Settings
        enhance_group = QGroupBox("Visual Enhancements")
        enhance_layout = QFormLayout(enhance_group)
        
        # Color saturation - Changed to 0.01 step size
        self.color_slider = SliderWithSpinBox(0.5, 2.0, 
                                             self.config.get("processing.color_saturation", 1.0),
                                             0.01, 2)  # Changed step to 0.01, 2 decimal places
        self.color_slider.valueChanged.connect(
            lambda val: self.config.set("processing.color_saturation", val))
        enhance_layout.addRow("Color Saturation:", self.color_slider)
        
        # Brightness - Changed to 0.01 step size
        self.brightness_slider = SliderWithSpinBox(0.5, 2.0, 
                                             self.config.get("processing.brightness", 1.0),
                                             0.01, 2)  # Changed step to 0.01, 2 decimal places
        self.brightness_slider.valueChanged.connect(
            lambda val: self.config.set("processing.brightness", val))
        enhance_layout.addRow("Brightness:", self.brightness_slider)
        
        # Zoom Pulse effect removed
        
        # Denoise strength
        self.denoise_slider = SliderWithSpinBox(0, 10, 
                                              self.config.get("processing.denoise_strength", 3),
                                              1, 0)
        self.denoise_slider.valueChanged.connect(
            lambda val: self.config.set("processing.denoise_strength", val))
        enhance_layout.addRow("Denoise Strength:", self.denoise_slider)
        
        # Sharpness
        self.sharpness_slider = SliderWithSpinBox(0.0, 3.0, 
                                                 self.config.get("processing.sharpness", 1.5),
                                                 0.1, 1)
        self.sharpness_slider.valueChanged.connect(
            lambda val: self.config.set("processing.sharpness", val))
        enhance_layout.addRow("Sharpness:", self.sharpness_slider)
        
        # Add Visual Enhancement group to the form
        settings_layout.addRow(enhance_group)
        
        # Branding Elements group
        brand_group = QGroupBox("Branding Elements")
        brand_layout = QFormLayout(brand_group)
        
        # Watermark opacity
        self.watermark_slider = SliderWithSpinBox(0.0, 1.0, 
                                                 self.config.get("processing.watermark_opacity", 0.8),
                                                 0.05, 2)
        self.watermark_slider.valueChanged.connect(
            lambda val: self.config.set("processing.watermark_opacity", val))
        brand_layout.addRow("Watermark Opacity:", self.watermark_slider)
        
        # Watermark selection button
        self.watermark_btn = QPushButton("Select Watermark Image")
        self.watermark_btn.clicked.connect(self.select_watermark)
        brand_layout.addRow("Watermark:", self.watermark_btn)
        
        # Add Branding Elements group to the form
        settings_layout.addRow(brand_group)
        
        # Content Protection group
        protect_group = QGroupBox("Content Protection")
        protect_layout = QFormLayout(protect_group)
        
        # Speed randomization
        self.speed_slider = SliderWithSpinBox(0.0, 0.2, 
                                             self.config.get("processing.speed_randomization", 0.05),
                                             0.01, 2)
        self.speed_slider.valueChanged.connect(
            lambda val: self.config.set("processing.speed_randomization", val))
        protect_layout.addRow("Speed Randomization:", self.speed_slider)
        
        # Zoom factor
        self.zoom_factor_slider = SliderWithSpinBox(1.0, 1.1, 
                                                   self.config.get("processing.zoom_factor", 1.02),
                                                   0.01, 2)
        self.zoom_factor_slider.valueChanged.connect(
            lambda val: self.config.set("processing.zoom_factor", val))
        protect_layout.addRow("Zoom Factor:", self.zoom_factor_slider)
        
        # Pixel shift
        self.pixel_shift_slider = SliderWithSpinBox(0, 5, 
                                                   self.config.get("processing.pixel_shift", 1),
                                                   1, 0)
        self.pixel_shift_slider.valueChanged.connect(
            lambda val: self.config.set("processing.pixel_shift", val))
        protect_layout.addRow("Pixel Shift:", self.pixel_shift_slider)
        
        # Add Content Protection group to the form
        settings_layout.addRow(protect_group)
        
        # Output Settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        
        # Audio normalization
        self.audio_norm_check = QCheckBox("Enable")
        self.audio_norm_check.setChecked(self.config.get("processing.audio_normalization", True))
        self.audio_norm_check.toggled.connect(
            lambda val: self.config.set("processing.audio_normalization", val))
        output_layout.addRow("Audio Normalization:", self.audio_norm_check)
        
        # CRF (quality)
        self.crf_slider = SliderWithSpinBox(18, 28, 
                                           self.config.get("processing.crf", 23),
                                           1, 0)
        self.crf_slider.valueChanged.connect(
            lambda val: self.config.set("processing.crf", val))
        output_layout.addRow("Quality (CRF):", self.crf_slider)
        
        # Bitrate options
        self.bitrate_combo = QComboBox()
        bitrates = ["1M", "2M", "3M", "4M", "5M", "8M"]
        self.bitrate_combo.addItems(bitrates)
        current_bitrate = self.config.get("processing.bitrate", "2M")
        index = bitrates.index(current_bitrate) if current_bitrate in bitrates else 1
        self.bitrate_combo.setCurrentIndex(index)
        self.bitrate_combo.currentTextChanged.connect(
            lambda val: self.config.set("processing.bitrate", val))
        output_layout.addRow("Bitrate:", self.bitrate_combo)
        
        # Threads
        self.threads_slider = SliderWithSpinBox(1, 16, 
                                               self.config.get("processing.threads", 4),
                                               1, 0)
        self.threads_slider.valueChanged.connect(
            lambda val: self.config.set("processing.threads", val))
        output_layout.addRow("Threads:", self.threads_slider)
        
        # Add Output Settings group to the form
        settings_layout.addRow(output_group)
        
        # Add the settings form to the scroll layout
        scroll_layout.addWidget(settings_group)
        
        # Add preset buttons (save/load settings)
        preset_layout = QHBoxLayout()
        self.save_preset_btn = QPushButton("Save Settings Preset")
        self.save_preset_btn.clicked.connect(self.save_preset)
        preset_layout.addWidget(self.save_preset_btn)
        
        self.load_preset_btn = QPushButton("Load Settings Preset")
        self.load_preset_btn.clicked.connect(self.load_preset)
        preset_layout.addWidget(self.load_preset_btn)
        
        scroll_layout.addLayout(preset_layout)
        
        # Finalize scroll area setup
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Processing Queue section
        queue_group = QGroupBox("Processing Queue")
        queue_layout = QVBoxLayout(queue_group)
        
        # Queue table
        self.queue_table = QTableWidget(0, 5)  # rows, columns
        self.queue_table.setHorizontalHeaderLabels(["Video", "Channel", "Status", "Progress", "Actions"])
        self.queue_table.setColumnWidth(0, 250)  # Video
        self.queue_table.setColumnWidth(1, 100)  # Channel
        self.queue_table.setColumnWidth(2, 100)  # Status
        self.queue_table.setColumnWidth(3, 200)  # Progress
        self.queue_table.setColumnWidth(4, 150)  # Actions
        queue_layout.addWidget(self.queue_table)
        
        # Queue control buttons
        queue_buttons = QHBoxLayout()
        
        # Add Video File button - REMOVED THE PROBLEMATIC ICON SETTING
        self.add_video_btn = QPushButton("Add Video File")
        # Using a simple text label instead of an icon that might not be available
        self.add_video_btn.clicked.connect(self.select_video_file)
        queue_buttons.addWidget(self.add_video_btn)
        
        self.process_all_btn = QPushButton("Process All")
        self.process_all_btn.clicked.connect(self.process_all)
        queue_buttons.addWidget(self.process_all_btn)
        
        self.clear_queue_btn = QPushButton("Clear Queue")
        self.clear_queue_btn.clicked.connect(self.clear_queue)
        queue_buttons.addWidget(self.clear_queue_btn)
        
        self.open_output_btn = QPushButton("Open Output Folder")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        queue_buttons.addWidget(self.open_output_btn)
        
        queue_layout.addLayout(queue_buttons)
        
        main_layout.addWidget(queue_group)
        
        # Set up processing queue update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_queue_display)
        self.update_timer.start(500)  # Update every half second
    
    def select_video_file(self):
        """Open file dialog to select video file(s) to add to the processing queue"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self,
            "Select Video Files",
            self.config.get("videos_dir", "./videos"),  # Default to videos directory
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm)"
        )
        
        if not file_paths:
            return
        
        # Add each selected file to the processing queue
        for file_path in file_paths:
            # Get the filename as the default title
            title = os.path.basename(file_path)
            
            # Add the video to the processing queue
            self.add_video(file_path, title)
        
        # Show a message if multiple videos were added
        if len(file_paths) > 1:
            QMessageBox.information(
                self,
                "Videos Added",
                f"{len(file_paths)} videos have been added to the processing queue."
            )
    
    def load_channels(self):
        """Load available YouTube channels from config into the combobox"""
        self.channel_combo.clear()
        
        # Add a "None" item
        self.channel_combo.addItem("No Channel (Generic)", "")
        
        # Add all configured channels
        channels = self.config.get("channels", {})
        for channel_id, channel_info in channels.items():
            self.channel_combo.addItem(channel_info["name"], channel_id)
    
    def select_watermark(self):
        """Open file dialog to select a watermark image"""
        channel_id = self.channel_combo.currentData()
        if not channel_id:
            QMessageBox.warning(self, "No Channel Selected", 
                             "Please select a channel before setting a watermark.")
            return
        
        # Open file dialog
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Select Watermark Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif)"
        )
        
        if file_path:
            # Create watermarks directory if it doesn't exist
            watermarks_dir = self.config.get("watermarks_dir", "./watermarks")
            os.makedirs(watermarks_dir, exist_ok=True)
            
            # Copy the file to the watermarks directory
            import shutil
            channel_name = self.channel_combo.currentText().replace(" ", "_").lower()
            new_filename = f"watermark_{channel_name}.png"
            new_path = os.path.join(watermarks_dir, new_filename)
            
            try:
                shutil.copy2(file_path, new_path)
                
                # Update the channel's watermark path
                channels = self.config.get("channels", {})
                if channel_id in channels:
                    channels[channel_id]["watermark"] = new_path
                    self.config.set("channels", channels)
                    
                QMessageBox.information(
                    self,
                    "Watermark Set",
                    f"Watermark for {self.channel_combo.currentText()} has been set."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to set watermark: {str(e)}")
    
    def save_preset(self):
        """Save current settings as a named preset"""
        # This is a placeholder implementation
        # In a full implementation, you would prompt for a preset name
        # and store the current settings under that name
        QMessageBox.information(self, "Not Implemented", 
                             "The preset functionality will be implemented in a future version.")
    
    def load_preset(self):
        """Load settings from a saved preset"""
        # This is a placeholder implementation
        QMessageBox.information(self, "Not Implemented", 
                             "The preset functionality will be implemented in a future version.")
    
    def add_video(self, video_path, title=""):
        """
        Add a video to the processing queue.
        Called when a video is downloaded or selected.
        
        Args:
            video_path: Path to the video file
            title: Video title (optional)
        """
        # Check if the video exists
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "File Not Found", f"Video file not found: {video_path}")
            return
        
        # Get the video info from FFmpeg to ensure it's a valid video
        try:
            video_info = self.ffmpeg.get_video_info(video_path)
            if not video_info:
                QMessageBox.warning(self, "Invalid Video", f"Could not get video information: {video_path}")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error inspecting video: {str(e)}")
            return
            
        # Add the video to the queue
        if not title:
            title = os.path.basename(video_path)
            
        # Get channel info
        channel_id = self.channel_combo.currentData()
        channel_name = self.channel_combo.currentText()
        
        # Check if video is already in queue
        for item in self.processing_queue:
            if item["video_path"] == video_path:
                QMessageBox.information(
                    self, 
                    "Already Queued", 
                    "This video is already in the processing queue."
                )
                return
                
        # Add to queue
        queue_item = {
            "video_path": video_path,
            "title": title,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "status": "Queued",
            "progress": 0,
            "output_path": None
        }
        
        self.processing_queue.append(queue_item)
        
        # Update display
        self.update_queue_display()
        
        # Start processing if not already processing
        if not self.currently_processing and len(self.processing_queue) == 1:
            # Auto-start processing if this is the first item
            self.process_next()
    
    def update_queue_display(self):
        """Update the processing queue table display"""
        # Preserve the current selection
        selected_rows = self.queue_table.selectionModel().selectedRows()
        selected_item = None
        if selected_rows:
            selected_item = self.processing_queue[selected_rows[0].row()] if selected_rows[0].row() < len(self.processing_queue) else None
        
        # Clear and update the table
        self.queue_table.setRowCount(len(self.processing_queue))
        
        for i, item in enumerate(self.processing_queue):
            # Video title/path
            title_item = QTableWidgetItem(item["title"])
            title_item.setToolTip(item["video_path"])
            self.queue_table.setItem(i, 0, title_item)
            
            # Channel
            channel_item = QTableWidgetItem(item["channel_name"])
            self.queue_table.setItem(i, 1, channel_item)
            
            # Status
            status_item = QTableWidgetItem(item["status"])
            self.queue_table.setItem(i, 2, status_item)
            
            # Progress bar
            if "progress_bar" not in item:
                progress_bar = QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(item["progress"])
                self.queue_table.setCellWidget(i, 3, progress_bar)
                item["progress_bar"] = progress_bar
            else:
                item["progress_bar"].setValue(item["progress"])
            
            # Actions button
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            # Different buttons based on status
            if item["status"] == "Queued":
                process_btn = QPushButton("Process")
                process_btn.clicked.connect(lambda _, idx=i: self.process_item(idx))
                actions_layout.addWidget(process_btn)
                
                remove_btn = QPushButton("Remove")
                remove_btn.clicked.connect(lambda _, idx=i: self.remove_item(idx))
                actions_layout.addWidget(remove_btn)
            elif item["status"] == "Processing":
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(lambda _, idx=i: self.cancel_item(idx))
                actions_layout.addWidget(cancel_btn)
            elif item["status"] == "Completed":
                view_btn = QPushButton("View")
                view_btn.clicked.connect(lambda _, path=item["output_path"]: 
                                      QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path))))
                actions_layout.addWidget(view_btn)
                
                next_btn = QPushButton("Next Step")
                next_btn.clicked.connect(lambda _, path=item["output_path"], title=item["title"]: 
                                      self.video_processed.emit(path, title))
                actions_layout.addWidget(next_btn)
            elif item["status"] == "Failed":
                retry_btn = QPushButton("Retry")
                retry_btn.clicked.connect(lambda _, idx=i: self.retry_item(idx))
                actions_layout.addWidget(retry_btn)
                
                remove_btn = QPushButton("Remove")
                remove_btn.clicked.connect(lambda _, idx=i: self.remove_item(idx))
                actions_layout.addWidget(remove_btn)
            
            self.queue_table.setCellWidget(i, 4, actions_widget)
            
        # Restore selection if possible
        if selected_item:
            for i, item in enumerate(self.processing_queue):
                if item is selected_item:
                    self.queue_table.selectRow(i)
                    break
    
    def process_item(self, index):
        """Process a specific queue item by index"""
        if index < 0 or index >= len(self.processing_queue):
            return
            
        # If already processing, just move this item to the front
        if self.currently_processing:
            # Reorder the queue to process this item next
            item = self.processing_queue.pop(index)
            
            # Find the currently processing item
            for i, current_item in enumerate(self.processing_queue):
                if current_item["status"] == "Processing":
                    # Insert right after the current item
                    self.processing_queue.insert(i + 1, item)
                    break
            else:
                # If no item is processing (shouldn't happen), put at front
                self.processing_queue.insert(0, item)
                
            self.update_queue_display()
            return
        
        # If not processing, start processing this item
        self.currently_processing = True
        
        # Update status
        self.processing_queue[index]["status"] = "Processing"
        self.processing_queue[index]["progress"] = 0
        self.update_queue_display()
        
        # Start processing thread
        threading.Thread(
            target=self._process_video_thread,
            args=(index,),
            daemon=True
        ).start()
    
    def _process_video_thread(self, index):
        """Background thread for video processing"""
        if index < 0 or index >= len(self.processing_queue):
            self.currently_processing = False
            return
            
        item = self.processing_queue[index]
        
        try:
            # Process the video using FFmpeg
            output_path = self.ffmpeg.process_video(
                item["video_path"],
                item["channel_id"],
                lambda progress: self._update_progress(index, progress)
            )
            
            # Update status and output path
            self.processing_queue[index]["status"] = "Completed"
            self.processing_queue[index]["progress"] = 100
            self.processing_queue[index]["output_path"] = output_path
            
            # Update UI
            self.update_queue_display()
            
        except Exception as e:
            # Update status
            self.processing_queue[index]["status"] = "Failed"
            self.processing_queue[index]["progress"] = 0
            self.processing_queue[index]["error"] = str(e)
            
            # Show error message
            def show_error():
                QMessageBox.critical(
                    self,
                    "Processing Error",
                    f"Error processing video: {str(e)}"
                )
            
            # Schedule UI update from main thread
            QTimer.singleShot(0, show_error)
            
        finally:
            # Mark as no longer processing
            self.currently_processing = False
            
            # Process next item if any
            queued_items = [item for item in self.processing_queue if item["status"] == "Queued"]
            if queued_items:
                self.process_next()
    
    def _update_progress(self, index, progress):
        """Update progress for a queue item from processing thread"""
        if index < 0 or index >= len(self.processing_queue):
            return
            
        self.processing_queue[index]["progress"] = progress
        
        # No need to call update_queue_display() here
        # as it's called by the timer
    
    def process_next(self):
        """Process the next queued item"""
        if self.currently_processing:
            return
            
        # Find the next queued item
        for i, item in enumerate(self.processing_queue):
            if item["status"] == "Queued":
                self.process_item(i)
                break
    
    def process_all(self):
        """Process all queued items"""
        if not self.processing_queue:
            QMessageBox.information(self, "Empty Queue", "No videos in the processing queue.")
            return
            
        # Start processing
        self.process_next()
    
    def remove_item(self, index):
        """Remove an item from the queue"""
        if index < 0 or index >= len(self.processing_queue):
            return
            
        # Can only remove queued or failed items
        if self.processing_queue[index]["status"] not in ["Queued", "Failed", "Completed"]:
            QMessageBox.warning(self, "Cannot Remove", "Cannot remove items that are currently processing.")
            return
            
        # Remove the item
        self.processing_queue.pop(index)
        self.update_queue_display()
    
    def retry_item(self, index):
        """Retry a failed item"""
        if index < 0 or index >= len(self.processing_queue):
            return
            
        # Reset status
        self.processing_queue[index]["status"] = "Queued"
        self.processing_queue[index]["progress"] = 0
        self.processing_queue[index].pop("error", None)
        
        # Update display
        self.update_queue_display()
        
        # Start processing if not already processing
        if not self.currently_processing:
            self.process_item(index)
    
    def cancel_item(self, index):
        """Cancel a processing item (not implemented)"""
        QMessageBox.information(
            self,
            "Not Implemented",
            "Cancelling in-progress video processing is not currently supported."
        )
    
    def clear_queue(self):
        """Clear the processing queue"""
        # Check if processing
        if self.currently_processing:
            QMessageBox.warning(
                self, 
                "Processing Active", 
                "Cannot clear queue while video processing is active. Wait for the current video to finish."
            )
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Clear Queue",
            "Are you sure you want to clear the processing queue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Clear the queue
            self.processing_queue = []
            self.update_queue_display()
    
    def open_output_folder(self):
        """Open the output folder in file explorer"""
        output_dir = self.config.get("output_dir", "./output")
        if os.path.exists(output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
        else:
            try:
                os.makedirs(output_dir, exist_ok=True)
                QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to open output folder: {str(e)}")