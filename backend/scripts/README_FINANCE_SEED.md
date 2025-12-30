# Finance Vertical Seed Data

This document describes the finance vertical seed data created by [seed_finance_capsules.py](seed_finance_capsules.py).

## Overview

The finance seed creates a comprehensive example of data capsules in the finance domain, demonstrating all 7 dimensions of the Data Capsule model, data products, and classification tags.

## Created Resources

### Domain & Owner

- **Domain**: `finance`
  - Description: Financial data domain including accounting, revenue, and regulatory reporting
  - Compliance frameworks: SOX, GAAP, IFRS
- **Owner**: Finance Data Team
  - Email: finance-data@company.com
  - Slack: #finance-data

### Tags (8 total)

Classification tags for finance data:

1. **sox** (Compliance) - Sarbanes-Oxley Act compliance requirement
2. **gaap** (Compliance) - Generally Accepted Accounting Principles
3. **ifrs** (Compliance) - International Financial Reporting Standards
4. **finance** (Domain) - Financial data and metrics
5. **revenue** (Business Area) - Revenue recognition and tracking
6. **general_ledger** (Business Area) - General ledger and accounting entries
7. **tier-1** (Data Quality) - Mission critical data
8. **regulatory** (Compliance) - Subject to regulatory reporting requirements

### Business Terms (5 total)

Finance-specific business glossary:

1. **revenue** - Total income from normal business operations
2. **debit** - Accounting entry (left side of double-entry)
3. **credit** - Accounting entry (right side of double-entry)
4. **account_balance** - Net amount in an account
5. **fiscal_period** - Period for calculating financial statements

### Value Domains (3 total)

1. **currency_usd** - Monetary values in USD with 2 decimal places
2. **account_type_enum** - Account types (asset, liability, equity, revenue, expense)
3. **transaction_status_enum** - Transaction processing status

### Data Capsules (3 total)

All capsules include all 7 dimensions:

#### 1. Chart of Accounts (Master Data)

**URN**: `urn:dcs:postgres:table:finance_erp.master:chart_of_accounts`

- **Type**: Master data (Gold layer)
- **Platform**: PostgreSQL (NetSuite)
- **Rows**: 500
- **Columns**: 5
  - `account_id` (VARCHAR) - PK
  - `account_name` (VARCHAR)
  - `account_type` (VARCHAR) - FK to value domain
  - `parent_account_id` (VARCHAR) - Self-referencing FK for hierarchy
  - `is_active` (BOOLEAN)

**7 Dimensions**:
- ✓ Identity & Context: Master data, gold layer, finance domain
- ✓ Structural Metadata: 5 columns, 2 constraints, 2 indexes
- ✓ Business Terms: Linked to "account_balance" term
- ✓ Quality & Profiling: Column profiles, 3 quality rules
- ✓ Data Policies: Internal sensitivity, 10-year retention, SOX/GAAP compliance
- ✓ Lineage & Transformation: Version history
- ✓ Operational Contract: 24hr freshness SLA, 99.99% availability, critical support

**Tags**: sox, gaap, general_ledger, tier-1

---

#### 2. GL Transactions (Fact Table)

**URN**: `urn:dcs:postgres:table:finance_erp.facts:gl_transactions`

- **Type**: Fact table (Gold layer)
- **Platform**: PostgreSQL (NetSuite)
- **Rows**: 50,000,000
- **Size**: 25 GB
- **Partitioning**: Range by transaction_date
- **Storage**: Parquet with Snappy compression
- **Columns**: 9
  - `transaction_id` (UUID) - PK
  - `transaction_date` (DATE) - Partition key
  - `account_id` (VARCHAR) - FK to chart_of_accounts
  - `debit_amount` (DECIMAL) - Debit side
  - `credit_amount` (DECIMAL) - Credit side
  - `transaction_status` (VARCHAR) - FK to value domain
  - `description` (TEXT)
  - `fiscal_period` (VARCHAR)
  - `created_by` (VARCHAR) - PII

**7 Dimensions**:
- ✓ Identity & Context: Fact table, gold layer, partitioned, compressed
- ✓ Structural Metadata: 9 columns, 3 constraints (PK, FK, CHECK), 3 indexes
- ✓ Business Terms: Linked to debit, credit, fiscal_period terms
- ✓ Quality & Profiling: Column profiles, 4 quality rules (including custom double-entry balance check)
- ✓ Data Policies: Restricted sensitivity, 7-year retention, SOX/GAAP/audit trail, 2 masking rules
- ✓ Lineage & Transformation: Upstream from chart_of_accounts, SQL transformation, 2 versions
- ✓ Operational Contract: 1hr freshness SLA, 99.99% availability, critical 24/7 support, 4 known consumers

**Tags**: sox, gaap, finance, general_ledger, tier-1, regulatory

---

#### 3. Revenue by Month (Aggregated Mart)

**URN**: `urn:dcs:dbt:model:finance_analytics.marts:revenue_by_month`

- **Type**: dbt mart (Gold layer)
- **Platform**: dbt (finance_analytics project)
- **Rows**: 12,000
- **Materialization**: Incremental
- **Columns**: 4
  - `fiscal_period` (VARCHAR) - Composite PK
  - `account_id` (VARCHAR) - Composite PK
  - `revenue_amount` (DECIMAL) - Revenue metric
  - `transaction_count` (INTEGER)

