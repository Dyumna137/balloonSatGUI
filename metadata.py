"""
BalloonSat Telemetry Dashboard - Metadata Definitions
======================================================

This module defines the metadata for telemetry fields and sensors used
throughout the BalloonSat telemetry system. It serves as the single source
of truth for sensor configurations and data field specifications.

Key Concepts:
    • TelemetryField: Defines how raw sensor data is displayed
    • SensorDef: Defines sensor identification and labeling
    • Immutable dataclasses ensure metadata integrity

Architecture:
    This module uses frozen dataclasses to define immutable metadata that
    can be safely shared across all dashboard components without risk of
    accidental modification.

Usage:
    Import telemetry fields:
        from metadata import TELEMETRY_FIELDS
        for field in TELEMETRY_FIELDS:
            print(f"{field.label}: {field.unit}")
    
    Import sensor definitions:
        from metadata import SENSORS
        for sensor in SENSORS:
            print(f"{sensor.id}: {sensor.label}")
    
    Access specific field:
        from metadata import TELEMETRY_FIELDS
        alt_field = next(f for f in TELEMETRY_FIELDS if f.id == 'alt_bmp')
        print(alt_field.fmt)  # "{:.1f}"

Data Flow:
    1. Raw sensor data arrives as dict from data source
    2. TelemetryTableModel uses TELEMETRY_FIELDS to format display
    3. Dashboard uses SENSORS to create status indicators
    4. Transform functions convert raw values if needed

Performance Notes:
    • All metadata is loaded once at import time
    • Frozen dataclasses prevent accidental mutations
    • List lookups are O(n) but lists are small (<20 items)
    • Consider dict mapping if lookup performance becomes critical

Author: Dyumna137
Date: 2025-11-06
Version: 2.0
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any, Optional


# ============================================================================
# === TELEMETRY FIELD DEFINITION ===
# ============================================================================

@dataclass(frozen=True)
class TelemetryField:
    """
    Defines how a telemetry data field is identified, formatted, and displayed.
    
    Each TelemetryField represents one row in the telemetry display table,
    specifying how raw sensor data should be formatted for human readability.
    
    The frozen=True parameter makes instances immutable, preventing accidental
    modification of metadata during runtime.
    
    Attributes:
        id (str): Unique identifier for this field
                 Used internally for lookups and references
                 Convention: lowercase with underscores
                 Example: "alt_bmp", "temp", "gps"
        
        label (str): Human-readable display label
                    Shown in the "Parameter" column of telemetry tables
                    Should be concise but descriptive
                    Example: "Altitude (BMP)", "Temperature (DHT22)"
        
        unit (str): Measurement unit for display
                   Shown after the value in the "Value" column
                   Use standard SI units where possible
                   Example: "m", "°C", "Pa", "ppm"
        
        fmt (str): Python format string for value display
                  Used with str.format() to format numeric values
                  Supports all Python format specifications
                  Example: "{:.1f}" for 1 decimal place
                          "{:.2f}" for 2 decimal places
                          "{:.6f}, {:.6f}" for lat/lon pairs
        
        source_key (str): Key name in the raw data dictionary
                         Used to extract value from incoming telemetry dict
                         May differ from 'id' if raw data uses different naming
                         Example: If raw data has {"altitude_bmp": 123.4},
                                 source_key would be "altitude_bmp"
        
        transform (Optional[Callable]): Optional data transformation function
                                       Applied to raw value before formatting
                                       Useful for unit conversions or calculations
                                       Example: lambda x: x * 3.28084  # m to ft
                                       Default: None (no transformation)
    
    Examples:
        Simple numeric field:
            TelemetryField(
                id="temp",
                label="Temperature (DHT22)",
                unit="°C",
                fmt="{:.1f}",
                source_key="temp"
            )
        
        GPS coordinate pair:
            TelemetryField(
                id="gps",
                label="GPS (lat,lon)",
                unit="",
                fmt="{:.6f}, {:.6f}",
                source_key="gps_latlon"
            )
        
        With transformation:
            TelemetryField(
                id="alt_ft",
                label="Altitude (feet)",
                unit="ft",
                fmt="{:.0f}",
                source_key="alt_bmp",
                transform=lambda m: m * 3.28084  # meters to feet
            )
    
    Notes:
        • Instances are immutable (frozen dataclass)
        • transform is optional (default: None)
        • Empty string unit is valid (e.g., for dimensionless quantities)
        • Format strings should match expected data type
    """
    
    id: str
    label: str
    unit: str
    fmt: str
    source_key: str
    transform: Optional[Callable[[Any], Any]] = None


# ============================================================================
# === SENSOR DEFINITION ===
# ============================================================================

@dataclass(frozen=True)
class SensorDef:
    """
    Defines a physical sensor's identification and display properties.
    
    Each SensorDef represents one sensor in the BalloonSat system and
    corresponds to one status LED indicator in the dashboard UI.
    
    The frozen=True parameter makes instances immutable, preventing accidental
    modification of sensor metadata during runtime.
    
    Attributes:
        id (str): Unique identifier for this sensor
                 Used to match sensor status updates to LED indicators
                 Must match keys in sensor status dictionaries
                 Convention: lowercase, short codes
                 Example: "bmp", "gps", "mpu", "esp32"
        
        label (str): Human-readable sensor label
                    Shown next to the status LED in the UI
                    Should be concise (fits in small space)
                    Example: "BMP", "GPS", "MPU6050", "ESP32"
    
    Examples:
        Basic sensor:
            SensorDef(
                id="bmp",
                label="BMP"
            )
        
        Longer descriptive name:
            SensorDef(
                id="mpu",
                label="MPU6050"
            )
    
    Notes:
        • Instances are immutable (frozen dataclass)
        • id is used for programmatic access
        • label is used for UI display
        • Keep labels short (3-8 characters ideal)
    """
    
    id: str
    label: str


# ============================================================================
# === TELEMETRY FIELDS CONFIGURATION ===
# ============================================================================

TELEMETRY_FIELDS: list[TelemetryField] = [
    # === ALTITUDE MEASUREMENTS ===
    # Three independent altitude sources for redundancy and comparison
    
    TelemetryField(
        id="alt_bmp",
        label="Altitude (BMP)",
        unit="m",
        fmt="{:.1f}",
        source_key="alt_bmp"
    ),
    # BMP280 barometric pressure sensor
    # Primary altitude measurement, very accurate
    # Range: -500m to 9000m, Accuracy: ±1m
    
    TelemetryField(
        id="alt_gps",
        label="Altitude (GPS)",
        unit="m",
        fmt="{:.1f}",
        source_key="alt_gps"
    ),
    # GPS module altitude (from satellites)
    # Less accurate than barometric but provides absolute reference
    # Range: 0m to 18000m, Accuracy: ±5-10m
    
    TelemetryField(
        id="alt_6m",
        label="Altitude (6M)",
        unit="m",
        fmt="{:.1f}",
        source_key="alt_6m"
    ),
    # Six-minute averaged altitude (smoothed)
    # Used for long-term trend analysis
    
    # === ATMOSPHERIC MEASUREMENTS ===
    
    TelemetryField(
        id="pressure_bmp",
        label="Pressure (BMP)",
        unit="Pa",
        fmt="{:.0f}",
        source_key="pressure"
    ),
    # Atmospheric pressure from BMP280
    # Used for altitude calculation and weather analysis
    # Range: 30000-110000 Pa, Resolution: 0.16 Pa
    
    # === MOTION MEASUREMENTS ===
    
    TelemetryField(
        id="speed",
        label="Speed (MPU6050)",
        unit="m/s",
        fmt="{:.2f}",
        source_key="speed"
    ),
    # Calculated from MPU6050 accelerometer
    # Derived speed (not GPS speed)
    # Useful for detecting rapid movements
    
    # === ENVIRONMENTAL MEASUREMENTS ===
    
    TelemetryField(
        id="temp",
        label="Temp (DHT22)",
        unit="°C",
        fmt="{:.1f}",
        source_key="temp"
    ),
    # DHT22 temperature sensor
    # Range: -40°C to 80°C, Accuracy: ±0.5°C
    
    # === GAS CONCENTRATION MEASUREMENTS ===
    
    TelemetryField(
        id="co",
        label="CO (MQ-7)",
        unit="ppm",
        fmt="{:.3f}",
        source_key="co"
    ),
    # MQ-7 Carbon Monoxide sensor
    # Range: 20-2000 ppm
    # Safety: >50 ppm is concerning, >200 ppm is dangerous
    
    TelemetryField(
        id="o3",
        label="Ozone (MQ-131)",
        unit="ppm",
        fmt="{:.4f}",
        source_key="o3"
    ),
    # MQ-131 Ozone sensor
    # Range: 10 ppb - 2 ppm
    # Atmospheric research sensor (stratospheric ozone detection)
    
    TelemetryField(
        id="flammable",
        label="Flammable (MQ-2)",
        unit="ppm",
        fmt="{:.3f}",
        source_key="flammable"
    ),
    # MQ-2 Flammable gas sensor
    # Detects LPG, methane, propane, hydrogen
    # Safety sensor for fuel leaks
    
    # === POSITION MEASUREMENT ===
    
    TelemetryField(
        id="gps",
        label="GPS (lat,lon)",
        unit="",
        fmt="{:.6f}, {:.6f}",
        source_key="gps_latlon"
    ),
    # GPS coordinates as (latitude, longitude) tuple
    # Format: 6 decimal places (~0.1m precision)
    # Expected data: tuple of (float, float)
    
    # === TIME MEASUREMENT ===
    
    TelemetryField(
        id="rtc",
        label="Real Time (DS1302)",
        unit="",
        fmt="{}",
        source_key="rtc_time"
    ),
    # DS1302 Real-Time Clock
    # Provides timestamp even if system clock drifts
    # Format: ISO 8601 string "YYYY-MM-DDTHH:MM:SSZ"
    
    # === COMPUTER HEALTH ===
    
    TelemetryField(
        id="cpu",
        label="Computer Health",
        unit="",
        fmt="CPU: {:.1f} %",
        source_key="cpu"
    ),
    # CPU usage of the onboard computer
    # Monitors system health and processing load
    # Range: 0-100%
]


# ============================================================================
# === SENSOR CONFIGURATION ===
# ============================================================================

SENSORS: list[SensorDef] = [
    # === PRIMARY SENSORS (Critical for flight) ===
    
    SensorDef(id="bmp", label="BMP"),
    # BMP280: Barometric Pressure/Altitude Sensor
    # Critical: Primary altitude measurement
    # I2C Address: 0x76 or 0x77
    
    SensorDef(id="esp32", label="ESP32"),
    # ESP32: Microcontroller with WiFi/Bluetooth
    # Critical: Main processor and communication hub
    # Monitors its own health status
    
    SensorDef(id="gps", label="GPS"),
    # GPS Module: Position and time reference
    # Critical: Position tracking and navigation
    # Protocol: NMEA over UART
    
    # === MOTION SENSORS ===
    
    SensorDef(id="mpu", label="MPU6050"),
    # MPU6050: 6-axis IMU (Accelerometer + Gyroscope)
    # Important: Motion and orientation tracking
    # I2C Address: 0x68 or 0x69
    
    # === GAS SENSORS ===
    
    SensorDef(id="mq131", label="MQ131"),
    # MQ131: Ozone (O3) sensor
    # Research: Atmospheric ozone detection
    # Analog output via ADC
    
    SensorDef(id="mq2", label="MQ2"),
    # MQ2: Flammable gas sensor (LPG, methane, propane)
    # Safety: Fuel leak detection
    # Analog output via ADC
    
    SensorDef(id="mq7", label="MQ7"),
    # MQ7: Carbon Monoxide (CO) sensor
    # Safety: CO leak detection
    # Analog output via ADC
    
    # === ENVIRONMENTAL SENSORS ===
    
    SensorDef(id="dht22", label="DHT22"),
    # DHT22: Temperature and Humidity sensor
    # Environmental: Cabin climate monitoring
    # Protocol: Single-wire digital
    
    # === TIMING ===
    
    SensorDef(id="rtc", label="RTC"),
    # DS1302: Real-Time Clock
    # Important: Accurate timestamping
    # Battery-backed to maintain time during power loss
    # Protocol: SPI
]


# ============================================================================
# === UTILITY FUNCTIONS ===
# ============================================================================

def get_telemetry_field_by_id(field_id: str) -> Optional[TelemetryField]:
    """
    Retrieve a TelemetryField by its ID.
    
    Args:
        field_id: The unique identifier of the field
    
    Returns:
        TelemetryField if found, None otherwise
    
    Example:
        >>> field = get_telemetry_field_by_id("alt_bmp")
        >>> if field:
        ...     print(f"{field.label}: {field.unit}")
        Altitude (BMP): m
    
    Performance:
        O(n) linear search (acceptable for small lists <20 items)
    """
    for field in TELEMETRY_FIELDS:
        if field.id == field_id:
            return field
    return None


def get_sensor_by_id(sensor_id: str) -> Optional[SensorDef]:
    """
    Retrieve a SensorDef by its ID.
    
    Args:
        sensor_id: The unique identifier of the sensor
    
    Returns:
        SensorDef if found, None otherwise
    
    Example:
        >>> sensor = get_sensor_by_id("bmp")
        >>> if sensor:
        ...     print(f"{sensor.id}: {sensor.label}")
        bmp: BMP
    
    Performance:
        O(n) linear search (acceptable for small lists <10 items)
    """
    for sensor in SENSORS:
        if sensor.id == sensor_id:
            return sensor
    return None


def get_telemetry_field_ids() -> list[str]:
    """
    Get list of all telemetry field IDs.
    
    Returns:
        List of field ID strings
    
    Example:
        >>> ids = get_telemetry_field_ids()
        >>> print(ids[:3])
        ['alt_bmp', 'alt_gps', 'alt_6m']
    
    Performance:
        O(n) list comprehension
    """
    return [field.id for field in TELEMETRY_FIELDS]


def get_sensor_ids() -> list[str]:
    """
    Get list of all sensor IDs.
    
    Returns:
        List of sensor ID strings
    
    Example:
        >>> ids = get_sensor_ids()
        >>> print(ids[:3])
        ['bmp', 'esp32', 'mq131']
    
    Performance:
        O(n) list comprehension
    """
    return [sensor.id for sensor in SENSORS]


# ============================================================================
# === MODULE VALIDATION (Run at import time) ===
# ============================================================================

def _validate_metadata():
    """
    Validate metadata for consistency and correctness.
    
    Checks:
        • No duplicate field IDs
        • No duplicate sensor IDs
        • All IDs are non-empty strings
        • All labels are non-empty strings
    
    Raises:
        ValueError: If validation fails
    
    Note:
        Called automatically at module import time to catch
        configuration errors early.
    """
    # Check for duplicate telemetry field IDs
    field_ids = [f.id for f in TELEMETRY_FIELDS]
    if len(field_ids) != len(set(field_ids)):
        duplicates = [fid for fid in field_ids if field_ids.count(fid) > 1]
        raise ValueError(f"Duplicate telemetry field IDs found: {set(duplicates)}")
    
    # Check for duplicate sensor IDs
    sensor_ids = [s.id for s in SENSORS]
    if len(sensor_ids) != len(set(sensor_ids)):
        duplicates = [sid for sid in sensor_ids if sensor_ids.count(sid) > 1]
        raise ValueError(f"Duplicate sensor IDs found: {set(duplicates)}")
    
    # Validate non-empty IDs and labels
    for field in TELEMETRY_FIELDS:
        if not field.id or not field.label:
            raise ValueError(f"TelemetryField has empty id or label: {field}")
    
    for sensor in SENSORS:
        if not sensor.id or not sensor.label:
            raise ValueError(f"SensorDef has empty id or label: {sensor}")


# Run validation at import time
_validate_metadata()


# ============================================================================
# === MODULE TESTING ===
# ============================================================================

if __name__ == "__main__":
    """
    Test metadata definitions.
    
    Usage:
        python metadata.py
    """
    print("=" * 70)
    print("BalloonSat Metadata Validation")
    print("=" * 70)
    
    # Print telemetry fields
    print(f"\n📊 Telemetry Fields ({len(TELEMETRY_FIELDS)}):")
    print("-" * 70)
    for field in TELEMETRY_FIELDS:
        print(f"  {field.id:15} | {field.label:25} | {field.unit:5} | {field.fmt}")
    
    # Print sensors
    print(f"\n🔧 Sensors ({len(SENSORS)}):")
    print("-" * 70)
    for sensor in SENSORS:
        print(f"  {sensor.id:10} | {sensor.label}")
    
    # Test utility functions
    print("\n🧪 Testing Utility Functions:")
    print("-" * 70)
    
    test_field = get_telemetry_field_by_id("alt_bmp")
    print(f"  get_telemetry_field_by_id('alt_bmp'): {test_field.label if test_field else 'Not found'}")
    
    test_sensor = get_sensor_by_id("bmp")
    print(f"  get_sensor_by_id('bmp'): {test_sensor.label if test_sensor else 'Not found'}")
    
    print(f"  get_telemetry_field_ids(): {get_telemetry_field_ids()[:3]}...")
    print(f"  get_sensor_ids(): {get_sensor_ids()[:3]}...")
    
    print("\n✓ All metadata validated successfully!")
    print("=" * 70)