{{ config(materialized='table') }}

SELECT
    p.product_id,
    p.product_name,
    p.category_name,
    p.packaging_size,
    CAST(COALESCE(SUM(i.quantity_sold), 0) AS INTEGER) AS total_sold_units,
    CAST(COALESCE(SUM(i.line_gross_eur), 0.0) AS DECIMAL(10, 2)) AS gross_revenue_eur,
    CAST(COALESCE(SUM(i.line_net_eur), 0.0) AS DECIMAL(10, 2)) AS net_revenue_eur,
    CAST(COALESCE(SUM(r.returned_units), 0) AS INTEGER) AS total_returned_units,
    ROUND(
        COALESCE(SUM(r.returned_units), 0) * 100.0 / NULLIF(SUM(i.quantity_sold), 0),
        2
    ) AS return_rate_pct
FROM {{ ref('dim_products') }} p
LEFT JOIN {{ ref('fct_order_items') }} i ON p.product_id = i.product_id
LEFT JOIN {{ ref('fct_returns') }} r ON p.product_id = r.product_id
GROUP BY p.product_id, p.product_name, p.category_name, p.packaging_size
