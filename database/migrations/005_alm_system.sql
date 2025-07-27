-- Asset Liability Management (ALM) Schema
-- Enterprise-grade financial infrastructure for comprehensive asset/liability tracking
-- Implements double-entry accounting with full audit trail

-- Create financial schema
CREATE SCHEMA IF NOT EXISTS financial;

-- =====================================================
-- CHART OF ACCOUNTS
-- =====================================================

-- Account types enum
DO $$ BEGIN
    CREATE TYPE financial.account_type AS ENUM (
        'asset',           -- Assets (cash, securities, receivables)
        'liability',       -- Liabilities (payables, borrowed securities, margin debt)
        'equity',          -- Owner's equity (capital, retained earnings)
        'revenue',         -- Income (trading gains, interest income, dividends)
        'expense'          -- Expenses (commissions, fees, interest expense)
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Account subtypes for detailed categorization
DO $$ BEGIN
    CREATE TYPE financial.account_subtype AS ENUM (
        -- Asset subtypes
        'current_assets', 'securities', 'derivatives', 'cash_equivalents',
        -- Liability subtypes  
        'current_liabilities', 'margin_debt', 'securities_borrowed',
        -- Equity subtypes
        'capital', 'retained_earnings', 'unrealized_gains',
        -- Revenue subtypes
        'trading_income', 'interest_income', 'dividend_income', 'other_income',
        -- Expense subtypes
        'trading_expenses', 'interest_expense', 'operational_expenses'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Chart of Accounts - Foundation of ALM system
CREATE TABLE IF NOT EXISTS financial.chart_of_accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    account_type financial.account_type NOT NULL,
    account_subtype financial.account_subtype,
    parent_account_id UUID REFERENCES financial.chart_of_accounts(account_id),
    
    -- Account properties
    is_active BOOLEAN DEFAULT true,
    normal_balance financial.account_type NOT NULL, -- 'asset'/'expense' = debit, 'liability'/'equity'/'revenue' = credit
    
    -- Metadata and configuration
    description TEXT,
    external_account_ref VARCHAR(100), -- Reference to IBKR account, etc.
    metadata JSONB DEFAULT '{}',
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system'
);

-- =====================================================
-- JOURNAL ENTRY SYSTEM (Double-Entry Accounting)
-- =====================================================

-- Transaction status enum
DO $$ BEGIN
    CREATE TYPE financial.transaction_status AS ENUM (
        'draft',           -- Being prepared
        'pending',         -- Ready for posting
        'posted',          -- Successfully posted to ledger
        'void'             -- Cancelled/reversed
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Journal Entries - Header for all financial transactions
CREATE TABLE IF NOT EXISTS financial.journal_entries (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_number VARCHAR(50) UNIQUE NOT NULL, -- Sequential numbering
    
    -- Transaction details
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE,
    description TEXT NOT NULL,
    reference VARCHAR(100), -- External reference (trade ID, invoice #, etc.)
    
    -- Source tracking
    source_system VARCHAR(50) NOT NULL, -- 'trading', 'manual', 'import', 'reconciliation'
    source_id VARCHAR(100), -- Original transaction ID
    source_metadata JSONB DEFAULT '{}',
    
    -- Status and control
    status financial.transaction_status DEFAULT 'draft',
    total_debit DECIMAL(20,2) DEFAULT 0,
    total_credit DECIMAL(20,2) DEFAULT 0,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) NOT NULL,
    posted_by VARCHAR(100),
    posted_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure balanced entries
    CONSTRAINT balanced_entry CHECK (total_debit = total_credit)
);

-- Journal Entry Lines - Individual debit/credit lines
CREATE TABLE IF NOT EXISTS financial.journal_lines (
    line_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL REFERENCES financial.journal_entries(entry_id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL, -- Line sequence within entry
    
    -- Account details
    account_id UUID NOT NULL REFERENCES financial.chart_of_accounts(account_id),
    
    -- Amounts (exactly one must be > 0)
    debit_amount DECIMAL(20,2) DEFAULT 0,
    credit_amount DECIMAL(20,2) DEFAULT 0,
    
    -- Line details
    description TEXT,
    quantity DECIMAL(20,8), -- For securities transactions
    unit_price DECIMAL(20,4), -- Price per unit
    
    -- Additional context
    line_metadata JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_debit_credit CHECK (
        (debit_amount > 0 AND credit_amount = 0) OR
        (credit_amount > 0 AND debit_amount = 0)
    ),
    CONSTRAINT positive_amounts CHECK (
        debit_amount >= 0 AND credit_amount >= 0
    ),
    UNIQUE (entry_id, line_number)
);

-- =====================================================
-- POSITION MANAGEMENT
-- =====================================================

-- Position tracking for all instruments
CREATE TABLE IF NOT EXISTS financial.positions (
    position_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Position identification
    account_id UUID NOT NULL REFERENCES financial.chart_of_accounts(account_id),
    instrument_type VARCHAR(50) NOT NULL, -- 'option', 'stock', 'cash', 'futures'
    instrument_id VARCHAR(100) NOT NULL, -- Contract identifier
    symbol VARCHAR(20),
    
    -- Position details
    quantity DECIMAL(20,8) NOT NULL,
    cost_basis DECIMAL(20,2) NOT NULL,
    average_price DECIMAL(20,4),
    
    -- Market valuation
    market_price DECIMAL(20,4),
    market_value DECIMAL(20,2),
    unrealized_pnl DECIMAL(20,2),
    
    -- Risk metrics
    delta_equivalent DECIMAL(20,8), -- For options
    gamma_exposure DECIMAL(20,8),
    theta_exposure DECIMAL(20,8),
    vega_exposure DECIMAL(20,8),
    
    -- Timestamps
    as_of_date TIMESTAMP WITH TIME ZONE NOT NULL,
    first_trade_date TIMESTAMP WITH TIME ZONE,
    last_trade_date TIMESTAMP WITH TIME ZONE,
    
    -- Position metadata
    position_metadata JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint for position tracking
    UNIQUE (account_id, instrument_type, instrument_id, as_of_date)
);

-- =====================================================
-- CASH FLOW TRACKING
-- =====================================================

-- Cash flow categories
DO $$ BEGIN
    CREATE TYPE financial.cash_flow_type AS ENUM (
        'operating',       -- Trading activities, income
        'investing',       -- Asset purchases/sales
        'financing'        -- Capital changes, margin
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Cash flow statement tracking
CREATE TABLE IF NOT EXISTS financial.cash_flows (
    flow_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Flow details
    flow_date TIMESTAMP WITH TIME ZONE NOT NULL,
    account_id UUID NOT NULL REFERENCES financial.chart_of_accounts(account_id),
    flow_type financial.cash_flow_type NOT NULL,
    flow_category VARCHAR(100) NOT NULL, -- 'commissions', 'margin_interest', 'dividends'
    
    -- Amounts
    amount DECIMAL(20,2) NOT NULL, -- Positive = inflow, Negative = outflow
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Context
    description TEXT NOT NULL,
    counterparty VARCHAR(100),
    
    -- Links
    related_entry_id UUID REFERENCES financial.journal_entries(entry_id),
    related_position_id UUID REFERENCES financial.positions(position_id),
    
    -- Metadata
    flow_metadata JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- FINANCIAL PERIODS & REPORTING
-- =====================================================

-- Financial periods for reporting
CREATE TABLE IF NOT EXISTS financial.reporting_periods (
    period_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_name VARCHAR(50) NOT NULL, -- 'Q1 2025', 'Jan 2025'
    period_type VARCHAR(20) NOT NULL, -- 'month', 'quarter', 'year'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_closed BOOLEAN DEFAULT false,
    closed_by VARCHAR(100),
    closed_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE (period_type, start_date, end_date)
);

-- =====================================================
-- RECONCILIATION FRAMEWORK
-- =====================================================

-- Reconciliation status
DO $$ BEGIN
    CREATE TYPE financial.reconciliation_status AS ENUM (
        'pending',
        'matched',
        'exception',
        'resolved'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Reconciliation tracking
CREATE TABLE IF NOT EXISTS financial.reconciliations (
    reconciliation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reconciliation details
    reconciliation_type VARCHAR(50) NOT NULL, -- 'trade_to_ledger', 'cash_balance', 'position'
    reconciliation_date DATE NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    target_system VARCHAR(50) NOT NULL,
    
    -- Results
    status financial.reconciliation_status DEFAULT 'pending',
    total_items INTEGER DEFAULT 0,
    matched_items INTEGER DEFAULT 0,
    exception_items INTEGER DEFAULT 0,
    
    -- Summary
    summary_report JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(100) NOT NULL
);

-- Reconciliation exceptions
CREATE TABLE IF NOT EXISTS financial.reconciliation_exceptions (
    exception_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID NOT NULL REFERENCES financial.reconciliations(reconciliation_id),
    
    -- Exception details
    exception_type VARCHAR(50) NOT NULL, -- 'missing_ledger', 'amount_mismatch', 'timing_difference'
    source_reference VARCHAR(100),
    target_reference VARCHAR(100),
    
    -- Amounts
    source_amount DECIMAL(20,2),
    target_amount DECIMAL(20,2),
    difference_amount DECIMAL(20,2),
    
    -- Details
    description TEXT,
    exception_data JSONB DEFAULT '{}',
    
    -- Resolution
    status financial.reconciliation_status DEFAULT 'exception',
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Chart of Accounts indexes
CREATE INDEX IF NOT EXISTS idx_coa_account_number ON financial.chart_of_accounts(account_number);
CREATE INDEX IF NOT EXISTS idx_coa_account_type ON financial.chart_of_accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_coa_parent_account ON financial.chart_of_accounts(parent_account_id);
CREATE INDEX IF NOT EXISTS idx_coa_active ON financial.chart_of_accounts(is_active);

-- Journal Entry indexes
CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON financial.journal_entries(transaction_date);
CREATE INDEX IF NOT EXISTS idx_journal_entries_source ON financial.journal_entries(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_status ON financial.journal_entries(status);
CREATE INDEX IF NOT EXISTS idx_journal_entries_number ON financial.journal_entries(entry_number);

-- Journal Lines indexes
CREATE INDEX IF NOT EXISTS idx_journal_lines_entry ON financial.journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON financial.journal_lines(account_id);

-- Position indexes
CREATE INDEX IF NOT EXISTS idx_positions_account ON financial.positions(account_id);
CREATE INDEX IF NOT EXISTS idx_positions_instrument ON financial.positions(instrument_type, instrument_id);
CREATE INDEX IF NOT EXISTS idx_positions_date ON financial.positions(as_of_date);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON financial.positions(symbol);

-- Cash Flow indexes
CREATE INDEX IF NOT EXISTS idx_cash_flows_date ON financial.cash_flows(flow_date);
CREATE INDEX IF NOT EXISTS idx_cash_flows_account ON financial.cash_flows(account_id);
CREATE INDEX IF NOT EXISTS idx_cash_flows_type ON financial.cash_flows(flow_type);

-- =====================================================
-- TRIGGERS AND FUNCTIONS
-- =====================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION financial.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_chart_of_accounts_updated_at 
    BEFORE UPDATE ON financial.chart_of_accounts
    FOR EACH ROW EXECUTE FUNCTION financial.update_updated_at_column();

CREATE TRIGGER update_journal_entries_updated_at 
    BEFORE UPDATE ON financial.journal_entries
    FOR EACH ROW EXECUTE FUNCTION financial.update_updated_at_column();

CREATE TRIGGER update_positions_updated_at 
    BEFORE UPDATE ON financial.positions
    FOR EACH ROW EXECUTE FUNCTION financial.update_updated_at_column();

-- Journal entry validation function
CREATE OR REPLACE FUNCTION financial.validate_journal_entry()
RETURNS TRIGGER AS $$
DECLARE
    total_debits DECIMAL(20,2);
    total_credits DECIMAL(20,2);
BEGIN
    -- Calculate totals for the entry
    SELECT 
        COALESCE(SUM(debit_amount), 0),
        COALESCE(SUM(credit_amount), 0)
    INTO total_debits, total_credits
    FROM financial.journal_lines
    WHERE entry_id = NEW.entry_id;
    
    -- Update the journal entry totals
    UPDATE financial.journal_entries
    SET total_debit = total_debits,
        total_credit = total_credits
    WHERE entry_id = NEW.entry_id;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply validation trigger
CREATE TRIGGER validate_journal_lines 
    AFTER INSERT OR UPDATE OR DELETE ON financial.journal_lines
    FOR EACH ROW EXECUTE FUNCTION financial.validate_journal_entry();

-- Add comments
COMMENT ON SCHEMA financial IS 'Asset Liability Management schema - Enterprise-grade financial infrastructure';
COMMENT ON TABLE financial.chart_of_accounts IS 'Chart of accounts for comprehensive asset/liability tracking';
COMMENT ON TABLE financial.journal_entries IS 'Double-entry journal entries for all financial transactions';
COMMENT ON TABLE financial.journal_lines IS 'Individual debit/credit lines for journal entries';
COMMENT ON TABLE financial.positions IS 'Real-time position tracking across all instruments';
COMMENT ON TABLE financial.cash_flows IS 'Cash flow categorization and tracking';
COMMENT ON TABLE financial.reconciliations IS 'Reconciliation framework for audit and control';-- Asset Liability Management Views
-- Comprehensive financial reporting views for enterprise ALM system

-- =====================================================
-- BALANCE SHEET VIEWS
-- =====================================================

-- Account Balances - Real-time balances for all accounts
CREATE OR REPLACE VIEW financial.account_balances AS
WITH account_totals AS (
    SELECT 
        a.account_id,
        a.account_number,
        a.account_name,
        a.account_type,
        a.account_subtype,
        a.normal_balance,
        a.parent_account_id,
        COALESCE(SUM(jl.debit_amount), 0) as total_debits,
        COALESCE(SUM(jl.credit_amount), 0) as total_credits,
        CASE 
            WHEN a.normal_balance = 'asset' OR a.normal_balance = 'expense' THEN
                COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0)
            ELSE
                COALESCE(SUM(jl.credit_amount), 0) - COALESCE(SUM(jl.debit_amount), 0)
        END as balance
    FROM financial.chart_of_accounts a
    LEFT JOIN financial.journal_lines jl ON a.account_id = jl.account_id
    LEFT JOIN financial.journal_entries je ON jl.entry_id = je.entry_id 
        AND je.status = 'posted'
    WHERE a.is_active = true
    GROUP BY a.account_id, a.account_number, a.account_name, a.account_type, 
             a.account_subtype, a.normal_balance, a.parent_account_id
)
SELECT 
    account_id,
    account_number,
    account_name,
    account_type,
    account_subtype,
    normal_balance,
    parent_account_id,
    total_debits,
    total_credits,
    balance,
    ABS(balance) as absolute_balance,
    CASE WHEN balance >= 0 THEN 'positive' ELSE 'negative' END as balance_sign,
    CURRENT_TIMESTAMP as as_of_date
FROM account_totals
ORDER BY account_number;

-- Balance Sheet Summary - Aggregated by account type
CREATE OR REPLACE VIEW financial.balance_sheet_summary AS
SELECT 
    account_type,
    account_subtype,
    COUNT(*) as account_count,
    SUM(CASE WHEN balance > 0 THEN balance ELSE 0 END) as positive_balance,
    SUM(CASE WHEN balance < 0 THEN ABS(balance) ELSE 0 END) as negative_balance,
    SUM(balance) as net_balance,
    CURRENT_TIMESTAMP as as_of_date
FROM financial.account_balances
GROUP BY account_type, account_subtype
ORDER BY 
    CASE account_type 
        WHEN 'asset' THEN 1 
        WHEN 'liability' THEN 2 
        WHEN 'equity' THEN 3 
        WHEN 'revenue' THEN 4 
        WHEN 'expense' THEN 5 
    END,
    account_subtype;

-- Traditional Balance Sheet Format
CREATE OR REPLACE VIEW financial.balance_sheet AS
WITH asset_totals AS (
    SELECT 
        1 as section_order,
        'Assets' as section,
        account_subtype as line_item,
        SUM(balance) as amount
    FROM financial.account_balances
    WHERE account_type = 'asset' AND balance != 0
    GROUP BY account_subtype
),
liability_totals AS (
    SELECT 
        2 as section_order,
        'Liabilities' as section,
        account_subtype as line_item,
        SUM(balance) as amount
    FROM financial.account_balances
    WHERE account_type = 'liability' AND balance != 0
    GROUP BY account_subtype
),
equity_totals AS (
    SELECT 
        3 as section_order,
        'Equity' as section,
        account_subtype as line_item,
        SUM(balance) as amount
    FROM financial.account_balances
    WHERE account_type = 'equity' AND balance != 0
    GROUP BY account_subtype
)
SELECT section_order, section, line_item, amount, CURRENT_TIMESTAMP as as_of_date
FROM asset_totals
UNION ALL
SELECT section_order, section, line_item, amount, CURRENT_TIMESTAMP as as_of_date
FROM liability_totals
UNION ALL
SELECT section_order, section, line_item, amount, CURRENT_TIMESTAMP as as_of_date
FROM equity_totals
ORDER BY section_order, line_item;

-- =====================================================
-- INCOME STATEMENT VIEWS
-- =====================================================

-- Income Statement Detail
CREATE OR REPLACE VIEW financial.income_statement_detail AS
WITH revenue_accounts AS (
    SELECT 
        account_number,
        account_name,
        account_subtype,
        balance as amount
    FROM financial.account_balances
    WHERE account_type = 'revenue' AND balance != 0
),
expense_accounts AS (
    SELECT 
        account_number,
        account_name,
        account_subtype,
        balance as amount
    FROM financial.account_balances
    WHERE account_type = 'expense' AND balance != 0
)
SELECT 
    'Revenue' as section,
    account_number,
    account_name,
    account_subtype as category,
    amount,
    CURRENT_TIMESTAMP as as_of_date
FROM revenue_accounts
UNION ALL
SELECT 
    'Expenses' as section,
    account_number,
    account_name,
    account_subtype as category,
    amount,
    CURRENT_TIMESTAMP as as_of_date
FROM expense_accounts
ORDER BY section DESC, account_number;

-- Income Statement Summary
CREATE OR REPLACE VIEW financial.income_statement_summary AS
WITH revenue_total AS (
    SELECT SUM(balance) as total_revenue
    FROM financial.account_balances
    WHERE account_type = 'revenue'
),
expense_total AS (
    SELECT SUM(balance) as total_expenses
    FROM financial.account_balances
    WHERE account_type = 'expense'
)
SELECT 
    r.total_revenue,
    e.total_expenses,
    (r.total_revenue - e.total_expenses) as net_income,
    CASE 
        WHEN r.total_revenue != 0 THEN 
            ROUND(((r.total_revenue - e.total_expenses) / r.total_revenue * 100), 2)
        ELSE 0 
    END as net_margin_pct,
    CURRENT_TIMESTAMP as as_of_date
FROM revenue_total r, expense_total e;

-- =====================================================
-- CASH FLOW VIEWS
-- =====================================================

-- Cash Flow Summary by Type
CREATE OR REPLACE VIEW financial.cash_flow_summary AS
SELECT 
    flow_type,
    flow_category,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_inflows,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_outflows,
    SUM(amount) as net_cash_flow,
    MIN(flow_date) as earliest_flow,
    MAX(flow_date) as latest_flow
FROM financial.cash_flows
GROUP BY flow_type, flow_category
ORDER BY flow_type, flow_category;

-- Daily Cash Flow Trends
CREATE OR REPLACE VIEW financial.daily_cash_flows AS
SELECT 
    DATE(flow_date) as flow_date,
    flow_type,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as daily_inflows,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as daily_outflows,
    SUM(amount) as net_daily_flow,
    SUM(SUM(amount)) OVER (ORDER BY DATE(flow_date)) as cumulative_flow
FROM financial.cash_flows
GROUP BY DATE(flow_date), flow_type
ORDER BY flow_date DESC, flow_type;

-- Cash Position Analysis
CREATE OR REPLACE VIEW financial.cash_positions AS
SELECT 
    a.account_number,
    a.account_name,
    a.external_account_ref,
    ab.balance as cash_balance,
    a.metadata->>'currency' as currency,
    CASE 
        WHEN ab.balance > 0 THEN 'positive'
        WHEN ab.balance < 0 THEN 'negative' 
        ELSE 'zero'
    END as balance_status,
    ab.as_of_date
FROM financial.chart_of_accounts a
JOIN financial.account_balances ab ON a.account_id = ab.account_id
WHERE a.account_subtype = 'cash_equivalents'
    AND a.is_active = true
ORDER BY ab.balance DESC;

-- =====================================================
-- POSITION MANAGEMENT VIEWS
-- =====================================================

-- Current Positions Summary
CREATE OR REPLACE VIEW financial.current_positions AS
SELECT 
    p.instrument_type,
    p.symbol,
    COUNT(*) as position_count,
    SUM(p.quantity) as total_quantity,
    SUM(p.cost_basis) as total_cost_basis,
    SUM(p.market_value) as total_market_value,
    SUM(p.unrealized_pnl) as total_unrealized_pnl,
    AVG(p.average_price) as weighted_avg_price,
    MAX(p.as_of_date) as latest_valuation_date
FROM financial.positions p
WHERE p.quantity != 0
GROUP BY p.instrument_type, p.symbol
ORDER BY total_market_value DESC;

-- Options Positions Detail (SPY Focus)
CREATE OR REPLACE VIEW financial.spy_options_positions AS
SELECT 
    p.position_id,
    p.instrument_id,
    p.symbol,
    p.quantity,
    p.cost_basis,
    p.average_price,
    p.market_value,
    p.unrealized_pnl,
    p.delta_equivalent,
    p.gamma_exposure,
    p.theta_exposure,
    p.vega_exposure,
    CASE 
        WHEN p.quantity > 0 THEN 'Long'
        WHEN p.quantity < 0 THEN 'Short'
        ELSE 'Flat'
    END as position_direction,
    p.as_of_date,
    p.position_metadata
FROM financial.positions p
WHERE p.instrument_type = 'option' 
    AND p.symbol = 'SPY'
    AND p.quantity != 0
ORDER BY p.unrealized_pnl DESC;

-- =====================================================
-- RISK AND PERFORMANCE VIEWS
-- =====================================================

-- Portfolio Risk Metrics
CREATE OR REPLACE VIEW financial.portfolio_risk_metrics AS
WITH position_stats AS (
    SELECT 
        COUNT(*) as total_positions,
        SUM(ABS(market_value)) as gross_exposure,
        SUM(market_value) as net_exposure,
        SUM(unrealized_pnl) as total_unrealized_pnl,
        SUM(ABS(delta_equivalent)) as total_delta_exposure,
        SUM(ABS(gamma_exposure)) as total_gamma_exposure,
        SUM(theta_exposure) as total_theta_exposure,
        SUM(ABS(vega_exposure)) as total_vega_exposure
    FROM financial.positions
    WHERE quantity != 0
),
cash_balance AS (
    SELECT SUM(balance) as total_cash
    FROM financial.account_balances
    WHERE account_subtype = 'cash_equivalents'
)
SELECT 
    ps.total_positions,
    ps.gross_exposure,
    ps.net_exposure,
    cb.total_cash,
    (ps.net_exposure + cb.total_cash) as net_asset_value,
    ps.total_unrealized_pnl,
    CASE 
        WHEN (ps.net_exposure + cb.total_cash) != 0 THEN
            ROUND((ps.total_unrealized_pnl / (ps.net_exposure + cb.total_cash) * 100), 2)
        ELSE 0
    END as unrealized_return_pct,
    ps.total_delta_exposure,
    ps.total_gamma_exposure,
    ps.total_theta_exposure,
    ps.total_vega_exposure,
    CURRENT_TIMESTAMP as as_of_date
FROM position_stats ps, cash_balance cb;

-- Trading Performance Metrics
CREATE OR REPLACE VIEW financial.trading_performance AS
WITH trading_revenue AS (
    SELECT SUM(balance) as total_trading_income
    FROM financial.account_balances
    WHERE account_subtype = 'trading_income'
),
trading_expenses AS (
    SELECT SUM(balance) as total_trading_expenses
    FROM financial.account_balances
    WHERE account_subtype = 'trading_expenses'
),
commission_costs AS (
    SELECT SUM(balance) as total_commissions
    FROM financial.account_balances
    WHERE account_name LIKE '%Commission%'
)
SELECT 
    tr.total_trading_income,
    te.total_trading_expenses,
    cc.total_commissions,
    (tr.total_trading_income - te.total_trading_expenses) as net_trading_pnl,
    CASE 
        WHEN tr.total_trading_income != 0 THEN
            ROUND(((tr.total_trading_income - te.total_trading_expenses) / tr.total_trading_income * 100), 2)
        ELSE 0
    END as trading_margin_pct,
    CASE 
        WHEN tr.total_trading_income != 0 THEN
            ROUND((cc.total_commissions / tr.total_trading_income * 100), 2)
        ELSE 0
    END as commission_rate_pct,
    CURRENT_TIMESTAMP as as_of_date
FROM trading_revenue tr, trading_expenses te, commission_costs cc;

-- =====================================================
-- RECONCILIATION VIEWS
-- =====================================================

-- Journal Entry Audit Trail
CREATE OR REPLACE VIEW financial.journal_audit_trail AS
SELECT 
    je.entry_id,
    je.entry_number,
    je.transaction_date,
    je.description,
    je.source_system,
    je.source_id,
    je.status,
    je.total_debit,
    je.total_credit,
    je.created_by,
    je.created_at,
    je.posted_by,
    je.posted_at,
    COUNT(jl.line_id) as line_count,
    CASE 
        WHEN je.total_debit = je.total_credit THEN 'Balanced'
        ELSE 'Unbalanced'
    END as balance_status
FROM financial.journal_entries je
LEFT JOIN financial.journal_lines jl ON je.entry_id = jl.entry_id
GROUP BY je.entry_id, je.entry_number, je.transaction_date, je.description,
         je.source_system, je.source_id, je.status, je.total_debit, 
         je.total_credit, je.created_by, je.created_at, je.posted_by, je.posted_at
ORDER BY je.transaction_date DESC, je.entry_number DESC;

-- Account Activity Summary
CREATE OR REPLACE VIEW financial.account_activity_summary AS
SELECT 
    a.account_number,
    a.account_name,
    a.account_type,
    COUNT(jl.line_id) as transaction_count,
    SUM(jl.debit_amount) as total_debits,
    SUM(jl.credit_amount) as total_credits,
    MIN(je.transaction_date) as first_transaction,
    MAX(je.transaction_date) as last_transaction,
    ab.balance as current_balance
FROM financial.chart_of_accounts a
LEFT JOIN financial.journal_lines jl ON a.account_id = jl.account_id
LEFT JOIN financial.journal_entries je ON jl.entry_id = je.entry_id AND je.status = 'posted'
LEFT JOIN financial.account_balances ab ON a.account_id = ab.account_id
WHERE a.is_active = true
GROUP BY a.account_id, a.account_number, a.account_name, a.account_type, ab.balance
HAVING COUNT(jl.line_id) > 0
ORDER BY transaction_count DESC;

-- Data Quality Checks
CREATE OR REPLACE VIEW financial.data_quality_checks AS
WITH unbalanced_entries AS (
    SELECT COUNT(*) as unbalanced_count
    FROM financial.journal_entries
    WHERE status = 'posted' AND total_debit != total_credit
),
orphaned_lines AS (
    SELECT COUNT(*) as orphaned_count
    FROM financial.journal_lines jl
    LEFT JOIN financial.journal_entries je ON jl.entry_id = je.entry_id
    WHERE je.entry_id IS NULL
),
inactive_accounts_with_activity AS (
    SELECT COUNT(DISTINCT a.account_id) as inactive_active_count
    FROM financial.chart_of_accounts a
    JOIN financial.journal_lines jl ON a.account_id = jl.account_id
    WHERE a.is_active = false
),
zero_amount_lines AS (
    SELECT COUNT(*) as zero_amount_count
    FROM financial.journal_lines
    WHERE debit_amount = 0 AND credit_amount = 0
)
SELECT 
    ue.unbalanced_count,
    ol.orphaned_count,
    iaa.inactive_active_count,
    zal.zero_amount_count,
    CASE 
        WHEN ue.unbalanced_count = 0 AND ol.orphaned_count = 0 
             AND iaa.inactive_active_count = 0 AND zal.zero_amount_count = 0 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as overall_quality_status,
    CURRENT_TIMESTAMP as check_date
FROM unbalanced_entries ue, orphaned_lines ol, inactive_accounts_with_activity iaa, zero_amount_lines zal;

-- Add view comments
COMMENT ON VIEW financial.account_balances IS 'Real-time account balances with proper debit/credit treatment';
COMMENT ON VIEW financial.balance_sheet IS 'Traditional balance sheet presentation';
COMMENT ON VIEW financial.income_statement_summary IS 'P&L summary with key metrics';
COMMENT ON VIEW financial.cash_flow_summary IS 'Cash flow analysis by type and category';
COMMENT ON VIEW financial.current_positions IS 'Current position holdings and valuations';
COMMENT ON VIEW financial.portfolio_risk_metrics IS 'Portfolio-level risk exposure metrics';
COMMENT ON VIEW financial.trading_performance IS 'Trading strategy performance analysis';
COMMENT ON VIEW financial.data_quality_checks IS 'Automated data quality validation';-- Chart of Accounts Setup for Asset Liability Management
-- Comprehensive account structure for enterprise financial tracking

-- Insert standard chart of accounts structure
INSERT INTO financial.chart_of_accounts (account_number, account_name, account_type, account_subtype, normal_balance, description, created_by) VALUES

-- =====================================================
-- ASSETS (Debit Normal Balance)
-- =====================================================

-- Cash and Cash Equivalents
('1000', 'Assets', 'asset', 'current_assets', 'asset', 'Root asset account', 'system'),
('1100', 'Cash and Cash Equivalents', 'asset', 'cash_equivalents', 'asset', 'Liquid cash positions', 'system'),
('1110', 'USD Cash', 'asset', 'cash_equivalents', 'asset', 'US Dollar cash position', 'system'),
('1111', 'IBKR USD Cash', 'asset', 'cash_equivalents', 'asset', 'Interactive Brokers USD cash', 'system'),
('1120', 'HKD Cash', 'asset', 'cash_equivalents', 'asset', 'Hong Kong Dollar cash position', 'system'),
('1121', 'IBKR HKD Cash', 'asset', 'cash_equivalents', 'asset', 'Interactive Brokers HKD cash', 'system'),
('1130', 'Money Market Funds', 'asset', 'cash_equivalents', 'asset', 'Short-term money market investments', 'system'),

-- Securities and Investments
('1200', 'Securities', 'asset', 'securities', 'asset', 'Marketable securities portfolio', 'system'),
('1210', 'Equity Securities', 'asset', 'securities', 'asset', 'Stock positions', 'system'),
('1211', 'SPY Holdings', 'asset', 'securities', 'asset', 'SPY ETF positions', 'system'),
('1220', 'Fixed Income Securities', 'asset', 'securities', 'asset', 'Bond and fixed income positions', 'system'),

-- Derivatives
('1300', 'Derivatives', 'asset', 'derivatives', 'asset', 'Derivative instruments', 'system'),
('1310', 'Options Positions', 'asset', 'derivatives', 'asset', 'Options contracts owned', 'system'),
('1311', 'SPY Call Options', 'asset', 'derivatives', 'asset', 'SPY call options owned', 'system'),
('1312', 'SPY Put Options', 'asset', 'derivatives', 'asset', 'SPY put options owned', 'system'),
('1320', 'Futures Positions', 'asset', 'derivatives', 'asset', 'Futures contracts', 'system'),

-- Receivables
('1400', 'Receivables', 'asset', 'current_assets', 'asset', 'Amounts due to be received', 'system'),
('1410', 'Dividend Receivables', 'asset', 'current_assets', 'asset', 'Dividends declared but not received', 'system'),
('1420', 'Interest Receivables', 'asset', 'current_assets', 'asset', 'Interest earned but not received', 'system'),
('1430', 'Settlement Receivables', 'asset', 'current_assets', 'asset', 'Trade settlements pending', 'system'),

-- =====================================================
-- LIABILITIES (Credit Normal Balance)
-- =====================================================

-- Current Liabilities
('2000', 'Liabilities', 'liability', 'current_liabilities', 'liability', 'Root liability account', 'system'),
('2100', 'Current Liabilities', 'liability', 'current_liabilities', 'liability', 'Short-term obligations', 'system'),
('2110', 'Accounts Payable', 'liability', 'current_liabilities', 'liability', 'Trade payables', 'system'),
('2120', 'Accrued Expenses', 'liability', 'current_liabilities', 'liability', 'Expenses incurred but not paid', 'system'),
('2121', 'Accrued Commissions', 'liability', 'current_liabilities', 'liability', 'Commission expenses accrued', 'system'),
('2122', 'Accrued Interest Expense', 'liability', 'current_liabilities', 'liability', 'Interest expense accrued', 'system'),

-- Margin and Borrowing
('2200', 'Margin Debt', 'liability', 'margin_debt', 'liability', 'Borrowed funds for trading', 'system'),
('2210', 'IBKR Margin Loan', 'liability', 'margin_debt', 'liability', 'Interactive Brokers margin debt', 'system'),
('2220', 'Interest on Margin', 'liability', 'margin_debt', 'liability', 'Accrued margin interest', 'system'),

-- Securities Borrowed
('2300', 'Securities Borrowed', 'liability', 'securities_borrowed', 'liability', 'Borrowed securities for short selling', 'system'),
('2310', 'Stock Loan Payable', 'liability', 'securities_borrowed', 'liability', 'Securities on loan from others', 'system'),
('2320', 'Borrow Fees Payable', 'liability', 'securities_borrowed', 'liability', 'Fees for borrowed securities', 'system'),

-- Options Liabilities (Short Positions)
('2400', 'Options Liabilities', 'liability', 'current_liabilities', 'liability', 'Short options positions', 'system'),
('2410', 'SPY Call Options Sold', 'liability', 'current_liabilities', 'liability', 'SPY calls sold short', 'system'),
('2411', 'SPY Put Options Sold', 'liability', 'current_liabilities', 'liability', 'SPY puts sold short', 'system'),

-- Settlement Payables
('2500', 'Settlement Payables', 'liability', 'current_liabilities', 'liability', 'Trade settlements due', 'system'),
('2510', 'Trade Settlement Payable', 'liability', 'current_liabilities', 'liability', 'Pending trade settlements', 'system'),

-- =====================================================
-- EQUITY (Credit Normal Balance)
-- =====================================================

-- Owner's Equity
('3000', 'Equity', 'equity', 'capital', 'equity', 'Owner equity accounts', 'system'),
('3100', 'Capital', 'equity', 'capital', 'equity', 'Initial and additional capital', 'system'),
('3110', 'Initial Capital', 'equity', 'capital', 'equity', 'Starting capital contribution', 'system'),
('3120', 'Additional Capital', 'equity', 'capital', 'equity', 'Additional capital contributions', 'system'),

-- Retained Earnings
('3200', 'Retained Earnings', 'equity', 'retained_earnings', 'equity', 'Accumulated profits/losses', 'system'),
('3210', 'Current Year Earnings', 'equity', 'retained_earnings', 'equity', 'Current year profit/loss', 'system'),
('3220', 'Prior Year Earnings', 'equity', 'retained_earnings', 'equity', 'Accumulated prior year earnings', 'system'),

-- Unrealized Gains/Losses
('3300', 'Unrealized Gains/Losses', 'equity', 'unrealized_gains', 'equity', 'Mark-to-market adjustments', 'system'),
('3310', 'Unrealized Securities Gains', 'equity', 'unrealized_gains', 'equity', 'Unrealized gains on securities', 'system'),
('3320', 'Unrealized Options Gains', 'equity', 'unrealized_gains', 'equity', 'Unrealized gains on options', 'system'),

-- =====================================================
-- REVENUE (Credit Normal Balance)
-- =====================================================

-- Trading Income
('4000', 'Revenue', 'revenue', 'trading_income', 'revenue', 'Root revenue account', 'system'),
('4100', 'Trading Income', 'revenue', 'trading_income', 'revenue', 'Profits from trading activities', 'system'),
('4110', 'Realized Options Gains', 'revenue', 'trading_income', 'revenue', 'Realized profits from options trading', 'system'),
('4111', 'SPY Options Premium Income', 'revenue', 'trading_income', 'revenue', 'Premium collected from selling SPY options', 'system'),
('4112', 'Options Closing Gains', 'revenue', 'trading_income', 'revenue', 'Gains from closing options positions', 'system'),
('4120', 'Securities Trading Gains', 'revenue', 'trading_income', 'revenue', 'Gains from stock trading', 'system'),
('4130', 'Foreign Exchange Gains', 'revenue', 'trading_income', 'revenue', 'FX gains on currency conversion', 'system'),

-- Investment Income
('4200', 'Investment Income', 'revenue', 'interest_income', 'revenue', 'Income from investments', 'system'),
('4210', 'Dividend Income', 'revenue', 'dividend_income', 'revenue', 'Dividends received', 'system'),
('4220', 'Interest Income', 'revenue', 'interest_income', 'revenue', 'Interest earned on cash balances', 'system'),
('4230', 'Securities Lending Income', 'revenue', 'other_income', 'revenue', 'Income from lending securities', 'system'),

-- Other Income
('4300', 'Other Income', 'revenue', 'other_income', 'revenue', 'Miscellaneous income', 'system'),
('4310', 'Rebates and Credits', 'revenue', 'other_income', 'revenue', 'Commission rebates and credits', 'system'),

-- =====================================================
-- EXPENSES (Debit Normal Balance)
-- =====================================================

-- Trading Expenses
('5000', 'Expenses', 'expense', 'trading_expenses', 'expense', 'Root expense account', 'system'),
('5100', 'Trading Expenses', 'expense', 'trading_expenses', 'expense', 'Direct trading costs', 'system'),
('5110', 'Commission Expenses', 'expense', 'trading_expenses', 'expense', 'Brokerage commissions', 'system'),
('5111', 'IBKR Commissions', 'expense', 'trading_expenses', 'expense', 'Interactive Brokers commission fees', 'system'),
('5120', 'Trading Fees', 'expense', 'trading_expenses', 'expense', 'Exchange and regulatory fees', 'system'),
('5121', 'SEC Fees', 'expense', 'trading_expenses', 'expense', 'SEC regulatory fees', 'system'),
('5122', 'Exchange Fees', 'expense', 'trading_expenses', 'expense', 'Exchange transaction fees', 'system'),
('5130', 'Realized Trading Losses', 'expense', 'trading_expenses', 'expense', 'Realized losses from trading', 'system'),
('5131', 'SPY Options Losses', 'expense', 'trading_expenses', 'expense', 'Losses from SPY options trading', 'system'),
('5132', 'Securities Trading Losses', 'expense', 'trading_expenses', 'expense', 'Losses from securities trading', 'system'),

-- Financing Expenses
('5200', 'Financing Expenses', 'expense', 'interest_expense', 'expense', 'Cost of borrowed funds', 'system'),
('5210', 'Margin Interest Expense', 'expense', 'interest_expense', 'expense', 'Interest on margin borrowing', 'system'),
('5220', 'Securities Borrowing Fees', 'expense', 'interest_expense', 'expense', 'Fees for borrowing securities', 'system'),

-- Operational Expenses
('5300', 'Operational Expenses', 'expense', 'operational_expenses', 'expense', 'Operating costs', 'system'),
('5310', 'Data Feed Costs', 'expense', 'operational_expenses', 'expense', 'Market data subscriptions', 'system'),
('5311', 'ThetaData Subscription', 'expense', 'operational_expenses', 'expense', 'ThetaData market data costs', 'system'),
('5312', 'IBKR Market Data', 'expense', 'operational_expenses', 'expense', 'IBKR market data fees', 'system'),
('5320', 'Technology Expenses', 'expense', 'operational_expenses', 'expense', 'Technology and infrastructure costs', 'system'),
('5330', 'Professional Services', 'expense', 'operational_expenses', 'expense', 'External professional services', 'system'),

-- FX and Other Expenses  
('5400', 'Foreign Exchange Losses', 'expense', 'operational_expenses', 'expense', 'FX losses on currency conversion', 'system'),
('5500', 'Other Expenses', 'expense', 'operational_expenses', 'expense', 'Miscellaneous expenses', 'system')

ON CONFLICT (account_number) DO NOTHING;

-- Update parent account relationships
UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1000'
) WHERE account_number IN ('1100', '1200', '1300', '1400');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1100'
) WHERE account_number IN ('1110', '1120', '1130');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1110'
) WHERE account_number = '1111';

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1120'
) WHERE account_number = '1121';

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1200'
) WHERE account_number IN ('1210', '1220');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1210'
) WHERE account_number = '1211';

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1300'
) WHERE account_number IN ('1310', '1320');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '1310'
) WHERE account_number IN ('1311', '1312');

