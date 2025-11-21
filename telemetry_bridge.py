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
import threading
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Optional, Dict, Any

from dispatcher import dispatch


class TelemetryFilePlayer:
    """Replay telemetry from a JSON file and emit dispatcher signals.

    Parameters
    - file_path: path to a NDJSON file or JSON array file
    - realtime: if True, honor timestamps and sleep between records
    - speed: replay speed multiplier (>1 faster, <1 slower)
    - default_interval: seconds between records if no timestamps (float)
    - loop: whether to loop the file continuously
    """

    def __init__(self, file_path: str, realtime: bool = True, speed: float = 1.0,
                 default_interval: float = 0.5, loop: bool = False):
        self.file_path = file_path
        self.realtime = realtime
        self.speed = float(speed) if speed > 0 else 1.0
        self.default_interval = float(default_interval)
        self.loop = loop

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    def _open_records(self):
        # Try to detect NDJSON vs JSON array
        with open(self.file_path, 'r', encoding='utf-8') as fh:
            first = fh.read(1)
            fh.seek(0)
            if not first:
                return []
            if first == '[':
                # JSON array
                return json.load(fh)
            # NDJSON: yield one JSON object per line
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # ignore bad lines
                    continue

    # ------------------------------------------------------------------
    def _parse_ts(self, record: Dict[str, Any]) -> Optional[float]:
        # Accept ISO 8601 string or numeric epoch (seconds or ms)
        ts = record.get('ts') or record.get('timestamp')
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            # if large, assume milliseconds
            if ts > 1e12:
                return ts / 1000.0
            return float(ts)
        # try parsing ISO format
        try:
            # datetime.fromisoformat doesn't accept trailing Z; handle Z
            if isinstance(ts, str) and ts.endswith('Z'):
                ts = ts[:-1] + '+00:00'
            dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return None

    # ------------------------------------------------------------------
    def _emit_record(self, record: Dict[str, Any]) -> None:
        # Emit telemetry dict
        telemetry = record.get('telemetry') or record.get('data') or {}

        # Normalize GPS fields: if gps_lat & gps_lon present, create gps_latlon
        if 'gps_lat' in telemetry and 'gps_lon' in telemetry:
            try:
                telemetry['gps_latlon'] = (float(telemetry['gps_lat']), float(telemetry['gps_lon']))
            except Exception:
                pass

        # For backwards compatibility with metadata which expects 'gps_latlon'
        if 'gps_latlon' in telemetry and isinstance(telemetry['gps_latlon'], (list, tuple)):
            lat, lon = telemetry['gps_latlon']
            telemetry['gps_latlon'] = f"{lat:.6f}, {lon:.6f}"

        # Emit telemetryUpdated
        try:
            dispatch.telemetryUpdated.emit(dict(telemetry))
        except Exception:
            pass

        # Emit sensorStatusUpdated if present
        sensors = record.get('sensors')
        if isinstance(sensors, dict):
            try:
                dispatch.sensorStatusUpdated.emit(sensors)
            except Exception:
                pass

        # Emit trajectoryAppended for GPS points if lat/lon present
        lat = telemetry.get('gps_lat')
        lon = telemetry.get('gps_lon')
        alt = telemetry.get('alt_gps') or telemetry.get('alt_bmp')
        if lat is not None and lon is not None:
            try:
                t = self._parse_ts(record) or time.time()
                point = SimpleNamespace(t=t, lat=float(lat), lon=float(lon),
                                        alt_expected=alt if alt is not None else 0.0,
                                        alt_actual=alt if alt is not None else 0.0)
                dispatch.trajectoryAppended.emit(point)
            except Exception:
                pass

    # ------------------------------------------------------------------
    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                records_iter = self._open_records()
                # If _open_records returned a list (JSON array) use it
                if isinstance(records_iter, list):
                    records = records_iter
                else:
                    records = list(records_iter)

                if not records:
                    return

                prev_ts = None
                for rec in records:
                    if self._stop_event.is_set():
                        break
                    ts = self._parse_ts(rec)
                    if self.realtime and ts is not None and prev_ts is not None:
                        # sleep scaled by speed
                        wait = max(0.0, (ts - prev_ts) / max(0.0001, self.speed))
                        time.sleep(wait)
                    elif self.realtime and ts is None:
                        time.sleep(self.default_interval / max(0.0001, self.speed))

                    self._emit_record(rec)
                    prev_ts = ts or time.time()

                if not self.loop:
                    break
                # loop: small pause before replaying
                time.sleep(0.1)
            except Exception:
                # Prevent thread from dying; log minimally then stop
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
