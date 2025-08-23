#!/usr/bin/env python3
"""
Monitoring und Alerting System für Aktienanalyse-Ökosystem
Überwacht Pipeline-Ausführung, Service-Health und Datenqualität
"""

import subprocess
import requests
import sqlite3
import json
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys
import time

class SystemMonitor:
    """Zentrale Monitoring-Klasse"""
    
    def __init__(self):
        self.config = {
            "services": {
                "intelligent_core": "http://localhost:8011/health",
                "ml_analytics": "http://localhost:8021/health", 
                "data_processing": "http://localhost:8017/health",
                "event_bus": "http://localhost:8014/health",
                "prediction_tracking": "http://localhost:8018/health"
            },
            "database": "/opt/aktienanalyse-ökosystem/data/ki_recommendations.db",
            "logs_dir": "/opt/aktienanalyse-ökosystem/logs",
            "alert_log": "/opt/aktienanalyse-ökosystem/logs/monitoring_alerts.log"
        }
        
        # Alert-Thresholds
        self.thresholds = {
            "service_timeout": 10,  # Sekunden
            "data_freshness": 6,    # Stunden
            "min_predictions": 10,  # Minimum für heute
            "disk_usage": 85,       # Prozent
            "memory_usage": 90      # Prozent
        }
    
    def log_alert(self, level: str, message: str, details: str = ""):
        """Alert loggen"""
        timestamp = datetime.now().isoformat()
        alert_entry = f"[{timestamp}] {level.upper()}: {message}"
        if details:
            alert_entry += f" | Details: {details}"
        
        print(alert_entry)
        
        try:
            with open(self.config["alert_log"], "a") as f:
                f.write(alert_entry + "\n")
        except Exception as e:
            print(f"❌ Alert logging failed: {e}")
    
    def check_service_health(self) -> Dict[str, bool]:
        """Alle Services auf Health prüfen"""
        results = {}
        
        for service_name, health_url in self.config["services"].items():
            try:
                response = requests.get(
                    health_url,
                    timeout=self.thresholds["service_timeout"]
                )
                
                if response.status_code == 200:
                    results[service_name] = True
                    # Prüfe JSON Response für detaillierte Health-Info
                    try:
                        health_data = response.json()
                        if health_data.get("status") != "healthy":
                            self.log_alert("WARNING", 
                                f"Service {service_name} reports unhealthy status",
                                str(health_data))
                    except:
                        pass
                else:
                    results[service_name] = False
                    self.log_alert("ERROR", 
                        f"Service {service_name} health check failed",
                        f"Status: {response.status_code}")
                        
            except requests.exceptions.Timeout:
                results[service_name] = False
                self.log_alert("ERROR", 
                    f"Service {service_name} timeout",
                    f"Timeout after {self.thresholds['service_timeout']}s")
            except Exception as e:
                results[service_name] = False
                self.log_alert("ERROR", 
                    f"Service {service_name} connection failed",
                    str(e))
        
        return results
    
    def check_data_freshness(self) -> Dict[str, any]:
        """Prüfe Datenfrische in der Datenbank"""
        try:
            conn = sqlite3.connect(self.config["database"])
            cursor = conn.cursor()
            
            # Prüfe neueste Einträge
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_today,
                    MAX(created_at) as latest_entry,
                    COUNT(DISTINCT symbol) as unique_symbols
                FROM ki_recommendations 
                WHERE DATE(created_at) = DATE('now')
            """)
            
            result = cursor.fetchone()
            total_today, latest_entry, unique_symbols = result
            
            # Prüfe zeitliche Frische
            if latest_entry:
                latest_time = datetime.fromisoformat(latest_entry.replace('Z', '+00:00'))
                hours_old = (datetime.now() - latest_time.replace(tzinfo=None)).total_seconds() / 3600
                
                if hours_old > self.thresholds["data_freshness"]:
                    self.log_alert("WARNING", 
                        "Data is stale",
                        f"Latest entry: {hours_old:.1f} hours old")
            else:
                self.log_alert("ERROR", "No data entries found for today")
                hours_old = 999
            
            # Prüfe Mindestanzahl Predictions
            if total_today < self.thresholds["min_predictions"]:
                self.log_alert("WARNING", 
                    "Insufficient predictions for today",
                    f"Only {total_today} predictions (min: {self.thresholds['min_predictions']})")
            
            conn.close()
            
            return {
                "total_today": total_today,
                "unique_symbols": unique_symbols,
                "hours_since_latest": hours_old if latest_entry else None,
                "latest_entry": latest_entry,
                "is_fresh": hours_old < self.thresholds["data_freshness"] if latest_entry else False
            }
            
        except Exception as e:
            self.log_alert("ERROR", "Database check failed", str(e))
            return {"error": str(e)}
    
    def check_system_resources(self) -> Dict[str, any]:
        """System-Ressourcen prüfen"""
        try:
            # Disk Usage
            disk_result = subprocess.run(
                ["df", "/opt/aktienanalyse-ökosystem", "--output=pcent"],
                capture_output=True, text=True
            )
            
            if disk_result.returncode == 0:
                disk_usage = int(disk_result.stdout.strip().split('\n')[1].replace('%', ''))
                if disk_usage > self.thresholds["disk_usage"]:
                    self.log_alert("WARNING", 
                        f"High disk usage: {disk_usage}%",
                        f"Threshold: {self.thresholds['disk_usage']}%")
            else:
                disk_usage = None
                
            # Memory Usage
            mem_result = subprocess.run(
                ["free", "-h"], capture_output=True, text=True
            )
            memory_info = "N/A"
            if mem_result.returncode == 0:
                memory_info = mem_result.stdout
            
            return {
                "disk_usage_percent": disk_usage,
                "memory_info": memory_info
            }
            
        except Exception as e:
            self.log_alert("ERROR", "System resource check failed", str(e))
            return {"error": str(e)}
    
    def check_log_health(self) -> Dict[str, any]:
        """Log-Dateien auf Anomalien prüfen"""
        log_status = {}
        
        try:
            logs_dir = Path(self.config["logs_dir"])
            
            # Prüfe wichtige Log-Dateien
            important_logs = [
                "pipeline_automation.log",
                "health_check.log", 
                "cron_pipeline.log"
            ]
            
            for log_name in important_logs:
                log_path = logs_dir / log_name
                if log_path.exists():
                    # Prüfe Log-Größe (Warnung bei > 100MB)
                    size_mb = log_path.stat().st_size / (1024 * 1024)
                    if size_mb > 100:
                        self.log_alert("WARNING", 
                            f"Large log file: {log_name}",
                            f"Size: {size_mb:.1f}MB")
                    
                    # Prüfe auf ERROR patterns in letzten 100 Zeilen
                    try:
                        with open(log_path, 'r') as f:
                            last_lines = f.readlines()[-100:]
                            error_count = sum(1 for line in last_lines if 'ERROR' in line.upper())
                            
                            if error_count > 5:
                                self.log_alert("WARNING", 
                                    f"High error count in {log_name}",
                                    f"{error_count} errors in last 100 lines")
                    except:
                        pass
                    
                    log_status[log_name] = {
                        "exists": True,
                        "size_mb": round(size_mb, 2)
                    }
                else:
                    log_status[log_name] = {"exists": False}
                    self.log_alert("WARNING", f"Log file missing: {log_name}")
            
            return log_status
            
        except Exception as e:
            self.log_alert("ERROR", "Log health check failed", str(e))
            return {"error": str(e)}
    
    def run_full_monitoring(self) -> Dict[str, any]:
        """Vollständige Monitoring-Suite ausführen"""
        self.log_alert("INFO", "Starting full system monitoring")
        
        monitoring_results = {
            "timestamp": datetime.now().isoformat(),
            "services": self.check_service_health(),
            "data": self.check_data_freshness(),
            "system": self.check_system_resources(),
            "logs": self.check_log_health()
        }
        
        # Zusammenfassung erstellen
        healthy_services = sum(1 for status in monitoring_results["services"].values() if status)
        total_services = len(monitoring_results["services"])
        
        summary = f"Services: {healthy_services}/{total_services} healthy"
        if monitoring_results["data"].get("total_today"):
            summary += f", Predictions today: {monitoring_results['data']['total_today']}"
        
        self.log_alert("INFO", f"Monitoring completed - {summary}")
        
        return monitoring_results
    
    def generate_health_report(self) -> str:
        """Detaillierter Health-Report generieren"""
        results = self.run_full_monitoring()
        
        report = f"""