-- Liabilities hierarchy
UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '2000'
) WHERE account_number IN ('2100', '2200', '2300', '2400', '2500');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '2100'
) WHERE account_number IN ('2110', '2120');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '2120'
) WHERE account_number IN ('2121', '2122');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '2200'
) WHERE account_number IN ('2210', '2220');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '2300'
) WHERE account_number IN ('2310', '2320');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '2400'
) WHERE account_number IN ('2410', '2411');

-- Equity hierarchy
UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '3000'
) WHERE account_number IN ('3100', '3200', '3300');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '3100'
) WHERE account_number IN ('3110', '3120');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '3200'
) WHERE account_number IN ('3210', '3220');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '3300'
) WHERE account_number IN ('3310', '3320');

-- Revenue hierarchy
UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '4000'
) WHERE account_number IN ('4100', '4200', '4300');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '4100'
) WHERE account_number IN ('4110', '4120', '4130');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '4110'
) WHERE account_number IN ('4111', '4112');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '4200'
) WHERE account_number IN ('4210', '4220', '4230');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '4300'
) WHERE account_number = '4310';

-- Expense hierarchy
UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5000'
) WHERE account_number IN ('5100', '5200', '5300', '5400', '5500');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5100'
) WHERE account_number IN ('5110', '5120', '5130');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5110'
) WHERE account_number = '5111';

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5120'
) WHERE account_number IN ('5121', '5122');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5130'
) WHERE account_number IN ('5131', '5132');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5200'
) WHERE account_number IN ('5210', '5220');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5300'
) WHERE account_number IN ('5310', '5320', '5330');

UPDATE financial.chart_of_accounts SET parent_account_id = (
    SELECT account_id FROM financial.chart_of_accounts WHERE account_number = '5310'
) WHERE account_number IN ('5311', '5312');

-- Add external account references for IBKR integration
UPDATE financial.chart_of_accounts 
SET external_account_ref = 'U19860056'
WHERE account_number IN ('1111', '1121', '2210');

-- Set metadata for key accounts
UPDATE financial.chart_of_accounts 
SET metadata = '{"currency": "USD", "broker": "IBKR", "account_type": "margin"}'
WHERE account_number = '1111';

UPDATE financial.chart_of_accounts 
SET metadata = '{"currency": "HKD", "broker": "IBKR", "account_type": "margin"}'
WHERE account_number = '1121';

UPDATE financial.chart_of_accounts 
SET metadata = '{"instrument_type": "SPY_options", "strategy": "premium_selling"}'
WHERE account_number IN ('2410', '2411', '4111', '5131');