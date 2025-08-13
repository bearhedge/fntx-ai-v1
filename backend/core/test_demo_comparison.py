#!/usr/bin/env python3
"""
Compare our implementation with the IBKR demo
"""

import os
import base64
import hashlib
import hmac
import secrets
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
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

def decrypt_access_token_secret():
    """Decrypt the access token secret"""
    encrypted_secret = os.getenv('IB_ACCESS_TOKEN_SECRET', '').strip('"')
    if not encrypted_secret:
        print("❌ No access token secret found")
        return None
        
    encryption_key = load_private_key(os.getenv('IB_ENCRYPTION_KEY_PATH'))
    
    try:
        encrypted_bytes = base64.b64decode(encrypted_secret)
        decrypted_bytes = encryption_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_bytes.hex()
    except Exception as e:
        print(f"❌ Failed to decrypt: {e}")
        return None

def test_demo_style_dh():
    """Test Diffie-Hellman using demo's approach"""
    print("\n" + "="*60)
    print("DEMO-STYLE DIFFIE-HELLMAN TEST")
    print("="*60)
    
    # Demo's prime (from the JavaScript)
    prime_hex = "00FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF"
    prime_int = int(prime_hex, 16)
    
    # Generate 25-byte random (like demo)
    dh_random = secrets.token_bytes(25)
    print(f"DH Random (25 bytes): {dh_random.hex()}")
    
    # Calculate g^a mod p (where g=2)
    dh_challenge = pow(2, int.from_bytes(dh_random, 'big'), prime_int)
    dh_challenge_hex = format(dh_challenge, 'x')
    print(f"DH Challenge: {dh_challenge_hex[:50]}...")
    
    # Load decrypted access token secret
    access_token_secret = decrypt_access_token_secret()
    if not access_token_secret:
        return
        
    print(f"Access Token Secret (hex): {access_token_secret[:50]}...")
    
    # For demo, we'd need the server's response to complete the calculation
    # The formula would be:
    # prepend = hex(pow(server_response, dh_random, prime))
    print("\n⚠️  Need server's DH response to complete calculation")
    
    return dh_challenge_hex, dh_random.hex(), access_token_secret

def test_hmac_variations():
    """Test different HMAC approaches"""
    print("\n" + "="*60)
    print("HMAC CALCULATION VARIATIONS")
    print("="*60)
    
    # Test data
    test_key = "test_key_123"
    test_data = "test_data_456"
    
    # SHA1 with key as key
    hmac1 = hmac.new(test_key.encode(), test_data.encode(), hashlib.sha1).hexdigest()
    print(f"HMAC-SHA1 (key as key): {hmac1}")
    
    # SHA1 with data as key (demo style)
    hmac2 = hmac.new(test_data.encode(), test_key.encode(), hashlib.sha1).hexdigest()
    print(f"HMAC-SHA1 (data as key): {hmac2}")
    
    # SHA256 variations
    hmac3 = hmac.new(test_key.encode(), test_data.encode(), hashlib.sha256).hexdigest()
    print(f"HMAC-SHA256 (key as key): {hmac3}")
    
    hmac4 = hmac.new(test_data.encode(), test_key.encode(), hashlib.sha256).hexdigest()
    print(f"HMAC-SHA256 (data as key): {hmac4}")

def main():
    """Run all tests"""
    print("IBKR OAuth Demo Comparison Tests")
    print("================================")
    
    print(f"\nConfiguration:")
    print(f"Consumer Key: {os.getenv('IB_CONSUMER_KEY')}")
    print(f"Access Token: {os.getenv('IB_ACCESS_TOKEN')}")
    print(f"Realm: {os.getenv('IB_REALM')}")
    
    # Test DH calculation
    test_demo_style_dh()
    
    # Test HMAC variations
    test_hmac_variations()
    
    print("\n" + "="*60)
    print("Key Differences Found:")
    print("1. Demo uses 25-byte DH random (not 256-bit)")
    print("2. Demo uses specific prime value")
    print("3. Demo uses HMAC-SHA1 (not SHA256)")
    print("4. Demo might swap key/data in HMAC")
    print("="*60)

if __name__ == "__main__":
    main()