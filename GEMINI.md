# KoRo Lakehouse Engineering & Zero-Facade Governance Rules

## 1. Core Architecture Directive (Zero-Facade Standard)
- This project is an authentic, production-grade **Analytics Engineering Lakehouse Platform**.
- **Prohibited Rule Removal**: The legacy assumption ("0-cost, 0-setup, fake in-memory demo") is permanently revoked.
- **Strict Prohibition**: Never simulate SQL queries, data lineage, or warehouse transformations via in-memory Python scripts (e.g., `synthetic_medallion.py`). 
- **Enforcement**: Any feature presented in the UI or documentation MUST be backed by physical files, a real database engine, and executable dbt models.

---

## 2. Storage & Transformation Engine Contract
- **Bronze Storage**: All raw ingested assets must be physically persisted in `data/bronze/*.parquet` using standard columnar formats.
- **Transformation Engine**: **DuckDB + dbt-duckdb** is the official in-process OLAP engine:
  - Database file: `data/koro_lakehouse.duckdb`
  - dbt project: `dbt_koro/`
  - Schemas: `main_bronze` (Staging), `main_silver` (Kimball Star Schema facts & dims), `main_gold` (Aggregated business marts).
- **Runtime Access**: Applications (Streamlit, Adapters, AI Copilot) MUST query `data/koro_lakehouse.duckdb` via DuckDB SQL connection. Direct in-memory generation at runtime is forbidden.

---

## 3. Single Source of Truth for Lineage & Metadata
- **dbt Compiler as SSoT**: The Directed Acyclic Graph (DAG) and data dependencies must be computed directly by `dbt compile` / `dbt docs generate` from `{{ ref(...) }}` and `{{ source(...) }}` macros.
- **Forbidden Practice**: Never manually patch or regex-inject Base64 JSON payloads into static report bundles (`docs/elementary_report.html`, `dbt_docs.html`).
- **Architectural Flow Direction**:
  - `Bronze (Raw Sources)` $\rightarrow$ `Staging (Views/Tables)` $\rightarrow$ `Silver (Kimball Facts & Dims)` $\rightarrow$ `Gold (Marts)`
  - Dimensions must NEVER depend on Facts.
  - Facts must NEVER cross-depend on unrelated staging domains (e.g. `order_items` cannot depend on `returns`).

---

## 4. Testing & Contract Enforcement
- **Data Contracts**: Every model in Silver and Gold must declare column-level tests (`unique`, `not_null`, `relationships`) in `schema.yml`.
- **Pre-Commit Verification**: All 18+ dbt data contract tests and all pytest suites must achieve **100% PASS** on physical database files.
- **CI Guarantee**: GitHub Actions (`.github/workflows/ci.yml`) must execute `python scripts/run_pipeline.py` (ingestion, dbt run, dbt test) before running `pytest`.

---

## 5. Anti-Smell Governance Rules (Goldfish Standard)
- **5.1 Single Source of Syntax**: All queries, documentation, and LookML must strictly use DuckDB / ANSI SQL standard with `main_silver.*` and `main_gold.*` schema paths. Pseudo-dialects (e.g. BigQuery backticks, `SAFE_DIVIDE`, unmounted `koro_marts.*`) are strictly prohibited.
- **5.2 Code-Contract Bi-directional Lock**: Data contracts (`contracts/*.yaml`) and semantic rules (`semantic/*.yaml`) must strictly match physical dbt models in `dbt_koro/models/**/schema.yml`. Fact tables must not declare dimension-owned attributes as atomic required columns (e.g. `packaging_size` belongs to `dim_products`, not `fct_returns`).
- **5.3 Eliminate Presentation-Only Fallbacks**: Applications must never maintain shadow in-memory datasets for demo fault-tolerance. Missing database files must trigger automated pipeline seeding (`scripts/run_pipeline.py`) rather than bypassing the database engine.
- **5.4 Honest Observability & Strict Testing**: Tests must never use accommodating `or` assertions to mask legacy artifacts (e.g. `assert "platzi" in html or "koro" in html`). Any presence of obsolete legacy tokens constitutes an immediate test failure.
- **5.5 Elimination of Silent State Mutations & Fake Wide Marts**:
  - **No Silent Overrides (Explicit State Locking)**: Any change to analysis scope (temporal range, market filters, product categories) negotiated in dialogue MUST be explicitly declared in the Analytical Requirement Memo and surfaced for human review. Silent or magical backend overrides that leave UI state decoupled from execution state are strictly forbidden.
  - **Metadata-Grounded Validation (No Phantom Entities)**: AI Copilots must strictly ground dimensional values against the reflected lakehouse metadata catalog (e.g., active markets from `fct_orders.market_country`). If an entity is absent from the warehouse catalog (e.g., non-existent markets like `TW`), the copilot must halt, reject the phantom entity, and demand explicit clarification. Fabricating ungrounded entities or silently falling back to defaults is prohibited.
  - **Kimball One-Mart-One-Grain Discipline**: Never synthesize ad-hoc hybrid wide tables that stitch together mismatched raw facts (e.g., direct 1:N joining of order_items and returns) into a single fan-out table that causes double-counting. Each mart must maintain a single, strictly defined grain. When cross-fact metrics are requested (e.g., product revenue vs. return rate), each fact domain MUST be pre-aggregated to the target grain (e.g., Product SKU x Market) in separate, independent CTEs before joining to the dimension table, ensuring mathematically safe, non-duplicated metrics.
