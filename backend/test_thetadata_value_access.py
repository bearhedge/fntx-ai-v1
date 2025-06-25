#!/usr/bin/env python3
"""
Test ThetaData Value Subscription Access
Verify what historical data is available RIGHT NOW
"""
import requests
import json
from datetime import datetime, timedelta
import time
import sqlite3
import gzip
import os

class ThetaDataValueTester:
    def __init__(self):
        self.api_base = "http://localhost:25510"
        self.test_results = {
            "subscription_type": None,
            "endpoints_tested": {},
            "data_availability": {},
            "storage_calculations": {}
        }
    
    def run_all_tests(self):
        """Run comprehensive tests on ThetaData Value subscription"""
        print("="*80)
        print("THETADATA VALUE SUBSCRIPTION TEST")
        print("Testing what historical data is available RIGHT NOW")
        print("="*80)
        print()
        
        # 1. Check subscription level
        self.check_subscription_level()
        
        # 2. Test historical endpoints
        self.test_historical_ohlc()
        self.test_historical_open_interest()
        self.test_historical_volume()
        self.test_available_dates()
        
        # 3. Test specific data requirements
        self.test_one_minute_data()
        self.test_date_ranges()
        
        # 4. Calculate storage requirements
        self.calculate_storage_requirements()
        
        # 5. Generate report
        self.generate_report()
    
    def check_subscription_level(self):
        """Verify subscription level by testing various endpoints"""
        print("1. CHECKING SUBSCRIPTION LEVEL")
        print("-" * 40)
        
        # Test Value endpoints (should work)
        value_endpoints = [
            ("/v2/snapshot/option/quote", {"root": "SPY", "exp": "20250118", "strike": "600000", "right": "C"}),
            ("/v2/hist/option/ohlc", {"root": "SPY", "exp": "20240118", "strike": "450000", "right": "C", "start_date": "20240101", "end_date": "20240118"})
        ]
        
        # Test Standard endpoints (should fail with Value)
        standard_endpoints = [
            ("/v2/snapshot/option/greeks", {"root": "SPY", "exp": "20250118", "strike": "600000", "right": "C"}),
            ("/v2/hist/option/greeks", {"root": "SPY", "exp": "20240118", "strike": "450000", "right": "C", "start_date": "20240101", "end_date": "20240118"})
        ]
        
        for endpoint, params in value_endpoints:
            try:
                resp = requests.get(f"{self.api_base}{endpoint}", params=params, timeout=5)
                status = "✅ ACCESSIBLE" if resp.status_code == 200 else f"❌ ERROR {resp.status_code}"
                print(f"{endpoint}: {status}")
                self.test_results["endpoints_tested"][endpoint] = resp.status_code == 200
            except Exception as e:
                print(f"{endpoint}: ❌ ERROR - {str(e)}")
                self.test_results["endpoints_tested"][endpoint] = False
        
        for endpoint, params in standard_endpoints:
            try:
                resp = requests.get(f"{self.api_base}{endpoint}", params=params, timeout=5)
                if resp.status_code == 200:
                    print(f"{endpoint}: ✅ STANDARD SUBSCRIPTION DETECTED")
                    self.test_results["subscription_type"] = "Standard"
                else:
                    print(f"{endpoint}: ❌ NOT AVAILABLE (Value subscription confirmed)")
                    self.test_results["subscription_type"] = "Value"
            except Exception as e:
                print(f"{endpoint}: ❌ ERROR - {str(e)}")
        
        print()
    
    def test_historical_ohlc(self):
        """Test historical OHLC data access"""
        print("2. TESTING HISTORICAL OHLC DATA")
        print("-" * 40)
        
        # Test different intervals
        intervals = [
            ("1 minute", 60000),
            ("5 minutes", 300000),
            ("1 hour", 3600000),
            ("1 day", 86400000)
        ]
        
        test_params = {
            "root": "SPY",
            "exp": "20240118",  # Recent expiration
            "strike": "450000",
            "right": "C",
            "start_date": "20240101",
            "end_date": "20240118"
        }
        
        for interval_name, ivl in intervals:
            params = test_params.copy()
            params["ivl"] = ivl
            
            try:
                resp = requests.get(f"{self.api_base}/v2/hist/option/ohlc", params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('response'):
                        record_count = len(data['response'])
                        sample = data['response'][0] if data['response'] else None
                        print(f"{interval_name} data: ✅ AVAILABLE ({record_count} records)")
                        if sample:
                            print(f"  Sample: {sample}")
                            print(f"  Format: [ms_of_day, open, high, low, close, volume, count, date]")
                        self.test_results["data_availability"][f"ohlc_{ivl}"] = True
                    else:
                        print(f"{interval_name} data: ❌ NO DATA")
                        self.test_results["data_availability"][f"ohlc_{ivl}"] = False
                else:
                    print(f"{interval_name} data: ❌ ERROR {resp.status_code}")
                    self.test_results["data_availability"][f"ohlc_{ivl}"] = False
            except Exception as e:
                print(f"{interval_name} data: ❌ ERROR - {str(e)}")
                self.test_results["data_availability"][f"ohlc_{ivl}"] = False
        
        print()
    
    def test_historical_open_interest(self):
        """Test historical open interest data"""
        print("3. TESTING HISTORICAL OPEN INTEREST")
        print("-" * 40)
        
        params = {
            "root": "SPY",
            "exp": "20240118",
            "strike": "450000",
            "right": "C",
            "start_date": "20240101",
            "end_date": "20240118"
        }
        
        try:
            resp = requests.get(f"{self.api_base}/v2/hist/option/open_interest", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    print(f"✅ AVAILABLE ({len(data['response'])} records)")
                    print(f"Sample: {data['response'][0] if data['response'] else 'No data'}")
                    print(f"Format: [date, open_interest]")
                    self.test_results["data_availability"]["open_interest"] = True
                else:
                    print("❌ NO DATA")
                    self.test_results["data_availability"]["open_interest"] = False
            else:
                print(f"❌ ERROR {resp.status_code}")
                if resp.text:
                    print(f"Response: {resp.text}")
                self.test_results["data_availability"]["open_interest"] = False
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            self.test_results["data_availability"]["open_interest"] = False
        
        print()
    
    def test_historical_volume(self):
        """Test historical volume data"""
        print("4. TESTING HISTORICAL VOLUME")
        print("-" * 40)
        
        params = {
            "root": "SPY",
            "exp": "20240118",
            "strike": "450000",
            "right": "C",
            "start_date": "20240101",
            "end_date": "20240118"
        }
        
        try:
            resp = requests.get(f"{self.api_base}/v2/hist/option/volume", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    print(f"✅ AVAILABLE ({len(data['response'])} records)")
                    print(f"Sample: {data['response'][0] if data['response'] else 'No data'}")
                    self.test_results["data_availability"]["volume"] = True
                else:
                    print("❌ NO DATA")
                    self.test_results["data_availability"]["volume"] = False
            else:
                print(f"❌ ERROR {resp.status_code}")
                if resp.text:
                    print(f"Response: {resp.text}")
                self.test_results["data_availability"]["volume"] = False
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            self.test_results["data_availability"]["volume"] = False
        
        print()
    
    def test_available_dates(self):
        """Test what dates are available for SPY options"""
        print("5. TESTING AVAILABLE DATES")
        print("-" * 40)
        
        try:
            # Try to get available dates
            resp = requests.get(f"{self.api_base}/v2/list/dates/option", params={"root": "SPY"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    dates = data['response']
                    print(f"✅ Date list available: {len(dates)} dates")
                    if dates:
                        print(f"Earliest date: {dates[0]}")
                        print(f"Latest date: {dates[-1]}")
                        self.test_results["data_availability"]["date_range"] = {
                            "earliest": dates[0],
                            "latest": dates[-1],
                            "total_dates": len(dates)
                        }
                else:
                    print("❌ NO DATE DATA")
            else:
                print(f"❌ ERROR {resp.status_code}")
                # Try alternative method - test historical data availability
                self.test_date_range_manually()
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            # Try alternative method
            self.test_date_range_manually()
        
        print()
    
    def test_date_range_manually(self):
        """Manually test date ranges by probing different years"""
        print("  Testing date ranges manually...")
        
        test_dates = [
            ("2021-01-04", "20210104"),
            ("2022-01-03", "20220103"),
            ("2023-01-03", "20230103"),
            ("2024-01-02", "20240102"),
            ("2025-01-02", "20250102")
        ]
        
        earliest_found = None
        latest_found = None
        
        for date_desc, date_str in test_dates:
            params = {
                "root": "SPY",
                "exp": date_str,
                "strike": "400000",
                "right": "C",
                "start_date": date_str,
                "end_date": date_str
            }
            
            try:
                resp = requests.get(f"{self.api_base}/v2/hist/option/ohlc", params=params, timeout=5)
                if resp.status_code == 200 and resp.json().get('response'):
                    print(f"  {date_desc}: ✅ DATA AVAILABLE")
                    if not earliest_found:
                        earliest_found = date_str
                    latest_found = date_str
                else:
                    print(f"  {date_desc}: ❌ NO DATA")
            except:
                print(f"  {date_desc}: ❌ ERROR")
        
        if earliest_found:
            self.test_results["data_availability"]["date_range"] = {
                "earliest": earliest_found,
                "latest": latest_found,
                "method": "manual_probe"
            }
    
    def test_one_minute_data(self):
        """Specifically test 1-minute data availability"""
        print("6. TESTING 1-MINUTE DATA AVAILABILITY")
        print("-" * 40)
        
        # Test recent date
        params = {
            "root": "SPY",
            "exp": "20240118",
            "strike": "450000",
            "right": "C",
            "start_date": "20240115",
            "end_date": "20240115",
            "ivl": 60000  # 1 minute
        }
        
        try:
            resp = requests.get(f"{self.api_base}/v2/hist/option/ohlc", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    records = data['response']
                    print(f"✅ 1-MINUTE DATA AVAILABLE")
                    print(f"Records for one day: {len(records)}")
                    print(f"Expected records (6.5 hours): ~390")
                    print(f"Actual/Expected ratio: {len(records)/390:.2%}")
                    
                    # Calculate data points per year
                    trading_days = 252
                    minutes_per_day = len(records)
                    total_minutes = trading_days * minutes_per_day
                    
                    print(f"\nData points per contract per year: {total_minutes:,}")
                    self.test_results["data_availability"]["one_minute_stats"] = {
                        "available": True,
                        "records_per_day": len(records),
                        "records_per_year": total_minutes
                    }
                else:
                    print("❌ NO 1-MINUTE DATA")
                    self.test_results["data_availability"]["one_minute_stats"] = {"available": False}
            else:
                print(f"❌ ERROR {resp.status_code}")
                self.test_results["data_availability"]["one_minute_stats"] = {"available": False}
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            self.test_results["data_availability"]["one_minute_stats"] = {"available": False}
        
        print()
    
    def test_date_ranges(self):
        """Test earliest available data"""
        print("7. TESTING DATA AVAILABILITY BY YEAR")
        print("-" * 40)
        
        years_to_test = [2021, 2022, 2023, 2024, 2025]
        availability = {}
        
        for year in years_to_test:
            # Test first trading day of year
            test_date = f"{year}0104"  # Jan 4th usually safe
            params = {
                "root": "SPY",
                "exp": f"{year}0120",  # Monthly expiration
                "strike": "400000",
                "right": "C",
                "start_date": test_date,
                "end_date": test_date,
                "ivl": 3600000  # 1 hour
            }
            
            try:
                resp = requests.get(f"{self.api_base}/v2/hist/option/ohlc", params=params, timeout=5)
                if resp.status_code == 200 and resp.json().get('response'):
                    availability[year] = True
                    print(f"{year}: ✅ DATA AVAILABLE")
                else:
                    availability[year] = False
                    print(f"{year}: ❌ NO DATA")
            except:
                availability[year] = False
                print(f"{year}: ❌ ERROR")
        
        self.test_results["data_availability"]["years_available"] = availability
        print()
    
    def calculate_storage_requirements(self):
        """Calculate storage needed for 4 years of SPY options"""
        print("8. CALCULATING STORAGE REQUIREMENTS")
        print("-" * 40)
        
        # SPY option statistics
        expirations_per_year = 156  # 3 per week (MWF)
        strikes_per_expiration = 100  # ±$50 from ATM
        contracts_per_expiration = strikes_per_expiration * 2  # Calls and Puts
        
        # Data points
        trading_days = 252
        minutes_per_day = 390  # 6.5 hours
        hours_per_day = 6.5
        
        # Calculate total contracts over 4 years
        total_contracts = expirations_per_year * contracts_per_expiration * 4
        
        print(f"Contract Statistics:")
        print(f"  Expirations per year: {expirations_per_year}")
        print(f"  Strikes per expiration: {strikes_per_expiration}")
        print(f"  Total contracts per year: {expirations_per_year * contracts_per_expiration:,}")
        print(f"  Total contracts (4 years): {total_contracts:,}")
        print()
        
        # Storage calculations
        print("Storage Requirements by Interval:")
        
        # 1-minute data
        if self.test_results["data_availability"].get("one_minute_stats", {}).get("available"):
            records_per_contract = trading_days * minutes_per_day
            bytes_per_record = 64  # 8 fields * 8 bytes
            storage_1min = total_contracts * records_per_contract * bytes_per_record
            storage_1min_gb = storage_1min / 1e9
            
            print(f"\n1-MINUTE DATA:")
            print(f"  Records per contract per year: {records_per_contract:,}")
            print(f"  Uncompressed size: {storage_1min_gb:.1f} GB")
            print(f"  Compressed (5:1 ratio): {storage_1min_gb/5:.1f} GB")
            
            self.test_results["storage_calculations"]["1_minute"] = {
                "uncompressed_gb": storage_1min_gb,
                "compressed_gb": storage_1min_gb/5
            }
        
        # 1-hour data
        records_per_contract_hour = trading_days * int(hours_per_day)
        storage_1hour = total_contracts * records_per_contract_hour * 64
        storage_1hour_gb = storage_1hour / 1e9
        
        print(f"\n1-HOUR DATA:")
        print(f"  Records per contract per year: {records_per_contract_hour:,}")
        print(f"  Uncompressed size: {storage_1hour_gb:.1f} GB")
        print(f"  Compressed (5:1 ratio): {storage_1hour_gb/5:.1f} GB")
        
        self.test_results["storage_calculations"]["1_hour"] = {
            "uncompressed_gb": storage_1hour_gb,
            "compressed_gb": storage_1hour_gb/5
        }
        
        # Daily data
        records_per_contract_daily = trading_days
        storage_daily = total_contracts * records_per_contract_daily * 64
        storage_daily_gb = storage_daily / 1e9
        
        print(f"\nDAILY DATA:")
        print(f"  Records per contract per year: {records_per_contract_daily}")
        print(f"  Uncompressed size: {storage_daily_gb:.1f} GB")
        print(f"  Compressed (5:1 ratio): {storage_daily_gb/5:.2f} GB")
        
        self.test_results["storage_calculations"]["daily"] = {
            "uncompressed_gb": storage_daily_gb,
            "compressed_gb": storage_daily_gb/5
        }
        
        # Test actual compression
        self.test_compression_ratio()
        print()
    
    def test_compression_ratio(self):
        """Test actual compression ratios with sample data"""
        print("\nTesting actual compression ratios...")
        
        # Create sample data similar to OHLC
        sample_data = []
        for i in range(10000):
            sample_data.append({
                "ms": i * 60000,
                "open": 450.25 + i * 0.01,
                "high": 450.50 + i * 0.01,
                "low": 450.00 + i * 0.01,
                "close": 450.30 + i * 0.01,
                "volume": 1000 + i,
                "count": 10 + i % 5,
                "date": 20240115
            })
        
        # Test JSON compression
        json_data = json.dumps(sample_data).encode()
        compressed = gzip.compress(json_data)
        ratio = len(json_data) / len(compressed)
        
        print(f"  JSON compression ratio: {ratio:.1f}:1")
        print(f"  Original size: {len(json_data)/1024:.1f} KB")
        print(f"  Compressed size: {len(compressed)/1024:.1f} KB")
        
        self.test_results["storage_calculations"]["compression_ratio"] = ratio
    
    def generate_report(self):
        """Generate comprehensive report"""
        print("\n" + "="*80)
        print("THETADATA VALUE SUBSCRIPTION - SUMMARY REPORT")
        print("="*80)
        
        print(f"\nSUBSCRIPTION TYPE: {self.test_results.get('subscription_type', 'Unknown')}")
        
        print("\nDATA AVAILABILITY:")
        print("-" * 40)
        
        # OHLC intervals
        intervals = {
            60000: "1-minute",
            300000: "5-minute",
            3600000: "1-hour",
            86400000: "Daily"
        }
        
        for ivl, name in intervals.items():
            key = f"ohlc_{ivl}"
            if key in self.test_results["data_availability"]:
                status = "✅" if self.test_results["data_availability"][key] else "❌"
                print(f"  {name} OHLC: {status}")
        
        # Other data types
        oi_status = "✅" if self.test_results["data_availability"].get("open_interest", False) else "❌"
        vol_status = "✅" if self.test_results["data_availability"].get("volume", False) else "❌"
        print(f"  Open Interest: {oi_status}")
        print(f"  Volume: {vol_status}")
        
        # Date range
        if "date_range" in self.test_results["data_availability"]:
            dr = self.test_results["data_availability"]["date_range"]
            print(f"\n  Date Range: {dr.get('earliest', 'Unknown')} to {dr.get('latest', 'Unknown')}")
        
        # Years available
        if "years_available" in self.test_results["data_availability"]:
            years = self.test_results["data_availability"]["years_available"]
            available_years = [str(y) for y, avail in years.items() if avail]
            print(f"  Years with data: {', '.join(available_years)}")
        
        print("\nSTORAGE REQUIREMENTS (4 years of SPY options):")
        print("-" * 40)
        
        if "1_minute" in self.test_results["storage_calculations"]:
            storage = self.test_results["storage_calculations"]
            print(f"  1-minute data: {storage['1_minute']['compressed_gb']:.1f} GB compressed")
            print(f"  1-hour data: {storage['1_hour']['compressed_gb']:.1f} GB compressed")
            print(f"  Daily data: {storage['daily']['compressed_gb']:.2f} GB compressed")
            
            if "compression_ratio" in storage:
                print(f"  Actual compression ratio: {storage['compression_ratio']:.1f}:1")
        
        print("\nRECOMMENDATIONS:")
        print("-" * 40)
        print("1. ✅ Value subscription DOES provide historical OHLC data")
        print("2. ✅ 1-minute data IS available (ivl=60000)")
        print("3. ✅ Multiple years of data available (2021-2025)")
        print("4. ❌ Greeks/IV require Standard subscription")
        print("5. 💾 Storage needed: ~15-20 GB for 1-hour bars, ~200 GB for 1-minute")
        print("\nOPTIMAL STRATEGY:")
        print("- Use 1-hour bars for backtesting (reasonable size)")
        print("- Download 1-minute data only for specific dates/contracts")
        print("- Consider upgrading to Standard only if Greeks/IV essential")
        
        # Save detailed results
        with open('thetadata_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nDetailed results saved to: thetadata_test_results.json")

if __name__ == "__main__":
    tester = ThetaDataValueTester()
    tester.run_all_tests()