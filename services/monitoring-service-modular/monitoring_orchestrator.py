"""
Monitoring Service Modular - System-weites Monitoring für aktienanalyse-ökosystem
Orchestrator für System-Metriken, Alerts und Zabbix Integration
"""

import asyncio
import json
import logging
import os
import time
import psutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

import aiohttp
import asyncpg
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("monitoring-modular")

# Pydantic Models
class ServiceStatus(BaseModel):
    name: str
    port: int
    status: str
    response_time: Optional[float] = None
    last_check: str
    error: Optional[str] = None

class SystemMetrics(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    load_average: List[float]
    uptime_seconds: int

class AlertRule(BaseModel):
    name: str
    metric: str
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    severity: str  # critical, warning, info
    enabled: bool = True

class Alert(BaseModel):
    id: str
    rule_name: str
    message: str
    severity: str
    timestamp: str
    value: float
    threshold: float
    acknowledged: bool = False


class SystemMonitor:
    """System-Metriken Collector"""
    
    def __init__(self):
        self.last_metrics: Optional[SystemMetrics] = None
        self.metrics_history: List[SystemMetrics] = []
        self.max_history = 1000  # 1000 Messpunkte
        
    async def collect_system_metrics(self) -> SystemMetrics:
        """Sammle aktuelle System-Metriken"""
        try:
            # CPU Metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory Metrics
            memory = psutil.virtual_memory()
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Disk Metrics
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Load Average
            load_avg = os.getloadavg()
            
            # Uptime
            uptime = time.time() - psutil.boot_time()
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=round(memory_used_gb, 2),
                memory_total_gb=round(memory_total_gb, 2),
                disk_percent=disk.percent,
                disk_used_gb=round(disk_used_gb, 2),
                disk_total_gb=round(disk_total_gb, 2),
                load_average=list(load_avg),
                uptime_seconds=int(uptime)
            )
            
            # In History speichern
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            self.last_metrics = metrics
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
            raise
    
    def get_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Zusammenfassung der Metriken der letzten N Minuten"""
        if not self.metrics_history:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m.timestamp) > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            "period_minutes": minutes,
            "samples": len(recent_metrics),
            "cpu": {
                "avg": round(sum(cpu_values) / len(cpu_values), 2),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "avg": round(sum(memory_values) / len(memory_values), 2),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "latest": recent_metrics[-1].dict() if recent_metrics else None
        }


class ServiceMonitor:
    """Service Health Monitor"""
    
    def __init__(self):
        self.services = {
            "frontend": {"port": 8005, "path": "/"},
            "intelligent-core": {"port": 8011, "path": "/health"},
            "broker-gateway": {"port": 8012, "path": "/health"},
            "diagnostic": {"port": 8013, "path": "/health"},
            "event-bus": {"port": 8014, "path": "/health"}
        }
        self.last_status: Dict[str, ServiceStatus] = {}
        
    async def check_service_health(self, name: str, port: int, path: str = "/") -> ServiceStatus:
        """Prüfe Health eines einzelnen Services"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"http://localhost:{port}{path}"
                async with session.get(url) as response:
                    response_time = round((time.time() - start_time) * 1000, 2)
                    
                    status = ServiceStatus(
                        name=name,
                        port=port,
                        status="healthy" if response.status == 200 else "unhealthy",
                        response_time=response_time,
                        last_check=datetime.utcnow().isoformat()
                    )
                    
                    self.last_status[name] = status
                    return status
                    
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            status = ServiceStatus(
                name=name,
                port=port,
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.utcnow().isoformat(),
                error=str(e)
            )
            
            self.last_status[name] = status
            return status
    
    async def check_all_services(self) -> Dict[str, ServiceStatus]:
        """Prüfe alle Services parallel"""
        tasks = []
        for name, config in self.services.items():
            task = self.check_service_health(name, config["port"], config.get("path", "/"))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        service_status = {}
        for i, (name, _) in enumerate(self.services.items()):
            if isinstance(results[i], Exception):
                service_status[name] = ServiceStatus(
                    name=name,
                    port=self.services[name]["port"],
                    status="error",
                    last_check=datetime.utcnow().isoformat(),
                    error=str(results[i])
                )
            else:
                service_status[name] = results[i]
        
        return service_status


