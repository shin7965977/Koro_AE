# 03: End-to-end Hero Scenario: 2-round Socratic guidance to traceable bulk packaging return chart

**What to build:**
Connect the end-to-end tracer bullet for the hero scenario ("🌰 Bulk Packaging Return Diagnosis"). Clicking the preset or asking about returns triggers Round 1 clarifying questions, converges in Round 2 to a locked `AnalyticalSpecContract`, and compiles into an `OnDemandInsightResult` showing the 5.2% 1kg Cashew return rate (78% vacuum packaging defect), grouped bar chart, executable Gold Mart SQL, lineage badge, and 5-row data snippet.

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] Implement the 2-round Socratic state machine (`IDLE` -> `ROUND_1_CLARIFYING` -> `ROUND_2_SPEC_LOCKED`) in `ai/spec_guide.py`.
- [ ] Implement the deterministic spec compiler for the Bulk Packaging Return Diagnosis scenario using DuckDB over the Gold Mart (`mart_product_performance`) and Silver returns table.
- [ ] Wire `KoroAdapter` hooks (`handle_spec_inquiry_turn` and `compile_spec_to_insight`) and create the Streamlit entrypoint `dashboard/app.py`.
- [ ] Verify the complete 2-round conversation and compiled `OnDemandInsightResult` parity via integration tests.
