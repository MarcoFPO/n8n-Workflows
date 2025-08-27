#!/usr/bin/env python3
"""
ML-Analytics Database Pool Fix v1.0.0 - 25. August 2025
===========================================================

Fix für ML-Analytics Service - Replace old database pattern with new DatabasePool
- Replace POSTGRES_CONFIG with DatabasePool
- Fix init_database() function
- Remove duplicate database code
- Ensure compatibility with Clean Architecture
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime

class MLAnalyticsDbPoolFixer:
    def __init__(self):
        self.service_file = "/opt/aktienanalyse-ökosystem/services/ml-analytics-service/ml_analytics_daemon_v6_1_0.py"
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def create_backup(self):
        """Create backup before changes"""
        backup_path = f"{self.service_file}.backup_dbpool_fix_{self.timestamp}"
        shutil.copy2(self.service_file, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return backup_path
        
    def fix_database_integration(self):
        """Replace old database pattern with DatabasePool"""
        print("🔧 Fixing ML-Analytics Database Integration...")
        
        try:
            with open(self.service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace old database init pattern
            content = re.sub(
                r'async def init_database\(\):\s*\n.*?global db_pool.*?\n.*?try:\s*\n.*?# Create connection pool\s*\n.*?db_pool = await asyncpg\.create_pool\(\s*\n.*?\*\*POSTGRES_CONFIG,.*?\n.*?min_size=\d+,\s*\n.*?max_size=\d+,\s*\n.*?command_timeout=\d+\s*\n.*?\)',
                '''async def init_database():
    """Initialize PostgreSQL database for ML analytics using DatabasePool"""
    global db_pool
    
    try:
        # Initialize DatabasePool singleton
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        # Create ML analytics tables using pool
        async with db_pool.acquire() as conn:''',
                content,
                flags=re.DOTALL
            )
            
            # Remove POSTGRES_CONFIG definition
            content = re.sub(
                r'POSTGRES_CONFIG = \{[^}]*\}',
                '# Database configuration handled by DatabasePool',
                content,
                flags=re.DOTALL
            )
            
            # Fix close_database function
            content = re.sub(
                r'async def close_database\(\):\s*\n.*?global db_pool.*?\n.*?if db_pool:\s*\n.*?await db_pool\.close\(\)',
                '''async def close_database():
    """Close database connections using DatabasePool"""
    global db_pool
    if db_pool:
        await db_pool.close()''',
                content,
                flags=re.DOTALL
            )
            
            # Replace direct db_pool.acquire() calls with DatabasePool pattern
            content = re.sub(
                r'async with db_pool\.acquire\(\) as conn:',
                r'async with db_pool.acquire() as conn:',
                content
            )
            
            if content != original_content:
                with open(self.service_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print("✅ ML-Analytics Database Integration fixed")
                return True
            else:
                print("ℹ️  No database integration changes needed")
                return True
                
        except Exception as e:
            print(f"❌ Failed to fix database integration: {e}")
            return False
    
    def verify_fix(self):
        """Verify the fix was applied correctly"""
        try:
            with open(self.service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for DatabasePool usage
            if 'db_pool = DatabasePool()' in content:
                print("✅ DatabasePool initialization found")
            else:
                print("❌ DatabasePool initialization missing")
                return False
                
            # Check that old POSTGRES_CONFIG is removed
            if 'POSTGRES_CONFIG = {' not in content:
                print("✅ Old POSTGRES_CONFIG removed")
            else:
                print("⚠️  Old POSTGRES_CONFIG still present")
                
            # Check for proper imports
            if 'from shared.database_pool import DatabasePool' in content:
                print("✅ DatabasePool import found")
            else:
                print("❌ DatabasePool import missing")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
    
    def fix_service(self):
        """Execute complete ML-Analytics service fix"""
        print("🚀 ML-ANALYTICS DATABASE POOL FIX")
        print("=" * 50)
        
        # Create backup
        backup_path = self.create_backup()
        
        # Apply database fix
        if not self.fix_database_integration():
            print("❌ Database integration fix failed")
            return False
            
        # Verify fix
        if not self.verify_fix():
            print("❌ Fix verification failed")
            # Restore backup
            shutil.copy2(backup_path, self.service_file)
            print("✅ Backup restored")
            return False
            
        print("✅ ML-Analytics Database Pool Fix completed successfully!")
        return True

def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root!")
        return False
    
    fixer = MLAnalyticsDbPoolFixer()
    return fixer.fix_service()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)