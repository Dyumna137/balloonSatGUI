"""
Manual demo for `LinearGauge` moved from module testing.
Run this from the project root or add the project root to `PYTHONPATH`.

Usage:
    python -m tests.manual_gauge_demo
"""
import sys
import random
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout

try:
    from widgets.gauge import LinearGauge
except Exception:
    # fallback when running from tests folder
    import sys as _sys
    _sys.path.insert(0, "..")
    from widgets.gauge import LinearGauge


def main():
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("LinearGauge Test")
    window.setStyleSheet("QWidget { background-color: #111; }")
    layout = QVBoxLayout(window)

    # Create test gauges
    cpu_gauge = LinearGauge(label="CPU %")
    mem_gauge = LinearGauge(label="Memory %")
    disk_gauge = LinearGauge(label="Disk %")

    layout.addWidget(cpu_gauge)
    layout.addWidget(mem_gauge)
    layout.addWidget(disk_gauge)

    # Animate gauges
    def update_gauges():
        cpu_gauge.setValue(random.uniform(0, 100))
        mem_gauge.setValue(random.uniform(0, 100))
        disk_gauge.setValue(random.uniform(0, 100))

    timer = QTimer()
    timer.timeout.connect(update_gauges)
    timer.start(500)  # Update every 500ms

    window.resize(400, 300)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
