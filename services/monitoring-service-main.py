#!/usr/bin/env python3
"""
Aktienanalyse Monitoring Service
System monitoring and Zabbix integration
"""

import asyncio
import json
import os
import time
import psutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import aiohttp

# Logging Setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Pydantic Models
class SystemMetrics(BaseModel):
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    load_average: List[float]

class ServiceStatus(BaseModel):
    name: str
    status: str
    pid: Optional[int]
    cpu_percent: float
    memory_percent: float
    uptime: str

class DatabaseMetrics(BaseModel):
    connection_count: int
    event_count: int
    latest_event: Optional[datetime]
    table_sizes: Dict[str, int]

class ZabbixItem(BaseModel):
    key: str
    value: str
    timestamp: int

# Monitoring Service
class MonitoringService:
    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.event_bus_url = os.getenv("EVENT_BUS_URL", "http://localhost:8081")
        self.zabbix_server = os.getenv("ZABBIX_SERVER", "10.1.1.103")
        self.session: Optional[aiohttp.ClientSession] = None
        self.services_to_monitor = [
            "aktienanalyse-event-bus",
            "aktienanalyse-core", 
            "aktienanalyse-broker",
            "postgresql",
            "redis-server",
            "rabbitmq-server"
        ]
        
    async def initialize(self):
        """Initialize monitoring service"""
        try:
            # Database connection
            postgres_url = os.getenv("POSTGRES_URL", "postgresql://aktienanalyse:secure_password@localhost:5432/aktienanalyse_events?sslmode=disable")
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=1, max_size=5)
            
            # HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
            
            logger.info("Monitoring Service initialized")
            
        except Exception as e:
            logger.error("Failed to initialize Monitoring Service", error=str(e))
            raise

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.db_pool:
            await self.db_pool.close()

    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage for system root
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
            # Load average
            load_avg = list(os.getloadavg())
            
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk_percent,
                network_io=network_io,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error("Error getting system metrics", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

    async def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get systemd service status"""
        try:
            # Get service status
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True
            )
            status = result.stdout.strip()
            
            # Get service PID if running
            pid = None
            cpu_percent = 0.0
            memory_percent = 0.0
            uptime = "unknown"
            
            if status == "active":
                try:
                    # Get main PID
                    pid_result = subprocess.run(
                        ["systemctl", "show", "--property=MainPID", service_name],
                        capture_output=True,
                        text=True
                    )
                    pid_line = pid_result.stdout.strip()
                    if "MainPID=" in pid_line:
                        pid = int(pid_line.split("=")[1])
                        
                        if pid > 0:
                            # Get process metrics
                            process = psutil.Process(pid)
                            cpu_percent = process.cpu_percent()
                            memory_percent = process.memory_percent()
                            
                            # Calculate uptime
                            create_time = datetime.fromtimestamp(process.create_time())
                            uptime_delta = datetime.utcnow() - create_time
                            uptime = str(uptime_delta).split('.')[0]  # Remove microseconds
                            
                except (psutil.NoSuchProcess, ValueError, subprocess.SubprocessError):
                    pass
            
            return ServiceStatus(
                name=service_name,
                status=status,
                pid=pid,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                uptime=uptime
            )
            
        except Exception as e:
            logger.error("Error getting service status", service=service_name, error=str(e))
            return ServiceStatus(
                name=service_name,
                status="unknown",
                pid=None,
                cpu_percent=0.0,
                memory_percent=0.0,
                uptime="unknown"
            )

    async def get_database_metrics(self) -> DatabaseMetrics:
        """Get database metrics"""
        try:
            async with self.db_pool.acquire() as conn:
                # Connection count
                conn_result = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE datname = 'aktienanalyse_events'
                """)
                
                # Event count
                event_count = await conn.fetchval("SELECT COUNT(*) FROM events")
                
                # Latest event
                latest_event = await conn.fetchval("""
                    SELECT created_at FROM events 
                    ORDER BY created_at DESC LIMIT 1
                """)
                
                # Table sizes
                table_sizes = {}
                tables = await conn.fetch("""
                    SELECT schemaname, tablename, pg_total_relation_size(schemaname||'.'||tablename) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                
                for table in tables:
                    table_sizes[table['tablename']] = table['size']
                
                return DatabaseMetrics(
                    connection_count=conn_result,
                    event_count=event_count,
                    latest_event=latest_event,
                    table_sizes=table_sizes
                )
                
        except Exception as e:
            logger.error("Error getting database metrics", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get database metrics: {str(e)}")

    async def send_to_zabbix(self, items: List[ZabbixItem]):
        """Send metrics to Zabbix server (mock implementation)"""
        try:
            # In production, implement real Zabbix sender protocol
            # For demo, just log the metrics
            for item in items:
                logger.info("Zabbix metric", 
                           key=item.key, 
                           value=item.value, 
                           timestamp=item.timestamp)
            
            return True
            
        except Exception as e:
            logger.error("Error sending to Zabbix", error=str(e))
            return False

    async def collect_and_send_metrics(self):
        """Collect all metrics and send to Zabbix"""
        try:
            # System metrics
            system_metrics = await self.get_system_metrics()
            
            # Database metrics
            db_metrics = await self.get_database_metrics()
            
            # Service statuses
            service_statuses = []
            for service_name in self.services_to_monitor:
                status = await self.get_service_status(service_name)
                service_statuses.append(status)
            
            # Prepare Zabbix items
            timestamp = int(time.time())
            zabbix_items = [
                ZabbixItem(key="system.cpu.util", value=str(system_metrics.cpu_percent), timestamp=timestamp),
                ZabbixItem(key="vm.memory.util", value=str(system_metrics.memory_percent), timestamp=timestamp),
                ZabbixItem(key="vfs.fs.util[/]", value=str(system_metrics.disk_percent), timestamp=timestamp),
                ZabbixItem(key="system.load1", value=str(system_metrics.load_average[0]), timestamp=timestamp),
                ZabbixItem(key="db.events.count", value=str(db_metrics.event_count), timestamp=timestamp),
                ZabbixItem(key="db.connections", value=str(db_metrics.connection_count), timestamp=timestamp),
            ]
            
            # Add service status items
            for service in service_statuses:
                status_value = "1" if service.status == "active" else "0"
                zabbix_items.append(
                    ZabbixItem(
                        key=f"service.status[{service.name}]", 
                        value=status_value, 
                        timestamp=timestamp
                    )
                )
                
                if service.pid:
                    zabbix_items.extend([
                        ZabbixItem(
                            key=f"service.cpu[{service.name}]", 
                            value=str(service.cpu_percent), 
                            timestamp=timestamp
                        ),
                        ZabbixItem(
                            key=f"service.memory[{service.name}]", 
                            value=str(service.memory_percent), 
                            timestamp=timestamp
                        )
                    ])
            
            # Send to Zabbix
            await self.send_to_zabbix(zabbix_items)
            
            logger.info("Metrics collected and sent", items_count=len(zabbix_items))
            
        except Exception as e:
            logger.error("Error collecting metrics", error=str(e))

# Global service instance
monitoring_service = MonitoringService()

# FastAPI Application
app = FastAPI(
    title="Aktienanalyse Monitoring Service", 
    description="System monitoring and Zabbix integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if monitoring_service.db_pool:
            async with monitoring_service.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        
        return {
            "service": "monitoring",
            "status": "healthy",
            "database": "connected",
            "zabbix_server": monitoring_service.zabbix_server,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# Monitoring Endpoints
@app.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics():
    """Get current system metrics"""
    return await monitoring_service.get_system_metrics()

@app.get("/metrics/database", response_model=DatabaseMetrics)
async def get_database_metrics():
    """Get database metrics"""
    return await monitoring_service.get_database_metrics()

@app.get("/metrics/services", response_model=List[ServiceStatus])
async def get_service_metrics():
    """Get all service statuses"""
    services = []
    for service_name in monitoring_service.services_to_monitor:
        status = await monitoring_service.get_service_status(service_name)
        services.append(status)
    return services

@app.get("/metrics/service/{service_name}", response_model=ServiceStatus)
async def get_service_metric(service_name: str):
    """Get specific service status"""
    return await monitoring_service.get_service_status(service_name)

@app.post("/metrics/collect")
async def collect_metrics(background_tasks: BackgroundTasks):
    """Trigger metrics collection"""
    background_tasks.add_task(monitoring_service.collect_and_send_metrics)
    return {"status": "collection_started", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics/overview")
async def get_metrics_overview():
    """Get complete metrics overview"""
    try:
        system_metrics = await monitoring_service.get_system_metrics()
        db_metrics = await monitoring_service.get_database_metrics()
        
        service_statuses = []
        for service_name in monitoring_service.services_to_monitor:
            status = await monitoring_service.get_service_status(service_name)
            service_statuses.append(status)
        
        # Calculate summary
        active_services = sum(1 for s in service_statuses if s.status == "active")
        total_services = len(service_statuses)
        
        return {
            "system": system_metrics,
            "database": db_metrics,
            "services": service_statuses,
            "summary": {
                "active_services": active_services,
                "total_services": total_services,
                "system_health": "healthy" if system_metrics.cpu_percent < 80 and system_metrics.memory_percent < 80 else "warning",
                "last_update": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Error getting metrics overview", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get metrics overview: {str(e)}")

# Background task for periodic metrics collection
async def periodic_metrics_collection():
    """Collect metrics every 30 seconds"""
    while True:
        try:
            await monitoring_service.collect_and_send_metrics()
            await asyncio.sleep(30)  # Collect every 30 seconds
        except Exception as e:
            logger.error("Error in periodic metrics collection", error=str(e))
            await asyncio.sleep(30)

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Monitoring Service...")
    await monitoring_service.initialize()
    
    # Start background metrics collection
    asyncio.create_task(periodic_metrics_collection())
    
    logger.info("Monitoring Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Monitoring Service...")
    await monitoring_service.cleanup()
    logger.info("Monitoring Service stopped")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8083,
        reload=False,
        access_log=True
    )