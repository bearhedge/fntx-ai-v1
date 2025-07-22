-- Investigate Greeks vs OHLC discrepancy
-- Question: Why are there 11.2% more Greeks/IV bars than OHLC bars?

-- 1. First, get exact counts from both tables
WITH counts AS (
    SELECT 
        'OHLC' as data_type,
        COUNT(*) as row_count
    FROM theta.options_ohlc
    
    UNION ALL
    
    SELECT 
        'Greeks' as data_type,
        COUNT(*) as row_count
    FROM theta.options_greeks
    
    UNION ALL
    
    SELECT 
        'IV' as data_type,
        COUNT(*) as row_count
    FROM theta.options_iv
)
SELECT * FROM counts;

-- 2. Find contracts that have Greeks but no OHLC data
WITH contract_counts AS (
    SELECT 
        c.contract_id,
        c.symbol,
        c.expiration,
        c.strike,
        c.option_type,
        COUNT(DISTINCT o.datetime) as ohlc_count,
        COUNT(DISTINCT g.datetime) as greeks_count,
        COUNT(DISTINCT iv.datetime) as iv_count
    FROM theta.options_contracts c
    LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
    LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id
    WHERE c.expiration >= '2023-01-01'
    GROUP BY c.contract_id, c.symbol, c.expiration, c.strike, c.option_type
)
SELECT 
    COUNT(*) as contracts_with_greeks_no_ohlc,
    SUM(greeks_count) as total_greeks_bars_without_ohlc
FROM contract_counts
WHERE greeks_count > 0 AND ohlc_count = 0;

-- 3. Sample specific contracts with Greeks but no OHLC
WITH contract_counts AS (
    SELECT 
        c.contract_id,
        c.symbol,
        c.expiration,
        c.strike,
        c.option_type,
        COUNT(DISTINCT o.datetime) as ohlc_count,
        COUNT(DISTINCT g.datetime) as greeks_count
    FROM theta.options_contracts c
    LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
    WHERE c.expiration >= '2023-01-01'
    GROUP BY c.contract_id, c.symbol, c.expiration, c.strike, c.option_type
)
SELECT 
    contract_id,
    expiration,
    strike,
    option_type,
    ohlc_count,
    greeks_count
FROM contract_counts
WHERE greeks_count > 0 AND ohlc_count = 0
ORDER BY expiration, strike
LIMIT 10;

-- 4. Check for duplicate Greeks entries per timestamp
WITH duplicate_greeks AS (
    SELECT 
        contract_id,
        datetime,
        COUNT(*) as dup_count
    FROM theta.options_greeks
    GROUP BY contract_id, datetime
    HAVING COUNT(*) > 1
)
SELECT COUNT(*) as contracts_with_duplicate_greeks
FROM duplicate_greeks;

-- 5. Check timestamp alignment between OHLC and Greeks
WITH sample_contract AS (
    SELECT contract_id 
    FROM theta.options_contracts 
    WHERE expiration = '2023-01-03' 
    AND strike = 385 
    AND option_type = 'P'
    LIMIT 1
),
timestamps AS (
    SELECT 
        'OHLC' as source,
        datetime
    FROM theta.options_ohlc
    WHERE contract_id = (SELECT contract_id FROM sample_contract)
    
    UNION ALL
    
    SELECT 
        'Greeks' as source,
        datetime
    FROM theta.options_greeks
    WHERE contract_id = (SELECT contract_id FROM sample_contract)
)
SELECT 
    datetime,
    COUNT(CASE WHEN source = 'OHLC' THEN 1 END) as has_ohlc,
    COUNT(CASE WHEN source = 'Greeks' THEN 1 END) as has_greeks
FROM timestamps
GROUP BY datetime
ORDER BY datetime
LIMIT 20;

-- 6. Distribution of bar counts per contract
WITH contract_bar_counts AS (
    SELECT 
        c.contract_id,
        c.expiration,
        COUNT(DISTINCT o.datetime) as ohlc_bars,
        COUNT(DISTINCT g.datetime) as greeks_bars
    FROM theta.options_contracts c
    LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
    WHERE c.expiration >= '2023-01-01'
    GROUP BY c.contract_id, c.expiration
)
SELECT 
    CASE 
        WHEN ohlc_bars = 0 THEN '0 OHLC bars'
        WHEN ohlc_bars < 60 THEN '1-59 OHLC bars'
        WHEN ohlc_bars >= 60 THEN '60+ OHLC bars'
    END as ohlc_category,
    COUNT(*) as contract_count,
    SUM(greeks_bars) as total_greeks_bars
FROM contract_bar_counts
GROUP BY 
    CASE 
        WHEN ohlc_bars = 0 THEN '0 OHLC bars'
        WHEN ohlc_bars < 60 THEN '1-59 OHLC bars'
        WHEN ohlc_bars >= 60 THEN '60+ OHLC bars'
    END
ORDER BY ohlc_category;