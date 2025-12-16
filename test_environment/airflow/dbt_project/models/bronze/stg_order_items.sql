{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'sales']
    )
}}

-- Staging model for order items
-- Cleans and standardizes raw order item data

WITH source AS (
    SELECT * FROM {{ source('bronze', 'order_items') }}
),

cleaned AS (
    SELECT
        order_item_id,
        order_id,
        product_id,
        TRIM(product_name) AS product_name,
        quantity,
        unit_price,
        total_price
    FROM source
    WHERE order_item_id IS NOT NULL
      AND order_id IS NOT NULL
)

SELECT * FROM cleaned
