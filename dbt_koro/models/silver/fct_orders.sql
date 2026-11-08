{{ config(materialized='table') }}

SELECT
    order_id,
    order_date,
    customer_id,
    market_country,
    customer_segment,
    CAST(order_gross_eur AS DECIMAL(10, 2)) AS order_gross_eur,
    CAST(order_gross_eur AS DECIMAL(10, 2)) AS total_gross_eur,
    CAST(discount_eur AS DECIMAL(10, 2)) AS discount_eur,
    CAST(discount_eur AS DECIMAL(10, 2)) AS total_discount_eur,
    CAST(order_net_eur AS DECIMAL(10, 2)) AS order_net_eur,
    CAST(order_net_eur AS DECIMAL(10, 2)) AS total_net_eur
FROM {{ ref('stg_shopware_orders') }}
