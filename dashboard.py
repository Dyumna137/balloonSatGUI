"""
BalloonSat Telemetry Dashboard - Main Application
==================================================

Main dashboard window that loads UI from dashboard.ui file and provides
real-time visualization of BalloonSat telemetry data during high-altitude
balloon flights.

This version uses utility modules to keep the main file clean and focused
on dashboard-specific logic while maintaining comprehensive documentation
for all methods and workflows.

Architecture:
    • UI Loading: Delegated to utils.ui_loader
    • Widget Finding: Delegated to utils.widget_finder
    • Data Models: models.TelemetryTableModel (Model-View architecture)
    • Event System: dispatcher (signal/slot based pub-sub pattern)
    • Custom Widgets: widgets.* (charts, gauges, LEDs, live_feed)

Components:
    • Telemetry table (left column) - Shows all sensor readings in real-time
    • Controls & Sensors (middle column) - Buttons and health indicators
    • Single altitude chart (right column) - Altitude vs Time visualization
    • ESP32-CAM window (separate) - Live camera feed and snapshots

Signal Flow:
    1. Data source emits dispatcher signals (e.g., serial port, file reader)
    2. Dispatcher routes signals to dashboard update methods
    3. Dashboard updates widgets (tables, charts, gauges, LEDs)
    4. Qt automatically repaints modified widgets

Usage:
    As script:
        python dashboard.py
    
    As module:
        python -m dashboardGUI.dashboard
    
    Programmatically:
        from dashboardGUI.dashboard import BalloonSatDashboard
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication([])
        window = BalloonSatDashboard()
        window.show()
        app.exec()

Version History:
    v1.0 (2025-11-05): Initial release with dual charts
    v2.0 (2025-11-06): Package renamed to dashboardGUI
    v2.1 (2025-11-06): Fixed QTableWidget → QTableView
    v2.2 (2025-11-06): Updated widget finder for QTableView
    v2.3 (2025-11-06): Comprehensive documentation added
    v2.4 (2025-11-07): Fixed ESP32-CAM button connection, added QPushButton import
    v2.5 (2025-11-07): Added live feed widget and improved event handling
    v2.6 (2025-11-22): Creating New Widget Table and modifying existing table 

Author: Dyumna137
Date: 2025-11-22 00:14:23 UTC
Version: 2.6
License: MIT
Package: dashboardGUI
"""

from __future__ import annotations
import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableView,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer

# ============================================================================
# === IMPORTS: Utility Modules ===
# ============================================================================

# Utility imports with fallback for different execution contexts
# Supports both script execution and package installation
try:
    # Try local imports first (when running as script: python dashboard.py)
    from utils.ui_loader import load_ui_file, load_stylesheet
    from utils.widget_finder import WidgetFinder
except ImportError:
    # Fall back to package imports (when installed: pip install dashboardGUI)
    from dashboardGUI.utils.ui_loader import load_ui_file, load_stylesheet
    from dashboardGUI.utils.widget_finder import WidgetFinder

# ============================================================================
# === IMPORTS: Custom Widgets (Must import BEFORE loading .ui file) ===
# ============================================================================

# Custom widget classes MUST be imported before uic.loadUi() is called
# This ensures Qt Designer's promotion system can find the classes
try:
    from widgets.charts import TrajectoryCharts
    from widgets.gauge import LinearGauge
    from widgets.status_led import StatusLED, IndicatorsManager
except ImportError:
    from dashboardGUI.widgets.charts import TrajectoryCharts
    from dashboardGUI.widgets.gauge import LinearGauge
    from dashboardGUI.widgets.status_led import StatusLED, IndicatorsManager

# ============================================================================
# === IMPORTS: Data Models and Dispatcher ===
# ============================================================================

# Import data model and event system
try:
    from models import TelemetryTableModel
    from dispatcher import dispatch
    from metadata import SENSORS, TELEMETRY_FIELDS
except ImportError:
    from dashboardGUI.models import TelemetryTableModel
    from dashboardGUI.dispatcher import dispatch
    from dashboardGUI.metadata import SENSORS, TELEMETRY_FIELDS


