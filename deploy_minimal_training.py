#!/usr/bin/env python3
"""
Deploy Minimal Training Service
Deployt den stabilen Minimal Training Service auf Production
"""

import subprocess
import tempfile

def deploy_minimal_service():
    """Deployt den Minimal Training Service"""
    
    # Aktualisierte Service Definition
    service_content = '''[Unit]
Description=ML Training Service - Minimal Stable Version
Documentation=file:///opt/aktienanalyse-ökosystem/README.md
After=network.target postgresql.service redis.service
Wants=network.target

[Service]
Type=simple
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular

# Minimal Training Service ausführen (STABLE VERSION)
ExecStart=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/venv/bin/python /opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular/minimal_training_service.py

# Environment Variables (minimal required)
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem/services/ml-analytics-service-modular
Environment=ML_SERVICE_TRAINING_PORT=8020
Environment=ML_LOG_LEVEL=INFO

# Restart Policy
Restart=on-failure
RestartSec=10
StartLimitInterval=300
StartLimitBurst=3

# Process Management
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=60
SendSIGKILL=yes

# Security (minimal for stability)
NoNewPrivileges=true
PrivateTmp=true

# Resource Limits (conservative)
LimitNOFILE=1024
LimitNPROC=512
MemoryMax=1G
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ml-training

[Install]
WantedBy=multi-user.target'''

    # Service Definition übertragen
    with tempfile.NamedTemporaryFile(mode='w', suffix='.service', delete=False) as tmp_file:
        tmp_file.write(service_content)
        tmp_file_path = tmp_file.name

    subprocess.run(f"scp {tmp_file_path} root@10.1.1.174:/etc/systemd/system/ml-training.service", shell=True, check=True)
    
    # Cleanup
    import os
    os.unlink(tmp_file_path)
    print("✅ Minimal Training Service Definition deployed")

def restart_and_verify():
    """Startet Service neu und verifiziert Stabilität"""
    print("🔄 Systemd daemon reload...")
    subprocess.run("ssh root@10.1.1.174 'systemctl daemon-reload'", shell=True, check=True)
    
    print("🔄 Stoppe alten Service...")
    subprocess.run("ssh root@10.1.1.174 'systemctl stop ml-training.service'", shell=True)
    
    print("🚀 Starte Minimal Training Service...")
    subprocess.run("ssh root@10.1.1.174 'systemctl start ml-training.service'", shell=True, check=True)
    
    # Warte und prüfe Status mehrfach
    import time
    for i in range(3):
        time.sleep(5)
        result = subprocess.run("ssh root@10.1.1.174 'systemctl is-active ml-training.service'", 
                              shell=True, capture_output=True, text=True)
        status = result.stdout.strip()
        print(f"Status Check {i+1}/3: {status}")
        
        if status == 'active':
            print("✅ Service läuft stabil!")
            break
    else:
        print("⚠️  Service noch nicht stabil")
        subprocess.run("ssh root@10.1.1.174 'journalctl -u ml-training.service -n 10 --no-pager'", shell=True)
        return False
    
    # Final Status Report
    print("\n📊 Final Service Status:")
    subprocess.run("ssh root@10.1.1.174 'systemctl status ml-training.service --no-pager -n 5'", shell=True)
    return True

def enable_service():
    """Aktiviert den Service für Autostart"""
    print("🔧 Aktiviere Service für Autostart...")
    subprocess.run("ssh root@10.1.1.174 'systemctl enable ml-training.service'", shell=True, check=True)
    print("✅ Service für Autostart aktiviert")

def main():
    print("🚀 Deploy Minimal ML Training Service...")
    print("=" * 50)
    
    try:
        deploy_minimal_service()
        success = restart_and_verify()
        
        if success:
            enable_service()
            print("\n🎉 Minimal ML Training Service erfolgreich deployed!")
            print("✅ Service läuft stabil auf Port 8020")
            print("✅ Autostart aktiviert")
            return True
        else:
            print("\n⚠️  Deployment teilweise erfolgreich, Service noch nicht stabil")
            return False
            
    except Exception as e:
        print(f"❌ Deployment Fehler: {e}")
        return False

if __name__ == "__main__":
    main()