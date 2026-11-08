{{ config(materialized='table') }}

SELECT DISTINCT
    category_name,
    CASE 
        WHEN category_name IN ('Nuts & Butters', 'Dried Fruits') THEN 'Bulk Pantry'
        WHEN category_name = 'Snacks & Bars' THEN 'On-the-go'
        ELSE 'Health & Nutrition'
    END AS department_group
FROM {{ ref('stg_koro_products') }}
