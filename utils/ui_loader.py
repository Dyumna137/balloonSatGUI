"""
UI Loading Utilities for BalloonSat Telemetry Dashboard
========================================================

This module provides robust utilities for loading Qt Designer .ui files
and QSS stylesheets with intelligent path resolution that works across
different execution contexts (script, module, packaged application).

Key Features:
    • Multi-path search for .ui and .qss files
    • Works with both script execution and package imports
    • Comprehensive error messages with search path reporting
    • UTF-8 encoding support for international characters
    • Verbose logging for debugging

Functions:
    load_ui_file(window, ui_filename, search_paths) -> Path
        Load a Qt Designer .ui file into a QMainWindow with smart path resolution.
    
    load_stylesheet(qss_filename, subdirectory, search_paths) -> Optional[str]
        Load a Qt stylesheet (.qss) file with smart path resolution.

Example Usage:
    >>> from utils.ui_loader import load_ui_file, load_stylesheet
    >>> from PyQt6.QtWidgets import QMainWindow, QApplication
    >>> 
    >>> app = QApplication([])
    >>> window = QMainWindow()
    >>> 
    >>> # Load UI file
    >>> ui_path = load_ui_file(window, "dashboard.ui")
    >>> print(f"Loaded from: {ui_path}")
    >>> 
    >>> # Load stylesheet
    >>> qss_content = load_stylesheet("dark.qss", "styles")
    >>> if qss_content:
    >>>     app.setStyleSheet(qss_content)

Author: Dyumna137
Date: 2025-11-06
Version: 2.0
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, List
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow


def load_ui_file(
    window: QMainWindow,
    ui_filename: str = "dashboard.ui",
    search_paths: Optional[List[Path]] = None
) -> Path:
    """
    Load a Qt Designer .ui file into a QMainWindow with intelligent path resolution.
    
    This function searches multiple common locations for the .ui file to support
    different execution contexts:
    1. Current working directory (when run as script: python main_dashboard.py)
    2. Package root directory (when imported as module)
    3. Package-qualified path (when installed as package)
    
    The function uses PyQt6's uic.loadUi() to dynamically load the UI definition
    and create all widgets, layouts, and connections defined in Qt Designer.
    
    Args:
        window: The QMainWindow instance to load the UI into. The window's
               centralWidget and all child widgets will be created based on
               the .ui file definition.
               
        ui_filename: Name of the .ui file to load (default: "dashboard.ui").
                    Should be just the filename, not a full path.
                    
        search_paths: Optional custom list of Path objects to search.
                     If None, uses default search paths based on common
                     Python project structures.
    
    Returns:
        Path: The absolute path where the .ui file was successfully found.
              This can be useful for logging or debugging path issues.
    
    Raises:
        FileNotFoundError: If the .ui file cannot be found in any of the
                          search paths. The error message includes a list
                          of all paths that were searched.
    
    Example:
        Basic usage with default paths:
        >>> from PyQt6.QtWidgets import QMainWindow
        >>> window = QMainWindow()
        >>> ui_path = load_ui_file(window, "dashboard.ui")
        >>> window.setWindowTitle("My Dashboard")
        >>> window.show()
        
        Custom search paths:
        >>> from pathlib import Path
        >>> custom_paths = [
        ...     Path("/opt/myapp/ui/dashboard.ui"),
        ...     Path.home() / ".config/myapp/dashboard.ui"
        ... ]
        >>> ui_path = load_ui_file(window, "dashboard.ui", custom_paths)
    
    Notes:
        • The window object is modified in-place by uic.loadUi()
        • All widgets defined in the .ui file become accessible via findChild()
        • Promoted custom widgets must be imported before calling this function
        • Signal/slot connections defined in Qt Designer are automatically connected
        
    Technical Details:
        The function uses PyQt6.uic.loadUi() which:
        1. Parses the XML structure of the .ui file
        2. Creates all widget instances
        3. Sets properties (size, text, style, etc.)
        4. Builds the layout hierarchy
        5. Connects signals/slots defined in Designer
        6. Sets the central widget and any dock widgets
    
    See Also:
        load_stylesheet(): For loading QSS stylesheet files
        PyQt6.uic.loadUi(): The underlying Qt function used
    """
    # === STEP 1: Determine search paths ===
    # If custom search paths not provided, use intelligent defaults
    if search_paths is None:
        search_paths = [
            # Path 1: Current working directory
            # Works when running as: python main_dashboard.py
            Path.cwd() / ui_filename,
            
            # Path 2: Directory containing this file (package root)
            # Works when running as: python -m dashboardGUI.main_dashboard
            # __file__ is this module's path, .parent.parent goes up to package root
            Path(__file__).parent.parent / ui_filename,
            
            # Path 3: Package-qualified path
            # Works when installed as package: pip install dashboardGUI
            Path("dashboardGUI") / ui_filename,
        ]
    
    # === STEP 2: Search for the .ui file ===
    ui_path = None
    for path in search_paths:
        if path.exists():
            ui_path = path
            break
    
    # === STEP 3: Handle file not found ===
    if ui_path is None:
        # Build detailed error message showing all searched locations
        error_msg = f"Could not find '{ui_filename}'. Searched in:\n"
        error_msg += "\n".join(f"  • {p.absolute()}" for p in search_paths)
        error_msg += "\n\nPlease ensure the .ui file exists in one of these locations."
        raise FileNotFoundError(error_msg)
    
    # === STEP 4: Load the UI file ===
    print(f"✓ Loading UI from: {ui_path.absolute()}")
    
    # Convert Path to string for uic.loadUi() compatibility
    # loadUi() modifies 'window' in-place, adding all widgets as attributes
    uic.loadUi(str(ui_path), window)
    
    # Return the path for logging/debugging purposes
    return ui_path


def load_stylesheet(
    qss_filename: str = "light.qss",
    subdirectory: str = "styles",
    search_paths: Optional[List[Path]] = None
) -> Optional[str]:
    """
    Load a Qt stylesheet (.qss) file with intelligent path resolution.
    
    Qt stylesheets use CSS-like syntax to style Qt widgets. This function
    searches multiple common locations for the stylesheet file and returns
    its contents as a string ready to apply with QApplication.setStyleSheet().
    
    The function is non-fatal: if the stylesheet is not found, it prints
    warnings but returns None, allowing the application to continue with
    default Qt styling.
    
    Args:
        qss_filename: Name of the .qss file to load (default: "dark.qss").
                     Should be just the filename without path.
                     
        subdirectory: Subdirectory containing the stylesheet (default: "styles").
                     Used to construct search paths like "styles/dark.qss".
                     
        search_paths: Optional custom list of Path objects to search.
                     If None, uses default search paths based on common
                     project structures with the subdirectory.
    
    Returns:
        str: The complete stylesheet content as a string, ready to pass to
             QApplication.setStyleSheet() or QWidget.setStyleSheet().
             
        None: If the stylesheet file cannot be found or cannot be read.
              Warnings are printed but no exception is raised.
    
    Example:
        Basic usage:
        >>> from PyQt6.QtWidgets import QApplication
        >>> app = QApplication([])
        >>> qss_content = load_stylesheet("dark.qss", "styles")
        >>> if qss_content:
        ...     app.setStyleSheet(qss_content)
        
        Custom theme directory:
        >>> qss = load_stylesheet("custom.qss", "themes")
        >>> if qss:
        ...     window.setStyleSheet(qss)
        
        Widget-specific styling:
        >>> button_style = load_stylesheet("button.qss", "styles")
        >>> if button_style:
        ...     my_button.setStyleSheet(button_style)
    
    Notes:
        • QSS syntax is similar to CSS but with Qt-specific selectors
        • Stylesheets can be applied at application level or widget level
        • File is read with UTF-8 encoding to support international comments
        • Returns None on error instead of raising exceptions (graceful degradation)
        
    QSS Syntax Reference:
        QWidget { background-color: #111; color: #ddd; }
        QPushButton:hover { background-color: #2d2d2d; }
        QGroupBox::title { color: #bbb; }
        
    Technical Details:
        The function:
        1. Searches multiple paths for the .qss file
        2. Opens file with UTF-8 encoding (supports unicode)
        3. Reads entire file into memory (safe for typical 10-100KB stylesheets)
        4. Returns string ready for setStyleSheet()
        5. Prints warnings but doesn't crash on errors
    
    See Also:
        load_ui_file(): For loading Qt Designer .ui files
        QApplication.setStyleSheet(): To apply stylesheet app-wide
        QWidget.setStyleSheet(): To apply stylesheet to specific widget
    """
    # === STEP 1: Determine search paths ===
    if search_paths is None:
        search_paths = [
            # Path 1: Current working directory + subdirectory
            # Example: ./styles/dark.qss
            Path.cwd() / subdirectory / qss_filename,
            
            # Path 2: Package root + subdirectory
            # Example: /path/to/dashboardGUI/styles/dark.qss
            Path(__file__).parent.parent / subdirectory / qss_filename,
            
            # Path 3: Package-qualified path + subdirectory
            # Example: dashboardGUI/styles/dark.qss
            Path("dashboardGUI") / subdirectory / qss_filename,
        ]
    
    # === STEP 2: Search for the stylesheet file ===
    qss_path = None
    for path in search_paths:
        if path.exists():
            qss_path = path
            break
    
    # === STEP 3: Handle file not found (non-fatal) ===
    if qss_path is None:
        print(f"⚠️  Warning: Could not find '{qss_filename}' in '{subdirectory}/' directory")
        print("    Dashboard will use default Qt styling.")
        print("    Searched in:")
        for p in search_paths:
            print(f"    • {p.absolute()}")
        return None
    
    # === STEP 4: Load and return stylesheet content ===
    try:
        # Open with UTF-8 encoding to support international characters in comments
        with open(qss_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"✓ Loaded stylesheet from: {qss_path.absolute()}")
        print(f"  ({len(content)} bytes, {content.count(chr(10))} lines)")
        
        return content
        
    except IOError as e:
        # Handle file read errors (permissions, disk errors, etc.)
        print(f"⚠️  Error reading stylesheet from {qss_path}: {e}")
        return None
        
    except UnicodeDecodeError as e:
        # Handle encoding errors (file not UTF-8)
        print(f"⚠️  Encoding error reading stylesheet from {qss_path}: {e}")
        print("    Hint: Ensure file is saved with UTF-8 encoding")
        return None


# ============================================================================
# === MODULE TESTING (Run directly to test functions) ===
# ============================================================================

if __name__ == "__main__":
    """
    Test the UI loader functions when module is run directly.
    
    Usage:
        python utils/ui_loader.py
    """
    print("Testing UI Loader Utilities")
    print("=" * 60)
    
    # Test stylesheet loading
    print("\n1. Testing stylesheet loading...")
    qss = load_stylesheet("dark.qss", "styles")
    if qss:
        print(f"   ✓ Loaded {len(qss)} characters")
        print(f"   First 100 chars: {qss[:100]}...")
    else:
        print("   ✗ Failed to load stylesheet")
    
    # Test UI loading would require QApplication and QMainWindow
    print("\n2. UI file loading requires QApplication (skipped in test mode)")
    print("   Use in application context to test load_ui_file()")
    
    print("\n" + "=" * 60)
    print("Testing complete")