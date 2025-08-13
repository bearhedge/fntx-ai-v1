#!/usr/bin/env python3
"""
Diagnostic script for Exercise Management System
Checks all components and provides actionable feedback
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))


def check_with_status(description, check_func):
    """Run a check and print status"""
    print(f"Checking {description}... ", end='', flush=True)
    try:
        result, message = check_func()
        if result:
            print("✅")
            if message:
                print(f"  └─ {message}")
        else:
            print("❌")
            if message:
                print(f"  └─ {message}")
        return result
    except Exception as e:
        print("❌")
        print(f"  └─ Error: {e}")
        return False


def check_environment():
    """Check environment setup"""
    def _check():
        # Check Python version
        if sys.version_info < (3, 6):
            return False, f"Python {sys.version_info.major}.{sys.version_info.minor} (need 3.6+)"
            
        # Check .env file
        env_path = Path(project_root) / '.env'
        if not env_path.exists():
            return False, ".env file not found"
            
        # Check IBKR credentials
        from dotenv import load_dotenv
        load_dotenv(env_path)
        
        token = os.getenv('IBKR_FLEX_TOKEN')
        query_id = os.getenv('IBKR_FLEX_QUERY_ID')
        
        if not token or not query_id:
            return False, "IBKR credentials not set in .env"
            
        return True, "Python 3.6+ and IBKR credentials configured"
    
    return _check()


def check_database():
    """Check database connectivity and schema"""
    def _check():
        try:
            from backend.data.database.trade_db import get_trade_db_connection
            conn = get_trade_db_connection()
            if not conn:
                return False, "Cannot connect to database"
                
            with conn.cursor() as cursor:
                # Check if exercise table exists
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'portfolio' 
                    AND table_name = 'option_exercises'
                    ORDER BY ordinal_position
                """)
                
                columns = cursor.fetchall()
                if not columns:
                    return False, "Exercise table not found - run: psql -d fntx_trading -f database/portfolio/003_exercise_tracking.sql"
                    
                # Check for recent data
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN disposal_status = 'PENDING' THEN 1 END) as pending
                    FROM portfolio.option_exercises
                """)
                
                total, pending = cursor.fetchone()
                
            conn.close()
            
            msg = f"Table exists with {total} exercises"
            if pending > 0:
                msg += f" ({pending} pending disposal)"
                
            return True, msg
            
        except Exception as e:
            return False, str(e)
    
    return _check()


def check_logs():
    """Check if log directory and files exist"""
    def _check():
        log_dir = Path(project_root) / 'logs'
        if not log_dir.exists():
            log_dir.mkdir(exist_ok=True)
            return True, "Created logs directory"
            
        log_files = list(log_dir.glob('*.log'))
        if log_files:
            recent = max(log_files, key=lambda p: p.stat().st_mtime)
            return True, f"Found {len(log_files)} log files, most recent: {recent.name}"
        else:
            return True, "Log directory exists (no logs yet)"
    
    return _check()


def check_scripts():
    """Check if all required scripts exist"""
    def _check():
        required_scripts = [
            '01_backend/scripts/exercise_detector.py',
            '01_backend/scripts/exercise_disposal_asap.py',
            '01_backend/scripts/daily_flex_import.py',
            '01_backend/scripts/historical_backfill.py',
            'scripts/scheduler.py',
            'scripts/run_daily_tasks.sh',
        ]
        
        missing = []
        for script in required_scripts:
            script_path = Path(project_root) / script
            if not script_path.exists():
                missing.append(script)
                
        if missing:
            return False, f"Missing {len(missing)} scripts: {', '.join(missing[:2])}..."
        else:
            return True, f"All {len(required_scripts)} required scripts present"
    
    return _check()


def check_ib_gateway():
    """Check IB Gateway connectivity"""
    def _check():
        try:
            from ib_insync import IB
            ib = IB()
            # Try different client IDs to avoid conflicts
            for client_id in [99, 98, 97]:
                try:
                    ib.connect('127.0.0.1', 4001, clientId=client_id)
                    ib.disconnect()
                    return True, "IB Gateway accessible on port 4001"
                except:
                    continue
                    
            return False, "IB Gateway not running on port 4001 (required for order placement)"
            
        except ImportError:
            return False, "ib_insync not installed - run: pip install ib_insync"
        except Exception as e:
            return False, f"Connection failed: {str(e)[:50]}..."
    
    return _check()


def check_cron():
    """Check if cron jobs are set up"""
    def _check():
        try:
            result = subprocess.run(['crontab', '-l'], 
                                  capture_output=True, 
                                  text=True)
            
            if result.returncode != 0:
                return True, "Cron not available (use Python scheduler instead)"
                
            output = result.stdout
            if 'fntx-ai-v1' in output:
                job_count = output.count('fntx-ai-v1')
                return True, f"Found {job_count} FNTX cron jobs"
            else:
                return False, "No cron jobs set - run: ./scripts/setup_cron_jobs.sh"
                
        except FileNotFoundError:
            return True, "Cron not installed (use Python scheduler)"
        except Exception as e:
            return False, str(e)
    
    return _check()


def suggest_next_steps(results):
    """Provide actionable next steps based on diagnostic results"""
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    
    critical_issues = []
    warnings = []
    
    # Check critical issues
    if not results.get('environment', False):
        critical_issues.append("1. Fix environment setup:")
        critical_issues.append("   - Ensure Python 3.6+ is installed")
        critical_issues.append("   - Add IBKR_FLEX_TOKEN and IBKR_FLEX_QUERY_ID to .env")
        
    if not results.get('database', False):
        critical_issues.append("2. Fix database:")
        critical_issues.append("   - Ensure PostgreSQL is running")
        critical_issues.append("   - Run: psql -d fntx_trading -f database/portfolio/003_exercise_tracking.sql")
        
    if not results.get('scripts', False):
        critical_issues.append("3. Missing scripts - check your git repository")
        
    # Check warnings
    if not results.get('ib_gateway', False):
        warnings.append("- IB Gateway not running (needed for automated order placement)")
        warnings.append("  Start IB Gateway and ensure it's on port 4001")
        
    if not results.get('cron', False):
        warnings.append("- No automated scheduling set up")
        warnings.append("  Run: ./scripts/setup_cron_jobs.sh")
        warnings.append("  Or: python3 scripts/scheduler.py &")
    
    # Print results
    if critical_issues:
        print("🚨 CRITICAL ISSUES (must fix):")
        for issue in critical_issues:
            print(issue)
        print()
        
    if warnings:
        print("⚠️  WARNINGS (recommended fixes):")
        for warning in warnings:
            print(warning)
        print()
        
    if not critical_issues:
        print("✅ System is ready for exercise detection!")
        print("\nTo test now:")
        print("  python3 scripts/check_exercises.py")
        print("\nTo run daily tasks manually:")
        print("  ./scripts/run_daily_tasks.sh")
        print("\nTo monitor:")
        print("  tail -f logs/exercise_detection.log")


def main():
    """Run all diagnostics"""
    print("="*60)
    print("EXERCISE MANAGEMENT SYSTEM DIAGNOSTICS")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} HKT")
    print(f"Path: {project_root}")
    print()
    
    # Run all checks
    results = {
        'environment': check_with_status("environment", check_environment),
        'database': check_with_status("database", check_database),
        'logs': check_with_status("log directory", check_logs),
        'scripts': check_with_status("required scripts", check_scripts),
        'ib_gateway': check_with_status("IB Gateway", check_ib_gateway),
        'cron': check_with_status("scheduled tasks", check_cron),
    }
    
    # Summary
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nSummary: {passed}/{total} checks passed")
    
    # Provide next steps
    suggest_next_steps(results)


if __name__ == "__main__":
    main()