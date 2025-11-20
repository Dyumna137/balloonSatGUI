"""
Widget Finder Utilities for BalloonSat Telemetry Dashboard
===========================================================

This module provides the WidgetFinder class, a powerful helper for locating
and organizing Qt widgets loaded from Qt Designer .ui files.

When you load a .ui file with uic.loadUi(), all widgets are created but
accessing them requires using findChild() repeatedly. WidgetFinder simplifies
this by:
    • Providing organized methods for finding groups of related widgets
    • Storing found widgets in categorized dictionaries
    • Offering safe finding with built-in error checking
    • Printing helpful warnings for missing widgets
    • Supporting custom/promoted widget types

Key Features:
    • Type-safe widget finding with proper type hints
    • Organized storage (buttons, tables, custom widgets, etc.)
    • Batch finding methods for multiple widgets at once
    • Silent mode for widgets that may not exist
    • Sensor LED mapping helper for BalloonSat-specific use
    • Summary reporting for debugging

Classes:
    WidgetFinder: Main helper class for finding and organizing widgets

Example Usage:
    >>> from PyQt6.QtWidgets import QMainWindow
    >>> from utils.widget_finder import WidgetFinder
    >>> 
    >>> # Load UI and create finder
    >>> window = QMainWindow()
    >>> load_ui_file(window, "dashboard.ui")
    >>> finder = WidgetFinder(window, verbose=True)
    >>> 
    >>> # Find multiple buttons at once
    >>> finder.find_buttons(['startButton', 'stopButton', 'clearButton'])
    >>> 
    >>> # Access found buttons
    >>> if finder.buttons['startButton']:
    ...     finder.buttons['startButton'].clicked.connect(on_start)
    >>> 
    >>> # Find custom promoted widgets
    >>> finder.find_custom_widgets({
    ...     'trajectoryChartsWidget': TrajectoryCharts,
    ...     'cpuGaugeWidget': LinearGauge
    ... })
    >>> 
    >>> # Print summary
    >>> print(finder.summary())

Author: Dyumna137
Date: 2025-11-06
Version: 2.0
"""

from __future__ import annotations
from typing import Optional, TypeVar, Type, Dict, List
from PyQt6.QtWidgets import QWidget, QGroupBox, QPushButton, QTableWidget, QLabel

# Type variable for generic widget finding
# Allows methods to return the correct widget type for IDE autocomplete
T = TypeVar('T', bound=QWidget)


