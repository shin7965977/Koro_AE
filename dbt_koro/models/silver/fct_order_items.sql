{{ config(materialized='table') }}

SELECT
    order_item_id,
    order_id,
    order_date,
    product_id,
    CAST(quantity_sold AS INTEGER) AS quantity_sold,
    CAST(line_gross_eur AS DECIMAL(10, 2)) AS line_gross_eur,
    CAST(line_discount_eur AS DECIMAL(10, 2)) AS line_discount_eur,
    CAST(line_refund_eur AS DECIMAL(10, 2)) AS line_refund_eur,
    CAST(line_net_eur AS DECIMAL(10, 2)) AS line_net_eur,
    CAST(cogs_eur AS DECIMAL(10, 2)) AS cogs_eur
FROM {{ ref('stg_shopware_order_items') }}

