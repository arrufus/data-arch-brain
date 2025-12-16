{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'customer']
    )
}}

-- Staging model for customers
-- Cleans and standardizes raw customer data

WITH source AS (
    SELECT * FROM {{ source('bronze', 'customers') }}
),

cleaned AS (
    SELECT
        customer_id,
        TRIM(first_name) AS first_name,
        TRIM(last_name) AS last_name,
        LOWER(TRIM(email)) AS email,
        phone,
        address,
        city,
        state,
        zip_code,
        UPPER(country_code) AS country_code,
        created_at,
        updated_at
    FROM source
    WHERE customer_id IS NOT NULL
)

SELECT * FROM cleaned
