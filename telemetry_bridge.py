"""
Telemetry File Player / Bridge
================================

This module provides a small bridge that reads telemetry from a JSON file
and emits signals through the global `dispatch` dispatcher so the GUI can
consume the data exactly as if it were coming from live sensors.

Features:
 - Reads NDJSON (newline-delimited JSON) or a JSON array file
 - Emits `dispatch.telemetryUpdated` with a dict of telemetry keys
 - Emits `dispatch.sensorStatusUpdated` when `sensors` field present
 - Emits `dispatch.trajectoryAppended` for GPS points (lat/lon/alt)
 - Supports realtime replay using timestamps in telemetry records
 - Speed multiplier for faster/slower replay and optional looping

JSON format suggestions (NDJSON preferred for streaming):

Each record is a JSON object with a top-level `ts` timestamp and a
`telemetry` object with sensor readings. Only include fields relevant to
your active components (DHT22, BMP180, GPS, gyroscope-derived speed).

Example NDJSON (one line per record):

{"ts":"2025-11-21T12:00:00.000Z","telemetry":{
    "temp_dht":22.5,"hum_dht":45.2,
    "alt_bmp":123.4,"pressure_bmp":101325.0,"temp_bmp":21.8,
    "gps_lat":12.971598,"gps_lon":77.594566,"alt_gps":124.0,
    "speed":5.12
  },
 "sensors": {"dht22": true, "bmp": true, "gps": true, "mpu": true}
}

Notes on field naming (matches `metadata.py`):
 - DHT22: `temp_dht` (°C), `hum_dht` (%). The table currently has `temp_dht`.
 - BMP180/BMP280: `alt_bmp`, `pressure_bmp`, `temp_bmp`.
 - GPS: `gps_lat`, `gps_lon`, `alt_gps` (we also emit `gps_latlon` pair for table).
 - Gyroscope/MPU: `speed` (m/s) is used by telemetry model.

Replay behavior:
 - If `ts` values exist, the player will wait between records according to
   their timestamp differences (scaled by `speed` multiplier).
 - If timestamps are absent, the player will emit at `default_interval`.

Usage (simple):
    from telemetry_bridge import TelemetryFilePlayer

    player = TelemetryFilePlayer('data/telemetry.ndjson', realtime=True, speed=1.0)
    player.start()

    # Stop when done or to interrupt
    player.stop()

"""

from __future__ import annotations
import json
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Optional, Dict, Any, List

from dispatcher import dispatch

try:
    # Prefer Qt timer-based replay when running inside the GUI app
    from PyQt6.QtCore import QObject, QTimer
    _QT_AVAILABLE = True
except Exception:
    _QT_AVAILABLE = False
    # Fallback to threading-based player if Qt not available
    import threading


def _parse_ts_static(ts_val) -> Optional[float]:
    if ts_val is None:
        return None
    if isinstance(ts_val, (int, float)):
        if ts_val > 1e12:
            return ts_val / 1000.0
        return float(ts_val)
    try:
        if isinstance(ts_val, str) and ts_val.endswith('Z'):
            ts_val = ts_val[:-1] + '+00:00'
        dt = datetime.fromisoformat(ts_val)
        return dt.timestamp()
    except Exception:
        return None


class TelemetryFilePlayerBase:
    """Base helpers for file loading and record emission."""

    def __init__(self, file_path: str, realtime: bool = True, speed: float = 1.0,
                 default_interval: float = 0.5, loop: bool = False):
        self.file_path = file_path
        self.realtime = realtime
        self.speed = float(speed) if speed > 0 else 1.0
        self.default_interval = float(default_interval)
        self.loop = loop

        self.records: List[Dict[str, Any]] = []

    def _open_records(self):
        records = []
        with open(self.file_path, 'r', encoding='utf-8') as fh:
            first = fh.read(1)
            fh.seek(0)
            if not first:
                return []
            if first == '[':
                try:
                    records = json.load(fh)
                except Exception:
                    records = []
                return records
            # NDJSON
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    def _emit_record(self, record: Dict[str, Any]) -> None:
        telemetry = record.get('telemetry') or record.get('data') or {}

        # Normalize GPS
        if 'gps_lat' in telemetry and 'gps_lon' in telemetry:
            try:
                telemetry['gps_latlon'] = (float(telemetry['gps_lat']), float(telemetry['gps_lon']))
            except Exception:
                pass

        if 'gps_latlon' in telemetry and isinstance(telemetry['gps_latlon'], (list, tuple)):
            lat, lon = telemetry['gps_latlon']
            telemetry['gps_latlon'] = f"{lat:.6f}, {lon:.6f}"

        try:
            dispatch.telemetryUpdated.emit(dict(telemetry))
        except Exception:
            pass

        sensors = record.get('sensors')
        if isinstance(sensors, dict):
            try:
                dispatch.sensorStatusUpdated.emit(sensors)
            except Exception:
                pass

        lat = telemetry.get('gps_lat')
        lon = telemetry.get('gps_lon')
        alt = telemetry.get('alt_gps') or telemetry.get('alt_bmp')
        if lat is not None and lon is not None:
            try:
                t = _parse_ts_static(record.get('ts') or record.get('timestamp')) or time.time()
                point = SimpleNamespace(t=t, lat=float(lat), lon=float(lon),
                                        alt_expected=alt if alt is not None else 0.0,
                                        alt_actual=alt if alt is not None else 0.0)
                dispatch.trajectoryAppended.emit(point)
            except Exception:
                pass


