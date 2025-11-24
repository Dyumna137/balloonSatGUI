"""
Manual demo for `StatusLED` moved from module testing.
Run this from the project root or add the project root to `PYTHONPATH`.

Usage:
    python -m tests.manual_status_led_demo
"""
import sys
from PyQt6.QtWidgets import QApplication

try:
    from widgets.status_led import StatusLED
except Exception:
    import sys as _sys
    _sys.path.insert(0, "..")
    from widgets.status_led import StatusLED


def main():
    app = QApplication(sys.argv)

    # Create a small demo window using StatusLEDs
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

    window = QWidget()
    window.setWindowTitle("StatusLED Test Suite v3.0")
    window.setStyleSheet("QWidget { background-color: #1a1a1a; }")
    layout = QVBoxLayout(window)

    # Simple states row
    layout.addWidget(QLabel("States: "))
    row = QHBoxLayout()
    for state in ['on','off','fault']:
        led = StatusLED(diameter=20)
        led.setState(state)
        row.addWidget(led)
    layout.addLayout(row)

    window.resize(300, 150)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
