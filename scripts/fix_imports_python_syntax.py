#!/usr/bin/env python3
"""
Script zur Korrektur der Import-Statements für Python-kompatible Syntax
Punkte in Modulnamen werden durch Underscores ersetzt für Imports
"""

import os
import re
import glob
from typing import Dict, List, Tuple

def fix_imports_in_file(file_path: str) -> List[str]:
    """Korrigiert Import-Statements für Python-Syntax"""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern für Import-Statements mit Versionen (Punkte ersetzen)
        # from modules.module_v1.2.0_20250815 import ... → from modules.module_v1_2_0_20250815 import ...
        pattern1 = r'from\s+modules\.([a-zA-Z_]+)_v(\d+)\.(\d+)\.(\d+)_(\d{8})\s+import'
        def replace1(match):
            module_name = match.group(1)
            major = match.group(2)
            minor = match.group(3)
            patch = match.group(4)
            date = match.group(5)
            return f'from modules.{module_name}_v{major}_{minor}_{patch}_{date} import'
        
        if re.search(pattern1, content):
            content = re.sub(pattern1, replace1, content)
            changes.append("  ✅ Fixed dots in module version numbers for imports")
        
        # Pattern für direkte Imports mit Versionen
        # import modules.module_v1.2.0_20250815 → import modules.module_v1_2_0_20250815
        pattern2 = r'import\s+modules\.([a-zA-Z_]+)_v(\d+)\.(\d+)\.(\d+)_(\d{8})'
        def replace2(match):
            module_name = match.group(1)
            major = match.group(2)
            minor = match.group(3)
            patch = match.group(4)
            date = match.group(5)
            return f'import modules.{module_name}_v{major}_{minor}_{patch}_{date}'
        
        if re.search(pattern2, content):
            content = re.sub(pattern2, replace2, content)
            changes.append("  ✅ Fixed dots in direct module imports")
        
        # Pattern für from-imports ohne modules prefix
        # from module_v1.2.0_20250815 import ... → from module_v1_2_0_20250815 import ...
        pattern3 = r'from\s+([a-zA-Z_]+)_v(\d+)\.(\d+)\.(\d+)_(\d{8})\s+import'
        def replace3(match):
            module_name = match.group(1)
            major = match.group(2)
            minor = match.group(3)
            patch = match.group(4)
            date = match.group(5)
            return f'from {module_name}_v{major}_{minor}_{patch}_{date} import'
        
        if re.search(pattern3, content):
            content = re.sub(pattern3, replace3, content)
            changes.append("  ✅ Fixed dots in direct from-imports")
        
        # Pattern für import ohne modules prefix
        # import module_v1.2.0_20250815 → import module_v1_2_0_20250815
        pattern4 = r'import\s+([a-zA-Z_]+)_v(\d+)\.(\d+)\.(\d+)_(\d{8})'
        def replace4(match):
            module_name = match.group(1)
            major = match.group(2)
            minor = match.group(3)
            patch = match.group(4)
            date = match.group(5)
            return f'import {module_name}_v{major}_{minor}_{patch}_{date}'
        
        if re.search(pattern4, content):
            content = re.sub(pattern4, replace4, content)
            changes.append("  ✅ Fixed dots in simple imports")
        
        # Schreibe nur wenn Änderungen vorhanden
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return changes
    
    except Exception as e:
        return [f"  ❌ Fehler: {str(e)}"]

def main():
    """Hauptfunktion"""
    print("🔧 Korrigiere Import-Statements für Python-Syntax...")
    
    # Finde alle Python-Dateien
    python_files = []
    for root, dirs, files in os.walk('/home/mdoehler/aktienanalyse-ökosystem/services'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 {len(python_files)} Python-Dateien gefunden")
    
    total_changes = 0
    updated_files = 0
    
    # Korrigiere jede Datei
    for file_path in python_files:
        changes = fix_imports_in_file(file_path)
        
        if changes and any('✅' in change for change in changes):
            updated_files += 1
            total_changes += len([c for c in changes if '✅' in c])
            print(f"\n📝 {os.path.relpath(file_path)}:")
            for change in changes:
                print(change)
    
    print(f"\n🎉 Import-Syntax-Korrektur abgeschlossen!")
    print(f"✅ {updated_files} Dateien korrigiert")
    print(f"✅ {total_changes} Import-Patterns gefixt")
    
    if updated_files == 0:
        print("ℹ️  Keine Import-Korrekturen erforderlich - alle Imports bereits korrekt")

if __name__ == "__main__":
    main()