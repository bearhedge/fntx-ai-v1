#!/usr/bin/env python3
"""
Test script to verify Supabase registration is working
"""
import asyncio
import sys
sys.path.append('/home/info/fntx-ai-v1')

from tui.services.supabase_client import SupabaseClient
import random
import string

async def test_registration():
    """Test the registration flow"""
    client = SupabaseClient()
    
    # Generate random test user data
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    test_email = f"test_{random_suffix}@example.com"
    test_password = "TestPassword123!"
    test_username = f"testuser_{random_suffix}"
    
    print(f"Testing registration with:")
    print(f"  Email: {test_email}")
    print(f"  Username: {test_username}")
    print(f"  Password: {test_password}")
    print()
    
    try:
        await client.start()
        
        # Test registration
        print("Attempting registration...")
        result = await client.register(
            email=test_email,
            password=test_password,
            username=test_username,
            full_name="Test User"
        )
        
        print("✅ Registration successful!")
        print(f"User ID: {result.get('user', {}).get('id')}")
        print(f"Email: {result.get('user', {}).get('email')}")
        
        # Check if we got tokens (auto-login)
        if result.get('access_token'):
            print("✅ Auto-login successful - received access token")
        else:
            print("⚠️ No auto-login - manual login required")
        
        # Test getting user data
        if client.access_token:
            print("\nTesting get_user...")
            user_data = await client.get_user()
            if user_data:
                print("✅ Successfully retrieved user data")
                if 'user_metadata' in user_data:
                    print(f"Username from metadata: {user_data['user_metadata'].get('username')}")
            else:
                print("⚠️ Could not retrieve user data")
        
        return True
        
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return False
        
    finally:
        await client.close()

async def test_duplicate_registration():
    """Test that duplicate email registration fails properly"""
    client = SupabaseClient()
    
    # Use a known email that might already exist
    test_email = "existing_user@example.com"
    test_password = "TestPassword123!"
    test_username = "existing_user"
    
    print("\nTesting duplicate registration handling...")
    print(f"Attempting to register with potentially existing email: {test_email}")
    
    try:
        await client.start()
        
        result = await client.register(
            email=test_email,
            password=test_password,
            username=test_username
        )
        
        print("⚠️ Registration succeeded (email was not previously registered)")
        
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            print(f"✅ Correctly rejected duplicate registration: {error_msg}")
        else:
            print(f"Got error: {error_msg}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    print("=" * 60)
    print("SUPABASE REGISTRATION TEST")
    print("=" * 60)
    print()
    
    # Run tests
    asyncio.run(test_registration())
    asyncio.run(test_duplicate_registration())
    
    print()
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)