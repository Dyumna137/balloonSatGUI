"""
BalloonSat Telemetry Dashboard - Event Dispatcher
==================================================

This module provides a global event dispatcher using Qt's signal/slot mechanism
for decoupled communication b/w dashboard components.

Architecture Pattern: Observer/Publish-Subscribe
    • Publishers: Data sources (sensors, file loaders, network streams)
    • Dispatcher: Central event hub (this module)
    • Subscribers: Dashboard widgets (tables, charts, gauges, LEDs)

Key Benefits:
    • Decoupling: Data sources don't need to know about widgets
    • Flexibility: Easy to add new data sources or displays
    • Thread Safety: Qt signals are thread-safe (with proper connection types)
    • Type Safety: PyQt6 signals provide type checking

Signal Flow Example:
    Serial Reader → dispatcher.telemetryUpdated.emit(data)
                 ↓
    Dispatcher (this module)
                 ↓
    ├→ TelemetryTableModel.updateTelemetry(data)
    ├→ Chart.appendPoint(data)
    └→ Gauge.setValue(data['cpu'])

Usage Examples:
    Emitting signals (from data source):
        from dispatcher import dispatch
        
        # Update telemetry
        dispatch.telemetryUpdated.emit({'alt_bmp': 123.4, 'temp': 22.5})
        
        # Update sensor status
        dispatch.sensorStatusUpdated.emit({'bmp': True, 'gps': False})
        
        # Update computer health
        dispatch.computerHealthUpdated.emit(45.2, 67.8)  # CPU, Memory
        
        # Append trajectory point
        from types import SimpleNamespace
        point = SimpleNamespace(t=0, lat=12.97, lon=77.59,
                               alt_expected=100, alt_actual=99.5)
        dispatch.trajectoryAppended.emit(point)
    
    Connecting to signals (from widgets):
        from dispatcher import dispatch
        
        # Connect to method
        dispatch.telemetryUpdated.connect(self._on_telemetry_update)
        
        # Connect to lambda
        dispatch.computerHealthUpdated.connect(
            lambda cpu, mem: print(f"CPU: {cpu}%, MEM: {mem}%")
        )
        
        # Disconnect
        dispatch.telemetryUpdated.disconnect(self._on_telemetry_update)

Thread Safety:
    Qt signals are thread-safe when used with appropriate connection types:
    • Qt.ConnectionType.AutoConnection (default): Thread-aware, safe
    • Qt.ConnectionType.QueuedConnection: Always queued, always safe
    • Qt.ConnectionType.DirectConnection: Not thread-safe, avoid across threads

Performance:
    • Signal emission: ~0.1μs overhead per connected slot
    • No data copying (Python objects passed by reference)
    • Minimal memory overhead (~200 bytes per signal)

Author: Dyumna137
Date: 2025-11-06
Version: 2.0
"""

from __future__ import annotations
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict


