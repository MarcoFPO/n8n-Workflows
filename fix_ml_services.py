#!/usr/bin/env python3
"""
ML Services Reparatur Script
Behebt die ausgefallenen ML-Services auf dem Production Server
"""

import subprocess
import sys
import tempfile
import os

def run_ssh_command(command):
    """Führt SSH-Befehl auf Production Server aus"""
    full_command = f"ssh root@10.1.1.174 \"{command}\""
    result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def create_ml_scheduler_script():
    """Erstellt das fehlende ML-Training-Scheduler Script"""
    scheduler_script_content = '''#!/bin/bash
# ML Training Scheduler Script
# Production-Version für Clean Architecture v6.1.0

set -euo pipefail

SCRIPT_DIR="/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular"
PYTHON_ENV="/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/venv/bin/python"
SCHEDULER_SCRIPT="automated_retraining_scheduler_v1_0_0_20250818.py"

# Logging Setup
LOGFILE="/var/log/ml-scheduler.log"
exec 1>> "$LOGFILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - ML Scheduler Start"

# Wechsel ins richtige Verzeichnis
cd "$SCRIPT_DIR" || {
    echo "ERROR: Kann nicht in Verzeichnis $SCRIPT_DIR wechseln"
    exit 1
}

# Python Virtual Environment prüfen
if [[ ! -f "$PYTHON_ENV" ]]; then
    echo "ERROR: Python Environment nicht gefunden: $PYTHON_ENV"
    exit 1
fi

# Scheduler Script ausführen
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starte ML Retraining Scheduler"
"$PYTHON_ENV" "$SCHEDULER_SCRIPT" || {
    echo "ERROR: ML Scheduler Ausführung fehlgeschlagen"
    exit 1
}

echo "$(date '+%Y-%m-%d %H:%M:%S') - ML Scheduler erfolgreich beendet"
'''

    # Erstelle temporäre Datei und übertrage sie
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp_file:
        tmp_file.write(scheduler_script_content)
        tmp_file_path = tmp_file.name

    # Übertrage Script auf Server
    subprocess.run(f"scp {tmp_file_path} root@10.1.1.174:/opt/aktienanalyse-ökosystem/deployment/scripts/ml-training-scheduler.sh", shell=True, check=True)
    
    # Berechtigungen setzen
    run_ssh_command("chmod +x /opt/aktienanalyse-ökosystem/deployment/scripts/ml-training-scheduler.sh")
    run_ssh_command("chown aktienanalyse:aktienanalyse /opt/aktienanalyse-ökosystem/deployment/scripts/ml-training-scheduler.sh")
    
    # Cleanup
    os.unlink(tmp_file_path)
    print("✅ ML-Scheduler Script erfolgreich erstellt")

def update_ml_scheduler_service():
    """Aktualisiert die ML-Scheduler Service Definition"""
    service_content = '''[Unit]
Description=ML Scheduler Service - Geplantes Model Training
Documentation=file:///opt/aktienanalyse-ökosystem/README.md
After=network.target postgresql.service redis.service ml-analytics.service
Wants=network.target
Requires=postgresql.service redis.service

[Service]
Type=oneshot
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular

# Scheduler Script ausführen (korrigierter Pfad)
ExecStart=/opt/aktienanalyse-ökosystem/deployment/scripts/ml-training-scheduler.sh

# Environment Variables
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular
Environment=ML_DATABASE_HOST=localhost
Environment=ML_DATABASE_PORT=5432
Environment=ML_DATABASE_NAME=aktienanalyse
Environment=ML_DATABASE_USER=ml_service
Environment=ML_DATABASE_PASSWORD=ml_service_secure_2025
Environment=ML_REDIS_URL=redis://localhost:6379/2
Environment=ML_LOG_LEVEL=INFO

# Keine automatischen Restarts für oneshot
Restart=no

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/logs /var/log /tmp

# Resource Limits
LimitNOFILE=1024
LimitNPROC=512
MemoryMax=512M

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ml-scheduler

[Install]
WantedBy=multi-user.target'''

    # Erstelle temporäre Datei
    with tempfile.NamedTemporaryFile(mode='w', suffix='.service', delete=False) as tmp_file:
        tmp_file.write(service_content)
        tmp_file_path = tmp_file.name

    # Übertrage und installiere Service
    subprocess.run(f"scp {tmp_file_path} root@10.1.1.174:/etc/systemd/system/ml-scheduler.service", shell=True, check=True)
    
    # Cleanup
    os.unlink(tmp_file_path)
    print("✅ ML-Scheduler Service Definition aktualisiert")