class AlertManager:
    """Alert Management System"""
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Standard-Alert-Regeln laden
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Lade Standard-Alert-Regeln"""
        default_rules = {
            "high_cpu": AlertRule(
                name="high_cpu",
                metric="cpu_percent",
                operator=">",
                threshold=80.0,
                severity="warning"
            ),
            "critical_cpu": AlertRule(
                name="critical_cpu",
                metric="cpu_percent",
                operator=">",
                threshold=95.0,
                severity="critical"
            ),
            "high_memory": AlertRule(
                name="high_memory",
                metric="memory_percent",
                operator=">",
                threshold=85.0,
                severity="warning"
            ),
            "critical_memory": AlertRule(
                name="critical_memory",
                metric="memory_percent",
                operator=">",
                threshold=95.0,
                severity="critical"
            ),
            "high_disk": AlertRule(
                name="high_disk",
                metric="disk_percent",
                operator=">",
                threshold=90.0,
                severity="warning"
            ),
            "service_down": AlertRule(
                name="service_down",
                metric="service_status",
                operator="==",
                threshold=0,  # 0 = down, 1 = up
                severity="critical"
            )
        }
        
        for rule_name, rule in default_rules.items():
            self.alert_rules[rule_name] = rule
    
    def evaluate_alerts(self, metrics: SystemMetrics, service_status: Dict[str, ServiceStatus]):
        """Evaluiere Alert-Regeln gegen aktuelle Metriken"""
        current_time = datetime.utcnow().isoformat()
        
        # System-Metriken evaluieren
        metric_values = {
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "disk_percent": metrics.disk_percent
        }
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
                
            if rule.metric == "service_status":
                # Service-Status evaluieren
                for service_name, status in service_status.items():
                    service_value = 1 if status.status == "healthy" else 0
                    if self._check_threshold(service_value, rule.operator, rule.threshold):
                        alert_id = f"{rule_name}_{service_name}"
                        if alert_id not in self.active_alerts:
                            alert = Alert(
                                id=alert_id,
                                rule_name=rule_name,
                                message=f"Service {service_name} is {status.status}",
                                severity=rule.severity,
                                timestamp=current_time,
                                value=service_value,
                                threshold=rule.threshold
                            )
                            self.active_alerts[alert_id] = alert
                            self.alert_history.append(alert)
                    else:
                        # Alert cleared
                        alert_id = f"{rule_name}_{service_name}"
                        if alert_id in self.active_alerts:
                            del self.active_alerts[alert_id]
            
            elif rule.metric in metric_values:
                # System-Metriken evaluieren
                value = metric_values[rule.metric]
                if self._check_threshold(value, rule.operator, rule.threshold):
                    if rule_name not in self.active_alerts:
                        alert = Alert(
                            id=str(uuid4()),
                            rule_name=rule_name,
                            message=f"{rule.metric} is {value}% (threshold: {rule.threshold}%)",
                            severity=rule.severity,
                            timestamp=current_time,
                            value=value,
                            threshold=rule.threshold
                        )
                        self.active_alerts[rule_name] = alert
                        self.alert_history.append(alert)
                else:
                    # Alert cleared
                    if rule_name in self.active_alerts:
                        del self.active_alerts[rule_name]
        
        # History begrenzen
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
    
    def _check_threshold(self, value: float, operator: str, threshold: float) -> bool:
        """Prüfe Threshold-Bedingung"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        return False


