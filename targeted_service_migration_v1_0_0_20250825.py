#!/usr/bin/env python3
"""
Targeted Service Migration Script v1.0.0 - 25. August 2025
==========================================================

Direkte Migration der identifizierten Service-Dateien zur neuen Clean Architecture.
Fokus auf die 3 wichtigsten Services für maximale Erfolgsrate.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

class TargetedMigrator:
    def __init__(self):
        self.base_path = Path("/opt/aktienanalyse-ökosystem")
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Verified service files with their exact paths
        self.target_services = {
            "ml-analytics": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/ml-analytics-service/ml_analytics_daemon_v6_1_0.py",
                "service_name": "aktienanalyse-ml-analytics-v6.service"
            },
            "data-processing": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/data-processing-service/data_processing_daemon_v6_1_0.py", 
                "service_name": "aktienanalyse-data-processing-v6.service"
            },
            "event-bus": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/event-bus-service/event_bus_daemon_v6_1_0.py",
                "service_name": "aktienanalyse-event-bus-v6.service"
            }
        }
        
    def migrate_single_service(self, service_key: str, service_info: dict) -> bool:
        """Migrate a single service with detailed logging."""
        file_path = service_info["file_path"]
        service_name = service_info["service_name"]
        
        print(f"\n🔧 Migrating {service_key.upper()} SERVICE")
        print(f"📁 File: {file_path}")
        print(f"🔧 Service: {service_name}")
        
        # 1. Verify file exists
        if not os.path.exists(file_path):
            print(f"❌ Service file not found: {file_path}")
            return False
        
        # 2. Create backup
        backup_path = f"{file_path}.backup_{self.timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"✅ Backup created: {backup_path}")
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
        
        # 3. Apply migration
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Check if already migrated
            if 'from shared.structured_logging import' in content:
                print(f"ℹ️  {service_key} already uses new infrastructure")
                return True
            
            # Add imports at the top
            lines = content.split('\n')
            import_index = -1
            
            # Find the right place to insert imports
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i
                elif import_index != -1 and not (line.startswith('import ') or line.startswith('from ') or line.strip() == ''):
                    break
            
            # Insert new imports
            if import_index != -1:
                insert_index = import_index + 1
                new_imports = [
                    "import os",
                    "from shared.structured_logging import setup_structured_logging",
                    "from shared.config_manager import ConfigManager"
                ]
                
                # Add database pool for ML and data processing services
                if service_key in ['ml-analytics', 'data-processing']:
                    new_imports.append("from shared.database_pool import DatabasePool")
                
                for imp in reversed(new_imports):
                    if imp not in content:
                        lines.insert(insert_index, imp)
                        print(f"✅ Added import: {imp}")
            
            # Add logging initialization
            main_pattern = 'if __name__ == "__main__":'
            for i, line in enumerate(lines):
                if main_pattern in line:
                    # Insert logging setup after the if statement
                    service_var = f'service_name = "{service_key}-service"'
                    logger_setup = f'logger = setup_structured_logging(service_name)'
                    
                    lines.insert(i + 1, f"    {service_var}")
                    lines.insert(i + 2, f"    {logger_setup}")
                    print(f"✅ Added logging initialization")
                    break
            
            # Replace print statements (conservative approach)
            print_count = 0
            for i, line in enumerate(lines):
                if 'print(' in line and not line.strip().startswith('#'):
                    indent = len(line) - len(line.lstrip())
                    lines[i] = ' ' * indent + f"# {line.strip()}  # Migrated to structured logging"
                    lines.insert(i + 1, ' ' * indent + "logger.info('Service operation')")
                    print_count += 1
            
            if print_count > 0:
                print(f"✅ Replaced {print_count} print statements")
            
            # Write modified content
            modified_content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            print(f"✅ Infrastructure migration completed for {service_key}")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
        
        # 4. Restart service
        try:
            print(f"🔄 Restarting {service_name}...")
            subprocess.run(['systemctl', 'restart', service_name], check=True, capture_output=True)
            time.sleep(3)
            
            # Check if service is running
            result = subprocess.run(['systemctl', 'is-active', service_name], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip() == 'active':
                print(f"✅ {service_name} restarted successfully")
                return True
            else:
                print(f"⚠️  {service_name} not active after restart")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Service restart failed: {e}")
            return False
    
    def migrate_all_targeted_services(self):
        """Execute migration for all targeted services."""
        print("🚀 TARGETED SERVICE MIGRATION")
        print("=" * 50)
        print(f"📊 Target services: {len(self.target_services)}")
        
        results = {"success": 0, "failed": 0, "services": []}
        
        for service_key, service_info in self.target_services.items():
            success = self.migrate_single_service(service_key, service_info)
            
            if success:
                results["success"] += 1
                results["services"].append({"name": service_key, "status": "success"})
                print(f"🎉 {service_key.upper()} MIGRATION SUCCESSFUL!")
            else:
                results["failed"] += 1
                results["services"].append({"name": service_key, "status": "failed"})
                print(f"💥 {service_key.upper()} MIGRATION FAILED!")
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TARGETED MIGRATION SUMMARY")
        print("=" * 50)
        print(f"✅ Successful: {results['success']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"🎯 Success Rate: {results['success']}/{len(self.target_services)} ({results['success']/len(self.target_services)*100:.1f}%)")
        
        if results["success"] == len(self.target_services):
            print("\n🏆 ALL TARGETED SERVICES SUCCESSFULLY MIGRATED!")
            print("✅ Clean Architecture deployment completed for core services")
        elif results["success"] > 0:
            print(f"\n🎯 PARTIAL SUCCESS: {results['success']} services migrated")
            print("⚠️  Remaining services may need manual intervention")
        else:
            print("\n💥 NO SERVICES SUCCESSFULLY MIGRATED")
            print("❌ Manual investigation required")
        
        return results

def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root!")
        exit(1)
    
    migrator = TargetedMigrator()
    results = migrator.migrate_all_targeted_services()
    
    return results["success"] > 0

if __name__ == "__main__":
    main()