"""Streamlit Dashboard Entrypoint for KoRo Analytics Engineering POC.

Injects KoroAdapter into the reusable lakehouse-cockpit-core (cockpit_core) microkernel.
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Ensure git submodule cockpit_core is always synced to latest commit on Streamlit Cloud
try:
    subprocess.run(
        ["git", "submodule", "sync", "--recursive"],
        cwd=ROOT_DIR,
        check=False,
        timeout=10,
    )
    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive", "--force"],
        cwd=ROOT_DIR,
        check=False,
        timeout=15,
    )
except Exception:
    pass

from cockpit_core import launch_cockpit_app

from koro_adapter import KoroAdapter


def main() -> None:
    """Launch the KoRo Analytics & AI Semantic Cockpit."""
    adapter = KoroAdapter()
    launch_cockpit_app(adapter)


if __name__ == "__main__":
    main()
