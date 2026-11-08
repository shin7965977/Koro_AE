"""CI Integration Tests for Progressive AE Guided Workflow State Machine and Intent Accuracy."""

from __future__ import annotations

import pytest
from cockpit_core.components.ae_workflow import synthesize_ae_lifecycle


def test_refund_query_prioritizes_return_defect_metrics_not_revenue() -> None:
    """Verify that stakeholder inquiries regarding refunds / returns map strictly to return_rate_pct and never to net_revenue_eur."""
    # Test case from real stakeholder input
    user_goal = "我想知道這個季度產生多少退款訂單?"
    state = synthesize_ae_lifecycle(user_goal=user_goal)

    assert state["intent"] == "bulk_returns"
    assert state["metric_name"] == "return_rate_pct"
    assert "returned_units" in state["formula"]
    assert "contracts/returns.yaml" == state["contract_file"]
    assert "raw_return_logs" in state["upstream_table"]
    # Ensure it didn't mistakenly fallback or match generic revenue/sales
    assert state["metric_name"] != "net_revenue_eur"


def test_sales_and_revenue_intent_routing() -> None:
    """Verify that pure sales queries map to net_revenue_eur."""
    user_goal = "我想知道這一季所有產品的銷售額"
    state = synthesize_ae_lifecycle(user_goal=user_goal)

    assert state["intent"] == "sales_revenue"
    assert state["metric_name"] == "net_revenue_eur"
    assert "gross_revenue_eur" in state["formula"]
    assert "contracts/orders_and_revenue_contract.yaml" == state["contract_file"]


def test_margin_and_inventory_intent_routing() -> None:
    """Verify that margin and inventory queries map to their respective governed metrics."""
    # Margin
    margin_state = synthesize_ae_lifecycle(user_goal="哪一個品類毛利率最高？")
    assert margin_state["intent"] == "category_margin"
    assert margin_state["metric_name"] == "net_margin_pct"

    # Inventory
    inv_state = synthesize_ae_lifecycle(user_goal="哪些熱銷商品有缺貨風險？")
    assert inv_state["intent"] == "inventory_health"
    assert inv_state["metric_name"] == "days_of_supply"
