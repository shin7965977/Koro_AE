{{ config(materialized='table') }}

SELECT
    product_id,
    TRIM(product_name) AS product_name,
    CASE 
        WHEN category_name = 'Nuts & Butters' THEN 'CAT-01'
        WHEN category_name = 'Dried Fruits' THEN 'CAT-02'
        WHEN category_name = 'Superfoods & Seeds' THEN 'CAT-03'
        WHEN category_name = 'Snacks & Bars' THEN 'CAT-04'
        ELSE 'CAT-99'
    END AS category_id,
    category_name,
    packaging_size,
    CAST(unit_price_eur AS DECIMAL(10, 2)) AS unit_price_eur,
    CAST(unit_cost_eur AS DECIMAL(10, 2)) AS unit_cost_eur,
    is_available AS is_in_stock,
    is_available,
    CAST(stock_on_hand AS INTEGER) AS stock_on_hand
FROM {{ ref('stg_koro_products') }}


