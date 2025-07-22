#!/usr/bin/env python3
"""
Setup TimescaleDB for optimal time-series performance
Creates hypertables and continuous aggregates
"""
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def setup_timescaledb():
    """Setup TimescaleDB hypertables and optimizations"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    try:
        print("SETTING UP TIMESCALEDB FOR OPTIONS DATA")
        print("="*60)
        
        # Check if TimescaleDB extension exists
        cursor.execute("SELECT * FROM pg_available_extensions WHERE name = 'timescaledb'")
        if not cursor.fetchone():
            print("❌ TimescaleDB extension not available")
            print("   Please install TimescaleDB first:")
            print("   https://docs.timescale.com/install/latest/self-hosted/")
            return False
        
        # Create extension if not exists
        print("1. Creating TimescaleDB extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
        print("   ✓ TimescaleDB extension ready")
        
        # Convert tables to hypertables
        print("\n2. Converting tables to hypertables...")
        
        tables = [
            ('options_ohlc', 'datetime'),
            ('options_greeks', 'datetime'),
            ('options_iv', 'datetime')
        ]
        
        for table, time_col in tables:
            try:
                # Check if already a hypertable
                cursor.execute("""
                    SELECT * FROM timescaledb_information.hypertables 
                    WHERE hypertable_schema = 'theta' 
                    AND hypertable_name = %s
                """, (table,))
                
                if cursor.fetchone():
                    print(f"   - {table} is already a hypertable")
                else:
                    # Convert to hypertable
                    cursor.execute(f"""
                        SELECT create_hypertable(
                            'theta.{table}',
                            '{time_col}',
                            chunk_time_interval => INTERVAL '1 day'
                        )
                    """)
                    print(f"   ✓ {table} converted to hypertable")
                    
                    # Create index on contract_id for better join performance
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table}_contract_id 
                        ON theta.{table} (contract_id)
                    """)
                    
            except Exception as e:
                print(f"   ⚠️  {table}: {str(e)[:60]}")
        
        # Create continuous aggregates for 5-minute OHLC
        print("\n3. Creating continuous aggregates...")
        
        try:
            # Drop if exists
            cursor.execute("DROP MATERIALIZED VIEW IF EXISTS theta.ohlc_5min CASCADE")
            
            # Create 5-minute OHLC aggregate
            cursor.execute("""
                CREATE MATERIALIZED VIEW theta.ohlc_5min
                WITH (timescaledb.continuous) AS
                SELECT 
                    contract_id,
                    time_bucket('5 minutes', datetime) AS bucket,
                    first(open, datetime) as open,
                    max(high) as high,
                    min(low) as low,
                    last(close, datetime) as close,
                    sum(volume) as volume,
                    sum(trade_count) as trade_count,
                    count(*) as bar_count
                FROM theta.options_ohlc
                GROUP BY contract_id, bucket
                WITH NO DATA
            """)
            print("   ✓ Created ohlc_5min continuous aggregate")
            
            # Create policy to refresh the aggregate
            cursor.execute("""
                SELECT add_continuous_aggregate_policy('theta.ohlc_5min',
                    start_offset => INTERVAL '1 day',
                    end_offset => INTERVAL '1 hour',
                    schedule_interval => INTERVAL '1 hour')
            """)
            print("   ✓ Added refresh policy for ohlc_5min")
            
        except Exception as e:
            print(f"   ⚠️  Continuous aggregate: {str(e)[:60]}")
        
        # Create compression policies
        print("\n4. Setting up compression policies...")
        
        for table in ['options_ohlc', 'options_greeks', 'options_iv']:
            try:
                # Enable compression
                cursor.execute(f"""
                    ALTER TABLE theta.{table} SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'contract_id'
                    )
                """)
                
                # Add compression policy (compress chunks older than 7 days)
                cursor.execute(f"""
                    SELECT add_compression_policy('theta.{table}', INTERVAL '7 days')
                """)
                
                print(f"   ✓ Compression enabled for {table}")
                
            except Exception as e:
                print(f"   ⚠️  Compression for {table}: {str(e)[:60]}")
        
        # Create useful indexes
        print("\n5. Creating optimized indexes...")
        
        indexes = [
            ("idx_ohlc_datetime_contract", "options_ohlc", "(datetime, contract_id)"),
            ("idx_greeks_datetime_contract", "options_greeks", "(datetime, contract_id)"),
            ("idx_iv_datetime_contract", "options_iv", "(datetime, contract_id)"),
            ("idx_contracts_exp_strike", "options_contracts", "(expiration, strike)")
        ]
        
        for idx_name, table, columns in indexes:
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} 
                ON theta.{table} {columns}
            """)
        print("   ✓ Optimized indexes created")
        
        # Create helper functions
        print("\n6. Creating helper functions...")
        
        # Function to get data coverage stats
        cursor.execute("""
            CREATE OR REPLACE FUNCTION theta.get_coverage_stats(
                start_date DATE,
                end_date DATE
            )
            RETURNS TABLE(
                date DATE,
                contracts BIGINT,
                ohlc_bars BIGINT,
                greeks_bars BIGINT,
                iv_bars BIGINT,
                ohlc_coverage NUMERIC,
                greeks_coverage NUMERIC,
                iv_coverage NUMERIC
            ) AS $$
            BEGIN
                RETURN QUERY
                WITH daily_stats AS (
                    SELECT 
                        oc.expiration as trade_date,
                        COUNT(DISTINCT oc.contract_id) as contract_count,
                        COUNT(DISTINCT o.id) as ohlc_count,
                        COUNT(DISTINCT g.id) as greeks_count,
                        COUNT(DISTINCT i.id) as iv_count
                    FROM theta.options_contracts oc
                    LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
                    LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id
                    LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id
                    WHERE oc.symbol = 'SPY'
                    AND oc.expiration >= start_date
                    AND oc.expiration <= end_date
                    GROUP BY oc.expiration
                )
                SELECT 
                    trade_date,
                    contract_count,
                    ohlc_count,
                    greeks_count,
                    iv_count,
                    CASE 
                        WHEN contract_count > 0 THEN 
                            (ohlc_count::NUMERIC / (contract_count * 78)) * 100
                        ELSE 0 
                    END as ohlc_pct,
                    CASE 
                        WHEN ohlc_count > 0 THEN 
                            (greeks_count::NUMERIC / ohlc_count) * 100
                        ELSE 0 
                    END as greeks_pct,
                    CASE 
                        WHEN ohlc_count > 0 THEN 
                            (iv_count::NUMERIC / ohlc_count) * 100
                        ELSE 0 
                    END as iv_pct
                FROM daily_stats
                ORDER BY trade_date;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✓ Created coverage stats function")
        
        print("\n✅ TimescaleDB setup complete!")
        
        # Show current status
        print("\n7. Current TimescaleDB status:")
        
        cursor.execute("""
            SELECT hypertable_schema, hypertable_name, 
                   num_chunks, num_dimensions
            FROM timescaledb_information.hypertables
            WHERE hypertable_schema = 'theta'
        """)
        
        results = cursor.fetchall()
        if results:
            print("   Hypertables:")
            for schema, table, chunks, dims in results:
                print(f"   - {schema}.{table}: {chunks} chunks, {dims} dimensions")
        else:
            print("   No hypertables found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_timescaledb()