-- Fix deposit timestamps to 8 AM ET instead of 4 PM ET
-- This ensures deposits are recognized as occurring before market open

UPDATE alm_reporting.chronological_events
SET event_timestamp = event_timestamp - INTERVAL '8 hours'
WHERE event_type = 'Deposits/Withdrawals'
  AND cash_impact_hkd > 0  -- Only deposits
  AND EXTRACT(HOUR FROM event_timestamp AT TIME ZONE 'US/Eastern') = 16;  -- Currently at 4 PM

-- Verify the change for July 28th
SELECT 
    DATE(event_timestamp AT TIME ZONE 'US/Eastern') as date,
    event_timestamp AT TIME ZONE 'US/Eastern' as timestamp_et,
    event_type,
    description,
    cash_impact_hkd
FROM alm_reporting.chronological_events
WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = '2025-07-28'
  AND event_type = 'Deposits/Withdrawals'
ORDER BY event_timestamp;