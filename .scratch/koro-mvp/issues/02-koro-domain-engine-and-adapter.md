# 02: Build KoRo domain data engine, semantic contracts, and base KoroAdapter

**What to build:**
Create the KoRo e-commerce domain foundation in `Koro_AE`, including YAML Data Contracts (`products.yaml`, `orders.yaml`, `order_items.yaml`, `returns.yaml`), Semantic Business Rules (`business_rules.yaml`), deterministic synthetic Medallion data (Bronze / Silver / Gold with DuckDB query support), and `KoroAdapter` implementing the 4 executive KPI cards and Medallion layer tabs.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Create YAML data contracts in `contracts/` and semantic metric definitions in `semantic/business_rules.yaml` plus `metadata/`.
- [ ] Build the deterministic synthetic Medallion dataset and DuckDB query helper in `ingestion/` and `warehouse/`, embedding realistic KoRo product categories (Nuts & Butters, Dried Fruits, Superfoods, Snacks) and the 1kg Cashew vacuum packaging defect pattern.
- [ ] Implement `KoroAdapter` with 4 KPI cards (`Gross Revenue`, `Net Revenue`, `AOV`, `Return Rate`) and Gold/Silver/Bronze tabs with 1:1 SQL & DataFrame snippet parity.
- [ ] Verify data generation, KPI calculations, and date filtering via unit tests.
