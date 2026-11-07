"""Integration tests for dynamic 6-step AE lifecycle and context inheritance across steps."""

from __future__ import annotations

import pytest

from cockpit_core.components.ae_workflow import synthesize_ae_lifecycle


def test_context_inheritance_when_user_specifies_quarterly_sales() -> None:
    """Verify that when a stakeholder enters '我想知道這一季產品的銷售額', all downstream steps inherit revenue metrics."""
    goal_input = "我想知道這一季產品的銷售額"
    state = synthesize_ae_lifecycle(user_goal=goal_input)

    # Step 1: Business Scoping
    assert state["intent"] == "sales_revenue"
    assert goal_input in state["stakeholder_q_zh"]
    assert "季度淨銷售額" in state["metric_title_zh"]

    # Step 2: Metric Definition (NOT return_rate_pct!)
    assert state["metric_name"] == "net_revenue_eur"
    assert "return_rate_pct" not in state["metric_name"]
    assert "gross_revenue_eur" in state["formula"]

    # Step 3: Data Contracts (NOT returns.yaml!)
    assert state["upstream_table"] == "raw_shopware_orders"
    assert "orders" in state["contract_file"]
    assert "returns.yaml" not in state["contract_file"]

    # Step 4: dbt SQL
    assert "net_revenue_eur" in state["dbt_sql"]
    assert "raw_shopware_orders" in state["dbt_sql"]

    # Step 5: LookML View
    assert "measure: total_net_revenue" in state["lookml_view"]
    assert "eur" in state["lookml_view"]


def test_context_inheritance_when_user_specifies_margin_goal() -> None:
    """Verify margin intent properly cascades across steps."""
    goal_input = "我想分析各品類折扣後的淨毛利率"
    state = synthesize_ae_lifecycle(user_goal=goal_input)

    assert state["intent"] == "category_margin"
    assert state["metric_name"] == "net_margin_pct"
    assert "cogs_eur" in state["formula"]
    assert "margin" in state["contract_file"]


def test_context_inheritance_when_user_specifies_inventory_goal() -> None:
    """Verify inventory intent properly cascades across steps."""
    goal_input = "我想知道哪些商品庫存快斷貨了"
    state = synthesize_ae_lifecycle(user_goal=goal_input)

    assert state["intent"] == "inventory_health"
    assert state["metric_name"] == "days_of_supply"
    assert "inventory" in state["contract_file"]
    assert "stock_on_hand" in state["formula"]
