#!/bin/bash
# Setup script for NAV reconciliation and IBKR data import

echo "NAV Reconciliation Setup Script"
echo "=============================="
echo ""

# Check if credentials are set
if [ -z "$IBKR_FLEX_TOKEN" ] || [ -z "$IBKR_FLEX_QUERY_ID" ]; then
    echo "⚠️  IBKR Flex Query credentials not configured!"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export IBKR_FLEX_TOKEN='your_flex_token'"
    echo "  export IBKR_FLEX_QUERY_ID='your_query_id'"
    echo ""
    echo "You can get these from IBKR Account Management:"
    echo "1. Log into IBKR Account Management"
    echo "2. Go to Reports/Tax Docs > Flex Queries"
    echo "3. Create a new Flex Query with:"
    echo "   - Account Information"
    echo "   - Cash Transactions"
    echo "   - Trades"
    echo "   - Positions"
    echo "4. Save and get the Query ID and Token"
    echo ""
    echo "Once configured, run this script again to import data."
    exit 1
fi

echo "✅ IBKR credentials configured"
echo ""

# Run the historical data import
echo "📊 Fetching historical NAV and trade data..."
cd /home/info/fntx-ai-v1
python3 backend/scripts/fetch_historical_nav_data.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "The following services are now available:"
echo ""
echo "1. NAV Tracking - Daily net asset value snapshots"
echo "2. Cash Movements - Withdrawal and deposit tracking"
echo "3. Reconciliation - Daily balance verification"
echo "4. API Endpoints:"
echo "   - GET  /api/portfolio/nav/current - Current portfolio status"
echo "   - GET  /api/portfolio/nav/history - NAV history"
echo "   - POST /api/portfolio/withdrawals - Create withdrawal"
echo "   - GET  /api/portfolio/withdrawals - Withdrawal history"
echo "   - GET  /api/portfolio/reconciliation/status - Reconciliation status"
echo "   - POST /api/portfolio/reconciliation/run - Run reconciliation"
echo ""
echo "The system will now track:"
echo "- Daily opening/closing NAV"
echo "- All deposits and withdrawals"
echo "- Trading P&L"
echo "- Automatic reconciliation ensuring: Closing NAV = Opening NAV + P&L - Withdrawals + Deposits"