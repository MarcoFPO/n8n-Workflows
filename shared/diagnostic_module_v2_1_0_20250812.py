#!/usr/bin/env python3
"""
Diagnostic Module v2.1.0 - Minimal Implementation
System Health und Diagnostic Funktionalität
Issue #65 Integration-Fix
"""

import asyncio
import json
import logging
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Fallback logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Health Check Result"""
    component: str
    status: str  # healthy, unhealthy, warning
    message: str
    details: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.details is None:
            self.details = {}


@dataclass
class SystemMetrics:
    """System Metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class DiagnosticModule:
    """
    Diagnostic Module - Minimale Implementation
    System Health Monitoring und Diagnostics
    """
    
    def __init__(self, service_name: str = "diagnostic-module"):
        self.service_name = service_name
        self.logger = logging.getLogger(f"diagnostic.{service_name}")
        self.health_checks: Dict[str, callable] = {}
        self.metrics_cache = {}
        self.last_check_time = None
        
        # Register standard health checks
        self._register_standard_health_checks()
    
    def _register_standard_health_checks(self):
        """Register Standard Health Checks"""
        self.health_checks.update({
            "system_resources": self._check_system_resources,
            "disk_space": self._check_disk_space,
            "process_health": self._check_process_health
        })
    
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check System Resources"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            status = "healthy"
            message = "System resources normal"
            
            if cpu_percent > 80:
                status = "warning"
                message = f"High CPU usage: {cpu_percent}%"
            elif cpu_percent > 95:
                status = "unhealthy"
                message = f"Critical CPU usage: {cpu_percent}%"
            
            if memory.percent > 80:
                status = "warning"
                message = f"High memory usage: {memory.percent}%"
            elif memory.percent > 95:
                status = "unhealthy"
                message = f"Critical memory usage: {memory.percent}%"
            
            return HealthCheckResult(
                component="system_resources",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "memory_total": memory.total
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component="system_resources",
                status="unhealthy",
                message=f"Resource check failed: {str(e)}"
            )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check Disk Space"""
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            status = "healthy"
            message = "Disk space normal"
            
            if disk_percent > 80:
                status = "warning" 
                message = f"High disk usage: {disk_percent:.1f}%"
            elif disk_percent > 95:
                status = "unhealthy"
                message = f"Critical disk usage: {disk_percent:.1f}%"
            
            return HealthCheckResult(
                component="disk_space",
                status=status,
                message=message,
                details={
                    "disk_percent": disk_percent,
                    "free_bytes": disk.free,
                    "total_bytes": disk.total
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component="disk_space",
                status="unhealthy",
                message=f"Disk check failed: {str(e)}"
            )
    
    async def _check_process_health(self) -> HealthCheckResult:
        """Check Process Health"""
        try:
            current_process = psutil.Process()
            
            # Basic process health indicators
            memory_info = current_process.memory_info()
            cpu_percent = current_process.cpu_percent()
            
            status = "healthy"
            message = "Process health normal"
            
            # Simple heuristics
            if memory_info.rss > 1024 * 1024 * 500:  # 500MB
                status = "warning"
                message = "High process memory usage"
            
            return HealthCheckResult(
                component="process_health",
                status=status,
                message=message,
                details={
                    "pid": current_process.pid,
                    "memory_rss": memory_info.rss,
                    "memory_vms": memory_info.vms,
                    "cpu_percent": cpu_percent,
                    "num_threads": current_process.num_threads()
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component="process_health",
                status="unhealthy",
                message=f"Process check failed: {str(e)}"
            )
    
    async def run_health_checks(self, components: List[str] = None) -> Dict[str, HealthCheckResult]:
        """Run Health Checks"""
        if components is None:
            components = list(self.health_checks.keys())
        
        results = {}
        
        for component in components:
            if component in self.health_checks:
                try:
                    result = await self.health_checks[component]()
                    results[component] = result
                    
                    self.logger.debug(f"Health check completed: {component} = {result.status}")
                except Exception as e:
                    results[component] = HealthCheckResult(
                        component=component,
                        status="unhealthy",
                        message=f"Health check failed: {str(e)}"
                    )
                    
                    self.logger.error(f"Health check failed: {component} - {str(e)}")
            else:
                results[component] = HealthCheckResult(
                    component=component,
                    status="unhealthy",
                    message=f"Unknown health check: {component}"
                )
        
        self.last_check_time = datetime.utcnow()
        return results
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get System Metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O (basic)
            network_io = {}
            try:
                net_io = psutil.net_io_counters()
                network_io = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            except:
                network_io = {"status": "unavailable"}
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=(disk.used / disk.total) * 100,
                network_io=network_io
            )
            
            # Cache metrics
            self.metrics_cache["latest"] = asdict(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {str(e)}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_io={"status": "error", "message": str(e)}
            )
    
    async def run_diagnostic_report(self) -> Dict[str, Any]:
        """Generate Comprehensive Diagnostic Report"""
        
        self.logger.info(f"Starting diagnostic report for {self.service_name}")
        
        # Run health checks
        health_results = await self.run_health_checks()
        
        # Get system metrics
        metrics = await self.get_system_metrics()
        
        # Overall health assessment
        overall_healthy = all(
            result.status in ["healthy", "warning"] 
            for result in health_results.values()
        )
        
        critical_issues = [
            result for result in health_results.values()
            if result.status == "unhealthy"
        ]
        
        report = {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "critical_issues_count": len(critical_issues),
            "health_checks": {
                name: asdict(result) for name, result in health_results.items()
            },
            "system_metrics": asdict(metrics),
            "summary": {
                "total_checks": len(health_results),
                "healthy_checks": len([r for r in health_results.values() if r.status == "healthy"]),
                "warning_checks": len([r for r in health_results.values() if r.status == "warning"]),
                "unhealthy_checks": len([r for r in health_results.values() if r.status == "unhealthy"]),
            }
        }
        
        self.logger.info(f"Diagnostic report completed: {self.service_name} = {report['overall_status']} ({len(critical_issues)} critical issues)")
        
        return report
    
    def register_health_check(self, name: str, check_func: callable):
        """Register Custom Health Check"""
        self.health_checks[name] = check_func
        self.logger.info(f"Health check registered: {name}")
    
    def get_cached_metrics(self) -> Dict[str, Any]:
        """Get Cached Metrics"""
        return self.metrics_cache.get("latest", {})