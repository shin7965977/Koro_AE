"""Unit tests for lakehouse-cockpit-core microkernel contracts and backward compatibility."""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import pytest

from cockpit_core.adapter import (
    AnalyticalSpecContract,
    BaseCockpitAdapter,
    KPICardSpec,
    OnDemandInsightResult,
)
from dashboard.app import main as dashboard_main


class LegacyMinimalAdapter(BaseCockpitAdapter):
    """Minimal legacy adapter implementing only the original contract methods."""

    @property
    def project_id(self) -> str:
        return "legacy-proj"

    @property
    def brand_title(self) -> str:
        return "Legacy Cockpit"

    @property
    def brand_icon(self) -> str:
        return "📊"

    @property
    def brand_badge_text(self) -> str:
        return "Legacy"

    @property
    def kpi_cards(self) -> list[KPICardSpec]:
        return []

    @property
    def medallion_layers(self) -> dict[str, Any]:
        return {"gold": {"tabs": []}, "silver": {"tabs": []}, "bronze": {"tabs": []}}

    def load_domain_data(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, pd.DataFrame]:
        return {}

    def get_fastmcp_tools(self) -> list:
        return []

    @property
    def default_system_prompt_en(self) -> str:
        return "You are an advisor."


def test_legacy_adapter_backward_compatibility() -> None:
    """Verify existing adapters instantiate without needing to implement new spec hooks."""
    adapter = LegacyMinimalAdapter()
    assert adapter.project_id == "legacy-proj"
    assert adapter.supports_spec_guidance is False
    assert adapter.compile_spec_to_insight(None, {}) is None


def test_analytical_spec_contract_and_on_demand_insight_result_shape() -> None:
    """Verify AnalyticalSpecContract and OnDemandInsightResult hold required traceability fields."""
    spec = AnalyticalSpecContract(
        spec_id="SPEC-TEST-001",
        scenario_key="bulk_returns",
        business_question="Analyze 1kg nut packaging return rate and defect causes",
        target_layer="gold",
        target_mart="mart_product_performance",
        metrics=[
            {
                "name": "return_rate",
                "formula": "SUM(returned_units) / SUM(sold_units)",
                "source": "semantic/business_rules.yaml#return_rate",
            }
        ],
        dimensions=["packaging_size", "return_reason"],
        filters={"category_name": "Nuts & Butters", "time_window": "Last 90 Days"},
        chart_recommendation="Grouped Bar Chart",
        governance_checks={
            "contains_pii": False,
            "finops_estimate": "4.2 MB (< 100 MB Guard)",
            "dbt_tested": True,
        },
    )
    assert spec.spec_id == "SPEC-TEST-001"
    assert spec.governance_checks["contains_pii"] is False

    df_snip = pd.DataFrame({"packaging_size": ["1kg", "500g"], "return_rate_pct": [5.2, 1.8]})
    fig = go.Figure()
    insight = OnDemandInsightResult(
        spec_id=spec.spec_id,
        title="1kg Bulk Packaging Return Diagnosis",
        executive_takeaway="1kg Cashews exhibit a 5.2% return rate, 78% caused by vacuum seal defects.",
        figure=fig,
        executed_sql="SELECT packaging_size, return_rate_pct FROM mart_product_performance",
        source_table_label="main_gold.mart_product_performance",
        lineage_markdown="### Metric Lineage\n- **return_rate**: `SUM(returned_units) / SUM(sold_units)`",
        df_snippet=df_snip,
        governance_badges=["FinOps: 4.2 MB / 100 MB", "GDPR: No PII Exposed", "dbt Tests: PASS"],
    )
    assert insight.spec_id == "SPEC-TEST-001"
    assert len(insight.df_snippet) == 2
    assert "5.2%" in insight.executive_takeaway


def test_sql_sandbox_executes_synthesized_dbt_jinja_on_koro_dummy_data() -> None:
    """Verify SQL sandbox automatically compiles dbt Jinja ref() and executes on real Koro domain data."""
    from koro_adapter import KoroAdapter

    adapter = KoroAdapter()
    data = adapter.load_domain_data()

    query = """
    SELECT
        p.category_name,
        COUNT(DISTINCT i.order_id) AS total_orders,
        SUM(i.quantity_sold) AS total_units_sold,
        ROUND(SUM(i.line_gross_eur), 2) AS gross_revenue_eur,
        ROUND(SUM(i.line_net_eur), 2) AS net_revenue_eur,
        ROUND(SUM(i.cogs_eur), 2) AS total_cogs_eur
    FROM {{ ref('fct_order_items') }} i
    JOIN {{ ref('dim_products') }} p USING (product_id)
    WHERE i.order_date BETWEEN '2026-10-01' AND '2026-10-31'
    GROUP BY p.category_name
    ORDER BY net_revenue_eur DESC;
    """
    result_df = adapter.execute_custom_sql(query, data)
    assert not result_df.empty
    assert "category_name" in result_df.columns
    assert "net_revenue_eur" in result_df.columns
    assert len(result_df) > 0

    # Verify CSV exportable format
    csv_bytes = result_df.to_csv(index=False).encode("utf-8")
    assert len(csv_bytes) > 0
