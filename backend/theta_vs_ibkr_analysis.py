#!/usr/bin/env python3
"""
Cost-benefit analysis: ThetaData vs IBKR data subscriptions
"""

# ThetaData Standard Pricing
theta_standard_monthly = 75  # $75/month for Standard with Greeks
theta_standard_yearly = theta_standard_monthly * 12  # $900/year

# IBKR Market Data Pricing
ibkr_opra_top = 4.50  # OPRA Top Of Book
ibkr_opra_full = 65   # OPRA Full (all exchanges, full depth)
ibkr_monthly = ibkr_opra_full  # Assuming you need full OPRA
ibkr_yearly = ibkr_monthly * 12  # $780/year

# Download & Refresh Strategy (3 months on, 9 months off)
download_strategy_yearly = theta_standard_monthly * 3  # $225/year

print("=== DATA SUBSCRIPTION COST ANALYSIS ===\n")

print("Option 1: ThetaData Continuous Subscription")
print(f"Monthly cost: ${theta_standard_monthly}")
print(f"Yearly cost: ${theta_standard_yearly}")
print("✅ Pros:")
print("  - Continuous access to historical data")
print("  - Real-time Greeks and IV")
print("  - 4+ years of historical options data")
print("  - Expired options data (IBKR doesn't have)")
print("  - Simple API, no connection issues")
print("❌ Cons:")
print("  - Higher cost")
print("  - Not real-time during market hours")
print()

print("Option 2: IBKR Market Data")
print(f"Monthly cost: ${ibkr_monthly}")
print(f"Yearly cost: ${ibkr_yearly}")
print(f"Savings vs ThetaData: ${theta_standard_yearly - ibkr_yearly}/year")
print("✅ Pros:")
print("  - Real-time streaming data")
print("  - Live Greeks calculated by IBKR")
print("  - Integrated with trading execution")
print("  - Slightly cheaper (~$120/year savings)")
print("❌ Cons:")
print("  - NO historical data on expired options")
print("  - Complex connection management")
print("  - No backtesting capability")
print("  - Must maintain IB Gateway connection")
print()

print("Option 3: Download & Refresh Strategy")
print(f"3 months/year cost: ${download_strategy_yearly}")
print(f"Savings vs continuous: ${theta_standard_yearly - download_strategy_yearly}/year")
print("✅ Pros:")
print("  - Massive cost savings ($675/year)")
print("  - Still get historical data for backtesting")
print("  - Can time subscriptions for important periods")
print("❌ Cons:")
print("  - No real-time data for 9 months")
print("  - Greeks/IV only during active months")
print("  - May miss important market events")
print("  - Manual process every 3 months")
print()

print("=== RECOMMENDATION FOR YOUR USE CASE ===")
print()
print("Given that you're:")
print("1. Selling SPY options (need current Greeks/IV)")
print("2. Want to backtest strategies")
print("3. Mentioned cost consciousness")
print()
print("RECOMMENDED: Hybrid Approach")
print("-" * 40)
print("1. Use ThetaData Standard for 1 month (July 18 - Aug 18)")
print("   - Download ALL historical data")
print("   - Store in local database")
print("   Cost: $75")
print()
print("2. Switch to IBKR for real-time trading")
print("   - Real-time Greeks for active positions")
print("   - Lower ongoing cost")
print("   Cost: $65/month")
print()
print("3. Resubscribe to ThetaData quarterly for 1 month")
print("   - Update historical database")
print("   - Backtest new strategies")
print("   Cost: $75 x 4 = $300/year")
print()
print("Total Annual Cost: $75 + ($65 x 11) + ($75 x 3) = $1,015")
print("vs Pure ThetaData: $900/year")
print("vs Pure IBKR: $780/year (but no historical)")
print()
print("You pay $235 more than pure IBKR but get:")
print("- Complete historical dataset")
print("- Quarterly updates")
print("- Best of both worlds")