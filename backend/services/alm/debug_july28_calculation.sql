-- Debug July 28th calculation

-- Get summary data
SELECT 
    opening_nav_hkd,
    closing_nav_hkd,
    total_pnl_hkd as gross_pnl,
    net_cash_flow_hkd
FROM alm_reporting.daily_summary
WHERE summary_date = '2025-07-28';

-- Get deposits before market open
SELECT 
    SUM(cash_impact_hkd) as deposits_before_open,
    STRING_AGG(event_timestamp AT TIME ZONE 'US/Eastern'::text || ' - ' || cash_impact_hkd::text, ', ') as deposit_details
FROM alm_reporting.chronological_events
WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = '2025-07-28'
AND event_type = 'Deposits/Withdrawals'
AND cash_impact_hkd > 0
AND EXTRACT(HOUR FROM event_timestamp AT TIME ZONE 'US/Eastern') < 9.5;

-- Get total commissions
SELECT 
    SUM(ib_commission_hkd) as total_commissions,
    COUNT(*) as commission_count
FROM alm_reporting.chronological_events
WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = '2025-07-28';

-- Get realized P&L breakdown
SELECT 
    event_type,
    SUM(realized_pnl_hkd) as total_realized_pnl,
    COUNT(*) as event_count
FROM alm_reporting.chronological_events
WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = '2025-07-28'
GROUP BY event_type
ORDER BY event_type;

-- Show the trades with P&L
SELECT 
    event_timestamp AT TIME ZONE 'US/Eastern' as time_et,
    event_type,
    description,
    cash_impact_hkd,
    realized_pnl_hkd,
    ib_commission_hkd
FROM alm_reporting.chronological_events
WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = '2025-07-28'
AND event_type = 'Trade'
ORDER BY event_timestamp;