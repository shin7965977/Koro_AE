"""KoRo Domain Adapter for Lakehouse Cockpit Core.

Connects KoRo's Medallion datasets, semantic metric contracts, and Socratic Spec
Guidance Engine to the generic Lakehouse Cockpit microkernel.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure project root is on sys.path so cockpit_core package is importable
_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from cockpit_core.adapter import (
    AnalyticalSpecContract,
    BaseCockpitAdapter,
    KPICardSpec,
    MedallionTabSpec,
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
        return "Medallion Lakehouse · Semantic Guarded AI"

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supports_spec_guidance(self) -> bool:
        return True

    @property
    def kpi_cards(self) -> list[KPICardSpec]:
        def calc_gross(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("mart_product_performance", pd.DataFrame())
            val = float(df["gross_revenue_eur"].sum()) if not df.empty else 0.0
            return {
                "value": f"€{val:,.0f}",
                "status": "normal" if val >= 400000 else "warning",
                "caption": "Gross product sales before vouchers & returns",
            }

        def calc_net(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df = data.get("mart_product_performance", pd.DataFrame())
            val = float(df["net_revenue_eur"].sum()) if not df.empty else 0.0
            return {
                "value": f"€{val:,.0f}",
                "status": "normal" if val >= 350000 else "warning",
                "caption": "Realized revenue after discounts & refunds",
            }

        def calc_aov(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
            df_ord = data.get("raw_shopware_orders", pd.DataFrame())
            if df_ord.empty:
                return {"value": "€0.00", "status": "warning", "caption": "No orders"}
            val = float(df_ord["order_net_eur"].sum()) / max(1, len(df_ord))
            return {
                "value": f"€{val:,.2f}",
                "status": "normal" if val >= 58.0 else "warning",
                "caption": f"Across {len(df_ord):,} valid Shopware orders",
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
                metric_formula="SUM(gross_revenue_eur)",
                target_rule=">= €450,000 / quarter",
                calculate=calc_gross,
                accent_color="#6366f1",
            ),
            KPICardSpec(
                key="net_revenue",
                title_en="Net Revenue",
                title_zh="實質淨營收 (Net Revenue)",
                metric_formula="SUM(gross_revenue_eur - discount_eur - refunded_eur)",
                target_rule=">= €400,000 / quarter",
                calculate=calc_net,
                accent_color="#10b981",
            ),
            KPICardSpec(
                key="aov",
                title_en="Average Order Value (AOV)",
                title_zh="平均客單價 (AOV)",
                metric_formula="SUM(order_net_eur) / COUNT(DISTINCT order_id)",
                target_rule=">= €58.00",
                calculate=calc_aov,
                accent_color="#3b82f6",
            ),
            KPICardSpec(
                key="return_rate",
                title_en="Unit Return Rate",
                title_zh="商品退貨率 (Return Rate)",
                metric_formula="SUM(returned_units) / SUM(sold_units)",
                target_rule="<= 2.50%",
                calculate=calc_return_rate,
                accent_color="#f59e0b",
            ),
        ]

    @property
    def medallion_layers(self) -> dict[str, Any]:
        def render_gold_product_mart(
            data_dict: dict[str, pd.DataFrame], is_en: bool, adapter: Any
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
                is_en=is_en,
            )

        def render_silver_returns(
            data_dict: dict[str, pd.DataFrame], is_en: bool, adapter: Any
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
                is_en=is_en,
            )

        def render_bronze_orders(
            data_dict: dict[str, pd.DataFrame], is_en: bool, adapter: Any
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
                is_en=is_en,
            )

        def render_looker_embedded_view(
            data_dict: dict[str, pd.DataFrame], is_en: bool, adapter: Any
        ) -> None:
            import streamlit.components.v1 as components

            st.markdown(
                "### 📊 Looker Enterprise Embedded View"
                if is_en
                else "### 📊 Looker 企業級嵌入式儀表板"
            )
            st.caption(
                "🌐 **Unified Semantic Layer**: Looker directly models BigQuery Gold Marts via **LookML**, providing a single source of truth for both traditional BI and AI applications."
                if is_en
                else "🌐 **全公司統一語意層**：Looker 透過 **LookML** 直接對接 BigQuery 金牌層，為傳統 BI 報表與 AI 應用提供統一的商業指標口徑。"
            )

            # Option to load a live Looker / Looker Studio URL
            default_looker_url = os.getenv("LOOKER_EMBED_URL", "")
            looker_url = st.text_input(
                "Looker Embed URL (Optional — Paste your Looker / Looker Studio Dashboard link):"
                if is_en
                else "Looker 嵌入網址（選填 — 可貼上您的 Looker 或 Looker Studio 報表連結）：",
                value=default_looker_url,
                placeholder="https://lookerstudio.google.com/embed/reporting/...",
                help="Supports Looker Signed SSO Embed or Looker Studio Public Embed URLs",
            )

            if looker_url.strip():
                st.info(f"🔗 Embedding Looker dashboard from `{looker_url.strip()}`...")
                components.iframe(src=looker_url.strip(), height=750, scrolling=True)
            else:
                # High-fidelity Looker Semantic View with LookML Explorer
                l_col1, l_col2 = st.columns([6, 4])
                with l_col1:
                    st.markdown(
                        "#### 🏛️ Looker Semantic View: `mart_product_performance`"
                        if is_en
                        else "#### 🏛️ Looker 語意模型視圖：`mart_product_performance`"
                    )
                    df = data_dict.get("mart_product_performance", pd.DataFrame())
                    if not df.empty:
                        # Emulate Looker tabular visualization with formatted numbers
                        looker_table = df[[
                            "product_name",
                            "category_name",
                            "packaging_size",
                            "sold_units",
                            "returned_units",
                            "return_rate_pct",
                            "net_revenue_eur",
                            "net_margin_pct",
                        ]].copy()
                        looker_table.columns = [
                            "Product Name",
                            "Category",
                            "Packaging Size",
                            "Sold Units",
                            "Returned Units",
                            "Return Rate (%)",
                            "Net Revenue (€)",
                            "Net Margin (%)",
                        ]
                        st.dataframe(looker_table, use_container_width=True, height=380)

                with l_col2:
                    st.markdown(
                        "#### 📜 LookML Model Definition"
                        if is_en
                        else "#### 📜 LookML 語意模型原始碼"
                    )
                    lookml_path = os.path.join(
                        os.path.dirname(__file__),
                        "warehouse",
                        "lookml",
                        "mart_product_performance.view.lkml",
                    )
                    if os.path.exists(lookml_path):
                        with open(lookml_path, encoding="utf-8") as f:
                            lookml_content = f.read()
                        st.code(lookml_content, language="yaml")
                    else:
                        st.code("view: mart_product_performance { ... }", language="yaml")

        return {
            "gold": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="gold_sku_perf",
                        title_en="🥇 SKU & Category Performance Mart",
                        title_zh="🥇 商品與品類表現寬表 (Gold Mart)",
                        render_content=render_gold_product_mart,
                    ),
                    MedallionTabSpec(
                        tab_id="gold_looker_embed",
                        title_en="📊 Looker Enterprise View",
                        title_zh="📊 Looker 企業級嵌入視圖",
                        render_content=render_looker_embedded_view,
                    ),
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

    def get_fastmcp_tools(self) -> list[Callable]:
        def inspect_1kg_return_anomaly() -> dict[str, Any]:
            """Return summary metrics for 1kg bulk packaging return rates."""
            data = self.load_domain_data()
            df = data["mart_product_performance"]
            cashew = df[df["product_id"] == "KORO-NUT-001"].iloc[0]
            return {
                "product_id": "KORO-NUT-001",
                "return_rate_pct": float(cashew["return_rate_pct"]),
                "primary_cause": "Vacuum Packaging Defect (78%)",
            }

        return [inspect_1kg_return_anomaly]

    @property
    def default_system_prompt_en(self) -> str:
        return (
            "You are the KoRo Senior Analytics Engineering & Semantic Copilot. "
            "Guide stakeholders through a 2-round Socratic specification flow before "
            "compiling governed BigQuery/DuckDB SQL against Gold Marts."
        )

    @property
    def default_system_prompt_zh(self) -> str:
        return (
            "您是 KoRo 資深分析工程與語意引導助理。"
            "請透過 2 輪蘇格拉底式提問協助業務主管鎖定指標規格，再編譯為金牌層合規 SQL 與可追蹤圖表。"
        )

    @property
    def quick_diagnosis_questions_en(self) -> list[str]:
        return [
            "🌰 1kg Bulk Packaging Return Diagnosis",
            "💰 Category Net Margin & Discount Impact",
            "📦 Inventory Availability & Stockout Risk",
        ]

    @property
    def quick_diagnosis_questions_zh(self) -> list[str]:
        return [
            "🌰 堅果 1kg 大包裝退貨率異常歸因",
            "💰 品類淨毛利率與促銷折扣影響排行",
            "📦 商品庫存可用率與缺貨風險診斷",
        ]

    def handle_spec_inquiry_turn(
        self,
        user_query: str,
        current_round: int,
        session_context: dict[str, Any] | None = None,
        is_en: bool = True,
    ) -> dict[str, Any]:
        from ai.spec_guide import process_socratic_turn

        return process_socratic_turn(
            user_query=user_query,
            current_round=current_round,
            session_context=session_context,
            is_en=is_en,
        )

    def compile_spec_to_insight(
        self,
        spec_contract: AnalyticalSpecContract | None,
        data_dict: dict[str, pd.DataFrame],
        is_en: bool = True,
    ) -> OnDemandInsightResult | None:
        if spec_contract is None:
            return None
        from ai.spec_guide import compile_analytical_spec

        return compile_analytical_spec(
            spec_contract=spec_contract,
            data_dict=data_dict,
            project_id=self.project_id,
            is_en=is_en,
        )
