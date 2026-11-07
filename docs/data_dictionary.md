# 📚 KoRo Centralized Data Dictionary & Governance Catalog

> **Data Disclaimer**: Public product catalog attributes are combined with synthetic operational transactions (`orders`, `order_items`, `returns`). Synthetic records must never be presented as KoRo's actual internal sales figures.

## 1. Gold Layer Marts (`koro_marts`)

### `koro_marts.mart_product_performance`
- **Grain**: 1 row per `product_id` across the selected reporting window.
- **GDPR Classification**: `Public / Aggregated (contains_pii: false)`.
- **Upstream Lineage**: `raw_koro_products`, `raw_shopware_orders`, `int_returns_enriched`.

| Field Name | Data Type | Contract Source | Business Definition |
| :--- | :--- | :--- | :--- |
| `product_id` | `STRING` | `contracts/products.yaml` | Unique SKU identifier (e.g., `KORO-NUT-001`) |
| `product_name` | `STRING` | `contracts/products.yaml` | Official catalog product name |
| `category_name` | `STRING` | `contracts/products.yaml` | Top-level category (`Nuts & Butters`, `Dried Fruits`, `Superfoods & Seeds`, `Snacks & Bars`) |
| `packaging_size` | `STRING` | `contracts/products.yaml` | Bulk packaging specification (`1kg`, `500g`, `250g`) |
| `sold_units` | `INT64` | `contracts/order_items.yaml` | Total units sold in period |
| `returned_units` | `INT64` | `contracts/returns.yaml` | Total units returned by customers |
| `return_rate_pct` | `FLOAT64` | `semantic/business_rules.yaml#return_rate` | `ROUND(SUM(returned_units) * 100.0 / NULLIF(SUM(sold_units), 0), 2)` |
| `gross_revenue_eur` | `NUMERIC` | `semantic/business_rules.yaml#gross_revenue` | Total sales revenue before discounts and refunds |
| `net_revenue_eur` | `NUMERIC` | `semantic/business_rules.yaml#net_revenue` | Realized revenue after subtracting vouchers and refunds |
| `net_margin_pct` | `FLOAT64` | `semantic/business_rules.yaml#net_margin_pct` | `ROUND((SUM(net_revenue_eur) - SUM(cogs_eur)) * 100.0 / NULLIF(SUM(net_revenue_eur), 0), 2)` |
| `is_available` | `BOOL` | `contracts/products.yaml` | Current website in-stock flag |
| `days_of_supply` | `FLOAT64` | `semantic/business_rules.yaml#product_availability` | Current stock on hand divided by daily unit sales velocity |
