"""
Manual demo for `TrajectoryCharts` moved from module testing.
Run this from the project root or add the project root to `PYTHONPATH`.

Usage:
    python -m tests.manual_charts_demo

This script demonstrates the TrajectoryCharts widget with simulated data.
"""
from types import SimpleNamespace
import math
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

# Import the widget from package
try:
    from widgets.charts import TrajectoryCharts
except Exception:
    # Support running from project root where package path may differ
    sys.path.insert(0, "..")
    from widgets.charts import TrajectoryCharts


def main():
    app = QApplication(sys.argv)

    charts = TrajectoryCharts()
    charts.setWindowTitle("TrajectoryCharts Test - Altitude Only")
    charts.resize(800, 600)
    charts.show()

    # Simulate trajectory data
    t = [0.0]

    def add_point():
        t[0] += 0.1

        point = SimpleNamespace(
            t=t[0],
            alt_expected=100 + t[0] * 2,  # Rising at 2 m/s
            alt_actual=100 + t[0] * 2 + math.sin(t[0]) * 5,  # With oscillation
        )
        charts.appendPoint(point)

    timer = QTimer()
    timer.timeout.connect(add_point)
    timer.start(100)  # Add point every 100ms

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
