#!/usr/bin/env python3
"""
Test OAuth using IBind library to verify our keys work
"""

import os
import sys
from pathlib import Path

# Load environment variables
env_path = Path('/home/info/fntx-ai-v1/config/.env')
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

# Set IBind environment variables
os.environ['IBIND_USE_OAUTH'] = 'True'
os.environ['IBIND_OAUTH1A_CONSUMER_KEY'] = os.environ['IB_CONSUMER_KEY']
os.environ['IBIND_OAUTH1A_ACCESS_TOKEN'] = os.environ['IB_ACCESS_TOKEN']
os.environ['IBIND_OAUTH1A_ACCESS_TOKEN_SECRET'] = os.environ['IB_ACCESS_TOKEN_SECRET']
os.environ['IBIND_OAUTH1A_ENCRYPTION_KEY_FP'] = os.environ['IB_ENCRYPTION_KEY_PATH']
os.environ['IBIND_OAUTH1A_SIGNATURE_KEY_FP'] = os.environ['IB_SIGNATURE_KEY_PATH']
os.environ['IBIND_OAUTH1A_DH_PRIME'] = "e9c0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5ed5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4fb527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e69d2ec0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5ed5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4fb527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e6af"

print("="*70)
print("Testing OAuth with IBind Library")
print("="*70)

print("\nConfiguration:")
print(f"  Consumer Key: {os.environ.get('IBIND_OAUTH1A_CONSUMER_KEY')}")
print(f"  Access Token: {os.environ.get('IBIND_OAUTH1A_ACCESS_TOKEN')}")
print(f"  Has Access Secret: {bool(os.environ.get('IBIND_OAUTH1A_ACCESS_TOKEN_SECRET'))}")
print(f"  Signature Key: {os.environ.get('IBIND_OAUTH1A_SIGNATURE_KEY_FP')}")
print(f"  Encryption Key: {os.environ.get('IBIND_OAUTH1A_ENCRYPTION_KEY_FP')}")

try:
    # Activate virtual environment for IBind
    import subprocess
    result = subprocess.run([
        sys.executable, '-c', '''
import os
os.environ.update({env})

try:
    from ibind import IbkrClient
    
    print("\\nInitializing IBind client with OAuth...")
    client = IbkrClient(use_oauth=True)
    
    print("Attempting to get accounts...")
    response = client.get('/portfolio/accounts')
    
    if response.ok:
        print("✅ SUCCESS! OAuth is working with IBind!")
        print(f"Response: {{response.data}}")
    else:
        print(f"❌ Failed with status {{response.status_code}}")
        print(f"Error: {{response.error}}")
except Exception as e:
    print(f"❌ Error: {{e}}")
    import traceback
    traceback.print_exc()
'''.format(env=repr(dict(os.environ)))
    ], cwd='/home/info/fntx-ai-v1/ibind_venv', capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()