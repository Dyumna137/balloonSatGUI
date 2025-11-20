"""
Add debug prints to find where it crashes
"""

from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QPushButton
from PyQt6.QtCore import Qt

print("✓ Step 1: Imports completed")

try:
    from utils.ui_loader import load_ui_file, load_stylesheet
    from utils.widget_finder import WidgetFinder
    print("✓ Step 2: Utils imported")
except Exception as e:
    print(f"❌ Utils import failed: {e}")
    exit(1)

try:
    from widgets.charts import TrajectoryCharts
    from widgets.gauge import LinearGauge
    from widgets.status_led import StatusLED
    print("✓ Step 3: Widgets imported")
except Exception as e:
    print(f"❌ Widgets import failed: {e}")
    exit(1)

try:
    from models import TelemetryTableModel
    from dispatcher import dispatch
    from metadata import SENSORS
    print("✓ Step 4: Models imported")
except Exception as e:
    print(f"❌ Models import failed: {e}")
    exit(1)

print("✓ Step 5: Starting class definition...")

class BalloonSatDashboard(QMainWindow):
    """Main dashboard window."""
    
    def __init__(self):
        print("  → __init__ called")
        super().__init__()
        print("  → super().__init__ done")
        
        try:
            load_ui_file(self, "dashboard.ui")
            print("  → UI loaded")
        except Exception as e:
            print(f"  ❌ UI load failed: {e}")
            raise
        
        self.setWindowTitle("🎈 BalloonSat Telemetry Dashboard")
        print("  → Window title set")
        
        try:
            self._find_all_widgets()
            print("  → Widgets found")
        except Exception as e:
            print(f"  ❌ Widget finding failed: {e}")
            raise
        
        try:
            self._setup_models()
            print("  → Models setup")
        except Exception as e:
            print(f"  ❌ Model setup failed: {e}")
            raise
        
        try:
            self._connect_signals()
            print("  → Signals connected")
        except Exception as e:
            print(f"  ❌ Signal connection failed: {e}")
            raise
        
        try:
            self._initialize_ui_state()
            print("  → UI initialized")
        except Exception as e:
            print(f"  ❌ UI initialization failed: {e}")
            raise
        
        print("✓ __init__ completed successfully")
    
    def _find_all_widgets(self):
        print("    → _find_all_widgets starting")
        finder = WidgetFinder(self, verbose=True)
        finder.find_group_boxes(['telemetryGroup', 'controlsGroup', 'sensorsHealthGroup', 
                                 'computerHealthGroup', 'latestReadingsGroup', 'trajectoryGroup'])
        finder.find_buttons(['startButton', 'stopButton', 'clearButton'])
        self.telemetry_table = finder.find_widget(QTableView, 'telemetryTable')
        self.latest_readings_table = finder.find_widget(QTableView, 'latestReadingsTable')
        finder.find_custom_widgets({
            'trajectoryChartsWidget': TrajectoryCharts,
            'cpuGaugeWidget': LinearGauge,
            'memGaugeWidget': LinearGauge,
        })
        sensor_map = {
            'bmp': 'bmpIndicator', 'esp32': 'esp32Indicator', 'mq131': 'mq131Indicator',
            'mpu': 'mpu6050Indicator', 'gps': 'gpsIndicator', 'mq2': 'mq2Indicator',
            'dht22': 'dht22Indicator', 'mq7': 'mq7Indicator', 'rtc': 'rtcIndicator',
        }
        self.sensor_leds = finder.find_sensor_indicators(StatusLED, sensor_map)
        self.btn_start = finder.buttons.get('startButton')
        self.btn_stop = finder.buttons.get('stopButton')
        self.btn_clear = finder.buttons.get('clearButton')
        self.trajectory_charts = finder.custom_widgets.get('trajectoryChartsWidget')
        self.cpu_gauge = finder.custom_widgets.get('cpuGaugeWidget')
        self.mem_gauge = finder.custom_widgets.get('memGaugeWidget')
        print("    → _find_all_widgets complete")
    
    def _setup_models(self):
        print("    → _setup_models starting")
        self.telemetry_model = TelemetryTableModel()
        if self.telemetry_table:
            self._configure_table(self.telemetry_table, self.telemetry_model)
        if self.latest_readings_table:
            self._configure_table(self.latest_readings_table, self.telemetry_model)
        print("    → _setup_models complete")
    
    def _configure_table(self, table, model):
        table.setModel(model)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QTableView.SelectionMode.NoSelection)
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    
    def _connect_signals(self):
        print("    → _connect_signals starting")
        dispatch.telemetryUpdated.connect(self.telemetry_model.updateTelemetry)
        dispatch.sensorStatusUpdated.connect(self._update_sensors)
        dispatch.computerHealthUpdated.connect(self._update_computer_health)
        dispatch.trajectoryAppended.connect(self._append_trajectory)
        
        if self.btn_start:
            self.btn_start.clicked.connect(self._on_start)
        if self.btn_stop:
            self.btn_stop.clicked.connect(self._on_stop)
        if self.btn_clear:
            self.btn_clear.clicked.connect(self._on_clear)
        
        # ESP32-CAM button
        camera_btn = None
        for btn_name in ['cameraButton', 'btn_camera', 'btn_esp32cam', 'openCameraButton']:
            camera_btn = self.findChild(QPushButton, btn_name)
            if camera_btn:
                camera_btn.clicked.connect(self._on_open_esp32cam)
                print(f"      ✓ Connected camera button: {btn_name}")
                break
        
        if not camera_btn:
            print("      ℹ️  No camera button found")
        
        print("    → _connect_signals complete")
    
    def _initialize_ui_state(self):
        print("    → _initialize_ui_state starting")
        if self.btn_start:
            self.btn_start.setEnabled(False)
        if self.btn_stop:
            self.btn_stop.setEnabled(False)
        if self.btn_clear:
            self.btn_clear.setEnabled(True)
        for sensor_id, led in self.sensor_leds.items():
            led.setState('off')
        if self.cpu_gauge:
            self.cpu_gauge.setLabel("CPU %")
        if self.mem_gauge:
            self.mem_gauge.setLabel("Mem %")
        print("    → _initialize_ui_state complete")
    
    def _update_sensors(self, status):
        for sensor_id, led in self.sensor_leds.items():
            val = status.get(sensor_id, None)
            led.setState('on' if val is True else 'fault')
    
    def _update_computer_health(self, cpu, mem):
        if self.cpu_gauge:
            self.cpu_gauge.setValue(cpu)
        if self.mem_gauge:
            self.mem_gauge.setValue(mem)
    
    def _append_trajectory(self, p):
        if not self.trajectory_charts:
            return
        if getattr(p, "clear", False):
            self.trajectory_charts.clear()
        self.trajectory_charts.appendPoint(p)
    
    def _on_start(self):
        print("Start clicked")
    
    def _on_stop(self):
        print("Stop clicked")
    
    def _on_clear(self):
        if self.trajectory_charts:
            self.trajectory_charts.clear()
    
    def _on_open_esp32cam(self):
        print("Opening ESP32-CAM window...")
        try:
            from esp32cam_window import ESP32CamWindow
        except ImportError:
            from dashboardGUI.esp32cam_window import ESP32CamWindow
        
        if ESP32CamWindow.is_open():
            print("  Window already open")
            existing = ESP32CamWindow.get_instance()
            if existing:
                existing.activateWindow()
            return
        
        camera_window = ESP32CamWindow(parent=self)
        camera_window.show()
        print("  Window opened")


print("✓ Step 6: Class defined")

def main(argv=None):
    print("✓ Step 7: main() called")
    argv = argv or sys.argv
    
    app = QApplication(argv)
    print("✓ Step 8: QApplication created")
    
    qss_content = load_stylesheet("dark.qss", "styles")
    if qss_content:
        app.setStyleSheet(qss_content)
        print("✓ Step 9: Stylesheet loaded")
    
    try:
        print("✓ Step 10: Creating dashboard window...")
        window = BalloonSatDashboard()
        print("✓ Step 11: Dashboard created")
        
        window.resize(1500, 800)
        print("✓ Step 12: Window resized")
        
        window.show()
        print("✓ Step 13: Window shown")
        
        print("\n" + "="*60)
        print("🚀 BalloonSat Telemetry Dashboard Started")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error in main: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("✓ Step 14: Entering event loop...")
    return app.exec()


if __name__ == "__main__":
    print("✓ Step 15: Script entry point")
    sys.exit(main())