#!/usr/bin/env python3
"""
Diagnostic Service - FastAPI Application v6.1.0
Clean Architecture Implementation mit PostgreSQL Migration

CLEAN ARCHITECTURE v6.1.0 LAYERS:
✅ Domain Layer: Business Logic, Entities, Value Objects, Repository Interfaces
✅ Application Layer: Use Cases, Service Interfaces, Event Monitoring
✅ Infrastructure Layer: PostgreSQL Database Manager, External Services, Event Publishing
✅ Presentation Layer: FastAPI Controllers, Request/Response Models, HTTP Handling

MIGRATION v6.0.0 → v6.1.0:
- SQLite Repositories zu PostgreSQL Repositories Migration
- Central Database Manager Integration (database_connection_manager_v1_0_0_20250825)
- Multi-Schema Design: diagnostic_events, diagnostic_tests, system_health, module_communication
- Connection Pool Management für Performance

ARCHITECTURE COMPLIANCE v6.1.0:
✅ SOLID Principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
✅ Dependency Injection: Container mit PostgreSQL Database Manager
✅ Event-Driven Pattern: Diagnostic Events, System Health Events
✅ Repository Pattern: Multi-Repository Data Access mit PostgreSQL
✅ Use Case Pattern: Event Monitoring, Diagnostic Testing, Health Monitoring

FEATURES v6.1.0:
- Diagnostic Event Storage and Analysis (PostgreSQL)
- System Health Monitoring und Snapshots
- Diagnostic Test Execution und Results
- Module Communication Testing
- Automated Cleanup und Maintenance
- Comprehensive Health Checks
- FastAPI REST API mit OpenAPI Documentation
- Background Tasks für Long-running Operations

Code-Qualität: HÖCHSTE PRIORITÄT - Architecture Refactoring Specialist
Autor: Claude Code - Clean Architecture Implementation
Datum: 25. August 2025
Version: 6.1.0 (PostgreSQL Migration)
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/diagnostic_service.log')
    ]
)

logger = logging.getLogger(__name__)

# Import Clean Architecture Components
from infrastructure.container_v6_1_0 import DiagnosticServiceContainer
from presentation.models.diagnostic_models import (
    DiagnosticEventRequestDTO,
    DiagnosticEventResponseDTO,
    DiagnosticTestRequestDTO,
    DiagnosticTestResponseDTO,
    SystemHealthRequestDTO,
    SystemHealthResponseDTO,
    HealthCheckResponseDTO
)


# Global container instance
container = DiagnosticServiceContainer()


async def initialize_service() -> bool:
    """
    Initialize diagnostic service with database manager and schema
    
    Returns:
        True if service initialized successfully
    """
    try:
        logger.info("Initializing Diagnostic Service v6.1.0...")
        
        # Initialize container with database manager
        success = await container.initialize()
        if not success:
            logger.error("Failed to initialize diagnostic service container")
            return False
        
        # Verify database connection
        db_manager = container.get_database_manager()
        health = await db_manager.health_check()
        if not health.get('healthy', False):
            logger.error(f"Database manager unhealthy: {health}")
            return False
            
        logger.info("Diagnostic Service v6.1.0 initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Diagnostic service initialization failed: {e}")
        return False


async def shutdown_service():
    """Graceful service shutdown"""
    try:
        logger.info("Shutting down Diagnostic Service...")
        
        # Shutdown container and cleanup resources
        await container.shutdown()
        
        logger.info("Diagnostic Service shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during diagnostic service shutdown: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Startup
    logger.info("Starting up Diagnostic Service v6.1.0...")
    
    success = await initialize_service()
    if not success:
        logger.error("Failed to initialize diagnostic service - startup aborted")
        sys.exit(1)
    
    logger.info("Diagnostic Service v6.1.0 startup completed")
    
    yield
    
    # Shutdown
    await shutdown_service()


# FastAPI application with Clean Architecture
app = FastAPI(
    title="Diagnostic Service",
    description="Clean Architecture Implementation v6.1.0 - PostgreSQL Migration",
    version="6.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware for development/private usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private environment - broad CORS allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_container() -> DiagnosticServiceContainer:
    """Get container instance for dependency injection"""
    return container


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthCheckResponseDTO, 
         summary="Health Check", description="Service health status")
async def health_check(container: DiagnosticServiceContainer = Depends(get_container)):
    """
    Health check endpoint
    
    Returns comprehensive service health including:
    - Container status
    - Database manager status
    - Repository health
    - Component status
    """
    try:
        health_status = await container.health_check()
        
        # Determine overall health
        components_healthy = all(
            comp.get('status') in ['healthy', 'disabled', 'not_initialized'] 
            for comp in health_status.get('components', {}).values()
        )
        
        overall_status = 'healthy' if components_healthy else 'degraded'
        
        return HealthCheckResponseDTO(
            status=overall_status,
            service="diagnostic-service",
            version="6.1.0",
            database="PostgreSQL",
            timestamp=datetime.utcnow().isoformat(),
            components=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponseDTO(
            status="unhealthy",
            service="diagnostic-service", 
            version="6.1.0",
            database="PostgreSQL",
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )


@app.get("/api/v1/status", 
         summary="Service Status", description="Detailed service status")
async def get_service_status(container: DiagnosticServiceContainer = Depends(get_container)):
    """
    Get detailed service status
    
    Returns:
        Comprehensive service status information
    """
    try:
        health_status = await container.health_check()
        
        return JSONResponse({
            "service": "diagnostic-service",
            "version": "6.1.0",
            "architecture": "Clean Architecture",
            "database": "PostgreSQL",
            "migration": "v6.0.0 → v6.1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "container": health_status.get('container', {}),
            "health": health_status,
            "endpoints": {
                "events": "/api/v1/diagnostic/events",
                "tests": "/api/v1/diagnostic/tests", 
                "health_monitoring": "/api/v1/diagnostic/health",
                "maintenance": "/api/v1/diagnostic/maintenance",
                "status": "/api/v1/status",
                "health": "/health",
                "docs": "/docs"
            }
        })
        
    except Exception as e:
        logger.error(f"Status endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# =============================================================================
# DIAGNOSTIC EVENT ENDPOINTS
# =============================================================================

@app.post("/api/v1/diagnostic/events/store", response_model=DiagnosticEventResponseDTO,
          summary="Store Diagnostic Event", description="Store a diagnostic event")
async def store_diagnostic_event(
    request: DiagnosticEventRequestDTO,
    background_tasks: BackgroundTasks,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Store a diagnostic event
    
    Args:
        request: Diagnostic event data
        background_tasks: FastAPI background tasks
        
    Returns:
        DiagnosticEventResponseDTO with operation result
    """
    try:
        event_monitoring_use_case = container.get_event_monitoring_use_case()
        
        # Execute use case
        result = await event_monitoring_use_case.store_event(request.to_domain_entity())
        
        return DiagnosticEventResponseDTO(
            success=result,
            message="Event stored successfully" if result else "Failed to store event"
        )
        
    except Exception as e:
        logger.error(f"Store diagnostic event failed: {e}")
        raise HTTPException(status_code=500, detail=f"Store event failed: {str(e)}")


