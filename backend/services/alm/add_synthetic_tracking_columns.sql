-- Add columns to track synthetic vs actual events and validation status
ALTER TABLE alm_reporting.chronological_events 
ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS synthetic_validated BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS ibkr_exercise_time TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add comments to explain the columns
COMMENT ON COLUMN alm_reporting.chronological_events.is_synthetic IS 
'TRUE if event was created by assumption logic, FALSE if from actual IBKR data';

COMMENT ON COLUMN alm_reporting.chronological_events.synthetic_validated IS 
'TRUE if synthetic event was later confirmed by IBKR data, FALSE if contradicted, NULL if not yet checked';

COMMENT ON COLUMN alm_reporting.chronological_events.ibkr_exercise_time IS 
'Actual exercise/expiration time from IBKR when available';

-- Create index for efficient synthetic event lookups
CREATE INDEX IF NOT EXISTS idx_synthetic_events 
ON alm_reporting.chronological_events(is_synthetic, synthetic_validated) 
WHERE event_type IN ('Option_Assignment', 'Option_Expiration', 'Option_Assignment_Assumed');

-- Update existing events to mark them as synthetic based on description patterns
UPDATE alm_reporting.chronological_events
SET is_synthetic = TRUE
WHERE (description LIKE '%ASSUMED%' 
   OR description LIKE '%[SYNTHETIC]%'
   OR event_type = 'Option_Assignment_Assumed')
  AND is_synthetic IS FALSE;