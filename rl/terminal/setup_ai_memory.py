#!/usr/bin/env python3
"""
Setup AI Memory Schema in PostgreSQL
"""
import asyncio
import asyncpg
import sys

async def setup_database():
    # Try different connection options
    passwords = ['theta_data_2024', 'fntx2024', 'TempPass123!']
    users = ['postgres', 'info']
    
    conn = None
    for user in users:
        for password in passwords:
            try:
                print(f"Trying to connect as {user}...")
                conn = await asyncpg.connect(
                    host='localhost',
                    port=5432,
                    user=user,
                    password=password,
                    database='options_data'
                )
                print(f"✓ Connected successfully as {user}")
                break
            except Exception as e:
                print(f"  Failed with {user}/{password[:4]}...: {str(e)}")
                continue
        if conn:
            break
    
    if not conn:
        print("ERROR: Could not connect to database with any credentials")
        return False
    
    try:
        # Read the schema file
        with open('memory_system/database_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema
        print("Creating AI memory schema...")
        await conn.execute(schema_sql)
        print("✓ AI memory schema created successfully!")
        
        # Verify schema exists
        result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ai_memory')")
        if result:
            print("✓ Verified: ai_memory schema exists")
            
            # List tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'ai_memory'
                ORDER BY table_name
            """)
            print(f"\nCreated {len(tables)} tables:")
            for table in tables:
                print(f"  - ai_memory.{table['table_name']}")
        
        return True
        
    except Exception as e:
        print(f"ERROR creating schema: {e}")
        return False
    finally:
        await conn.close()

if __name__ == "__main__":
    success = asyncio.run(setup_database())
    sys.exit(0 if success else 1)