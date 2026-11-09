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


def test_taiwanese_product_revenue_inquiry_strictly_rejected() -> None:
    """Verify 'I would like to know the taiwanese product's revenue' is rejected and never compiles revenue mart."""
    session = analyze_socratic_inquiry("I would like to know the taiwanese product's revenue")
    assert session.is_out_of_domain is True
    assert session.needs_clarification is False
    assert "超出湖倉分析範疇" in session.rejection_reason or "無台灣產品" in session.rejection_reason


def test_missing_api_key_in_runtime_strictly_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that in live runtime without GEMINI_API_KEY, queries are immediately rejected."""
    import os
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    session = analyze_socratic_inquiry("I would like to know the taiwanese product's revenue", api_key="")
    assert session.is_out_of_domain is True
    assert session.is_api_key_missing is True
    assert "未檢測到 Gemini API Key" in session.rejection_reason


def test_gemini_rejects_taiwanese_products_via_llm_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Gemini evaluates out-of-catalog entities and returns honest domain rejection."""
    import sys
    import types
    import json
    from typing import Any

    class MockModelResponse:
        def __init__(self, text: str):
            self.text = text

    class MockModels:
        def generate_content(self, model: str, contents: str, config: Any = None):
            fake_payload = {
                "is_out_of_domain": True,
                "rejection_reason": "KoRo 湖倉現有型錄僅包含 12 款歐洲堅果、果乾、點心與料理粉類 SKU，且 dim_products 不含產地 (origin_country) 或台灣產品資料。為了遵守 Zero-Facade 規範，系統拒絕合成不存在的指標模型。",
                "needs_clarification": False,
                "questions": [],
                "locked_decisions": {}
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

    session = analyze_socratic_inquiry(
        "I would like to know the taiwanese product's revenue",
        api_key="AIzaSyTestMockKey12345"
    )
    assert session.is_out_of_domain is True
    assert session.needs_clarification is False
    assert "12 款歐洲堅果" in session.rejection_reason
    assert "dim_products 不含產地" in session.rejection_reason


def test_socratic_clarification_for_european_market_inquiry() -> None:
    """Verify natural language inquiry concerning European country revenue triggers geographic market question."""
    session = analyze_socratic_inquiry("i would like to know the european countries revenue")
    assert session.is_out_of_domain is False
    assert session.needs_clarification is True
    geo_q = next(q for q in session.questions if q.dimension_type == "geographic")
    assert "地理市場維度動態解析" in geo_q.title
    opt_values = [opt["value"] for opt in geo_q.options]
    assert "DE" in opt_values
    assert "AT" in opt_values
    assert "FR" in opt_values
    assert "ALL_EU" in opt_values


def test_dynamic_dbt_synthesis_german_market_revenue() -> None:
    """Verify selecting German market dynamically compiles and physical dry-runs mart_de_market_revenue."""
    decisions = {
        "temporal": "2026-08-03:2026-10-31",
        "geographic": "DE",
    }
    result = synthesize_dynamic_dbt_model("i would like to know the german product's revenue", decisions)
    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert len(result.data_preview) > 0
    assert "market_country" in result.data_preview.columns
    assert "gross_revenue_eur" in result.data_preview.columns
    assert (result.data_preview["market_country"] == "DE").all()
    assert "mart_de_market_revenue" in result.dbt_sql


def test_dynamic_dbt_synthesis_with_custom_fill_in() -> None:
    """Verify user can fill in custom criteria to override decisions and dynamically synthesize dbt model."""
    decisions = {
        "temporal": "custom:請鎖定2026年9月份促銷數據",
        "geographic": "custom:我想看奧地利市場 (AT)",
    }
    result = synthesize_dynamic_dbt_model("我想看促銷數據", decisions)
    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert "mart_at_market_revenue" in result.dbt_sql
    assert "2026-09-01" in result.dbt_sql
    assert "2026-09-30" in result.dbt_sql
    assert len(result.data_preview) > 0
    assert (result.data_preview["market_country"] == "AT").all()
    assert any("Custom Note" in trace["detail"] for trace in result.audit_trace)


def test_temporal_watermark_exceeded_triggers_socratic_clarification() -> None:
    """Verify asking for an out-of-watermark month (e.g. 12月, 4月, 6月) halts and asks Socratic question."""
    session = analyze_socratic_inquiry("請給我12月的營業銷售額")
    assert session.is_out_of_domain is False
    assert session.needs_clarification is True
    temp_q = next(q for q in session.questions if q.dimension_type == "temporal")
    assert "超出實體水浮標記" in temp_q.title
    assert "2026-10" in temp_q.explanation
    opt_values = [opt["value"] for opt in temp_q.options]
    assert any("2026-10-01" in v for v in opt_values)
    assert any("2026-09-01" in v for v in opt_values)


def test_catalog_query_intent_synthesizes_product_catalog() -> None:
    """Verify asking '我目前有多少產品' synthesizes mart_product_catalog with 12 real SKUs."""
    session = analyze_socratic_inquiry("我目前有多少產品")
    assert session.is_out_of_domain is False
    assert session.needs_clarification is False
    assert session.locked_decisions.get("grain") == "catalog_summary"

    result = synthesize_dynamic_dbt_model("我目前有多少產品", session.locked_decisions)
    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert result.spec_id == "SCHEMA-MART_PRODUCT_CATALOG"
    assert len(result.data_preview) == 12  # All 12 core catalog SKUs
    cols = list(result.data_preview.columns)
    assert "product_id" in cols
    assert "product_name" in cols
    assert "category_name" in cols
    assert "price_eur" in cols


def test_promotions_and_vouchers_intent_synthesizes_voucher_metrics() -> None:
    """Verify asking for '促銷訂單量' synthesizes mart_promotions_and_vouchers with voucher columns."""
    decisions = {
        "temporal": "2026-09-01:2026-09-30",
        "grain": "promotions_vouchers",
    }
    result = synthesize_dynamic_dbt_model("我想查看促銷訂單量", decisions)
    assert result.is_rejected is False
    assert result.dry_run_success is True
    assert result.spec_id == "SCHEMA-MART_PROMOTIONS_AND_VOUCHERS"
    assert "total_promotional_orders" in result.data_preview.columns
    assert "total_voucher_discount_eur" in result.data_preview.columns
    assert "market_country" in result.data_preview.columns
    assert len(result.data_preview) > 0
