#!/usr/bin/env python3
"""
Verify that public and private keys match
"""

import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

keys_dir = "/home/info/fntx-ai-v1/config/keys"

# Load private key
with open(f"{keys_dir}/private_signature.pem", 'rb') as f:
    private_key = serialization.load_pem_private_key(
        f.read(),
        password=None,
        backend=default_backend()
    )

# Load public key
with open(f"{keys_dir}/public_signature.pem", 'rb') as f:
    public_key = serialization.load_pem_public_key(
        f.read(),
        backend=default_backend()
    )

# Get public key from private key
derived_public = private_key.public_key()

# Compare
private_numbers = private_key.private_numbers()
public_numbers = public_key.public_numbers()
derived_numbers = derived_public.public_numbers()

print("=== Key Verification ===")
print(f"Private key modulus (first 50 chars): {str(private_numbers.public_numbers.n)[:50]}...")
print(f"Public key modulus (first 50 chars):  {str(public_numbers.n)[:50]}...")
print(f"Derived public modulus (first 50 chars): {str(derived_numbers.n)[:50]}...")

if public_numbers.n == derived_numbers.n and public_numbers.e == derived_numbers.e:
    print("\n✅ Public key MATCHES private key!")
else:
    print("\n❌ Public key DOES NOT match private key!")

# Test signing and verification
test_message = b"Test message for signature verification"

# Sign with private key
signature = private_key.sign(
    test_message,
    padding.PKCS1v15(),
    hashes.SHA256()
)

# Verify with public key
try:
    public_key.verify(
        signature,
        test_message,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    print("✅ Signature verification successful!")
except Exception as e:
    print(f"❌ Signature verification failed: {e}")

print("\n=== Key Information ===")
print(f"Key size: {private_key.key_size} bits")
print(f"Public exponent: {public_numbers.e}")

# Show public key in PEM format (first few lines)
with open(f"{keys_dir}/public_signature.pem", 'r') as f:
    lines = f.readlines()
    print("\nPublic key PEM (first 3 lines):")
    for line in lines[:3]:
        print(f"  {line.strip()}")
    print("  ...")
    print(f"  {lines[-1].strip()}")