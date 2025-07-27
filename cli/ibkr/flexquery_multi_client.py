#!/usr/bin/env python3
"""
Multi-Query IBKR FlexQuery API Client
Handles fetching multiple FlexQuery reports in parallel
"""
import os
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time
import concurrent.futures
from dataclasses import dataclass

from flexquery_config import flexquery_manager, FlexQueryConfig

logger = logging.getLogger(__name__)


@dataclass 
class FlexQueryResult:
    """Result from a FlexQuery API request"""
    query_config: FlexQueryConfig
    reference_code: Optional[str] = None
    xml_data: Optional[str] = None
    error: Optional[str] = None
    fetch_time: Optional[datetime] = None
    

class MultiFlexQueryClient:
    """Client for fetching multiple IBKR FlexQuery reports"""
    
    def __init__(self):
        self.base_url = "https://gdcdyn.interactivebrokers.com/Universal/servlet"
        self.token = flexquery_manager.token
        self.max_workers = 5  # Parallel request limit
        self.request_timeout = 30
        self.fetch_timeout = 60
        self.max_retries = 20
        
    def request_single_report(self, query_config: FlexQueryConfig) -> FlexQueryResult:
        """Request a single FlexQuery report"""
        result = FlexQueryResult(query_config=query_config)
        
        url = f"{self.base_url}/FlexStatementService.SendRequest"
        params = {
            "t": self.token,
            "q": query_config.query_id,
            "v": "3"
        }
        
        try:
            logger.info(f"Requesting {query_config.name} (ID: {query_config.query_id})")
            response = requests.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            if root.tag == "FlexStatementResponse":
                status = root.find("Status")
                if status is not None and status.text == "Success":
                    reference_code = root.find("ReferenceCode")
                    if reference_code is not None:
                        result.reference_code = reference_code.text
                        logger.info(f"Request successful for {query_config.name}: {result.reference_code}")
                else:
                    error_code = root.find("ErrorCode")
                    error_msg = root.find("ErrorMessage") 
                    result.error = f"{error_code.text if error_code is not None else 'Unknown'} - " \
                                  f"{error_msg.text if error_msg is not None else 'Unknown error'}"
                    logger.error(f"Request failed for {query_config.name}: {result.error}")
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Exception requesting {query_config.name}: {e}")
            
        return result
    
    def fetch_single_report(self, result: FlexQueryResult) -> FlexQueryResult:
        """Fetch a previously requested report using reference code"""
        if not result.reference_code:
            return result
            
        url = f"{self.base_url}/FlexStatementService.GetStatement"
        
        for attempt in range(self.max_retries):
            params = {
                "q": result.reference_code,
                "t": self.token,
                "v": "3"
            }
            
            try:
                logger.info(f"Fetching {result.query_config.name} (attempt {attempt + 1}/{self.max_retries})")
                response = requests.get(url, params=params, timeout=self.fetch_timeout)
                
                if response.status_code == 200:
                    # Check if report is ready
                    if (response.text.startswith("<?xml") or "FlexQueryResponse" in response.text) and \
                       "Statement generation in progress" not in response.text:
                        result.xml_data = response.text
                        result.fetch_time = datetime.now()
                        logger.info(f"Successfully fetched {result.query_config.name}")
                        return result
                    elif "not yet available" in response.text.lower() or \
                         "generation in progress" in response.text.lower():
                        logger.info(f"Report not ready for {result.query_config.name}, waiting...")
                        time.sleep(10)
                        continue
                else:
                    result.error = f"HTTP {response.status_code}: {response.text[:100]}"
                    logger.error(f"HTTP error for {result.query_config.name}: {result.error}")
                    return result
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Retry {attempt + 1} for {result.query_config.name}: {e}")
                    time.sleep(5)
                    continue
                result.error = str(e)
                logger.error(f"Failed to fetch {result.query_config.name}: {e}")
                
        if not result.error:
            result.error = "Max retries reached"
        return result
    
    def request_all_reports(self, query_configs: List[FlexQueryConfig]) -> List[FlexQueryResult]:
        """Request multiple reports in parallel"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_config = {
                executor.submit(self.request_single_report, config): config 
                for config in query_configs
            }
            
            for future in concurrent.futures.as_completed(future_to_config):
                result = future.result()
                results.append(result)
                
        return results
    
    def fetch_all_reports(self, results: List[FlexQueryResult]) -> List[FlexQueryResult]:
        """Fetch all previously requested reports"""
        # Wait a bit for reports to be generated
        time.sleep(5)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.fetch_single_report, result) for result in results]
            fetched_results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        return fetched_results
    
    def get_reports(self, query_configs: List[FlexQueryConfig]) -> Tuple[List[FlexQueryResult], List[FlexQueryResult]]:
        """Get multiple FlexQuery reports - returns (successful, failed)"""
        logger.info(f"Starting batch request for {len(query_configs)} FlexQuery reports")
        
        # Request all reports
        results = self.request_all_reports(query_configs)
        
        # Separate successful requests from failed
        requested = [r for r in results if r.reference_code]
        failed = [r for r in results if not r.reference_code]
        
        if requested:
            logger.info(f"Successfully requested {len(requested)} reports, now fetching...")
            # Fetch the successfully requested reports
            fetched = self.fetch_all_reports(requested)
            
            # Separate successful fetches from failed
            successful = [r for r in fetched if r.xml_data]
            failed.extend([r for r in fetched if not r.xml_data])
        else:
            successful = []
            
        logger.info(f"Batch complete: {len(successful)} successful, {len(failed)} failed")
        return successful, failed
    
    def get_daily_reports(self) -> Tuple[List[FlexQueryResult], List[FlexQueryResult]]:
        """Get all LBD (Last Business Day) reports for daily import"""
        daily_queries = flexquery_manager.get_daily_queries()
        return self.get_reports(daily_queries)
    
    def get_monthly_reports(self) -> Tuple[List[FlexQueryResult], List[FlexQueryResult]]:
        """Get all MTD (Month to Date) reports for monthly reconciliation"""
        monthly_queries = flexquery_manager.get_monthly_queries()
        return self.get_reports(monthly_queries)
    
    def get_single_report(self, import_type: str) -> Optional[FlexQueryResult]:
        """Get a single report by import type"""
        query_config = flexquery_manager.get_query(import_type)
        if not query_config:
            logger.error(f"Unknown import type: {import_type}")
            return None
            
        result = self.request_single_report(query_config)
        if result.reference_code:
            time.sleep(5)
            result = self.fetch_single_report(result)
            
        return result if result.xml_data else None


if __name__ == "__main__":
    # Test the multi-client
    logging.basicConfig(level=logging.INFO)
    
    client = MultiFlexQueryClient()
    
    # Test with one query
    print("\nTesting single query fetch...")
    result = client.get_single_report("NAV_LBD")
    if result:
        print(f"✓ Successfully fetched {result.query_config.name}")
        print(f"  XML size: {len(result.xml_data)} bytes")
    else:
        print("✗ Failed to fetch NAV_LBD")
    
    # Test daily reports (uncomment to test all)
    # print("\nTesting daily reports batch fetch...")
    # successful, failed = client.get_daily_reports()
    # print(f"\nResults:")
    # print(f"  Successful: {len(successful)}")
    # for r in successful:
    #     print(f"    ✓ {r.query_config.name} - {len(r.xml_data)} bytes")
    # print(f"  Failed: {len(failed)}")
    # for r in failed:
    #     print(f"    ✗ {r.query_config.name} - {r.error}")