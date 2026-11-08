"""KoRo Domain Adapter for Lakehouse Cockpit Core.

Connects KoRo's Medallion datasets, semantic metric contracts, Looker LookML,
and Conversational Analytics Copilot to the generic Lakehouse Cockpit microkernel.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from cockpit_core.adapter import (
    AnalyticalSpecContract,
    BaseCockpitAdapter,
    KPICardSpec,
    MedallionTabSpec,
    MetricComponent,
    OnDemandInsightResult,
)
from cockpit_core.components.sql_expander import render_sql_snippet_module

from ingestion.synthetic_medallion import build_koro_medallion_data


class KoroAdapter(BaseCockpitAdapter):
    """Domain Adapter for KoRo Analytics Engineering & AI-Ready Data Platform POC."""

    @property
    def project_id(self) -> str:
        return os.getenv("GCP_PROJECT_ID", "koro-analytics-poc")

    @property
    def brand_title(self) -> str:
        return "KoRo Analytics & AI Semantic Cockpit"

    @property
    def brand_icon(self) -> str:
        return "🌰"

    @property
    def brand_badge_text(self) -> str:
        return "Medallion Lakehouse · Semantic Guarded"

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supports_spec_guidance(self) -> bool:
        return True

    @property
    def supports_looker(self) -> bool:
        return True

    @property
    def looker_embed_url(self) -> str:
        return os.getenv("LOOKER_EMBED_URL", "")

    @property
    def lookml_view_definition(self) -> str:
        lookml_path = os.path.join(_ROOT_DIR, "warehouse", "lookml", "mart_product_performance.view.lkml")
        if os.path.exists(lookml_path):
            with open(lookml_path, encoding="utf-8") as f:
                return f.read()
        return "view: mart_product_performance { ... }"

    @property
    def default_sandbox_sql(self) -> str:
        return (
            "-- Audit KoRo Product Return Rates & Defect Causes\n"
            "SELECT product_id, product_name, packaging_size, sold_units, returned_units, return_rate_pct\n"
            "FROM mart_product_performance\n"
            "ORDER BY return_rate_pct DESC\n"
            "LIMIT 10;"
        )

    @property
    def kpi_cards(self) -> list[KPICardSpec]:
        def calc_gross(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("mart_product_performance", pd.DataFrame())
            val = float(df["gross_revenue_eur"].sum()) if not df.empty else 0.0
            return {
                "value": f"€{val:,.0f}",
                "status": "normal" if val >= 300000 else "warning",
                "caption": "Gross product sales before vouchers & refunds",
            }

        def calc_net(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("mart_product_performance", pd.DataFrame())
            val = float(df["net_revenue_eur"].sum()) if not df.empty else 0.0
            return {
                "value": f"€{val:,.0f}",
                "status": "normal" if val >= 280000 else "warning",
                "caption": "Realized revenue after discounts & refunds",
            }

        def calc_aov(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df_ord = data.get("raw_shopware_orders", pd.DataFrame())
            if df_ord.empty:
                return {"value": "€0.00", "status": "warning", "caption": "No orders"}
            val = float(df_ord["order_net_eur"].sum()) / max(1, len(df_ord))
            return {
                "value": f"€{val:,.2f}",
                "status": "normal" if val >= 55.0 else "warning",
                "caption": f"Across {len(df_ord):,} Shopware orders",
            }

        def calc_return_rate(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("mart_product_performance", pd.DataFrame())
            if df.empty or df["sold_units"].sum() == 0:
                return {"value": "0.00%", "status": "normal", "caption": "No sales"}
            rate = float(df["returned_units"].sum() * 100.0 / df["sold_units"].sum())
            return {
                "value": f"{rate:.2f}%",
                "status": "normal" if rate <= 2.50 else "warning",
                "caption": "⚠️ 1kg Cashews outlier at 5.20% (Vacuum seal)",
            }

        return [
            KPICardSpec(
                key="gross_revenue",
                title_en="Gross Revenue",
                title_zh="營業總額 (Gross Revenue)",
                metric_formula="gross_sales / orders_count",
                target_rule=">= €300,000 / period",
                calculate=calc_gross,
                accent_color="#6366f1",
                formula_numerator=MetricComponent(
                    label="gross_sales",
                    role="Numerator",
                    description="Total product sales before vouchers, discounts and refunds.",
                    description_zh="未扣除折扣與退款前的商品銷售總額。",
                ),
                formula_denominator=MetricComponent(
                    label="order_lines",
                    role="Denominator",
                    description="Total completed line item purchases recorded in Shopware 6.",
                    description_zh="Shopware 6 中記錄的總完成購買明細筆數。",
                ),
            ),
            KPICardSpec(
                key="net_revenue",
                title_en="Net Revenue",
                title_zh="實質淨營收 (Net Revenue)",
                metric_formula="net_sales / period_days",
                target_rule=">= €280,000 / period",
                calculate=calc_net,
                accent_color="#10b981",
                formula_numerator=MetricComponent(
                    label="net_sales",
                    role="Numerator",
                    description="Realized revenue after subtracting promotional vouchers and refunded returns.",
                    description_zh="扣除促銷折價券與退貨退款後的實質入帳淨營收（財務與行銷統一對齊口徑）。",
                ),
                formula_denominator=MetricComponent(
                    label="period_days",
                    role="Denominator",
                    description="Standard accounting reporting timeframe in calendar days.",
                    description_zh="日曆天數標準會計報表統計期間。",
                ),
            ),
            KPICardSpec(
                key="aov",
                title_en="Avg Order Value (AOV)",
                title_zh="平均客單價 (AOV)",
                metric_formula="net_order_val / orders_count",
                target_rule=">= €55.00",
                calculate=calc_aov,
                accent_color="#3b82f6",
                formula_numerator=MetricComponent(
                    label="net_order_val",
                    role="Numerator",
                    description="Cumulative net order value from valid completed cart checkouts.",
                    description_zh="有效完成結帳購物車之累積淨訂單金額。",
                ),
                formula_denominator=MetricComponent(
                    label="orders_count",
                    role="Denominator",
                    description="Total count of distinct valid customer orders.",
                    description_zh="獨立有效顧客訂單總筆數。",
                ),
            ),
            KPICardSpec(
                key="return_rate",
                title_en="Unit Return Rate",
                title_zh="商品退貨率 (Return Rate)",
                metric_formula="returned_units / sold_units",
                target_rule="<= 2.50%",
                calculate=calc_return_rate,
                accent_color="#f59e0b",
                formula_numerator=MetricComponent(
                    label="returned_units",
                    role="Numerator",
                    description="Count of items returned by customers due to packaging defect or claim.",
                    description_zh="顧客因包裝破損或瑕疵申訴而退回之商品件數。",
                ),
                formula_denominator=MetricComponent(
                    label="sold_units",
                    role="Denominator",
                    description="Total quantity of product units shipped and delivered to customers.",
                    description_zh="成功發貨送達顧客之商品總售出件數。",
                ),
            ),
        ]

    @property
    def medallion_layers(self) -> dict[str, Any]:
        def render_gold_product_mart(
            data_dict: dict[str, pd.DataFrame],
            is_en: bool,
            adapter: Any,
            start_date: date | None = None,
            end_date: date | None = None,
        ) -> None:
            df = data_dict.get("mart_product_performance", pd.DataFrame())
            st.caption(
                "⚖️ **Data Disclaimer**: Public KoRo catalog structure paired with synthetic transactional metrics."
            )
            if not df.empty:
                fig = px.bar(
                    df.sort_values("net_revenue_eur", ascending=True),
                    x="net_revenue_eur",
                    y="product_name",
                    color="category_name",
                    orientation="h",
                    title="Gold Mart: Net Revenue by SKU & Category (EUR)",
                    labels={"net_revenue_eur": "Net Revenue (€)", "product_name": "Product"},
                )
                st.plotly_chart(fig, use_container_width=True)
            render_sql_snippet_module(
                module_id="gold_prod_mart",
                title_en="Gold Mart SQL & Aligned Table (`koro_marts.mart_product_performance`)",
                source_table_label=f"{self.project_id}.koro_marts.mart_product_performance",
                sql_template=(
                    "SELECT product_id, product_name, category_name, packaging_size,\n"
                    "       sold_units, returned_units, return_rate_pct, net_revenue_eur, net_margin_pct\n"
                    "FROM `koro_marts.mart_product_performance`\n"
                    "WHERE order_date BETWEEN '{start_str}' AND '{end_str}'\n"
                    "ORDER BY net_revenue_eur DESC;"
                ),
                df_preview=df,
                start_date=start_date,
                end_date=end_date,
                is_en=is_en,
            )

        def render_silver_returns(
            data_dict: dict[str, pd.DataFrame],
            is_en: bool,
            adapter: Any,
            start_date: date | None = None,
            end_date: date | None = None,
        ) -> None:
            df = data_dict.get("int_returns_enriched", pd.DataFrame())
            if not df.empty:
                agg = (
                    df.groupby(["packaging_size", "return_reason"], as_index=False)[
                        "returned_units"
                    ]
                    .sum()
                )
                fig = px.bar(
                    agg,
                    x="packaging_size",
                    y="returned_units",
                    color="return_reason",
                    barmode="group",
                    title="Silver Layer: Returned Units by Packaging Size & Root Cause",
                )
                st.plotly_chart(fig, use_container_width=True)
            render_sql_snippet_module(
                module_id="silver_returns",
                title_en="Silver Enriched Returns (`koro_staging.int_returns_enriched`)",
                source_table_label=f"{self.project_id}.koro_staging.int_returns_enriched",
                sql_template=(
                    "SELECT return_id, product_id, product_name, packaging_size,\n"
                    "       return_reason, returned_units, refunded_eur\n"
                    "FROM `koro_staging.int_returns_enriched`\n"
                    "WHERE return_date BETWEEN '{start_str}' AND '{end_str}';"
                ),
                df_preview=df.head(25),
                start_date=start_date,
                end_date=end_date,
                is_en=is_en,
            )

        def render_bronze_orders(
            data_dict: dict[str, pd.DataFrame],
            is_en: bool,
            adapter: Any,
            start_date: date | None = None,
            end_date: date | None = None,
        ) -> None:
            df = data_dict.get("raw_shopware_orders", pd.DataFrame())
            render_sql_snippet_module(
                module_id="bronze_orders",
                title_en="Bronze Shopware 6 Orders (`koro_raw.raw_shopware_orders`)",
                source_table_label=f"{self.project_id}.koro_raw.raw_shopware_orders",
                sql_template=(
                    "SELECT order_id, order_date, market_country, customer_segment,\n"
                    "       order_gross_eur, discount_eur, order_net_eur\n"
                    "FROM `koro_raw.raw_shopware_orders`\n"
                    "WHERE order_date BETWEEN '{start_str}' AND '{end_str}'\n"
                    "LIMIT 25;"
                ),
                df_preview=df.head(25),
                start_date=start_date,
                end_date=end_date,
                is_en=is_en,
            )

        return {
            "gold": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="gold_sku_perf",
                        title_en="🥇 SKU & Category Performance Mart",
                        title_zh="🥇 商品與品類表現寬表 (Gold Mart)",
                        render_content=render_gold_product_mart,
                    )
                ]
            },
            "silver": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="silver_returns",
                        title_en="🥈 Enriched Returns & Packaging Quality",
                        title_zh="🥈 退貨原因與包裝品質明細 (Silver)",
                        render_content=render_silver_returns,
                    )
                ]
            },
            "bronze": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="bronze_shopware",
                        title_en="🥉 Raw Shopware 6 Orders",
                        title_zh="🥉 Shopware 6 原始訂單紀錄 (Bronze)",
                        render_content=render_bronze_orders,
                    )
                ]
            },
        }

    def load_domain_data(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, pd.DataFrame]:
        return build_koro_medallion_data(start_date=start_date, end_date=end_date)

    @property
    def default_system_prompt_en(self) -> str:
        return (
            "You are the KoRo Analytics Engineering Copilot. Help stakeholders understand "
            "product catalog data, available metrics, and diagnose business anomalies."
        )

    @property
    def default_system_prompt_zh(self) -> str:
        return (
            "您是 KoRo 分析工程協作助理。協助主管理解商品目錄、指標定義並診斷營運異常。"
        )

    @property
    def quick_diagnosis_questions_en(self) -> list[str]:
        return [
            "What data and catalog categories are currently available?",
            "Which product categories show the highest margin dilution after discounts?",
        ]

    @property
    def quick_diagnosis_questions_zh(self) -> list[str]:
        return [
            "目前有哪些數據與品類目錄？",
            "哪一個品類在折價促銷後毛利稀釋最嚴重？",
        ]

    @property
    def supports_spec_guidance(self) -> bool:
        return True

    def handle_spec_inquiry_turn(
        self,
        user_query: str,
        chat_history: list[dict[str, str]] | None = None,
        data_dict: dict[str, pd.DataFrame] | None = None,
        is_en: bool = True,
        current_round: int = 0,
        session_context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from ai.spec_guide import process_conversational_copilot_turn

        api_key: str = kwargs.get("api_key", "")
        return process_conversational_copilot_turn(
            user_query=user_query,
            chat_history=chat_history or [],
            data_dict=data_dict or {},
            is_en=is_en,
            current_round=current_round,
            session_context=session_context or {},
            api_key=api_key,
        )

    def compile_spec_to_insight(
        self,
        spec_contract: AnalyticalSpecContract | None,
        data_dict: dict[str, pd.DataFrame],
        start_date: date | None = None,
        end_date: date | None = None,
        is_en: bool = True,
    ) -> OnDemandInsightResult | None:
        if spec_contract is None:
            return None
        from ai.spec_guide import compile_analytical_spec

        return compile_analytical_spec(
            spec_contract=spec_contract,
            data_dict=data_dict,
            start_date=start_date,
            end_date=end_date,
            project_id=self.project_id,
            is_en=is_en,
        )
