{{
    config(
        materialized='table',
        tags=['silver', 'fact', 'sales']
    )
}}

-- Orders fact table
-- Includes order details and aggregated order items

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

order_items AS (
    SELECT * FROM {{ ref('stg_order_items') }}
),

order_aggregates AS (
    SELECT
        order_id,
        COUNT(*) AS total_items,
        SUM(quantity) AS total_quantity,
        SUM(total_price) AS calculated_order_amount
    FROM order_items
    GROUP BY order_id
),

final AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.order_amount,
        o.status,
        o.payment_method,
        o.shipping_address,
        COALESCE(oa.total_items, 0) AS total_items,
        COALESCE(oa.total_quantity, 0) AS total_quantity,
        COALESCE(oa.calculated_order_amount, 0) AS calculated_order_amount,
        o.created_at,
        CURRENT_TIMESTAMP AS dbt_updated_at
    FROM orders o
    LEFT JOIN order_aggregates oa
        ON o.order_id = oa.order_id
)

SELECT * FROM final
