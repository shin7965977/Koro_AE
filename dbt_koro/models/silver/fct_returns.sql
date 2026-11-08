{{ config(materialized='table') }}

SELECT
    return_id,
    order_id,
    product_id,
    return_date,
    CAST(returned_units AS INTEGER) AS returned_units,
    CAST(refunded_eur AS DECIMAL(10, 2)) AS refunded_eur,
    return_reason,
    defect_severity
FROM {{ ref('stg_return_logs') }}
