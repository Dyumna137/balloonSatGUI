"""Simplified launcher that runs the existing dashboard in a minimal mode.

This module is intentionally non-invasive: it imports the existing
`BalloonSatDashboard` and applies a small set of runtime changes to
reduce UI complexity and CPU/GPU cost on embedded devices.

It does NOT modify the original source files; it simply configures
the created window instance before showing it.

Usage:
    python dashboard_simple.py
"""
from __future__ import annotations
import os
import sys
from PyQt6.QtWidgets import QApplication, QPushButton

# Conservative defaults for embedded devices
os.environ.setdefault("DASHBOARD_EMBEDDED", "1")
os.environ.setdefault("DASHBOARD_LIGHT_MODE", "1")
os.environ.setdefault("PYQTGRAPH_NO_OPENGL", "1")


def _import_dashboard():
    try:
        from dashboard import main as _main  # script import path
        from dashboard import BalloonSatDashboard as _Dashboard
        return _main, _Dashboard
    except Exception:
        from dashboardGUI.dashboard import main as _main
        from dashboardGUI.dashboard import BalloonSatDashboard as _Dashboard
        return _main, _Dashboard


def _apply_minimal_settings(window):
    """Apply conservative runtime changes to the dashboard window.

    - Hide/disable camera button (avoids loading live feed)
    - Reduce chart update frequency and buffer sizes
    - Disable per-point markers
    - Disable start/stop UI controls to avoid user confusion
    """
    # Hide camera/open-camera button if present
    try:
        for name in ('cameraButton', 'btn_camera', 'btn_esp32cam', 'openCameraButton'):
            b = window.findChild(QPushButton, name)
            if b:
                b.setVisible(False)
    except Exception:
        pass

    # Disable start/stop controls (GUI-only view)
    try:
        if getattr(window, 'btn_start', None):
            window.btn_start.setEnabled(False)
        if getattr(window, 'btn_stop', None):
            window.btn_stop.setEnabled(False)
    except Exception:
        pass

    # Tweak trajectory chart for low-power devices
    try:
        charts = getattr(window, 'trajectory_charts', None)
        if charts is not None:
            try:
                charts.setUpdateInterval(20)   # batch more points before repaint
            except Exception:
                pass
            try:
                charts.setMaxPoints(500)      # reduce rolling buffer
            except Exception:
                pass
            try:
                charts.setShowMarkers(False)  # avoid per-point draw cost
            except Exception:
                pass
    except Exception:
        pass


def main(argv=None):
    argv = argv or sys.argv

    # Create QApplication
    app = QApplication(argv)

    # Import dashboard classes
    _, Dashboard = _import_dashboard()

    # Create and configure window
    win = Dashboard()
    _apply_minimal_settings(win)
    win.resize(1200, 700)
    win.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
