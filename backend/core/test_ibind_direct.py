#!/usr/bin/env python3
"""
Test OAuth directly with IBind library
"""

import os
import sys
import subprocess

# Add IBind virtual environment to path
sys.path.insert(0, '/home/info/fntx-ai-v1/ibind_venv/lib/python3.13/site-packages')

# Set environment variables
os.environ['IBIND_USE_OAUTH'] = 'True'
os.environ['IBIND_OAUTH1A_CONSUMER_KEY'] = 'BEARHEDGE'
os.environ['IBIND_OAUTH1A_ACCESS_TOKEN'] = '8444def5466e38fb8b86'
os.environ['IBIND_OAUTH1A_ACCESS_TOKEN_SECRET'] = 'YGYtDXjRbBaSnC7kDosATGcyUvcWb78Niodek7y5TUcnybAr6IbVgQVckczTUXH9T+8AFc7b3huweDyPGC3wxDXf43luSaTAiIX9kzYs3YNAq/XO2j4fqKdvOO4cY9aTDtGPJCkFz1z/SyHj+usv44V0pUvncuqJ8m/YQy/SBrrs/JzBbD6PFd94IWCrhANdRvePHF65L3kWyeVAv5/1o8YAhZpGx2JCrA3D1vTXNvE/8KDxXn+n9TrlXXBNNpkRG0N/sBB47NdyMAgM6jzxdBdIYgIBlWlqy41E6q4gKlntEbuoFeaudEA0FKqqXhReQyP/XsRo6iILTUv/I+I/bQ=='
os.environ['IBIND_OAUTH1A_ENCRYPTION_KEY_FP'] = '/home/info/fntx-ai-v1/config/keys/private_encryption.pem'
os.environ['IBIND_OAUTH1A_SIGNATURE_KEY_FP'] = '/home/info/fntx-ai-v1/config/keys/private_signature.pem'
os.environ['IBIND_OAUTH1A_DH_PRIME'] = 'e9c0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5ed5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4fb527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e69d2ec0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5ed5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4fb527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e6af'

print("="*70)
print("Testing OAuth with IBind Library")
print("="*70)

try:
    from ibind import IbkrClient
    
    print("\nInitializing IBind client with OAuth...")
    client = IbkrClient(use_oauth=True)
    
    print("Attempting to get accounts...")
    response = client.get('/portfolio/accounts')
    
    if response.ok:
        print("✅ SUCCESS! OAuth is working with IBind!")
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"Error: {response.error}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()