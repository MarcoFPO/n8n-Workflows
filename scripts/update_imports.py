#!/usr/bin/env python3
"""
Script zur systematischen Aktualisierung aller Import-Statements 
für die neue Modul-Versioning-Konvention
"""

import os
import re
import glob
from typing import Dict, List, Tuple

def get_module_mapping() -> Dict[str, str]:
    """Mapping von alten zu neuen Modulnamen"""
    mapping = {}
    
    # Finde alle umbenannten Module
    for root, dirs, files in os.walk('/home/mdoehler/aktienanalyse-ökosystem/services'):
        for file in files:
            if file.endswith('.py') and '_v' in file and re.search(r'_v\d+\.\d+\.\d+_\d{8}\.py$', file):
                # Extrahiere alten Namen
                old_name = re.sub(r'_v\d+\.\d+\.\d+_\d{8}\.py$', '', file)
                new_name = file[:-3]  # Ohne .py Extension
                mapping[old_name] = new_name
    
    return mapping

def update_imports_in_file(file_path: str, module_mapping: Dict[str, str]) -> List[str]:
    """Aktualisiert Imports in einer Datei"""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Update verschiedene Import-Patterns
        for old_module, new_module in module_mapping.items():
            # from modules.old_module import ...
            pattern1 = rf'from\s+modules\.{re.escape(old_module)}\s+import'
            replacement1 = f'from modules.{new_module} import'
            if re.search(pattern1, content):
                content = re.sub(pattern1, replacement1, content)
                changes.append(f"  ✅ from modules.{old_module} → modules.{new_module}")
            
            # import modules.old_module
            pattern2 = rf'import\s+modules\.{re.escape(old_module)}'
            replacement2 = f'import modules.{new_module}'
            if re.search(pattern2, content):
                content = re.sub(pattern2, replacement2, content)
                changes.append(f"  ✅ import modules.{old_module} → modules.{new_module}")
            
            # from old_module import ...
            pattern3 = rf'from\s+{re.escape(old_module)}\s+import'
            replacement3 = f'from {new_module} import'
            if re.search(pattern3, content):
                content = re.sub(pattern3, replacement3, content)
                changes.append(f"  ✅ from {old_module} → {new_module}")
            
            # import old_module
            pattern4 = rf'import\s+{re.escape(old_module)}'
            replacement4 = f'import {new_module}'
            if re.search(pattern4, content):
                content = re.sub(pattern4, replacement4, content)
                changes.append(f"  ✅ import {old_module} → {new_module}")
        
        # Schreibe nur wenn Änderungen vorhanden
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
        return changes
    
    except Exception as e:
        return [f"  ❌ Fehler: {str(e)}"]

def main():
    """Hauptfunktion"""
    print("🔄 Starte Import-Aktualisierung für Modul-Versioning...")
    
    # Erstelle Modul-Mapping
    module_mapping = get_module_mapping()
    print(f"📋 {len(module_mapping)} Module-Mappings gefunden")
    
    if not module_mapping:
        print("❌ Keine umbenannten Module gefunden!")
        return
    
    # Finde alle Python-Dateien
    python_files = []
    for root, dirs, files in os.walk('/home/mdoehler/aktienanalyse-ökosystem/services'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 {len(python_files)} Python-Dateien gefunden")
    
    total_changes = 0
    updated_files = 0
    
    # Aktualisiere jede Datei
    for file_path in python_files:
        changes = update_imports_in_file(file_path, module_mapping)
        
        if changes and any('✅' in change for change in changes):
            updated_files += 1
            total_changes += len([c for c in changes if '✅' in c])
            print(f"\n📝 {os.path.relpath(file_path)}:")
            for change in changes:
                print(change)
    
    print(f"\n🎉 Import-Aktualisierung abgeschlossen!")
    print(f"✅ {updated_files} Dateien aktualisiert")
    print(f"✅ {total_changes} Import-Statements geändert")
    
    if updated_files == 0:
        print("ℹ️  Keine Import-Updates erforderlich - alle Imports bereits korrekt")

if __name__ == "__main__":
    main()