=== AKTIENANALYSE-ÖKOSYSTEM HEALTH REPORT ===
Generated: {results['timestamp']}

🔧 SERVICE STATUS:
"""
        
        for service, healthy in results["services"].items():
            status = "✅ HEALTHY" if healthy else "❌ UNHEALTHY"
            report += f"  {service}: {status}\n"
        
        if "data" in results and not results["data"].get("error"):
            data = results["data"]
            report += f"""
📊 DATA STATUS:
  Today's Predictions: {data.get('total_today', 0)}
  Unique Symbols: {data.get('unique_symbols', 0)}
  Data Freshness: {data.get('hours_since_latest', 'N/A')} hours old
  Status: {'✅ FRESH' if data.get('is_fresh') else '⚠️ STALE'}
"""
        
        if "system" in results and not results["system"].get("error"):
            system = results["system"]
            report += f"""
💻 SYSTEM RESOURCES:
  Disk Usage: {system.get('disk_usage_percent', 'N/A')}%
"""
        
        report += "\n=== END REPORT ===\n"
        
        return report

def main():
    """CLI Interface für Monitoring"""
    monitor = SystemMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "health":
            results = monitor.run_full_monitoring()
            print(json.dumps(results, indent=2))
        elif command == "report":
            report = monitor.generate_health_report()
            print(report)
        elif command == "services":
            services = monitor.check_service_health()
            for service, healthy in services.items():
                status = "HEALTHY" if healthy else "UNHEALTHY"
                print(f"{service}: {status}")
        elif command == "data":
            data = monitor.check_data_freshness()
            print(json.dumps(data, indent=2))
        else:
            print(f"Unknown command: {command}")
            print("Available commands: health, report, services, data")
    else:
        # Default: Kurzer Health-Check
        report = monitor.generate_health_report()
        print(report)

if __name__ == "__main__":
    main()