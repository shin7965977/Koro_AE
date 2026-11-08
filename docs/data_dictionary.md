# 📚 KoRo Centralized Data Dictionary & Governance Catalog

> **Data Disclaimer**: Public product catalog attributes are combined with synthetic operational transactions (`orders`, `order_items`, `returns`). Synthetic records must never be presented as KoRo's actual internal sales figures.

## 1. Gold Layer Marts (`main_gold`)

### `main_gold.mart_product_performance`
- **Grain**: 1 row per `product_id` across the selected reporting window.
- **GDPR Classification**: `Public / Aggregated (contains_pii: false)`.
- **Upstream Lineage**: `main_silver.dim_products`, `main_silver.fct_order_items`, `main_silver.fct_returns`.

| Field Name | Data Type | Contract Source | Business Definition |
| :--- | :--- | :--- | :--- |
| `product_id` | `VARCHAR` | `contracts/products.yaml` | Unique SKU identifier (e.g., `KORO-NUT-001`) |
| `product_name` | `VARCHAR` | `contracts/products.yaml` | Official catalog product name |
| `category_name` | `VARCHAR` | `contracts/products.yaml` | Top-level category (`Nuts & Butters`, `Dried Fruits`, `Superfoods & Seeds`, `Snacks & Bars`) |
| `packaging_size` | `VARCHAR` | `contracts/products.yaml` | Bulk packaging specification (`1kg`, `500g`, `250g`) |
| `sold_units` | `INTEGER` | `contracts/order_items.yaml` | Total units sold in period |
| `returned_units` | `INTEGER` | `contracts/returns.yaml` | Total units returned by customers |
| `return_rate_pct` | `DOUBLE` | `semantic/business_rules.yaml#return_rate` | `ROUND(SUM(returned_units) * 100.0 / NULLIF(SUM(sold_units), 0), 2)` |
| `gross_revenue_eur` | `DECIMAL(10,2)` | `semantic/business_rules.yaml#gross_revenue` | Total sales revenue before discounts and refunds |
| `net_revenue_eur` | `DECIMAL(10,2)` | `semantic/business_rules.yaml#net_revenue` | Realized revenue after subtracting vouchers and refunds |
| `net_margin_pct` | `DOUBLE` | `semantic/business_rules.yaml#net_margin_pct` | `ROUND((SUM(net_revenue_eur) - SUM(cogs_eur)) * 100.0 / NULLIF(SUM(net_revenue_eur), 0), 2)` |
| `is_available` | `BOOLEAN` | `contracts/products.yaml` | Current website in-stock flag |
| `days_of_supply` | `DOUBLE` | `semantic/business_rules.yaml#days_of_supply` | Current stock on hand divided by daily unit sales velocity |
