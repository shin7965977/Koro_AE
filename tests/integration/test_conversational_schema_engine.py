"""Unit & Integration Tests for Autonomous Schema Design & dbt Transformation Engine."""

from __future__ import annotations

import pytest
from ai.schema_engine import DatabaseReflectionService, compile_dbt_and_schema_contract, classify_schema_intent
from koro_adapter import KoroAdapter


def test_schema_reflection_discovers_kimball_models() -> None:
    """Verify that reflection service extracts conformed Kimball facts and dimensions accurately from DuckDB."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    models = reflection.get_kimball_models()
    assert "dim_products" in models["dimensions"]
    assert "dim_categories" in models["dimensions"]
    assert "dim_customers" in models["dimensions"]
    assert "fct_order_items" in models["facts"]
    assert "fct_returns" in models["facts"]
    assert "fct_orders" in models["facts"]

    # Check schema inspection on dim_products
    prod_meta = reflection.inspect_table_schema("dim_products")
    col_names = [c["name"] for c in prod_meta["columns"]]
    assert "product_id" in col_names
    assert "packaging_size" in col_names
    assert "unit_price_eur" in col_names


def test_schema_reflection_resolves_standard_kimball_joins() -> None:
    """Verify join path resolution between facts and dimensions."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    joins = reflection.resolve_join_paths(["dim_products", "fct_order_items", "fct_returns"])
    assert any("fct_order_items" in j and "product_id" in j for j in joins)
    assert any("fct_returns" in j and "product_id" in j for j in joins)


def test_end_to_end_conversational_schema_synthesis_and_dry_run() -> None:
    """Verify natural language request generates valid dbt SQL, schema.yml, and passes physical dry-run."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    result = compile_dbt_and_schema_contract(
        scenario_key="bulk_returns",
        user_goal="I want to isolate product return rates by packaging size (1kg vs 500g)",
        reflection=reflection,
    )

    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert len(result.data_preview) > 0
    assert "return_rate_pct" in result.data_preview.columns
    assert "product_name" in result.data_preview.columns

    # Verify dbt SQL contents
    assert "{{ ref('dim_products') }}" in result.dbt_sql
    assert "{{ ref('fct_order_items') }}" in result.dbt_sql
    assert "{{ ref('fct_returns') }}" in result.dbt_sql
    assert "NULLIF" in result.dbt_sql

    # Verify schema.yml contents & GDPR governance
    assert "version: 2" in result.schema_yaml
    assert "contains_pii: false" in result.schema_yaml
    assert "relationships:" in result.schema_yaml
    assert "tests:" in result.schema_yaml

    # Verify audit trace observability
    assert len(result.audit_trace) >= 4
    trace_steps = [t["step"] for t in result.audit_trace]
    assert "Socratic Clarification" in trace_steps
    assert "Physical DuckDB Dry-Run" in trace_steps
    assert "Governance Verification" in trace_steps


def test_out_of_domain_inquiry_triggers_guardrail_rejection() -> None:
    """Verify that unrelated or gibberish inquiries like '威爾是誰' are rejected by domain guardrails."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    result = compile_dbt_and_schema_contract(
        user_goal="威爾是誰",
        reflection=reflection,
    )

    assert result.is_rejected is True
    assert "REJECTED" in result.spec_id
    assert "outside lakehouse analytics scope" in result.rejection_reason
    assert result.dry_run_success is False
    assert len(result.data_preview) == 0
    assert result.dbt_sql == ""
    assert result.schema_yaml == ""

    # Verify audit trace contains rejection step
    trace_steps = [t["step"] for t in result.audit_trace]
    assert "Domain Guardrail" in trace_steps
    guardrail_step = next(t for t in result.audit_trace if t["step"] == "Domain Guardrail")
    assert guardrail_step["status"] == "BLOCKED"


def test_classify_schema_intent_matrix() -> None:
    """Verify that intent classifier properly routes returns, margins, and rejects gibberish."""
    # Domain 1: Returns
    intent_ret, _ = classify_schema_intent("分析 1kg 堅果大包裝退貨率與破損")
    assert intent_ret == "bulk_returns"

    # Domain 2: Margins
    intent_margin, _ = classify_schema_intent("計算各品類促銷折價券後的淨毛利率")
    assert intent_margin == "category_margin"

    # Out of Domain
    intent_ood, _ = classify_schema_intent("威爾是誰")
    assert intent_ood is None
    intent_empty, _ = classify_schema_intent("   ")
    assert intent_empty is None
