"""Unit tests for KoRo domain contracts, semantic rules, Medallion data engine, and KoroAdapter."""

from __future__ import annotations

import os
from datetime import date

import yaml

from koro_adapter import KoroAdapter


def test_data_contracts_and_semantic_rules_exist_and_valid() -> None:
    """Verify all YAML data contracts and semantic business rules are valid and GDPR-compliant."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for contract_file in ["products.yaml", "orders.yaml", "order_items.yaml", "returns.yaml"]:
        path = os.path.join(root, "contracts", contract_file)
        assert os.path.exists(path), f"Missing contract: {contract_file}"
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        assert "entity" in doc
        assert "fields" in doc
        assert doc.get("metadata", {}).get("contains_pii") is False

    rules_path = os.path.join(root, "semantic", "business_rules.yaml")
    assert os.path.exists(rules_path)
    with open(rules_path, encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    metric_keys = {m["key"] for m in rules.get("metrics", [])}
    assert {"gross_revenue", "net_revenue", "aov", "return_rate", "asp", "product_availability"}.issubset(
        metric_keys
    )


def test_koro_adapter_medallion_data_and_hero_anomaly_pattern() -> None:
    """Verify KoroAdapter loads Bronze/Silver/Gold tables and preserves the 1kg Cashew return anomaly."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    assert "mart_product_performance" in data
    assert "mart_category_daily" in data
    assert "int_returns_enriched" in data
    assert "raw_shopware_orders" in data

    gold_df = data["mart_product_performance"]
    cashew_1kg = gold_df[gold_df["product_id"] == "KORO-NUT-001"].iloc[0]
    assert cashew_1kg["packaging_size"] == "1kg"
    assert abs(float(cashew_1kg["return_rate_pct"]) - 5.2) < 0.15

    returns_df = data["int_returns_enriched"]
    cashew_returns = returns_df[returns_df["product_id"] == "KORO-NUT-001"]
    total_ret = cashew_returns["returned_units"].sum()
    vacuum_ret = cashew_returns[
        cashew_returns["return_reason"] == "Vacuum Packaging Defect"
    ]["returned_units"].sum()
    assert abs((vacuum_ret / total_ret) - 0.78) < 0.03


def test_koro_adapter_kpi_cards_and_date_filtering() -> None:
    """Verify the 4 executive KPI cards calculate valid metrics and respond to date filters."""
    adapter = KoroAdapter()
    full_data = adapter.load_domain_data()
    cards = adapter.kpi_cards
    assert len(cards) == 4
    card_keys = [c.key for c in cards]
    assert card_keys == ["gross_revenue", "net_revenue", "aov", "return_rate"]

    for card in cards:
        res = card.calculate(full_data)
        assert "value" in res
        assert res["status"] in ("normal", "warning")

    # Filtered window should have fewer or equal orders than full window
    filtered_data = adapter.load_domain_data(
        start_date=date(2026, 10, 1), end_date=date(2026, 10, 15)
    )
    assert len(filtered_data["raw_shopware_orders"]) < len(full_data["raw_shopware_orders"])


def test_readcall_style_kpi_formula_tooltips_without_unit() -> None:
    """Verify all 4 KPI cards supply ReadCall-style numerator and denominator tooltips without unit."""
    adapter = KoroAdapter()
    for card in adapter.kpi_cards:
        assert card.formula_numerator is not None
        assert card.formula_denominator is not None
        assert card.formula_numerator.label
        assert card.formula_numerator.description
        assert card.formula_numerator.description_zh
        assert card.formula_denominator.label
        assert card.formula_denominator.description
        assert card.formula_denominator.description_zh
        # Strictly verify no 'unit' attribute on MetricComponent
        assert not hasattr(card.formula_numerator, "unit")
        assert not hasattr(card.formula_denominator, "unit")


def test_open_exploration_copilot_turn_handles_no_idea_conversationally() -> None:
    """Verify Copilot answers open questions conversationally without forcing rigid scenario locks."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    # User query from real user feedback
    query = "我想要做一些報表，但我現在沒想法，我可以做哪些報表，現在有哪些資訊？"
    turn = adapter.handle_spec_inquiry_turn(user_query=query, chat_history=[], data_dict=data, is_en=False)

    assert turn["spec_contract"] is None
    assert turn["next_round"] == 0
    # Must introduce categories and not lock spec
    assert "堅果" in turn["reply"] or "品類" in turn["reply"]
    assert "退貨率" in turn["reply"] or "營收" in turn["reply"]


def test_looker_and_lookml_integration_properties() -> None:
    """Verify Looker support and LookML view definition are active and well-formed."""
    adapter = KoroAdapter()
    assert adapter.supports_looker is True
    lookml = adapter.lookml_view_definition
    assert "view: mart_product_performance" in lookml
    assert "dimension: product_id" in lookml
    assert "measure: net_revenue" in lookml
    assert "measure: unit_return_rate" in lookml


def test_sql_sandbox_execution_and_finops_protection() -> None:
    """Verify custom SQL sandbox query executes safely and blocks destructive DDL/DML."""
    import pytest
    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    # Safe SELECT query
    res_df = adapter.execute_custom_sql("SELECT product_id, product_name FROM mart_product_performance LIMIT 5", data)
    assert len(res_df) == 5
    assert "product_id" in res_df.columns

    # Destructive DROP command must be blocked
    with pytest.raises(ValueError, match="Security Alert"):
        adapter.execute_custom_sql("DROP TABLE mart_product_performance", data)


def test_multilingual_adaptive_and_language_capability_inquiry() -> None:
    """Verify system handles '能說中文嗎' and '你是誰' politely in Traditional Chinese without forcing bulk_returns."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    # Query from user's screenshot
    res = adapter.handle_spec_inquiry_turn(user_query="能說中文嗎", chat_history=[], data_dict=data, is_en=True)
    assert res["spec_contract"] is None
    assert res["next_round"] == 0
    assert "繁體中文" in res["reply"] or "當然可以" in res["reply"]
    # Must NOT force bulk_returns
    assert "Bulk Packaging Returns" not in res["reply"]
    assert "Round 1/2" not in res["reply"]

    # Identity question
    res2 = adapter.handle_spec_inquiry_turn(user_query="你是誰", chat_history=[], data_dict=data, is_en=True)
    assert res2["spec_contract"] is None
    assert "分析工程智能協作助理" in res2["reply"]
