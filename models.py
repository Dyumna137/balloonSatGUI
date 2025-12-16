"""
BalloonSat Telemetry Dashboard - Data Models
=============================================

This module provides Qt data models for displaying telemetry data in table views.
It implements the Model-View architecture pattern used throughout PyQt6 applications.

Key Classes:
    TelemetryTableModel: QAbstractTableModel for telemetry data display
                        Handles data storage, formatting, and table updates

Architecture:
    The Model-View pattern separates data (model) from presentation (view):
    • Model: Stores and formats data (TelemetryTableModel)
    • View: Displays data (QTableView/QTableWidget)
    • When model changes, all connected views auto-update

Performance Optimizations:
    • Uses dict for O(1) data access by field key
    • Minimal dataChanged signals (only for changed rows)
    • Lazy formatting (only format visible cells during paint)
    • No unnecessary data copies

Usage Examples:
    Basic usage:
        model = TelemetryTableModel()
        table_view.setModel(model)
        
        # Update data
        model.updateTelemetry({'alt_bmp': 123.4, 'temp': 22.5})
    
    Multiple views (synchronized):
        model = TelemetryTableModel()
        table1.setModel(model)
        table2.setModel(model)  # Both tables show same data
        
        model.updateTelemetry({'alt_bmp': 456.7})  # Both update

Data Flow:
    1. Raw data arrives as dict from data source
    2. Dispatcher emits telemetryUpdated signal
    3. Signal connected to model.updateTelemetry()
    4. Model updates internal storage
    5. Model emits dataChanged signal
    6. All connected views repaint affected cells

Author: Dyumna137
Date: 2025-11-06
Version: 2.0
"""

from __future__ import annotations
from typing import Any, Dict
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex

# ============================================================================
# === IMPORTS: Metadata ===
# ============================================================================

# Import with fallback for different execution contexts
try:
    # When running from inside the package folder
    from metadata import TELEMETRY_FIELDS, TelemetryField
except ImportError:
    try:
        # When running as a package
        from dashboardGUI.metadata import TELEMETRY_FIELDS, TelemetryField
    except ImportError:
        # Relative import as last resort
        from .metadata import TELEMETRY_FIELDS, TelemetryField


