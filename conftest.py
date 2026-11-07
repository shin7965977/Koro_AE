"""Pytest configuration ensuring project root and lakehouse-cockpit-core are on sys.path."""

from __future__ import annotations

import os
import sys

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
COCKPIT_CORE_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "lakehouse-cockpit-core"))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if COCKPIT_CORE_DIR not in sys.path:
    sys.path.insert(0, COCKPIT_CORE_DIR)