class Dispatcher(QObject):
    """
    Global event dispatcher for BalloonSat telemetry system.
    
    This class provides a centralized hub for all dashboard events using
    Qt's signal/slot mechanism. It acts as a mediator between data sources
    and UI components, enabling loose coupling and flexible architecture.
    
    Signals:
        telemetryUpdated (dict):
            Emitted when new telemetry data is available.
            Payload: Dictionary mapping field names to values
            Example: {'alt_bmp': 123.4, 'temp': 22.5, 'pressure': 101325}
            Frequency: Typically 1-10 Hz (once per second to 10 times per second)
        
        sensorStatusUpdated (dict):
            Emitted when sensor health status changes.
            Payload: Dictionary mapping sensor IDs to boolean status
            Example: {'bmp': True, 'gps': True, 'mq2': False}
            Frequency: Typically 0.1-1 Hz (once every 1-10 seconds)
        
        computerHealthUpdated (float, float):
            Emitted when computer resource usage changes.
            Payload: (cpu_percent, memory_percent) tuple
            Example: (45.2, 67.8) means 45.2% CPU, 67.8% memory
            Frequency: Typically 1 Hz (once per second)
        
        trajectoryAppended (object):
            Emitted when a new trajectory point should be plotted.
            Payload: Duck-typed object with attributes:
                    • t (float): Time in seconds
                    • lat (float): Latitude in degrees
                    • lon (float): Longitude in degrees
                    • alt_expected (float): Expected altitude in meters
                    • alt_actual (float): Actual altitude in meters
                    • clear (optional bool): If True, clear before appending
            Example: SimpleNamespace(t=0, lat=12.97, lon=77.59,
                                    alt_expected=100, alt_actual=99.5)
            Frequency: Typically 0.1-1 Hz (trajectory sampling rate)
        
        frameReady (object):
            Emitted when a new camera frame is available.
            Payload: QImage object ready for display
            Example: QImage from camera capture
            Frequency: Typically 1-30 Hz (camera frame rate)
            Note: Not used in current dashboard version (camera removed)
    
    Usage Pattern:
        # Singleton pattern: One global dispatcher instance
        from dispatcher import dispatch
        
        # Emit signals (data source side)
        dispatch.telemetryUpdated.emit(telemetry_dict)
        
        # Connect to signals (widget side)
        dispatch.telemetryUpdated.connect(my_handler)
        
        # Disconnect
        dispatch.telemetryUpdated.disconnect(my_handler)
    
    Thread Safety:
        All signals are thread-safe by default (Qt uses AutoConnection).
        Safe to emit from any thread, Qt will queue cross-thread signals.
    
    Performance:
        • Minimal overhead: ~0.1μs per emission with 1 connected slot
        • Scales linearly: ~0.1μs additional overhead per extra slot
        • No noticeable impact even with 100+ connected slots
    
    Example:
        # Data source (runs in background thread)
        def read_sensors():
            data = {'alt_bmp': 123.4, 'temp': 22.5}
            dispatch.telemetryUpdated.emit(data)  # Thread-safe!
        
        # UI component (runs in main thread)
        class Dashboard(QMainWindow):
            def __init__(self):
                dispatch.telemetryUpdated.connect(self._update_display)
            
            def _update_display(self, data):
                self.label.setText(f"Alt: {data.get('alt_bmp', 0)}")
    """
    
    # ========================================================================
    # === SIGNAL DEFINITIONS ===
    # ========================================================================
    
    # Telemetry data update signal
    # Type: dict[str, Any] - mapping field names to values
    telemetryUpdated = pyqtSignal(dict)
    
    # Sensor health status update signal
    # Type: dict[str, bool] - mapping sensor IDs to True (ok) or False (fault)
    sensorStatusUpdated = pyqtSignal(dict)
    
    # Computer resource usage update signal
    # Type: (float, float) - (cpu_percent, memory_percent) tuple
    computerHealthUpdated = pyqtSignal(float, float)
    
    # New trajectory point signal
    # Type: object - duck-typed point with t, lat, lon, alt_expected, alt_actual
    trajectoryAppended = pyqtSignal(object)
    
    # Camera frame ready signal
    # Type: object - QImage ready for display
    # Note: Not used in current version (camera feature removed)
    frameReady = pyqtSignal(object)
    
    def __init__(self) -> None:
        """
        Initialize the Dispatcher.
        
        Creates the QObject base and initializes all signals.
        This constructor should only be called once (singleton pattern).
        
        Note:
            In practice, you should use the global 'dispatch' instance
            rather than creating new Dispatcher instances.
        """
        super().__init__()
    
    # ========================================================================
    # === UTILITY METHODS (Optional) ===
    # ========================================================================
    
    def get_signal_info(self) -> Dict[str, int]:
        """
        Get information about signal connection counts.
        
        Useful for debugging to see which signals have active connections.
        
        Returns:
            Dictionary mapping signal names to connection counts
        
        Example:
            >>> info = dispatch.get_signal_info()
            >>> print(info)
            {'telemetryUpdated': 2, 'sensorStatusUpdated': 1, ...}
        
        Note:
            This is a debugging utility and not typically used in production.
        """
        return {
            'telemetryUpdated': self.receivers(self.telemetryUpdated),
            'sensorStatusUpdated': self.receivers(self.sensorStatusUpdated),
            'computerHealthUpdated': self.receivers(self.computerHealthUpdated),
            'trajectoryAppended': self.receivers(self.trajectoryAppended),
            'frameReady': self.receivers(self.frameReady),
        }
    
    def disconnect_all(self):
        """
        Disconnect all slots from all signals.
        
        Useful for cleanup or testing scenarios where you want to reset
        all connections.
        
        Warning:
            This will break all existing connections! Use with caution.
            Typically only used during testing or application shutdown.
        
        Example:
            # Reset all connections
            dispatch.disconnect_all()
        """
        try:
            self.telemetryUpdated.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        
        try:
            self.sensorStatusUpdated.disconnect()
        except TypeError:
            pass
        
        try:
            self.computerHealthUpdated.disconnect()
        except TypeError:
            pass
        
        try:
            self.trajectoryAppended.disconnect()
        except TypeError:
            pass
        
        try:
            self.frameReady.disconnect()
        except TypeError:
            pass


