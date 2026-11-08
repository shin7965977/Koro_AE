# KoRo Analytics Engineering MVP Specification: Conversational Spec Guidance & Traceable Chart Engine

## Problem Statement

In e-commerce operations (such as KoRo), non-technical business stakeholders (Category Managers, Marketing Leads, Operations Heads) face a dilemma when seeking data insights:
1. Traditional ticket queues take days to clarify metric definitions (e.g., Gross vs Net Revenue, Return Rate by units vs value), often resulting in misaligned reports across teams.
2. Direct free-form Text-to-SQL LLM tools lack business semantic guardrails, leading to hallucinated joins, unverified formulas, and zero auditability.

Additionally, mixing generic UI layout and AI drawer state management with KoRo-specific domain logic prevents reuse across future business verticals.

## Solution

Build a decoupled **Conversational Spec Guidance & Traceable Chart Engine** using the **Microkernel + Domain Adapter Pattern**:
1. **Strict Framework vs Domain Decoupling**: Generic UI layout (7:3 split drawer, On-Demand Insight Panel, 3-Layer Traceability Inspector, 2-round Socratic state machine) lives in `lakehouse-cockpit-core`. KoRo-specific data models, data contracts, semantic rules, and bulk-packaging business logic live in `Koro_AE`.
2. **2-Round Socratic Spec Guidance**: When a stakeholder asks a question or clicks a 1-click Golden Preset, Round 1 clarifies 2-3 core metric/dimension parameters, and Round 2 immediately locks down an immutable `AnalyticalSpecContract` card.
3. **On-Demand Insight & Executive Takeaway**: Upon confirming the spec, an `On-Demand Insight Panel` renders directly beneath the 4 top-level KPI cards, featuring an MBB-style `Executive Takeaway Card` ("So What?") and an interactive Plotly chart.
4. **3-Layer Traceability Inspector**: Beneath the chart, a collapsible inspector exposes (1) Executed SQL, (2) Metric Lineage & Dictionary definition with FinOps (<100MB) and GDPR (No PII) badges, and (3) a 1:1 aligned 5-row DataFrame snippet.

## User Stories

1. As a stakeholder, I want to see 4 top-level KPI cards (Gross Revenue, Net Revenue, AOV, Return Rate) upon opening the cockpit, so that I immediately grasp overall business health.
2. As a stakeholder, I want the screen to split into a 7:3 layout when opening the AI Advisor drawer, so that I can converse with the assistant while viewing the main dashboard.
3. As a non-technical manager, I want 3 one-click golden preset buttons at the top of the drawer ("Bulk Packaging Return Diagnosis", "Category Net Margin Ranking", "Inventory Stockout Risk"), so that I can experience the workflow with zero latency.
4. As a stakeholder, I want the assistant to ask 2-3 clarifying questions in Round 1 when I ask an ambiguous question, so that metric definitions are aligned before querying.
5. As a stakeholder, I want the conversation to strictly converge in Round 2 by displaying a structured `AnalyticalSpecContract` card with a confirm button, so that I never get stuck in endless chat loops.
6. As a stakeholder, I want an `On-Demand Insight Panel` to render right below the 4 KPI cards when I confirm the spec, so that I immediately see my custom visual analysis.
7. As an executive, I want an `Executive Takeaway Card` above the generated chart summarizing the key finding (e.g., 1kg Cashews have a 5.2% return rate, 78% due to vacuum packaging defects), so that I immediately understand the business impact.
8. As a data governance lead, I want to inspect the exact executed SQL in the 3-Layer Traceability Inspector, so that I can verify the query targets governed Gold marts.
9. As a stakeholder, I want to view the Metric Lineage & Data Dictionary definition in the inspector, so that I trust the metric matches finance and marketing standards.
10. As an analytics engineer, I want to see the 5-row aligned Data Snippet along with FinOps (<100MB) and GDPR (No PII) verification badges, so that I can verify 1:1 data parity and compliance.
11. As a demo presenter, I want a `New Inquiry` reset button in the drawer to clear chat history, pending specs, and on-demand charts in one click, so that I can switch demo scenarios cleanly.
12. As a bilingual team member, I want to toggle between English and Traditional Chinese in the sidebar, updating KPI cards, tabs, and guidance prompts.
13. As a platform architect, I want the spec card lifecycle and on-demand insight panel implemented generically in `lakehouse-cockpit-core` via `BaseCockpitAdapter`, so that other domain projects inherit this capability automatically.
14. As an Analytics Engineer, I want a robust self-healing Lakehouse engine that automatically executes pipeline seeding (Bronze Parquet -> DuckDB) on startup if the database file is missing, guaranteeing 100% physical SQL execution without in-memory synthetic fallbacks.

## Implementation Decisions

- Extend `lakehouse-cockpit-core` with `AnalyticalSpecContract` and `OnDemandInsightResult` dataclasses, plus default hook methods on `BaseCockpitAdapter` (`get_quick_presets`, `handle_spec_inquiry_turn`, `compile_spec_to_insight`).
- Upgrade `lakehouse-cockpit-core` engine and AI drawer to render the `On-Demand Insight Panel` (below the 4 KPI cards) and the 2-round Spec Confirmation workflow with a `New Inquiry` reset button.
- Build `Koro_AE` with YAML Data Contracts (`contracts/`), YAML Semantic Rules (`semantic/`), physical Lakehouse storage (`data/bronze/*.parquet`, `data/koro_lakehouse.duckdb`), `KoroAdapter`, Socratic Spec Engine, and an automated 12-question Benchmark Evaluation suite.
