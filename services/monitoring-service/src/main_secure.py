#!/usr/bin/env python3
"""
Aktienanalyse Monitoring Service - SECURE VERSION
System Health and Performance Monitoring with Security Hardening
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import aiohttp
import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import psutil

# Import shared libraries (SECURITY FIX)
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging, setup_security_logging, setup_performance_logging
from database_mock import DatabaseManager, EventStore, HealthChecker
from security import InputValidator, SecurityConfig, create_security_headers, get_client_ip, RateLimiter
from event_bus_simple import EventBusConnector, EventType

# Load environment variables (SECURITY FIX)
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Setup structured logging (SECURITY FIX)
logger = setup_logging("monitoring-service")
security_logger = setup_security_logging("monitoring-service")
performance_logger = setup_performance_logging("monitoring-service")

# ================================================================
# SECURE MODELS
# ================================================================

class ServiceStatus(BaseModel):
    service_name: str = Field(..., pattern="^[a-zA-Z0-9_-]+$")
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    last_check: datetime
    response_time_ms: Optional[float] = Field(None, ge=0, le=60000)
    error_message: Optional[str] = Field(None, max_length=500)

class SystemMetrics(BaseModel):
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_percent: float = Field(..., ge=0, le=100)
    disk_usage_percent: float = Field(..., ge=0, le=100)
    network_io: Dict[str, float]
    active_connections: int = Field(..., ge=0)
    timestamp: datetime

class AlertRule(BaseModel):
    rule_id: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    metric_name: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    threshold: float = Field(..., ge=0, le=100)
    comparison: str = Field(..., pattern="^(gt|lt|eq|gte|lte)$")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    enabled: bool = True

# ================================================================
# SECURE MONITORING SERVICE
# ================================================================

class SecureMonitoringService:
    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.event_bus: Optional[EventBusConnector] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.security_config = SecurityConfig()
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(max_requests=200, window_seconds=60)
        
        # Service URLs from environment (SECURITY FIX)
        self.service_urls = {
            "intelligent-core": os.getenv("INTELLIGENT_CORE_URL", "http://localhost:8001"),
            "broker-gateway": os.getenv("BROKER_GATEWAY_URL", "http://localhost:8002"),
            "event-bus": os.getenv("EVENT_BUS_URL", "http://localhost:8081"),
            "frontend": os.getenv("FRONTEND_URL", "http://localhost:3000")
        }
        
        # Alert rules
        self.alert_rules: List[AlertRule] = []
        self.load_default_alert_rules()
        
    def load_default_alert_rules(self):
        """Load default alert rules with security validation"""
        default_rules = [
            AlertRule(
                rule_id="cpu_high",
                metric_name="cpu_usage_percent",
                threshold=80.0,
                comparison="gt",
                severity="medium"
            ),
            AlertRule(
                rule_id="memory_high",
                metric_name="memory_usage_percent", 
                threshold=85.0,
                comparison="gt",
                severity="high"
            ),
            AlertRule(
                rule_id="disk_full",
                metric_name="disk_usage_percent",
                threshold=90.0,
                comparison="gt",
                severity="critical"
            )
        ]
        self.alert_rules.extend(default_rules)
        
    async def initialize(self):
        """Initialize monitoring service with security"""
        try:
            # Database manager (SECURITY FIX)
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Event bus connector (SECURITY FIX)
            self.event_bus = EventBusConnector("monitoring-service")
            await self.event_bus.connect()
            
            # Secure HTTP session (SECURITY FIX)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={
                    "User-Agent": "aktienanalyse-monitoring/1.0.0-secure",
                    "X-Service": "monitoring"
                },
                connector=aiohttp.TCPConnector(
                    limit=20,
                    limit_per_host=5,
                    ttl_dns_cache=300
                )
            )
            
            logger.info("Secure Monitoring Service initialized")
            
        except Exception as e:
            logger.error("Failed to initialize monitoring service", error=str(e))
            raise

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.close()
            if self.event_bus:
                await self.event_bus.disconnect()
            if self.db_manager:
                await self.db_manager.close()
                
            logger.info("Secure Monitoring Service cleaned up")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def check_service_health(self, service_name: str, url: str) -> ServiceStatus:
        """Check health of a specific service with security validation"""
        try:
            # Validate service name
            if not self.validator.validate_service_name(service_name):
                raise ValueError(f"Invalid service name: {service_name}")
            
            start_time = time.time()
            
            try:
                async with self.session.get(f"{url}/health", timeout=5) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        status = "healthy"
                        error_message = None
                    else:
                        status = "degraded"
                        error_message = f"HTTP {response.status}"
                        
            except asyncio.TimeoutError:
                status = "unhealthy"
                error_message = "Timeout"
                response_time = 5000
            except Exception as e:
                status = "unhealthy"
                error_message = str(e)[:500]  # Limit error message length
                response_time = (time.time() - start_time) * 1000
            
            return ServiceStatus(
                service_name=service_name,
                status=status,
                last_check=datetime.utcnow(),
                response_time_ms=response_time,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error("Error checking service health", 
                        service=service_name, 
                        error=str(e))
            return ServiceStatus(
                service_name=service_name,
                status="unhealthy",
                last_check=datetime.utcnow(),
                error_message="Health check failed"
            )

    async def get_system_metrics(self) -> SystemMetrics:
        """Get secure system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O (limited for security)
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": float(net_io.bytes_sent),
                "bytes_recv": float(net_io.bytes_recv)
            }
            
            # Active connections (limited count for security)
            try:
                connections = len(psutil.net_connections(kind='tcp'))
            except (psutil.AccessDenied, OSError):
                connections = 0  # Security fallback
            
            return SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory_percent,
                disk_usage_percent=disk_percent,
                network_io=network_io,
                active_connections=connections,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error("Error getting system metrics", error=str(e))
            # Return safe default values
            return SystemMetrics(
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                network_io={"bytes_sent": 0.0, "bytes_recv": 0.0},
                active_connections=0,
                timestamp=datetime.utcnow()
            )

    async def check_alert_rules(self, metrics: SystemMetrics) -> List[Dict[str, Any]]:
        """Check alert rules against metrics"""
        alerts = []
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
                
            try:
                metric_value = getattr(metrics, rule.metric_name, None)
                if metric_value is None:
                    continue
                
                triggered = False
                if rule.comparison == "gt" and metric_value > rule.threshold:
                    triggered = True
                elif rule.comparison == "gte" and metric_value >= rule.threshold:
                    triggered = True
                elif rule.comparison == "lt" and metric_value < rule.threshold:
                    triggered = True
                elif rule.comparison == "lte" and metric_value <= rule.threshold:
                    triggered = True
                elif rule.comparison == "eq" and metric_value == rule.threshold:
                    triggered = True
                
                if triggered:
                    alert = {
                        "rule_id": rule.rule_id,
                        "metric_name": rule.metric_name,
                        "current_value": metric_value,
                        "threshold": rule.threshold,
                        "severity": rule.severity,
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": f"{rule.metric_name} is {metric_value}% (threshold: {rule.threshold}%)"
                    }
                    alerts.append(alert)
                    
                    # Publish alert event
                    alert_event = {
                        "event_type": "system.alert.triggered",
                        "source": "monitoring-service",
                        "data": alert
                    }
                    await self.event_bus.publish(alert_event)
                    
            except Exception as e:
                logger.error("Error checking alert rule", 
                           rule_id=rule.rule_id, 
                           error=str(e))
        
        return alerts

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            health_checker = HealthChecker(self.db_manager)
            db_status = await health_checker.check_database()
            
            # Check all services
            service_statuses = {}
            for service_name, url in self.service_urls.items():
                status = await self.check_service_health(service_name, url)
                service_statuses[service_name] = status.dict()
            
            # Get system metrics
            metrics = await self.get_system_metrics()
            
            # Check alerts
            alerts = await self.check_alert_rules(metrics)
            
            # Determine overall status
            overall_status = "healthy"
            unhealthy_services = [
                name for name, status in service_statuses.items() 
                if status["status"] == "unhealthy"
            ]
            
            if unhealthy_services or any(alert["severity"] in ["high", "critical"] for alert in alerts):
                overall_status = "degraded"
            
            if len(unhealthy_services) > len(service_statuses) / 2:
                overall_status = "unhealthy"
            
            return {
                "service": "secure-monitoring",
                "status": overall_status,
                "database": db_status,
                "services": service_statuses,
                "system_metrics": metrics.dict(),
                "active_alerts": alerts,
                "alert_rules_count": len([r for r in self.alert_rules if r.enabled]),
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0-secure"
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "service": "secure-monitoring",
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }

