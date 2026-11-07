"""Integration tests for Ticket #03: Hero Bulk Packaging Return Diagnosis 2-round flow."""

from __future__ import annotations

from koro_adapter import KoroAdapter


def test_two_round_socratic_flow_locks_bulk_return_spec() -> None:
    """Verify Round 1 asks clarifying questions and Round 2 locks the AnalyticalSpecContract."""
    adapter = KoroAdapter()

    # Round 1: Stakeholder clicks preset or asks vague question about returns
    turn1 = adapter.handle_spec_inquiry_turn(
        user_query="🌰 1kg Bulk Packaging Return Diagnosis",
        current_round=0,
        session_context={},
        is_en=True,
    )
    assert turn1["next_round"] == 1
    assert turn1["spec_contract"] is None
    assert turn1["scenario_key"] == "bulk_returns"
    assert "return" in turn1["reply"].lower() or "packaging" in turn1["reply"].lower()

    # Round 2: Stakeholder confirms metric scope -> immediately locks Spec Contract
    turn2 = adapter.handle_spec_inquiry_turn(
        user_query="Count by units, last 90 days, compare 1kg vs 500g in Nuts & Butters",
        current_round=turn1["next_round"],
        session_context={"scenario_key": turn1["scenario_key"]},
        is_en=True,
    )
    assert turn2["next_round"] == 2
    spec = turn2["spec_contract"]
    assert spec is not None
    assert spec.scenario_key == "bulk_returns"
    assert spec.target_layer == "gold"
    assert spec.target_mart == "mart_product_performance"
    assert any(m["name"] == "return_rate" for m in spec.metrics)


def test_compile_bulk_return_spec_produces_aligned_traceable_insight() -> None:
    """Verify compiling the locked spec produces Executive Takeaway, Figure, SQL, Lineage, and 1:1 DataFrame."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    turn1 = adapter.handle_spec_inquiry_turn(
        user_query="I want to see nut return rates",
        current_round=0,
        session_context={},
        is_en=True,
    )
    turn2 = adapter.handle_spec_inquiry_turn(
        user_query="Yes, unit return rate for 1kg bulk bags",
        current_round=turn1["next_round"],
        session_context={"scenario_key": turn1["scenario_key"]},
        is_en=True,
    )
    spec = turn2["spec_contract"]
    insight = adapter.compile_spec_to_insight(spec_contract=spec, data_dict=data, is_en=True)

    assert insight is not None
    assert "5.2%" in insight.executive_takeaway or "5.20%" in insight.executive_takeaway
    assert "78%" in insight.executive_takeaway
    assert insight.figure is not None
    assert "mart_product_performance" in insight.executed_sql
    assert "semantic/business_rules.yaml" in insight.lineage_markdown
    assert not insight.df_snippet.empty
    assert "return_rate_pct" in insight.df_snippet.columns
