import os
import sys
import psycopg2

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.theta_config import DB_CONFIG

def check_schema():
    """Check the actual database schema"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Check if theta schema exists
        cursor.execute("""
            SELECT EXISTS(
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'theta'
            );
        """)
        schema_exists = cursor.fetchone()[0]
        print(f"Schema 'theta' exists: {schema_exists}")
        
        if schema_exists:
            # List all tables in theta schema
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'theta'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print("\nTables in 'theta' schema:")
            for table in tables:
                print(f"  - {table[0]}")
                
                # Get column info for each table
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'theta' 
                    AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table[0],))
                columns = cursor.fetchall()
                for col in columns:
                    print(f"      {col[0]} ({col[1]})")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()