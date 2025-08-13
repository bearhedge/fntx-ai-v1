-- Report showing synthetic vs actual events and validation status

-- Summary of synthetic events
SELECT 
    'Summary' as report_section,
    COUNT(*) FILTER (WHERE is_synthetic = TRUE) as synthetic_events,
    COUNT(*) FILTER (WHERE is_synthetic = FALSE OR is_synthetic IS NULL) as actual_events,
    COUNT(*) FILTER (WHERE is_synthetic = TRUE AND synthetic_validated = TRUE) as validated_synthetic,
    COUNT(*) FILTER (WHERE is_synthetic = TRUE AND synthetic_validated = FALSE) as contradicted_synthetic,
    COUNT(*) FILTER (WHERE is_synthetic = TRUE AND synthetic_validated IS NULL) as unvalidated_synthetic
FROM alm_reporting.chronological_events
WHERE event_type IN ('Option_Assignment', 'Option_Expiration', 'Option_Assignment_Assumed');

-- Detailed list of synthetic events
SELECT 
    event_timestamp at time zone 'US/Eastern' as event_time_et,
    event_type,
    description,
    realized_pnl_hkd,
    CASE 
        WHEN synthetic_validated IS TRUE THEN 'Validated ✓'
        WHEN synthetic_validated IS FALSE THEN 'Contradicted ✗'
        ELSE 'Not Yet Validated'
    END as validation_status,
    ibkr_exercise_time at time zone 'US/Eastern' as actual_time_et
FROM alm_reporting.chronological_events
WHERE is_synthetic = TRUE
ORDER BY event_timestamp DESC
LIMIT 20;

-- Show any contradicted events (where IBKR data differs from assumptions)
SELECT 
    event_timestamp at time zone 'US/Eastern' as event_time_et,
    event_type,
    description,
    realized_pnl_hkd,
    'IBKR data contradicts this assumption' as note
FROM alm_reporting.chronological_events
WHERE is_synthetic = TRUE 
  AND synthetic_validated = FALSE
ORDER BY event_timestamp DESC;