class WidgetFinder:
    """
    Helper class to find and organize widgets from Qt Designer .ui files.
    
    This class provides a systematic way to locate widgets created by
    uic.loadUi() and organize them into categorized dictionaries for
    easy access throughout your application.
    
    The class uses Qt's findChild() method internally but adds:
        • Error checking and helpful warnings
        • Organized storage by widget type
        • Batch finding for multiple widgets
        • Type hints for IDE support
        • Special handling for custom/promoted widgets
    
    Attributes:
        parent: The parent QWidget to search within (usually QMainWindow)
        verbose: Whether to print warnings for missing widgets
        group_boxes: Dict mapping object names to found QGroupBox widgets
        buttons: Dict mapping object names to found QPushButton widgets
        tables: Dict mapping object names to found QTableWidget widgets
        labels: Dict mapping object names to found QLabel widgets
        custom_widgets: Dict mapping object names to found custom widgets
    
    Example:
        Basic usage:
        >>> finder = WidgetFinder(main_window)
        >>> finder.find_buttons(['okButton', 'cancelButton'])
        >>> ok_btn = finder.buttons['okButton']
        >>> ok_btn.clicked.connect(on_ok_clicked)
        
        Finding custom widgets:
        >>> from widgets.charts import TrajectoryCharts
        >>> finder.find_custom_widgets({
        ...     'chartWidget': TrajectoryCharts
        ... })
        >>> chart = finder.custom_widgets['chartWidget']
        >>> chart.appendPoint(point)
        
        Finding sensor indicators:
        >>> sensor_map = {'bmp': 'bmpIndicator', 'gps': 'gpsIndicator'}
        >>> leds = finder.find_sensor_indicators(StatusLED, sensor_map)
        >>> leds['bmp'].setState('on')
    
    Notes:
        • All find_*() methods store results in instance dictionaries
        • Widgets that aren't found are stored as None
        • verbose=True (default) prints warnings for missing widgets
        • Widget object names must match Qt Designer exactly (case-sensitive)
        
    Technical Details:
        The class uses QObject.findChild() which performs a recursive search
        through the widget hierarchy. For large UIs with many widgets, consider:
        1. Finding widgets once in __init__() and storing references
        2. Using silent=True for optional widgets
        3. Checking for None before using widgets
    """
    
    def __init__(self, parent: QWidget, verbose: bool = True):
        """
        Initialize the WidgetFinder with a parent widget to search within.
        
        Args:
            parent: Parent widget to search within (usually QMainWindow).
                   All findChild() calls will search this widget's hierarchy.
                   
            verbose: Whether to print warnings for missing widgets (default: True).
                    Set to False for cleaner output if you expect some widgets
                    to be missing (e.g., optional UI elements).
        
        Example:
            >>> from PyQt6.QtWidgets import QMainWindow
            >>> window = QMainWindow()
            >>> finder = WidgetFinder(window, verbose=True)
            >>> 
            >>> # Silent mode (no warnings)
            >>> finder_silent = WidgetFinder(window, verbose=False)
        
        Notes:
            • The parent is typically the QMainWindow instance after loadUi()
            • All storage dictionaries are initialized empty
            • No actual widget finding happens in __init__
        """
        self.parent = parent
        self.verbose = verbose
        
        # Initialize storage dictionaries for organized widget access
        # Each dictionary maps objectName (str) to widget instance (or None)
        self.group_boxes: Dict[str, Optional[QGroupBox]] = {}
        self.buttons: Dict[str, Optional[QPushButton]] = {}
        self.tables: Dict[str, Optional[QTableWidget]] = {}
        self.labels: Dict[str, Optional[QLabel]] = {}
        self.custom_widgets: Dict[str, Optional[QWidget]] = {}
    
    def find_widget(
        self,
        widget_class: Type[T],
        object_name: str,
        silent: bool = False
    ) -> Optional[T]:
        """
        Find a single widget by class and object name with error checking.
        
        This is the core widget finding method used by all other find_*()
        methods. It wraps Qt's findChild() with additional error checking
        and optional warning messages.
        
        Args:
            widget_class: The Qt widget class to search for (e.g., QPushButton).
                         Must be the exact class or a parent class of the widget.
                         
            object_name: The objectName property from Qt Designer.
                        This is case-sensitive and must match exactly.
                        
            silent: Don't print warning if widget not found (default: False).
                   Useful for optional widgets that may not exist in all
                   versions of your UI.
        
        Returns:
            The found widget instance with correct type, or None if not found.
            The return type matches widget_class for IDE autocomplete.
        
        Example:
            Basic usage:
            >>> button = finder.find_widget(QPushButton, 'startButton')
            >>> if button:
            ...     button.clicked.connect(on_start)
            
            Silent finding (no warning):
            >>> optional = finder.find_widget(QLabel, 'optionalLabel', silent=True)
            >>> if optional:
            ...     optional.setText("Found!")
            
            With type safety:
            >>> from typing import cast
            >>> button = cast(QPushButton, finder.find_widget(QPushButton, 'btn'))
            >>> button.click()  # IDE knows this is a QPushButton
        
        Technical Details:
            Uses QObject.findChild() which:
            1. Searches immediate children first
            2. Then recursively searches children's children
            3. Returns first match by objectName
            4. Returns None if no match found
            
            The search is case-sensitive and matches exact objectName only.
            Widget must be a descendant (not necessarily direct child).
        
        See Also:
            find_buttons(): For finding multiple buttons at once
            find_custom_widgets(): For finding promoted custom widgets
        """
        # Use Qt's findChild() to search the widget hierarchy
        # First argument: class type to find
        # Second argument: objectName to match
        widget = self.parent.findChild(widget_class, object_name)
        
        # Print warning if widget not found (unless silent mode)
        if widget is None and self.verbose and not silent:
            print(f"⚠️  Warning: Could not find {widget_class.__name__} "
                  f"with name '{object_name}'")
            print(f"    • Check objectName in Qt Designer matches exactly")
            print(f"    • Ensure widget is in the .ui file")
            print(f"    • For promoted widgets, ensure class is imported")
        
        return widget
    
    def find_group_boxes(self, names: List[str]) -> Dict[str, Optional[QGroupBox]]:
        """
        Find multiple QGroupBox widgets and store them in the group_boxes dict.
        
        QGroupBox widgets are typically used as visual containers with borders
        and titles. This method finds all specified group boxes at once.
        
        Args:
            names: List of objectName values to search for.
                  Each name should match a QGroupBox objectName in Qt Designer.
        
        Returns:
            Dictionary mapping object names to found QGroupBox widgets.
            Same as self.group_boxes (also stored in instance).
        
        Example:
            >>> finder.find_group_boxes([
            ...     'telemetryGroup',
            ...     'controlsGroup',
            ...     'sensorsHealthGroup'
            ... ])
            >>> 
            >>> # Access found group boxes
            >>> if finder.group_boxes['telemetryGroup']:
            ...     finder.group_boxes['telemetryGroup'].setTitle("Telemetry Data")
        
        Notes:
            • Results are stored in self.group_boxes dictionary
            • Missing group boxes will be stored as None
            • Warnings printed for missing widgets (unless verbose=False)
        """
        for name in names:
            self.group_boxes[name] = self.find_widget(QGroupBox, name)
        return self.group_boxes
    
    def find_buttons(self, names: List[str]) -> Dict[str, Optional[QPushButton]]:
        """
        Find multiple QPushButton widgets and store them in the buttons dict.
        
        Convenience method for finding all buttons in your UI at once,
        which is common during initialization.
        
        Args:
            names: List of objectName values to search for.
                  Each name should match a QPushButton objectName in Qt Designer.
        
        Returns:
            Dictionary mapping object names to found QPushButton widgets.
            Same as self.buttons (also stored in instance).
        
        Example:
            >>> finder.find_buttons(['startButton', 'stopButton', 'clearButton'])
            >>> 
            >>> # Connect button signals
            >>> if finder.buttons['startButton']:
            ...     finder.buttons['startButton'].clicked.connect(on_start)
            >>> if finder.buttons['stopButton']:
            ...     finder.buttons['stopButton'].clicked.connect(on_stop)
        
        Notes:
            • Results are stored in self.buttons dictionary
            • Missing buttons will be stored as None
            • Always check for None before connecting signals
        """
        for name in names:
            self.buttons[name] = self.find_widget(QPushButton, name)
        return self.buttons
    
    def find_tables(self, names: List[str]) -> Dict[str, Optional[QTableWidget]]:
        """
        Find multiple QTableWidget widgets and store them in the tables dict.
        
        QTableWidget is the item-based table widget. For model-based tables
        (QTableView), you may need to use find_widget() directly.
        
        Args:
            names: List of objectName values to search for.
                  Each name should match a QTableWidget objectName in Qt Designer.
        
        Returns:
            Dictionary mapping object names to found QTableWidget widgets.
            Same as self.tables (also stored in instance).
        
        Example:
            >>> finder.find_tables(['telemetryTable', 'latestReadingsTable'])
            >>> 
            >>> # Configure found tables
            >>> for table in finder.tables.values():
            ...     if table:
            ...         table.setAlternatingRowColors(True)
            ...         table.horizontalHeader().setStretchLastSection(True)
        
        Notes:
            • Results are stored in self.tables dictionary
            • Works with QTableWidget (item-based tables)
            • For QTableView (model-based), use find_widget() directly
        """
        for name in names:
            self.tables[name] = self.find_widget(QTableWidget, name)
        return self.tables
    
    def find_labels(self, names: List[str]) -> Dict[str, Optional[QLabel]]:
        """
        Find multiple QLabel widgets and store them in the labels dict.
        
        QLabel widgets are used for text display, images, and sometimes
        custom painted indicators (when promoted to custom classes).
        
        Args:
            names: List of objectName values to search for.
                  Each name should match a QLabel objectName in Qt Designer.
        
        Returns:
            Dictionary mapping object names to found QLabel widgets.
            Same as self.labels (also stored in instance).
        
        Example:
            >>> finder.find_labels(['statusLabel', 'titleLabel', 'valueLabel'])
            >>> 
            >>> # Update label text
            >>> if finder.labels['statusLabel']:
            ...     finder.labels['statusLabel'].setText("Ready")
        
        Notes:
            • Results are stored in self.labels dictionary
            • QLabel can be promoted to custom classes in Qt Designer
            • For promoted labels, consider using find_custom_widgets() instead
        """
        for name in names:
            self.labels[name] = self.find_widget(QLabel, name)
        return self.labels
    
    def find_custom_widgets(
        self,
        widget_map: Dict[str, Type[QWidget]]
    ) -> Dict[str, Optional[QWidget]]:
        """
        Find custom/promoted widgets with different classes.
        
        When you promote a widget in Qt Designer (e.g., promote QWidget to
        LinearGauge), you need to search for the custom class. This method
        handles finding multiple custom widgets with different classes.
        
        Args:
            widget_map: Dictionary mapping objectName to widget class.
                       Example: {
                           'cpuGaugeWidget': LinearGauge,
                           'trajectoryChartsWidget': TrajectoryCharts
                       }
        
        Returns:
            Dictionary mapping object names to found widget instances.
            Same as self.custom_widgets (also stored in instance).
        
        Example:
            >>> from widgets.charts import TrajectoryCharts
            >>> from widgets.gauge import LinearGauge
            >>> 
            >>> finder.find_custom_widgets({
            ...     'trajectoryChartsWidget': TrajectoryCharts,
            ...     'cpuGaugeWidget': LinearGauge,
            ...     'memGaugeWidget': LinearGauge,
            ... })
            >>> 
            >>> # Access custom widgets
            >>> charts = finder.custom_widgets['trajectoryChartsWidget']
            >>> if charts:
            ...     charts.appendPoint(point)
        
        Important:
            • Custom widget classes MUST be imported before loading .ui file
            • Promotion in Qt Designer must specify correct header file
            • Header file should be: module.class_file (e.g., widgets.charts)
            • NOT: module/class_file.py or class_file.py
        
        Troubleshooting:
            If custom widgets not found:
            1. Verify import before uic.loadUi()
            2. Check promotion header in Qt Designer
            3. Ensure class name matches exactly
            4. Try finding as base class (e.g., QWidget) to verify it exists
        """
        for name, widget_class in widget_map.items():
            self.custom_widgets[name] = self.find_widget(widget_class, name)
        return self.custom_widgets
    
    def find_sensor_indicators(
        self,
        led_class: Type[QWidget],
        sensor_map: Dict[str, str]
    ) -> Dict[str, Optional[QWidget]]:
        """
        Find sensor status LED indicators (BalloonSat-specific helper).
        
        This is a specialized method for the BalloonSat dashboard that maps
        sensor IDs from metadata.py to their corresponding StatusLED widgets
        in the UI. It provides helpful summary reporting for debugging.
        
        Args:
            led_class: The StatusLED class (or compatible promoted widget class).
                      Should be the class used in Qt Designer promotion.
                      
            sensor_map: Dictionary mapping sensor IDs to widget objectNames.
                       Example: {
                           'bmp': 'bmpIndicator',
                           'gps': 'gpsIndicator',
                           'mpu': 'mpu6050Indicator'
                       }
        
        Returns:
            Dictionary mapping sensor IDs to found LED widgets.
            NOTE: Unlike other methods, this returns sensor_id -> widget,
                  not objectName -> widget.
        
        Example:
            >>> from widgets.status_led import StatusLED
            >>> 
            >>> sensor_map = {
            ...     'bmp': 'bmpIndicator',
            ...     'esp32': 'esp32Indicator',
            ...     'gps': 'gpsIndicator',
            ... }
            >>> 
            >>> leds = finder.find_sensor_indicators(StatusLED, sensor_map)
            >>> # ✓ Found 3/3 sensor indicators
            >>> 
            >>> # Update sensor status
            >>> if leds['bmp']:
            ...     leds['bmp'].setState('on')
            >>> if leds['gps']:
            ...     leds['gps'].setState('fault')
        
        Notes:
            • Prints summary: "✓ Found X/Y sensor indicators"
            • Returns dict keyed by sensor ID, not widget objectName
            • Missing sensors get warning messages (if verbose=True)
            • Sensor IDs should match those in metadata.SENSORS
        
        See Also:
            metadata.py: For sensor definitions
            widgets.status_led.py: For StatusLED implementation
        """
        sensor_leds = {}
        
        # Find each sensor's LED widget
        for sensor_id, widget_name in sensor_map.items():
            led = self.find_widget(led_class, widget_name)
            
            if led:
                # Store using sensor ID as key (not widget name)
                sensor_leds[sensor_id] = led
            else:
                # Print warning for missing sensor LED
                if self.verbose:
                    print(f"⚠️  Warning: Could not find sensor LED for "
                          f"{sensor_id} (widget: {widget_name})")
        
        # Print helpful summary
        if self.verbose:
            found_count = len(sensor_leds)
            total_count = len(sensor_map)
            print(f"✓ Found {found_count}/{total_count} sensor indicators")
            
            # List any missing sensors
            if found_count < total_count:
                missing = set(sensor_map.keys()) - set(sensor_leds.keys())
                print(f"  Missing: {', '.join(missing)}")
        
        return sensor_leds
    
    def summary(self) -> str:
        """
        Generate a summary report of all found widgets.
        
        Useful for debugging widget finding issues or verifying that
        all expected widgets were found during initialization.
        
        Returns:
            Multi-line string with widget count summary by category.
        
        Example:
            >>> finder = WidgetFinder(window)
            >>> finder.find_buttons(['startButton', 'stopButton'])
            >>> finder.find_tables(['telemetryTable'])
            >>> print(finder.summary())
            Widget Finder Summary:
              • Group Boxes: 0
              • Buttons: 2
              • Tables: 1
              • Labels: 0
              • Custom Widgets: 0
        
        Notes:
            • Counts all widgets, including those that weren't found (None)
            • Call after all find_*() methods have been called
            • Useful in __init__() for debugging
        """
        lines = ["Widget Finder Summary:"]
        lines.append(f"  • Group Boxes: {len(self.group_boxes)}")
        lines.append(f"  • Buttons: {len(self.buttons)}")
        lines.append(f"  • Tables: {len(self.tables)}")
        lines.append(f"  • Labels: {len(self.labels)}")
        lines.append(f"  • Custom Widgets: {len(self.custom_widgets)}")
        
        # Count how many were actually found (not None)
        total_searched = (
            len(self.group_boxes) + len(self.buttons) + len(self.tables) +
            len(self.labels) + len(self.custom_widgets)
        )
        total_found = sum(1 for widgets in [
            self.group_boxes.values(),
            self.buttons.values(),
            self.tables.values(),
            self.labels.values(),
            self.custom_widgets.values()
        ] for widget in widgets if widget is not None)
        
        lines.append(f"  • Total Found: {total_found}/{total_searched}")
        
        return "\n".join(lines)


# ============================================================================
# === MODULE TESTING (Run directly to test) ===
# ============================================================================

if __name__ == "__main__":
    """
    Test the WidgetFinder class when module is run directly.
    
    Usage:
        python utils/widget_finder.py
    """
    print("Testing Widget Finder Utilities")
    print("=" * 60)
    
    print("\nWidgetFinder requires QApplication and loaded UI to test.")
    print("Run tests from main_dashboard.py or create integration tests.")
    
    print("\n" + "=" * 60)
    print("Testing complete")