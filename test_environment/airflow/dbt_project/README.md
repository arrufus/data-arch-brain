# Customer Analytics DBT Project

This DBT project implements a multi-layered data architecture for customer analytics.

## Project Structure

```
customer_analytics/
├── dbt_project.yml       # Project configuration
├── profiles.yml          # Database connection profiles
├── models/
│   ├── bronze/          # Staging layer (cleaned sources)
│   │   ├── sources.yml  # Source definitions
│   │   ├── stg_customers.sql
│   │   ├── stg_orders.sql
│   │   └── stg_order_items.sql
│   └── silver/          # Dimensional layer
│       ├── schema.yml   # Model documentation
│       ├── int_customer_orders.sql
│       ├── dim_customers.sql
│       └── fct_orders.sql
└── seeds/
    └── country_codes.csv
```

## Data Layers

### Bronze Layer (Staging)
- **Purpose**: Clean and standardize raw source data
- **Materialization**: Views
- **Models**:
  - `stg_customers`: Cleaned customer data
  - `stg_orders`: Cleaned order data
  - `stg_order_items`: Cleaned order line items

### Silver Layer (Dimensional)
- **Purpose**: Create analytics-ready dimensional models
- **Materialization**: Tables
- **Models**:
  - `int_customer_orders`: Intermediate joined data
  - `dim_customers`: Customer dimension with metrics
  - `fct_orders`: Orders fact table

## Data Lineage

```
Sources (bronze schema)
    ├── customers ──> stg_customers ──┐
    ├── orders ────> stg_orders ──────┤
    └── order_items > stg_order_items ┤
                                      ├──> int_customer_orders
                                      │
                                      ├──> dim_customers
                                      │
                                      └──> fct_orders
```

## Running the Project

```bash
# Install dependencies
dbt deps

# Load seed data
dbt seed

# Run bronze layer models
dbt run --select tag:bronze

# Run silver layer models
dbt run --select tag:silver

# Run all models
dbt run

# Test models
dbt test

# Generate documentation
dbt docs generate
dbt docs serve
```

## Tags

- `bronze`: Bronze layer staging models
- `silver`: Silver layer dimensional models
- `staging`: Staging transformations
- `dimensional`: Dimensional models
- `customer`: Customer domain
- `sales`: Sales domain

## PII Handling

This project identifies PII fields using meta tags:
- `email`: Customer email addresses
- `phone`: Phone numbers
- `address`: Physical addresses

These fields are marked with `pii: true` and `sensitivity: high` in the schema definitions.
