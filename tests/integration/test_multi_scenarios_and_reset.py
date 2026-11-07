"""Integration tests for Ticket #04: Multi-scenario presets, dual-mode fallback, and state reset."""

from __future__ import annotations

import pytest

from koro_adapter import KoroAdapter


@pytest.mark.parametrize(
    ("initial_query", "expected_scenario", "expected_keyword_in_sql"),
    [
        (
            "💰 Category Net Margin & Discount Impact",
            "category_margin",
            "net_margin_pct",
        ),
        (
            "📦 Inventory Availability & Stockout Risk",
            "inventory_health",
            "days_of_supply",
        ),
        (
            "Which product category has the highest profit margin after discounts?",
            "category_margin",
            "net_margin_pct",
        ),
        (
            "Are any products out of stock or facing availability issues?",
            "inventory_health",
            "is_available",
        ),
    ],
)
def test_multi_scenarios_and_intent_fallback(
    initial_query: str,
    expected_scenario: str,
    expected_keyword_in_sql: str,
) -> None:
    """Verify all preset scenarios and free-text intent queries converge in 2 turns and compile cleanly."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    t1 = adapter.handle_spec_inquiry_turn(
        user_query=initial_query,
        current_round=0,
        session_context={},
        is_en=True,
    )
    assert t1["next_round"] == 1
    assert t1["scenario_key"] == expected_scenario
    assert t1["spec_contract"] is None

    t2 = adapter.handle_spec_inquiry_turn(
        user_query="Confirm standard definition and last 90 days.",
        current_round=t1["next_round"],
        session_context={"scenario_key": t1["scenario_key"]},
        is_en=True,
    )
    assert t2["next_round"] == 2
    assert t2["spec_contract"] is not None

    insight = adapter.compile_spec_to_insight(
        spec_contract=t2["spec_contract"],
        data_dict=data,
        is_en=True,
    )
    assert insight is not None
    assert expected_keyword_in_sql in insight.executed_sql
    assert insight.figure is not None
    assert not insight.df_snippet.empty
