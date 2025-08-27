#!/usr/bin/env python3
"""
Database Connection Pool Migration Script
Updates alle Services um den zentralisierten Database Pool zu verwenden
"""

import os
import shutil
from pathlib import Path

def update_service_files():
    """Updates all service files to use centralized database pool"""
    
    services_to_update = [
        "/opt/aktienanalyse-ökosystem/services/ml-pipeline-service/ml_pipeline_service_v6_0_0_20250824.py",
        "/opt/aktienanalyse-ökosystem/services/portfolio-management-service/portfolio_management_service_v6_0_0_20250824.py", 
        "/opt/aktienanalyse-ökosystem/services/market-data-service/market_data_service_v6_0_0_20250824.py",
        "/opt/aktienanalyse-ökosystem/services/intelligent-core-service/intelligent_core_service_v6_0_0_20250824.py",
        "/opt/aktienanalyse-ökosystem/services/frontend-service/run_frontend_multihorizon.py",
        "/opt/aktienanalyse-ökosystem/services/broker-gateway-service/src/main.py"
    ]
    
    # Standard-Ersetzungen für alle Services
    replacements = [
        # Import hinzufügen
        ("import asyncpg", """import asyncpg
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')
from shared.database_pool import db_pool, init_db_pool, get_db_connection"""),
        
        # Pool-Initialization ersetzen
        ("self.connection_pool = await asyncpg.create_pool(", "await init_db_pool()  # Old: self.connection_pool = await asyncpg.create_pool("),
        ("self.db_pool = await asyncpg.create_pool(", "await init_db_pool()  # Old: self.db_pool = await asyncpg.create_pool("),
        
        # Pool-Attribute entfernen
        ("self.connection_pool: Optional[asyncpg.Pool] = None", "# Database pool is now centralized via shared.database_pool"),
        ("self.db_pool = None", "# Database pool is now centralized via shared.database_pool"),
        ("self.db_pool: Optional[asyncpg.Pool] = None", "# Database pool is now centralized via shared.database_pool"),
        
        # Pool-Usage ersetzen
        ("async with self.connection_pool.acquire() as conn:", "async with get_db_connection() as conn:"),
        ("async with self.db_pool.acquire() as conn:", "async with get_db_connection() as conn:"),
        
        # Cleanup ersetzen
        ("await self.connection_pool.close()", "# Database pool cleanup is handled centrally"),
        ("await self.db_pool.close()", "# Database pool cleanup is handled centrally"),
        
        # Direct connect calls ersetzen  
        ("conn = await asyncpg.connect(", "async with get_db_connection() as conn:  # Old: conn = await asyncpg.connect(")
    ]
    
    print("Database Connection Pool Migration")
    print("=" * 50)
    
    for service_file in services_to_update:
        if os.path.exists(service_file):
            print(f"\nUpdating: {service_file}")
            
            # Read file
            with open(service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply replacements
            original_content = content
            for old, new in replacements:
                if old in content:
                    content = content.replace(old, new)
                    print(f"  ✅ Replaced: {old[:50]}...")
            
            # Write updated file
            if content != original_content:
                with open(service_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  💾 File updated successfully")
            else:
                print(f"  ℹ️  No changes needed")
        else:
            print(f"\n❌ File not found: {service_file}")

if __name__ == "__main__":
    update_service_files()
    print("\n🎯 Database Connection Pool Migration completed!")
    print("\nNext steps:")
    print("1. Copy shared/database_pool.py to /opt/aktienanalyse-ökosystem/shared/")
    print("2. Restart all services to use the new centralized pool")
    print("3. Verify all services connect successfully")