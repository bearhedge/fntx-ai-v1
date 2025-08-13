#!/usr/bin/env python3
"""
Test direct authentication with pre-authorized access token
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_authentication():
    """Test using pre-authorized access token"""
    print("\n" + "="*60)
    print("DIRECT AUTHENTICATION TEST")
    print("="*60)
    
    try:
        # Initialize auth handler
        auth = IBRestAuth()
        
        # Set access token directly
        auth.access_token = os.getenv('IB_ACCESS_TOKEN')
        auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
        
        print(f"Consumer Key: {auth.consumer_key}")
        print(f"Access Token: {auth.access_token}")
        print(f"Access Token Secret: {auth.access_token_secret[:50]}...")
        print(f"Realm: {auth.realm}")
        
        # Try to get live session token directly
        print("\n" + "-"*60)
        print("Getting Live Session Token")
        print("-"*60)
        
        if auth.get_live_session_token():
            print("✅ Got live session token!")
            
            # Try to initialize brokerage session
            print("\n" + "-"*60)
            print("Initializing Brokerage Session")
            print("-"*60)
            
            if auth.init_brokerage_session():
                print("✅ Brokerage session initialized!")
                
                # Test API access
                print("\n" + "-"*60)
                print("Testing API Access")
                print("-"*60)
                
                accounts = auth.get_accounts()
                if accounts:
                    print(f"✅ Found {len(accounts)} accounts:")
                    for account in accounts:
                        print(f"   {account}")
                else:
                    print("❌ Could not retrieve accounts")
            else:
                print("❌ Failed to initialize brokerage session")
        else:
            print("❌ Failed to get live session token")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_authentication()