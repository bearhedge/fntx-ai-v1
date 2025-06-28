#\!/bin/bash
export IBKR_FLEX_TOKEN="355054594472094189405478"
export IBKR_FLEX_QUERY_ID="1243757"
export PYTHONPATH="/home/info/fntx-ai-v1"

echo "Starting IBKR Flex Query import..."
cd /home/info/fntx-ai-v1

# Try the direct import
python3 -c "
import sys
sys.path.append('/home/info/fntx-ai-v1')
from backend.services.ibkr_flex_query import IBKRFlexQueryService
from backend.scripts.import_flex_trades import import_matched_trades
import asyncio

async def run_import():
    service = IBKRFlexQueryService()
    print(f'Credentials configured: Token={bool(service.token)}, Query={bool(service.query_id)}')
    
    # Request report
    reference_code = service.request_flex_report()
    if reference_code:
        print(f'Report requested: {reference_code}')
        xml_data = service.get_flex_report(reference_code, max_retries=15)
        if xml_data and len(xml_data) > 1000:
            print(f'Report received: {len(xml_data)} chars')
            trades = service.parse_trades_from_xml(xml_data)
            print(f'Parsed {len(trades)} trades')
            if trades:
                matched = service.match_opening_closing_trades(trades)
                print(f'Matched {len(matched)} trade pairs')
                result = import_matched_trades(matched)
                print(f'Import result: {result}')
        else:
            print('Report not ready or empty')
    else:
        print('Failed to request report')

asyncio.run(run_import())
"