# ================================================================
# GLOBAL SERVICE INSTANCE
# ================================================================

monitoring_service = SecureMonitoringService()

# ================================================================
# FASTAPI APPLICATION WITH SECURITY
# ================================================================

app = FastAPI(
    title="Aktienanalyse Secure Monitoring Service",
    description="System Health and Performance Monitoring with Security Hardening",
    version="1.0.0-secure",
    docs_url=None,  # Disable docs in production
    redoc_url=None  # Disable redoc in production
)

# Security Middleware (SECURITY FIX)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    response = await call_next(request)
    security_headers = create_security_headers()
    for header, value in security_headers.items():
        response.headers[header] = value
    return response

# CORS Middleware with Hardened Configuration (SECURITY FIX)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://aktienanalyse.local").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # No wildcard
    allow_credentials=True,
    allow_methods=["GET"],  # Only GET for monitoring
    allow_headers=["Content-Type", "Authorization"],
)

# ================================================================
# SECURE ENDPOINTS
# ================================================================

@app.get("/health")
async def health_check():
    """Secure health check endpoint"""
    return await monitoring_service.get_health_status()

@app.get("/metrics/system")
async def get_system_metrics(request: Request):
    """Get system metrics with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not monitoring_service.rate_limiter.allow_request(f"metrics_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    metrics = await monitoring_service.get_system_metrics()
    return metrics.dict()

@app.get("/services/status")
async def get_services_status(request: Request):
    """Get all services status with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not monitoring_service.rate_limiter.allow_request(f"services_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    service_statuses = {}
    for service_name, url in monitoring_service.service_urls.items():
        status = await monitoring_service.check_service_health(service_name, url)
        service_statuses[service_name] = status.dict()
    
    return {
        "services": service_statuses,
        "total_count": len(service_statuses),
        "healthy_count": len([s for s in service_statuses.values() if s["status"] == "healthy"]),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/alerts/active")
async def get_active_alerts(request: Request):
    """Get active alerts with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not monitoring_service.rate_limiter.allow_request(f"alerts_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Get current metrics to check alerts
    metrics = await monitoring_service.get_system_metrics()
    alerts = await monitoring_service.check_alert_rules(metrics)
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "severities": {
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "high": len([a for a in alerts if a["severity"] == "high"]),
            "medium": len([a for a in alerts if a["severity"] == "medium"]),
            "low": len([a for a in alerts if a["severity"] == "low"])
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/alerts/rules")
async def list_alert_rules(request: Request):
    """List alert rules with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not monitoring_service.rate_limiter.allow_request(f"rules_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    rules = [rule.dict() for rule in monitoring_service.alert_rules]
    
    return {
        "rules": rules,
        "total_count": len(rules),
        "enabled_count": len([r for r in rules if r["enabled"]]),
        "timestamp": datetime.utcnow().isoformat()
    }

# ================================================================
# STARTUP AND SHUTDOWN EVENTS
# ================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Secure Monitoring Service...")
    await monitoring_service.initialize()
    logger.info("Secure Monitoring Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Secure Monitoring Service...")
    await monitoring_service.cleanup()
    logger.info("Secure Monitoring Service stopped")

if __name__ == "__main__":
    port = int(os.getenv("MONITORING_PORT", "8080"))
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        log_config=None  # Use our structured logging
    )