@app.get("/api/v1/diagnostic/events", response_model=List[DiagnosticEventResponseDTO],
         summary="Get Diagnostic Events", description="Retrieve diagnostic events")
async def get_diagnostic_events(
    limit: int = 100,
    event_type: Optional[str] = None,
    service_name: Optional[str] = None,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Get diagnostic events with filtering
    
    Args:
        limit: Maximum number of events to return
        event_type: Filter by event type
        service_name: Filter by service name
        
    Returns:
        List of diagnostic events
    """
    try:
        event_repository = container.get_event_repository()
        
        if service_name:
            events = await event_repository.get_events_by_service(service_name, limit)
        else:
            events = await event_repository.get_events(limit, event_type)
        
        return [
            DiagnosticEventResponseDTO(
                success=True,
                event_id=event.event_id,
                event_type=event.event_type,
                service_name=event.service_name,
                message=event.message,
                timestamp=event.timestamp.isoformat(),
                data=event.additional_data
            )
            for event in events
        ]
        
    except Exception as e:
        logger.error(f"Get diagnostic events failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get events failed: {str(e)}")


# =============================================================================
# DIAGNOSTIC TESTING ENDPOINTS
# =============================================================================

@app.post("/api/v1/diagnostic/tests/execute", response_model=DiagnosticTestResponseDTO,
          summary="Execute Diagnostic Test", description="Execute a diagnostic test")
async def execute_diagnostic_test(
    request: DiagnosticTestRequestDTO,
    background_tasks: BackgroundTasks,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Execute a diagnostic test
    
    Args:
        request: Test execution parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        DiagnosticTestResponseDTO with test results
    """
    try:
        diagnostic_testing_use_case = container.get_diagnostic_testing_use_case()
        
        # Execute test in background if requested
        if request.background_execution:
            background_tasks.add_task(
                diagnostic_testing_use_case.execute_test,
                request.to_domain_entity()
            )
            
            return DiagnosticTestResponseDTO(
                success=True,
                test_id=request.test_id,
                message="Test execution started in background"
            )
        else:
            # Execute synchronously
            result = await diagnostic_testing_use_case.execute_test(request.to_domain_entity())
            
            return DiagnosticTestResponseDTO(
                success=True,
                test_id=result.test_id,
                status=result.status.value,
                execution_time_ms=result.execution_time_ms,
                message="Test executed successfully"
            )
        
    except Exception as e:
        logger.error(f"Execute diagnostic test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@app.get("/api/v1/diagnostic/tests", response_model=List[DiagnosticTestResponseDTO],
         summary="Get Diagnostic Tests", description="Retrieve diagnostic test results")
async def get_diagnostic_tests(
    limit: int = 100,
    service_name: Optional[str] = None,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Get diagnostic test results
    
    Args:
        limit: Maximum number of tests to return
        service_name: Filter by service name
        
    Returns:
        List of diagnostic test results
    """
    try:
        test_repository = container.get_test_repository()
        
        if service_name:
            tests = await test_repository.get_tests_by_service(service_name)
        else:
            tests = await test_repository.get_tests(limit)
        
        return [
            DiagnosticTestResponseDTO(
                success=True,
                test_id=test.test_id,
                test_name=test.test_name,
                service_name=test.service_name,
                status=test.status.value,
                execution_time_ms=test.execution_time_ms,
                error_message=test.error_message,
                timestamp=test.created_at.isoformat()
            )
            for test in tests
        ]
        
    except Exception as e:
        logger.error(f"Get diagnostic tests failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get tests failed: {str(e)}")


# =============================================================================
# SYSTEM HEALTH ENDPOINTS
# =============================================================================

@app.post("/api/v1/diagnostic/health/snapshot", response_model=SystemHealthResponseDTO,
          summary="Create Health Snapshot", description="Create system health snapshot")
async def create_health_snapshot(
    request: SystemHealthRequestDTO,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Create system health snapshot
    
    Args:
        request: Health snapshot parameters
        
    Returns:
        SystemHealthResponseDTO with snapshot result
    """
    try:
        system_health_use_case = container.get_system_health_use_case()
        
        # Create health snapshot
        snapshot = await system_health_use_case.create_health_snapshot(
            service_name=request.service_name,
            component_checks=request.component_checks or []
        )
        
        return SystemHealthResponseDTO(
            success=True,
            snapshot_id=snapshot.snapshot_id,
            service_name=snapshot.service_name,
            overall_status=snapshot.overall_status.value,
            message="Health snapshot created successfully"
        )
        
    except Exception as e:
        logger.error(f"Create health snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health snapshot failed: {str(e)}")


@app.get("/api/v1/diagnostic/health/{service_name}", response_model=List[SystemHealthResponseDTO],
         summary="Get Health History", description="Get health history for service")
async def get_health_history(
    service_name: str,
    limit: int = 50,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Get health history for service
    
    Args:
        service_name: Name of service
        limit: Maximum number of snapshots
        
    Returns:
        List of health snapshots
    """
    try:
        health_repository = container.get_health_repository()
        
        snapshots = await health_repository.get_recent_snapshots(service_name, limit)
        
        return [
            SystemHealthResponseDTO(
                success=True,
                snapshot_id=snapshot.snapshot_id,
                service_name=snapshot.service_name,
                overall_status=snapshot.overall_status.value,
                component_statuses={k: v.value for k, v in snapshot.component_statuses.items()},
                timestamp=snapshot.timestamp.isoformat()
            )
            for snapshot in snapshots
        ]
        
    except Exception as e:
        logger.error(f"Get health history failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get health history failed: {str(e)}")


# =============================================================================
# MAINTENANCE ENDPOINTS
# =============================================================================

@app.post("/api/v1/diagnostic/maintenance/cleanup",
          summary="Cleanup Old Data", description="Cleanup old diagnostic data")
async def cleanup_old_data(
    days_old: int = 30,
    background_tasks: BackgroundTasks,
    container: DiagnosticServiceContainer = Depends(get_container)
):
    """
    Cleanup old diagnostic data
    
    Args:
        days_old: Age threshold in days
        background_tasks: FastAPI background tasks
        
    Returns:
        Cleanup operation result
    """
    try:
        maintenance_use_case = container.get_diagnostic_maintenance_use_case()
        
        # Run cleanup in background
        background_tasks.add_task(
            maintenance_use_case.cleanup_old_data,
            days_old
        )
        
        return JSONResponse({
            "success": True,
            "message": f"Cleanup of data older than {days_old} days started in background",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Cleanup operation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# =============================================================================
# DEVELOPMENT ENDPOINTS
# =============================================================================

@app.get("/api/v1/dev/database-status",
         summary="Database Status", description="Database manager status")
async def get_database_status(container: DiagnosticServiceContainer = Depends(get_container)):
    """Get database manager status for development/debugging"""
    try:
        db_manager = container.get_database_manager()
        health = await db_manager.health_check()
        
        return JSONResponse({
            "database_manager": {
                "type": "centralized_postgresql",
                "version": "v1.0.0",
                "health": health,
                "connection_pool": health.get("connection_pool", {}),
                "configuration": health.get("configuration", {})
            },
            "repositories": {
                "event_repository": "PostgreSQL",
                "test_repository": "PostgreSQL",
                "health_repository": "PostgreSQL",
                "communication_repository": "PostgreSQL"
            },
            "migration": "SQLite → PostgreSQL",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database status failed: {str(e)}")


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum} - initiating graceful shutdown...")
    # FastAPI lifespan will handle the actual cleanup


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    logger.info("Starting Diagnostic Service v6.1.0...")
    
    # Run FastAPI application
    uvicorn.run(
        "main_v6_1_0:app",
        host="0.0.0.0",
        port=8019,
        reload=False,  # Production mode
        access_log=True,
        log_level="info"
    )