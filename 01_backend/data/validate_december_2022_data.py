#!/usr/bin/env python3
"""
Validate December 2022 0DTE data quality and coverage
Generates comprehensive validation report
"""
import sys
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import json

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class December2022DataValidator:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.report = {
            'summary': {},
            'daily_stats': [],
            'data_quality': {},
            'coverage_analysis': {},
            'issues_found': []
        }
    
    def validate_data(self):
        """Run comprehensive validation checks"""
        print("VALIDATING DECEMBER 2022 SPY 0DTE DATA")
        print("="*80)
        
        # 1. Overall summary
        self.check_overall_summary()
        
        # 2. Daily breakdown
        self.check_daily_stats()
        
        # 3. Data quality checks
        self.check_data_quality()
        
        # 4. Coverage analysis
        self.check_coverage()
        
        # 5. Time consistency
        self.check_time_consistency()
        
        # 6. 0DTE compliance
        self.check_0dte_compliance()
        
        # Print and save report
        self.print_report()
        self.save_report()
    
    def check_overall_summary(self):
        """Check overall data summary"""
        cursor = self.conn.cursor()
        
        print("\n1. OVERALL SUMMARY")
        print("-" * 60)
        
        # Total contracts
        cursor.execute("""
            SELECT COUNT(*) FROM theta.options_contracts
            WHERE symbol = 'SPY'
            AND expiration >= '2022-12-01'
            AND expiration <= '2022-12-31'
        """)
        total_contracts = cursor.fetchone()[0]
        
        # Total data points
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM theta.options_ohlc o
                 JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
                 WHERE oc.symbol = 'SPY' 
                 AND oc.expiration >= '2022-12-01' 
                 AND oc.expiration <= '2022-12-31') as ohlc_count,
                (SELECT COUNT(*) FROM theta.options_greeks g
                 JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
                 WHERE oc.symbol = 'SPY' 
                 AND oc.expiration >= '2022-12-01' 
                 AND oc.expiration <= '2022-12-31') as greeks_count,
                (SELECT COUNT(*) FROM theta.options_iv i
                 JOIN theta.options_contracts oc ON i.contract_id = oc.contract_id
                 WHERE oc.symbol = 'SPY' 
                 AND oc.expiration >= '2022-12-01' 
                 AND oc.expiration <= '2022-12-31') as iv_count
        """)
        ohlc_count, greeks_count, iv_count = cursor.fetchone()
        
        # Date range
        cursor.execute("""
            SELECT MIN(expiration), MAX(expiration), COUNT(DISTINCT expiration)
            FROM theta.options_contracts
            WHERE symbol = 'SPY'
            AND expiration >= '2022-12-01'
            AND expiration <= '2022-12-31'
        """)
        min_date, max_date, unique_dates = cursor.fetchone()
        
        self.report['summary'] = {
            'total_contracts': total_contracts,
            'total_ohlc_bars': ohlc_count,
            'total_greeks_bars': greeks_count,
            'total_iv_bars': iv_count,
            'date_range': f"{min_date} to {max_date}" if min_date else "No data",
            'unique_dates': unique_dates or 0
        }
        
        print(f"Total contracts: {total_contracts:,}")
        print(f"Total OHLC bars: {ohlc_count:,}")
        print(f"Total Greeks bars: {greeks_count:,}")
        print(f"Total IV bars: {iv_count:,}")
        print(f"Date range: {self.report['summary']['date_range']}")
        print(f"Unique dates: {unique_dates}")
        
        cursor.close()
    
    def check_daily_stats(self):
        """Check daily statistics"""
        cursor = self.conn.cursor()
        
        print("\n2. DAILY BREAKDOWN")
        print("-" * 60)
        
        cursor.execute("""
            WITH daily_data AS (
                SELECT 
                    oc.expiration,
                    COUNT(DISTINCT oc.contract_id) as contracts,
                    COUNT(DISTINCT oc.strike) as unique_strikes,
                    MIN(oc.strike) as min_strike,
                    MAX(oc.strike) as max_strike,
                    COUNT(DISTINCT o.id) as ohlc_bars,
                    COUNT(DISTINCT g.id) as greeks_bars,
                    COUNT(DISTINCT i.id) as iv_bars
                FROM theta.options_contracts oc
                LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
                LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id
                LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id
                WHERE oc.symbol = 'SPY'
                AND oc.expiration >= '2022-12-01'
                AND oc.expiration <= '2022-12-31'
                GROUP BY oc.expiration
            )
            SELECT * FROM daily_data ORDER BY expiration
        """)
        
        daily_data = cursor.fetchall()
        
        print(f"{'Date':<12} {'Contracts':<10} {'Strikes':<10} {'Range':<15} {'OHLC':<10} {'Greeks':<10} {'IV':<10}")
        print("-" * 80)
        
        for row in daily_data:
            date, contracts, strikes, min_s, max_s, ohlc, greeks, iv = row
            strike_range = f"${min_s}-${max_s}" if min_s else "N/A"
            
            print(f"{date.strftime('%Y-%m-%d'):<12} {contracts:<10} {strikes:<10} "
                  f"{strike_range:<15} {ohlc:<10} {greeks:<10} {iv:<10}")
            
            self.report['daily_stats'].append({
                'date': date.strftime('%Y-%m-%d'),
                'contracts': contracts,
                'strikes': strikes,
                'strike_range': strike_range,
                'ohlc_bars': ohlc,
                'greeks_bars': greeks,
                'iv_bars': iv
            })
        
        cursor.close()
    
    def check_data_quality(self):
        """Check data quality issues"""
        cursor = self.conn.cursor()
        
        print("\n3. DATA QUALITY CHECKS")
        print("-" * 60)
        
        quality_checks = {}
        
        # Check for null values
        for table, fields in [
            ('options_ohlc', ['open', 'high', 'low', 'close']),
            ('options_greeks', ['delta', 'gamma', 'theta', 'vega', 'rho']),
            ('options_iv', ['implied_volatility'])
        ]:
            for field in fields:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM theta.{table} t
                    JOIN theta.options_contracts oc ON t.contract_id = oc.contract_id
                    WHERE oc.symbol = 'SPY'
                    AND oc.expiration >= '2022-12-01'
                    AND oc.expiration <= '2022-12-31'
                    AND t.{field} IS NULL
                """)
                null_count = cursor.fetchone()[0]
                
                if null_count > 0:
                    self.report['issues_found'].append(
                        f"{table}.{field} has {null_count} NULL values"
                    )
                
                quality_checks[f"{table}.{field}_nulls"] = null_count
        
        # Check for invalid OHLC relationships
        cursor.execute("""
            SELECT COUNT(*) FROM theta.options_ohlc o
            JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
            WHERE oc.symbol = 'SPY'
            AND oc.expiration >= '2022-12-01'
            AND oc.expiration <= '2022-12-31'
            AND (o.high < o.low OR o.open < 0 OR o.close < 0)
        """)
        invalid_ohlc = cursor.fetchone()[0]
        quality_checks['invalid_ohlc'] = invalid_ohlc
        
        if invalid_ohlc > 0:
            self.report['issues_found'].append(
                f"Found {invalid_ohlc} OHLC bars with invalid price relationships"
            )
        
        # Check for duplicate entries
        cursor.execute("""
            SELECT contract_id, datetime, COUNT(*)
            FROM theta.options_ohlc o
            JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
            WHERE oc.symbol = 'SPY'
            AND oc.expiration >= '2022-12-01'
            AND oc.expiration <= '2022-12-31'
            GROUP BY contract_id, datetime
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        quality_checks['duplicate_ohlc'] = len(duplicates)
        
        self.report['data_quality'] = quality_checks
        
        # Print summary
        print(f"NULL values found: {sum(v for k, v in quality_checks.items() if 'nulls' in k)}")
        print(f"Invalid OHLC bars: {invalid_ohlc}")
        print(f"Duplicate entries: {len(duplicates)}")
        
        cursor.close()
    
    def check_coverage(self):
        """Check data coverage and completeness"""
        cursor = self.conn.cursor()
        
        print("\n4. COVERAGE ANALYSIS")
        print("-" * 60)
        
        # Expected bars per contract (78 = 6.5 hours * 12 bars/hour)
        expected_bars = 78
        
        cursor.execute("""
            WITH contract_coverage AS (
                SELECT 
                    oc.contract_id,
                    oc.expiration,
                    oc.strike,
                    oc.option_type,
                    COUNT(DISTINCT o.datetime) as ohlc_count,
                    COUNT(DISTINCT g.datetime) as greeks_count,
                    COUNT(DISTINCT i.datetime) as iv_count
                FROM theta.options_contracts oc
                LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
                LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id
                LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id
                WHERE oc.symbol = 'SPY'
                AND oc.expiration >= '2022-12-01'
                AND oc.expiration <= '2022-12-31'
                GROUP BY oc.contract_id, oc.expiration, oc.strike, oc.option_type
            )
            SELECT 
                AVG(ohlc_count) as avg_ohlc,
                AVG(CASE WHEN ohlc_count > 0 THEN greeks_count::float / ohlc_count ELSE 0 END) * 100 as greeks_coverage,
                AVG(CASE WHEN ohlc_count > 0 THEN iv_count::float / ohlc_count ELSE 0 END) * 100 as iv_coverage,
                COUNT(CASE WHEN ohlc_count = 0 THEN 1 END) as contracts_no_data,
                COUNT(CASE WHEN ohlc_count < %s * 0.9 THEN 1 END) as contracts_low_coverage
            FROM contract_coverage
        """, (expected_bars,))
        
        avg_ohlc, greeks_cov, iv_cov, no_data, low_cov = cursor.fetchone()
        
        self.report['coverage_analysis'] = {
            'avg_bars_per_contract': avg_ohlc or 0,
            'expected_bars_per_contract': expected_bars,
            'coverage_percentage': (avg_ohlc or 0) / expected_bars * 100,
            'greeks_coverage': greeks_cov or 0,
            'iv_coverage': iv_cov or 0,
            'contracts_with_no_data': no_data or 0,
            'contracts_with_low_coverage': low_cov or 0
        }
        
        print(f"Average bars per contract: {avg_ohlc:.1f} / {expected_bars} "
              f"({(avg_ohlc or 0) / expected_bars * 100:.1f}%)")
        print(f"Greeks coverage: {greeks_cov:.1f}%")
        print(f"IV coverage: {iv_cov:.1f}%")
        print(f"Contracts with no data: {no_data}")
        print(f"Contracts with <90% coverage: {low_cov}")
        
        cursor.close()
    
    def check_time_consistency(self):
        """Check 5-minute interval consistency"""
        cursor = self.conn.cursor()
        
        print("\n5. TIME CONSISTENCY CHECK")
        print("-" * 60)
        
        # Check for gaps in 5-minute intervals
        cursor.execute("""
            WITH time_gaps AS (
                SELECT 
                    contract_id,
                    datetime,
                    LAG(datetime) OVER (PARTITION BY contract_id ORDER BY datetime) as prev_time,
                    datetime - LAG(datetime) OVER (PARTITION BY contract_id ORDER BY datetime) as gap
                FROM theta.options_ohlc o
                JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
                WHERE oc.symbol = 'SPY'
                AND oc.expiration >= '2022-12-01'
                AND oc.expiration <= '2022-12-31'
            )
            SELECT 
                COUNT(CASE WHEN gap > INTERVAL '5 minutes' 
                          AND gap < INTERVAL '1 hour' THEN 1 END) as small_gaps,
                COUNT(CASE WHEN gap >= INTERVAL '1 hour' THEN 1 END) as large_gaps
            FROM time_gaps
            WHERE gap IS NOT NULL
        """)
        
        small_gaps, large_gaps = cursor.fetchone()
        
        print(f"5-minute gaps (< 1 hour): {small_gaps}")
        print(f"Large gaps (>= 1 hour): {large_gaps}")
        
        if small_gaps > 0 or large_gaps > 0:
            self.report['issues_found'].append(
                f"Found {small_gaps + large_gaps} time gaps in data"
            )
        
        cursor.close()
    
    def check_0dte_compliance(self):
        """Verify all data is truly 0DTE"""
        cursor = self.conn.cursor()
        
        print("\n6. 0DTE COMPLIANCE CHECK")
        print("-" * 60)
        
        # Check if any data timestamps don't match expiration date
        cursor.execute("""
            SELECT COUNT(*) FROM theta.options_ohlc o
            JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
            WHERE oc.symbol = 'SPY'
            AND oc.expiration >= '2022-12-01'
            AND oc.expiration <= '2022-12-31'
            AND o.datetime::date != oc.expiration
        """)
        
        non_0dte = cursor.fetchone()[0]
        
        if non_0dte > 0:
            print(f"❌ Found {non_0dte} non-0DTE data points!")
            self.report['issues_found'].append(
                f"CRITICAL: {non_0dte} data points are not 0DTE"
            )
        else:
            print("✅ All data is 0DTE compliant")
        
        cursor.close()
    
    def print_report(self):
        """Print validation report"""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        
        if self.report['issues_found']:
            print(f"\n❌ ISSUES FOUND ({len(self.report['issues_found'])})")
            for issue in self.report['issues_found']:
                print(f"   - {issue}")
        else:
            print("\n✅ NO ISSUES FOUND - Data quality is excellent!")
        
        # Coverage summary
        cov = self.report['coverage_analysis']
        print(f"\nCOVERAGE SUMMARY:")
        print(f"  OHLC: {cov.get('coverage_percentage', 0):.1f}%")
        print(f"  Greeks: {cov.get('greeks_coverage', 0):.1f}%")
        print(f"  IV: {cov.get('iv_coverage', 0):.1f}%")
    
    def save_report(self):
        """Save detailed report to file"""
        report_file = f"/home/info/fntx-ai-v1/08_logs/december_2022_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed validation report saved to: {report_file}")

def main():
    validator = December2022DataValidator()
    validator.validate_data()

if __name__ == "__main__":
    main()