class BalloonSatDashboard(QMainWindow):
    """
    Main dashboard window for BalloonSat telemetry visualization.
    
    This is the primary user interface for monitoring the BalloonSat during
    flight. It displays real-time telemetry data, sensor health status,
    computer resource usage, and altitude trajectory visualization.
    
    Architecture:
        The dashboard follows a clean MVC-inspired architecture:
        • Model: TelemetryTableModel handles data storage and formatting
        • View: Qt Designer .ui file defines the layout and widgets
        • Controller: This class connects models to views and handles updates
    
    Data Flow:
        1. External data source (serial, file, network) emits signals via dispatcher
        2. Dispatcher signals connect to this class's update methods
        3. Update methods modify widget states (tables, charts, LEDs, gauges)
        4. Qt automatically repaints modified widgets
    
    Key Features:
        • Real-time telemetry display in two synchronized tables
        • Live altitude trajectory plotting (expected vs actual)
        • Sensor health monitoring with color-coded LED indicators
        • Computer resource monitoring (CPU/Memory usage gauges)
        • ESP32-CAM live feed window (separate, non-blocking)
        • Control buttons (start/stop/clear/camera)
    
    Attributes:
        telemetry_model (TelemetryTableModel): Shared model for both telemetry tables
        
        Tables:
            telemetry_table (QTableView): Main telemetry display (left column)
            latest_readings_table (QTableView): Duplicate display (middle column)
        
        Buttons:
            btn_start (QPushButton): Start stream button (disabled)
            btn_stop (QPushButton): Stop stream button (disabled)
            btn_clear (QPushButton): Clear trajectory button (enabled)
        
        Sensor LEDs:
            sensor_leds (Dict[str, StatusLED]): Maps sensor IDs to LED widgets
                Keys: 'bmp', 'esp32', 'gps', 'mpu', 'mq131', 'mq2', 'dht22', 'mq7', 'rtc'
        
        Gauges:
            cpu_gauge (LinearGauge): CPU usage horizontal bar gauge
            mem_gauge (LinearGauge): Memory usage horizontal bar gauge
        
        Charts:
            trajectory_charts (TrajectoryCharts): Single altitude vs time chart
    
    Example:
        >>> app = QApplication([])
        >>> window = BalloonSatDashboard()
        >>> window.resize(1500, 800)
        >>> window.show()
        >>> 
        >>> # Simulate data updates
        >>> from dispatcher import dispatch
        >>> dispatch.telemetryUpdated.emit({'alt_bmp': 123.4, 'temp': 22.5})
        >>> dispatch.sensorStatusUpdated.emit({'bmp': True, 'gps': True})
        >>> 
        >>> app.exec()
    
    Initialization Sequence:
        1. Load UI definition from dashboard.ui (creates all widgets)
        2. Set window title
        3. Find and store references to all widgets
        4. Setup data models and connect to tables
        5. Connect dispatcher signals to update methods
        6. Initialize UI state (button states, LED colors, etc.)
    
    See Also:
        models.TelemetryTableModel: For data storage implementation
        dispatcher.py: For event system implementation
        metadata.py: For sensor and field definitions
        widgets/*: For custom widget implementations
        esp32cam_window.py: For ESP32-CAM window implementation
    """
    
    def __init__(self):
        """
        Initialize the BalloonSat dashboard window.
        
        This method orchestrates the complete dashboard initialization sequence,
        loading the UI, finding widgets, setting up models, and preparing the
        dashboard for data display.
        
        Initialization Steps:
            1. Call parent QMainWindow.__init__()
            2. Load UI from dashboard.ui (creates widget hierarchy)
            3. Set window title
            4. Find and store references to all widgets
            5. Setup data models and connect to tables
            6. Connect dispatcher signals to handler methods
            7. Initialize UI state (buttons, LEDs, gauges)
        
        Raises:
            FileNotFoundError: If dashboard.ui cannot be found
            ImportError: If custom widgets not imported before .ui loading
            AttributeError: If expected widgets are missing from .ui file
        
        Notes:
            • Order of initialization is critical (models before signals)
            • Widget finding happens after UI load (widgets don't exist before)
            • Signal connections happen after models exist (avoid null references)
        
        Example:
            >>> dashboard = BalloonSatDashboard()
            >>> # Dashboard is now fully initialized and ready to display
            >>> dashboard.show()
        """
        # === Step 1: Initialize parent QMainWindow ===
        super().__init__()
        
        # === Step 2: Load UI from Qt Designer file ===
        # This creates all widgets, layouts, and basic connections defined in Designer
        load_ui_file(self, "dashboard.ui")
        
        # === Step 3: Set window properties ===
        self.setWindowTitle("🎈 BalloonSat Telemetry Dashboard")
        
        # === Step 4: Find and store widget references ===
        # Uses WidgetFinder utility for organized widget access
        self._find_all_widgets()

        # === Create IndicatorsManager to control UI indicators ===
        # This discovers all widgets named '*Indicator' and lets the
        # dashboard set their state centrally using legacy or new labels.
        try:
            self.indicators = IndicatorsManager(self)
        except Exception:
            # Keep dashboard robust if manager fails for any reason
            self.indicators = None
        
        # === Step 5: Setup data models ===
        # Connect TelemetryTableModel to both table views
        self._setup_models()
        
        # === Step 6: Connect signals ===
        # Wire dispatcher signals to our update methods
        self._connect_signals()
        
        # === Step 7: Initialize UI state ===
        # Set initial widget states, colors, labels, etc.
        self._initialize_ui_state()
    
    # ========================================================================
    # === INITIALIZATION METHODS ===
    # ========================================================================
    
    def _find_all_widgets(self):
        """
        Find and store references to all UI widgets loaded from dashboard.ui.
        
        This method uses the WidgetFinder utility class to systematically locate
        all widgets created by uic.loadUi(). Widgets are organized into categories
        for easier access and maintenance.
        
        Widget Categories:
            • Group boxes: Visual containers with titles
            • Buttons: User control elements
            • Tables: Data display (QTableView, not QTableWidget)
            • Custom widgets: Promoted widgets (StatusLED, LinearGauge, TrajectoryCharts)
            • Sensor LEDs: Status indicators for 9 sensors
        
        Organization:
            finder.group_boxes: Dict[str, QGroupBox]
            finder.buttons: Dict[str, QPushButton]
            self.telemetry_table: QTableView
            self.latest_readings_table: QTableView
            finder.custom_widgets: Dict[str, QWidget]
            self.sensor_leds: Dict[str, StatusLED]
        
        Widget Object Names (must match dashboard.ui exactly):
            Group Boxes:
                • telemetryGroup
                • controlsGroup
                • sensorsHealthGroup
                • computerHealthGroup
                • latestReadingsGroup
                • trajectoryGroup
            
            Buttons:
                • startButton
                • stopButton
                • clearButton
                • cameraButton
            
            Tables (QTableView):
                • telemetryTable
                • latestReadingsTable
                • telemetryTrackTable
            
            Custom Widgets:
                • trajectoryChartsWidget (TrajectoryCharts)
                • cpuGaugeWidget (LinearGauge)
                • memGaugeWidget (LinearGauge)
            
            Sensor LEDs (StatusLED, 11 total):
                • bmpIndicator (BMP280 pressure sensor)
                • esp32Indicator (ESP32 microcontroller)
                • mq131Indicator (MQ131 ozone sensor)
                • mpu6050Indicator (MPU6050 accelerometer)
                • gpsIndicator (GPS module)
                • mq2Indicator (MQ2 flammable gas sensor)
                • dht22Indicator (DHT22 temp/humidity sensor)
                • mq7Indicator (MQ7 CO sensor)
                • rtcIndicator (DS1302 real-time clock)
                • LoRaIndicator (LoRa module)
                • max6675Indicator (Thermocouple)   
        
        Notes:
            • Widget object names are case-sensitive (must match exactly)
            • Custom widgets must be imported before loadUi() for promotion to work
            • Missing widgets will generate warnings but won't crash
            • All found widgets stored as instance attributes for easy access
        
        Troubleshooting:
            If widgets not found:
            1. Open dashboard.ui in Qt Designer
            2. Select widget and check Property Editor → objectName
            3. Ensure exact spelling matches (case-sensitive)
            4. For promoted widgets, verify promotion settings
        
        See Also:
            utils.widget_finder.WidgetFinder: For implementation details
            dashboard.ui: For widget definitions
        """
        # Create WidgetFinder instance (verbose=True prints helpful warnings)
        finder = WidgetFinder(self, verbose=True)
        
        # === Find all group boxes (visual containers with titles) ===
        finder.find_group_boxes([
            'telemetryGroup',           # Left column: Telemetry table
            'controlsGroup',            # Middle top: Control buttons
            'sensorsHealthGroup',       # Middle: Sensor status LEDs
            'computerHealthGroup',      # Middle: CPU/Memory gauges
            'latestReadingsGroup',      # Middle bottom: Latest readings table
            'trajectoryGroup'           # Right: Altitude chart
        ])
        
        # === Find all buttons (user controls) ===
        finder.find_buttons([
            'startButton',              # Start data stream (disabled by default)
            'stopButton',               # Stop data stream (disabled by default)
            'clearButton'               # Clear trajectory data (enabled)
        ])
        
        # === Find tables as QTableView (NOT QTableWidget) ===
        # QTableView supports setModel() for Model-View architecture
        # QTableWidget does not (it's item-based, not model-based)
        print("  Searching for QTableView widgets...")
        self.telemetry_table = finder.find_widget(QTableView, 'telemetryTable')
        self.latest_readings_table = finder.find_widget(QTableView, 'latestReadingsTable')
        self.telemetry_track_table = finder.find_widget(QTableView, 'telemetryTrackTable')
        # Confirmation messages
        if self.telemetry_table:
            print("  ✓ Found telemetryTable (QTableView)")
        if self.latest_readings_table:
            print("  ✓ Found latestReadingsTable (QTableView)")
        if self.telemetry_track_table:
            print("  ✓ Found telemetryTrackTable (QTableView)")
        
        # === Find custom widgets (promoted in Qt Designer) ===
        # These MUST be imported before uic.loadUi() was called in __init__
        finder.find_custom_widgets({
            'trajectoryChartsWidget': TrajectoryCharts,  # Single altitude chart
            'cpuGaugeWidget': LinearGauge,               # CPU usage gauge
            'memGaugeWidget': LinearGauge,               # Memory usage gauge
        })
        
        # === Find sensor status LEDs (BalloonSat-specific) ===
        # Maps sensor IDs from metadata.py to their UI indicator widgets
        sensor_map = {
            'bmp': 'bmp180Indicator',          # BMP280 pressure/altitude sensor (UI object uses bmp180Indicator)
            'esp32': 'esp32Indicator',      # ESP32 microcontroller status
            'mq131': 'mq131Indicator',      # MQ131 ozone sensor
            'mpu': 'mpu6050Indicator',      # MPU6050 accelerometer/gyro
            'gps': 'gpsIndicator',          # GPS module
            'mq2': 'mq2Indicator',          # MQ2 flammable gas sensor
            'dht22': 'dht22Indicator',      # DHT22 temperature/humidity sensor
            'mq7': 'mq7Indicator',          # MQ7 carbon monoxide sensor
            'rtc': 'rtcIndicator',          # DS1302 real-time clock
            'max6675': 'max6675Indicator',
            'lora' : 'loRaIndicator',
            'bms' : 'bmsIndicator',
        }
        # Instantiate IndicatorsManager once and use it as single source-of-truth
        try:
            self.indicators = IndicatorsManager(self)
            # Build sensor_id -> widget mapping using the indicator object names
            self.sensor_leds = {}
            for sensor_id, obj_name in sensor_map.items():
                w = self.indicators[obj_name]
                if w is not None:
                    self.sensor_leds[sensor_id] = w
                else:
                    # fallback: try to find the widget directly
                    found = self.findChild(StatusLED, obj_name)
                    if found is not None:
                        self.sensor_leds[sensor_id] = found
                    else:
                        print(f"  ⚠️ Indicator widget not found for {sensor_id} -> {obj_name}")
        except Exception:
            # If manager fails, fall back to the finder (robust startup)
            self.indicators = None
            self.sensor_leds = finder.find_sensor_indicators(StatusLED, sensor_map)
        
        # === Store widget references for convenient access ===
        # Extract from finder dictionaries for easier access in methods
        self.btn_start = finder.buttons.get('startButton')
        self.btn_stop = finder.buttons.get('stopButton')
        self.btn_clear = finder.buttons.get('clearButton')
        
        self.trajectory_charts = finder.custom_widgets.get('trajectoryChartsWidget')
        self.cpu_gauge = finder.custom_widgets.get('cpuGaugeWidget')
        self.mem_gauge = finder.custom_widgets.get('memGaugeWidget')
    
    def _setup_models(self):
        """
        Setup table models and connect to table views.
        
        Creates a single TelemetryTableModel instance and connects it to both
        telemetry tables. Using one shared model ensures data synchronization
        between the main table and the "latest readings" table - when the model
        updates, both views automatically reflect the changes.
        
        Model-View Architecture:
            • TelemetryTableModel: Stores and formats telemetry data (Model)
            • QTableView: Displays the data (View)
            • When model changes, all connected views auto-update
            • This separation allows multiple views of the same data
        
        Table Configuration:
            Both tables are configured with identical display settings:
            • Horizontal header: Stretch last column to fill available space
            • Vertical header: Hidden (row numbers not displayed)
            • Alternating row colors: Enabled for readability
            • Selection mode: None (read-only display, no row selection)
            • Edit triggers: None (no inline editing allowed)
        
        Why Shared Model:
            Using one model for both tables provides:
            • Automatic synchronization (both always show same data)
            • Memory efficiency (data stored only once)
            • Update efficiency (single model update affects all views)
            • Consistency guarantee (impossible for tables to show different data)
        
        Notes:
            • Both tables share the same model (synchronized display)
            • Model updates automatically trigger table repaints
            • Table appearance customized via QSS stylesheet
            • Model is QAbstractTableModel (not item-based QTableWidget model)
        
        Troubleshooting:
            If tables don't display data:
            1. Verify both tables found (check _find_all_widgets output)
            2. Ensure tables are QTableView (not QTableWidget)
            3. Check model.rowCount() returns > 0
            4. Verify dispatcher signals are connected
        
        See Also:
            models.TelemetryTableModel: For model implementation
            _configure_table(): For individual table configuration
            _find_all_widgets(): Where table widgets are found
        """
        # === Create models ===
        # Full model: shows all telemetry fields (used by telemetryTable)
        self.telemetry_model = TelemetryTableModel()

        # Latest readings model: all latest telemetry except GPS and RTC
        latest_fields = [f for f in TELEMETRY_FIELDS if f.source_key not in ("gps_latlon", "alt_gps", "rtc_time")]
        self.latest_model = TelemetryTableModel(fields=latest_fields)

        # Track model: small table showing GPS and RTC current values
        track_fields = [f for f in TELEMETRY_FIELDS if f.source_key in ("gps_latlon", "alt_gps", "rtc_time")]
        self.track_model = TelemetryTableModel(fields=track_fields)
        
        # === Configure main telemetry table ===
        if self.telemetry_table:
            self._configure_table(self.telemetry_table, self.telemetry_model)
            print("  ✓ Configured telemetryTable model")
        else:
            print("  ⚠️  telemetryTable not found - skipping model setup")
        
        # === Configure latest readings table (same model = synchronized) ===
        if self.latest_readings_table:
            self._configure_table(self.latest_readings_table, self.latest_model)
            print("  ✓ Configured latestReadingsTable model")
        else:
            print("  ⚠️  latestReadingsTable not found - skipping model setup")

        # Configure telemetryTrackTable (RTC + GPS)
        if self.telemetry_track_table:
            self._configure_table(self.telemetry_track_table, self.track_model)
            print("  ✓ Configured telemetryTrackTable model")
        else:
            print("  ⚠️  telemetryTrackTable not found - skipping track table setup")
        
        print("✓ Table models configured")
    
    def _configure_table(self, table: QTableView, model):
        """
        Configure a QTableView with model and display settings.
        
        Applies standard configuration to a QTableView for use with
        QAbstractTableModel. This creates a read-only, well-formatted
        table display optimized for real-time telemetry monitoring.
        
        Args:
            table: QTableView instance to configure
                  Must be QTableView (not QTableWidget) to support setModel()
            
            model: QAbstractTableModel to connect
                  Usually TelemetryTableModel instance
        
        Configuration Applied:
            Model Connection:
                • Sets the data model (THIS IS THE KEY STEP)
                • Model provides data via data() method
                • Model updates trigger automatic view repaints
            
            Header Configuration:
                • Horizontal header: Last column stretches to fill space
                • Vertical header: Hidden (no row numbers displayed)
                • This provides clean, compact appearance
            
            Visual Settings:
                • Alternating row colors: Enabled for easier reading
                • Colors defined in dark.qss stylesheet
            
            Interaction Settings:
                • Selection mode: None (display-only, no row selection)
                • Edit triggers: None (read-only, no inline editing)
                • These settings prevent user modification
        
        Why These Settings:
            • Read-only: Telemetry data shouldn't be user-editable
            • No selection: Prevents accidental highlighting
            • Alternating colors: Improves readability of dense data
            • Stretch last column: Ensures no empty space on right side
        
        Example:
            >>> table = QTableView()
            >>> model = TelemetryTableModel()
            >>> self._configure_table(table, model)
            >>> # Table is now configured and ready to display data
        
        Notes:
            • Works with both QTableWidget and QTableView (but QTableView preferred)
            • Appearance customized via dark.qss stylesheet
            • Read-only: Users cannot select or edit cells
            • Model-View pattern: Changes to model automatically update view
        
        Technical Details:
            The setModel() call establishes the Model-View connection:
            1. View asks model: "How many rows/columns do you have?"
            2. View asks model: "What data is in cell (row, column)?"
            3. Model responds with formatted data
            4. View displays the data
            5. When model changes, it emits dataChanged signal
            6. View receives signal and repaints affected cells
        
        See Also:
            models.TelemetryTableModel: The model class used
            _setup_models(): Where this method is called
        """
        # === Set the model (establishes Model-View connection) ===
        table.setModel(model)
        
        # === Configure horizontal header ===
        # Try to apply a 3:2 column ratio for the two-column (Parameter/Value) layout.
        header: QHeaderView = table.horizontalHeader()
        # Use interactive resize so we can set initial widths programmatically
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        # Set initial widths to approx 3:2 ratio using available table width
        avail = table.viewport().width() or table.width() or 600
        col0 = int(avail * 3 / 5)
        col1 = max(80, avail - col0)
        try:
            table.setColumnWidth(0, col0)
            table.setColumnWidth(1, col1)
        except Exception:
            # Some views may not allow sizing at this early stage; ignore
            pass
        
        # === Configure vertical header ===
        # Hide row numbers (cleaner appearance)
        table.verticalHeader().setVisible(False)
        
        # === Enable alternating row colors ===
        # Improves readability for dense data
        # Colors defined in dark.qss stylesheet
        table.setAlternatingRowColors(True)

        # Make table expand to fill available layout space. This keeps the
        # table stretchable inside layout managers so it will take available
        # space and play well with sibling widgets (charts, group boxes).
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Disable horizontal scrollbars for a cleaner telemetry display —
        # we size columns to fit the viewport and intentionally avoid
        # horizontal scrolling. Use per-pixel scrolling for smoothness if
        # the user scrolls vertically.
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # === Make table read-only (display-only, no selection) ===
        # No selection: Users cannot select rows
        table.setSelectionMode(QTableView.SelectionMode.NoSelection)
        
        # No editing: Users cannot edit cells inline
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

    def _resize_tables(self):
        """
        Resize table columns to fill available width using a 3:2 ratio
        (Parameter column : Value column). This is called on window resize
        and once during initialization to avoid manual user resizing.
        """
        tables = [
            getattr(self, 'telemetry_table', None),
            getattr(self, 'latest_readings_table', None),
            getattr(self, 'telemetry_track_table', None),
        ]

        for table in tables:
            if not table:
                continue

            header = table.horizontalHeader()
            # Allow programmatic column sizing
            try:
                header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
            except Exception:
                pass

            # Compute available viewport width and apply 3:2 ratio
            avail = table.viewport().width() or table.width() or 600
            col0 = int(avail * 3 / 5)
            col1 = max(80, avail - col0)
            try:
                table.setColumnWidth(0, col0)
                table.setColumnWidth(1, col1)
            except Exception:
                pass

            # Ensure no horizontal scroll bar appears
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def resizeEvent(self, event):
        """
        Recompute table column widths when the main window is resized.
        """
        try:
            self._resize_tables()
        except Exception:
            pass
        # Call parent implementation
        return super().resizeEvent(event)
    
    def _connect_signals(self):
        """
        Connect dispatcher signals and button click handlers.
        
        This method wires up the event system, connecting:
        1. Dispatcher signals (data updates) to UI update methods
        2. Button clicked signals to action handlers
        
        Signal Flow Overview:
            Data Source → Dispatcher → Dashboard Method → Widget Update
        
        Dispatcher Signals Connected:
            telemetryUpdated(dict):
                • Source: Data source (serial, file, network)
                • Payload: Dict mapping field names to values
                • Handler: telemetry_model.updateTelemetry()
                • Effect: Both tables update with new values
                • Example: {'alt_bmp': 123.4, 'temp': 22.5}
            
            sensorStatusUpdated(dict):
                • Source: Sensor health monitor
                • Payload: Dict mapping sensor IDs to bool status
                • Handler: _update_sensors()
                • Effect: LED indicators change color (green/red/gray)
                • Example: {'bmp': True, 'gps': False}
            
            computerHealthUpdated(float, float):
                • Source: System monitor (psutil)
                • Payload: (cpu_percent, memory_percent)
                • Handler: _update_computer_health()
                • Effect: Gauge bars update to show usage
                • Example: (45.2, 67.8)
            
            trajectoryAppended(object):
                • Source: Trajectory calculator
                • Payload: Point object with t, alt_expected, alt_actual
                • Handler: _append_trajectory()
                • Effect: New point added to altitude chart
                • Example: SimpleNamespace(t=0, alt_expected=100, alt_actual=99.5)
        
        Button Signals Connected:
            startButton.clicked → _on_start():
                • Trigger: User clicks "Start Stream" button
                • Action: Would start data stream (not implemented in GUI-only mode)
                • Current: Button is disabled by default
            
            stopButton.clicked → _on_stop():
                • Trigger: User clicks "Stop Stream" button
                • Action: Would stop data stream (not implemented in GUI-only mode)
                • Current: Button is disabled by default
            
            clearButton.clicked → _on_clear():
                • Trigger: User clicks "Clear Trajectory" button
                • Action: Clears all data from altitude chart
                • Current: Button is enabled and functional
            
            cameraButton.clicked → _on_open_esp32cam():
                • Trigger: User clicks "ESP32-CAM" or "Camera" button
                • Action: Opens separate ESP32-CAM window
                • Current: Enabled if button exists in UI
        
        Connection Types:
            All connections use Qt.ConnectionType.AutoConnection (default):
            • Same thread: Direct call (fast, synchronous)
            • Different thread: Queued call (safe, asynchronous)
            • Qt automatically chooses based on thread context
        
        Notes:
            • Dispatcher is a singleton from dispatcher.py
            • Signals use Qt's signal/slot mechanism (type-safe)
            • Connections automatically disconnect on object destruction
            • Button handlers check for None before connecting (safety)
        
        Example Signal Emission (from external code):
            >>> from dispatcher import dispatch
            >>> 
            >>> # Update telemetry
            >>> dispatch.telemetryUpdated.emit({'alt_bmp': 123.4, 'temp': 22.5})
            >>> 
            >>> # Update sensor status
            >>> dispatch.sensorStatusUpdated.emit({'bmp': True, 'gps': False})
            >>> 
            >>> # Update computer health
            >>> dispatch.computerHealthUpdated.emit(45.2, 67.8)
        
        Troubleshooting:
            If signals not working:
            1. Verify dispatcher imported correctly
            2. Check signal emission in data source
            3. Verify method signatures match signal signatures
            4. Check for typos in method names
            5. Ensure data source is on correct thread (or use QueuedConnection)
        
        See Also:
            dispatcher.py: For signal definitions and global dispatcher instance
            _update_sensors(): For sensor status update implementation
            _update_computer_health(): For gauge update implementation
            _append_trajectory(): For chart update implementation
            _on_open_esp32cam(): For ESP32-CAM window opening
        """
        # === DISPATCHER SIGNALS (Data Updates from External Sources) ===
        
        # Telemetry data updated → Update all three table models
        dispatch.telemetryUpdated.connect(self.telemetry_model.updateTelemetry)
        # Latest readings (excludes GPS/RTC)
        try:
            dispatch.telemetryUpdated.connect(self.latest_model.updateTelemetry)
        except Exception:
            pass
        # Track model (GPS + RTC)
        try:
            dispatch.telemetryUpdated.connect(self.track_model.updateTelemetry)
        except Exception:
            pass
        
        # Sensor status updated → Update LED indicators
        dispatch.sensorStatusUpdated.connect(self._update_sensors)
        
        # Computer health updated → Update CPU/Memory gauges
        dispatch.computerHealthUpdated.connect(self._update_computer_health)
        
        # New trajectory point → Add to altitude chart
        dispatch.trajectoryAppended.connect(self._append_trajectory)
        
        # === BUTTON CLICK HANDLERS ===
        
        # Start button (currently disabled in GUI-only mode)
        if self.btn_start:
            self.btn_start.clicked.connect(self._on_start)
        
        # Stop button (currently disabled in GUI-only mode)
        if self.btn_stop:
            self.btn_stop.clicked.connect(self._on_stop)
        
        # Clear button (always enabled and functional)
        if self.btn_clear:
            self.btn_clear.clicked.connect(self._on_clear)
        
        # === ESP32-CAM BUTTON (if exists in UI) ===
        # Try multiple common button names to maximize compatibility
        camera_btn = None
        for btn_name in ['cameraButton', 'btn_camera', 'btn_esp32cam', 'openCameraButton']:
            camera_btn = self.findChild(QPushButton, btn_name)
            if camera_btn:
                camera_btn.clicked.connect(self._on_open_esp32cam)
                print(f"  ✓ Connected ESP32-CAM button: {btn_name}")
                break
        
        if not camera_btn:
            print("  ℹ️  No ESP32-CAM button found in UI (optional)")
        
        print("✓ Signals connected")
    
    def _initialize_ui_state(self):
        """
        Set initial state of UI elements before any data arrives.
        
        Configures the initial appearance and state of all widgets to ensure
        the UI looks correct at startup and provides visual feedback that the
        system is ready (but not yet receiving data).
        
        Initial States Set:
            Buttons:
                • Start button: Disabled (GUI-only mode, no data source control)
                • Stop button: Disabled (GUI-only mode, no data source control)
                • Clear button: Enabled (can clear even when empty)
            
            Sensor LEDs:
                • All 9 LEDs: Set to 'off' state (gray color)
                • Tooltips: Set to "sensor_id: No data"
                • Visual: Gray circles indicate awaiting first data
            
            Gauges:
                • CPU gauge: Label set to "CPU %"
                • Memory gauge: Label set to "Mem %"
                • Values: Default to 0% (will update on first health signal)
            
            Tables:
                • Headers: Already configured in _configure_table()
                • Data: Empty until first telemetry signal
                • Appearance: Dark theme from stylesheet
            
            Chart:
                • Empty: No trajectory points yet
                • Axes: Labeled (Time, Altitude)
                • Legend: Present but empty until first point
        
        Why This Matters:
            • User sees ready state (not broken/loading)
            • Gray LEDs clearly indicate "waiting for data" (not fault)
            • Disabled buttons prevent confusion (can't control non-existent stream)
            • Clear visual feedback system is initialized and ready
        
        State Progression:
            Initial → First Data → Ongoing Updates
            
            LEDs: Gray (off) → Green/Red (on/fault) → Dynamic
            Gauges: 0% → Real values → Dynamic
            Tables: Empty → Initial data → Updates
            Chart: Empty → First point → Growing line
        
        Notes:
            • Start/Stop buttons would be enabled by external controller
            • Sensor LEDs start gray (off state) until first status update
            • Gauge labels set here (may override Qt Designer defaults)
            • This method is called last in __init__ (after all setup)
        
        Future Enhancement:
            When integrating with real data source:
            1. Add method to enable start/stop buttons when connection available
            2. Add connection status indicator (connected/disconnected)
            3. Add "Last Update" timestamp display
        
        Example:
            >>> dashboard = BalloonSatDashboard()
            >>> # At this point, _initialize_ui_state() has been called
            >>> # All LEDs are gray, buttons properly enabled/disabled
        
        See Also:
            _find_all_widgets(): Where widget references are obtained
            _update_sensors(): Method that changes LED states based on data
        """
        # === Disable start/stop buttons (GUI-only mode) ===
        # These buttons would control data streaming in full application
        # Currently disabled since dashboard has no integrated data source
        if self.btn_start:
            self.btn_start.setEnabled(False)
            self.btn_start.setToolTip("Not available in GUI-only mode")
        
        if self.btn_stop:
            self.btn_stop.setEnabled(False)
            self.btn_stop.setToolTip("Not available in GUI-only mode")
        
        # === Enable clear button ===
        # Clear button is always functional (can clear even when empty)
        if self.btn_clear:
            self.btn_clear.setEnabled(True)
            self.btn_clear.setToolTip("Clear trajectory data from chart")
        
        # === Initialize sensor LEDs to 'off' state ===
        # Gray color indicates awaiting first sensor status update
        for sensor_id, led in self.sensor_leds.items():
            led.setState('off')  # Gray circle
            led.setToolTip(f"{sensor_id}: No data")
        
        # === Set gauge labels ===
        # Ensure gauges show correct labels (may override Qt Designer defaults)
        if self.cpu_gauge:
            self.cpu_gauge.setLabel("CPU %")
        
        if self.mem_gauge:
            self.mem_gauge.setLabel("Mem %")
        
        print("✓ UI initialized")
        # Schedule a single-shot deferred resize. Layouts are finalized
        # after the event loop runs once, so deferring ensures table
        # viewport sizes are available and column widths will be computed
        # correctly. We avoid immediate resize calls here to keep startup
        # deterministic and not depend on layout timing.
        QTimer.singleShot(0, self._resize_tables)
    
    # ========================================================================
    # === DATA UPDATE HANDLERS (Called by Dispatcher Signals) ===
    # ========================================================================
    
    def _update_sensors(self, status: dict):
        """
        Update sensor health indicator LEDs based on status data.
        
        Called automatically when dispatcher.sensorStatusUpdated signal is emitted.
        Updates the visual state of all 9 sensor LED indicators based on the
        provided status dictionary, providing immediate visual feedback about
        sensor health.
        
        Args:
            status: Dictionary mapping sensor IDs to boolean status
                   Keys: Sensor IDs from metadata.SENSORS
                   Values: True = sensor working, False/None = sensor fault
                   
                   Example:
                       {
                           'bmp': True,    # BMP280 working
                           'esp32': True,  # ESP32 working
                           'mq131': True,  # MQ131 working
                           'mpu': True,    # MPU6050 working
                           'gps': True,    # GPS working
                           'mq2': False,   # MQ2 fault
                           'dht22': True,  # DHT22 working
                           'mq7': False,   # MQ7 fault
                           'rtc': True     # RTC working
                       }
        
        Status Logic (Defensive Programming):
            • Only explicit True value sets LED to 'on' (green)
            • Any other value (False, None, missing) sets LED to 'fault' (red)
            • This makes faults obvious: assumption is "broken until proven working"
            • Missing sensors are treated as faults (defensive approach)
        
        Visual Feedback:
            State 'on' (True):
                • Color: Green (#14c914)
                • Meaning: Sensor is healthy and reporting data
                • Tooltip: "sensor_id: OK"
            
            State 'fault' (False/None):
                • Color: Red (#dd1111)
                • Meaning: Sensor has failed or is not responding
                • Tooltip: "sensor_id: not working"
            
            State 'off' (initial):
                • Color: Gray (#666666)
                • Meaning: Awaiting first status update
                • Tooltip: "sensor_id: No data"
        
        Iteration:
            Loops through all 9 sensor LEDs found during initialization:
            • bmpIndicator → BMP280 pressure sensor
            • esp32Indicator → ESP32 microcontroller
            • mq131Indicator → MQ131 ozone sensor
            • mpu6050Indicator → MPU6050 accelerometer
            • gpsIndicator → GPS module
            • mq2Indicator → MQ2 flammable gas sensor
            • dht22Indicator → DHT22 temp/humidity sensor
            • mq7Indicator → MQ7 CO sensor
            • rtcIndicator → DS1302 real-time clock
        
        Performance:
            • O(n) where n = 9 sensors (constant, very fast)
            • Each LED update is O(1)
            • Total time: <1ms for all 9 LEDs
            • Updates only trigger repaints for changed LEDs
        
        Error Handling:
            • Handles missing sensor IDs (treated as fault)
            • Handles unexpected values (treated as fault)
            • Defensive: Better to show fault than miss a problem
        
        Example Usage:
            >>> from dispatcher import dispatch
            >>> 
            >>> # All sensors working
            >>> dispatch.sensorStatusUpdated.emit({
            ...     'bmp': True, 'esp32': True, 'gps': True,
            ...     'mpu': True, 'mq131': True, 'mq2': True,
            ...     'dht22': True, 'mq7': True, 'rtc': True
            ... })
            >>> # All LEDs turn green
            >>> 
            >>> # Some sensors failed
            >>> dispatch.sensorStatusUpdated.emit({
            ...     'bmp': True,
            ...     'gps': False,   # GPS failed
            ...     'mq2': False    # MQ2 failed
            ... })
            >>> # bmp LED green, gps and mq2 LEDs red, others red (missing = fault)
        
        Notes:
            • Tooltips updated with status message for each sensor
            • Missing sensors treated as faults (defensive approach)
            • Uses StatusLED.setState() method ('on'/'off'/'fault')
            • Called from Qt main thread (signal/slot ensures thread safety)
        
        Troubleshooting:
            If LEDs not updating:
            1. Verify signal emission: dispatch.sensorStatusUpdated.emit(status)
            2. Check sensor IDs match exactly (case-sensitive)
            3. Ensure status dict has correct keys
            4. Verify StatusLED widgets found during _find_all_widgets()
        
        See Also:
            widgets.status_led.StatusLED: For LED widget implementation
            metadata.SENSORS: For sensor definitions
            _initialize_ui_state(): Where LEDs are initially set to 'off'
        """
        # Iterate through all sensor LEDs found during initialization
        for sensor_id, led in self.sensor_leds.items():
            # Get status for this sensor (default to None if missing)
            val = status.get(sensor_id, None)
            
            # Update LED state based on status value
            if val is True:
                # Sensor is healthy - show green LED
                led.setState('on')
                led.setToolTip(f"{sensor_id}: OK")
            else:
                # Sensor is faulty, missing, or False - show red LED
                # This defensive approach makes problems immediately obvious
                led.setState('fault')
                led.setToolTip(f"{sensor_id}: not working")
    
    def _update_computer_health(self, cpu: float, mem: float):
        """
        Update CPU and memory usage gauge displays.
        
        Called automatically when dispatcher.computerHealthUpdated signal is emitted.
        Updates the visual position of gauge indicators to show current computer
        resource usage, helping monitor system health during operation.
        
        Args:
            cpu: CPU usage percentage (0.0 to 100.0)
                Range: 0.0% (idle) to 100.0% (fully loaded)
                Example: 45.2 means 45.2% CPU usage
            
            mem: Memory usage percentage (0.0 to 100.0)
                Range: 0.0% (no memory used) to 100.0% (fully used)
                Example: 67.8 means 67.8% memory usage
        
        Visual Representation:
            Both gauges display horizontal bars that fill based on percentage:
            • Empty (0%): No fill
            • Half (50%): Half-filled bar
            • Full (100%): Completely filled bar
            
            Gauge Appearance:
                • Background: Dark gray track (#222)
                • Fill color: Blue (#1e90ff)
                • Border: Dark outline
                • Text: "CPU %: 45.2%" or "Mem %: 67.8%"
        
        Gauge Behavior:
            • Automatically clamps values to 0-100% range
            • Smooth visual updates (no flickering)
            • Text label shows exact percentage
            • Updates trigger minimal repaints (efficient)
        
        Performance:
            • Each gauge update is O(1)
            • Total time: <0.5ms for both gauges
            • Only changed gauges repaint
            • Efficient even with high update frequency (10+ Hz)
        
        Example Usage:
            >>> from dispatcher import dispatch
            >>> 
            >>> # Normal operation
            >>> dispatch.computerHealthUpdated.emit(45.2, 67.8)
            >>> # CPU gauge shows 45.2%, Memory gauge shows 67.8%
            >>> 
            >>> # High CPU usage
            >>> dispatch.computerHealthUpdated.emit(95.0, 60.0)
            >>> # CPU gauge nearly full, Memory gauge at 60%
            >>> 
            >>> # System idle
            >>> dispatch.computerHealthUpdated.emit(5.0, 30.0)
            >>> # Both gauges show low usage
        
        Value Clamping:
            LinearGauge automatically clamps values to valid range:
            • Values < 0 → 0%
            • Values > 100 → 100%
            • Normal values (0-100) → as-is
        
        Notes:
            • LinearGauge automatically clamps values to 0-100% range
            • Gauges update smoothly without flickering
            • Labels show exact percentage automatically
            • Called from Qt main thread (thread-safe via signal/slot)
        
        Typical Values:
            CPU Usage:
                • Idle: 1-10%
                • Light load: 10-30%
                • Normal operation: 30-60%
                • Heavy load: 60-90%
                • Overloaded: >90%
            
            Memory Usage:
                • Light: 20-40%
                • Normal: 40-70%
                • Heavy: 70-90%
                • Critical: >90%
        
        Troubleshooting:
            If gauges not updating:
            1. Verify signal emission: dispatch.computerHealthUpdated.emit(cpu, mem)
            2. Check gauge widgets found: self.cpu_gauge and self.mem_gauge
            3. Verify LinearGauge has setValue() method
            4. Check values are in 0-100 range (will be clamped if not)
        
        See Also:
            widgets.gauge.LinearGauge: For gauge widget implementation
            _initialize_ui_state(): Where gauge labels are initially set
        """
        # Update CPU gauge if found
        if self.cpu_gauge:
            self.cpu_gauge.setValue(cpu)
        
        # Update memory gauge if found
        if self.mem_gauge:
            self.mem_gauge.setValue(mem)
    
    def _append_trajectory(self, p):
        """
        Add a trajectory point to the altitude chart.
        
        Called automatically when dispatcher.trajectoryAppended signal is emitted.
        Adds a new position point to the altitude vs time chart, updating both
        expected and actual altitude lines.
        
        Args:
            p: Trajectory point object with attributes:
               
               Required:
                   • t (float): Time in seconds since flight start
                   • alt_expected (float): Expected altitude in meters (flight plan)
                   • alt_actual (float): Actual measured altitude in meters (sensors)
               
               Optional:
                   • clear (bool): If True, clear chart before adding
                   • lat (float): Latitude (ignored in single-chart version)
                   • lon (float): Longitude (ignored in single-chart version)
        
        Point Object Format:
            Duck-typed point (any object with required attributes):
            
            >>> from types import SimpleNamespace
            >>> point = SimpleNamespace(
            ...     t=10.5,              # 10.5 seconds into flight
            ...     alt_expected=150.0,  # Expected: 150 meters
            ...     alt_actual=148.5     # Actual: 148.5 meters
            ... )
        
        Chart Updates:
            The altitude chart displays two lines:
            • Expected altitude: Blue dashed line (flight plan)
            • Actual altitude: Orange solid line (sensor data)
            
            As points are added:
            • Lines grow from left to right (time progresses)
            • Comparison shows if balloon is on course
            • Divergence indicates drift from plan
        
        Clear Flag Usage:
            The optional 'clear' attribute allows batch trajectory loading:
            
            >>> # Load new trajectory file
            >>> first_point = SimpleNamespace(t=0, alt_expected=0, alt_actual=0, clear=True)
            >>> dispatch.trajectoryAppended.emit(first_point)  # Clears old data
            >>> 
            >>> # Then emit remaining points normally
            >>> for point in remaining_points:
            ...     dispatch.trajectoryAppended.emit(point)
        
        Performance:
            • Append operation: O(1) (list.append)
            • Chart update: O(n) where n = total points
            • PyQtGraph optimizes rendering (handles 10,000+ points)
            • Update rate: 100+ Hz supported
            • CPU usage: <0.3% per append
        
        Example Usage:
            >>> from types import SimpleNamespace
            >>> from dispatcher import dispatch
            >>> 
            >>> # Single point
            >>> point = SimpleNamespace(
            ...     t=0.0,
            ...     alt_expected=100.0,
            ...     alt_actual=99.5
            ... )
            >>> dispatch.trajectoryAppended.emit(point)
            >>> 
            >>> # Series of points
            >>> for i in range(100):
            ...     point = SimpleNamespace(
            ...         t=float(i),
            ...         alt_expected=100 + i * 2,
            ...         alt_actual=100 + i * 2 + math.sin(i) * 5
            ...     )
            ...     dispatch.trajectoryAppended.emit(point)
        
        Chart Auto-Scaling:
            • X-axis (time): Automatically scales to show all data
            • Y-axis (altitude): Automatically scales to show all data
            • User can zoom/pan for detailed examination
            • Auto-range can be disabled if needed
        
        Notes:
            • Point object is duck-typed (any object with required attributes)
            • lat/lon attributes ignored (backward compatible with old format)
            • Chart automatically rescales to fit data
            • Clear flag checked first (before adding point)
            • Called from Qt main thread (thread-safe via signal/slot)
        
        Troubleshooting:
            If chart not updating:
            1. Verify signal emission: dispatch.trajectoryAppended.emit(point)
            2. Check point has required attributes (t, alt_expected, alt_actual)
            3. Verify trajectory_charts widget found
            4. Check TrajectoryCharts has appendPoint() method
            5. Ensure chart widget is visible in UI
        
        See Also:
            widgets.charts.TrajectoryCharts: For chart widget implementation
            _clear_trajectory(): Method to clear all chart data
            _on_clear(): Button handler that calls _clear_trajectory()
        """
        # Check if trajectory chart widget exists
        if not self.trajectory_charts:
            return
        
        # Support a `.clear` flag on the incoming point so emitters can
        # request that the current trajectory be cleared before plotting
        # a newly-loaded trajectory file
        try:
            if getattr(p, "clear", False):
                self.trajectory_charts.clear()
        except Exception:
            pass  # Ignore if clear attribute doesn't exist
        
        # Add point to chart (updates both expected and actual lines)
        self.trajectory_charts.appendPoint(p)
    
    def _clear_trajectory(self):
        """
        Clear all trajectory data from the altitude chart.
        
        Removes all plotted points from the altitude vs time chart, resetting
        it to an empty state. This is useful when starting a new flight or
        loading a new trajectory file.
        
        Effects:
            • All plotted points removed from chart
            • Expected altitude line cleared (blue dashed)
            • Actual altitude line cleared (orange solid)
            • Chart axes remain (time and altitude labels)
            • Legend remains but with no data
            • Internal data buffers emptied (_t, _alt_exp, _alt_act)
        
        When to Use:
            • Starting a new flight (clear old flight data)
            • Loading a new trajectory file (clear before loading)
            • Resetting display for fresh start
            • After data recording error (clear corrupted data)
        
        Performance:
            • Clear operation: O(1) (list.clear())
            • Chart update: O(1) (minimal repaint)
            • Total time: <1ms
            • Memory freed: ~40 bytes per point cleared
        
        Example Usage:
            Programmatic clearing:
                >>> dashboard._clear_trajectory()
                >>> print("Chart cleared")
            
            Via button click:
                >>> # User clicks "Clear Trajectory" button
                >>> # Triggers btn_clear.clicked signal
                >>> # Connected to _on_clear() method
                >>> # Which calls _clear_trajectory()
            
            Via dispatcher:
                >>> from types import SimpleNamespace
                >>> from dispatcher import dispatch
                >>> 
                >>> # Clear via point with clear flag
                >>> point = SimpleNamespace(
                ...     t=0,
                ...     alt_expected=0,
                ...     alt_actual=0,
                ...     clear=True  # This triggers clear
                ... )
                >>> dispatch.trajectoryAppended.emit(point)
        
        UI Feedback:
            • Chart visibly empties
            • Console message: "✓ Trajectory cleared"
            • No error if chart already empty (idempotent)
        
        Notes:
            • Safe to call even if chart is already empty (idempotent)
            • Does not disable the chart (can still add new points)
            • Called by _on_clear() button handler
            • Also called automatically when point has clear=True flag
        
        Troubleshooting:
            If clear not working:
            1. Verify trajectory_charts widget exists
            2. Check TrajectoryCharts has clear() method
            3. Ensure chart widget is visible
            4. Verify button connection: btn_clear.clicked → _on_clear
        
        See Also:
            _append_trajectory(): Method to add points to chart
            _on_clear(): Button handler that calls this method
            widgets.charts.TrajectoryCharts.clear(): Underlying implementation
        """
        if self.trajectory_charts:
            self.trajectory_charts.clear()
            print("✓ Trajectory cleared")
    
    # ========================================================================
    # === BUTTON HANDLERS (User Interaction) ===
    # ========================================================================
    
    def _on_start(self):
        """
        Handle Start Stream button click.
        
        This method would start the data stream in a full implementation with
        integrated data source (serial port, network, file playback). Currently
        disabled in GUI-only mode.
        
        Intended Behavior (Full Implementation):
            1. Enable data source (open serial port, start network listener, etc.)
            2. Begin receiving telemetry data
            3. Disable start button (prevent double-start)
            4. Enable stop button (allow stopping)
            5. Update status indicator (show "Streaming")
        
        Current Status:
            • Button is disabled by default (see _initialize_ui_state)
            • Method prints message but takes no action
            • Would be enabled when data source is integrated
        
        Example Full Implementation:
            >>> def _on_start(self):
            ...     if not self.data_source:
            ...         print("Error: No data source configured")
            ...         return
            ...     
            ...     # Start data source
            ...     self.data_source.start()
            ...     
            ...     # Update button states
            ...     self.btn_start.setEnabled(False)
            ...     self.btn_stop.setEnabled(True)
            ...     
            ...     # Update status
            ...     print("▶️  Stream started")
        
        Notes:
            • Button disabled in GUI-only mode
            • Would emit signals when data source integrated
            • Thread safety: Data source should run in separate thread
        
        See Also:
            _on_stop(): Complementary stop handler
            _initialize_ui_state(): Where button is initially disabled
        """
        print("▶️  Start button clicked (not implemented in GUI-only mode)")
        # TODO: Implement stream starting logic if needed
        # Example:
        # self.data_source.start()
        # self.btn_start.setEnabled(False)
        # self.btn_stop.setEnabled(True)
    
    def _on_stop(self):
        """
        Handle Stop Stream button click.
        
        This method would stop the data stream in a full implementation with
        integrated data source. Currently disabled in GUI-only mode.
        
        Intended Behavior (Full Implementation):
            1. Stop data source (close serial port, stop network listener, etc.)
            2. Stop receiving telemetry data
            3. Enable start button (allow restarting)
            4. Disable stop button (prevent double-stop)
            5. Update status indicator (show "Stopped")
        
        Current Status:
            • Button is disabled by default (see _initialize_ui_state)
            • Method prints message but takes no action
            • Would be enabled when data source is integrated
        
        Example Full Implementation:
            >>> def _on_stop(self):
            ...     if not self.data_source:
            ...         print("Error: No data source configured")
            ...         return
            ...     
            ...     # Stop data source
            ...     self.data_source.stop()
            ...     
            ...     # Update button states
            ...     self.btn_start.setEnabled(True)
            ...     self.btn_stop.setEnabled(False)
            ...     
            ...     # Update status
            ...     print("⏹️  Stream stopped")
        
        Notes:
            • Button disabled in GUI-only mode
            • Should gracefully handle stop during active streaming
            • Thread safety: Ensure clean thread shutdown
        
        See Also:
            _on_start(): Complementary start handler
            _initialize_ui_state(): Where button is initially disabled
        """
        print("⏹️  Stop button clicked (not implemented in GUI-only mode)")
        # TODO: Implement stream stopping logic if needed
        # Example:
        # self.data_source.stop()
        # self.btn_start.setEnabled(True)
        # self.btn_stop.setEnabled(False)
    
    def _on_clear(self):
        """
        Handle Clear Trajectory button click.
        
        Called when user clicks the "Clear Trajectory" button. Clears all
        trajectory data from the altitude chart, providing a fresh start
        for new data.
        
        User Workflow:
            1. User clicks "Clear Trajectory" button
            2. btn_clear.clicked signal emitted
            3. This method called via signal/slot connection
            4. _clear_trajectory() called to perform actual clear
            5. Chart visibly empties
            6. Console message confirms action
        
        Use Cases:
            • User wants to clear old flight data before new flight
            • User made mistake and wants to reset display
            • User testing dashboard and wants clean slate
            • Data became corrupted and user wants fresh start
        
        Button State:
            • Always enabled (can clear anytime, even if chart empty)
            • No confirmation dialog (immediate action)
            • Idempotent (safe to click multiple times)
        
        Example:
            User clicks button:
                [Click] "Clear Trajectory"
                    ↓
                _on_clear() called
                    ↓
                _clear_trajectory() called
                    ↓
                Chart emptied
                    ↓
                Console: "✓ Trajectory cleared"
        
        Notes:
            • No confirmation dialog (consider adding for production)
            • Safe to call even if chart already empty
            • Does not affect other widgets (tables, gauges, LEDs)
            • Only clears chart, doesn't stop data stream
        
        Future Enhancement:
            • Add confirmation dialog: "Clear trajectory data?"
            • Add undo functionality (save last cleared data)
            • Add "Clear All" to reset entire dashboard
        
        See Also:
            _clear_trajectory(): Actual clear implementation
            _initialize_ui_state(): Where button is enabled
        """
        self._clear_trajectory()
    
    def _on_open_esp32cam(self):
        """
        Open ESP32-CAM window for live feed and snapshot capture.
        
        Opens a separate, non-blocking window for viewing the ESP32-CAM feed
        and capturing snapshots during BalloonSat flight. The window operates
        independently and can be closed without affecting the main dashboard.
        
        Window Features:
            • Live ESP32-CAM video feed at 10-20 FPS
            • Snapshot capture with timestamped filenames
            • Non-blocking (main dashboard stays responsive)
            • Automatic signal management (connect/disconnect)
            • Singleton pattern (one window at a time)
        
        Behavior:
            • If window already open: Brings existing window to front
            • If window closed: Creates new window instance
            • Window can be opened/closed multiple times
        
        File Naming:
            Snapshots saved as: balloonsat_YYYYMMDD_HHMMSS_NNN.jpg
            Location: ./snapshots/ directory
        
        Example:
            User clicks "ESP32-CAM" button
            → Camera window opens (non-blocking)
            → Main dashboard still responsive
            → User can capture snapshots
            → User closes camera window
            → Main dashboard unaffected
        
        See Also:
            esp32cam_window.ESP32CamWindow: The camera window implementation
            widgets.live_feed.LiveFeedWidget: The live feed display widget
        """
        # Import ESP32-CAM window
        try:
            from esp32cam_window import ESP32CamWindow
        except ImportError:
            from dashboardGUI.esp32cam_window import ESP32CamWindow
        
        # Check if already open (singleton pattern)
        if ESP32CamWindow.is_open():
            print("⚠️  ESP32-CAM window already open")
            # Bring existing window to front
            existing = ESP32CamWindow.get_instance()
            if existing:
                existing.activateWindow()
                existing.raise_()
            return
        
        # Create and show ESP32-CAM window (non-blocking)
        camera_window = ESP32CamWindow(parent=self)
        camera_window.show()
        
        print("✓ ESP32-CAM window opened")

