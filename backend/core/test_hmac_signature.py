#!/usr/bin/env python3
"""
Test HMAC-SHA256 signature generation
"""

import base64
import hmac
import hashlib
from urllib.parse import quote_plus

# Live Session Token from file
lst_b64 = "1Oiv6C3CPShUrjVMzItykiZaxMI="
lst = base64.b64decode(lst_b64)

# Test base string
base_string = "GET&https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%2Fportfolio%2Faccounts&oauth_consumer_key%3DBEARHEDGE%26oauth_nonce%3Dtest123%26oauth_signature_method%3DHMAC-SHA256%26oauth_timestamp%3D1234567890%26oauth_token%3D8444def5466e38fb8b86"

print("Live Session Token (base64):", lst_b64)
print("Live Session Token (bytes):", lst)
print("Length:", len(lst))
print("\nBase string (first 100 chars):", base_string[:100])

# Generate HMAC signature
signature = hmac.new(lst, base_string.encode('utf-8'), hashlib.sha256).digest()
signature_b64 = base64.b64encode(signature).decode('utf-8')

print("\n" + "="*70)
print("Signature generation:")
print("Raw signature (hex):", signature.hex())
print("Base64 signature:", signature_b64)
print("URL-encoded signature:", quote_plus(signature_b64))

# What should be in the header
print("\n" + "="*70)
print("OAuth header value for signature:")
print(f'oauth_signature="{quote_plus(signature_b64)}"')

# Compare to what our code produces
print("\n" + "="*70)
print("From our logs, we had:")
print('oauth_signature="hYYQrSJU6UDkfMTssy7j9XTf7fxVBpSYumZFnIWwETM%3D"')
print("\nNote: The %3D at the end is the URL-encoded '=' sign")