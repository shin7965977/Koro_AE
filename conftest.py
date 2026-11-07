"""Pytest configuration ensuring project root and cockpit_core are on sys.path."""

from __future__ import annotations

import os
import sys

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
SUBMODULE_DIR = os.path.join(ROOT_DIR, "cockpit_core")
SIBLING_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "lakehouse-cockpit-core"))
COCKPIT_CORE_DIR = SUBMODULE_DIR if os.path.isdir(SUBMODULE_DIR) else SIBLING_DIR

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if COCKPIT_CORE_DIR not in sys.path:
    sys.path.insert(0, COCKPIT_CORE_DIR)
