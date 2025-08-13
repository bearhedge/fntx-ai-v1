#!/usr/bin/env python3
"""
Test OAuth header formatting
"""

from urllib.parse import quote, quote_plus

# Test signature
sig = "TUNOvPirUMHuHXyyQk2e2gL1OpA0DM3yyKD2mCcM3y1AMex3rebPN8obto0LrSOzUvq6jxTXuPmyUDCnd3B8jkuWiFpNK/5ennZ4aEQGCFjVY/T6eaGxZtr/xfaSI3Vlsk32Iwc8HKruNqx8iaK5VOAIg5H2NdaLlhXb02HPWSFYGKlT/2GZTpxSe8oDhjz7URBYTaR1wthesDBZtERDPpmuPwC9HY9BL6uNx4U2cwb4G7P4LTa/+/+yspn65nX3RHQGKG4yIAZPWfzz7V/6rs6ErA/1AbUYzF0XYmISCE1cY7XGqeE9qol7m6IXMorJBTqhUhM3qAoqv1Zjr0at0w=="

# Test different encodings
print("Original signature:")
print(sig)
print("\nquote (safe='~'):")
print(quote(sig, safe='~'))
print("\nquote_plus:")
print(quote_plus(sig))

# Check if signature contains special characters
print("\nSpecial characters in signature:")
print(f"Contains +: {'+' in sig}")
print(f"Contains /: {'/' in sig}")
print(f"Contains =: {'=' in sig}")

# What the header should look like
params = {
    'oauth_consumer_key': 'BEARHEDGE',
    'oauth_nonce': 'test123',
    'oauth_signature': sig,
    'oauth_signature_method': 'RSA-SHA256',
    'oauth_timestamp': '1234567890',
    'oauth_token': 'token123'
}

# IBind style header
def ibind_style_header(params, realm='limited_poa'):
    header_items = ', '.join([f'{k}="{v}"' for k, v in sorted(params.items())])
    return f'OAuth realm="{realm}", {header_items}'

print("\n" + "="*70)
print("Header format:")
print(ibind_style_header(params))

# Check if the signature needs to be percent-encoded in the header
print("\n" + "="*70)
print("With percent-encoded signature in header:")
params_encoded = params.copy()
params_encoded['oauth_signature'] = quote(sig, safe='~')
print(ibind_style_header(params_encoded))