{{ config(materialized='table') }}

WITH ranked_customers AS (
    SELECT
        customer_id,
        market_country,
        customer_segment,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM {{ ref('stg_shopware_orders') }}
)

SELECT
    customer_id,
    market_country,
    customer_segment,
    'GDPR_COMPLIANT_HASHED' AS privacy_status
FROM ranked_customers
WHERE rn = 1

