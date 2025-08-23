#!/usr/bin/env python3
"""
Continuous Monitoring Service v1.0.0
Persistent LXC Container & ML Analytics Performance Monitoring
For Container 10.1.1.174 - Production Ready
"""

import asyncio
import aiohttp
import psutil
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import os
import sys


@dataclass
class MonitoringMetrics:
    """Container and Service Monitoring Metrics"""
    timestamp: str
    container_ip: str
    
    # System Metrics
    cpu_percent: float
    memory_percent: float
    memory_usage_mb: float
    memory_available_mb: float
    load_average: List[float]
    
    # Service Metrics
    service_status: str
    service_response_time_ms: float
    service_port_accessible: bool
    
    # ML Engine Metrics
    ml_engine_status: str
    ml_models_active: int
    ml_requests_processed: int
    
    # Health Status
    overall_health: str
    alerts: List[str]


class ContinuousMonitoringService:
    """
    Continuous Monitoring Service für LXC Container 10.1.1.174
    Überwacht ML Analytics Service Performance persistent
    """
    
    def __init__(self, container_ip: str = "10.1.1.174", service_port: int = 8021):
        self.container_ip = container_ip
        self.service_port = service_port
        self.service_url = f"http://localhost:{service_port}"
        
        # Monitoring Configuration
        self.monitoring_interval = 30  # seconds
        self.health_check_interval = 10  # seconds
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "response_time_ms": 5000.0
        }
        
        # Persistent Storage
        self.metrics_log_file = "continuous_monitoring_metrics.jsonl"
        self.alerts_log_file = "continuous_monitoring_alerts.log"
        
        # Internal State
        self.metrics_history: List[MonitoringMetrics] = []
        self.alert_count = 0
        self.start_time = datetime.utcnow()
        
        # Setup Logging
        self.setup_logging()
        
        logger.info(f"Continuous Monitoring Service initialized für Container {container_ip}")
        logger.info(f"Service URL: {self.service_url}")
        logger.info(f"Monitoring Interval: {self.monitoring_interval}s")
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        global logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('continuous_monitoring.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger(__name__)
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Load Average
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_usage_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024),
                "load_average": list(load_avg)
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_usage_mb": 0.0,
                "memory_available_mb": 0.0,
                "load_average": [0.0, 0.0, 0.0]
            }
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check ML Analytics Service Health"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{self.service_url}/api/v1/classical-enhanced/status") as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "service_status": "operational",
                            "service_response_time_ms": response_time_ms,
                            "service_port_accessible": True,
                            "ml_engine_status": data.get("engine_status", {}).get("status", "unknown"),
                            "ml_models_active": data.get("engine_status", {}).get("num_enhanced_models", 0),
                            "ml_requests_processed": data.get("_request_count", 0)
                        }
                    else:
                        return {
                            "service_status": f"error_http_{response.status}",
                            "service_response_time_ms": response_time_ms,
                            "service_port_accessible": True,
                            "ml_engine_status": "unknown",
                            "ml_models_active": 0,
                            "ml_requests_processed": 0
                        }
        
        except asyncio.TimeoutError:
            return {
                "service_status": "timeout",
                "service_response_time_ms": 10000.0,
                "service_port_accessible": False,
                "ml_engine_status": "unreachable",
                "ml_models_active": 0,
                "ml_requests_processed": 0
            }
        except Exception as e:
            logger.error(f"Service health check failed: {e}")
            return {
                "service_status": f"error_{type(e).__name__}",
                "service_response_time_ms": 0.0,
                "service_port_accessible": False,
                "ml_engine_status": "error",
                "ml_models_active": 0,
                "ml_requests_processed": 0
            }
    
    def analyze_health_status(self, metrics: Dict[str, Any]) -> tuple[str, List[str]]:
        """Analyze overall health and generate alerts"""
        alerts = []
        health_status = "healthy"
        
        # CPU Threshold
        if metrics["cpu_percent"] > self.alert_thresholds["cpu_percent"]:
            alerts.append(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
            health_status = "warning"
        
        # Memory Threshold
        if metrics["memory_percent"] > self.alert_thresholds["memory_percent"]:
            alerts.append(f"High memory usage: {metrics['memory_percent']:.1f}%")
            health_status = "warning"
        
        # Response Time Threshold
        if metrics["service_response_time_ms"] > self.alert_thresholds["response_time_ms"]:
            alerts.append(f"Slow service response: {metrics['service_response_time_ms']:.1f}ms")
            health_status = "warning"
        
        # Service Down
        if not metrics["service_port_accessible"]:
            alerts.append("ML Analytics Service unreachable")
            health_status = "critical"
        
        # ML Engine Issues
        if metrics["ml_engine_status"] not in ["operational", "unknown"]:
            alerts.append(f"ML Engine status: {metrics['ml_engine_status']}")
            health_status = "warning" if health_status == "healthy" else health_status
        
        return health_status, alerts
    
    async def collect_metrics(self) -> MonitoringMetrics:
        """Collect comprehensive monitoring metrics"""
        timestamp = datetime.utcnow().isoformat()
        
        # Get System and Service Metrics
        system_metrics = await self.get_system_metrics()
        service_metrics = await self.check_service_health()
        
        # Combine metrics
        combined_metrics = {**system_metrics, **service_metrics}
        
        # Analyze Health
        health_status, alerts = self.analyze_health_status(combined_metrics)
        
        # Create Metrics Object
        metrics = MonitoringMetrics(
            timestamp=timestamp,
            container_ip=self.container_ip,
            cpu_percent=combined_metrics["cpu_percent"],
            memory_percent=combined_metrics["memory_percent"],
            memory_usage_mb=combined_metrics["memory_usage_mb"],
            memory_available_mb=combined_metrics["memory_available_mb"],
            load_average=combined_metrics["load_average"],
            service_status=combined_metrics["service_status"],
            service_response_time_ms=combined_metrics["service_response_time_ms"],
            service_port_accessible=combined_metrics["service_port_accessible"],
            ml_engine_status=combined_metrics["ml_engine_status"],
            ml_models_active=combined_metrics["ml_models_active"],
            ml_requests_processed=combined_metrics["ml_requests_processed"],
            overall_health=health_status,
            alerts=alerts
        )
        
        return metrics
    
    def log_metrics(self, metrics: MonitoringMetrics):
        """Log metrics to persistent storage"""
        # Append to JSONL file
        try:
            with open(self.metrics_log_file, 'a') as f:
                f.write(json.dumps(asdict(metrics)) + '\n')
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
        
        # Log alerts separately
        if metrics.alerts:
            try:
                with open(self.alerts_log_file, 'a') as f:
                    for alert in metrics.alerts:
                        f.write(f"{metrics.timestamp} - {alert}\n")
                self.alert_count += len(metrics.alerts)
            except Exception as e:
                logger.error(f"Failed to log alerts: {e}")
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get monitoring summary statistics"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
        
        return {
            "monitoring_duration_hours": (datetime.utcnow() - self.start_time).total_seconds() / 3600,
            "total_measurements": len(self.metrics_history),
            "total_alerts": self.alert_count,
            "current_health": recent_metrics[-1].overall_health if recent_metrics else "unknown",
            "avg_cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            "avg_memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            "avg_response_time_ms": sum(m.service_response_time_ms for m in recent_metrics) / len(recent_metrics),
            "service_uptime_percent": sum(1 for m in recent_metrics if m.service_port_accessible) / len(recent_metrics) * 100
        }
    
    async def monitoring_cycle(self):
        """Single monitoring cycle"""
        try:
            # Collect Metrics
            metrics = await self.collect_metrics()
            
            # Store in History
            self.metrics_history.append(metrics)
            
            # Keep only recent history (last 24 hours worth)
            max_history = int(24 * 3600 / self.monitoring_interval)
            if len(self.metrics_history) > max_history:
                self.metrics_history = self.metrics_history[-max_history:]
            
            # Log Metrics
            self.log_metrics(metrics)
            
            # Log Summary
            logger.info(f"Monitoring Cycle Complete:")
            logger.info(f"  Health: {metrics.overall_health}")
            logger.info(f"  CPU: {metrics.cpu_percent:.1f}%")
            logger.info(f"  Memory: {metrics.memory_percent:.1f}%")
            logger.info(f"  Service: {metrics.service_status}")
            logger.info(f"  Response: {metrics.service_response_time_ms:.1f}ms")
            
            if metrics.alerts:
                logger.warning(f"  Alerts: {', '.join(metrics.alerts)}")
        
        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")
    
    async def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        logger.info("🔍 Starting Continuous Monitoring für LXC Container 10.1.1.174")
        logger.info("============================================================")
        
        try:
            while True:
                await self.monitoring_cycle()
                await asyncio.sleep(self.monitoring_interval)
        
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring service failed: {e}")
        finally:
            # Final summary
            summary = self.get_monitoring_summary()
            logger.info("============================================================")
            logger.info("📊 CONTINUOUS MONITORING SUMMARY:")
            logger.info(f"  Duration: {summary.get('monitoring_duration_hours', 0):.2f} hours")
            logger.info(f"  Measurements: {summary.get('total_measurements', 0)}")
            logger.info(f"  Alerts: {summary.get('total_alerts', 0)}")
            logger.info(f"  Service Uptime: {summary.get('service_uptime_percent', 0):.1f}%")


async def main():
    """Main entry point"""
    monitoring_service = ContinuousMonitoringService()
    await monitoring_service.run_continuous_monitoring()


if __name__ == "__main__":
    asyncio.run(main())