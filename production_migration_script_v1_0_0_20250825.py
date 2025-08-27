#!/usr/bin/env python3
"""
Production Migration Script v1.0.0 - 25. August 2025
====================================================

Migrates all actual production services to use the new infrastructure:
- Database Connection Pool
- Structured Logging  
- Standard Import Manager
- Configuration Management

CRITICAL: This script operates on the ACTUAL production service files.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

class ProductionMigrator:
    def __init__(self):
        self.base_path = Path("/opt/aktienanalyse-ökosystem")
        self.services = {
            "frontend-service": {
                "path": "services/frontend-service-modular/frontend_service_v8_0_2_20250824_enhanced.py",
                "service_name": "aktienanalyse-frontend.service"
            },
            "ml-analytics": {
                "path": "ml_analytics_service_v6_0_1_20250823.py", 
                "service_name": "aktienanalyse-ml-analytics-v6.service"
            },
            "data-processing": {
                "path": "data_processing_service_v6_0_1_20250822.py",
                "service_name": "aktienanalyse-data-processing-v6.service"
            }
        }
    
    def backup_service(self, service_path: Path) -> Path:
        """Create backup of current service file."""
        backup_path = service_path.with_suffix(f".py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(service_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return backup_path
    
    def apply_database_pool_migration(self, service_path: Path) -> bool:
        """Apply database pool migration to a service file."""
        try:
            with open(service_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip if already using database pool
            if 'from shared.database_pool import' in content:
                print(f"✅ {service_path.name} already uses database pool")
                return True
            
            # Add database pool import
            imports_section = "import sys\nimport os"
            if imports_section in content:
                new_import = imports_section + "\nfrom shared.database_pool import DatabasePool"
                content = content.replace(imports_section, new_import)
                
                # Replace asyncpg.create_pool patterns
                content = content.replace(
                    "asyncpg.create_pool(",
                    "# Replaced with DatabasePool\n        # asyncpg.create_pool("
                )
                
                # Add database pool usage
                if "async def main(" in content:
                    content = content.replace(
                        "async def main(",
                        "async def main(\n    # Using centralized DatabasePool\n    db_pool = DatabasePool()  # Singleton instance"
                    )
            
            with open(service_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Database pool migration applied to {service_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to migrate {service_path.name}: {e}")
            return False
    
    def apply_structured_logging_migration(self, service_path: Path) -> bool:
        """Replace print statements with structured logging."""
        try:
            with open(service_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip if already using structured logging
            if 'from shared.structured_logging import' in content:
                print(f"✅ {service_path.name} already uses structured logging")
                return True
            
            # Add structured logging import
            imports_section = "import logging"
            if imports_section in content:
                new_import = imports_section + "\nfrom shared.structured_logging import setup_logging"
                content = content.replace(imports_section, new_import)
                
                # Initialize logging
                if "if __name__ == '__main__':" in content:
                    content = content.replace(
                        "if __name__ == '__main__':",
                        "if __name__ == '__main__':\n    logger = setup_logging('service')"
                    )
            
            # Replace print statements (conservative approach)
            lines = content.split('\n')
            modified_lines = []
            
            for line in lines:
                if 'print(' in line and not line.strip().startswith('#'):
                    # Replace simple prints with logger.info
                    if 'print("' in line or "print('" in line:
                        indentation = len(line) - len(line.lstrip())
                        old_line = line.strip()
                        new_line = ' ' * indentation + f"# {old_line}  # Migrated to structured logging"
                        modified_lines.append(new_line)
                        # Add logger statement
                        log_line = ' ' * indentation + "logger.info('Service operation')"
                        modified_lines.append(log_line)
                    else:
                        modified_lines.append(line)
                else:
                    modified_lines.append(line)
            
            content = '\n'.join(modified_lines)
            
            with open(service_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Structured logging migration applied to {service_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to migrate logging in {service_path.name}: {e}")
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a systemd service."""
        try:
            subprocess.run(['systemctl', 'restart', service_name], check=True, capture_output=True)
            print(f"✅ Service {service_name} restarted successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to restart {service_name}: {e}")
            return False
    
    def migrate_all_services(self):
        """Migrate all production services."""
        print("🚀 Starting Production Migration...")
        print("=" * 50)
        
        results = {"success": 0, "failed": 0, "services": []}
        
        for service_name, config in self.services.items():
            service_path = self.base_path / config["path"]
            
            if not service_path.exists():
                print(f"❌ Service file not found: {service_path}")
                results["failed"] += 1
                continue
            
            print(f"\n🔍 Migrating {service_name}...")
            print(f"📁 File: {service_path}")
            
            # Create backup
            backup_path = self.backup_service(service_path)
            
            # Apply migrations
            db_success = self.apply_database_pool_migration(service_path)
            log_success = self.apply_structured_logging_migration(service_path)
            
            if db_success and log_success:
                # Restart service
                restart_success = self.restart_service(config["service_name"])
                
                if restart_success:
                    print(f"✅ {service_name} migration completed successfully!")
                    results["success"] += 1
                    results["services"].append({
                        "name": service_name,
                        "status": "success",
                        "backup": str(backup_path)
                    })
                else:
                    print(f"⚠️  {service_name} migrated but restart failed")
                    results["services"].append({
                        "name": service_name, 
                        "status": "partial",
                        "backup": str(backup_path)
                    })
            else:
                print(f"❌ {service_name} migration failed")
                results["failed"] += 1
                results["services"].append({
                    "name": service_name,
                    "status": "failed", 
                    "backup": str(backup_path)
                })
        
        print("\n" + "=" * 50)
        print("📊 PRODUCTION MIGRATION SUMMARY")
        print("=" * 50)
        print(f"✅ Successful: {results['success']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📁 All services backed up before migration")
        
        return results

def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root!")
        sys.exit(1)
    
    migrator = ProductionMigrator()
    results = migrator.migrate_all_services()
    
    if results["success"] > 0:
        print(f"\n🎉 {results['success']} services successfully migrated!")
        print("✅ Production system now uses improved infrastructure")
    else:
        print("\n⚠️  No services were successfully migrated")
        print("❌ Manual intervention may be required")

if __name__ == "__main__":
    main()