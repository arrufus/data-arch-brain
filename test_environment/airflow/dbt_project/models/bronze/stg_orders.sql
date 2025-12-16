{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'sales']
    )
}}

-- Staging model for orders
-- Cleans and standardizes raw order data

WITH source AS (
    SELECT * FROM {{ source('bronze', 'orders') }}
),

cleaned AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        order_amount,
        LOWER(status) AS status,
        LOWER(payment_method) AS payment_method,
        shipping_address,
        created_at
    FROM source
    WHERE order_id IS NOT NULL
      AND customer_id IS NOT NULL
      AND order_date IS NOT NULL
)

SELECT * FROM cleaned
