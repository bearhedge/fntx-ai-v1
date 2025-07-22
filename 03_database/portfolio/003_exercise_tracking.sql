-- Exercise Tracking Table
-- Tracks option exercises and their disposal status

CREATE TABLE IF NOT EXISTS portfolio.option_exercises (
    exercise_id SERIAL PRIMARY KEY,
    exercise_date DATE NOT NULL,
    option_symbol VARCHAR(50) NOT NULL,
    strike_price DECIMAL(10,2) NOT NULL,
    option_type VARCHAR(4) CHECK (option_type IN ('PUT', 'CALL')),
    contracts INTEGER NOT NULL,
    shares_received INTEGER NOT NULL,
    detection_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    disposal_order_id VARCHAR(50),
    disposal_price DECIMAL(10,2),
    disposal_time TIMESTAMP WITH TIME ZONE,
    disposal_status VARCHAR(20) DEFAULT 'PENDING',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_exercise UNIQUE (option_symbol, exercise_date),
    CONSTRAINT valid_disposal_status CHECK (disposal_status IN ('PENDING', 'ORDER_PLACED', 'FILLED', 'PARTIAL', 'CANCELLED', 'FAILED'))
);

-- Index for quick lookup of pending disposals
CREATE INDEX idx_pending_disposals ON portfolio.option_exercises(disposal_status) 
WHERE disposal_status = 'PENDING';

-- Index for date-based queries
CREATE INDEX idx_exercise_date ON portfolio.option_exercises(exercise_date DESC);

-- Comments
COMMENT ON TABLE portfolio.option_exercises IS 'Tracks option exercises and their disposal status';
COMMENT ON COLUMN portfolio.option_exercises.exercise_id IS 'Unique identifier for the exercise event';
COMMENT ON COLUMN portfolio.option_exercises.exercise_date IS 'Date when the option was exercised';
COMMENT ON COLUMN portfolio.option_exercises.option_symbol IS 'Full option symbol (e.g., SPY 250715P00622000)';
COMMENT ON COLUMN portfolio.option_exercises.strike_price IS 'Strike price of the exercised option';
COMMENT ON COLUMN portfolio.option_exercises.option_type IS 'PUT or CALL';
COMMENT ON COLUMN portfolio.option_exercises.contracts IS 'Number of contracts exercised';
COMMENT ON COLUMN portfolio.option_exercises.shares_received IS 'Number of shares received (contracts * 100)';
COMMENT ON COLUMN portfolio.option_exercises.detection_time IS 'When the exercise was detected by our system';
COMMENT ON COLUMN portfolio.option_exercises.disposal_order_id IS 'IB order ID for the disposal order';
COMMENT ON COLUMN portfolio.option_exercises.disposal_price IS 'Price at which disposal order was placed';
COMMENT ON COLUMN portfolio.option_exercises.disposal_time IS 'When the disposal order was placed';
COMMENT ON COLUMN portfolio.option_exercises.disposal_status IS 'Current status of the disposal';

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION portfolio.update_exercise_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update the timestamp
CREATE TRIGGER update_exercise_timestamp
    BEFORE UPDATE ON portfolio.option_exercises
    FOR EACH ROW
    EXECUTE FUNCTION portfolio.update_exercise_timestamp();

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE portfolio.option_exercises TO info;
GRANT USAGE ON SEQUENCE portfolio.option_exercises_exercise_id_seq TO info;