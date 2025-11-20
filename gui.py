"""Single-file GUI launcher.

Run this from inside the `dashboardGUI` folder with:

    python gui.py

It starts the dashboard UI only and does not require any external data producer.
The GUI listens for events on the local `dispatch` object so you
can emit demo data from a separate REPL.
"""
from __future__ import annotations
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QTableView, QGridLayout, QLabel
)
from PyQt6.QtCore import Qt

# Local GUI modules (kept in this package).
# Try top-level imports first so `python gui.py` works when this file is the
# executed script. Fall back to package imports for `-m dashboardGUI`.
try:
    from metadata import SENSORS
    from models import TelemetryTableModel
    from dispatcher import dispatch
    from widgets.status_led import StatusLED
    from widgets.gauge import LinearGauge
    from widgets.charts import TrajectoryCharts
    from widgets.camera import CameraPreview
except Exception:
    from dashboardGUI.metadata import SENSORS
    from dashboardGUI.models import TelemetryTableModel
    from dashboardGUI.dispatcher import dispatch
    from dashboardGUI.widgets.status_led import StatusLED
    from dashboardGUI.widgets.gauge import LinearGauge
    from dashboardGUI.widgets.charts import TrajectoryCharts
    from dashboardGUI.widgets.camera import CameraPreview


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BalloonSat Telemetry Dashboard ")
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(6,6,6,6)
        root_layout.setSpacing(8)

        # Left: Telemetry
        self.telemetry_model = TelemetryTableModel()
        telemetry_box = QGroupBox("Telemetry")
        t_layout = QVBoxLayout(telemetry_box)
        t_table = QTableView()
        t_table.setModel(self.telemetry_model)
        t_table.horizontalHeader().setStretchLastSection(True)
        t_table.verticalHeader().setVisible(False)
        t_table.setAlternatingRowColors(True)
        t_table.setSelectionMode(QTableView.SelectionMode.NoSelection)
        t_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        t_layout.addWidget(t_table)
        root_layout.addWidget(telemetry_box, 2)

        # Middle column
        mid_col = QVBoxLayout()
        root_layout.addLayout(mid_col, 3)

        # Controls (start/stop intentionally disabled in GUI-only)
        controls = QGroupBox("Controls")
        c_layout = QHBoxLayout(controls)
        self.btn_start = QPushButton("Start Stream")
        self.btn_stop = QPushButton("Stop Stream")
        self.btn_clear = QPushButton("Clear Trajectory")
        c_layout.addWidget(self.btn_start)
        c_layout.addWidget(self.btn_stop)
        c_layout.addWidget(self.btn_clear)
        # Start/Stop are disabled by default; a demo watcher can enable them
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        mid_col.addWidget(controls)

        # Sensor Health
        sensor_box = QGroupBox("Sensors Health")
        s_layout = QGridLayout(sensor_box)
        self.sensor_leds: dict[str, StatusLED] = {}
        for i, s in enumerate(SENSORS):
            lbl = QLabel(s.label)
            led = StatusLED()
            self.sensor_leds[s.id] = led
            row = i // 5
            col = (i % 5) * 2
            s_layout.addWidget(lbl, row, col)
            s_layout.addWidget(led, row, col + 1)
        mid_col.addWidget(sensor_box)

        # Computer Health
        comp_box = QGroupBox("Computer Health")
        ch_layout = QHBoxLayout(comp_box)
        self.cpu_gauge = LinearGauge(label="CPU %")
        self.mem_gauge = LinearGauge(label="Mem %")
        ch_layout.addWidget(self.cpu_gauge)
        ch_layout.addWidget(self.mem_gauge)
        mid_col.addWidget(comp_box)

        # Latest Readings (reuse same model for simplicity)
        latest_box = QGroupBox("Latest Readings")
        l_layout = QVBoxLayout(latest_box)
        latest_table = QTableView()
        latest_table.setModel(self.telemetry_model)
        latest_table.horizontalHeader().setStretchLastSection(True)
        latest_table.verticalHeader().setVisible(False)
        latest_table.setSelectionMode(QTableView.SelectionMode.NoSelection)
        latest_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        l_layout.addWidget(latest_table)
        mid_col.addWidget(latest_box, 2)

        # Right column
        right_col = QVBoxLayout()
        root_layout.addLayout(right_col, 4)

        self.charts = TrajectoryCharts()
        traj_box = QGroupBox("Trajectory (Expected vs Actual)")
        tb_layout = QVBoxLayout(traj_box)
        tb_layout.addWidget(self.charts)
        right_col.addWidget(traj_box, 3)

        # Camera + snapshot
        cam_row = QHBoxLayout()
        cam_box = QGroupBox("ESP32-CAM Preview")
        cam_layout = QVBoxLayout(cam_box)
        self.camera = CameraPreview()
        cam_layout.addWidget(self.camera)
        cam_row.addWidget(cam_box, 2)

        snap_box = QGroupBox()
        snap_layout = QVBoxLayout(snap_box)
        self.btn_snapshot = QPushButton("Snapshot")
        snap_layout.addStretch(1)
        snap_layout.addWidget(self.btn_snapshot)
        snap_layout.addStretch(1)
        cam_row.addWidget(snap_box, 1)

        right_col.addLayout(cam_row, 2)

        # Connections: wire dispatcher to UI updates
        dispatch.telemetryUpdated.connect(self.telemetry_model.updateTelemetry)
        dispatch.sensorStatusUpdated.connect(self._update_sensors)
        dispatch.computerHealthUpdated.connect(self._update_computer_health)
        dispatch.trajectoryAppended.connect(self._append_trajectory)
        dispatch.frameReady.connect(self.camera.updateFrame)

        self.btn_clear.clicked.connect(self._clear_trajectory)
        self.btn_snapshot.clicked.connect(self._snapshot)

    def _update_sensors(self, status: dict):
        for k, led in self.sensor_leds.items():
            # General rule: only an explicit True means the sensor is OK.
            # Any other value (False, None, missing) is treated as a fault so
            # it's visible in the UI. This keeps the GUI obvious when sensors
            # stop reporting.
            val = status.get(k, None)
            try:
                if val is True:
                    led.setState('on')
                    led.setToolTip(f"{k}: OK")
                else:
                    # falsy or missing -> fault
                    led.setState('fault')
                    led.setToolTip(f"{k}: not working")
            except Exception:
                # best-effort fallback to boolean API
                led.setOn(bool(val))

    def _update_computer_health(self, cpu: float, mem: float):
        self.cpu_gauge.setValue(cpu)
        self.mem_gauge.setValue(mem)

    def _append_trajectory(self, p):
        # Support a `.clear` flag on the incoming point so emitters can
        # request that the current trajectory be cleared before plotting
        # a newly-written trajectory file.
        try:
            if getattr(p, "clear", False):
                self.charts.clear()
        except Exception:
            pass
        self.charts.appendPoint(p)

    def _clear_trajectory(self):
        self.charts.clear()

    def _snapshot(self):
        pix = self.camera.pixmap()
        if pix:
            pix.save("snapshot.png", "PNG")


def main(argv=None):
    argv = argv or sys.argv
    app = QApplication(argv)
    try:
        with open("styles/dark.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    win = DashboardWindow()
    win.resize(1500, 800)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
