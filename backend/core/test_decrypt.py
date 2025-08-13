#!/usr/bin/env python3
"""
Test access token secret decryption with different approaches
"""

import os
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

def load_private_key(key_path):
    """Load a private key from PEM file"""
    with open(key_path, 'rb') as f:
        key_data = f.read()
        print(f"Key file size: {len(key_data)} bytes")
        print(f"Key starts with: {key_data[:50]}")
        return serialization.load_pem_private_key(
            key_data,
            password=None,
            backend=default_backend()
        )

def test_decryption():
    """Test different decryption approaches"""
    encrypted_secret = os.getenv('IB_ACCESS_TOKEN_SECRET', '').strip('"')
    print(f"Encrypted secret length: {len(encrypted_secret)}")
    print(f"Encrypted secret (first 50): {encrypted_secret[:50]}...")
    
    # Try with encryption key
    print("\n1. Trying with encryption key:")
    encryption_key_path = os.getenv('IB_ENCRYPTION_KEY_PATH')
    print(f"Encryption key path: {encryption_key_path}")
    
    try:
        encryption_key = load_private_key(encryption_key_path)
        print(f"Key type: {type(encryption_key)}")
        print(f"Key size: {encryption_key.key_size}")
        
        encrypted_bytes = base64.b64decode(encrypted_secret)
        print(f"Encrypted bytes length: {len(encrypted_bytes)}")
        
        # Try OAEP with SHA256
        try:
            decrypted = encryption_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            print(f"✅ OAEP SHA256 Success: {decrypted.hex()[:50]}...")
            return decrypted
        except Exception as e:
            print(f"❌ OAEP SHA256 failed: {e}")
        
        # Try OAEP with SHA1
        try:
            decrypted = encryption_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )
            print(f"✅ OAEP SHA1 Success: {decrypted.hex()[:50]}...")
            return decrypted
        except Exception as e:
            print(f"❌ OAEP SHA1 failed: {e}")
        
        # Try PKCS1v15
        try:
            decrypted = encryption_key.decrypt(
                encrypted_bytes,
                padding.PKCS1v15()
            )
            print(f"✅ PKCS1v15 Success: {decrypted.hex()[:50]}...")
            return decrypted
        except Exception as e:
            print(f"❌ PKCS1v15 failed: {e}")
            
    except Exception as e:
        print(f"❌ Failed to load encryption key: {e}")
    
    # Try with signature key
    print("\n2. Trying with signature key:")
    signature_key_path = os.getenv('IB_SIGNATURE_KEY_PATH')
    print(f"Signature key path: {signature_key_path}")
    
    try:
        signature_key = load_private_key(signature_key_path)
        print(f"Key type: {type(signature_key)}")
        print(f"Key size: {signature_key.key_size}")
        
        # Try all padding schemes
        for name, padding_scheme in [
            ("OAEP SHA256", padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)),
            ("OAEP SHA1", padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None)),
            ("PKCS1v15", padding.PKCS1v15())
        ]:
            try:
                decrypted = signature_key.decrypt(encrypted_bytes, padding_scheme)
                print(f"✅ {name} Success: {decrypted.hex()[:50]}...")
                return decrypted
            except Exception as e:
                print(f"❌ {name} failed: {type(e).__name__}")
                
    except Exception as e:
        print(f"❌ Failed to load signature key: {e}")
    
    return None

def main():
    print("Access Token Secret Decryption Test")
    print("="*60)
    
    result = test_decryption()
    
    if result:
        print(f"\n✅ Successfully decrypted!")
        print(f"Hex: {result.hex()}")
        print(f"Length: {len(result)} bytes")
        print(f"ASCII (if printable): {result.decode('ascii', errors='ignore')}")
    else:
        print("\n❌ All decryption attempts failed")

if __name__ == "__main__":
    main()