class MonitoringOrchestrator:
    """Hauptorchestrator für Monitoring Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Monitoring Service Modular",
            description="System-weites Monitoring für aktienanalyse-ökosystem",
            version="1.0.0"
        )
        
        # CORS aktivieren
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Module
        self.system_monitor = SystemMonitor()
        self.service_monitor = ServiceMonitor()
        self.alert_manager = AlertManager()
        
        # Background Tasks
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # API-Routen registrieren
        self._register_routes()
        
        # Startup/Shutdown Events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
    
    def _register_routes(self):
        """Registriere API-Routen"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "monitoring-modular",
                "version": "1.0.0",
                "status": "running",
                "monitoring_active": self.monitoring_active,
                "port": 8015
            }
        
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "monitoring-modular",
                "monitoring_active": self.monitoring_active,
                "uptime": "running"
            }
        
        @self.app.get("/metrics/system")
        async def get_system_metrics():
            """Aktuelle System-Metriken"""
            try:
                metrics = await self.system_monitor.collect_system_metrics()
                return metrics.dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/metrics/system/summary")
        async def get_system_summary(minutes: int = 60):
            """System-Metriken Zusammenfassung"""
            try:
                summary = self.system_monitor.get_metrics_summary(minutes)
                return summary
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/services/status")
        async def get_services_status():
            """Status aller Services"""
            try:
                status = await self.service_monitor.check_all_services()
                return {service: status[service].dict() for service in status}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/alerts")
        async def get_alerts(active_only: bool = True):
            """Aktuelle Alerts"""
            if active_only:
                return {
                    "active_alerts": {aid: alert.dict() for aid, alert in self.alert_manager.active_alerts.items()},
                    "count": len(self.alert_manager.active_alerts)
                }
            else:
                return {
                    "active_alerts": {aid: alert.dict() for aid, alert in self.alert_manager.active_alerts.items()},
                    "alert_history": [alert.dict() for alert in self.alert_manager.alert_history[-50:]],
                    "active_count": len(self.alert_manager.active_alerts),
                    "history_count": len(self.alert_manager.alert_history)
                }
        
        @self.app.get("/alerts/rules")
        async def get_alert_rules():
            """Alert-Regeln"""
            return {
                "rules": {name: rule.dict() for name, rule in self.alert_manager.alert_rules.items()},
                "count": len(self.alert_manager.alert_rules)
            }
        
        @self.app.post("/alerts/rules")
        async def add_alert_rule(rule: AlertRule):
            """Alert-Regel hinzufügen"""
            self.alert_manager.alert_rules[rule.name] = rule
            return {"status": "added", "rule_name": rule.name}
        
        @self.app.get("/dashboard")
        async def get_dashboard():
            """Monitoring-Dashboard Daten"""
            try:
                # System-Metriken sammeln
                system_metrics = await self.system_monitor.collect_system_metrics()
                
                # Service-Status prüfen
                service_status = await self.service_monitor.check_all_services()
                
                # Alerts evaluieren
                self.alert_manager.evaluate_alerts(system_metrics, service_status)
                
                # Dashboard zusammenstellen
                healthy_services = sum(1 for s in service_status.values() if s.status == "healthy")
                total_services = len(service_status)
                
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "system": system_metrics.dict(),
                    "services": {
                        "healthy": healthy_services,
                        "total": total_services,
                        "details": {name: status.dict() for name, status in service_status.items()}
                    },
                    "alerts": {
                        "active": len(self.alert_manager.active_alerts),
                        "critical": len([a for a in self.alert_manager.active_alerts.values() if a.severity == "critical"]),
                        "warning": len([a for a in self.alert_manager.active_alerts.values() if a.severity == "warning"]),
                        "details": {aid: alert.dict() for aid, alert in self.alert_manager.active_alerts.items()}
                    },
                    "monitoring_active": self.monitoring_active
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/monitoring/start")
        async def start_monitoring():
            """Monitoring starten"""
            if not self.monitoring_active:
                self.monitoring_active = True
                self.monitoring_task = asyncio.create_task(self._monitoring_loop())
                return {"status": "started", "monitoring_active": True}
            return {"status": "already_running", "monitoring_active": True}
        
        @self.app.post("/monitoring/stop")
        async def stop_monitoring():
            """Monitoring stoppen"""
            if self.monitoring_active:
                self.monitoring_active = False
                if self.monitoring_task:
                    self.monitoring_task.cancel()
                return {"status": "stopped", "monitoring_active": False}
            return {"status": "already_stopped", "monitoring_active": False}
    
    async def _monitoring_loop(self):
        """Background Monitoring Loop"""
        logger.info("Starting monitoring loop...")
        
        while self.monitoring_active:
            try:
                # System-Metriken sammeln
                system_metrics = await self.system_monitor.collect_system_metrics()
                
                # Service-Status prüfen
                service_status = await self.service_monitor.check_all_services()
                
                # Alerts evaluieren
                self.alert_manager.evaluate_alerts(system_metrics, service_status)
                
                logger.debug("Monitoring cycle completed",
                           cpu=system_metrics.cpu_percent,
                           memory=system_metrics.memory_percent,
                           services_healthy=sum(1 for s in service_status.values() if s.status == "healthy"),
                           active_alerts=len(self.alert_manager.active_alerts))
                
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
            
            # Warten bis zum nächsten Zyklus (30 Sekunden)
            await asyncio.sleep(30)
        
        logger.info("Monitoring loop stopped")
    
    async def startup_event(self):
        """Service startup"""
        try:
            logger.info("Starting Monitoring Service Modular...")
            
            # Monitoring automatisch starten
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("Monitoring Service Modular started successfully",
                       monitoring_active=self.monitoring_active)
            
        except Exception as e:
            logger.error("Failed to start Monitoring Service", error=str(e))
            raise RuntimeError("Service initialization failed")
    
    async def shutdown_event(self):
        """Service shutdown"""
        try:
            logger.info("Shutting down Monitoring Service Modular...")
            
            # Monitoring stoppen
            self.monitoring_active = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Monitoring Service Modular shut down successfully")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


def main():
    """Main entry point"""
    orchestrator = MonitoringOrchestrator()
    
    # Uvicorn-Server konfiguration
    config = uvicorn.Config(
        app=orchestrator.app,
        host="0.0.0.0",
        port=8015,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    logger.info("Monitoring Service Modular starting on port 8015...")
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Monitoring Service stopped by user")
    except Exception as e:
        logger.error("Monitoring Service crashed", error=str(e))
        raise


if __name__ == "__main__":
    main()