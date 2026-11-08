{{ config(materialized='table') }}

WITH item_agg AS (
    SELECT
        product_id,
        CAST(COALESCE(SUM(quantity_sold), 0) AS INTEGER) AS sold_units,
        CAST(COALESCE(SUM(quantity_sold), 0) AS INTEGER) AS total_sold_units,
        CAST(COALESCE(SUM(line_gross_eur), 0.0) AS DECIMAL(10, 2)) AS gross_revenue_eur,
        CAST(COALESCE(SUM(line_discount_eur), 0.0) AS DECIMAL(10, 2)) AS discount_eur,
        CAST(COALESCE(SUM(line_refund_eur), 0.0) AS DECIMAL(10, 2)) AS refunded_eur,
        CAST(COALESCE(SUM(line_net_eur), 0.0) AS DECIMAL(10, 2)) AS net_revenue_eur,
        CAST(COALESCE(SUM(cogs_eur), 0.0) AS DECIMAL(10, 2)) AS cogs_eur
    FROM {{ ref('fct_order_items') }}
    GROUP BY product_id
),
ret_agg AS (
    SELECT
        product_id,
        CAST(COALESCE(SUM(returned_units), 0) AS INTEGER) AS returned_units,
        CAST(COALESCE(SUM(returned_units), 0) AS INTEGER) AS total_returned_units
    FROM {{ ref('fct_returns') }}
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category_name,
    p.packaging_size,
    p.stock_on_hand,
    p.is_available,
    COALESCE(i.sold_units, 0) AS sold_units,
    COALESCE(i.total_sold_units, 0) AS total_sold_units,
    COALESCE(i.gross_revenue_eur, 0.0) AS gross_revenue_eur,
    COALESCE(i.discount_eur, 0.0) AS discount_eur,
    COALESCE(i.refunded_eur, 0.0) AS refunded_eur,
    COALESCE(i.net_revenue_eur, 0.0) AS net_revenue_eur,
    COALESCE(i.cogs_eur, 0.0) AS cogs_eur,
    COALESCE(r.returned_units, 0) AS returned_units,
    COALESCE(r.total_returned_units, 0) AS total_returned_units,
    ROUND(
        COALESCE(r.returned_units, 0) * 100.0 / NULLIF(COALESCE(i.sold_units, 0), 0),
        2
    ) AS return_rate_pct,
    ROUND(COALESCE(i.net_revenue_eur, 0.0) - COALESCE(i.cogs_eur, 0.0), 2) AS net_margin_eur,
    ROUND(
        (COALESCE(i.net_revenue_eur, 0.0) - COALESCE(i.cogs_eur, 0.0)) * 100.0 / NULLIF(COALESCE(i.net_revenue_eur, 0.0), 0),
        2
    ) AS net_margin_pct,
    ROUND(
        p.stock_on_hand / NULLIF(COALESCE(i.sold_units, 0) / 90.0, 0),
        1
    ) AS days_of_supply
FROM {{ ref('dim_products') }} p
LEFT JOIN item_agg i ON p.product_id = i.product_id
LEFT JOIN ret_agg r ON p.product_id = r.product_id
