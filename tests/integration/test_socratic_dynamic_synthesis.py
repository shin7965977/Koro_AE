"""Integration Tests for Socratic Intent Clarification & Dynamic dbt Model Synthesis."""

from __future__ import annotations

import pytest
from koro_adapter import KoroAdapter
from ai.schema_engine import DatabaseReflectionService
from ai.socratic_copilot import (
    get_lakehouse_watermark,
    analyze_socratic_inquiry,
    synthesize_dynamic_dbt_model,
)


def test_lakehouse_watermark_probes_physical_duckdb() -> None:
    """Verify physical warehouse watermarks accurately reflect latest October 2026 data."""
    watermark = get_lakehouse_watermark()
    assert watermark["max_date"] == "2026-10-31"
    assert watermark["current_month"] == "2026-10"
    assert watermark["current_month_start"] == "2026-10-01"
    assert watermark["current_month_end"] == "2026-10-31"


def test_socratic_clarification_for_monthly_refunds_inquiry() -> None:
    """Verify natural language request '我想知道這個月的產品退款紀錄' triggers 2 targeted questions."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    session = analyze_socratic_inquiry("我想知道這個月的產品退款紀錄", reflection=reflection)

    assert session.is_out_of_domain is False
    assert session.needs_clarification is True
    assert len(session.questions) == 2

    # Question 1: Temporal
    q_temp = next(q for q in session.questions if q.dimension_type == "temporal")
    assert "2026-10" in q_temp.explanation
    assert any("2026-10-01" in opt["value"] for opt in q_temp.options)

    # Question 2: Grain
    q_grain = next(q for q in session.questions if q.dimension_type == "grain")
    assert "return_event" in [opt["value"] for opt in q_grain.options]
    assert "sku_summary" in [opt["value"] for opt in q_grain.options]


def test_dynamic_dbt_synthesis_monthly_refund_events() -> None:
    """Verify locked decisions dynamically synthesize authentic monthly product refund log without templates."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    decisions = {
        "temporal": "2026-10-01:2026-10-31",
        "grain": "return_event",
    }
    result = synthesize_dynamic_dbt_model("我想知道這個月的產品退款紀錄", decisions, reflection)

    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert len(result.data_preview) > 0  # 179 real refund records in Oct 2026
    assert result.spec_id == "SCHEMA-MART_MONTHLY_PRODUCT_REFUNDS"
    assert "Return Event" in result.target_grain

    # Verify SQL structure
    assert "{{ ref('fct_returns') }}" in result.dbt_sql
    assert "{{ ref('dim_products') }}" in result.dbt_sql
    assert "2026-10-01" in result.dbt_sql
    assert "2026-10-31" in result.dbt_sql

    # Verify columns in live preview
    cols = list(result.data_preview.columns)
    assert "return_id" in cols
    assert "order_id" in cols
    assert "refunded_eur" in cols
    assert "return_reason" in cols
    assert "product_name" in cols

    # Verify audit trace
    steps = [t["step"] for t in result.audit_trace]
    assert "Socratic Clarification" in steps
    assert "Physical DuckDB Dry-Run" in steps
    socratic_step = next(t for t in result.audit_trace if t["step"] == "Socratic Clarification")
    assert "2026-10-01" in socratic_step["detail"]


def test_out_of_domain_inquiry_halted_by_socratic_guardrail() -> None:
    """Verify out-of-domain inquiries are cleanly rejected without generating SQL."""
    session = analyze_socratic_inquiry("威爾是誰")
    assert session.is_out_of_domain is True
    assert session.needs_clarification is False
    assert "超出湖倉分析範疇" in session.rejection_reason
