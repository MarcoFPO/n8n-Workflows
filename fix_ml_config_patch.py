#!/usr/bin/env python3
"""
ML Config Hotfix für Production
Repariert ml_service_config.py für Training Service
"""

import subprocess
import tempfile

def apply_ml_config_fix():
    """Fügt den fehlenden training_port zur ML-Config hinzu"""
    
    config_fix_content = '''
# Patch für ML Service Config - Training Port hinzufügen
# Diese Änderung fügt den fehlenden 'training_port' zur Config hinzu

# In Zeile ca. 18-25 nach 'port': int(...) einfügen:
        'training_port': int(os.getenv('ML_SERVICE_TRAINING_PORT', 8020)),
'''

    # Hole aktuelle Config
    result = subprocess.run("ssh root@10.1.1.174 'cat /opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/config/ml_service_config.py'", 
                          shell=True, capture_output=True, text=True)
    
    original_config = result.stdout
    
    # Suche nach der Zeile mit 'port': int(os.getenv('ML_SERVICE_PORT', 8021)),
    lines = original_config.split('\n')
    new_lines = []
    
    for line in lines:
        new_lines.append(line)
        # Füge training_port nach der port-Zeile ein
        if "'port': int(os.getenv('ML_SERVICE_PORT'" in line:
            # Ermittle die Einrückung
            indentation = len(line) - len(line.lstrip())
            indent = ' ' * indentation
            new_lines.append(f"{indent}'training_port': int(os.getenv('ML_SERVICE_TRAINING_PORT', 8020)),")
    
    # Schreibe die korrigierte Config in temporäre Datei
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
        tmp_file.write('\n'.join(new_lines))
        tmp_file_path = tmp_file.name
    
    # Übertrage korrigierte Config
    subprocess.run(f"scp {tmp_file_path} root@10.1.1.174:/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/config/ml_service_config.py", shell=True, check=True)
    
    # Cleanup
    import os
    os.unlink(tmp_file_path)
    
    print("✅ ML Config erfolgreich gepatcht - training_port hinzugefügt")

def restart_ml_training():
    """Startet ML-Training Service neu"""
    print("🔄 Starte ML-Training Service neu...")
    subprocess.run("ssh root@10.1.1.174 'systemctl restart ml-training.service'", shell=True, check=True)
    
    # Warte kurz und prüfe Status
    import time
    time.sleep(5)
    
    result = subprocess.run("ssh root@10.1.1.174 'systemctl is-active ml-training.service'", 
                          shell=True, capture_output=True, text=True)
    
    if result.stdout.strip() == 'active':
        print("✅ ML-Training Service läuft jetzt stabil!")
        return True
    else:
        print("❌ ML-Training Service noch nicht stabil - prüfe Logs...")
        # Zeige letzte Logs
        log_result = subprocess.run("ssh root@10.1.1.174 'journalctl -u ml-training.service -n 10 --no-pager'", 
                                  shell=True, capture_output=True, text=True)
        print(log_result.stdout)
        return False

def main():
    print("🔧 Starte ML Config Hotfix...")
    print("=" * 50)
    
    try:
        apply_ml_config_fix()
        success = restart_ml_training()
        
        if success:
            print("\n🎉 ML Config Hotfix erfolgreich!")
            print("✅ ML-Training Service läuft stabil")
        else:
            print("\n⚠️  ML Config Hotfix angewendet, aber Service noch nicht stabil")
            
    except Exception as e:
        print(f"❌ Fehler beim ML Config Hotfix: {e}")

if __name__ == "__main__":
    main()