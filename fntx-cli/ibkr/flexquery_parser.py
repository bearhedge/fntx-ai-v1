#!/usr/bin/env python3
"""
Streaming FlexQuery XML Parser
Handles IBKR FlexQuery XML files of any size using iterparse
"""

import xml.etree.ElementTree as ET
from typing import Iterator, Dict, Any, List, Optional, Set
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FlexQueryParser:
    """Streaming parser for IBKR FlexQuery XML files"""
    
    def __init__(self):
        self.supported_record_types = {
            'Trade', 'Order', 'AssetSummary', 'SymbolSummary',
            'OpenPosition', 'CashTransaction', 'InterestAccrualsCurrency',
            'EquitySummaryByReportDateInBase', 'CashReport',
            'ChangeInNAV', 'ChangeInPositionValue'
        }
    
    def parse_flexquery_stream(self, file_path: str, 
                           record_types: Optional[Set[str]] = None) -> Iterator[Dict[str, Any]]:
        """
        Stream parse a FlexQuery XML file, yielding individual records
        
        Args:
            file_path: Path to the XML file
            record_types: Set of record types to parse (None = all supported types)
            
        Yields:
            Dict containing parsed record data with '_record_type' field
        """
        if record_types is None:
            record_types = self.supported_record_types
        
        # Use iterparse for streaming
        context = ET.iterparse(file_path, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        record_count = 0
        
        try:
            for event, elem in context:
                if event == 'end' and elem.tag in record_types:
                    # Parse the element based on its type
                    record = self._parse_element(elem)
                    if record:
                        record['_record_type'] = elem.tag
                        record_count += 1
                        yield record
                    
                    # Clear the element to free memory
                    elem.clear()
                    # Also clear the root element's children periodically
                    if record_count % 100 == 0:
                        root.clear()
        
        except Exception as e:
            logger.error(f"Error parsing FlexQuery XML: {e}")
            raise
        finally:
            # Final cleanup
            root.clear()
    
    def _parse_element(self, elem: ET.Element) -> Dict[str, Any]:
        """Convert XML element attributes to dictionary"""
        record = {}
        
        # Get all attributes
        for key, value in elem.attrib.items():
            # Skip empty values
            if value == '':
                continue
                
            # Convert numeric fields
            if self._is_numeric_field(key):
                try:
                    # Handle decimal values
                    if '.' in value or key in ['price', 'rate', 'commission']:
                        record[key] = Decimal(value)
                    else:
                        record[key] = int(value)
                except (ValueError, TypeError):
                    record[key] = value
            # Convert date fields
            elif self._is_date_field(key):
                record[key] = self._parse_date(value)
            else:
                record[key] = value
        
        return record
    
    def _is_numeric_field(self, field_name: str) -> bool:
        """Check if field should be treated as numeric"""
        numeric_keywords = [
            'quantity', 'price', 'amount', 'proceeds', 'commission',
            'cash', 'value', 'pnl', 'cost', 'balance', 'rate',
            'money', 'total', 'fee', 'interest', 'strike'
        ]
        field_lower = field_name.lower()
        return any(keyword in field_lower for keyword in numeric_keywords)
    
    def _is_date_field(self, field_name: str) -> bool:
        """Check if field should be treated as date"""
        date_keywords = ['date', 'time', 'expiry']
        field_lower = field_name.lower()
        return any(keyword in field_lower for keyword in date_keywords)
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from IBKR"""
        if not date_str:
            return None
            
        # Common IBKR date formats
        formats = [
            '%Y%m%d',                    # 20250718
            '%Y%m%d;%H%M%S',            # 20250718;162000 (ignore timezone)
            '%Y-%m-%d',                  # 2025-07-18
            '%Y-%m-%dT%H:%M:%S',        # 2025-07-18T16:20:00
        ]
        
        # Remove timezone suffix if present
        date_str_clean = date_str.split(' ')[0]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str_clean, fmt)
            except ValueError:
                continue
        
        # If no format matches, try to parse just the date part
        if len(date_str) >= 8:
            try:
                # Extract just YYYYMMDD
                date_part = date_str[:8]
                return datetime.strptime(date_part, '%Y%m%d')
            except ValueError:
                pass
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def parse_trades(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Parse only trade records from a Trades FlexQuery"""
        return self.parse_flexquery_stream(file_path, {'Trade'})
    
    def parse_nav(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Parse NAV-related records from a NAV FlexQuery"""
        nav_types = {
            'EquitySummaryByReportDateInBase', 'CashReport',
            'ChangeInNAV', 'ChangeInPositionValue'
        }
        return self.parse_flexquery_stream(file_path, nav_types)
    
    def parse_cash_transactions(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Parse cash transaction records"""
        return self.parse_flexquery_stream(file_path, {'CashTransaction'})
    
    def parse_interest_accruals(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Parse interest accrual records"""
        return self.parse_flexquery_stream(file_path, {'InterestAccrualsCurrency'})
    
    def parse_open_positions(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Parse open position records"""
        return self.parse_flexquery_stream(file_path, {'OpenPosition'})
    
    def parse_exercises_expiries(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Parse option exercise and expiry records"""
        # These typically come as Trade records with special transaction types
        for record in self.parse_flexquery_stream(file_path, {'Trade'}):
            if record.get('transactionType') in ['Exercise', 'Expiry', 'Assignment']:
                yield record
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from FlexQuery file header"""
        metadata = {}
        
        # Parse just the header elements
        for event, elem in ET.iterparse(file_path, events=('start', 'end')):
            if event == 'end' and elem.tag == 'FlexStatement':
                metadata['account_id'] = elem.get('accountId')
                metadata['from_date'] = self._parse_date(elem.get('fromDate'))
                metadata['to_date'] = self._parse_date(elem.get('toDate'))
                metadata['period'] = elem.get('period')
                metadata['when_generated'] = elem.get('whenGenerated')
                elem.clear()
                break
            elif event == 'end' and elem.tag == 'FlexQueryResponse':
                metadata['query_name'] = elem.get('queryName')
                metadata['type'] = elem.get('type')
        
        return metadata


# Utility functions for common operations

def count_records(file_path: str) -> Dict[str, int]:
    """Count records by type in a FlexQuery file"""
    parser = FlexQueryParser()
    counts = {}
    
    for record in parser.parse_flexquery_stream(file_path):
        record_type = record['_record_type']
        counts[record_type] = counts.get(record_type, 0) + 1
    
    return counts


def validate_flexquery_file(file_path: str) -> bool:
    """Validate that a file is a valid FlexQuery XML"""
    try:
        # Try to parse the first few elements
        parser = FlexQueryParser()
        metadata = parser.get_file_metadata(file_path)
        return 'account_id' in metadata
    except Exception as e:
        logger.error(f"Invalid FlexQuery file {file_path}: {e}")
        return False