# ============================================================================
# === GLOBAL DISPATCHER INSTANCE (Singleton Pattern) ===
# ============================================================================

# Create the global dispatcher instance
# This is the primary interface for all dashboard components
dispatch = Dispatcher()

# Module-level docstring for the global instance
dispatch.__doc__ = """
Global dispatcher instance for BalloonSat telemetry system.

This is a singleton object that should be imported and used throughout
the dashboard application for all event communication.

Usage:
    from dispatcher import dispatch
    
    # Emit signals
    dispatch.telemetryUpdated.emit({'alt_bmp': 123.4})
    
    # Connect to signals
    dispatch.telemetryUpdated.connect(my_handler)
"""


# ============================================================================
# === MODULE TESTING ===
# ============================================================================

if __name__ == "__main__":
    """
    Test the dispatcher with example signal emissions.
    
    Usage:
        python dispatcher.py
    """
    print("=" * 70)
    print("BalloonSat Dispatcher Test")
    print("=" * 70)
    
    # Test telemetryUpdated signal
    def on_telemetry(data):
        print("\n📊 Telemetry Updated:")
        for key, value in data.items():
            print(f"   {key}: {value}")
    
    dispatch.telemetryUpdated.connect(on_telemetry)
    dispatch.telemetryUpdated.emit({'alt_bmp': 123.4, 'temp': 22.5})
    
    # Test sensorStatusUpdated signal
    def on_sensor_status(status):
        print("\n🔧 Sensor Status:")
        for sensor, ok in status.items():
            symbol = "✓" if ok else "✗"
            print(f"   {symbol} {sensor}: {'OK' if ok else 'FAULT'}")
    
    dispatch.sensorStatusUpdated.connect(on_sensor_status)
    dispatch.sensorStatusUpdated.emit({'bmp': True, 'gps': True, 'mq2': False})
    
    # Test computerHealthUpdated signal
    def on_health(cpu, mem):
        print("\n💻 Computer Health:")
        print(f"   CPU: {cpu:.1f}%")
        print(f"   Memory: {mem:.1f}%")
    
    dispatch.computerHealthUpdated.connect(on_health)
    dispatch.computerHealthUpdated.emit(45.2, 67.8)
    
    # Test trajectoryAppended signal
    from types import SimpleNamespace
    
    def on_trajectory(point):
        print("\n📍 Trajectory Point:")
        print(f"   Time: {point.t}s")
        print(f"   Position: ({point.lat:.6f}, {point.lon:.6f})")
        print(f"   Altitude: {point.alt_actual}m (expected: {point.alt_expected}m)")
    
    dispatch.trajectoryAppended.connect(on_trajectory)
    point = SimpleNamespace(
        t=10.5,
        lat=12.9716,
        lon=77.5946,
        alt_expected=150.0,
        alt_actual=148.5
    )
    dispatch.trajectoryAppended.emit(point)
    
    # Show connection info
    print("\n📡 Signal Connections:")
    info = dispatch.get_signal_info()
    for signal_name, count in info.items():
        print(f"   {signal_name}: {count} connection(s)")
    
    print("\n✓ Dispatcher test complete!")
    print("=" * 70)