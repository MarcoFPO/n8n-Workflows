#!/usr/bin/env python3
"""
Service Health Dashboard v1.0.0 - 25. August 2025
===================================================

Comprehensive Service Health Monitoring für Aktienanalyse-Ökosystem
- Real-time Service Status Monitoring
- Health Check Integration
- Performance Metrics Collection
- Migration Status Tracking
"""

import asyncio
import aiohttp
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

class ServiceHealthDashboard:
    def __init__(self):
        self.services = {
            # Vollständig migrierte Services
            "frontend": {
                "name": "aktienanalyse-frontend.service",
                "health_url": "http://10.1.1.174:8080/health",
                "status": "migrated",
                "description": "Frontend Service - Clean Architecture"
            },
            "data-processing": {
                "name": "aktienanalyse-data-processing-v6.service", 
                "health_url": "http://10.1.1.174:8013/health",
                "status": "migrated",
                "description": "Data Processing Service - Clean Architecture"
            },
            
            # Erfolgreich reparierte Services
            "prediction-tracking": {
                "name": "aktienanalyse-prediction-tracking-v6.service",
                "health_url": "http://10.1.1.174:8012/health", 
                "status": "repaired",
                "description": "Prediction Tracking - Clean Architecture"
            },
            
            # Stabile nicht-migrierte Services
            "broker-gateway": {
                "name": "aktienanalyse-broker-gateway-eventbus-first.service",
                "health_url": "http://10.1.1.174:8001/health",
                "status": "stable",
                "description": "Broker Gateway - Event-Bus-First"
            },
            "intelligent-core": {
                "name": "aktienanalyse-intelligent-core-eventbus-first.service",
                "health_url": "http://10.1.1.174:8002/health",
                "status": "stable", 
                "description": "Intelligent Core - Event-Bus-First"
            },
            "monitoring": {
                "name": "aktienanalyse-monitoring-modular.service",
                "health_url": "http://10.1.1.174:8000/health",
                "status": "stable",
                "description": "Monitoring Service - Modular"
            },
            
            # Problematische Services
            "ml-analytics": {
                "name": "aktienanalyse-ml-analytics-v6.service",
                "health_url": "http://10.1.1.174:8011/health",
                "status": "failing",
                "description": "ML Analytics - Database Issues"
            },
            "event-bus": {
                "name": "aktienanalyse-event-bus-v6.service", 
                "health_url": "http://10.1.1.174:8014/health",
                "status": "failing",
                "description": "Event Bus - Runtime Issues"
            },
            "diagnostic": {
                "name": "aktienanalyse-diagnostic-v6.service",
                "health_url": "http://10.1.1.174:8015/health", 
                "status": "unknown",
                "description": "Diagnostic Service"
            },
            "marketcap": {
                "name": "aktienanalyse-marketcap-v6.service",
                "health_url": "http://10.1.1.174:8016/health",
                "status": "unknown", 
                "description": "MarketCap Service"
            }
        }
        
    async def check_systemctl_status(self, service_name: str) -> dict:
        """Check systemctl status for service"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True, text=True
            )
            active = result.stdout.strip() == 'active'
            
            if active:
                # Get detailed status
                status_result = subprocess.run(
                    ['systemctl', 'status', service_name, '--no-pager', '-l'],
                    capture_output=True, text=True
                )
                return {
                    "active": True,
                    "status": "running",
                    "details": status_result.stdout
                }
            else:
                return {
                    "active": False, 
                    "status": result.stdout.strip(),
                    "details": f"Service {service_name} is not active"
                }
                
        except Exception as e:
            return {
                "active": False,
                "status": "error",
                "details": f"Failed to check status: {str(e)}"
            }
    
    async def check_health_endpoint(self, url: str) -> dict:
        """Check service health endpoint"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "healthy": True,
                            "status_code": response.status,
                            "data": data
                        }
                    else:
                        return {
                            "healthy": False,
                            "status_code": response.status,
                            "data": await response.text()
                        }
        except Exception as e:
            return {
                "healthy": False,
                "status_code": 0,
                "error": str(e)
            }
    
    async def generate_health_report(self) -> dict:
        """Generate comprehensive health report"""
        print("🔍 Generating Service Health Report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "summary": {
                "total_services": len(self.services),
                "active_services": 0,
                "healthy_services": 0,
                "migrated_services": 0,
                "failing_services": 0
            }
        }
        
        # Check each service
        for service_key, service_config in self.services.items():
            print(f"📊 Checking {service_key}...")
            
            # Check systemctl status
            systemctl_status = await self.check_systemctl_status(service_config["name"])
            
            # Check health endpoint if service is active
            health_status = {"healthy": False, "error": "Service not active"}
            if systemctl_status["active"]:
                health_status = await self.check_health_endpoint(service_config["health_url"])
            
            # Combine results
            service_report = {
                "name": service_config["name"],
                "description": service_config["description"],
                "migration_status": service_config["status"],
                "systemctl": systemctl_status,
                "health": health_status,
                "overall_status": "healthy" if (systemctl_status["active"] and health_status["healthy"]) else "unhealthy"
            }
            
            report["services"][service_key] = service_report
            
            # Update summary
            if systemctl_status["active"]:
                report["summary"]["active_services"] += 1
            if health_status["healthy"]:
                report["summary"]["healthy_services"] += 1
            if service_config["status"] == "migrated":
                report["summary"]["migrated_services"] += 1
            if service_config["status"] == "failing":
                report["summary"]["failing_services"] += 1
        
        return report
    
    def print_dashboard(self, report: dict):
        """Print formatted dashboard"""
        print("\\n" + "=" * 80)
        print("🎯 AKTIENANALYSE SERVICE HEALTH DASHBOARD")
        print("=" * 80)
        print(f"📅 Report Time: {report['timestamp']}")
        print()
        
        # Summary
        summary = report["summary"]
        print("📊 SYSTEM OVERVIEW:")
        print(f"   Total Services: {summary['total_services']}")
        print(f"   🟢 Active Services: {summary['active_services']}")
        print(f"   ❤️  Healthy Services: {summary['healthy_services']}")
        print(f"   🚀 Migrated Services: {summary['migrated_services']}")
        print(f"   ❌ Failing Services: {summary['failing_services']}")
        print()
        
        # Service details
        print("🔍 SERVICE DETAILS:")
        print("-" * 80)
        
        for service_key, service_data in report["services"].items():
            status_icon = "🟢" if service_data["overall_status"] == "healthy" else "🔴"
            migration_icon = {
                "migrated": "🚀",
                "repaired": "🔧", 
                "stable": "✅",
                "failing": "❌",
                "unknown": "❓"
            }.get(service_data["migration_status"], "❓")
            
            print(f"{status_icon} {migration_icon} {service_key.upper()}")
            print(f"   Service: {service_data['name']}")
            print(f"   Status: {service_data['systemctl']['status']}")
            print(f"   Health: {'OK' if service_data['health']['healthy'] else 'FAIL'}")
            print(f"   Migration: {service_data['migration_status']}")
            print()
        
        print("=" * 80)
        
        # Success rate calculation
        success_rate = (summary["healthy_services"] / summary["total_services"]) * 100
        migration_rate = (summary["migrated_services"] / summary["total_services"]) * 100
        
        print(f"🎯 SYSTEM HEALTH: {success_rate:.1f}% ({summary['healthy_services']}/{summary['total_services']} services healthy)")
        print(f"🚀 MIGRATION PROGRESS: {migration_rate:.1f}% ({summary['migrated_services']}/{summary['total_services']} services migrated)")
        
        if success_rate >= 75:
            print("✅ SYSTEM STATUS: PRODUCTION READY")
        elif success_rate >= 50:
            print("⚠️  SYSTEM STATUS: PARTIALLY OPERATIONAL")
        else:
            print("❌ SYSTEM STATUS: NEEDS ATTENTION")
    
    def save_report(self, report: dict, filename: str = None):
        """Save report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"service_health_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Report saved: {filename}")
    
    async def run_dashboard(self):
        """Run complete dashboard"""
        print("🚀 AKTIENANALYSE SERVICE HEALTH DASHBOARD v1.0.0")
        print("=" * 60)
        
        # Generate report
        report = await self.generate_health_report()
        
        # Display dashboard
        self.print_dashboard(report)
        
        # Save report
        self.save_report(report)
        
        return report

async def main():
    dashboard = ServiceHealthDashboard()
    report = await dashboard.run_dashboard()
    return report

if __name__ == "__main__":
    asyncio.run(main())