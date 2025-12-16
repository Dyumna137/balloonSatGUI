Run and tune on Raspberry Pi
===========================

This project uses `PyQt6` + `pyqtgraph` (which depends on `numpy`) for GUI and plotting. To run on Raspberry Pi, follow these recommendations to reduce CPU and memory usage.

1. Embedded mode (recommended)
- Set environment variable `DASHBOARD_EMBEDDED=1` before launching the app to enable conservative defaults (fewer plot points, faster scaling, disabled markers).

2. Recommended hardware
- Raspberry Pi 4 (4GB+) or Raspberry Pi 5 for comfortable performance.
- Pi 3 can run but will be much slower; Pi Zero not recommended for the full GUI.

3. System packages and Python
- Prefer system packages for Qt and NumPy where possible (`apt install python3-pyqt6 python3-numpy`).
- Example install commands for Raspberry Pi OS (run on the Pi):

```pwsh
sudo apt update
sudo apt install python3-pyqt6 python3-numpy python3-pip
pip3 install pyqtgraph psutil pyserial paho-mqtt
```

4. Graphics driver
- Enable hardware-accelerated GL driver (if available) via raspi-config or appropriate Mesa driver. If driver causes issues, use embedded mode (which disables OpenGL for pyqtgraph).

5. Tuning notes
- The embedded mode reduces `max_points`, increases `update_interval`, disables markers, and uses faster image scaling. You can also tweak these at runtime via code in `widgets/charts.py` and `widgets/live_feed.py`.

6. Avoid adding heavy libraries
- Avoid installing OpenCV (`cv2`) unless required; it increases memory and CPU.

7. Run with a lightweight desktop
- Use LXDE/Openbox and avoid compositor animations while running the dashboard.

If you'd like, I can:
- Add a command-line flag or settings file to toggle embedded mode instead of using env var.
- Further reduce defaults (e.g., `_max_points=500`) for Pi 3 / low-memory targets.
- Replace pyqtgraph with a simpler drawing solution (less features but lower overhead).

Which of these would you like me to implement next?

Simplified launcher
--------------------
To make running on Raspberry Pi easier without changing any code, a
small helper script `run_simple.py` has been added. It sets conservative
environment variables and starts the dashboard with embedded-friendly
defaults (reduced drawing detail, OpenGL disabled).

Usage (from project root):

```pwsh
python run_simple.py
```

This script is non-invasive: it doesn't modify the dashboard source,
only sets environment variables at process start to enable the lower-cost
path already present in the codebase.