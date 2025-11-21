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

    # ======================================================================
    # === ALTITUDE & ATMOSPHERIC MEASUREMENT ===============================
    # Sensors: BMP280 (pressure+altitude), GPS
    # Purpose: Track balloon ascent/descent, detect burst, analyze atmosphere
    # ======================================================================

    TelemetryField(
        id="alt_bmp",
        label="Altitude (BMP280)",
        unit="m",
        fmt="{:.1f}",
        source_key="alt_bmp"
    ),
    # Barometric altitude from BMP280
    # Range: -500m to 9000m; accuracy: ±1m

    TelemetryField(
        id="pressure_bmp",
        label="Pressure (BMP280)",
        unit="Pa",
        fmt="{:.0f}",
        source_key="pressure_bmp"
    ),
    # Atmospheric pressure
    # Range: 30000–110000 Pa; used for altitude & weather modeling

    TelemetryField(
        id="alt_gps",
        label="Altitude (GPS)",
        unit="m",
        fmt="{:.1f}",
        source_key="alt_gps"
    ),
    # Satellite-derived altitude
    # Less accurate than barometric; used as absolute reference

    TelemetryField(
        id="alt_6m",
        label="Altitude (6-min Avg)",
        unit="m",
        fmt="{:.1f}",
        source_key="alt_6m"
    ),
    # Long-term smoothed altitude for trend analysis



    # ======================================================================
    # === ENVIRONMENTAL TEMPERATURES =======================================
    # Sensors: MAX6675, BMP280 internal temp, DHT22
    # Purpose: Study thermal environment & electronics temperature
    # ======================================================================

    TelemetryField(
        id="temp_tc",
        label="Temp (MAX6675)",
        unit="°C",
        fmt="{:.1f}",
        source_key="temp_tc"
    ),
    # MAX6675 K-type thermocouple
    # Range: 0°C to 1024°C
    # Useful for high-temp surfaces or insulated payload interior

    TelemetryField(
        id="temp_bmp",
        label="Temp (BMP280)",
        unit="°C",
        fmt="{:.2f}",
        source_key="temp_bmp"
    ),
    # BMP280 internal temperature (for compensation)
    # Also environmental temp but slower responding

    TelemetryField(
        id="temp_dht",
        label="Temp (DHT22)",
        unit="°C",
        fmt="{:.1f}",
        source_key="temp_dht"
    ),
    # DHT22 ambient temperature
    # Range: -40°C to 80°C; accuracy: ±0.5°C



    # ======================================================================
    # === GAS MEASUREMENTS ==================================================
    # Sensors: MQ-7, MQ-131, MQ-2
    # Purpose: Atmospheric chemistry research + safety detection
    # ======================================================================

    TelemetryField(
        id="co",
        label="CO (MQ-7)",
        unit="ppm",
        fmt="{:.3f}",
        source_key="co"
    ),
    # Carbon Monoxide sensor
    # Safety threshold: >50 ppm concerning, >200 ppm dangerous

    TelemetryField(
        id="o3",
        label="Ozone (MQ-131)",
        unit="ppm",
        fmt="{:.4f}",
        source_key="o3"
    ),
    # Ozone concentration
    # Range: 10 ppb–2 ppm; used for stratospheric ozone detection

    TelemetryField(
        id="flammable",
        label="Flammable Gas (MQ-2)",
        unit="ppm",
        fmt="{:.3f}",
        source_key="flammable"
    ),
    # Detects methane, propane, LPG, hydrogen
    # Useful for leak detection in experiments



    # ======================================================================
    # === MOTION & DYNAMICS =================================================
    # Sensors: MPU6050
    # Purpose: Detect rapid movement, turbulence, acceleration events
    # ======================================================================

    TelemetryField(
        id="speed",
        label="Speed (MPU6050)",
        unit="m/s",
        fmt="{:.2f}",
        source_key="speed"
    ),
    # Derived speed from accelerometer integration
    # Useful for motion event detection (not actual GPS speed)



    # ======================================================================
    # === POSITION ==========================================================
    # Sensors: GPS Module
    # Purpose: Absolute position and tracking
    # ======================================================================

    TelemetryField(
        id="gps",
        label="GPS (lat, lon)",
        unit="",
        fmt="{:.6f}, {:.6f}",
        source_key="gps_latlon"
    ),
    # GPS coordinates with 6-decimal precision
    # Accuracy ~0.1m ideal conditions



    # ======================================================================
    # === TIMEKEEPING =======================================================
    # Sensors: DS1302 RTC
    # Purpose: Accurate timestamping independent of CPU clock
    # ======================================================================

    TelemetryField(
        id="rtc",
        label="RTC Time (DS1302)",
        unit="",
        fmt="{}",
        source_key="rtc_time"
    ),
    # ISO 8601 timestamp "YYYY-MM-DDTHH:MM:SSZ"
    # Battery-backed time keeping



    # ======================================================================
    # === POWER SYSTEM (BMS) ===============================================
    # Sensors: Battery Management System (BMS)
    # Purpose: Monitor battery health during high-altitude cold exposure
    # ======================================================================

    TelemetryField(
        id="batt_voltage",
        label="Battery Voltage (BMS)",
        unit="V",
        fmt="{:.2f}",
        source_key="batt_voltage"
    ),
    # Battery voltage measurement
    # Determines health, charge level, and cold-weather drop

    TelemetryField(
        id="batt_current",
        label="Battery Current (BMS)",
        unit="A",
        fmt="{:.2f}",
        source_key="batt_current"
    ),
    # Current draw from BMS
    # Useful for monitoring sudden power spikes

    TelemetryField(
        id="batt_temp",
        label="Battery Temp (BMS)",
        unit="°C",
        fmt="{:.1f}",
        source_key="batt_temp"
    ),
    # Battery temperature
    # Helps detect freezing during high-altitude flight



    # ======================================================================
    # === COMMUNICATION / RADIO LINK (LORA) ================================
    # Sensors: SX127x LoRa Radio
    # Purpose: Verify link quality, detect dropouts, measure range
    # ======================================================================

    TelemetryField(
        id="lora_rssi",
        label="LoRa RSSI",
        unit="dBm",
        fmt="{:.0f}",
        source_key="lora_rssi"
    ),
    # Received Signal Strength Indicator
    # Typical range: -120 dBm (weak) to -30 dBm (strong)

    TelemetryField(
        id="lora_snr",
        label="LoRa SNR",
        unit="dB",
        fmt="{:.1f}",
        source_key="lora_snr"
    ),
    # Signal-to-noise ratio
    # Range: -20 dB (bad) to +10 dB (excellent)

    TelemetryField(
        id="lora_packets",
        label="LoRa Packet Count",
        unit="",
        fmt="{}",
        source_key="lora_packets"
    ),
    # Number of packets received by the ground station
    # Helps detect link interruptions



    # ======================================================================
    # === SYSTEM HEALTH ====================================================
    # Sensors: ESP32 internal metrics
    # Purpose: Monitor CPU load and software performance
    # ======================================================================

    TelemetryField(
        id="cpu",
        label="CPU Load",
        unit="%",
        fmt="{:.1f}",
        source_key="cpu"
    ),
    # CPU usage in %
    # Ensures onboard computer is not overloaded
]


