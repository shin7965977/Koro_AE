"""Unit tests for Step 6 Looker Studio embedding and strict removal of Plotly mock."""

from __future__ import annotations

import inspect

from cockpit_core.components import ae_workflow
from koro_adapter import KoroAdapter


def test_step_6_embeds_real_looker_studio_and_eliminates_plotly() -> None:
    """Verify that Step 6 is powered by real Looker Studio iframe and Plotly Express is eliminated."""
    source = inspect.getsource(ae_workflow)

    # 1. Plotly facade must be completely eliminated
    assert "plotly.express" not in source, "Plotly Express facade must be completely eliminated from Step 6!"
    assert "px.bar" not in source
    assert "px.line" not in source

    # 2. Real Looker Studio must be integrated
    assert "lookerstudio.google.com" in source
    assert "components.iframe" in source
    assert "Open in Looker Studio" in source
    assert "Edit Report in Looker Studio" in source


def test_adapter_supports_looker_and_ae_workflow() -> None:
    """Verify that KoroAdapter has looker and workflow flags enabled for tab selection."""
    adapter = KoroAdapter()
    assert adapter.supports_ae_workflow is True
    assert adapter.supports_looker is True