class TelemetryTableModel(QAbstractTableModel):
    """
    Qt data model for displaying telemetry data in table views.
    
    This model implements QAbstractTableModel to provide telemetry data
    to Qt table views (QTableView, QTableWidget). It handles data storage,
    formatting, and automatic view updates when data changes.
    
    Table Structure:
        Column 0: Parameter name (from TelemetryField.label)
        Column 1: Formatted value (from TelemetryField.fmt + unit)
    
    Data Storage:
        Internal dict mapping source_key → raw value
        Values formatted on-demand during display
    
    Features:
        • Two-column display (Parameter, Value)
        • Automatic formatting using metadata
        • Efficient updates (only changed rows)
        • Support for multiple simultaneous views
        • Special handling for tuple data (GPS coordinates)
        • Transform function support (unit conversions)
    
    Attributes:
        _values (Dict[str, Any]): Internal storage mapping source_key to value
    
    Signals (inherited from QAbstractTableModel):
        dataChanged: Emitted when data changes (Qt handles view updates)
        layoutChanged: Emitted when structure changes (not used here)
    
    Performance:
        • O(1) value storage and retrieval (dict-based)
        • O(1) row count (constant, equals len(TELEMETRY_FIELDS))
        • O(1) column count (constant, always 2)
        • O(k) update time where k = number of changed fields
    
    Example:
        >>> model = TelemetryTableModel()
        >>> table = QTableView()
        >>> table.setModel(model)
        >>> 
        >>> # Update with new data
        >>> model.updateTelemetry({
        ...     'alt_bmp': 123.4,
        ...     'temp': 22.5,
        ...     'pressure': 101325
        ... })
        >>> 
        >>> # All views with this model automatically update
    """
    
    def __init__(self, fields: list[TelemetryField] | None = None):
        """
        Initialize TelemetryTableModel.
        
        Sets up empty data storage and initializes the base QAbstractTableModel.
        No data is stored initially; values appear as empty strings until first update.
        """
        super().__init__()
        
        # Fields displayed by this model (defaults to global TELEMETRY_FIELDS)
        self._fields: list[TelemetryField] = fields if fields is not None else TELEMETRY_FIELDS

        # Internal data storage: source_key → raw value
        # Using dict for O(1) lookup performance
        self._values: Dict[str, Any] = {}
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """
        Return number of rows in the table.
        
        Args:
            parent: Parent model index (unused for table models)
        
        Returns:
            Number of telemetry fields (rows in table)
        
        Notes:
            • Called frequently by Qt during rendering
            • Must be fast (O(1) operation)
            • Row count is constant (equals len(TELEMETRY_FIELDS))
        """
        return len(self._fields)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """
        Return number of columns in the table.
        
        Args:
            parent: Parent model index (unused for table models)
        
        Returns:
            Always 2 (Parameter column and Value column)
        
        Notes:
            • Called frequently by Qt during rendering
            • Must be fast (O(1) operation)
            • Column count is constant (always 2)
        """
        return 2  # Parameter, Value
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """
        Return data for a specific cell in the table.
        
        This is the core method that Qt calls to retrieve data for display.
        It's called for every visible cell during rendering, so performance
        is critical.
        
        Args:
            index: Model index identifying the cell (row, column)
            role: Data role (DisplayRole for text, DecorationRole for icons, etc.)
        
        Returns:
            Cell data (usually string) for DisplayRole, None for other roles
        
        Roles Handled:
            • DisplayRole: The main text to display in the cell
            • Other roles: Returns None (could add tooltips, colors, etc.)
        
        Performance:
            • O(1) for column 0 (parameter name from metadata)
            • O(1) for column 1 (value lookup from dict)
            • String formatting overhead minimal (cached by Qt)
        
        Example Data Flow:
            Qt rendering engine calls:
            data(index(0, 0), DisplayRole) → "Altitude (BMP)"
            data(index(0, 1), DisplayRole) → "123.4 m"
        """
        # === Validate index and role ===
        if not index.isValid():
            return None
        
        if role != Qt.ItemDataRole.DisplayRole:
            return None  # Only handle display role (text)
        
        # === Get field definition for this row ===
        field = self._fields[index.row()]
        
        # === Column 0: Parameter name ===
        if index.column() == 0:
            return field.label
        
        # === Column 1: Formatted value ===
        elif index.column() == 1:
            raw_value = self._resolve_field_value(field)
            return raw_value
        
        # Invalid column
        return None
    
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role=Qt.ItemDataRole.DisplayRole
    ):
        """
        Return header data for the table.
        
        Provides column headers (Parameter, Value) and optionally row headers
        (though vertical header is typically hidden in our UI).
        
        Args:
            section: Column number (for horizontal) or row number (for vertical)
            orientation: Horizontal (column headers) or Vertical (row headers)
            role: Data role (DisplayRole for text)
        
        Returns:
            Header text string for DisplayRole, None for other roles
        
        Column Headers:
            Column 0: "Parameter"
            Column 1: "Value"
        
        Example:
            Qt calls:
            headerData(0, Horizontal, DisplayRole) → "Parameter"
            headerData(1, Horizontal, DisplayRole) → "Value"
        """
        # Only handle display role for horizontal headers
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        
        # Return column header text
        return ["Parameter", "Value"][section]
    
    def updateTelemetry(self, data: Dict[str, Any]):
        """
        Update telemetry data and notify views of changes.
        
        This is the primary method for updating the model with new telemetry data.
        It efficiently updates only the changed values and emits dataChanged signals
        for only the affected rows, minimizing unnecessary view repaints.
        
        Args:
            data: Dictionary mapping source_key to new value
                 Keys should match TelemetryField.source_key
                 Example: {'alt_bmp': 123.4, 'temp': 22.5, 'pressure': 101325}
        
        Performance Optimizations:
            • Only stores values for fields we recognize (fast rejection)
            • Collects changed row numbers (no redundant signals)
            • Single dataChanged signal per contiguous range of rows
            • No unnecessary data copies
        
        Signal Emission:
            Emits dataChanged for each changed row, causing Qt to repaint
            only the affected cells in all connected views.
        
        Example:
            >>> model = TelemetryTableModel()
            >>> 
            >>> # First update (all rows marked as changed)
            >>> model.updateTelemetry({
            ...     'alt_bmp': 100.0,
            ...     'temp': 20.0
            ... })
            >>> 
            >>> # Second update (only changed rows updated)
            >>> model.updateTelemetry({
            ...     'alt_bmp': 101.0,  # Changed
            ...     'temp': 20.0        # Unchanged (but still stored)
            ... })
        
        Thread Safety:
            This method should be called from the main Qt thread.
            If calling from another thread, use Qt signals or QMetaObject.invokeMethod.
        """
        changed_rows = []

        # Update values and track changed rows
        for i, field in enumerate(self._fields):
            if field.source_key in data:
                self._values[field.source_key] = data[field.source_key]
                changed_rows.append(i)

        # Emit a single contiguous dataChanged range covering all changed rows
        if changed_rows:
            first = min(changed_rows)
            last = max(changed_rows)
            index_first = self.index(first, 1)
            index_last = self.index(last, 1)
            # Emit one signal for the whole range (simpler and still efficient)
            self.dataChanged.emit(index_first, index_last)
    
    def _resolve_field_value(self, field: TelemetryField) -> str:
        """
        Resolve and format a field value for display.
        
        This internal method handles:
        1. Retrieving raw value from storage
        2. Applying transform function if present
        3. Formatting value according to field format string
        4. Special handling for tuple data (GPS coordinates)
        5. Error handling for invalid data
        
        Args:
            field: TelemetryField definition with format specifications
        
        Returns:
            Formatted string ready for display
            Empty string if value not available
        
        Format Examples:
            Numeric: "{:.1f}" with unit "m" → "123.4 m"
            GPS: "{:.6f}, {:.6f}" → "12.971600, 77.594600"
            Text: "{}" with unit "" → "2025-11-06T12:00:00Z"
        
        Error Handling:
            • Missing value → empty string
            • Format error → fallback to str(value)
            • Transform error → use raw value
        
        Performance:
            • O(1) dict lookup
            • O(1) format operation (string interpolation)
            • Minimal overhead for happy path
        """
        # === Get raw value from storage ===
        value = self._values.get(field.source_key)
        
        # Return empty string if no value available
        if value is None:
            return ""
        
        # === Special handling for GPS lat/lon tuples ===
        if field.source_key == "gps_latlon" and isinstance(value, tuple):
            try:
                return field.fmt.format(value[0], value[1])
            except (IndexError, TypeError, ValueError):
                # Fallback if tuple format fails
                return str(value)
        
        # === Apply transform function if present ===
        if field.transform:
            try:
                value = field.transform(value)
            except Exception:
                # If transform fails, use raw value
                pass
        
        # === Format value using field format string ===
        try:
            # Check if format string includes unit
            if "{}" in field.fmt:
                # Simple format: "Value" (unit added separately if exists)
                formatted = field.fmt.format(value)
                if field.unit:
                    return f"{formatted} {field.unit}"
                return formatted
            else:
                # Complex format or value-only format
                formatted = field.fmt.format(value)
                if field.unit:
                    return f"{formatted} {field.unit}"
                return formatted
        except (ValueError, TypeError, KeyError):
            # If formatting fails, return string representation
            return str(value)


