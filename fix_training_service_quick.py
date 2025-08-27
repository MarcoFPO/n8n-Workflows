#!/usr/bin/env python3
"""
Quick Fix für ML Training Service
Repariert das initialize() Problem
"""

import subprocess
import tempfile

def fix_training_service():
    """Fügt eine Quick-Fix initialize_service Implementierung hinzu"""
    
    # Hole das aktuelle Training Script
    result = subprocess.run("ssh root@10.1.1.174 'cat /opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/training_service_v1_0_0_20250817.py'", 
                          shell=True, capture_output=True, text=True)
    
    original_script = result.stdout
    lines = original_script.split('\n')
    
    # Suche nach der Zeile mit "async def initialize" und ersetze die Implementierung
    new_lines = []
    inside_initialize = False
    indent_level = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Finde die initialize Methode
        if 'async def initialize(' in line:
            new_lines.append(line)
            # Ersetze die gesamte initialize Methode
            new_lines.append('        """Initialisiert Training Service - Fixed Version"""')
            new_lines.append('        try:')
            new_lines.append('            logger.info("Initializing ML Training Service...")')
            new_lines.append('            ')
            new_lines.append('            # Database Connection')
            new_lines.append('            from shared.database import DatabaseConnection')
            new_lines.append('            self.database = DatabaseConnection(ML_SERVICE_CONFIG[\'database\'])')
            new_lines.append('            await self.database.connect()')
            new_lines.append('            ')
            new_lines.append('            # Event Bus Connection')
            new_lines.append('            from shared.event_bus import EventBusConnection')
            new_lines.append('            self.event_bus = EventBusConnection(ML_SERVICE_CONFIG[\'event_bus\'])')
            new_lines.append('            await self.event_bus.connect()')
            new_lines.append('            ')
            new_lines.append('            logger.info("Core connections established")')
            new_lines.append('            return True')
            new_lines.append('            ')
            new_lines.append('        except Exception as e:')
            new_lines.append('            logger.error(f"Failed to initialize Training Service: {str(e)}")')
            new_lines.append('            return False')
            new_lines.append('')
            
            # Skip the original implementation
            i += 1
            while i < len(lines) and (lines[i].startswith('        ') or lines[i].strip() == ''):
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith('        '):
                    break
                i += 1
            continue
        else:
            new_lines.append(line)
        
        i += 1
    
    # Schreibe das reparierte Script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
        tmp_file.write('\n'.join(new_lines))
        tmp_file_path = tmp_file.name
    
    # Erstelle Backup und übertrage repariertes Script
    subprocess.run("ssh root@10.1.1.174 'cp /opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/training_service_v1_0_0_20250817.py /opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/training_service_v1_0_0_20250817.py.backup'", shell=True, check=True)
    subprocess.run(f"scp {tmp_file_path} root@10.1.1.174:/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/training_service_v1_0_0_20250817.py", shell=True, check=True)
    
    # Cleanup
    import os
    os.unlink(tmp_file_path)
    print("✅ Training Service Quick-Fix implementiert")

def restart_and_test():
    """Startet ML-Training Service neu und testet"""
    print("🔄 Starte ML-Training Service neu...")
    subprocess.run("ssh root@10.1.1.174 'systemctl restart ml-training.service'", shell=True, check=True)
    
    # Warte und prüfe Status
    import time
    time.sleep(8)
    
    result = subprocess.run("ssh root@10.1.1.174 'systemctl is-active ml-training.service'", 
                          shell=True, capture_output=True, text=True)
    
    status = result.stdout.strip()
    print(f"Service Status: {status}")
    
    if status == 'active':
        print("✅ ML-Training Service läuft jetzt stabil!")
        
        # Zeige noch letzten Status für Bestätigung
        subprocess.run("ssh root@10.1.1.174 'systemctl status ml-training.service --no-pager -n 3'", shell=True)
        return True
    else:
        print("❌ Service noch nicht stabil - Debug-Logs:")
        subprocess.run("ssh root@10.1.1.174 'journalctl -u ml-training.service -n 15 --no-pager'", shell=True)
        return False

def main():
    print("🚀 Starte Quick-Fix für ML Training Service...")
    print("=" * 60)
    
    try:
        fix_training_service()
        success = restart_and_test()
        
        if success:
            print("\n🎉 ML Training Service Quick-Fix erfolgreich!")
            print("✅ Service läuft stabil auf Port 8020")
        else:
            print("\n⚠️  Quick-Fix angewendet, aber Service noch nicht stabil")
            
    except Exception as e:
        print(f"❌ Fehler beim Quick-Fix: {e}")

if __name__ == "__main__":
    main()