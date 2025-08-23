#!/usr/bin/env python3
"""
Health Monitor Service v1.0.0 - Comprehensive System Health Monitoring
Überwacht alle Services und liefert zentrale Health-Checks

Code-Qualität: HÖCHSTE PRIORITÄT
- Clean Code Architecture
- Async HTTP Client mit Timeout-Handling
- Structured Logging
- Error Resilience
"""

import asyncio
import aiohttp
import logging
import uvicorn
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dataclasses import dataclass, asdict
import json

# Import Manager für Clean Architecture
from shared.import_manager import setup_imports
setup_imports()

from config.central_config_v1_0_0_20250821 import config
from shared.service_registry import service_registry, ServiceStatus

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Service Configuration with Health Check Endpoints"""
    name: str
    url: str
    health_endpoint: str
    timeout: int = 10
    critical: bool = True

@dataclass
class HealthStatus:
    """Health Status Data Structure"""
    service_name: str
    status: str  # healthy, degraded, unhealthy, unknown
    response_time_ms: int
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class HealthMonitor:
    """Centralized Health Monitoring Service - Clean Architecture"""
    
    def __init__(self):
        self.health_history: Dict[str, List[HealthStatus]] = {}
        self.last_check_time: Optional[datetime] = None
        
        # Service Registry aus zentraler Konfiguration
        self.services = self._build_service_configs()
    
    def _build_service_configs(self) -> List[ServiceConfig]:
        """Build service configurations from central config"""
        services = []
        
        # Alle Services aus zentraler Konfiguration
        for service_name, service_config in config.SERVICES.items():
            service_url = config.get_service_url(service_name)
            health_endpoint = service_config["health_endpoint"]
            
            # Kritische Services definieren
            critical = service_name in ["frontend", "data_processing", "prediction_tracking"]
            
            services.append(ServiceConfig(
                name=service_name,
                url=service_url,
                health_endpoint=health_endpoint,
                critical=critical
            ))
        
        return services
    
    async def check_service_health(self, service: ServiceConfig) -> HealthStatus:
        """Check individual service health with comprehensive error handling"""
        start_time = datetime.now()
        
        try:
            timeout = aiohttp.ClientTimeout(total=service.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{service.url}{service.health_endpoint}") as response:
                    response_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return HealthStatus(
                                service_name=service.name,
                                status="healthy",
                                response_time_ms=response_time,
                                timestamp=datetime.now().isoformat(),
                                details=data
                            )
                        except json.JSONDecodeError:
                            # Service responded but not with JSON
                            return HealthStatus(
                                service_name=service.name,
                                status="degraded",
                                response_time_ms=response_time,
                                timestamp=datetime.now().isoformat(),
                                error_message="Invalid JSON response"
                            )
                    else:
                        return HealthStatus(
                            service_name=service.name,
                            status="unhealthy",
                            response_time_ms=response_time,
                            timestamp=datetime.now().isoformat(),
                            error_message=f"HTTP {response.status}"
                        )
                        
        except asyncio.TimeoutError:
            response_time = service.timeout * 1000
            return HealthStatus(
                service_name=service.name,
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now().isoformat(),
                error_message="Timeout"
            )
        except aiohttp.ClientConnectorError:
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return HealthStatus(
                service_name=service.name,
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now().isoformat(),
                error_message="Connection refused"
            )
        except Exception as e:
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Unexpected error checking {service.name}: {e}")
            return HealthStatus(
                service_name=service.name,
                status="unknown",
                response_time_ms=response_time,
                timestamp=datetime.now().isoformat(),
                error_message=str(e)
            )
    
    async def check_all_services(self) -> Dict[str, HealthStatus]:
        """Check all services concurrently"""
        tasks = [self.check_service_health(service) for service in self.services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service = self.services[i]
                health_results[service.name] = HealthStatus(
                    service_name=service.name,
                    status="unknown",
                    response_time_ms=0,
                    timestamp=datetime.now().isoformat(),
                    error_message=f"Check failed: {result}"
                )
            else:
                health_results[result.service_name] = result
        
        # Store in history
        for service_name, health in health_results.items():
            if service_name not in self.health_history:
                self.health_history[service_name] = []
            
            self.health_history[service_name].append(health)
            
            # Keep only last 100 entries per service
            if len(self.health_history[service_name]) > 100:
                self.health_history[service_name] = self.health_history[service_name][-100:]
        
        self.last_check_time = datetime.now()
        return health_results
    
    def get_system_summary(self, health_results: Dict[str, HealthStatus]) -> Dict[str, Any]:
        """Generate system health summary"""
        total_services = len(health_results)
        healthy_services = len([h for h in health_results.values() if h.status == "healthy"])
        degraded_services = len([h for h in health_results.values() if h.status == "degraded"])
        unhealthy_services = len([h for h in health_results.values() if h.status == "unhealthy"])
        unknown_services = len([h for h in health_results.values() if h.status == "unknown"])
        
        # Determine overall system status
        if unhealthy_services == 0 and unknown_services == 0 and degraded_services == 0:
            overall_status = "healthy"
        elif unhealthy_services == 0 and unknown_services == 0:
            overall_status = "degraded"
        elif unhealthy_services > 0:
            overall_status = "unhealthy"
        else:
            overall_status = "unknown"
        
        # Calculate average response time
        valid_times = [h.response_time_ms for h in health_results.values() if h.response_time_ms > 0]
        avg_response_time = sum(valid_times) / len(valid_times) if valid_times else 0
        
        return {
            "overall_status": overall_status,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "unhealthy_services": unhealthy_services,
            "unknown_services": unknown_services,
            "average_response_time_ms": round(avg_response_time, 2),
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "uptime_percentage": round((healthy_services / total_services) * 100, 2) if total_services > 0 else 0
        }

# FastAPI Application
app = FastAPI(
    title="Health Monitor Service",
    version="1.0.0",
    description="Comprehensive system health monitoring for all services"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global health monitor instance
health_monitor = HealthMonitor()

@app.get("/health")
async def service_health():
    """Own service health check"""
    return {
        "status": "healthy",
        "service": "health-monitor",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health/all")
async def check_all_services():
    """Check all registered services"""
    try:
        health_results = await health_monitor.check_all_services()
        summary = health_monitor.get_system_summary(health_results)
        
        return {
            "summary": summary,
            "services": {name: asdict(health) for name, health in health_results.items()}
        }
    except Exception as e:
        logger.error(f"Error checking all services: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/health/service/{service_name}")
async def check_specific_service(service_name: str):
    """Check specific service health"""
    service_config = next((s for s in health_monitor.services if s.name == service_name), None)
    
    if not service_config:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    try:
        health_status = await health_monitor.check_service_health(service_config)
        return asdict(health_status)
    except Exception as e:
        logger.error(f"Error checking service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/health/history/{service_name}")
async def get_service_history(service_name: str, limit: int = 20):
    """Get health history for specific service"""
    if service_name not in health_monitor.health_history:
        raise HTTPException(status_code=404, detail=f"No history found for service '{service_name}'")
    
    history = health_monitor.health_history[service_name][-limit:]
    return {
        "service": service_name,
        "history_count": len(history),
        "history": [asdict(h) for h in history]
    }

@app.get("/health/summary")
async def get_health_summary():
    """Get system health summary without detailed checks"""
    if not health_monitor.last_check_time:
        return {"message": "No health checks performed yet", "last_check": None}
    
    # Use last known results if recent (< 5 minutes)
    if datetime.now() - health_monitor.last_check_time < timedelta(minutes=5):
        latest_results = {}
        for service_name, history in health_monitor.health_history.items():
            if history:
                latest_results[service_name] = history[-1]
        
        if latest_results:
            summary = health_monitor.get_system_summary(latest_results)
            return summary
    
    # Perform fresh check if no recent data
    health_results = await health_monitor.check_all_services()
    summary = health_monitor.get_system_summary(health_results)
    return summary

@app.get("/health/metrics")
async def get_health_metrics():
    """Get aggregated health metrics"""
    if not health_monitor.health_history:
        return {"message": "No metrics available"}
    
    metrics = {}
    for service_name, history in health_monitor.health_history.items():
        if not history:
            continue
            
        # Calculate service-specific metrics
        total_checks = len(history)
        healthy_checks = len([h for h in history if h.status == "healthy"])
        avg_response_time = sum(h.response_time_ms for h in history) / total_checks
        
        metrics[service_name] = {
            "total_checks": total_checks,
            "uptime_percentage": round((healthy_checks / total_checks) * 100, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "last_status": history[-1].status,
            "last_check": history[-1].timestamp
        }
    
    return {
        "metrics": metrics,
        "generated_at": datetime.now().isoformat()
    }

@app.get("/registry")
async def get_service_registry():
    """Get complete service registry with discovery"""
    try:
        # Update service registry with latest health checks
        await service_registry.check_all_services()
        
        return {
            "registry": service_registry.export_registry(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting service registry: {e}")
        raise HTTPException(status_code=500, detail=f"Registry access failed: {str(e)}")

@app.get("/registry/healthy")
async def get_healthy_services():
    """Get only healthy services from registry"""
    try:
        healthy_services = service_registry.get_healthy_services()
        
        return {
            "healthy_services": [
                {
                    "name": service.name,
                    "url": service.url,
                    "status": service.status.value,
                    "response_time_ms": service.response_time_ms,
                    "last_seen": service.last_seen.isoformat() if service.last_seen else None
                }
                for service in healthy_services
            ],
            "count": len(healthy_services),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting healthy services: {e}")
        raise HTTPException(status_code=500, detail=f"Registry access failed: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting Health Monitor Service v1.0.0")
    
    # Zentrale Konfiguration verwenden
    health_monitor_config = config.SERVICES["health_monitor"]
    uvicorn.run(
        app, 
        host=health_monitor_config["host"], 
        port=health_monitor_config["port"], 
        log_level="info"
    )