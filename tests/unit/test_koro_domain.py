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
