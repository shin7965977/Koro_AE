"""Streamlit Dashboard Entrypoint for KoRo Analytics Engineering POC.

Injects KoroAdapter into the reusable lakehouse-cockpit-core microkernel.
"""

from __future__ import annotations

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COCKPIT_CORE_DIR = os.environ.get(
    "COCKPIT_CORE_PATH",
    os.path.abspath(os.path.join(ROOT_DIR, "..", "lakehouse-cockpit-core")),
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if COCKPIT_CORE_DIR not in sys.path:
    sys.path.insert(0, COCKPIT_CORE_DIR)

from engine import launch_cockpit_app

from koro_adapter import KoroAdapter


def main() -> None:
    """Launch the KoRo Analytics & AI Semantic Cockpit."""
    adapter = KoroAdapter()
    launch_cockpit_app(adapter)


if __name__ == "__main__":
    main()
