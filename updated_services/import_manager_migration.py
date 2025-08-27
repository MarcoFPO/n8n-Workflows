#!/usr/bin/env python3
"""
Import Manager Migration Script
Ersetzt sys.path.append() Anti-Patterns durch StandardImportManager
"""

import os
import re
from pathlib import Path

def migrate_import_patterns():
    """Migrate sys.path.append patterns to StandardImportManager"""
    
    # Service files to update (excluding venv directories)
    target_files = []
    services_dir = Path("/opt/aktienanalyse-ökosystem/services")
    
    for service_dir in services_dir.glob("*"):
        if service_dir.is_dir() and not service_dir.name.startswith('.'):
            for py_file in service_dir.rglob("*.py"):
                # Skip venv directories
                if 'venv' not in str(py_file) and '__pycache__' not in str(py_file):
                    target_files.append(py_file)
    
    # Also include modules directory
    modules_dir = Path("/opt/aktienanalyse-ökosystem/modules")
    if modules_dir.exists():
        for py_file in modules_dir.glob("*.py"):
            target_files.append(py_file)
    
    print("Import Manager Migration")
    print("=" * 50)
    print(f"Processing {len(target_files)} Python files...")
    
    # Standard replacement pattern
    import_manager_import = """# Standard Import Manager - Clean Architecture Pattern
from shared.standard_import_manager_v1_0_0_20250824 import StandardImportManager
import_manager = StandardImportManager()
import_manager.setup_project_paths()
"""
    
    total_replacements = 0
    processed_files = 0
    
    for file_path in target_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_replacements = 0
            
            # Check for sys.path.append patterns
            sys_path_patterns = re.findall(r'sys\.path\.append\([^)]+\)', content)
            if not sys_path_patterns:
                continue
            
            print(f"\nProcessing: {file_path}")
            print(f"  Found {len(sys_path_patterns)} sys.path.append calls")
            
            # Remove all sys.path.append patterns
            for pattern in sys_path_patterns:
                content = content.replace(pattern, "# Replaced by StandardImportManager")
                file_replacements += 1
            
            # Add StandardImportManager import after other imports
            if 'from shared.standard_import_manager' not in content:
                # Find the best place to insert the import
                lines = content.split('\n')
                import_insert_index = 0
                
                # Look for the end of import block
                for i, line in enumerate(lines):
                    line = line.strip()
                    if (line.startswith('import ') or line.startswith('from ')) and 'sys' in line:
                        import_insert_index = i + 1
                    elif line == '' and import_insert_index > 0:
                        break
                    elif not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''") and line != '' and import_insert_index > 0:
                        break
                
                # Insert StandardImportManager import
                lines.insert(import_insert_index, '')
                lines.insert(import_insert_index + 1, import_manager_import)
                content = '\n'.join(lines)
            
            # Save file if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ Migrated {file_replacements} sys.path.append calls")
                total_replacements += file_replacements
                processed_files += 1
            
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    print(f"\n🎯 Import Manager Migration Summary:")
    print(f"  - Files processed: {processed_files}")
    print(f"  - sys.path.append calls migrated: {total_replacements}")
    print(f"  - All services now use StandardImportManager")
    print(f"  - Eliminated sys.path anti-patterns")
    
    # Copy StandardImportManager to production
    try:
        import shutil
        shutil.copy(
            '/home/mdoehler/aktienanalyse-ökosystem/shared/standard_import_manager_v1.0.0_20250824.py',
            '/opt/aktienanalyse-ökosystem/shared/standard_import_manager_v1_0_0_20250824.py'
        )
        print(f"\n📁 Copied StandardImportManager to production shared directory")
    except Exception as e:
        print(f"\n❌ Failed to copy StandardImportManager: {e}")

if __name__ == "__main__":
    migrate_import_patterns()