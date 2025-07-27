#!/usr/bin/env python3
"""
FlexQuery API to Parser Bridge
Connects the Multi-Query API client with the streaming parser and database importer
"""
import os
import logging
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from flexquery_multi_client import MultiFlexQueryClient, FlexQueryResult
from flexquery_parser import FlexQueryParser
from db_importer import FlexQueryDBImporter
from flexquery_config import flexquery_manager

logger = logging.getLogger(__name__)


class FlexQueryAPIBridge:
    """Bridge between FlexQuery API and the parsing/import pipeline"""
    
    def __init__(self, connection_string: str):
        self.api_client = MultiFlexQueryClient()
        self.parser = FlexQueryParser()
        self.db_importer = FlexQueryDBImporter(connection_string)
        self.temp_dir = tempfile.mkdtemp(prefix="flexquery_")
        logger.info(f"Created temporary directory: {self.temp_dir}")
        
    def save_xml_to_temp(self, result: FlexQueryResult) -> Optional[str]:
        """Save XML data to temporary file for parsing"""
        if not result.xml_data:
            return None
            
        filename = f"{result.query_config.import_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        filepath = os.path.join(self.temp_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result.xml_data)
            logger.info(f"Saved XML to temporary file: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save XML to temp file: {e}")
            return None
    
    def import_single_report(self, import_type: str) -> Dict[str, Any]:
        """Fetch and import a single FlexQuery report"""
        logger.info(f"Starting import for {import_type}")
        
        # Fetch report from API
        result = self.api_client.get_single_report(import_type)
        if not result or not result.xml_data:
            return {
                'status': 'FAILED',
                'import_type': import_type,
                'error': result.error if result else 'Failed to fetch report'
            }
        
        # Save to temp file
        temp_filepath = self.save_xml_to_temp(result)
        if not temp_filepath:
            return {
                'status': 'FAILED',
                'import_type': import_type,
                'error': 'Failed to save XML to temporary file'
            }
        
        # Import using our existing pipeline
        try:
            import_result = self.db_importer.import_flexquery_file(temp_filepath, import_type)
            import_result['source'] = 'API'
            import_result['fetch_time'] = result.fetch_time.isoformat() if result.fetch_time else None
            return import_result
        finally:
            # Clean up temp file
            try:
                os.remove(temp_filepath)
            except:
                pass
    
    def import_daily_reports(self) -> Dict[str, Any]:
        """Import all daily (LBD) reports"""
        logger.info("Starting daily import of all LBD reports")
        start_time = datetime.now()
        
        # Fetch all daily reports
        successful_fetches, failed_fetches = self.api_client.get_daily_reports()
        
        results = {
            'start_time': start_time.isoformat(),
            'total_queries': len(flexquery_manager.get_daily_queries()),
            'fetched': len(successful_fetches),
            'fetch_failed': len(failed_fetches),
            'imports': [],
            'errors': []
        }
        
        # Log fetch failures
        for failed in failed_fetches:
            error_info = {
                'import_type': failed.query_config.import_type,
                'query_name': failed.query_config.name,
                'error': failed.error
            }
            results['errors'].append(error_info)
            logger.error(f"Failed to fetch {failed.query_config.name}: {failed.error}")
        
        # Import successful fetches
        for fetched in successful_fetches:
            temp_filepath = self.save_xml_to_temp(fetched)
            if not temp_filepath:
                results['errors'].append({
                    'import_type': fetched.query_config.import_type,
                    'query_name': fetched.query_config.name,
                    'error': 'Failed to save XML'
                })
                continue
            
            try:
                import_result = self.db_importer.import_flexquery_file(
                    temp_filepath, 
                    fetched.query_config.import_type
                )
                import_result['query_name'] = fetched.query_config.name
                import_result['source'] = 'API'
                results['imports'].append(import_result)
                
                if import_result['status'] == 'COMPLETED':
                    logger.info(f"Successfully imported {fetched.query_config.name}: "
                              f"{import_result.get('results', {})}")
                else:
                    logger.error(f"Import failed for {fetched.query_config.name}: "
                               f"{import_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Exception importing {fetched.query_config.name}: {e}")
                results['errors'].append({
                    'import_type': fetched.query_config.import_type,
                    'query_name': fetched.query_config.name,
                    'error': str(e)
                })
            finally:
                # Clean up temp file
                try:
                    os.remove(temp_filepath)
                except:
                    pass
        
        # Summary
        results['end_time'] = datetime.now().isoformat()
        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        results['successful_imports'] = sum(1 for i in results['imports'] if i['status'] == 'COMPLETED')
        results['failed_imports'] = len(results['errors']) + sum(1 for i in results['imports'] if i['status'] != 'COMPLETED')
        
        logger.info(f"Daily import complete: {results['successful_imports']} successful, "
                   f"{results['failed_imports']} failed")
        
        return results
    
    def import_monthly_reports(self) -> Dict[str, Any]:
        """Import all monthly (MTD) reports for reconciliation"""
        logger.info("Starting monthly import of all MTD reports")
        start_time = datetime.now()
        
        # Fetch all monthly reports
        successful_fetches, failed_fetches = self.api_client.get_monthly_reports()
        
        results = {
            'start_time': start_time.isoformat(),
            'total_queries': len(flexquery_manager.get_monthly_queries()),
            'fetched': len(successful_fetches),
            'fetch_failed': len(failed_fetches),
            'imports': [],
            'errors': []
        }
        
        # Process similar to daily imports...
        # (Code similar to import_daily_reports but for MTD queries)
        
        return results
    
    def get_import_summary(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable summary of import results"""
        summary = []
        summary.append(f"Import Summary - {results.get('start_time', 'Unknown time')}")
        summary.append("=" * 60)
        summary.append(f"Total queries: {results.get('total_queries', 0)}")
        summary.append(f"Successfully fetched: {results.get('fetched', 0)}")
        summary.append(f"Fetch failures: {results.get('fetch_failed', 0)}")
        summary.append(f"Successful imports: {results.get('successful_imports', 0)}")
        summary.append(f"Failed imports: {results.get('failed_imports', 0)}")
        summary.append(f"Duration: {results.get('duration_seconds', 0):.1f} seconds")
        
        if results.get('imports'):
            summary.append("\nSuccessful Imports:")
            for imp in results['imports']:
                if imp['status'] == 'COMPLETED':
                    summary.append(f"  ✓ {imp.get('query_name', imp.get('import_type'))}: "
                                 f"{imp.get('results', {}).get('records_processed', 0)} records")
        
        if results.get('errors'):
            summary.append("\nErrors:")
            for err in results['errors']:
                summary.append(f"  ✗ {err.get('query_name', err.get('import_type'))}: {err.get('error')}")
        
        return "\n".join(summary)
    
    def cleanup(self):
        """Clean up temporary directory"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {e}")


def run_daily_import(connection_string: str) -> Dict[str, Any]:
    """Convenience function to run daily import"""
    bridge = FlexQueryAPIBridge(connection_string)
    try:
        results = bridge.import_daily_reports()
        print(bridge.get_import_summary(results))
        return results
    finally:
        bridge.cleanup()


if __name__ == "__main__":
    # Test the bridge
    logging.basicConfig(level=logging.INFO)
    
    # You'll need to set the actual connection string
    CONNECTION_STRING = os.getenv("DATABASE_URL", "postgresql://username:password@localhost/dbname")
    
    bridge = FlexQueryAPIBridge(CONNECTION_STRING)
    
    try:
        # Test single import
        print("\nTesting single import (NAV_LBD)...")
        result = bridge.import_single_report("NAV_LBD")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Uncomment to test full daily import
        # print("\nTesting daily import...")
        # daily_results = bridge.import_daily_reports()
        # print(bridge.get_import_summary(daily_results))
        
    finally:
        bridge.cleanup()