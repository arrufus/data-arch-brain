{{
    config(
        materialized='view',
        tags=['silver', 'intermediate']
    )
}}

-- Intermediate model joining customers and orders
-- Creates a denormalized view for easier dimensional modeling

WITH customers AS (
    SELECT * FROM {{ ref('stg_customers') }}
),

orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

joined AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        c.city,
        c.state,
        c.country_code,
        o.order_date,
        o.order_amount,
        o.status,
        o.payment_method
    FROM orders o
    INNER JOIN customers c
        ON o.customer_id = c.customer_id
)

SELECT * FROM joined
