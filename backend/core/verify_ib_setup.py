#!/usr/bin/env python3
"""
Quick verification of IB REST API setup
Checks environment variables and file paths
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'

print(f"Looking for .env at: {env_path}")
if env_path.exists():
    load_dotenv(env_path)
    print("✅ Loaded .env file")
else:
    print("❌ No .env file found")

print("\nEnvironment Variables:")
print("-" * 40)

# Check critical variables
vars_to_check = {
    'IB_CONSUMER_KEY': 'Consumer Key',
    'IB_ACCESS_TOKEN_SECRET': 'Access Token Secret',
    'IB_SIGNATURE_KEY_PATH': 'Signature Key Path',
    'IB_ENCRYPTION_KEY_PATH': 'Encryption Key Path', 
    'IB_DH_PARAM_PATH': 'DH Param Path'
}

for var, name in vars_to_check.items():
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if 'SECRET' in var or 'KEY' in var and 'PATH' not in var:
            if len(value) > 10:
                display = f"{value[:6]}...{value[-4:]}"
            else:
                display = "***SET***"
        else:
            display = value
        print(f"✅ {name}: {display}")
        
        # Check if file exists for path variables
        if 'PATH' in var:
            if os.path.exists(value):
                print(f"   ✅ File exists")
            else:
                print(f"   ❌ File NOT found at: {value}")
    else:
        print(f"❌ {name}: NOT SET")

print("\nNext Steps:")
print("-" * 40)
print("1. If variables are missing, update: /home/info/fntx-ai-v1/config/.env")
print("2. If key files don't exist, run: /home/info/fntx-ai-v1/backend/scripts/generate_ib_keys.sh")
print("3. Then test with: python /home/info/fntx-ai-v1/backend/core/test_ib_rest_auth.py")