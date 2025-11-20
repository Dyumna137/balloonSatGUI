"""
ESP32-CAM Live Feed Window - Non-Modal Independent Window
==========================================================

Fixed Issues:
• Non-modal window (doesn't block main dashboard)
• Independent window (can be minimized/maximized separately)
• Stays on top option (configurable)
• Both windows can be focused independently

Author: Dyumna137
Date: 2025-11-07 15:46:47 UTC
Version: 2.4.1 (Fixed)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from pathlib import Path
from datetime import datetime
import os

try:
    from widgets.live_feed import LiveFeedWidget
except ImportError:
    from dashboardGUI.widgets.live_feed import LiveFeedWidget

try:
    from dispatcher import dispatch
except ImportError:
    from dashboardGUI.dispatcher import dispatch


class ESP32CamWindow(QDialog):
    """
    Non-modal independent window for ESP32-CAM live feed.
    
    Key Features (Fixed):
    • Non-modal: Main dashboard remains accessible
    • Independent: Can be minimized/maximized separately
    • Singleton: Only one window at a time
    • Stay on top: Optional (disabled by default)
    
    Usage:
        window = ESP32CamWindow(parent=main_dashboard)
        window.show()  # Non-blocking!
    """
    
    # Class variable for singleton pattern
    _instance = None
    
    # Signals
    closed = pyqtSignal()
    
    def __init__(self, parent=None, stay_on_top=False):
        """
        Initialize ESP32-CAM window.
        
        Args:
            parent: Parent widget (main dashboard)
            stay_on_top: If True, window stays on top (default: False)
        """
        # Enforce singleton
        if ESP32CamWindow._instance is not None:
            print("⚠️  ESP32-CAM window already open")
            ESP32CamWindow._instance.activateWindow()
            ESP32CamWindow._instance.raise_()
            return
        
        super().__init__(parent)
        
        ESP32CamWindow._instance = self
        
        # ════════════════════════════════════════════════════════════
        # CRITICAL FIX: Window Flags
        # ════════════════════════════════════════════════════════════
        
        # Set window flags for independent, non-modal window
        flags = (
            Qt.WindowType.Window |                    # Independent window
            Qt.WindowType.WindowCloseButtonHint |     # Close button
            Qt.WindowType.WindowMinimizeButtonHint |  # Minimize button
            Qt.WindowType.WindowMaximizeButtonHint    # Maximize button
        )
        
        # Optional: Stay on top (disabled by default - less annoying)
        if stay_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        
        # ✅ CRITICAL: Set non-modal (allows parent interaction)
        self.setModal(False)
        
        # ════════════════════════════════════════════════════════════
        # Window Setup
        # ════════════════════════════════════════════════════════════
        
        self.setWindowTitle("📹 ESP32-CAM Live Feed")
        self.resize(800, 600)
        
        # Snapshot directory
        self.snapshot_dir = Path("snapshots")
        self.snapshot_dir.mkdir(exist_ok=True)
        
        # Snapshot counter
        self.snapshot_counter = self._get_next_snapshot_number()
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        print("✓ ESP32-CAM window created (non-modal)")
    
    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        
        # ────────────────────────────────────────────────────────────
        # Live Feed Widget
        # ────────────────────────────────────────────────────────────
        
        self.live_feed = LiveFeedWidget()
        self.live_feed.setMinimumSize(640, 480)
        layout.addWidget(self.live_feed)
        
        # ────────────────────────────────────────────────────────────
        # Status Label
        # ────────────────────────────────────────────────────────────
        
        self.status_label = QLabel("📡 Waiting for connection...")
        self.status_label.setStyleSheet("padding: 5px; background: #2a2a2a;")
        layout.addWidget(self.status_label)
        
        # ────────────────────────────────────────────────────────────
        # Buttons
        # ────────────────────────────────────────────────────────────
        
        button_layout = QHBoxLayout()
        
        # Snapshot button
        self.btn_snapshot = QPushButton("📸 Capture Snapshot")
        self.btn_snapshot.clicked.connect(self._on_snapshot)
        self.btn_snapshot.setEnabled(False)  # Disabled until first frame
        button_layout.addWidget(self.btn_snapshot)
        
        # Settings button (NEW - toggle stay on top)
        self.btn_stay_on_top = QPushButton("📌 Stay On Top: OFF")
        self.btn_stay_on_top.setCheckable(True)
        self.btn_stay_on_top.clicked.connect(self._toggle_stay_on_top)
        button_layout.addWidget(self.btn_stay_on_top)
        
        # Close button
        self.btn_close = QPushButton("❌ Close")
        self.btn_close.clicked.connect(self.close)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect dispatcher signals."""
        # Connect to frame signal
        dispatch.frameReady.connect(self._on_frame_ready)
        print("  ✓ Connected to frameReady signal")
    
    def _disconnect_signals(self):
        """Disconnect dispatcher signals."""
        try:
            dispatch.frameReady.disconnect(self._on_frame_ready)
            print("  ✓ Disconnected from frameReady signal")
        except:
            pass
    
    def _on_frame_ready(self, frame):
        """
        Handle incoming camera frame.
        
        Args:
            frame: QImage from ESP32-CAM
        """
        if frame and not frame.isNull():
            # Update live feed
            self.live_feed.updateFrame(frame)
            
            # Update status
            self.status_label.setText(
                f"📡 Connected | Resolution: {frame.width()}x{frame.height()} | "
                f"Snapshots: {self.snapshot_counter - 1}"
            )
            
            # Enable snapshot button
            self.btn_snapshot.setEnabled(True)
    
    def _on_snapshot(self):
        """Capture snapshot to file."""
        # Get current frame
        frame = self.live_feed.getCurrentFrame()
        
        if not frame:
            QMessageBox.warning(
                self,
                "No Frame",
                "No frame available to capture.\n"
                "Please wait for camera connection."
            )
            return
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"balloonsat_{timestamp}_{self.snapshot_counter:03d}.jpg"
        filepath = self.snapshot_dir / filename
        
        # Save snapshot
        try:
            success = frame.save(str(filepath), "JPEG", quality=95)
            
            if success:
                file_size = filepath.stat().st_size / 1024  # KB
                
                QMessageBox.information(
                    self,
                    "✓ Snapshot Saved",
                    f"Snapshot saved successfully!\n\n"
                    f"File: {filename}\n"
                    f"Location: {filepath.parent.absolute()}\n"
                    f"Size: {file_size:.1f} KB"
                )
                
                self.snapshot_counter += 1
                
                # Update status
                self.status_label.setText(
                    f"📸 Snapshot saved: {filename} | "
                    f"Total: {self.snapshot_counter - 1}"
                )
            else:
                raise Exception("Save failed")
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Save Failed",
                f"Failed to save snapshot:\n{e}"
            )
    
    def _toggle_stay_on_top(self, checked):
        """
        Toggle stay-on-top mode.
        
        Args:
            checked: True if button checked, False otherwise
        """
        flags = self.windowFlags()
        
        if checked:
            # Add stay on top flag
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.btn_stay_on_top.setText("📌 Stay On Top: ON")
            print("✓ Stay on top: ENABLED")
        else:
            # Remove stay on top flag
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.btn_stay_on_top.setText("📌 Stay On Top: OFF")
            print("✓ Stay on top: DISABLED")
        
        # Apply new flags (requires hide/show)
        self.setWindowFlags(flags)
        self.show()  # Re-show with new flags
    
    def _get_next_snapshot_number(self):
        """
        Get next snapshot counter number.
        
        Returns:
            Next counter number (001, 002, etc.)
        """
        # Find existing snapshots
        existing = list(self.snapshot_dir.glob("balloonsat_*.jpg"))
        
        if not existing:
            return 1
        
        # Extract numbers
        numbers = []
        for file in existing:
            try:
                # Extract number from filename (last 3 digits before .jpg)
                name = file.stem  # balloonsat_20251107_154647_001
                num_str = name.split('_')[-1]  # 001
                numbers.append(int(num_str))
            except:
                pass
        
        return max(numbers, default=0) + 1
    
    def closeEvent(self, event):
        """Handle window close event."""
        print("Closing ESP32-CAM window...")
        
        # Disconnect signals
        self._disconnect_signals()
        
        # Clear frame
        self.live_feed.clearFrame()
        
        # Clear singleton reference
        ESP32CamWindow._instance = None
        
        # Emit closed signal
        self.closed.emit()
        
        print("✓ ESP32-CAM window closed")
        
        # Accept close event
        event.accept()
    
    @classmethod
    def is_open(cls):
        """Check if window is currently open."""
        return cls._instance is not None
    
    @classmethod
    def get_instance(cls):
        """Get current window instance (if open)."""
        return cls._instance


# ════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
    import sys
    
    app = QApplication(sys.argv)
    
    # Create fake main window (simulates dashboard)
    main = QMainWindow()
    main.setWindowTitle("Main Dashboard (Fake)")
    main.resize(1200, 800)
    
    btn = QPushButton("Open Camera Window", main)
    btn.clicked.connect(lambda: ESP32CamWindow(parent=main).show())
    btn.setGeometry(10, 10, 200, 40)
    
    main.show()
    
    print("=" * 60)
    print("Testing ESP32-CAM Window (Non-Modal)")
    print("=" * 60)
    print("✓ Main window opened")
    print("\nTest Instructions:")
    print("1. Click 'Open Camera Window' button")
    print("2. Camera window should open")
    print("3. Try clicking main window - should work! ✅")
    print("4. Both windows can be focused independently")
    print("5. Toggle 'Stay On Top' to test that feature")
    print("=" * 60)
    
    sys.exit(app.exec())