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


def test_sales_and_revenue_inquiry_accepted_and_synthesized() -> None:
    """Verify '我想知道10月的整體營業額' is recognized within domain and synthesizes physical revenue model."""
    adapter = KoroAdapter()
    data = adapter.load_domain_data()
    reflection = DatabaseReflectionService(data)

    session = analyze_socratic_inquiry("我想知道10月的整體營業額", reflection=reflection)
    assert session.is_out_of_domain is False

    decisions = {
        "temporal": "2026-10-01:2026-10-31",
        "grain": "monthly_revenue",
    }
    result = synthesize_dynamic_dbt_model("我想知道10月的整體營業額", decisions, reflection)
    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert len(result.data_preview) > 0
    assert "gross_revenue_eur" in result.data_preview.columns
    assert "net_revenue_eur" in result.data_preview.columns


def test_gemini_genai_socratic_call_with_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _call_gemini_socratic interacts properly with Google GenAI SDK when api_key is present."""
    import sys
    import types
    import json

    class MockModelResponse:
        def __init__(self, text: str):
            self.text = text

    class MockModels:
        def generate_content(self, model: str, contents: str, config: Any = None):
            fake_payload = {
                "is_out_of_domain": False,
                "rejection_reason": "",
                "needs_clarification": True,
                "questions": [
                    {
                        "question_id": "temporal_test",
                        "dimension_type": "temporal",
                        "title": "時間意圖解析 (LLM 生成)",
                        "explanation": "Gemini 檢測到您提及 10 月份。",
                        "options": [
                            {"id": "oct", "label": "2026 年 10 月", "value": "2026-10-01:2026-10-31"}
                        ]
                    }
                ],
                "locked_decisions": {"grain": "monthly_revenue"}
            }
            return MockModelResponse(json.dumps(fake_payload))

    class MockClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = MockModels()

    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = MockClient  # type: ignore
    fake_types = types.ModuleType("google.genai.types")
    fake_types.GenerateContentConfig = lambda **kwargs: kwargs  # type: ignore
    fake_genai.types = fake_types  # type: ignore

    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

    session = analyze_socratic_inquiry("我想知道10月的整體營業額", api_key="AIzaSyTestMockKey12345")
    assert session.is_out_of_domain is False
    assert session.needs_clarification is True
    assert len(session.questions) == 1
    assert session.questions[0].title == "時間意圖解析 (LLM 生成)"
