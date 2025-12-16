"""Simplified launcher for BalloonSat dashboard

This lightweight entry script sets conservative environment options
for embedded/Raspberry Pi usage and starts the existing dashboard
without changing the core code. It intentionally avoids enabling
camera or OpenGL features and uses the demo replay if available.

Usage:
    python run_simple.py

This file is placed on a new branch `simplify-minimal` and is
meant to be a non-invasive helper: it doesn't modify any existing
module behavior, only sets environment variables at process start.
"""
from __future__ import annotations
import os
import sys

# Conservative defaults for embedded devices
os.environ.setdefault("DASHBOARD_EMBEDDED", "1")
os.environ.setdefault("DASHBOARD_LIGHT_MODE", "1")

# Prevent pyqtgraph from trying to use OpenGL on low-powered devices
os.environ.setdefault("PYQTGRAPH_NO_OPENGL", "1")

def _run():
    # Import the main entry point and run it.
    # Prefer local script import (running from repo root) but fall back
    # to package import if installed.
    try:
        # When running from repo root
        from dashboard import main
    except Exception:
        from dashboardGUI.dashboard import main

    # Pass minimal argv so Qt won't interpret other flags unexpectedly
    argv = [sys.argv[0]]
    return main(argv)


if __name__ == "__main__":
    sys.exit(_run())