if _QT_AVAILABLE:
    # Use a plain Python class that owns a QTimer (avoid subclassing QObject)
    class TelemetryFilePlayer(TelemetryFilePlayerBase):
        """Qt QTimer-based telemetry player that can be attached as `window.data_source`.

        Usage in GUI:
            player = TelemetryFilePlayer(path, realtime=True)
            window.data_source = player
            # Buttons call player.start()/player.stop()
        """

        def __init__(self, file_path: str, realtime: bool = True, speed: float = 1.0,
                     default_interval: float = 0.5, loop: bool = False, parent=None):
            # Initialize the pure-Python base first.
            TelemetryFilePlayerBase.__init__(self, file_path, realtime, speed, default_interval, loop)

            # Create a QTimer instance and optionally set its parent to keep
            # Qt ownership semantics, but do NOT subclass QObject to avoid
            # constructor argument conflicts with PyQt's sip wrapper.
            self._timer = QTimer()
            if parent is not None:
                # Attach the timer to the given Qt parent so it is cleaned up
                try:
                    self._timer.setParent(parent)
                except Exception:
                    pass
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._on_timeout)
            self._idx = 0
            self._prev_ts = None

        def start(self, restart: bool = False) -> None:
            """Start or resume playback.

            If `restart` is True, playback restarts from the beginning.
            Otherwise, playback resumes from the current index where it was
            stopped (pause/resume behavior).
            """
            # Load records into memory only if not loaded yet or if restart requested
            if not self.records or restart:
                self.records = self._open_records()
            if not self.records:
                return

            # If restarting explicitly, reset index; otherwise resume from stored index
            if restart:
                self._idx = 0
            else:
                # If index is beyond end (previously completed), wrap if looping
                if self._idx >= len(self.records):
                    if self.loop:
                        self._idx = 0
                    else:
                        # nothing to resume; start from beginning
                        self._idx = 0

            # Immediately emit the record at current index and schedule next
            self._on_timeout()

        def stop(self) -> None:
            # Stop the timer but keep `self._idx` so playback can resume
            if self._timer.isActive():
                self._timer.stop()

        def _on_timeout(self):
            if not self.records:
                return
            if self._idx >= len(self.records):
                if self.loop:
                    self._idx = 0
                else:
                    return

            rec = self.records[self._idx]
            try:
                self._emit_record(rec)
            except Exception:
                pass

            # compute delay to next record
            curr_ts = _parse_ts_static(rec.get('ts') or rec.get('timestamp'))
            next_idx = self._idx + 1
            delay_ms = int(self.default_interval * 1000 / max(0.0001, self.speed))
            if self.realtime and curr_ts is not None and next_idx < len(self.records):
                next_ts = _parse_ts_static(self.records[next_idx].get('ts') or self.records[next_idx].get('timestamp'))
                if next_ts is not None and curr_ts is not None:
                    wait = max(0.0, (next_ts - curr_ts) / max(0.0001, self.speed))
                    delay_ms = int(wait * 1000)

            self._idx = next_idx
            # schedule next
            self._timer.start(max(1, delay_ms))


else:
    # Fallback threading-based player (keeps earlier behavior for CLI use)
    class TelemetryFilePlayer(TelemetryFilePlayerBase):
        def __init__(self, file_path: str, realtime: bool = True, speed: float = 1.0,
                     default_interval: float = 0.5, loop: bool = False):
            super().__init__(file_path, realtime, speed, default_interval, loop)
            self._thread: Optional[threading.Thread] = None
            self._stop_event = threading.Event()

        def start(self) -> None:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

        def stop(self) -> None:
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=1.0)

        def _run(self) -> None:
            while not self._stop_event.is_set():
                try:
                    # Load records if not yet loaded
                    if not self.records:
                        self.records = self._open_records()
                    if not self.records:
                        return

                    prev_ts = None
                    # Iterate starting at current index to allow resume
                    idx = self._idx
                    while idx < len(self.records) and not self._stop_event.is_set():
                        rec = self.records[idx]
                        ts = _parse_ts_static(rec.get('ts') or rec.get('timestamp'))
                        if self.realtime and ts is not None and prev_ts is not None:
                            wait = max(0.0, (ts - prev_ts) / max(0.0001, self.speed))
                            time.sleep(wait)
                        elif self.realtime and ts is None:
                            time.sleep(self.default_interval / max(0.0001, self.speed))

                        self._emit_record(rec)
                        prev_ts = ts or time.time()
                        idx += 1
                        # store idx as next-to-play so stop/resume works
                        self._idx = idx

                    if not self.loop:
                        break
                    time.sleep(0.1)
                except Exception:
                    break


if __name__ == "__main__":
    # Quick CLI demo: play `data/replays/demo.ndjson` if available
    import os, sys
    base = os.path.dirname(__file__)
    candidates = [
        os.path.join(base, 'data', 'replays', 'demo.ndjson'),
        os.path.join(base, 'data', 'replays', 'demo.json'),
        os.path.join(base, 'data', 'demo.ndjson'),
        os.path.join(base, 'data', 'demo.json')
    ]
    fp = None
    for c in candidates:
        if os.path.exists(c):
            fp = c
            break

    if not fp:
        print("No demo file found in data/replays/ or data/. Place NDJSON replay(s) under data/replays/. Exiting.")
        sys.exit(0)

    player = TelemetryFilePlayer(fp, realtime=False, speed=1.0, loop=False)
    player.start()
    try:
        while player._thread and player._thread.is_alive():
            time.sleep(0.2)
    except KeyboardInterrupt:
        player.stop()
