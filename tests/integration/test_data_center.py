"""Integration tests for Data Center (dbt Docs & Elementary Observability)."""

import pytest
from pathlib import Path
from cockpit_core.reports.elementary_generator import get_elementary_report_html, export_elementary_report_file
from cockpit_core.reports.dbt_docs_generator import get_dbt_docs_html, export_dbt_docs_file
from koro_adapter import KoroAdapter


def test_elementary_report_contains_official_observability_elements(tmp_path: Path):
    """Verify Elementary report contains essential dashboard and anomaly telemetry elements."""
    html = get_elementary_report_html()
    
    # Check KPI Donut & Telemetry titles
    assert "Test results breakdown" in html
    assert "Tables health" in html
    assert "Monitored tables" in html
    
    # Check Anomaly Cards
    assert "Freshness" in html
    assert "Volume" in html
    assert "Schema changes" in html
    assert "dbt tests" in html
    assert "Anomalies Detected" in html
    
    # Check Navigation
    assert "Dashboard" in html
    assert "Lineage" in html
    assert "Model Duration" in html
    assert "koro_lakehouse_prod" in html

    # Test file export
    out_file = tmp_path / "reports" / "elementary_report.html"
    res_path = export_elementary_report_file(out_file)
    assert res_path.exists()
    assert res_path.stat().st_size > 1000


def test_dbt_docs_contains_catalog_and_lineage_elements(tmp_path: Path):
    """Verify dbt docs contains catalog hierarchy, Kimball Star Schema, and DAG lineage."""
    html = get_dbt_docs_html()
    
    # Check project structure and models
    assert "dbt docs" in html
    assert "fct_order_items" in html
    assert "fct_orders" in html
    assert "fct_returns" in html
    assert "dim_products" in html
    assert "dim_customers" in html
    
    # Check Data Contract & Tests
    assert "Columns & Data Contract" in html
    assert "unique" in html
    assert "not_null" in html
    assert "Structural DAG Lineage" in html

    # Test file export
    out_file = tmp_path / "reports" / "dbt_docs.html"
    res_path = export_dbt_docs_file(out_file)
    assert res_path.exists()
    assert res_path.stat().st_size > 1000


def test_koro_adapter_supports_data_center():
    """Verify KoroAdapter has data center enabled."""
    adapter = KoroAdapter()
    assert getattr(adapter, "supports_data_center", False) is True
    assert getattr(adapter, "supports_schema_designer", False) is True