# ============================================================================
# === MODULE TESTING ===
# ============================================================================

if __name__ == "__main__":
    """
    Test TelemetryTableModel with sample data.
    
    Usage:
        python models.py
    """
    import sys
    from PyQt6.QtWidgets import QApplication, QTableView
    
    app = QApplication(sys.argv)
    
    # Create model
    model = TelemetryTableModel()
    
    # Create view
    table = QTableView()
    table.setModel(model)
    table.setWindowTitle("TelemetryTableModel Test")
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setVisible(False)
    table.resize(500, 600)
    
    # Add test data
    test_data = {
        'alt_bmp': 123.4,
        'alt_gps': 122.9,
        'alt_6m': 124.0,
        'pressure': 101325,
        'speed': 5.23,
        'temp': 22.5,
        'co': 0.003,
        'o3': 0.0001,
        'flammable': 0.02,
        'gps_latlon': (12.9716, 77.5946),
        'rtc_time': "2025-11-06T21:55:48Z",
        'cpu': 12.3
    }
    
    model.updateTelemetry(test_data)
    
    table.show()
    
    print("✓ TelemetryTableModel test running")
    print(f"  Rows: {model.rowCount()}")
    print(f"  Columns: {model.columnCount()}")
    print(f"  Data fields: {len(test_data)}")
    
    sys.exit(app.exec())