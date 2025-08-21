#!/usr/bin/env python3
"""
LXC Production Monitoring System - Health Checks für 10.1.1.174
================================================================

Production-ready monitoring system für ML Analytics Service auf LXC
Comprehensive health checks, performance monitoring, alerting

Features:
- Service Health Monitoring
- Performance Metrics Collection
- Automated Alerting System
- LXC Resource Monitoring
- ML Engine Status Tracking
- Production Dashboard

Author: Claude Code & Production Monitoring Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LXCProductionMonitor:
    """Production Monitoring für LXC ML Analytics Service"""
    
    def __init__(self, container_ip: str = "10.1.1.174", service_port: int = 8021):
        self.container_ip = container_ip
        self.service_port = service_port
        self.base_url = f"http://{container_ip}:{service_port}"
        
        # Monitoring configuration
        self.check_interval = 30  # seconds
        self.alert_thresholds = {
            "response_time_ms": 5000,      # 5 seconds
            "memory_usage_percent": 80,    # 80%
            "cpu_usage_percent": 90,       # 90%
            "error_rate_percent": 5,       # 5% error rate
            "uptime_hours": 24             # Alert if down for >24h
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.health_history = []
        self.performance_history = []
        self.alerts = []
        
        # Endpoints to monitor
        self.endpoints = {
            "health": "/health",
            "ml_status": "/api/v1/classical-enhanced/status",
            "portfolio_optimization": "/api/v1/classical-enhanced/vce/portfolio-optimization",
            "qiaoa_optimization": "/api/v1/classical-enhanced/qiaoa/optimization"
        }
        
        logger.info(f"Production Monitor initialized for LXC {container_ip}:{service_port}")
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check service health status"""
        start_time = time.time()
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "container_ip": self.container_ip,
            "service_port": self.service_port,
            "endpoints": {},
            "overall_status": "healthy",
            "response_time_ms": 0,
            "errors": []
        }
        
        # Check each endpoint
        for endpoint_name, endpoint_path in self.endpoints.items():
            endpoint_url = f"{self.base_url}{endpoint_path}"
            endpoint_status = {
                "url": endpoint_url,
                "status": "unknown",
                "response_time_ms": 0,
                "status_code": None,
                "error": None
            }
            
            try:
                response_start = time.time()
                
                if endpoint_name in ["portfolio_optimization", "qiaoa_optimization"]:
                    # POST endpoints - send test data
                    if endpoint_name == "portfolio_optimization":
                        test_data = {
                            "expected_returns": [0.1, 0.08, 0.12],
                            "covariance_matrix": [[0.01, 0.002, 0.003], [0.002, 0.015, 0.001], [0.003, 0.001, 0.02]],
                            "risk_tolerance": 0.5
                        }
                    else:  # qiaoa_optimization
                        test_data = {
                            "cost_matrix": [[0, 1, 2], [1, 0, 1], [2, 1, 0]],
                            "num_layers": 2
                        }
                    
                    response = requests.post(
                        endpoint_url,
                        json=test_data,
                        timeout=10,
                        headers={"Content-Type": "application/json"}
                    )
                else:
                    # GET endpoints
                    response = requests.get(endpoint_url, timeout=10)
                
                response_time = (time.time() - response_start) * 1000
                endpoint_status.update({
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response_time,
                    "status_code": response.status_code
                })
                
                if response.status_code != 200:
                    endpoint_status["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                    health_status["errors"].append(f"{endpoint_name}: HTTP {response.status_code}")
                    health_status["overall_status"] = "degraded"
                
            except requests.exceptions.Timeout:
                endpoint_status.update({
                    "status": "timeout",
                    "error": "Request timeout"
                })
                health_status["errors"].append(f"{endpoint_name}: timeout")
                health_status["overall_status"] = "unhealthy"
                
            except requests.exceptions.ConnectionError:
                endpoint_status.update({
                    "status": "connection_error",
                    "error": "Connection failed"
                })
                health_status["errors"].append(f"{endpoint_name}: connection failed")
                health_status["overall_status"] = "unhealthy"
                
            except Exception as e:
                endpoint_status.update({
                    "status": "error",
                    "error": str(e)
                })
                health_status["errors"].append(f"{endpoint_name}: {str(e)}")
                health_status["overall_status"] = "unhealthy"
            
            health_status["endpoints"][endpoint_name] = endpoint_status
        
        # Calculate overall response time
        total_response_time = (time.time() - start_time) * 1000
        health_status["response_time_ms"] = total_response_time
        
        return health_status
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "usage_percent": memory.percent,
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory.available / (1024 * 1024),
                    "used_mb": memory.used / (1024 * 1024)
                },
                "disk": {
                    "usage_percent": (disk.used / disk.total) * 100,
                    "total_gb": disk.total / (1024 ** 3),
                    "free_gb": disk.free / (1024 ** 3),
                    "used_gb": disk.used / (1024 ** 3)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
        except Exception as e:
            logger.error(f"Error checking system resources: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def check_lxc_container_status(self) -> Dict[str, Any]:
        """Check LXC container specific status"""
        container_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "container_ip": self.container_ip,
            "status": "unknown",
            "connectivity": False,
            "ssh_accessible": False,
            "error": None
        }
        
        try:
            # Check ping connectivity
            ping_result = subprocess.run(
                ["ping", "-c", "2", "-W", "5", self.container_ip],
                capture_output=True,
                timeout=15
            )
            
            container_status["connectivity"] = ping_result.returncode == 0
            
            if container_status["connectivity"]:
                container_status["status"] = "online"
                
                # Check SSH accessibility (optional)
                try:
                    ssh_result = subprocess.run(
                        ["nc", "-z", "-w", "3", self.container_ip, "22"],
                        capture_output=True,
                        timeout=10
                    )
                    container_status["ssh_accessible"] = ssh_result.returncode == 0
                except:
                    container_status["ssh_accessible"] = False
            else:
                container_status["status"] = "offline"
                container_status["error"] = "Container not reachable"
                
        except subprocess.TimeoutExpired:
            container_status["status"] = "timeout"
            container_status["error"] = "Connection timeout"
        except Exception as e:
            container_status["status"] = "error"
            container_status["error"] = str(e)
        
        return container_status
    
    def generate_alerts(self, health_check: Dict[str, Any], resource_check: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on monitoring data"""
        alerts = []
        timestamp = datetime.utcnow().isoformat()
        
        # Service health alerts
        if health_check["overall_status"] == "unhealthy":
            alerts.append({
                "level": "critical",
                "type": "service_down",
                "message": f"ML Analytics Service is unhealthy: {', '.join(health_check['errors'])}",
                "timestamp": timestamp,
                "details": health_check
            })
        elif health_check["overall_status"] == "degraded":
            alerts.append({
                "level": "warning",
                "type": "service_degraded",
                "message": f"ML Analytics Service degraded: {', '.join(health_check['errors'])}",
                "timestamp": timestamp,
                "details": health_check
            })
        
        # Response time alerts
        if health_check["response_time_ms"] > self.alert_thresholds["response_time_ms"]:
            alerts.append({
                "level": "warning",
                "type": "slow_response",
                "message": f"Service response time high: {health_check['response_time_ms']:.1f}ms > {self.alert_thresholds['response_time_ms']}ms",
                "timestamp": timestamp,
                "details": {"response_time_ms": health_check["response_time_ms"]}
            })
        
        # Resource usage alerts
        if "error" not in resource_check:
            if resource_check["memory"]["usage_percent"] > self.alert_thresholds["memory_usage_percent"]:
                alerts.append({
                    "level": "warning",
                    "type": "high_memory_usage",
                    "message": f"Memory usage high: {resource_check['memory']['usage_percent']:.1f}% > {self.alert_thresholds['memory_usage_percent']}%",
                    "timestamp": timestamp,
                    "details": resource_check["memory"]
                })
            
            if resource_check["cpu"]["usage_percent"] > self.alert_thresholds["cpu_usage_percent"]:
                alerts.append({
                    "level": "warning",
                    "type": "high_cpu_usage",
                    "message": f"CPU usage high: {resource_check['cpu']['usage_percent']:.1f}% > {self.alert_thresholds['cpu_usage_percent']}%",
                    "timestamp": timestamp,
                    "details": resource_check["cpu"]
                })
        
        return alerts
    
    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run single monitoring cycle"""
        logger.info("Running monitoring cycle...")
        
        # Perform checks
        health_check = await self.check_service_health()
        resource_check = self.check_system_resources()
        container_check = self.check_lxc_container_status()
        
        # Generate alerts
        new_alerts = self.generate_alerts(health_check, resource_check)
        self.alerts.extend(new_alerts)
        
        # Store history
        monitoring_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "health_check": health_check,
            "resource_check": resource_check,
            "container_check": container_check,
            "alerts": new_alerts,
            "monitoring_summary": {
                "overall_status": health_check["overall_status"],
                "container_status": container_check["status"],
                "new_alerts": len(new_alerts),
                "total_alerts": len(self.alerts)
            }
        }
        
        self.health_history.append(monitoring_result)
        
        # Keep only last 100 records
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        return monitoring_result
    
    async def start_continuous_monitoring(self):
        """Start continuous monitoring"""
        logger.info(f"Starting continuous monitoring (interval: {self.check_interval}s)")
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                result = await self.run_monitoring_cycle()
                
                # Log important events
                if result["alerts"]:
                    logger.warning(f"New alerts generated: {len(result['alerts'])}")
                    for alert in result["alerts"]:
                        logger.warning(f"{alert['level'].upper()}: {alert['message']}")
                
                if result["monitoring_summary"]["overall_status"] != "healthy":
                    logger.error(f"Service status: {result['monitoring_summary']['overall_status']}")
                
                # Save monitoring data
                self.save_monitoring_data(result)
                
                # Wait for next cycle
                await asyncio.sleep(self.check_interval)
                
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
            self.monitoring_active = False
    
    def save_monitoring_data(self, monitoring_result: Dict[str, Any]):
        """Save monitoring data to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lxc_monitoring_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(monitoring_result, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving monitoring data: {str(e)}")
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        if not self.health_history:
            return {"error": "No monitoring data available"}
        
        # Calculate uptime statistics
        total_checks = len(self.health_history)
        healthy_checks = sum(1 for h in self.health_history if h["health_check"]["overall_status"] == "healthy")
        uptime_percentage = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # Calculate average response times
        response_times = [h["health_check"]["response_time_ms"] for h in self.health_history]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Alert summary
        critical_alerts = [a for a in self.alerts if a["level"] == "critical"]
        warning_alerts = [a for a in self.alerts if a["level"] == "warning"]
        
        # Recent status
        latest_check = self.health_history[-1] if self.health_history else None
        
        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "monitoring_period": {
                "start": self.health_history[0]["timestamp"] if self.health_history else None,
                "end": self.health_history[-1]["timestamp"] if self.health_history else None,
                "total_checks": total_checks
            },
            "uptime_statistics": {
                "uptime_percentage": uptime_percentage,
                "healthy_checks": healthy_checks,
                "total_checks": total_checks
            },
            "performance_statistics": {
                "avg_response_time_ms": avg_response_time,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0
            },
            "alert_summary": {
                "total_alerts": len(self.alerts),
                "critical_alerts": len(critical_alerts),
                "warning_alerts": len(warning_alerts)
            },
            "current_status": latest_check["monitoring_summary"] if latest_check else None,
            "container_info": {
                "ip": self.container_ip,
                "port": self.service_port,
                "monitored_endpoints": len(self.endpoints)
            }
        }
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        logger.info("Stopping monitoring...")
        self.monitoring_active = False

async def main():
    """Main monitoring function"""
    print("🔍 LXC Production Monitoring System")
    print("🔧 Monitoring ML Analytics Service on LXC 10.1.1.174")
    print("=" * 60)
    
    # Initialize monitor
    monitor = LXCProductionMonitor()
    
    try:
        print("Running initial health check...")
        initial_check = await monitor.run_monitoring_cycle()
        
        print("\n📊 Initial Health Check Results:")
        print(f"   Overall Status: {initial_check['monitoring_summary']['overall_status']}")
        print(f"   Container Status: {initial_check['monitoring_summary']['container_status']}")
        print(f"   Response Time: {initial_check['health_check']['response_time_ms']:.1f}ms")
        
        if initial_check['alerts']:
            print(f"   ⚠️  {len(initial_check['alerts'])} alerts generated")
            for alert in initial_check['alerts']:
                print(f"      {alert['level'].upper()}: {alert['message']}")
        else:
            print("   ✅ No alerts")
        
        # Ask user if they want continuous monitoring
        print("\n🔄 Continuous monitoring available")
        response = input("   Start continuous monitoring? (y/N): ")
        
        if response.lower() == 'y':
            print(f"   Starting continuous monitoring (interval: {monitor.check_interval}s)")
            print("   Press Ctrl+C to stop monitoring")
            
            await monitor.start_continuous_monitoring()
        else:
            print("   Single check complete. Monitoring stopped.")
        
        # Generate final report
        report = monitor.generate_monitoring_report()
        
        print("\n📋 Final Monitoring Report:")
        print(f"   Total Checks: {report['uptime_statistics']['total_checks']}")
        print(f"   Uptime: {report['uptime_statistics']['uptime_percentage']:.1f}%")
        print(f"   Avg Response: {report['performance_statistics']['avg_response_time_ms']:.1f}ms")
        print(f"   Total Alerts: {report['alert_summary']['total_alerts']}")
        
        # Save report
        report_file = f"lxc_monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📁 Report saved to: {report_file}")
        print("✅ LXC Production Monitoring Complete!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Monitoring interrupted by user")
        monitor.stop_monitoring()
    except Exception as e:
        logger.error(f"Monitoring failed: {str(e)}")
        print(f"❌ Monitoring failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())