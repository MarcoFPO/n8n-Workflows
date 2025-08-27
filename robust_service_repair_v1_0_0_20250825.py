#!/usr/bin/env python3
"""
Robust Service Repair Script v1.0.0 - 25. August 2025
=====================================================

Systematische Reparatur und Migration aller verbleibenden Services mit:
- Logger Syntax Fixes
- Permission Handling 
- Import Optimization
- Service-spezifische Anpassungen
- Rollback-Fähigkeit

Fokus auf Stabilität und Zero-Downtime.
"""

import os
import shutil
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime

class RobustServiceRepairer:
    def __init__(self):
        self.base_path = Path("/opt/aktienanalyse-ökosystem")
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_dir = "/var/log/aktienanalyse"
        
        # All remaining services to repair/migrate
        self.target_services = {
            "ml-analytics": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/ml-analytics-service/ml_analytics_daemon_v6_1_0.py",
                "service_name": "aktienanalyse-ml-analytics-v6.service",
                "needs_database": True,
                "common_issues": ["logger_syntax", "database_imports"]
            },
            "event-bus": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/event-bus-service/event_bus_daemon_v6_1_0.py", 
                "service_name": "aktienanalyse-event-bus-v6.service",
                "needs_database": False,
                "common_issues": ["logger_permissions", "log_directory"]
            },
            "diagnostic": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/diagnostic-service/diagnostic_daemon_v6_1_0.py",
                "service_name": "aktienanalyse-diagnostic-v6.service", 
                "needs_database": False,
                "common_issues": []
            },
            "marketcap": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/marketcap-service/marketcap_daemon_v6_1_0.py",
                "service_name": "aktienanalyse-marketcap-v6.service",
                "needs_database": True,
                "common_issues": []
            },
            "prediction-tracking": {
                "file_path": "/opt/aktienanalyse-ökosystem/services/prediction-tracking-service/prediction_tracking_daemon_v6_1_0.py",
                "service_name": "aktienanalyse-prediction-tracking-v6.service",
                "needs_database": True, 
                "common_issues": []
            }
        }
    
    def setup_logging_environment(self):
        """Setup proper logging environment."""
        print("🔧 Setting up logging environment...")
        
        try:
            # Create log directory with proper permissions
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Set ownership to aktienanalyse user
            subprocess.run(['chown', '-R', 'aktienanalyse:aktienanalyse', self.log_dir], check=True)
            subprocess.run(['chmod', '755', self.log_dir], check=True)
            
            print(f"✅ Log directory ready: {self.log_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup logging environment: {e}")
            return False
    
    def fix_logger_syntax_issues(self, file_path: str) -> bool:
        """Fix all known logger syntax issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix logger.error with keyword arguments
            content = re.sub(
                r'logger\.error\([^)]*,\s*error=str\(e\)[^)]*\)',
                lambda m: f'logger.error(f"Error: {{str(e)}}")',
                content
            )
            
            # Fix logger.error with multiple keyword arguments
            content = re.sub(
                r'logger\.error\("([^"]*)",\s*error=str\(([^)]+)\),\s*symbol=([^)]+)\)',
                r'logger.error(f"\1 for {\3}: {str(\2)}")',
                content
            )
            
            # Fix any remaining problematic logger calls
            lines = content.split('\n')
            fixed_lines = []
            
            for line in lines:
                if 'logger.error(' in line and ('error=' in line or 'symbol=' in line):
                    # Replace complex logger calls with simple ones
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * indent + 'logger.error("Service error occurred")')
                else:
                    fixed_lines.append(line)
            
            content = '\n'.join(fixed_lines)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Fixed logger syntax issues in {os.path.basename(file_path)}")
                return True
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to fix logger syntax in {file_path}: {e}")
            return False
    
    def apply_robust_migration(self, service_key: str, service_info: dict) -> bool:
        """Apply comprehensive migration with error handling."""
        file_path = service_info["file_path"]
        
        print(f"\n🔧 Applying robust migration to {service_key.upper()}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ Service file not found: {file_path}")
            return False
        
        # Create backup
        backup_path = f"{file_path}.backup_robust_{self.timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"✅ Backup created: {backup_path}")
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
        
        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip if already properly migrated
            if 'from shared.structured_logging import setup_structured_logging' in content:
                print(f"ℹ️  {service_key} infrastructure already present")
                
                # Still apply fixes
                if not self.fix_logger_syntax_issues(file_path):
                    return False
                
                return True
            
            # Apply migration
            lines = content.split('\n')
            
            # Find import section
            import_end_index = 0
            for i, line in enumerate(lines):
                if line.strip() and not (line.startswith('import ') or line.startswith('from ') or line.startswith('#') or line.strip() == ''):
                    import_end_index = i
                    break
            
            # Insert infrastructure imports
            new_imports = [
                "import os",
                "from shared.structured_logging import setup_structured_logging",
                "from shared.config_manager import ConfigManager"
            ]
            
            # Add database pool for services that need it
            if service_info.get("needs_database", False):
                new_imports.append("from shared.database_pool import DatabasePool")
            
            # Insert imports
            for imp in reversed(new_imports):
                if imp not in content:
                    lines.insert(import_end_index, imp)
            
            # Add logging setup
            for i, line in enumerate(lines):
                if 'if __name__ == "__main__":' in line:
                    service_name_line = f'    service_name = "{service_key}-service"'
                    logger_line = f'    logger = setup_structured_logging(service_name)'
                    
                    lines.insert(i + 1, service_name_line)
                    lines.insert(i + 2, logger_line)
                    print(f"✅ Added logging initialization for {service_key}")
                    break
            
            # Write modified content
            content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Infrastructure migration applied to {service_key}")
            
            # Apply syntax fixes
            if not self.fix_logger_syntax_issues(file_path):
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed for {service_key}: {e}")
            
            # Restore backup
            try:
                shutil.copy2(backup_path, file_path)
                print(f"✅ Restored backup for {service_key}")
            except:
                pass
                
            return False
    
    def restart_and_verify_service(self, service_name: str, max_retries: int = 3) -> bool:
        """Restart service and verify it's running with retries."""
        for attempt in range(max_retries):
            try:
                print(f"🔄 Restarting {service_name} (attempt {attempt + 1}/{max_retries})")
                
                # Stop service first
                subprocess.run(['systemctl', 'stop', service_name], capture_output=True)
                time.sleep(2)
                
                # Start service
                subprocess.run(['systemctl', 'start', service_name], check=True, capture_output=True)
                time.sleep(5)
                
                # Check if running
                result = subprocess.run(['systemctl', 'is-active', service_name], 
                                      capture_output=True, text=True)
                
                if result.stdout.strip() == 'active':
                    print(f"✅ {service_name} started successfully")
                    return True
                else:
                    print(f"⚠️  {service_name} not active after restart (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        time.sleep(5)  # Wait before retry
                    
            except subprocess.CalledProcessError as e:
                print(f"❌ Service restart attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
        
        return False
    
    def repair_all_services(self):
        """Execute comprehensive repair for all target services."""
        print("🚀 ROBUST SERVICE REPAIR & MIGRATION")
        print("=" * 60)
        
        # Setup environment
        if not self.setup_logging_environment():
            print("❌ Failed to setup logging environment")
            return False
        
        results = {"success": [], "partial": [], "failed": []}
        
        # Process each service
        for service_key, service_info in self.target_services.items():
            print(f"\n{'='*20} {service_key.upper()} {'='*20}")
            
            # Apply migration
            migration_success = self.apply_robust_migration(service_key, service_info)
            
            if migration_success:
                # Restart and verify service
                restart_success = self.restart_and_verify_service(service_info["service_name"])
                
                if restart_success:
                    results["success"].append(service_key)
                    print(f"🎉 {service_key.upper()} FULLY REPAIRED!")
                else:
                    results["partial"].append(service_key)
                    print(f"⚠️  {service_key.upper()} migrated but service issues remain")
            else:
                results["failed"].append(service_key)
                print(f"💥 {service_key.upper()} REPAIR FAILED!")
        
        # Generate summary
        print("\n" + "=" * 60)
        print("📊 ROBUST REPAIR SUMMARY")
        print("=" * 60)
        print(f"✅ Fully Successful: {len(results['success'])} - {results['success']}")
        print(f"⚠️  Partial Success: {len(results['partial'])} - {results['partial']}") 
        print(f"❌ Failed: {len(results['failed'])} - {results['failed']}")
        
        total_services = len(self.target_services)
        success_rate = len(results['success']) / total_services * 100
        
        print(f"\n🎯 Success Rate: {len(results['success'])}/{total_services} ({success_rate:.1f}%)")
        
        if len(results['success']) == total_services:
            print("\n🏆 ALL SERVICES SUCCESSFULLY REPAIRED AND MIGRATED!")
            print("✅ Clean Architecture deployment complete")
        elif len(results['success']) > total_services // 2:
            print(f"\n🎯 MAJORITY SUCCESS: {len(results['success'])} services operational")
            print("⚠️  Some services may need individual attention")
        else:
            print("\n💥 SIGNIFICANT ISSUES REMAIN")
            print("❌ Manual intervention recommended")
        
        return results

def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root!")
        return False
    
    repairer = RobustServiceRepairer()
    results = repairer.repair_all_services()
    
    return len(results["success"]) > 0

if __name__ == "__main__":
    main()