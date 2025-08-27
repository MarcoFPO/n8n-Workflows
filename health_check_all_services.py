#!/usr/bin/env python3
"""
Service Health Dashboard v1.0.0
Comprehensive Production Health Monitoring für Aktienanalyse-Ökosystem

Überwacht alle 11+ Services und zeigt detaillierten Status
Autor: Claude Code Production Stabilization
"""

import subprocess
import sys
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class ServiceHealthDashboard:
    def __init__(self):
        self.server_host = "10.1.1.174"
        self.services_config = {
            # Core Services
            "aktienanalyse-event-bus-v6.service": {
                "port": 8014,
                "description": "Event Bus - Core Communication Hub",
                "critical": True,
                "health_endpoint": "/health"
            },
            "aktienanalyse-data-processing-v6.service": {
                "port": 8017,
                "description": "Data Processing - CSV Middleware", 
                "critical": True,
                "health_endpoint": "/health"
            },
            "aktienanalyse-prediction-tracking-v6.service": {
                "port": 8018,
                "description": "Prediction Tracking - SOLL-IST Analysis",
                "critical": True,
                "health_endpoint": "/health"
            },
            "aktienanalyse-marketcap-v6.service": {
                "port": 8019,
                "description": "MarketCap Service - Market Data",
                "critical": True,
                "health_endpoint": "/health"
            },
            "ml-training.service": {
                "port": 8020,
                "description": "ML Training - Model Training Engine",
                "critical": False,
                "health_endpoint": None
            },
            "aktienanalyse-monitoring-modular.service": {
                "port": 8015,
                "description": "System Monitoring - Health Aggregator",
                "critical": True,
                "health_endpoint": "/health"
            },
            
            # Business Logic Services
            "aktienanalyse-broker-gateway-eventbus-first.service": {
                "port": 8008,
                "description": "Broker Gateway - External Data Integration",
                "critical": True,
                "health_endpoint": "/health"
            },
            "aktienanalyse-intelligent-core-eventbus-first.service": {
                "port": 8011,
                "description": "Intelligent Core - Business Logic Hub",
                "critical": True,
                "health_endpoint": "/health"
            },
            "aktienanalyse-prediction-averages.service": {
                "port": 8026,
                "description": "Prediction Averages - Statistical Analysis",
                "critical": True,
                "health_endpoint": "/health"
            },
            
            # Frontend Services
            "frontend-port-8080": {
                "port": 8080,
                "description": "Primary Frontend - User Interface",
                "critical": True,
                "health_endpoint": "/",
                "is_http_service": True
            },
            "frontend-port-8081": {
                "port": 8081, 
                "description": "Secondary Frontend - Admin Interface",
                "critical": False,
                "health_endpoint": "/",
                "is_http_service": True
            }
        }
        
        self.ml_services = ["ml-scheduler.service", "ml-training.service"]
        
    def run_ssh_command(self, command: str) -> Tuple[int, str, str]:
        """Führt SSH-Befehl auf Production Server aus"""
        full_command = f"ssh root@{self.server_host} \"{command}\""
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    
    def check_systemd_service_status(self, service_name: str) -> Dict:
        """Prüft systemd Service Status"""
        status_info = {
            "name": service_name,
            "active": False,
            "enabled": False,
            "status": "unknown",
            "pid": None,
            "memory": None,
            "cpu_time": None,
            "restart_count": 0
        }
        
        # Service Status prüfen
        returncode, stdout, stderr = self.run_ssh_command(f"systemctl is-active {service_name}")
        if returncode == 0:
            status_info["active"] = stdout.strip() == "active"
            status_info["status"] = stdout.strip()
        
        # Service Enabled Status
        returncode, stdout, stderr = self.run_ssh_command(f"systemctl is-enabled {service_name}")
        if returncode == 0:
            status_info["enabled"] = stdout.strip() == "enabled"
        
        # Detaillierte Informationen
        returncode, stdout, stderr = self.run_ssh_command(f"systemctl show {service_name} --property=MainPID,MemoryCurrent,CPUUsageNSec,NRestarts")
        if returncode == 0:
            for line in stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'MainPID' and value != '0':
                        status_info["pid"] = int(value)
                    elif key == 'MemoryCurrent' and value.isdigit():
                        status_info["memory"] = int(value)
                    elif key == 'CPUUsageNSec' and value.isdigit():
                        status_info["cpu_time"] = int(value) / 1000000000  # Convert to seconds
                    elif key == 'NRestarts':
                        status_info["restart_count"] = int(value)
        
        return status_info
    
    def check_port_connectivity(self, port: int) -> bool:
        """Prüft ob Port erreichbar ist"""
        returncode, stdout, stderr = self.run_ssh_command(f"netstat -tln | grep ':{port} ' | head -1")
        return returncode == 0 and f":{port} " in stdout
    
    def check_http_health(self, port: int, endpoint: str = "/health") -> Dict:
        """Prüft HTTP Health Endpoint"""
        health_info = {
            "responsive": False,
            "status_code": None,
            "response_time": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            url = f"http://{self.server_host}:{port}{endpoint}"
            response = requests.get(url, timeout=5)
            health_info["responsive"] = True
            health_info["status_code"] = response.status_code
            health_info["response_time"] = round((time.time() - start_time) * 1000, 2)
        except Exception as e:
            health_info["error"] = str(e)
        
        return health_info
    
    def format_memory(self, bytes_val: Optional[int]) -> str:
        """Formatiert Memory-Werte"""
        if bytes_val is None:
            return "N/A"
        
        if bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.1f} GB"
    
    def print_service_status(self, service_name: str, config: Dict, status: Dict, port_status: bool, health_info: Optional[Dict] = None):
        """Druckt Service Status formatiert"""
        # Status Icon
        if status["active"] and port_status:
            icon = "✅"
            status_text = "HEALTHY"
        elif status["active"]:
            icon = "⚠️"
            status_text = "RUNNING (NO PORT)"
        else:
            icon = "❌"
            status_text = "FAILED"
        
        # Criticality
        critical_text = "CRITICAL" if config.get("critical", False) else "OPTIONAL"
        
        print(f"{icon} [{critical_text}] {config['description']}")
        print(f"   Service: {service_name}")
        print(f"   Status: {status_text} | Active: {status['active']} | Enabled: {status['enabled']}")
        
        if config.get("port"):
            print(f"   Port {config['port']}: {'OPEN' if port_status else 'CLOSED'}")
        
        if status.get("pid"):
            print(f"   PID: {status['pid']} | Memory: {self.format_memory(status.get('memory'))} | Restarts: {status.get('restart_count', 0)}")
        
        if health_info:
            if health_info["responsive"]:
                print(f"   Health Check: ✅ {health_info['status_code']} ({health_info['response_time']}ms)")
            else:
                print(f"   Health Check: ❌ {health_info.get('error', 'No response')}")
        
        print()
    
    def check_ml_services(self) -> Dict:
        """Spezielle Prüfung für ML Services"""
        ml_status = {}
        
        for service in self.ml_services:
            status = self.check_systemd_service_status(service)
            
            # Für ML-Scheduler: oneshot service kann "inactive" aber erfolgreich sein
            if service == "ml-scheduler.service" and status["status"] in ["inactive", "dead"]:
                # Prüfe ob letzter Run erfolgreich war
                returncode, stdout, stderr = self.run_ssh_command(f"systemctl show {service} --property=Result")
                if "Result=success" in stdout:
                    status["status"] = "completed successfully"
                    status["active"] = True  # Behandle als "aktiv" für Health Check
            
            ml_status[service] = status
        
        return ml_status
    
    def generate_health_report(self) -> Dict:
        """Generiert kompletten Health Report"""
        print("🔍 Gathering Service Health Data...")
        print("=" * 70)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "server": self.server_host,
            "overall_health": "UNKNOWN",
            "services": {},
            "summary": {
                "total_services": 0,
                "healthy_services": 0,
                "failed_services": 0,
                "critical_services": 0,
                "critical_healthy": 0
            }
        }
        
        # Prüfe alle konfigurierten Services
        for service_name, config in self.services_config.items():
            report["summary"]["total_services"] += 1
            
            if config.get("critical", False):
                report["summary"]["critical_services"] += 1
            
            # Service Status prüfen
            if service_name.startswith("frontend-"):
                # Spezielle Behandlung für Frontend Services
                port = config["port"]
                port_status = self.check_port_connectivity(port)
                status = {
                    "active": port_status, 
                    "enabled": True,  # Frontend Services sind immer "enabled"
                    "status": "active" if port_status else "inactive",
                    "pid": None,
                    "memory": None,
                    "restart_count": 0
                }
            else:
                status = self.check_systemd_service_status(service_name)
            
            # Port Connectivity
            port_status = True
            if config.get("port"):
                port_status = self.check_port_connectivity(config["port"])
            
            # HTTP Health Check
            health_info = None
            if config.get("health_endpoint") and port_status:
                health_info = self.check_http_health(config["port"], config["health_endpoint"])
            
            # Service Health bewerten
            is_healthy = status["active"] and port_status
            if health_info:
                is_healthy = is_healthy and health_info.get("responsive", False)
            
            if is_healthy:
                report["summary"]["healthy_services"] += 1
                if config.get("critical", False):
                    report["summary"]["critical_healthy"] += 1
            else:
                report["summary"]["failed_services"] += 1
            
            # Service zu Report hinzufügen
            report["services"][service_name] = {
                "config": config,
                "status": status,
                "port_status": port_status,
                "health_info": health_info,
                "is_healthy": is_healthy
            }
            
            # Status ausgeben
            self.print_service_status(service_name, config, status, port_status, health_info)
        
        # ML Services separat prüfen
        print("🤖 ML Services Status:")
        print("-" * 30)
        
        ml_status = self.check_ml_services()
        for service_name, status in ml_status.items():
            if service_name == "ml-scheduler.service":
                print(f"✅ ML Scheduler: {status['status']} (oneshot service)")
            elif service_name == "ml-training.service":
                port_status = self.check_port_connectivity(8020)
                health_icon = "✅" if status["active"] and port_status else "❌"
                print(f"{health_icon} ML Training: {'RUNNING' if status['active'] else 'STOPPED'} (Port 8020: {'OPEN' if port_status else 'CLOSED'})")
        print()
        
        # Overall Health bestimmen
        critical_ratio = report["summary"]["critical_healthy"] / max(1, report["summary"]["critical_services"])
        if critical_ratio >= 1.0:
            report["overall_health"] = "EXCELLENT"
        elif critical_ratio >= 0.8:
            report["overall_health"] = "GOOD"
        elif critical_ratio >= 0.6:
            report["overall_health"] = "DEGRADED"
        else:
            report["overall_health"] = "CRITICAL"
        
        return report
    
    def print_summary(self, report: Dict):
        """Druckt Health Summary"""
        summary = report["summary"]
        
        print("📊 SYSTEM HEALTH SUMMARY")
        print("=" * 70)
        print(f"Overall Health: {report['overall_health']}")
        print(f"Server: {report['server']}")
        print(f"Timestamp: {report['timestamp']}")
        print()
        print(f"Total Services: {summary['total_services']}")
        print(f"Healthy Services: {summary['healthy_services']} ✅")
        print(f"Failed Services: {summary['failed_services']} ❌")
        print(f"Critical Services: {summary['critical_services']} (Required: {summary['critical_healthy']})")
        print()
        
        # Uptime Information
        returncode, stdout, stderr = self.run_ssh_command("uptime")
        if returncode == 0:
            print(f"System Uptime: {stdout.strip()}")
        
        # Load Average
        returncode, stdout, stderr = self.run_ssh_command("cat /proc/loadavg")
        if returncode == 0:
            print(f"Load Average: {stdout.strip()}")
        
        print("=" * 70)
    
    def save_report(self, report: Dict, filename: Optional[str] = None):
        """Speichert Health Report als JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/home/mdoehler/aktienanalyse-ökosystem/health_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Health Report gespeichert: {filename}")

def main():
    print("🏥 Aktienanalyse-Ökosystem Health Dashboard v1.0.0")
    print("Production Server: 10.1.1.174")
    print("=" * 70)
    
    dashboard = ServiceHealthDashboard()
    
    try:
        # Generiere Health Report
        report = dashboard.generate_health_report()
        
        # Zeige Summary
        dashboard.print_summary(report)
        
        # Speichere Report
        dashboard.save_report(report)
        
        # Exit Code basierend auf Health Status
        if report["overall_health"] in ["EXCELLENT", "GOOD"]:
            sys.exit(0)
        elif report["overall_health"] == "DEGRADED":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        print(f"❌ Health Check fehlgeschlagen: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()