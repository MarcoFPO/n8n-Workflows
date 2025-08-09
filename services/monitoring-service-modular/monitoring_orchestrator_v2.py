#!/usr/bin/env python3
"""
Modernisierter Monitoring Service v2
Verwendet shared libraries und eliminiert Code-Duplikation
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Shared Libraries Import (eliminiert Code-Duplikation)
from shared import (
    # Basis-Klassen
    ModularService, DatabaseMixin, EventBusMixin, LoggerMixin,
    # Standard-Imports
    datetime, timedelta, Dict, Any, Optional, List,
    FastAPI, HTTPException, BackgroundTasks, BaseModel, Field,
    # Security & Logging
    SecurityConfig, setup_logging,
    # Utilities
    get_current_timestamp, safe_get_env, safe_json_loads
)

# System-Monitoring Imports
import psutil
import aiohttp
import subprocess
from uuid import uuid4

# Environment laden
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')


class SystemMetrics(BaseModel):
    """System-Metriken Model"""
    timestamp: datetime = Field(default_factory=get_current_timestamp)
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]


class ServiceStatus(BaseModel):
    """Service-Status Model"""
    service_name: str
    status: str
    port: int
    health_url: str
    last_check: datetime = Field(default_factory=get_current_timestamp)
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class AlertRule(BaseModel):
    """Alert-Regel Model"""
    rule_id: str
    metric_name: str
    threshold: float
    operator: str  # >, <, ==, !=
    severity: str  # critical, warning, info
    enabled: bool = True


class MonitoringService(ModularService, DatabaseMixin, EventBusMixin, LoggerMixin):
    """
    Modernisierter Monitoring Service
    Verwendet shared libraries für bessere Code-Qualität
    """
    
    def __init__(self):
        # Service-Initialisierung über BaseService
        super().__init__(
            service_name="monitoring",
            version="2.0.0", 
            port=SecurityConfig.get_service_port("monitoring")
        )
        
        # Monitoring-spezifische Konfiguration
        self.services_to_monitor = {
            "frontend": {
                "port": SecurityConfig.get_service_port("frontend"),
                "health_endpoint": "/health"
            },
            "intelligent-core": {
                "port": SecurityConfig.get_service_port("intelligent_core"),
                "health_endpoint": "/health"
            },
            "broker-gateway": {
                "port": SecurityConfig.get_service_port("broker_gateway"),
                "health_endpoint": "/health"
            },
            "diagnostic": {
                "port": SecurityConfig.get_service_port("diagnostic"),
                "health_endpoint": "/health"
            },
            "event-bus": {
                "port": SecurityConfig.get_service_port("event_bus"),
                "health_endpoint": "/health"
            }
        }
        
        # Alert-Regeln
        self.alert_rules = [
            AlertRule(
                rule_id="cpu_high",
                metric_name="cpu_percent",
                threshold=80.0,
                operator=">",
                severity="warning"
            ),
            AlertRule(
                rule_id="memory_high", 
                metric_name="memory_percent",
                threshold=85.0,
                operator=">",
                severity="critical"
            ),
            AlertRule(
                rule_id="disk_high",
                metric_name="disk_percent", 
                threshold=90.0,
                operator=">",
                severity="critical"
            )
        ]
        
        # Monitoring State
        self.current_metrics: Optional[SystemMetrics] = None
        self.service_statuses: Dict[str, ServiceStatus] = {}
        self.active_alerts: List[Dict[str, Any]] = []
    
    async def _setup_service(self):
        """Service-spezifische Initialisierung"""
        # Database Connections
        await self.setup_postgres()
        await self.setup_redis()
        
        # Event-Bus Connection
        await self.setup_event_bus("monitoring")
        
        # API Routes registrieren
        self._setup_api_routes()
        
        # Background Tasks starten
        self._start_background_monitoring()
        
        self.logger.info("Monitoring Service v2 fully initialized")
    
    def _setup_api_routes(self):
        """API Routes registrieren"""
        
        @self.app.get("/api/v2/metrics/system")
        async def get_system_metrics():
            """Aktuelle System-Metriken abrufen"""
            if not self.current_metrics:
                await self._collect_system_metrics()
            
            return self.current_metrics
        
        @self.app.get("/api/v2/services/status")
        async def get_services_status():
            """Status aller Services abrufen"""
            return {
                "services": self.service_statuses,
                "total_services": len(self.services_to_monitor),
                "healthy_services": len([s for s in self.service_statuses.values() if s.status == "healthy"]),
                "last_check": get_current_timestamp().isoformat()
            }
        
        @self.app.get("/api/v2/alerts/active")
        async def get_active_alerts():
            """Aktive Alerts abrufen"""
            return {
                "alerts": self.active_alerts,
                "total_alerts": len(self.active_alerts),
                "critical_alerts": len([a for a in self.active_alerts if a.get("severity") == "critical"]),
                "timestamp": get_current_timestamp().isoformat()
            }
        
        @self.app.post("/api/v2/alerts/rules")
        async def add_alert_rule(rule: AlertRule):
            """Neue Alert-Regel hinzufügen"""
            self.alert_rules.append(rule)
            self.logger.info(f"Alert rule added: {rule.rule_id}")
            return {"status": "success", "rule_id": rule.rule_id}
        
        @self.app.get("/api/v2/health/detailed")
        async def detailed_health_check():
            """Detaillierter Health-Check"""
            system_metrics = await self._collect_system_metrics()
            service_health = await self._check_all_services()
            
            return {
                "service": "monitoring-v2",
                "status": "healthy",
                "timestamp": get_current_timestamp().isoformat(),
                "system_metrics": system_metrics.dict(),
                "services": service_health,
                "alerts": {
                    "active": len(self.active_alerts),
                    "rules": len(self.alert_rules)
                },
                "database": {
                    "postgres": self.db_pool is not None,
                    "redis": self.redis_client is not None
                },
                "event_bus": self.event_bus is not None
            }
    
    def _start_background_monitoring(self):
        """Background Monitoring Tasks starten"""
        import asyncio
        
        # System-Metriken alle 30 Sekunden sammeln
        asyncio.create_task(self._metrics_collection_loop())
        
        # Service Health-Checks alle 60 Sekunden
        asyncio.create_task(self._service_health_loop())
        
        # Alert-Checking alle 15 Sekunden
        asyncio.create_task(self._alert_checking_loop())
    
    async def _metrics_collection_loop(self):
        """Kontinuierliche System-Metriken-Sammlung"""
        while True:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(30)  # 30 Sekunden Intervall
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)  # Längere Pause bei Fehlern
    
    async def _service_health_loop(self):
        """Kontinuierliche Service Health-Checks"""  
        while True:
            try:
                await self._check_all_services()
                await asyncio.sleep(60)  # 60 Sekunden Intervall
            except Exception as e:
                self.logger.error(f"Service health check error: {e}")
                await asyncio.sleep(90)  # Längere Pause bei Fehlern
    
    async def _alert_checking_loop(self):
        """Kontinuierliche Alert-Überprüfung"""
        while True:
            try:
                await self._check_alerts()
                await asyncio.sleep(15)  # 15 Sekunden Intervall
            except Exception as e:
                self.logger.error(f"Alert checking error: {e}")
                await asyncio.sleep(30)  # Längere Pause bei Fehlern
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """System-Metriken sammeln"""
        try:
            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory Usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk Usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
            # Process Count
            process_count = len(psutil.pids())
            
            # Load Average
            load_average = list(psutil.getloadavg())
            
            self.current_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                load_average=load_average
            )
            
            return self.current_metrics
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            raise
    
    async def _check_all_services(self) -> Dict[str, ServiceStatus]:
        """Alle Services auf Health prüfen"""
        async with aiohttp.ClientSession() as session:
            for service_name, config in self.services_to_monitor.items():
                await self._check_service_health(session, service_name, config)
        
        return self.service_statuses
    
    async def _check_service_health(self, session: aiohttp.ClientSession, service_name: str, config: Dict[str, Any]):
        """Einzelnen Service auf Health prüfen"""
        port = config["port"]
        health_endpoint = config["health_endpoint"]
        health_url = f"http://localhost:{port}{health_endpoint}"
        
        start_time = get_current_timestamp()
        
        try:
            async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                end_time = get_current_timestamp()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    status = "healthy"
                    error_message = None
                else:
                    status = "unhealthy"
                    error_message = f"HTTP {response.status}"
                
        except Exception as e:
            end_time = get_current_timestamp()
            response_time = (end_time - start_time).total_seconds() * 1000
            status = "unreachable"
            error_message = str(e)
        
        self.service_statuses[service_name] = ServiceStatus(
            service_name=service_name,
            status=status,
            port=port,
            health_url=health_url,
            response_time_ms=response_time,
            error_message=error_message
        )
    
    async def _check_alerts(self):
        """Alert-Regeln überprüfen"""
        if not self.current_metrics:
            return
        
        current_alerts = []
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            # Metrik-Wert abrufen
            metric_value = getattr(self.current_metrics, rule.metric_name, None)
            if metric_value is None:
                continue
            
            # Alert-Bedingung prüfen
            alert_triggered = self._evaluate_alert_condition(
                metric_value, rule.threshold, rule.operator
            )
            
            if alert_triggered:
                alert = {
                    "alert_id": f"{rule.rule_id}_{int(get_current_timestamp().timestamp())}",
                    "rule_id": rule.rule_id,
                    "metric_name": rule.metric_name,
                    "current_value": metric_value,
                    "threshold": rule.threshold,
                    "severity": rule.severity,
                    "timestamp": get_current_timestamp().isoformat(),
                    "message": f"{rule.metric_name} is {metric_value}, threshold: {rule.threshold}"
                }
                current_alerts.append(alert)
                
                # Event über Event-Bus publishen
                if self.event_bus:
                    await self.event_bus.publish_event(
                        event_type="alert_triggered",
                        data=alert,
                        source="monitoring-v2"
                    )
        
        self.active_alerts = current_alerts
    
    def _evaluate_alert_condition(self, value: float, threshold: float, operator: str) -> bool:
        """Alert-Bedingung evaluieren"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            return False
    
    async def _get_health_details(self) -> Dict[str, Any]:
        """Erweiterte Health-Details für Monitoring Service"""
        base_health = await super()._get_health_details()
        
        return {
            **base_health,
            "monitoring": {
                "services_monitored": len(self.services_to_monitor),
                "healthy_services": len([s for s in self.service_statuses.values() if s.status == "healthy"]),
                "active_alerts": len(self.active_alerts),
                "alert_rules": len(self.alert_rules),
                "metrics_available": self.current_metrics is not None
            },
            "database": {
                "postgres": self.db_pool is not None,
                "redis": self.redis_client is not None
            },
            "api_version": "v2",
            "code_quality": "refactored_with_shared_libraries"
        }


# Service-Instanz erstellen
def create_app() -> FastAPI:
    """FastAPI App erstellen"""
    service = MonitoringService()
    return service.app


async def start_service():
    """Service starten"""
    service = MonitoringService()
    await service._setup_service()
    
    # Server starten
    service.run(
        host="0.0.0.0",
        debug=SecurityConfig.is_debug_mode()
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_service())