#!/usr/bin/env python3
"""
Clean up and organize the backend/core folder
Groups files by category and moves to appropriate locations
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def organize_files():
    """Organize files in backend/core"""
    
    core_dir = Path("/home/info/fntx-ai-v1/backend/core")
    
    # Create archive directories
    archive_dir = core_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    (archive_dir / "oauth_tests").mkdir(exist_ok=True)
    (archive_dir / "old_trade_scripts").mkdir(exist_ok=True)
    (archive_dir / "debug_scripts").mkdir(exist_ok=True)
    
    # Define file categories
    categories = {
        "oauth_tests": [
            "test_bearhedge_*.py",
            "test_oauth_*.py",
            "test_rsa_*.py", 
            "test_hmac_*.py",
            "test_signature_*.py",
            "test_header*.py",
            "test_base_string.py",
            "test_direct_request.py",
            "test_demo_comparison.py",
            "test_full_oauth_flow.py",
            "test_ib_rest_auth.py",
            "test_fix_now.py",
            "oauth_diagnostic.py",
            "compare_implementations.py",
            "compare_rsa_hmac.py"
        ],
        "old_trade_scripts": [
            "execute_spy_trades_ib_insync_backup.py",
            "execute_spy_trades_ibapi.py",
            "execute_spy_trades_ibapi_simple.py",
            "execute_spy_trades_rest.py",
            "close_spy_trades.py",
            "force_cleanup.py",
            "simple_connect_test.py",
            "diag_connect.py"
        ],
        "debug_scripts": [
            "debug_*.py",
            "regenerate_lst.py",
            "check_api_status.py"
        ]
    }
    
    # Files to KEEP in core
    keep_files = [
        "execute_spy_trades.py",  # Main trading script
        "ib_rest_auth_fixed.py",  # Fixed OAuth implementation
        "__init__.py",
        "IB_REST_API_IMPLEMENTATION_STATUS.md"
    ]
    
    # Move files to archive
    moves = []
    
    for category, patterns in categories.items():
        target_dir = archive_dir / category
        for pattern in patterns:
            if "*" in pattern:
                # Handle wildcards
                for file in core_dir.glob(pattern):
                    if file.name not in keep_files and file.is_file():
                        target = target_dir / file.name
                        moves.append((file, target, category))
            else:
                # Handle specific files
                file = core_dir / pattern
                if file.exists() and file.name not in keep_files:
                    target = target_dir / file.name
                    moves.append((file, target, category))
    
    return moves

def preview_changes():
    """Preview what will be moved"""
    moves = organize_files()
    
    print("="*60)
    print("PREVIEW: Files to be archived")
    print("="*60)
    
    by_category = {}
    for source, target, category in moves:
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(source.name)
    
    for category, files in by_category.items():
        print(f"\n{category.upper()} ({len(files)} files):")
        print("-"*40)
        for file in sorted(files)[:10]:  # Show first 10
            print(f"  • {file}")
        if len(files) > 10:
            print(f"  ... and {len(files)-10} more")
    
    print("\n" + "="*60)
    print("FILES TO KEEP IN CORE:")
    print("-"*40)
    
    core_dir = Path("/home/info/fntx-ai-v1/backend/core")
    keep_files = [
        "execute_spy_trades.py",
        "ib_rest_auth_fixed.py", 
        "__init__.py",
        "IB_REST_API_IMPLEMENTATION_STATUS.md"
    ]
    
    for file in keep_files:
        if (core_dir / file).exists():
            print(f"  ✓ {file}")
    
    # Check auth folder
    auth_dir = core_dir / "auth"
    if auth_dir.exists():
        print(f"\n  📁 auth/ (keeping authentication modules)")
    
    # Check trading folder
    trading_dir = core_dir / "trading"
    if trading_dir.exists():
        print(f"  📁 trading/ (keeping trading modules)")
    
    print("\n" + "="*60)
    print(f"Total files to archive: {len(moves)}")
    print("="*60)
    
    return moves

def execute_cleanup(dry_run=True):
    """Execute the cleanup"""
    moves = organize_files()
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be moved")
        preview_changes()
        return
    
    print("\n⚠️  EXECUTING CLEANUP...")
    
    # Log movements
    log_file = Path("/home/info/fntx-ai-v1/.claude/refactor_log.xml")
    timestamp = datetime.now().isoformat()
    
    with open(log_file, "a") as f:
        f.write(f"\n<!-- Backend Core Cleanup - {timestamp} -->\n")
    
    moved_count = 0
    for source, target, category in moves:
        try:
            print(f"Moving {source.name} → archive/{category}/")
            shutil.move(str(source), str(target))
            moved_count += 1
            
            # Log to refactor_log.xml
            with open(log_file, "a") as f:
                f.write(f'<movement timestamp="{timestamp}" '
                       f'action="archive" '
                       f'description="Archive {category} file" '
                       f'source="{source}" '
                       f'target="{target}" />\n')
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n✅ Moved {moved_count} files to archive")
    
    # Show final structure
    print("\n" + "="*60)
    print("FINAL STRUCTURE:")
    print("="*60)
    
    core_dir = Path("/home/info/fntx-ai-v1/backend/core")
    
    # Count remaining files
    remaining = list(core_dir.glob("*.py"))
    print(f"\nFiles in core: {len(remaining)}")
    for file in sorted(remaining):
        if file.is_file():
            print(f"  • {file.name}")
    
    # Show folders
    folders = [d for d in core_dir.iterdir() if d.is_dir()]
    print(f"\nFolders in core: {len(folders)}")
    for folder in sorted(folders):
        file_count = len(list(folder.glob("*")))
        print(f"  📁 {folder.name}/ ({file_count} items)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        print("🚀 EXECUTING CLEANUP...")
        execute_cleanup(dry_run=False)
    else:
        print("📋 PREVIEW MODE (use --execute to actually move files)")
        execute_cleanup(dry_run=True)
        print("\nTo execute: python cleanup_and_organize.py --execute")