# KoRo Analytics Engineering & Governed AI Copilot Platform

[![Live Demo](https://img.shields.io/badge/Streamlit_App-Live_Demo-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://koroae-emnrmedur9bkudgaygri4f.streamlit.app/)
[![dbt](https://img.shields.io/badge/dbt--core-1.12.6-orange.svg?style=for-the-badge&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-In--Process_OLAP-FFF000.svg?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Langfuse](https://img.shields.io/badge/Langfuse-LLM_Observability-000000.svg?style=for-the-badge&logo=langfuse&logoColor=white)](https://cloud.langfuse.com/)

---

### 💡 What Problem Does This POC Solve? (The Executive Storyline)

In modern e-commerce data platforms, Analytics Engineers are overwhelmed by ad-hoc business requests, while unguided AI copilot queries often produce warehouse-breaking hallucinations, phantom entities, and severe financial fan-out errors (e.g. cross-fact 1:N double-counting).

This production-grade Lakehouse POC bridges the gap between commercial stakeholders and data engineering:
1. **Stakeholders Inquire in Natural Language**: Commercial teams ask nuanced questions (e.g., *"How does 1kg bulk packaging affect return rates across DE vs. FR markets?"*) via a guided Socratic clarification workflow.
2. **Context-Engineered Semantic Mapping**: Instead of guessing SQL, the Copilot dynamically inspects physical DuckDB metadata, conformed Kimball star-schema grains (`fct_orders`, `fct_order_items`, `fct_returns`, `dim_products`), and active dimension values to prevent phantom filters.
3. **Automated dbt Contract & SQL Compilation**: The system compiles a signed specification memo into a fully governed dbt model (`.sql`) alongside its version-controlled data contract (`schema.yml`), validated by live DuckDB dry-runs before deployment.
4. **End-to-End Observability with Langfuse**: Every step—from dialogue intent parsing to AST compilation and dry-run execution—is instrumented with real-time Langfuse tracing and automated semantic-grounding scoring.

---

## 🏗️ Architecture Overview

```mermaid
flowchart LR
    subgraph Sources [Source Layer]
        S1[KoRo Website / Scraper]
        S2[Shopware 6 API]
        S3[Synthetic Orders/Returns]
    end

    subgraph Ingestion [Ingestion & Validation]
        I1[Python Extractors]
        I2[Pydantic Data Contracts]
    end

    subgraph Medallion [DuckDB Lakehouse In-Process OLAP]
        B1[(Bronze / Raw Parquet)]
        B2[(Silver / Kimball Star Schema)]
        B3[(Gold / Governed Marts)]
    end

    subgraph Semantic [Semantic & Knowledge Layer]
        K1[Taxonomy & Ontology]
        K2[Metrics & Business Rules]
        K3[NetworkX Knowledge Graph]
    end

    subgraph Consumption [Consumption Layer]
        C1[Streamlit BI Dashboard]
        C2[AI Analytics Assistant / MCP]
    end

    Sources --> Ingestion
    Ingestion --> B1
    B1 -->|dbt clean & deduplicate| B2
    B2 -->|dbt dimensional model| B3
    B3 --> Semantic
    B3 --> C1
    Semantic --> C2
```

---

## 📁 Repository Structure

```
├── .github/workflows/ci.yml     # Automated CI testing and validation
├── ai/                          # AI Assistant, tools, LLM clients & prompts
├── contracts/                   # Data contract specifications (YAML)
├── data/                        # Physical Lakehouse storage (bronze/*.parquet, duckdb)
├── dbt_koro/                    # dbt project (Bronze, Silver, Gold models & tests)
├── docs/                        # Specifications, mappings, and data dictionaries
├── evaluation/                  # Benchmark questions & AI evaluation framework
├── ingestion/                   # Python scrapers, Shopware API clients, validators
├── knowledge/                   # Taxonomy, ontology definitions & graph builders
├── metadata/                    # Data catalog and business glossary
├── monitoring/                  # Data quality tests & LLM observability
├── scripts/                     # Pipeline orchestrators (run_pipeline.py)
├── semantic/                    # Metric definitions and business rules
├── tests/                       # Unit, integration, and regression tests
├── .env.example                 # Environment variable templates
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 🚀 Quickstart

### 1. Clone & Setup Environment
```bash
git clone https://github.com/your-org/koro-analytics-engineering-poc.git
cd koro-analytics-engineering-poc
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run Lakehouse Pipeline (Ingest Bronze + dbt Run + dbt Test)
```bash
python scripts/run_pipeline.py
```

### 3. Run Test Suite
```bash
pytest -v
```

### 4. Launch BI Cockpit & AI Copilot
```bash
streamlit run app.py
```

---

## 📊 Core Business KPIs

* **Gross Revenue**: Total revenue before discounts and refunds.
* **Net Revenue**: Revenue after discounts and refunds.
* **Units Sold**: Total volume of products sold.
* **Average Order Value (AOV)**: Net revenue divided by total valid orders.
* **Average Selling Price (ASP)**: Net product revenue divided by units sold.
* **Return Rate**: Returned units divided by total sold units.
* **Product Availability**: Available products divided by total catalog size.

---

## ⚖️ Disclaimer
Public product information and synthetic transactional data must be strictly separated. Synthetic data generated for demonstration purposes does not reflect KoRo's internal proprietary sales records.
