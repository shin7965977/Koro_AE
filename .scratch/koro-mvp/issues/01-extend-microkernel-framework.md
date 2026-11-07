# 01: Extend microkernel framework for On-Demand Insight Panel and 2-round Spec Contract

**What to build:**
Upgrade `lakehouse-cockpit-core` while maintaining 100% backward compatibility so that any `BaseCockpitAdapter` can drive a 2-round Socratic Spec workflow in the AI drawer, display an `AnalyticalSpecContract` card with a confirm button, render an `On-Demand Insight Panel` (Executive Takeaway + Plotly Chart + 3-Layer Traceability Inspector) directly beneath the 4 KPI cards, and reset state via a `New Inquiry` button.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Define `AnalyticalSpecContract` and `OnDemandInsightResult` dataclasses in `lakehouse-cockpit-core/adapter.py` and add default hook methods on `BaseCockpitAdapter`.
- [x] Render the conditional `On-Demand Insight Panel` beneath the KPI grid in `lakehouse-cockpit-core/engine.py` with Executive Takeaway card, Plotly chart, and 3-Layer Traceability Inspector (`Executed SQL`, `Metric Lineage & Dictionary`, `Data Snippet`).
- [x] Add `🔄 New Inquiry` reset button and 2-round `AnalyticalSpecContract` confirmation card + `✅ Confirm & Generate Insight` button in `lakehouse-cockpit-core/components/ai_drawer.py`.
- [x] Verify backward compatibility and new contract lifecycle via unit tests.
