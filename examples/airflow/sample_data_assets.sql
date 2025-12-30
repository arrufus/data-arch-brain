-- Sample Data Assets for Finance GL Pipeline Example
-- These tables should exist in your database before running the Airflow integration demo

-- =============================================================================
-- Dimension Tables
-- =============================================================================

-- Chart of Accounts (reference data)
CREATE TABLE IF NOT EXISTS dim.chart_of_accounts (
    account_id SERIAL PRIMARY KEY,
    account_code VARCHAR(20) NOT NULL UNIQUE,
    account_name VARCHAR(200) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- 'Asset', 'Liability', 'Equity', 'Revenue', 'Expense'
    parent_account_id INTEGER REFERENCES dim.chart_of_accounts(account_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO dim.chart_of_accounts (account_code, account_name, account_type) VALUES
    ('1000', 'Cash and Cash Equivalents', 'Asset'),
    ('1100', 'Accounts Receivable', 'Asset'),
    ('2000', 'Accounts Payable', 'Liability'),
    ('3000', 'Common Stock', 'Equity'),
    ('4000', 'Revenue', 'Revenue'),
    ('5000', 'Cost of Goods Sold', 'Expense'),
    ('6000', 'Operating Expenses', 'Expense');

-- =============================================================================
-- Staging Tables
-- =============================================================================

-- Raw transactions from source systems
CREATE TABLE IF NOT EXISTS staging.raw_transactions (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(20) NOT NULL,
    amount DECIMAL(18, 2) NOT NULL,
    posted_date DATE NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    source_system VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO staging.raw_transactions (account_code, amount, posted_date, description, status) VALUES
    ('1000', 50000.00, CURRENT_DATE, 'Customer payment received', 'approved'),
    ('4000', -50000.00, CURRENT_DATE, 'Sales revenue', 'approved'),
    ('5000', 30000.00, CURRENT_DATE, 'Inventory purchase', 'approved'),
    ('1000', -30000.00, CURRENT_DATE, 'Inventory payment', 'approved'),
    ('6000', 5000.00, CURRENT_DATE, 'Office supplies', 'approved');

-- =============================================================================
-- Facts Tables
-- =============================================================================

-- General Ledger transactions (target fact table)
CREATE TABLE IF NOT EXISTS facts.gl_transactions (
    transaction_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES dim.chart_of_accounts(account_id),
    amount DECIMAL(18, 2) NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_amount CHECK (amount <> 0)
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_gl_transactions_date ON facts.gl_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_gl_transactions_account ON facts.gl_transactions(account_id);

-- =============================================================================
-- Reports Tables
-- =============================================================================

-- GL reconciliation report
CREATE TABLE IF NOT EXISTS reports.gl_reconciliation (
    report_date DATE NOT NULL,
    account_id INTEGER NOT NULL REFERENCES dim.chart_of_accounts(account_id),
    account_code VARCHAR(20) NOT NULL,
    account_name VARCHAR(200) NOT NULL,
    debit_total DECIMAL(18, 2) DEFAULT 0,
    credit_total DECIMAL(18, 2) DEFAULT 0,
    balance DECIMAL(18, 2) NOT NULL,
    transaction_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (report_date, account_id)
);

-- Monthly close summary
CREATE TABLE IF NOT EXISTS reports.monthly_close_summary (
    close_date DATE NOT NULL PRIMARY KEY,
    total_debits DECIMAL(18, 2) NOT NULL,
    total_credits DECIMAL(18, 2) NOT NULL,
    net_balance DECIMAL(18, 2) NOT NULL,
    account_count INTEGER NOT NULL,
    transaction_count INTEGER NOT NULL,
    is_balanced BOOLEAN NOT NULL,
    closed_by VARCHAR(100),
    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Views for Analytics
-- =============================================================================

-- Account balance view
CREATE OR REPLACE VIEW reports.account_balances AS
SELECT
    c.account_id,
    c.account_code,
    c.account_name,
    c.account_type,
    COALESCE(SUM(t.amount), 0) AS balance,
    COUNT(t.transaction_id) AS transaction_count
FROM dim.chart_of_accounts c
LEFT JOIN facts.gl_transactions t ON c.account_id = t.account_id
WHERE c.is_active = TRUE
GROUP BY c.account_id, c.account_code, c.account_name, c.account_type;

-- Trial balance view
CREATE OR REPLACE VIEW reports.trial_balance AS
SELECT
    CURRENT_DATE AS balance_date,
    account_type,
    SUM(CASE WHEN balance > 0 THEN balance ELSE 0 END) AS debit_total,
    SUM(CASE WHEN balance < 0 THEN ABS(balance) ELSE 0 END) AS credit_total,
    SUM(balance) AS net_balance
FROM reports.account_balances
GROUP BY account_type;

-- =============================================================================
-- Helper: Create schemas if they don't exist
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS dim;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS facts;
CREATE SCHEMA IF NOT EXISTS reports;

-- =============================================================================
-- Verification Queries
-- =============================================================================

-- Check data existence
-- SELECT 'Chart of Accounts', COUNT(*) FROM dim.chart_of_accounts
-- UNION ALL
-- SELECT 'Raw Transactions', COUNT(*) FROM staging.raw_transactions
-- UNION ALL
-- SELECT 'GL Transactions', COUNT(*) FROM facts.gl_transactions;

-- Sample lineage query (manual verification)
-- SELECT
--   'staging.raw_transactions.account_code' AS source_column,
--   'facts.gl_transactions.account_id' AS target_column,
--   'JOIN via dim.chart_of_accounts.account_code' AS lineage_path;