**7 Dimensions**:
- ✓ Identity & Context: dbt mart, gold layer, incremental materialization
- ✓ Structural Metadata: 4 columns, 1 composite PK, 1 index
- ✓ Business Terms: Linked to "revenue" term (capsule and column level)
- ✓ Quality & Profiling: Column profiles, 3 quality rules
- ✓ Data Policies: Confidential, 7-year retention, SOX/GAAP/ASC 606 compliance
- ✓ Lineage & Transformation: Downstream from gl_transactions, dbt SQL with Jinja, version history
- ✓ Operational Contract: 24hr freshness SLA, 99.90% availability, business hours support, 3 known consumers

**Tags**: sox, gaap, finance, revenue, regulatory

---

### Data Products (2 total)

#### 1. Financial Reporting Product

- **Status**: Active
- **Version**: 1.0.0
- **SLOs**:
  - Freshness: 24 hours
  - Availability: 99.9%
  - Quality: 99.9%
- **Capsules**:
  - `chart_of_accounts` (Input role)
  - `gl_transactions` (Member role)
  - `revenue_by_month` (Output role / Output port)
- **Use Case**: Core financial reporting data product providing GL transactions and revenue metrics for financial statements
- **Tags**: finance, reporting, sox

#### 2. General Ledger Data Product

- **Status**: Active
- **Version**: 1.0.0
- **SLOs**:
  - Freshness: 1 hour
  - Availability: 99.99%
  - Quality: 99.99%
- **Capsules**:
  - `chart_of_accounts` (Output role / Output port)
  - `gl_transactions` (Output role / Output port)
- **Use Case**: Comprehensive general ledger data product providing detailed transaction history and account structure
- **Tags**: finance, general_ledger, sox, tier-1

---

## Data Lineage

```
chart_of_accounts (Master Data)
        |
        | foreign_key_join
        ↓
gl_transactions (Fact Table)
        |
        | aggregation
        ↓
revenue_by_month (Mart)
```

## Compliance & Governance

### SOX Controls
- `chart_of_accounts`: Internal sensitivity, audit logging required
- `gl_transactions`: Restricted sensitivity, 7-year retention, SOX controls ITGC-01 and FSCA-02
- `revenue_by_month`: Confidential, SOX control FSCA-03

### Data Masking
- `gl_transactions.created_by`: Hashed with SHA-256 for analysts and external auditors
- `gl_transactions.description`: Partial redaction (show first 20 chars) for analysts

### Quality Rules
- **Uniqueness**: Primary keys enforced on all tables
- **Referential Integrity**: Foreign keys enforced
- **Double-Entry Accounting**: Custom SQL rule ensures debits equal credits
- **Freshness**: 1hr for GL transactions, 24hr for marts
- **Range Checks**: Revenue amounts validated

## Usage Examples

### Query the Capsules

```sql
-- Get all finance capsules
SELECT urn, name, layer, row_count
FROM dcs.capsules
WHERE domain_id = (SELECT id FROM dcs.domains WHERE name = 'finance')
ORDER BY layer, name;

-- Get all tags for GL transactions
SELECT t.name, t.category, t.sensitivity_level
FROM dcs.tags t
INNER JOIN dcs.capsule_tags ct ON t.id = ct.tag_id
INNER JOIN dcs.capsules c ON ct.capsule_id = c.id
WHERE c.name = 'gl_transactions';

-- Get data products in finance domain
SELECT dp.name, dp.version, dp.status,
       COUNT(cdp.capsule_id) as capsule_count
FROM dcs.data_products dp
LEFT JOIN dcs.capsule_data_products cdp ON dp.id = cdp.data_product_id
WHERE dp.domain_id = (SELECT id FROM dcs.domains WHERE name = 'finance')
GROUP BY dp.id, dp.name, dp.version, dp.status;
```

### API Endpoints

```bash
# List all finance capsules
curl http://localhost:8000/api/v1/capsules?domain=finance

# Get GL transactions capsule details
curl http://localhost:8000/api/v1/capsules?name=gl_transactions

# List all data products
curl http://localhost:8000/api/v1/products

# Get Financial Reporting Product
curl http://localhost:8000/api/v1/products?name=Financial%20Reporting%20Product

# List all finance tags
curl http://localhost:8000/api/v1/tags?category=compliance
```

## Running the Seed Script

```bash
cd backend
python -m scripts.seed_finance_capsules
```

## Architecture Highlights

### Medallion Architecture
- **Raw**: Source system data (NetSuite)
- **Bronze**: Staged transactions
- **Gold**: `chart_of_accounts`, `gl_transactions`, `revenue_by_month`

### Data Mesh Principles
- Domain-oriented (finance domain)
- Data products as first-class citizens
- Self-serve data infrastructure
- Federated computational governance

### Compliance by Design
- Automatic masking rules for PII
- Audit logging on all tables
- 7-year retention for regulatory compliance
- SOX and GAAP framework alignment

---

*Generated by seed_finance_capsules.py*
*Last updated: 2025-12-23*
