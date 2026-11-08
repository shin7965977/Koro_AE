"""KoRo Domain Adapter for Lakehouse Cockpit Core.

Connects KoRo's Medallion datasets conforming to Ralph Kimball Dimensional Modeling,
semantic metric contracts, Looker LookML, and Conversational Analytics Copilot
to the generic Lakehouse Cockpit microkernel.
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
        return "Medallion Lakehouse · Kimball Dimensional Model"

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supports_spec_guidance(self) -> bool:
        return True

    @property
    def supports_ae_workflow(self) -> bool:
        return False

    @property
    def supports_looker(self) -> bool:
        return True

    @property
    def supports_schema_designer(self) -> bool:
        return True

    @property
    def supports_data_center(self) -> bool:
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
            "-- Query Silver Star Schema: High-return products by joining fct_order_items, fct_returns, and dim_products\n"
            "SELECT \n"
            "    p.product_id, \n"
            "    p.product_name, \n"
            "    p.packaging_size,\n"
            "    SUM(i.quantity_sold) AS units_sold,\n"
            "    COALESCE(SUM(r.returned_units), 0) AS units_returned,\n"
            "    ROUND(COALESCE(SUM(r.returned_units), 0) * 100.0 / NULLIF(SUM(i.quantity_sold), 0), 2) AS return_rate_pct\n"
            "FROM dim_products p\n"
            "JOIN fct_order_items i USING (product_id)\n"
            "LEFT JOIN fct_returns r USING (product_id)\n"
            "GROUP BY p.product_id, p.product_name, p.packaging_size\n"
            "ORDER BY return_rate_pct DESC\n"
            "LIMIT 10;"
        )

    @property
    def kpi_cards(self) -> list[KPICardSpec]:
        def calc_gross(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("fct_order_items", pd.DataFrame())
            val = float(df["line_gross_eur"].sum()) if not df.empty else 0.0
            return {
                "value": f"€{val:,.0f}",
                "status": "normal" if val >= 300000 else "warning",
                "caption": "Gross product sales before vouchers & refunds",
            }

        def calc_net(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("fct_order_items", pd.DataFrame())
            val = float(df["line_net_eur"].sum()) if not df.empty else 0.0
            return {
                "value": f"€{val:,.0f}",
                "status": "normal" if val >= 280000 else "warning",
                "caption": "Realized revenue after discounts & refunds",
            }

        def calc_aov(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df_ord = data.get("fct_orders", pd.DataFrame())
            if df_ord.empty:
                return {"value": "€0.00", "status": "warning", "caption": "No orders"}
            val = float(df_ord["total_net_eur"].sum()) / max(1, len(df_ord))
            return {
                "value": f"€{val:,.2f}",
                "status": "normal" if val >= 55.0 else "warning",
                "caption": f"Across {len(df_ord):,} completed orders",
            }

        def calc_return_rate(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df_items = data.get("fct_order_items", pd.DataFrame())
            df_ret = data.get("fct_returns", pd.DataFrame())
            total_sold = df_items["quantity_sold"].sum() if not df_items.empty else 0
            total_ret = df_ret["returned_units"].sum() if not df_ret.empty else 0
            if total_sold == 0:
                return {"value": "0.00%", "status": "normal", "caption": "No sales"}
            rate = float(total_ret * 100.0 / total_sold)
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
                metric_formula="SUM(fct_order_items.line_gross_eur)",
                target_rule=">= €300,000 / period",
                calculate=calc_gross,
                accent_color="#6366f1",
                formula_numerator=MetricComponent(
                    label="line_gross_eur",
                    role="Numerator",
                    description="Total item line purchase price before vouchers and refunds.",
                    description_zh="未扣除折扣與退款前的商品明細銷售總額。",
                ),
                formula_denominator=MetricComponent(
                    label="None",
                    role="Denominator",
                    description="Absolute monetary volume aggregation.",
                    description_zh="貨幣總量聚合指標。",
                ),
            ),
            KPICardSpec(
                key="net_revenue",
                title_en="Net Revenue",
                title_zh="實質淨營收 (Net Revenue)",
                metric_formula="SUM(fct_order_items.line_net_eur)",
                target_rule=">= €280,000 / period",
                calculate=calc_net,
                accent_color="#10b981",
                formula_numerator=MetricComponent(
                    label="line_net_eur",
                    role="Numerator",
                    description="Realized revenue after subtracting promotional vouchers and customer refunds.",
                    description_zh="扣除折價券與顧客退款後之真實入帳淨營業額。",
                ),
                formula_denominator=MetricComponent(
                    label="None",
                    role="Denominator",
                    description="Absolute monetary volume aggregation.",
                    description_zh="貨幣總量聚合指標。",
                ),
            ),
            KPICardSpec(
                key="aov",
                title_en="Average Order Value (AOV)",
                title_zh="平均客單價 (AOV)",
                metric_formula="total_net_eur / total_orders",
                target_rule=">= €55.00 / order",
                calculate=calc_aov,
                accent_color="#3b82f6",
                formula_numerator=MetricComponent(
                    label="total_net_eur",
                    role="Numerator",
                    description="Total net realized revenue across all orders in fct_orders.",
                    description_zh="fct_orders 中全數訂單之淨營收加總。",
                ),
                formula_denominator=MetricComponent(
                    label="order_id_count",
                    role="Denominator",
                    description="Total count of distinct valid customer orders in fct_orders.",
                    description_zh="fct_orders 中獨立有效顧客訂單總筆數。",
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
                    description="Count of items returned in fct_returns due to defect or complaint.",
                    description_zh="fct_returns 中因瑕疵或客訴而退回之商品總件數。",
                ),
                formula_denominator=MetricComponent(
                    label="quantity_sold",
                    role="Denominator",
                    description="Total quantity of product units sold recorded in fct_order_items.",
                    description_zh="fct_order_items 中記錄之商品總銷售件數。",
                ),
            ),
        ]

    @property
    def medallion_layers(self) -> dict[str, Any]:
        def render_gold_dynamic_mart(
            data_dict: dict[str, pd.DataFrame],
            is_en: bool,
            adapter: Any,
            start_date: date | None = None,
            end_date: date | None = None,
        ) -> None:
            # Dynamically compute Gold Mart view from Silver facts & dimensions on the fly
            df_items = data_dict.get("fct_order_items", pd.DataFrame())
            df_prod = data_dict.get("dim_products", pd.DataFrame())
            st.caption(
                "⚖️ **Kimball Gold Mart**: Dynamically aggregated from Silver `fct_order_items` & `dim_products`."
            )
            if not df_items.empty and not df_prod.empty:
                merged = df_items.groupby("product_id", as_index=False).agg(
                    total_sold_units=("quantity_sold", "sum"),
                    net_revenue_eur=("line_net_eur", "sum"),
                )
                gold_df = pd.merge(df_prod, merged, on="product_id", how="left")
                fig = px.bar(
                    gold_df.sort_values("net_revenue_eur", ascending=True),
                    x="net_revenue_eur",
                    y="product_name",
                    color="category_name",
                    orientation="h",
                    title="Gold Mart Dynamic View: Net Revenue by SKU & Category (EUR)",
                    labels={"net_revenue_eur": "Net Revenue (€)", "product_name": "Product"},
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                gold_df = pd.DataFrame()

            render_sql_snippet_module(
                module_id="gold_dynamic_mart",
                title_en="Gold View Compiled via dbt (`koro_marts.mart_product_performance`)",
                source_table_label=f"{self.project_id}.koro_marts.mart_product_performance",
                sql_template=(
                    "SELECT \n"
                    "    p.product_id, p.product_name, p.category_name, p.packaging_size,\n"
                    "    SUM(i.quantity_sold) AS total_sold_units,\n"
                    "    ROUND(SUM(i.line_net_eur), 2) AS net_revenue_eur\n"
                    "FROM `koro_silver.dim_products` p\n"
                    "JOIN `koro_silver.fct_order_items` i USING (product_id)\n"
                    "WHERE i.order_date BETWEEN '{start_str}' AND '{end_str}'\n"
                    "GROUP BY p.product_id, p.product_name, p.category_name, p.packaging_size\n"
                    "ORDER BY net_revenue_eur DESC;"
                ),
                df_preview=gold_df,
                start_date=start_date,
                end_date=end_date,
                is_en=is_en,
            )

        def render_silver_star_schema(
            data_dict: dict[str, pd.DataFrame],
            is_en: bool,
            adapter: Any,
            start_date: date | None = None,
            end_date: date | None = None,
        ) -> None:
            st.markdown(
                "#### 🥈 Silver Layer: Kimball Conformed Star Schema"
                if is_en
                else "#### 🥈 Silver 銀牌層：Kimball 標準星狀綱要（Facts & Dimensions）"
            )
            st.caption(
                "Conformed dimensions and granular transactional facts cleansed from Bronze raw data."
                if is_en
                else "由 Bronze 銅牌原始數據清洗、去重並正規化而成的標準事實表與維度表。"
            )

            schema_tab1, schema_tab2, schema_tab3, schema_tab4 = st.tabs(
                [
                    "📄 fct_order_items (Line Grain)",
                    "📦 fct_orders (Order Grain)",
                    "🔄 fct_returns (Event Grain)",
                    "🏷️ dim_products & categories",
                ]
            )
            with schema_tab1:
                df_items = data_dict.get("fct_order_items", pd.DataFrame())
                st.dataframe(df_items.head(25), use_container_width=True)
            with schema_tab2:
                df_ord = data_dict.get("fct_orders", pd.DataFrame())
                st.dataframe(df_ord.head(25), use_container_width=True)
            with schema_tab3:
                df_ret = data_dict.get("fct_returns", pd.DataFrame())
                st.dataframe(df_ret.head(25), use_container_width=True)
            with schema_tab4:
                df_p = data_dict.get("dim_products", pd.DataFrame())
                st.dataframe(df_p, use_container_width=True)

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
                        tab_id="gold_dynamic_mart",
                        title_en="🥇 Dynamic Gold Mart (Compiled from Silver)",
                        title_zh="🥇 金牌動態寬表（由 Silver 即時編譯）",
                        render_content=render_gold_dynamic_mart,
                    )
                ]
            },
            "silver": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="silver_star_schema",
                        title_en="🥈 Kimball Star Schema (Facts & Dimensions)",
                        title_zh="🥈 Kimball 星狀綱要（事實表與維度表）",
                        render_content=render_silver_star_schema,
                    )
                ]
            },
            "bronze": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="bronze_shopware",
                        title_en="🥉 Raw Ingested Orders & Catalog",
                        title_zh="🥉 原始攝取訂單與目錄 (Bronze)",
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
            "You are the KoRo Analytics Engineering Copilot. Help stakeholders explore "
            "Kimball Star Schema facts and dimensions (dim_products, fct_order_items, fct_returns), "
            "understand governed metric definitions, and diagnose business anomalies."
        )

    @property
    def default_system_prompt_zh(self) -> str:
        return (
            "您是 KoRo 分析工程協作助理。協助主管理解 Kimball 星狀模型事實表與維度表"
            "（dim_products, fct_order_items, fct_returns）、指標定義並診斷營運異常。"
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

    @property
    def supports_ae_workflow(self) -> bool:
        return False

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
