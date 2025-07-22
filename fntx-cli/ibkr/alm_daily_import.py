#!/usr/bin/env python3
"""
ALM Daily Import Service
Automated daily import of all IBKR FlexQuery reports for ALM reconciliation
"""
import os
import sys
import logging
import argparse
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import json

from flexquery_api_bridge import FlexQueryAPIBridge
from flexquery_config import flexquery_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ALMDailyImportService:
    """Service for automated daily ALM imports"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.bridge = FlexQueryAPIBridge(connection_string)
        
    def run_daily_import(self, import_date: Optional[date] = None) -> Dict[str, Any]:
        """Run the complete daily import process"""
        start_time = datetime.now()
        import_date = import_date or date.today()
        
        logger.info(f"Starting ALM daily import for {import_date}")
        logger.info("=" * 60)
        
        # Step 1: Import all LBD reports
        logger.info("\nStep 1: Importing Last Business Day (LBD) reports...")
        lbd_results = self.bridge.import_daily_reports()
        
        # Step 2: Log results
        logger.info("\n" + self.bridge.get_import_summary(lbd_results))
        
        # Step 3: Run ALM reconciliation check
        reconciliation_status = self._check_alm_reconciliation(import_date)
        
        # Step 4: Save import summary
        summary = self._save_import_summary(import_date, lbd_results, reconciliation_status)
        
        # Step 5: Send notifications if needed
        self._send_notifications(summary)
        
        # Calculate total duration
        duration = (datetime.now() - start_time).total_seconds()
        summary['total_duration_seconds'] = duration
        
        logger.info(f"\nDaily import completed in {duration:.1f} seconds")
        
        return summary
    
    def _check_alm_reconciliation(self, import_date: date) -> Dict[str, Any]:
        """Check ALM reconciliation formula after import"""
        logger.info("\nStep 2: Checking ALM reconciliation...")
        
        try:
            import psycopg2
            conn = psycopg2.connect(self.connection_string)
            
            with conn.cursor() as cursor:
                # Get the ALM reconciliation data
                cursor.execute("""
                    SELECT 
                        snapshot_date,
                        opening_nav,
                        closing_nav,
                        deposits,
                        withdrawals,
                        trading_pnl,
                        commissions_paid,
                        interest_earned,
                        fees_charged,
                        calculated_nav,
                        nav_difference,
                        difference_percentage,
                        is_reconciled
                    FROM portfolio.alm_reconciliation_view
                    WHERE snapshot_date = %s
                """, (import_date,))
                
                result = cursor.fetchone()
                
                if result:
                    reconciliation = {
                        'date': str(result[0]),
                        'opening_nav': float(result[1]),
                        'closing_nav': float(result[2]),
                        'deposits': float(result[3]),
                        'withdrawals': float(result[4]),
                        'trading_pnl': float(result[5]),
                        'commissions': float(result[6]),
                        'interest': float(result[7]),
                        'fees': float(result[8]),
                        'calculated_nav': float(result[9]),
                        'difference': float(result[10]),
                        'difference_pct': float(result[11]),
                        'is_reconciled': result[12]
                    }
                    
                    # Log reconciliation formula
                    logger.info(f"  Opening NAV: ${reconciliation['opening_nav']:,.2f}")
                    logger.info(f"  + Deposits: ${reconciliation['deposits']:,.2f}")
                    logger.info(f"  - Withdrawals: ${reconciliation['withdrawals']:,.2f}")
                    logger.info(f"  + Trading P&L: ${reconciliation['trading_pnl']:,.2f}")
                    logger.info(f"  - Commissions: ${reconciliation['commissions']:,.2f}")
                    logger.info(f"  - Fees: ${reconciliation['fees']:,.2f}")
                    logger.info(f"  + Interest: ${reconciliation['interest']:,.2f}")
                    logger.info(f"  = Calculated NAV: ${reconciliation['calculated_nav']:,.2f}")
                    logger.info(f"  Actual Closing NAV: ${reconciliation['closing_nav']:,.2f}")
                    logger.info(f"  Difference: ${reconciliation['difference']:,.2f} ({reconciliation['difference_pct']:.2f}%)")
                    
                    if reconciliation['is_reconciled']:
                        logger.info("  ✓ RECONCILED")
                    else:
                        logger.warning("  ✗ NOT RECONCILED - Difference exceeds threshold")
                    
                    return reconciliation
                else:
                    logger.warning("  No reconciliation data found for date")
                    return {'status': 'NO_DATA', 'date': str(import_date)}
                    
        except Exception as e:
            logger.error(f"Failed to check reconciliation: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _save_import_summary(self, import_date: date, lbd_results: Dict[str, Any], 
                           reconciliation: Dict[str, Any]) -> Dict[str, Any]:
        """Save import summary to database"""
        try:
            import psycopg2
            conn = psycopg2.connect(self.connection_string)
            
            summary = {
                'import_date': str(import_date),
                'import_time': datetime.now().isoformat(),
                'lbd_results': lbd_results,
                'reconciliation': reconciliation,
                'status': 'SUCCESS' if lbd_results.get('successful_imports', 0) > 0 else 'FAILED'
            }
            
            with conn.cursor() as cursor:
                # Save to import log
                cursor.execute("""
                    INSERT INTO portfolio.import_logs (
                        import_date,
                        import_type,
                        status,
                        queries_attempted,
                        queries_successful,
                        records_imported,
                        errors,
                        reconciliation_status,
                        summary_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    import_date,
                    'DAILY_LBD',
                    summary['status'],
                    lbd_results.get('total_queries', 0),
                    lbd_results.get('successful_imports', 0),
                    sum(imp.get('results', {}).get('records_processed', 0) 
                        for imp in lbd_results.get('imports', [])
                        if imp.get('status') == 'COMPLETED'),
                    json.dumps(lbd_results.get('errors', [])),
                    reconciliation.get('is_reconciled', False) if 'is_reconciled' in reconciliation else None,
                    json.dumps(summary)
                ))
                
                conn.commit()
                logger.info("\nStep 3: Import summary saved to database")
                
            return summary
            
        except Exception as e:
            logger.error(f"Failed to save import summary: {e}")
            return {
                'import_date': str(import_date),
                'status': 'ERROR',
                'error': str(e)
            }
    
    def _send_notifications(self, summary: Dict[str, Any]):
        """Send notifications about import status"""
        status = summary.get('status', 'UNKNOWN')
        reconciliation = summary.get('reconciliation', {})
        
        if status == 'FAILED':
            logger.error("\n⚠️  IMPORT FAILED - Manual intervention required")
            # TODO: Send email/webhook notification
        elif reconciliation.get('is_reconciled') == False:
            logger.warning("\n⚠️  RECONCILIATION FAILED - Review required")
            # TODO: Send email/webhook notification
        else:
            logger.info("\n✓ Daily import completed successfully")
    
    def run_monthly_reconciliation(self) -> Dict[str, Any]:
        """Run monthly reconciliation import"""
        logger.info("Starting ALM monthly reconciliation import")
        logger.info("=" * 60)
        
        # Import all MTD reports
        mtd_results = self.bridge.import_monthly_reports()
        
        logger.info("\n" + self.bridge.get_import_summary(mtd_results))
        
        # TODO: Add monthly-specific reconciliation logic
        
        return mtd_results
    
    def cleanup(self):
        """Clean up resources"""
        self.bridge.cleanup()


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(description='ALM Daily Import Service')
    parser.add_argument('--date', type=str, help='Import date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--monthly', action='store_true', help='Run monthly reconciliation instead')
    parser.add_argument('--db-url', type=str, help='Database connection URL',
                       default=os.getenv('DATABASE_URL'))
    
    args = parser.parse_args()
    
    if not args.db_url:
        logger.error("Database URL not provided. Set DATABASE_URL environment variable or use --db-url")
        sys.exit(1)
    
    # Create service
    service = ALMDailyImportService(args.db_url)
    
    try:
        if args.monthly:
            # Run monthly reconciliation
            results = service.run_monthly_reconciliation()
        else:
            # Run daily import
            import_date = None
            if args.date:
                import_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            
            results = service.run_daily_import(import_date)
        
        # Exit with appropriate code
        if results.get('status') == 'FAILED':
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
    finally:
        service.cleanup()


if __name__ == "__main__":
    main()