{{
    config(
        materialized='table',
        tags=['silver', 'dimensional', 'customer']
    )
}}

-- Customer dimension table
-- Enriched with customer metrics

WITH customers AS (
    SELECT * FROM {{ ref('stg_customers') }}
),

orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

customer_metrics AS (
    SELECT
        customer_id,
        COUNT(*) AS total_orders,
        SUM(order_amount) AS total_spent,
        AVG(order_amount) AS avg_order_value,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date
    FROM orders
    GROUP BY customer_id
),

final AS (
    SELECT
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        c.phone,
        c.address,
        c.city,
        c.state,
        c.zip_code,
        c.country_code,
        COALESCE(m.total_orders, 0) AS total_orders,
        COALESCE(m.total_spent, 0) AS total_spent,
        COALESCE(m.avg_order_value, 0) AS avg_order_value,
        m.first_order_date,
        m.last_order_date,
        c.created_at,
        c.updated_at,
        CURRENT_TIMESTAMP AS dbt_updated_at
    FROM customers c
    LEFT JOIN customer_metrics m
        ON c.customer_id = m.customer_id
)

SELECT * FROM final