def update_ml_training_service():
    """Aktualisiert die ML-Training Service Definition"""
    service_content = '''[Unit]
Description=ML Training Service - Model Training für ML-Pipeline
Documentation=file:///opt/aktienanalyse-ökosystem/README.md
After=network.target postgresql.service redis.service ml-analytics.service
Wants=network.target
Requires=postgresql.service redis.service

[Service]
Type=simple
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular

# Training Service ausführen (korrigierter Pfad)
ExecStart=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/venv/bin/python /opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/training_service_v1_0_0_20250817.py

# Environment Variables
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular
Environment=ML_SERVICE_NAME=ml-training
Environment=ML_SERVICE_TRAINING_PORT=8020
Environment=ML_DATABASE_HOST=localhost
Environment=ML_DATABASE_PORT=5432
Environment=ML_DATABASE_NAME=aktienanalyse
Environment=ML_DATABASE_USER=ml_service
Environment=ML_DATABASE_PASSWORD=ml_service_secure_2025
Environment=ML_REDIS_URL=redis://localhost:6379/2
Environment=ML_LOG_LEVEL=INFO
Environment=ML_MODEL_STORAGE_PATH=/opt/aktienanalyse-ökosystem/ml-models
Environment=ML_ENABLE_GPU=false
Environment=ML_MIXED_PRECISION=false
Environment=ML_TRAINING_EPOCHS=50
Environment=ML_TRAINING_BATCH_SIZE=32

# Restart Policy (weniger aggressiv für Training)
Restart=on-failure
RestartSec=30
StartLimitInterval=300
StartLimitBurst=2

# Process Management
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=300
SendSIGKILL=no

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/ml-models /opt/aktienanalyse-ökosystem/logs /tmp

# Resource Limits (höher für Training)
LimitNOFILE=65536
LimitNPROC=8192
MemoryMax=8G
CPUQuota=400%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ml-training

[Install]
WantedBy=multi-user.target'''

    # Erstelle temporäre Datei
    with tempfile.NamedTemporaryFile(mode='w', suffix='.service', delete=False) as tmp_file:
        tmp_file.write(service_content)
        tmp_file_path = tmp_file.name

    # Übertrage und installiere Service
    subprocess.run(f"scp {tmp_file_path} root@10.1.1.174:/etc/systemd/system/ml-training.service", shell=True, check=True)
    
    # Cleanup
    os.unlink(tmp_file_path)
    print("✅ ML-Training Service Definition aktualisiert")

def restart_ml_services():
    """Startet die ML-Services neu"""
    print("🔄 Lade systemd daemon neu...")
    run_ssh_command("systemctl daemon-reload")
    
    print("🔄 Aktiviere ML-Services...")
    run_ssh_command("systemctl enable ml-scheduler.service")
    run_ssh_command("systemctl enable ml-training.service")
    
    print("🚀 Starte ML-Training Service...")
    returncode, stdout, stderr = run_ssh_command("systemctl start ml-training.service")
    if returncode == 0:
        print("✅ ML-Training Service erfolgreich gestartet")
    else:
        print(f"❌ ML-Training Service Start fehlgeschlagen: {stderr}")
    
    print("🚀 Führe ML-Scheduler einmalig aus...")
    returncode, stdout, stderr = run_ssh_command("systemctl start ml-scheduler.service")
    if returncode == 0:
        print("✅ ML-Scheduler erfolgreich ausgeführt")
    else:
        print(f"❌ ML-Scheduler Ausführung fehlgeschlagen: {stderr}")

def verify_ml_services():
    """Verifiziert den Status der ML-Services"""
    print("\n📊 Überprüfung ML-Services Status...")
    
    # ML-Training Status
    returncode, stdout, stderr = run_ssh_command("systemctl is-active ml-training.service")
    print(f"ML-Training Service: {stdout.strip()}")
    
    # ML-Scheduler letzter Run Status
    returncode, stdout, stderr = run_ssh_command("systemctl status ml-scheduler.service --no-pager -n 3")
    print(f"ML-Scheduler letzter Status:\n{stdout}")

def main():
    """Hauptfunktion für ML-Services Reparatur"""
    print("🔧 Starting ML Services Reparatur...")
    print("=" * 50)
    
    try:
        # Erstelle fehlende Directories
        print("📁 Erstelle benötigte Verzeichnisse...")
        run_ssh_command("mkdir -p /opt/aktienanalyse-ökosystem/deployment/scripts")
        run_ssh_command("mkdir -p /opt/aktienanalyse-ökosystem/ml-models")
        run_ssh_command("chown -R aktienanalyse:aktienanalyse /opt/aktienanalyse-ökosystem/ml-models")
        
        # Repariere ML-Services
        create_ml_scheduler_script()
        update_ml_scheduler_service()
        update_ml_training_service()
        restart_ml_services()
        
        print("\n" + "=" * 50)
        verify_ml_services()
        
        print("\n🎉 ML-Services Reparatur abgeschlossen!")
        print("✅ Alle Services sollten jetzt funktionsfähig sein")
        
    except Exception as e:
        print(f"❌ Fehler bei ML-Services Reparatur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()