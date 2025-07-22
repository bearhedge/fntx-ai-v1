#!/usr/bin/env python3
"""
Database Importer for IBKR FlexQuery Data
Handles batch insertion of parsed FlexQuery records into PostgreSQL
"""

import psycopg2
from psycopg2.extras import execute_batch, execute_values
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime
import logging
import hashlib
import os
import re

from flexquery_parser import FlexQueryParser

logger = logging.getLogger(__name__)


class FlexQueryDBImporter:
    """Imports parsed FlexQuery data into PostgreSQL database"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.parser = FlexQueryParser()
        
    def import_flexquery_file(self, file_path: str, import_type: str) -> Dict[str, Any]:
        """Import a complete FlexQuery file into the database"""
        import_id = None
        
        try:
            # Get file metadata
            file_stats = os.stat(file_path)
            file_hash = self._calculate_file_hash(file_path)
            metadata = self.parser.get_file_metadata(file_path)
            
            # Start database transaction
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    
                    # Check if file already imported
                    cursor.execute("""
                        SELECT import_id, import_status 
                        FROM portfolio.flexquery_imports 
                        WHERE file_hash = %s AND import_type = %s
                    """, (file_hash, import_type))
                    
                    existing = cursor.fetchone()
                    if existing:
                        logger.warning(f"File already imported: {file_path}")
                        return {
                            'import_id': existing[0],
                            'status': 'DUPLICATE',
                            'message': 'File already imported'
                        }
                    
                    # Create import record
                    import_id = self._create_import_record(
                        cursor, file_path, import_type, file_stats.st_size, 
                        file_hash, metadata
                    )
                    
                    # Process import
                    start_time = datetime.now()
                    results = self._import_by_type(cursor, file_path, import_type, import_id)
                    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    # Update import record
                    self._complete_import_record(cursor, import_id, results, duration_ms)
                    
                    conn.commit()
                    logger.info(f"Successfully imported {file_path}: {results}")
                    
                    return {
                        'import_id': import_id,
                        'status': 'COMPLETED',
                        'results': results,
                        'duration_ms': duration_ms
                    }
                    
        except Exception as e:
            logger.error(f"Error importing {file_path}: {e}")
            return {
                'import_id': import_id,
                'status': 'FAILED',
                'error': str(e)
            }
    
    def _import_by_type(self, cursor, file_path: str, import_type: str, 
                       import_id: str) -> Dict[str, int]:
        """Route import to appropriate handler based on type"""
        
        if 'NAV' in import_type:
            return self._import_nav_data(cursor, file_path, import_id)
        elif 'OPEN_POSITIONS' in import_type:
            return self._import_positions_data(cursor, file_path, import_id)
        elif 'CASH_TRANSACTIONS' in import_type:
            return self._import_cash_transactions(cursor, file_path, import_id)
        elif 'INTEREST_ACCRUALS' in import_type:
            return self._import_interest_accruals(cursor, file_path, import_id)
        elif 'TRADES' in import_type:
            return self._import_trades_data(cursor, file_path, import_id)
        elif 'EXERCISES_EXPIRIES' in import_type:
            return self._import_exercises_expiries_data(cursor, file_path, import_id)
        else:
            raise ValueError(f"Unsupported import type: {import_type}")
    
    def _import_nav_data(self, cursor, file_path: str, import_id: str) -> Dict[str, int]:
        """Import NAV-related data"""
        records_processed = 0
        records_inserted = 0
        nav_records = []
        
        for record in self.parser.parse_nav(file_path):
            records_processed += 1
            
            if record['_record_type'] == 'EquitySummaryByReportDateInBase':
                nav_record = self._prepare_nav_record(record, import_id)
                if nav_record:
                    nav_records.append(nav_record)
        
        if nav_records:
            insert_sql = """
                INSERT INTO portfolio.nav_snapshots (
                    report_date, from_date, to_date, period,
                    opening_nav, closing_nav, change_in_nav,
                    change_in_position_value, realized_pnl, unrealized_pnl,
                    cash_balance, cash_changes,
                    account_id, base_currency, flexquery_import_id
                ) VALUES %s
                ON CONFLICT (report_date, account_id, period) 
                DO UPDATE SET
                    closing_nav = EXCLUDED.closing_nav,
                    change_in_nav = EXCLUDED.change_in_nav,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            execute_values(cursor, insert_sql, nav_records, page_size=100)
            records_inserted = len(nav_records)
        
        return {
            'records_processed': records_processed,
            'records_inserted': records_inserted,
            'records_updated': 0,
            'records_skipped': records_processed - records_inserted
        }
    
    def _prepare_cash_transaction_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare cash transaction record for database insertion"""
        try:
            # Determine category from type
            transaction_type = record.get('type', '')
            if 'Deposit' in transaction_type:
                category = 'DEPOSIT'
            elif 'Withdrawal' in transaction_type:
                category = 'WITHDRAWAL'
            elif 'Interest' in transaction_type and 'Paid' in transaction_type:
                category = 'INTEREST_PAID'
            elif 'Interest' in transaction_type and 'Received' in transaction_type:
                category = 'INTEREST_RECEIVED'
            elif 'Fee' in transaction_type:
                category = 'FEE'
            elif 'Commission' in transaction_type:
                category = 'COMMISSION_ADJ'
            else:
                category = 'OTHER'
            
            return (
                record.get('dateTime', record.get('date')),  # transaction_date
                record.get('dateTime'),  # transaction_time
                transaction_type,  # transaction_type
                category,  # category
                record.get('amount', 0),  # amount
                record.get('currency', 'USD'),  # currency
                record.get('currencyPrimary', 'HKD'),  # currency_primary
                record.get('description'),  # description
                record.get('transactionID'),  # ibkr_transaction_id
                record.get('settleDate'),  # settlement_date
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing cash transaction record: {e}")
            return None
    
    def _prepare_interest_accrual_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare interest accrual record for database insertion"""
        try:
            return (
                record.get('fromDate'),  # from_date
                record.get('toDate'),  # to_date
                record.get('currency', 'HKD'),  # currency
                record.get('startingBalance'),  # starting_balance
                record.get('interestAccrued'),  # interest_accrued
                record.get('accrualReversal'),  # accrual_reversal
                record.get('fxTranslation'),  # fx_translation
                record.get('endingBalance'),  # ending_balance
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing interest accrual record: {e}")
            return None
    
    def import_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Import all FlexQuery XML files from a directory"""
        results = []
        import_types = {
            'NAV_(.*?)_MTD.xml': 'NAV_MTD',
            'NAV_(.*?)_LBD.xml': 'NAV_LBD',
            'Trades_(.*?)_MTD.xml': 'TRADES_MTD',
            'Trades_(.*?)_LBD.xml': 'TRADES_LBD',
            'Open_Positions_(.*?)_LBD.xml': 'OPEN_POSITIONS_LBD',
            'Cash_Transactions_(.*?)_MTD.xml': 'CASH_TRANSACTIONS_MTD',
            'Cash_Transactions_(.*?)_LBD.xml': 'CASH_TRANSACTIONS_LBD',
            'Interest_Accruals_(.*?)_MTD.xml': 'INTEREST_ACCRUALS_MTD',
            'Interest_Accruals_(.*?)_LBD.xml': 'INTEREST_ACCRUALS_LBD',
            'Exercises_and_Expiries_(.*?)_MTD.xml': 'EXERCISES_EXPIRIES_MTD',
            'Exercises_and_Expiries_(.*?)_LBD.xml': 'EXERCISES_EXPIRIES_LBD'
        }
        
        for filename in os.listdir(directory_path):
            if filename.endswith('.xml'):
                file_path = os.path.join(directory_path, filename)
                
                # Determine import type from filename
                import_type = None
                for pattern, itype in import_types.items():
                    if re.match(pattern, filename):
                        import_type = itype
                        break
                
                if import_type:
                    logger.info(f"Importing {filename} as {import_type}")
                    result = self.import_flexquery_file(file_path, import_type)
                    result['filename'] = filename
                    results.append(result)
                else:
                    logger.warning(f"Unknown file type: {filename}")
        
        return results
    
    def _import_positions_data(self, cursor, file_path: str, import_id: str) -> Dict[str, int]:
        """Import open positions data"""
        records_processed = 0
        records_inserted = 0
        position_records = []
        
        for record in self.parser.parse_open_positions(file_path):
            records_processed += 1
            position_record = self._prepare_position_record(record, import_id)
            if position_record:
                position_records.append(position_record)
        
        if position_records:
            insert_sql = """
                INSERT INTO portfolio.open_positions (
                    symbol, underlying_symbol, security_type,
                    strike, expiry, call_put, multiplier,
                    position, mark_price, position_value,
                    avg_cost, unrealized_pnl, pct_of_nav,
                    report_date, value_date,
                    account_id, currency, flexquery_import_id
                ) VALUES %s
                ON CONFLICT (report_date, account_id, symbol, security_type, strike, expiry, call_put)
                DO UPDATE SET
                    position = EXCLUDED.position,
                    mark_price = EXCLUDED.mark_price,
                    position_value = EXCLUDED.position_value,
                    unrealized_pnl = EXCLUDED.unrealized_pnl
            """
            
            execute_values(cursor, insert_sql, position_records, page_size=100)
            records_inserted = len(position_records)
        
        return {
            'records_processed': records_processed,
            'records_inserted': records_inserted,
            'records_updated': 0,
            'records_skipped': records_processed - records_inserted
        }
    
    def _prepare_cash_transaction_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare cash transaction record for database insertion"""
        try:
            # Determine category from type
            transaction_type = record.get('type', '')
            if 'Deposit' in transaction_type:
                category = 'DEPOSIT'
            elif 'Withdrawal' in transaction_type:
                category = 'WITHDRAWAL'
            elif 'Interest' in transaction_type and 'Paid' in transaction_type:
                category = 'INTEREST_PAID'
            elif 'Interest' in transaction_type and 'Received' in transaction_type:
                category = 'INTEREST_RECEIVED'
            elif 'Fee' in transaction_type:
                category = 'FEE'
            elif 'Commission' in transaction_type:
                category = 'COMMISSION_ADJ'
            else:
                category = 'OTHER'
            
            return (
                record.get('dateTime', record.get('date')),  # transaction_date
                record.get('dateTime'),  # transaction_time
                transaction_type,  # transaction_type
                category,  # category
                record.get('amount', 0),  # amount
                record.get('currency', 'USD'),  # currency
                record.get('currencyPrimary', 'HKD'),  # currency_primary
                record.get('description'),  # description
                record.get('transactionID'),  # ibkr_transaction_id
                record.get('settleDate'),  # settlement_date
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing cash transaction record: {e}")
            return None
    
    def _prepare_interest_accrual_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare interest accrual record for database insertion"""
        try:
            return (
                record.get('fromDate'),  # from_date
                record.get('toDate'),  # to_date
                record.get('currency', 'HKD'),  # currency
                record.get('startingBalance'),  # starting_balance
                record.get('interestAccrued'),  # interest_accrued
                record.get('accrualReversal'),  # accrual_reversal
                record.get('fxTranslation'),  # fx_translation
                record.get('endingBalance'),  # ending_balance
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing interest accrual record: {e}")
            return None
    
    def import_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Import all FlexQuery XML files from a directory"""
        results = []
        import_types = {
            'NAV_(.*?)_MTD.xml': 'NAV_MTD',
            'NAV_(.*?)_LBD.xml': 'NAV_LBD',
            'Trades_(.*?)_MTD.xml': 'TRADES_MTD',
            'Trades_(.*?)_LBD.xml': 'TRADES_LBD',
            'Open_Positions_(.*?)_LBD.xml': 'OPEN_POSITIONS_LBD',
            'Cash_Transactions_(.*?)_MTD.xml': 'CASH_TRANSACTIONS_MTD',
            'Cash_Transactions_(.*?)_LBD.xml': 'CASH_TRANSACTIONS_LBD',
            'Interest_Accruals_(.*?)_MTD.xml': 'INTEREST_ACCRUALS_MTD',
            'Interest_Accruals_(.*?)_LBD.xml': 'INTEREST_ACCRUALS_LBD',
            'Exercises_and_Expiries_(.*?)_MTD.xml': 'EXERCISES_EXPIRIES_MTD',
            'Exercises_and_Expiries_(.*?)_LBD.xml': 'EXERCISES_EXPIRIES_LBD'
        }
        
        for filename in os.listdir(directory_path):
            if filename.endswith('.xml'):
                file_path = os.path.join(directory_path, filename)
                
                # Determine import type from filename
                import_type = None
                for pattern, itype in import_types.items():
                    if re.match(pattern, filename):
                        import_type = itype
                        break
                
                if import_type:
                    logger.info(f"Importing {filename} as {import_type}")
                    result = self.import_flexquery_file(file_path, import_type)
                    result['filename'] = filename
                    results.append(result)
                else:
                    logger.warning(f"Unknown file type: {filename}")
        
        return results
    
    def _prepare_nav_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare NAV record for database insertion"""
        try:
            return (
                record.get('reportDate'),
                record.get('fromDate'),
                record.get('toDate'),
                record.get('period', 'Unknown'),
                record.get('startingValue'),
                record.get('endingValue'),
                record.get('changeInNav'),
                record.get('changeInPositionValue'),
                record.get('realizedPnl'),
                record.get('unrealizedPnl'),
                record.get('cash'),
                record.get('cashChanges'),
                record.get('accountId'),
                record.get('currency', 'HKD'),
                import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing NAV record: {e}")
            return None
    
    def _prepare_position_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare position record for database insertion"""
        try:
            return (
                record.get('symbol'),
                record.get('underlyingSymbol'),
                record.get('securityType'),
                record.get('strike'),
                record.get('expiry'),
                record.get('putCall'),
                record.get('multiplier', 1),
                record.get('position'),
                record.get('markPrice'),
                record.get('positionValue'),
                record.get('avgCost'),
                record.get('unrealizedPnl'),
                record.get('percentOfNAV'),
                record.get('reportDate'),
                record.get('valueDate'),
                record.get('accountId'),
                record.get('currency', 'USD'),
                import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing position record: {e}")
            return None
    
    def _create_import_record(self, cursor, file_path: str, import_type: str,
                            file_size: int, file_hash: str, 
                            metadata: Dict[str, Any]) -> str:
        """Create initial import tracking record"""
        cursor.execute("""
            INSERT INTO portfolio.flexquery_imports (
                import_type, file_path, file_size, file_hash,
                account_id, query_name, from_date, to_date, period, when_generated,
                import_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PROCESSING'
            ) RETURNING import_id
        """, (
            import_type, file_path, file_size, file_hash,
            metadata.get('account_id'),
            metadata.get('query_name'),
            metadata.get('from_date'),
            metadata.get('to_date'),
            metadata.get('period'),
            metadata.get('when_generated')
        ))
        
        return cursor.fetchone()[0]
    
    def _complete_import_record(self, cursor, import_id: str, 
                              results: Dict[str, int], duration_ms: int):
        """Complete import record with final results"""
        cursor.execute("""
            UPDATE portfolio.flexquery_imports 
            SET 
                import_status = 'COMPLETED',
                records_processed = %s,
                records_inserted = %s,
                records_updated = %s,
                records_skipped = %s,
                processing_duration_ms = %s,
                completed_at = CURRENT_TIMESTAMP
            WHERE import_id = %s
        """, (
            results['records_processed'],
            results['records_inserted'],
            results['records_updated'],
            results['records_skipped'],
            duration_ms,
            import_id
        ))
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file content"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _import_cash_transactions(self, cursor, file_path: str, import_id: str) -> Dict[str, int]:
        """Import cash transactions data"""
        records_processed = 0
        records_inserted = 0
        cash_records = []
        
        for record in self.parser.parse_cash_transactions(file_path):
            records_processed += 1
            cash_record = self._prepare_cash_transaction_record(record, import_id)
            if cash_record:
                cash_records.append(cash_record)
        
        if cash_records:
            insert_sql = """
                INSERT INTO portfolio.cash_transactions (
                    transaction_date, transaction_time, transaction_type,
                    category, amount, currency, currency_primary,
                    description, ibkr_transaction_id, settlement_date,
                    account_id, flexquery_import_id
                ) VALUES %s
                ON CONFLICT (ibkr_transaction_id) 
                DO UPDATE SET
                    amount = EXCLUDED.amount,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            execute_values(cursor, insert_sql, cash_records, page_size=100)
            records_inserted = len(cash_records)
        
        return {
            'records_processed': records_processed,
            'records_inserted': records_inserted,
            'records_updated': 0,
            'records_skipped': records_processed - records_inserted
        }
    
    def _prepare_cash_transaction_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare cash transaction record for database insertion"""
        try:
            # Determine category from type
            transaction_type = record.get('type', '')
            if 'Deposit' in transaction_type:
                category = 'DEPOSIT'
            elif 'Withdrawal' in transaction_type:
                category = 'WITHDRAWAL'
            elif 'Interest' in transaction_type and 'Paid' in transaction_type:
                category = 'INTEREST_PAID'
            elif 'Interest' in transaction_type and 'Received' in transaction_type:
                category = 'INTEREST_RECEIVED'
            elif 'Fee' in transaction_type:
                category = 'FEE'
            elif 'Commission' in transaction_type:
                category = 'COMMISSION_ADJ'
            else:
                category = 'OTHER'
            
            return (
                record.get('dateTime', record.get('date')),  # transaction_date
                record.get('dateTime'),  # transaction_time
                transaction_type,  # transaction_type
                category,  # category
                record.get('amount', 0),  # amount
                record.get('currency', 'USD'),  # currency
                record.get('currencyPrimary', 'HKD'),  # currency_primary
                record.get('description'),  # description
                record.get('transactionID'),  # ibkr_transaction_id
                record.get('settleDate'),  # settlement_date
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing cash transaction record: {e}")
            return None
    
    def _prepare_interest_accrual_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare interest accrual record for database insertion"""
        try:
            return (
                record.get('fromDate'),  # from_date
                record.get('toDate'),  # to_date
                record.get('currency', 'HKD'),  # currency
                record.get('startingBalance'),  # starting_balance
                record.get('interestAccrued'),  # interest_accrued
                record.get('accrualReversal'),  # accrual_reversal
                record.get('fxTranslation'),  # fx_translation
                record.get('endingBalance'),  # ending_balance
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing interest accrual record: {e}")
            return None
    
    def import_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Import all FlexQuery XML files from a directory"""
        results = []
        import_types = {
            'NAV_(.*?)_MTD.xml': 'NAV_MTD',
            'NAV_(.*?)_LBD.xml': 'NAV_LBD',
            'Trades_(.*?)_MTD.xml': 'TRADES_MTD',
            'Trades_(.*?)_LBD.xml': 'TRADES_LBD',
            'Open_Positions_(.*?)_LBD.xml': 'OPEN_POSITIONS_LBD',
            'Cash_Transactions_(.*?)_MTD.xml': 'CASH_TRANSACTIONS_MTD',
            'Cash_Transactions_(.*?)_LBD.xml': 'CASH_TRANSACTIONS_LBD',
            'Interest_Accruals_(.*?)_MTD.xml': 'INTEREST_ACCRUALS_MTD',
            'Interest_Accruals_(.*?)_LBD.xml': 'INTEREST_ACCRUALS_LBD',
            'Exercises_and_Expiries_(.*?)_MTD.xml': 'EXERCISES_EXPIRIES_MTD',
            'Exercises_and_Expiries_(.*?)_LBD.xml': 'EXERCISES_EXPIRIES_LBD'
        }
        
        for filename in os.listdir(directory_path):
            if filename.endswith('.xml'):
                file_path = os.path.join(directory_path, filename)
                
                # Determine import type from filename
                import_type = None
                for pattern, itype in import_types.items():
                    if re.match(pattern, filename):
                        import_type = itype
                        break
                
                if import_type:
                    logger.info(f"Importing {filename} as {import_type}")
                    result = self.import_flexquery_file(file_path, import_type)
                    result['filename'] = filename
                    results.append(result)
                else:
                    logger.warning(f"Unknown file type: {filename}")
        
        return results
    
    def _import_interest_accruals(self, cursor, file_path: str, import_id: str) -> Dict[str, int]:
        """Import interest accruals data"""
        records_processed = 0
        records_inserted = 0
        accrual_records = []
        
        for record in self.parser.parse_interest_accruals(file_path):
            records_processed += 1
            
            if record['_record_type'] == 'InterestAccrualsCurrency':
                accrual_record = self._prepare_interest_accrual_record(record, import_id)
                if accrual_record:
                    accrual_records.append(accrual_record)
        
        if accrual_records:
            insert_sql = """
                INSERT INTO portfolio.interest_accruals (
                    from_date, to_date, currency,
                    starting_balance, interest_accrued, accrual_reversal,
                    fx_translation, ending_balance,
                    account_id, flexquery_import_id
                ) VALUES %s
                ON CONFLICT (from_date, to_date, currency) 
                DO UPDATE SET
                    ending_balance = EXCLUDED.ending_balance,
                    interest_accrued = EXCLUDED.interest_accrued,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            execute_values(cursor, insert_sql, accrual_records, page_size=100)
            records_inserted = len(accrual_records)
        
        return {
            'records_processed': records_processed,
            'records_inserted': records_inserted,
            'records_updated': 0,
            'records_skipped': records_processed - records_inserted
        }
    
    def _prepare_cash_transaction_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare cash transaction record for database insertion"""
        try:
            # Determine category from type
            transaction_type = record.get('type', '')
            if 'Deposit' in transaction_type:
                category = 'DEPOSIT'
            elif 'Withdrawal' in transaction_type:
                category = 'WITHDRAWAL'
            elif 'Interest' in transaction_type and 'Paid' in transaction_type:
                category = 'INTEREST_PAID'
            elif 'Interest' in transaction_type and 'Received' in transaction_type:
                category = 'INTEREST_RECEIVED'
            elif 'Fee' in transaction_type:
                category = 'FEE'
            elif 'Commission' in transaction_type:
                category = 'COMMISSION_ADJ'
            else:
                category = 'OTHER'
            
            return (
                record.get('dateTime', record.get('date')),  # transaction_date
                record.get('dateTime'),  # transaction_time
                transaction_type,  # transaction_type
                category,  # category
                record.get('amount', 0),  # amount
                record.get('currency', 'USD'),  # currency
                record.get('currencyPrimary', 'HKD'),  # currency_primary
                record.get('description'),  # description
                record.get('transactionID'),  # ibkr_transaction_id
                record.get('settleDate'),  # settlement_date
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing cash transaction record: {e}")
            return None
    
    def _prepare_interest_accrual_record(self, record: Dict[str, Any], import_id: str) -> Optional[tuple]:
        """Prepare interest accrual record for database insertion"""
        try:
            return (
                record.get('fromDate'),  # from_date
                record.get('toDate'),  # to_date
                record.get('currency', 'HKD'),  # currency
                record.get('startingBalance'),  # starting_balance
                record.get('interestAccrued'),  # interest_accrued
                record.get('accrualReversal'),  # accrual_reversal
                record.get('fxTranslation'),  # fx_translation
                record.get('endingBalance'),  # ending_balance
                record.get('accountId'),  # account_id
                import_id  # flexquery_import_id
            )
        except Exception as e:
            logger.warning(f"Error preparing interest accrual record: {e}")
            return None
    
    def import_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Import all FlexQuery XML files from a directory"""
        results = []
        import_types = {
            'NAV_(.*?)_MTD.xml': 'NAV_MTD',
            'NAV_(.*?)_LBD.xml': 'NAV_LBD',
            'Trades_(.*?)_MTD.xml': 'TRADES_MTD',
            'Trades_(.*?)_LBD.xml': 'TRADES_LBD',
            'Open_Positions_(.*?)_LBD.xml': 'OPEN_POSITIONS_LBD',
            'Cash_Transactions_(.*?)_MTD.xml': 'CASH_TRANSACTIONS_MTD',
            'Cash_Transactions_(.*?)_LBD.xml': 'CASH_TRANSACTIONS_LBD',
            'Interest_Accruals_(.*?)_MTD.xml': 'INTEREST_ACCRUALS_MTD',
            'Interest_Accruals_(.*?)_LBD.xml': 'INTEREST_ACCRUALS_LBD',
            'Exercises_and_Expiries_(.*?)_MTD.xml': 'EXERCISES_EXPIRIES_MTD',
            'Exercises_and_Expiries_(.*?)_LBD.xml': 'EXERCISES_EXPIRIES_LBD'
        }
        
        for filename in os.listdir(directory_path):
            if filename.endswith('.xml'):
                file_path = os.path.join(directory_path, filename)
                
                # Determine import type from filename
                import_type = None
                for pattern, itype in import_types.items():
                    if re.match(pattern, filename):
                        import_type = itype
                        break
                
                if import_type:
                    logger.info(f"Importing {filename} as {import_type}")
                    result = self.import_flexquery_file(file_path, import_type)
                    result['filename'] = filename
                    results.append(result)
                else:
                    logger.warning(f"Unknown file type: {filename}")
        
        return results