# ============================================================================
# === SENSOR CONFIGURATION ===
# ============================================================================

SENSORS: list[SensorDef] = [

    # ======================================================================
    # === PRIMARY FLIGHT SENSORS ===========================================
    # Purpose: Core navigation, altitude, and system control
    # ======================================================================

    SensorDef(id="bmp", label="BMP180"),
    # Barometric pressure + altitude sensor
    # Primary altitude source; I2C address: 0x76/0x77

    SensorDef(id="gps", label="GPS"),
    # GNSS receiver for position, velocity, and satellite time
    # Communicates using NMEA sentences over UART

    SensorDef(id="esp32", label="ESP32"),
    # Onboard microcontroller
    # Handles processing, telemetry, and system health monitoring



    # ======================================================================
    # === ENVIRONMENTAL TEMPERATURE SENSORS ================================
    # Purpose: Thermal environment analysis (inside & outside payload)
    # ======================================================================

    SensorDef(id="max6675", label="MAX6675"),
    # K-type thermocouple amplifier
    # High-range temperature measurement (0–1024°C)

    SensorDef(id="dht22", label="DHT22"),
    # Temperature + humidity sensor
    # Digital single-wire protocol



    # ======================================================================
    # === MOTION & DYNAMICS SENSORS =======================================
    # Purpose: Detect movement, turbulence, acceleration events
    # ======================================================================

    SensorDef(id="mpu", label="MPU6050"),
    # 6-axis IMU: accelerometer + gyroscope
    # I2C address: 0x68/0x69



    # ======================================================================
    # === GAS CHEMISTRY SENSORS ============================================
    # Purpose: Atmospheric research + safety monitoring
    # ======================================================================

    SensorDef(id="mq131", label="MQ131"),
    # Ozone sensor
    # Used for atmospheric chemistry studies; analog output

    SensorDef(id="mq2", label="MQ2"),
    # Flammable gas detector (LPG, methane, hydrogen)
    # Safety sensor; analog output

    SensorDef(id="mq7", label="MQ7"),
    # Carbon Monoxide (CO) detector
    # Useful for combustion byproducts; analog output



    # ======================================================================
    # === POWER SYSTEM (BMS) ===============================================
    # Purpose: Battery health, charging, and power stability
    # ======================================================================

    SensorDef(id="bms", label="Battery Management System"),
    # Monitors battery voltage, current, temperature
    # Prevents undervoltage or overcurrent damage



    # ======================================================================
    # === TIMING / CLOCK ===================================================
    # Purpose: Stable timestamps independent of CPU clock drift
    # ======================================================================

    SensorDef(id="rtc", label="RTC"),
    # DS1302 or similar real-time clock
    # SPI protocol; battery-backed time retention



    # ======================================================================
    # === COMMUNICATION / RADIO ===========================================
    # Purpose: Long-range telemetry using LoRa
    # ======================================================================

    SensorDef(id="lora", label="LoRa Radio"),
    # SX127x series long-range RF modem
    # Provides RSSI, SNR, and packet telemetry
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