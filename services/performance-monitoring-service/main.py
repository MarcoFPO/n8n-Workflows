"""
Performance Monitoring Service v1.0.0
Zentrales Performance-Monitoring für das gesamte Aktienanalyse-Ökosystem

Features:
- System-weite Performance-Metriken
- Database und Redis Performance-Tracking
- Service Health Monitoring
- Performance-Alerting und Recommendations
- Real-time Performance-Dashboard
"""

import asyncio
import aiohttp
import json
import logging
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

# Enhanced Performance Infrastructure
from shared.enhanced_database_pool import (
    enhanced_db_pool,
    init_enhanced_db_pool,
    PoolConfig
)
from shared.enhanced_redis_pool import (
    enhanced_redis_pool,
    init_enhanced_redis_pool,
    RedisConfig
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [performance-monitor] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("performance-monitor")

# Pydantic Models
class ServiceEndpoint(BaseModel):
    name: str
    url: str
    health_endpoint: str = "/health"
    performance_endpoint: Optional[str] = "/metrics/performance"

class SystemAlert(BaseModel):
    level: str  # info, warning, critical
    service: str
    metric: str
    value: float
    threshold: float
    message: str
    timestamp: datetime

class PerformanceThresholds(BaseModel):
    response_time_warning: float = 500  # ms
    response_time_critical: float = 1000  # ms
    error_rate_warning: float = 5  # %
    error_rate_critical: float = 10  # %
    memory_usage_warning: float = 80  # %
    memory_usage_critical: float = 95  # %
    cpu_usage_warning: float = 80  # %
    cpu_usage_critical: float = 95  # %

@dataclass
class ServiceMetrics:
    """Service Performance Metrics"""
    name: str
    status: str = "unknown"
    response_time: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    last_check: datetime = field(default_factory=datetime.utcnow)
    health_details: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitoringService:
    """Zentraler Performance-Monitoring Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Performance Monitoring Service",
            version="1.0.0",
            description="System-wide performance monitoring and alerting"
        )
        
        # Service Configuration
        self.monitored_services = [
            ServiceEndpoint(
                name="event-bus-service",
                url="http://10.1.1.174:8006",
                performance_endpoint="/metrics/performance"
            ),
            ServiceEndpoint(
                name="prediction-evaluation-service",
                url="http://10.1.1.174:8009",
                performance_endpoint="/metrics/performance"
            ),
            ServiceEndpoint(
                name="prediction-averages-service",
                url="http://10.1.1.174:8007"
            ),
            ServiceEndpoint(
                name="marketcap-service",
                url="http://10.1.1.174:8001"
            ),
            ServiceEndpoint(
                name="ml-analytics-service",
                url="http://10.1.1.174:8003"
            )
        ]
        
        # Monitoring State
        self.service_metrics: Dict[str, ServiceMetrics] = {}
        self.system_alerts: List[SystemAlert] = []
        self.performance_history: Dict[str, List[Dict]] = {}
        self.thresholds = PerformanceThresholds()
        
        # WebSocket Connections für Real-time Updates
        self.active_connections: List[WebSocket] = []
        
        # Monitoring Tasks
        self.monitoring_active = True
        self.monitoring_interval = 30  # 30 Sekunden
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return await self._get_dashboard_html()
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "performance-monitoring", "timestamp": datetime.utcnow()}
        
        @self.app.get("/metrics/system")
        async def get_system_metrics():
            return await self._get_system_metrics()
        
        @self.app.get("/metrics/services")
        async def get_service_metrics():
            return await self._get_all_service_metrics()
        
        @self.app.get("/metrics/database")
        async def get_database_metrics():
            return await self._get_database_performance()
        
        @self.app.get("/metrics/redis")
        async def get_redis_metrics():
            return await self._get_redis_performance()
        
        @self.app.get("/alerts")
        async def get_alerts():
            return {"alerts": self.system_alerts[-50:]}  # Last 50 alerts
        
        @self.app.get("/performance/report")
        async def get_performance_report():
            return await self._generate_performance_report()
        
        @self.app.post("/thresholds")
        async def update_thresholds(thresholds: PerformanceThresholds):
            self.thresholds = thresholds
            return {"status": "updated", "thresholds": thresholds}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket(websocket)
    
    async def initialize(self):
        """Initialize monitoring service"""
        try:
            # Initialize performance pools für eigene Metriken
            await init_enhanced_db_pool(PoolConfig(
                min_connections=2,
                max_connections=5,
                enable_query_cache=True
            ))
            
            await init_enhanced_redis_pool(RedisConfig(
                max_connections=5,
                enable_performance_tracking=True
            ))
            
            # Initialize service metrics
            for service in self.monitored_services:
                self.service_metrics[service.name] = ServiceMetrics(name=service.name)
                self.performance_history[service.name] = []
            
            # Start monitoring tasks
            asyncio.create_task(self._monitoring_loop())
            asyncio.create_task(self._websocket_broadcaster())
            
            logger.info("Performance Monitoring Service initialized")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # System Metrics
                await self._collect_system_metrics()
                
                # Service Metrics
                await self._collect_service_metrics()
                
                # Database Performance
                await self._collect_database_metrics()
                
                # Redis Performance
                await self._collect_redis_metrics()
                
                # Check Alerts
                await self._check_performance_alerts()
                
                # Cleanup old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_system_metrics(self):
        """Collect system-wide metrics"""
        try:
            # CPU und Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_usage": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
            
            # System Alerts prüfen
            if cpu_percent > self.thresholds.cpu_usage_critical:
                await self._create_alert("critical", "system", "cpu_usage", cpu_percent, 
                                        self.thresholds.cpu_usage_critical, 
                                        f"Critical CPU usage: {cpu_percent}%")
            
            if memory.percent > self.thresholds.memory_usage_critical:
                await self._create_alert("critical", "system", "memory_usage", memory.percent,
                                        self.thresholds.memory_usage_critical,
                                        f"Critical memory usage: {memory.percent}%")
            
            # History speichern
            if "system" not in self.performance_history:
                self.performance_history["system"] = []
            
            self.performance_history["system"].append(system_metrics)
            
        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
    
    async def _collect_service_metrics(self):
        """Collect metrics from all monitored services"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for service in self.monitored_services:
                try:
                    start_time = datetime.now()
                    
                    # Health Check
                    health_url = f"{service.url}{service.health_endpoint}"
                    async with session.get(health_url) as response:
                        response_time = (datetime.now() - start_time).total_seconds() * 1000
                        health_data = await response.json() if response.content_type == 'application/json' else {}
                        
                        metrics = self.service_metrics[service.name]
                        metrics.status = "healthy" if response.status == 200 else "unhealthy"
                        metrics.response_time = response_time
                        metrics.last_check = datetime.utcnow()
                        metrics.health_details = health_data
                    
                    # Performance Metrics (if available)
                    if service.performance_endpoint:
                        perf_url = f"{service.url}{service.performance_endpoint}"
                        try:
                            async with session.get(perf_url) as perf_response:
                                if perf_response.status == 200:
                                    perf_data = await perf_response.json()
                                    await self._process_service_performance(service.name, perf_data)
                        except:
                            pass  # Performance endpoint optional
                    
                    # Response Time Alerts
                    if response_time > self.thresholds.response_time_critical:
                        await self._create_alert("critical", service.name, "response_time", response_time,
                                                self.thresholds.response_time_critical,
                                                f"Critical response time: {response_time:.0f}ms")
                    
                    # History speichern
                    self.performance_history[service.name].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": metrics.status,
                        "response_time": response_time,
                        "health_data": health_data
                    })
                    
                except asyncio.TimeoutError:
                    metrics = self.service_metrics[service.name]
                    metrics.status = "timeout"
                    metrics.response_time = 10000  # 10s timeout
                    await self._create_alert("critical", service.name, "timeout", 10000, 1000, 
                                           f"Service timeout: {service.name}")
                    
                except Exception as e:
                    metrics = self.service_metrics[service.name]
                    metrics.status = "error"
                    logger.error(f"Service monitoring failed for {service.name}: {e}")
    
    async def _process_service_performance(self, service_name: str, perf_data: Dict):
        """Process detailed performance data from services"""
        try:
            metrics = self.service_metrics[service_name]
            
            # Extract common metrics
            if "service_performance" in perf_data:
                svc_perf = perf_data["service_performance"]
                if "events_per_second" in svc_perf:
                    metrics.throughput = svc_perf["events_per_second"]
                elif "predictions_per_second" in svc_perf:
                    metrics.throughput = svc_perf["predictions_per_second"]
            
            # Error rate aus verschiedenen Quellen extrahieren
            if "database_performance" in perf_data:
                db_perf = perf_data["database_performance"].get("query_performance", {})
                if "error_rate" in db_perf:
                    metrics.error_rate = db_perf["error_rate"]
            
        except Exception as e:
            logger.error(f"Performance processing failed for {service_name}: {e}")
    
    async def _collect_database_metrics(self):
        """Collect database performance metrics"""
        try:
            if enhanced_db_pool.is_initialized:
                db_report = await enhanced_db_pool.get_performance_report()
                
                # Database-specific Alerts
                error_rate = db_report.get("query_performance", {}).get("error_rate", 0)
                if error_rate > self.thresholds.error_rate_critical:
                    await self._create_alert("critical", "database", "error_rate", error_rate,
                                            self.thresholds.error_rate_critical,
                                            f"Critical database error rate: {error_rate}%")
                
                # History speichern
                if "database" not in self.performance_history:
                    self.performance_history["database"] = []
                
                self.performance_history["database"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "performance_report": db_report
                })
                
        except Exception as e:
            logger.error(f"Database metrics collection failed: {e}")
    
    async def _collect_redis_metrics(self):
        """Collect Redis performance metrics"""
        try:
            if enhanced_redis_pool.is_initialized:
                redis_report = await enhanced_redis_pool.get_performance_report()
                
                # Memory Usage Alert
                memory_pct = redis_report.get("memory_usage", {}).get("memory_usage_percentage", 0)
                if memory_pct > 90:
                    await self._create_alert("critical", "redis", "memory_usage", memory_pct, 90,
                                           f"Critical Redis memory usage: {memory_pct:.1f}%")
                
                # History speichern
                if "redis" not in self.performance_history:
                    self.performance_history["redis"] = []
                
                self.performance_history["redis"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "performance_report": redis_report
                })
                
        except Exception as e:
            logger.error(f"Redis metrics collection failed: {e}")
    
    async def _create_alert(self, level: str, service: str, metric: str, 
                           value: float, threshold: float, message: str):
        """Create and store performance alert"""
        alert = SystemAlert(
            level=level,
            service=service,
            metric=metric,
            value=value,
            threshold=threshold,
            message=message,
            timestamp=datetime.utcnow()
        )
        
        self.system_alerts.append(alert)
        logger.warning(f"Performance Alert [{level.upper()}]: {message}")
        
        # WebSocket broadcast
        await self._broadcast_alert(alert)
    
    async def _check_performance_alerts(self):
        """Check all metrics against thresholds"""
        # Implemented above in individual collection methods
        pass
    
    async def _cleanup_old_data(self):
        """Cleanup old performance data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # Keep 24h of data
        
        # Cleanup alerts
        self.system_alerts = [alert for alert in self.system_alerts 
                            if alert.timestamp > cutoff_time]
        
        # Cleanup performance history (keep last 100 entries per service)
        for service_name in self.performance_history:
            if len(self.performance_history[service_name]) > 100:
                self.performance_history[service_name] = self.performance_history[service_name][-100:]
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_usage": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _get_all_service_metrics(self) -> Dict[str, Any]:
        """Get metrics for all monitored services"""
        return {
            "services": {
                name: {
                    "name": metrics.name,
                    "status": metrics.status,
                    "response_time": metrics.response_time,
                    "error_rate": metrics.error_rate,
                    "throughput": metrics.throughput,
                    "last_check": metrics.last_check.isoformat(),
                    "health_details": metrics.health_details
                }
                for name, metrics in self.service_metrics.items()
            },
            "summary": {
                "total_services": len(self.service_metrics),
                "healthy_services": len([m for m in self.service_metrics.values() if m.status == "healthy"]),
                "unhealthy_services": len([m for m in self.service_metrics.values() if m.status != "healthy"])
            }
        }
    
    async def _get_database_performance(self) -> Dict[str, Any]:
        """Get database performance metrics"""
        if enhanced_db_pool.is_initialized:
            return await enhanced_db_pool.get_performance_report()
        return {"status": "not_initialized"}
    
    async def _get_redis_performance(self) -> Dict[str, Any]:
        """Get Redis performance metrics"""
        if enhanced_redis_pool.is_initialized:
            return await enhanced_redis_pool.get_performance_report()
        return {"status": "not_initialized"}
    
    async def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        system_metrics = await self._get_system_metrics()
        service_metrics = await self._get_all_service_metrics()
        db_metrics = await self._get_database_performance()
        redis_metrics = await self._get_redis_performance()
        
        # Performance Summary
        critical_alerts = len([a for a in self.system_alerts if a.level == "critical"])
        warning_alerts = len([a for a in self.system_alerts if a.level == "warning"])
        
        return {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "monitoring_interval": self.monitoring_interval,
                "data_retention": "24 hours"
            },
            "system_health": system_metrics,
            "services_health": service_metrics,
            "database_performance": db_metrics,
            "redis_performance": redis_metrics,
            "alerts_summary": {
                "total_alerts": len(self.system_alerts),
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "recent_alerts": self.system_alerts[-10:]  # Last 10 alerts
            },
            "performance_summary": {
                "system_healthy": system_metrics["cpu_usage"] < 80 and system_metrics["memory_usage"] < 80,
                "services_healthy": service_metrics["summary"]["unhealthy_services"] == 0,
                "database_healthy": db_metrics.get("status") != "not_initialized",
                "redis_healthy": redis_metrics.get("status") != "not_initialized",
                "overall_status": "healthy" if critical_alerts == 0 else "degraded"
            },
            "recommendations": await self._get_performance_recommendations()
        }
    
    async def _get_performance_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # System recommendations
        system_metrics = await self._get_system_metrics()
        if system_metrics["cpu_usage"] > 80:
            recommendations.append("High CPU usage detected - consider scaling or optimization")
        if system_metrics["memory_usage"] > 80:
            recommendations.append("High memory usage - monitor for memory leaks")
        
        # Service recommendations
        for name, metrics in self.service_metrics.items():
            if metrics.response_time > self.thresholds.response_time_warning:
                recommendations.append(f"Service {name} has high response times - review performance")
            if metrics.status != "healthy":
                recommendations.append(f"Service {name} is unhealthy - check logs and connectivity")
        
        if not recommendations:
            recommendations.append("All systems performing within normal parameters")
        
        return recommendations
    
    async def _handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections for real-time updates"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                await websocket.receive_text()  # Keep connection alive
        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
    
    async def _websocket_broadcaster(self):
        """Broadcast performance updates via WebSocket"""
        while self.monitoring_active:
            try:
                if self.active_connections:
                    # Broadcast current metrics
                    metrics_data = {
                        "type": "metrics_update",
                        "system": await self._get_system_metrics(),
                        "services": await self._get_all_service_metrics(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    disconnected = []
                    for connection in self.active_connections:
                        try:
                            await connection.send_text(json.dumps(metrics_data))
                        except:
                            disconnected.append(connection)
                    
                    # Remove disconnected connections
                    for conn in disconnected:
                        if conn in self.active_connections:
                            self.active_connections.remove(conn)
                
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
    
    async def _broadcast_alert(self, alert: SystemAlert):
        """Broadcast alert to all connected clients"""
        alert_data = {
            "type": "alert",
            "alert": {
                "level": alert.level,
                "service": alert.service,
                "metric": alert.metric,
                "value": alert.value,
                "threshold": alert.threshold,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat()
            }
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(alert_data))
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
    
    async def _get_dashboard_html(self) -> str:
        """Simple HTML dashboard"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Monitoring Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .healthy { background: #d4edda; }
                .warning { background: #fff3cd; }
                .critical { background: #f8d7da; }
                #alerts { height: 200px; overflow-y: scroll; border: 1px solid #ddd; padding: 10px; }
            </style>
        </head>
        <body>
            <h1>Aktienanalyse Performance Dashboard</h1>
            <div id="system-metrics">
                <h2>System Metrics</h2>
                <div id="system-data">Loading...</div>
            </div>
            <div id="service-metrics">
                <h2>Service Health</h2>
                <div id="service-data">Loading...</div>
            </div>
            <div id="alerts">
                <h2>Recent Alerts</h2>
                <div id="alert-data">Loading...</div>
            </div>
            
            <script>
                const ws = new WebSocket('ws://localhost:8010/ws');
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'metrics_update') {
                        updateSystemMetrics(data.system);
                        updateServiceMetrics(data.services);
                    } else if (data.type === 'alert') {
                        addAlert(data.alert);
                    }
                };
                
                function updateSystemMetrics(system) {
                    document.getElementById('system-data').innerHTML = 
                        `<div class="metric">CPU: ${system.cpu_usage}%</div>
                         <div class="metric">Memory: ${system.memory_usage}%</div>
                         <div class="metric">Disk: ${system.disk_usage}%</div>`;
                }
                
                function updateServiceMetrics(services) {
                    let html = '';
                    for (const [name, metrics] of Object.entries(services.services)) {
                        const statusClass = metrics.status === 'healthy' ? 'healthy' : 'critical';
                        html += `<div class="metric ${statusClass}">
                            ${name}: ${metrics.status} (${metrics.response_time}ms)
                        </div>`;
                    }
                    document.getElementById('service-data').innerHTML = html;
                }
                
                function addAlert(alert) {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = `metric ${alert.level}`;
                    alertDiv.innerHTML = `${alert.timestamp}: ${alert.message}`;
                    document.getElementById('alert-data').prepend(alertDiv);
                }
                
                // Initial load
                fetch('/metrics/system').then(r => r.json()).then(updateSystemMetrics);
                fetch('/metrics/services').then(r => r.json()).then(updateServiceMetrics);
            </script>
        </body>
        </html>
        '''
    
    async def shutdown(self):
        """Shutdown monitoring service"""
        self.monitoring_active = False
        
        # Close WebSocket connections
        for connection in self.active_connections:
            try:
                await connection.close()
            except:
                pass
        
        logger.info("Performance Monitoring Service shutdown")


# Application Setup
service = PerformanceMonitoringService()
app = service.app

@app.on_event("startup")
async def startup_event():
    await service.initialize()

@app.on_event("shutdown") 
async def shutdown_event():
    await service.shutdown()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,
        workers=1,
        loop="asyncio",
        log_level="info"
    )