-- Test synthetic markers in output
-- Show events on July 28th with synthetic status

SELECT 
    event_timestamp at time zone 'US/Eastern' as time_et,
    event_type,
    description,
    realized_pnl_hkd,
    CASE 
        WHEN is_synthetic = TRUE THEN 'YES - Synthetic'
        ELSE 'NO - From IBKR'
    END as is_synthetic_event
FROM alm_reporting.chronological_events
WHERE date(event_timestamp at time zone 'US/Eastern') = '2025-07-28'
  AND event_type IN ('Option_Expiration', 'Option_Assignment', 'Trade')
ORDER BY event_timestamp;

-- Also check if we properly marked the Buy @ 0 trades
SELECT 
    event_timestamp at time zone 'US/Eastern' as time_et,
    event_type,
    description,
    source_transaction_id,
    is_synthetic
FROM alm_reporting.chronological_events
WHERE date(event_timestamp at time zone 'US/Eastern') = '2025-07-28'
  AND description LIKE '%Buy%@%0%'
ORDER BY event_timestamp;