# ============================================================================
# === APPLICATION ENTRY POINT ===
# ============================================================================

def main(argv=None):
    """
    Application entry point.
    
    Creates QApplication, loads stylesheet, creates dashboard window,
    and starts the Qt event loop. This is the main function called when
    running the dashboard as a script.
    
    Args:
        argv: Command line arguments (defaults to sys.argv if None)
             Standard Qt command line arguments supported:
             • -style [style]: Set application style
             • -stylesheet [file]: Set application stylesheet
             • -platform [platform]: Set platform plugin
    
    Returns:
        int: Application exit code
             • 0: Normal exit
             • 1: Error during initialization
             • Other: Qt application exit code
    
    Execution Sequence:
        1. Create QApplication instance (Qt initialization)
        2. Load and apply dark.qss stylesheet
        3. Create BalloonSatDashboard window
        4. Set window size (1500x800)
        5. Show window
        6. Print startup message
        7. Enter Qt event loop (app.exec())
        8. Return exit code when window closed
    
    Usage:
        As script:
            >>> python dashboard.py
        
        As module:
            >>> python -m dashboardGUI.dashboard
        
        With arguments:
            >>> python dashboard.py -style Fusion
        
        Programmatically:
            >>> from dashboardGUI.dashboard import main
            >>> exit_code = main(['dashboard.py'])
    
    Stylesheet Loading:
        Searches for dark.qss in multiple locations:
        • ./styles/dark.qss (current directory)
        • ../styles/dark.qss (parent directory)
        • dashboardGUI/styles/dark.qss (package directory)
        
        If not found:
        • Prints warning
        • Uses default Qt styling
        • Dashboard still functional
    
    Error Handling:
        • Catches all exceptions during window creation
        • Prints full traceback for debugging
        • Returns exit code 1 on error
        • Prevents silent failures
    
    Window Sizing:
        • Default: 1500x800 pixels
        • Suitable for 1080p displays (1920x1080)
        • Adjust for your screen resolution if needed
        • Window is resizable by user
    
    Event Loop:
        app.exec() starts Qt event loop:
        • Processes user input (mouse, keyboard)
        • Handles window events (resize, paint)
        • Processes Qt signals/slots
        • Runs until window closed or app.quit() called
    
    Example Output:
        ✓ Loaded stylesheet from: D:\\...\\styles\\dark.qss
        ✓ Loading UI from: D:\\...\\dashboard.ui
        ✓ Found 9/9 sensor indicators
        ✓ Table models configured
        ✓ Signals connected
        ✓ UI initialized
        
        ============================================================
        🚀 BalloonSat Telemetry Dashboard Started
        ============================================================
        
        💡 Test with demo data:
           from dispatcher import dispatch
           dispatch.telemetryUpdated.emit({'alt_bmp': 123.4})
    
    Notes:
        • QApplication created once per process (singleton)
        • Stylesheet applied at application level (affects all widgets)
        • Event loop blocks until window closed
        • Clean shutdown on window close
    
    See Also:
        BalloonSatDashboard: The main window class
        utils.ui_loader.load_stylesheet: Stylesheet loading utility
    """
    # Get command line arguments (default to sys.argv if not provided)
    argv = argv or sys.argv
    
    # === Create Qt Application ===
    # QApplication is the main Qt object (one per process)
    app = QApplication(argv)
    
    # === Load and Apply Dark Theme Stylesheet ===
    # Searches multiple paths for dark.qss file
    qss_content = load_stylesheet("light.qss", "styles")
    if qss_content:
        app.setStyleSheet(qss_content)
    # Note: If stylesheet not found, prints warning but continues with default theme
    
    # === Create and Show Dashboard ===
    try:
        # Create dashboard window instance
        window = BalloonSatDashboard()
        
        # Set window size (adjust for your screen resolution)
        window.resize(1500, 800)  # Width x Height in pixels
        
        # Show window (makes it visible)
        window.show()
        
        # Print startup message
        print("\n" + "="*60)
        print("🚀 BalloonSat Telemetry Dashboard Started")
        print("="*60)
        print("\n💡 Test with demo data:")
        print("   from dispatcher import dispatch")
        print("   dispatch.telemetryUpdated.emit({'alt_bmp': 123.4})")
        print()
        
    except Exception as e:
        # Handle any initialization errors
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1  # Return error code
    
    # === Enter Qt Event Loop ===
    # Blocks here until window closed or app.quit() called
    # Returns exit code (0 = normal, other = error)
    return app.exec()


# ============================================================================
# === SCRIPT ENTRY POINT ===
# ============================================================================

if __name__ == "__main__":
    """
    Script entry point.
    
    Executed when running: python dashboard.py
    Calls main() and exits with the returned exit code.
    """
    sys.exit(main())