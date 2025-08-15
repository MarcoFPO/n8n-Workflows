#!/usr/bin/env python3
"""
Script zur Umbenennung der Modul-Dateien für Python-kompatible Syntax
Punkte in Dateinamen werden durch Underscores ersetzt
"""

import os
import shutil
from typing import Dict, List, Tuple

def rename_files_for_python() -> List[str]:
    """Benennt alle Module-Dateien mit Punkten zu Underscores um"""
    changes = []
    
    # Durchsuche alle Service-Verzeichnisse
    for root, dirs, files in os.walk('/home/mdoehler/aktienanalyse-ökosystem/services'):
        for filename in files:
            if filename.endswith('.py') and '_v' in filename and '.' in filename:
                # Prüfe ob Dateiname Versioning mit Punkten hat
                if '_v' in filename and filename.count('.') > 1:  # Mehr als nur die .py Extension
                    old_path = os.path.join(root, filename)
                    
                    # Ersetze Punkte durch Underscores (außer .py)
                    name_parts = filename.rsplit('.py', 1)
                    if len(name_parts) == 2:
                        base_name = name_parts[0]
                        new_base_name = base_name.replace('.', '_')
                        new_filename = new_base_name + '.py'
                        new_path = os.path.join(root, new_filename)
                        
                        try:
                            shutil.move(old_path, new_path)
                            relative_old = os.path.relpath(old_path, '/home/mdoehler/aktienanalyse-ökosystem')
                            relative_new = os.path.relpath(new_path, '/home/mdoehler/aktienanalyse-ökosystem')
                            changes.append(f"  ✅ {relative_old} → {relative_new}")
                        except Exception as e:
                            changes.append(f"  ❌ Fehler bei {filename}: {str(e)}")
    
    return changes

def main():
    """Hauptfunktion"""
    print("🔧 Benenne Modul-Dateien für Python-Syntax um...")
    print("⚠️  Punkte in Dateinamen werden durch Underscores ersetzt")
    
    changes = rename_files_for_python()
    
    if changes:
        print(f"\n📝 {len(changes)} Dateien umbenannt:")
        for change in changes:
            print(change)
    else:
        print("\nℹ️  Keine Dateien benötigten Umbenennung")
    
    print("\n✅ Datei-Umbenennung abgeschlossen!")

if __name__ == "__main__":
    main()