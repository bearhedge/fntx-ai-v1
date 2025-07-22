# Greeks vs OHLC Discrepancy Explanation

## Summary
- **OHLC bars**: 1,401,017
- **Greeks bars**: 1,558,275  
- **Difference**: 157,258 (11.2% more Greeks)

## Key Finding
You were correct to question the logic! Here's what's happening:

1. **The 60-bar filter applies to OHLC data only**
   - Contracts must have at least 60 OHLC bars (5 hours of trading) to be included
   - This ensures we only keep liquid contracts with sufficient trading activity

2. **EVERY OHLC bar has corresponding Greeks**
   - Our investigation found ZERO cases where OHLC exists without Greeks
   - This is correct behavior - whenever there's a trade, Greeks are calculated

3. **Greeks exist at timestamps WITHOUT trades**
   - ThetaData calculates theoretical Greeks even when no trades occur
   - Common at market open (9:30), close (16:00), and during low activity periods
   - Example: Jan 3, 2023 $385 Put has Greeks at 13:15 and 16:00 with no trades

## The Numbers Breakdown
For contracts that passed the 60-bar filter:
- **1,296,506** timestamps have BOTH OHLC and Greeks (matching data)
- **0** timestamps have OHLC without Greeks (good - this should never happen)
- **47,126** timestamps have Greeks without OHLC (theoretical calculations)

However, the total database counts are higher because:
- Some contracts exist in the database with <60 OHLC bars (filtered out but still stored)
- These filtered contracts may have Greeks data

## Why This Makes Sense
1. **Greeks are model-based calculations** that can be computed anytime:
   - Using underlying price, strike, time to expiration, interest rates, and volatility
   - Don't require actual option trades to calculate

2. **OHLC requires actual trades** to record:
   - Open, High, Low, Close prices only exist when someone trades

3. **The filter ensures quality** by requiring 60+ trading bars:
   - But Greeks are still calculated and stored for all timestamps
   - This provides continuous theoretical values even during quiet periods

## Conclusion
The discrepancy is normal and expected. It shows that:
- Our data is complete (no missing Greeks for traded periods)
- We have additional theoretical Greeks for analysis
- The 60-bar filter successfully identifies liquid contracts while preserving all Greeks data