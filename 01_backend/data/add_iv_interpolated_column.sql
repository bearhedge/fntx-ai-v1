-- Add column to track interpolated IV values
ALTER TABLE theta.options_iv 
ADD COLUMN IF NOT EXISTS is_interpolated BOOLEAN DEFAULT FALSE;

-- Create index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_options_iv_interpolated 
ON theta.options_iv(contract_id, is_interpolated);

-- Add comment
COMMENT ON COLUMN theta.options_iv.is_interpolated IS 
'TRUE if IV was interpolated/filled, FALSE if original from API';