-- Cash Transactions and Interest Accruals Tables
-- For detailed tracking of cash movements and interest from IBKR FlexQuery

-- Cash Transactions Table
-- Tracks all cash movements from dedicated Cash Transactions FlexQuery
CREATE TABLE IF NOT EXISTS portfolio.cash_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Transaction details
    transaction_date DATE NOT NULL,
    transaction_time TIMESTAMP WITH TIME ZONE NOT NULL,
    transaction_type VARCHAR(100) NOT NULL, -- 'Deposits/Withdrawals', 'Broker Interest Paid', etc.
    category VARCHAR(50) NOT NULL, -- 'DEPOSIT', 'WITHDRAWAL', 'INTEREST_PAID', 'FEE', etc.
    
    -- Amounts
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    currency_primary VARCHAR(3) NOT NULL DEFAULT 'HKD',
    
    -- Reference information
    description TEXT,
    ibkr_transaction_id VARCHAR(50) UNIQUE,
    settlement_date DATE,
    account_id VARCHAR(20),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Interest Accruals Table
-- Tracks interest accrual summaries from Interest Accruals FlexQuery
CREATE TABLE IF NOT EXISTS portfolio.interest_accruals (
    accrual_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Period information
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'HKD',
    
    -- Accrual amounts
    starting_balance DECIMAL(15,2),
    interest_accrued DECIMAL(15,2),
    accrual_reversal DECIMAL(15,2),
    fx_translation DECIMAL(15,2),
    ending_balance DECIMAL(15,2),
    
    -- Account reference
    account_id VARCHAR(20),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint for period and currency
    UNIQUE(from_date, to_date, currency)
);

-- Interest Tier Details Table
-- Tracks detailed interest tier information
CREATE TABLE IF NOT EXISTS portfolio.interest_tier_details (
    detail_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Date information
    report_date DATE NOT NULL,
    value_date DATE,
    
    -- Tier details
    currency VARCHAR(3) NOT NULL DEFAULT 'HKD',
    interest_type VARCHAR(50),
    tier_break DECIMAL(15,2),
    balance_threshold DECIMAL(15,2),
    
    -- Principal and interest
    total_principal DECIMAL(15,2),
    margin_balance DECIMAL(15,2),
    rate DECIMAL(10,6), -- Interest rate as decimal
    total_interest DECIMAL(15,2),
    
    -- Account references
    code VARCHAR(50),
    from_acct VARCHAR(20),
    to_acct VARCHAR(20),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(report_date, currency, interest_type, tier_break)
);

-- Indexes for performance
CREATE INDEX idx_cash_transactions_date ON portfolio.cash_transactions(transaction_date DESC);
CREATE INDEX idx_cash_transactions_category ON portfolio.cash_transactions(category);
CREATE INDEX idx_cash_transactions_type ON portfolio.cash_transactions(transaction_type);
CREATE INDEX idx_cash_transactions_account ON portfolio.cash_transactions(account_id);

CREATE INDEX idx_interest_accruals_dates ON portfolio.interest_accruals(from_date, to_date);
CREATE INDEX idx_interest_accruals_currency ON portfolio.interest_accruals(currency);
CREATE INDEX idx_interest_accruals_account ON portfolio.interest_accruals(account_id);

CREATE INDEX idx_interest_tier_date ON portfolio.interest_tier_details(report_date DESC);
CREATE INDEX idx_interest_tier_currency ON portfolio.interest_tier_details(currency);

-- Views for reporting

-- Cash Transactions Summary by Category
CREATE OR REPLACE VIEW portfolio.cash_transactions_summary AS
SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    category,
    currency_primary as currency,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    MIN(transaction_date) as first_transaction,
    MAX(transaction_date) as last_transaction
FROM portfolio.cash_transactions
GROUP BY DATE_TRUNC('month', transaction_date), category, currency_primary
ORDER BY month DESC, category;

-- Interest Accruals Summary
CREATE OR REPLACE VIEW portfolio.interest_accruals_summary AS
SELECT 
    to_date,
    currency,
    starting_balance,
    interest_accrued,
    accrual_reversal,
    fx_translation,
    ending_balance,
    CASE 
        WHEN starting_balance != 0 THEN 
            ROUND((interest_accrued / starting_balance * 365 / (to_date - from_date)) * 100, 4)
        ELSE 0 
    END as annualized_rate_pct
FROM portfolio.interest_accruals
ORDER BY to_date DESC, currency;

-- Daily Cash Flow Analysis
CREATE OR REPLACE VIEW portfolio.daily_cash_flow_analysis AS
SELECT 
    transaction_date,
    SUM(CASE WHEN category = 'DEPOSIT' THEN amount ELSE 0 END) as deposits,
    SUM(CASE WHEN category = 'WITHDRAWAL' THEN amount ELSE 0 END) as withdrawals,
    SUM(CASE WHEN category IN ('INTEREST_PAID', 'INTEREST_RECEIVED') THEN amount ELSE 0 END) as interest,
    SUM(CASE WHEN category = 'FEE' THEN amount ELSE 0 END) as fees,
    SUM(CASE WHEN category = 'COMMISSION_ADJ' THEN amount ELSE 0 END) as commission_adjustments,
    SUM(amount) as net_cash_flow
FROM portfolio.cash_transactions
GROUP BY transaction_date
ORDER BY transaction_date DESC;

-- Triggers

-- Update timestamp trigger
CREATE TRIGGER update_cash_transactions_timestamp
    BEFORE UPDATE ON portfolio.cash_transactions
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

CREATE TRIGGER update_interest_accruals_timestamp
    BEFORE UPDATE ON portfolio.interest_accruals
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

-- Comments
COMMENT ON TABLE portfolio.cash_transactions IS 'Detailed cash transactions from IBKR Cash Transactions FlexQuery';
COMMENT ON TABLE portfolio.interest_accruals IS 'Interest accrual summaries from IBKR Interest Accruals FlexQuery';
COMMENT ON TABLE portfolio.interest_tier_details IS 'Detailed interest tier information for rate analysis';
COMMENT ON VIEW portfolio.cash_transactions_summary IS 'Monthly summary of cash transactions by category';
COMMENT ON VIEW portfolio.interest_accruals_summary IS 'Interest accruals with annualized rate calculation';
COMMENT ON VIEW portfolio.daily_cash_flow_analysis IS 'Daily breakdown of all cash movements';