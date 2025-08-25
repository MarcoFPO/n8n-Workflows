#!/usr/bin/env python3
"""
Diagnostic Service - Main FastAPI Application
CLEAN ARCHITECTURE v6.0.0 - Complete Implementation

Modern diagnostic monitoring with Clean Architecture patterns
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import uvicorn
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Path, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Import Management - CLEAN ARCHITECTURE
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from standard_import_manager_v1_0_0_20250824 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()

# Infrastructure
from infrastructure.container import diagnostic_container
from presentation.controllers.diagnostic_controller import DiagnosticController
from presentation.models.diagnostic_models import (
    StartMonitoringRequest, CreateTestRequest, SendTestMessageRequest, 
    EventFilterRequest, MonitoringActionEnum
)

# External dependencies
from event_bus import EventBusConnector, EventBusConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
diagnostic_controller: Optional[DiagnosticController] = None
periodic_health_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    logger.info("🔧 Diagnostic Service v6.0.0 starting up...")
    
    try:
        # Configure container
        config = {
            'events_database_path': os.getenv('DIAGNOSTIC_EVENTS_DB', 'diagnostic_events.db'),
            'tests_database_path': os.getenv('DIAGNOSTIC_TESTS_DB', 'diagnostic_tests.db'), 
            'health_database_path': os.getenv('DIAGNOSTIC_HEALTH_DB', 'diagnostic_health.db'),
            'use_real_event_bus': os.getenv('USE_REAL_EVENT_BUS', 'false').lower() == 'true',
            'simulate_event_failures': os.getenv('SIMULATE_FAILURES', 'false').lower() == 'true',
            'event_failure_rate': float(os.getenv('EVENT_FAILURE_RATE', '0.0'))
        }
        
        # Initialize Event Bus if enabled
        if config['use_real_event_bus']:
            try:
                event_bus_config = EventBusConfig()
                event_bus_connector = EventBusConnector("diagnostic_service", event_bus_config)
                config['event_bus_connector'] = event_bus_connector
                logger.info("✅ Real Event Bus connector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Event Bus, using mock: {e}")
                config['use_real_event_bus'] = False
        
        diagnostic_container.configure(config)
        
        # Initialize container
        initialization_success = await diagnostic_container.initialize()
        if not initialization_success:
            raise RuntimeError("Container initialization failed")
        
        # Create controller
        global diagnostic_controller
        diagnostic_controller = DiagnosticController(diagnostic_container)
        
        # Start periodic health monitoring
        global periodic_health_task
        periodic_health_task = asyncio.create_task(periodic_health_monitoring())
        
        logger.info("✅ Diagnostic Service v6.0.0 startup completed successfully")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    finally:
        # Shutdown cleanup
        logger.info("🔧 Shutting down Diagnostic Service...")
        
        # Cancel periodic task
        if periodic_health_task and not periodic_health_task.done():
            periodic_health_task.cancel()
            try:
                await periodic_health_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup container
        if diagnostic_container.initialized:
            await diagnostic_container.cleanup()
            
        logger.info("✅ Diagnostic Service shutdown completed")


async def periodic_health_monitoring():
    """Background task für periodic health monitoring"""
    try:
        # Wait for services to be fully ready
        await asyncio.sleep(5)
        
        while True:
            try:
                if diagnostic_controller:
                    health_use_case = diagnostic_container.get_service('system_health_use_case')
                    if health_use_case:
                        # Generate periodic health snapshot
                        await health_use_case.generate_health_snapshot()
                        logger.debug("Periodic health snapshot generated")
                
                # Wait 5 minutes before next health check
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Periodic health monitoring error: {e}")
                await asyncio.sleep(60)  # Shorter retry interval on error
                
    except asyncio.CancelledError:
        logger.info("Periodic health monitoring stopped")


# Initialize FastAPI app
app = FastAPI(
    title="🔧 Diagnostic Service",
    description="""
    **Clean Architecture v6.0.0 - Event Bus Monitoring & Testing Service**
    
    Advanced diagnostic capabilities for the Aktienanalyse Ecosystem:
    
    ## 🎯 Core Features
    - **Event Monitoring**: Real-time event bus monitoring with error detection
    - **Module Testing**: Automated diagnostic tests for all system modules  
    - **System Health**: Comprehensive health monitoring and trend analysis
    - **Performance Analytics**: Statistical analysis and reporting
    - **Clean Architecture**: Complete 4-layer separation with SOLID principles
    
    ## 🏗️ Architecture
    - **Domain Layer**: Rich entities, value objects, and repository interfaces
    - **Application Layer**: Use cases with business logic orchestration
    - **Infrastructure Layer**: SQLite persistence, Event Bus integration
    - **Presentation Layer**: FastAPI controllers with comprehensive validation
    
    ## 📊 Integration
    - **Real Event Bus**: Production Event Bus integration with fallback
    - **SQLite Storage**: High-performance local persistence with indices
    - **Background Processing**: Automatic health monitoring and cleanup
    - **Domain Events**: Event-driven architecture with observability
    """,
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Angepasst für privaten Gebrauch
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get controller
async def get_controller() -> DiagnosticController:
    """Dependency to get diagnostic controller"""
    if diagnostic_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return diagnostic_controller


# Root Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Service information and navigation"""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Diagnostic Service v6.0.0</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }}
            .header {{ color: #2563eb; margin-bottom: 30px; }}
            .section {{ margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px; }}
            .endpoint {{ margin: 8px 0; }}
            .endpoint a {{ color: #059669; text-decoration: none; }}
            .endpoint a:hover {{ text-decoration: underline; }}
            .status {{ color: #16a34a; font-weight: bold; }}
            .architecture {{ color: #7c3aed; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔧 Diagnostic Service v6.0.0</h1>
            <p><strong class="architecture">Clean Architecture Implementation</strong></p>
            <p class="status">Status: ✅ Operational</p>
        </div>
        
        <div class="section">
            <h2>📚 API Documentation</h2>
            <div class="endpoint"><a href="/docs">OpenAPI Documentation (Swagger UI)</a></div>
            <div class="endpoint"><a href="/redoc">Alternative Documentation (ReDoc)</a></div>
        </div>
        
        <div class="section">
            <h2>📊 Monitoring & Statistics</h2>
            <div class="endpoint"><a href="/monitoring/statistics">Event Monitoring Statistics</a></div>
            <div class="endpoint"><a href="/health/status">System Health Status</a></div>
            <div class="endpoint"><a href="/health/trend?hours=24">24-Hour Health Trend</a></div>
        </div>
        
        <div class="section">
            <h2>🧪 Testing & Development</h2>
            <div class="endpoint"><a href="/testing/results">Recent Test Results</a></div>
            <div class="endpoint"><a href="/dev/container-status">Service Container Status</a></div>
            <div class="endpoint"><a href="/dev/health-report">Detailed Health Report</a></div>
        </div>
        
        <div class="section">
            <h2>🎯 Quick Actions</h2>
            <p>Use the API endpoints to:</p>
            <ul>
                <li><strong>Start Monitoring:</strong> POST /monitoring/start</li>
                <li><strong>Test Module:</strong> POST /testing/communication/{{module}}</li>
                <li><strong>Send Test Message:</strong> POST /testing/message</li>
                <li><strong>Run Maintenance:</strong> POST /maintenance/cleanup</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>⚡ Service Info</h2>
            <p><strong>Version:</strong> 6.0.0 (Clean Architecture)</p>
            <p><strong>Started:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Architecture:</strong> Domain + Application + Infrastructure + Presentation</p>
            <p><strong>Persistence:</strong> SQLite with advanced indexing</p>
            <p><strong>Integration:</strong> Event Bus + Domain Events</p>
        </div>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check(controller: DiagnosticController = Depends(get_controller)):
    """Basic health check endpoint"""
    try:
        container_status = diagnostic_container.get_container_status()
        
        if container_status['initialized'] and len(container_status['failed_services']) == 0:
            return {
                "status": "healthy",
                "service": "diagnostic_service", 
                "version": "6.0.0",
                "architecture": "clean_architecture",
                "container_healthy": True,
                "active_services": len(container_status['started_services']),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "diagnostic_service",
                    "version": "6.0.0", 
                    "container_healthy": False,
                    "failed_services": container_status['failed_services'],
                    "initialization_error": container_status.get('initialization_error'),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "diagnostic_service",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Event Monitoring Endpoints
@app.post("/monitoring/start")
async def start_monitoring(
    request: StartMonitoringRequest,
    controller: DiagnosticController = Depends(get_controller)
):
    """Start event monitoring for specified event types"""
    return await controller.start_monitoring(request)


@app.post("/monitoring/stop")
async def stop_monitoring(
    controller: DiagnosticController = Depends(get_controller)
):
    """Stop event monitoring"""
    return await controller.stop_monitoring()


@app.get("/monitoring/statistics")
async def get_monitoring_statistics(
    controller: DiagnosticController = Depends(get_controller)
):
    """Get current event monitoring statistics"""
    return await controller.get_monitoring_statistics()


@app.get("/monitoring/events")
async def get_recent_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    source: Optional[str] = Query(None, description="Filter by source"),
    error_only: bool = Query(False, description="Show only error events"),
    max_age_seconds: Optional[int] = Query(None, description="Maximum event age in seconds"),
    limit: int = Query(50, description="Maximum events to return", ge=1, le=1000),
    controller: DiagnosticController = Depends(get_controller)
):
    """Get recent captured events with filtering options"""
    filter_params = EventFilterRequest(
        event_type=event_type,
        source=source,
        error_only=error_only,
        max_age_seconds=max_age_seconds,
        limit=limit
    )
    return await controller.get_recent_events(filter_params)


# Diagnostic Testing Endpoints
@app.post("/testing/create")
async def create_test(
    request: CreateTestRequest,
    controller: DiagnosticController = Depends(get_controller)
):
    """Create and execute diagnostic test"""
    return await controller.create_test(request)


@app.post("/testing/communication/{module_name}")
async def test_module_communication(
    module_name: str = Path(..., description="Module name to test"),
    controller: DiagnosticController = Depends(get_controller)
):
    """Test communication with specific module"""
    return await controller.test_module_communication(module_name)


@app.post("/testing/message")
async def send_test_message(
    request: SendTestMessageRequest,
    controller: DiagnosticController = Depends(get_controller)
):
    """Send test message to target module"""
    return await controller.send_test_message(request)


@app.get("/testing/results")
async def get_test_results(
    test_id: Optional[str] = Query(None, description="Specific test ID to retrieve"),
    controller: DiagnosticController = Depends(get_controller)
):
    """Get diagnostic test results"""
    return await controller.get_test_results(test_id)


# System Health Endpoints
@app.get("/health/status")
async def get_system_health(
    controller: DiagnosticController = Depends(get_controller)
):
    """Get current system health snapshot"""
    return await controller.get_system_health()


@app.get("/health/trend")
async def get_health_trend(
    hours: int = Query(24, description="Timeframe in hours", ge=1, le=168),
    controller: DiagnosticController = Depends(get_controller)
):
    """Get system health trend over specified hours"""
    return await controller.get_health_trend(hours)


# Maintenance Endpoints
@app.post("/maintenance/cleanup")
async def perform_maintenance_cleanup(
    background_tasks: BackgroundTasks,
    controller: DiagnosticController = Depends(get_controller)
):
    """Perform diagnostic data cleanup"""
    return await controller.perform_maintenance_cleanup(background_tasks)


@app.get("/maintenance/storage-stats")
async def get_storage_statistics(
    controller: DiagnosticController = Depends(get_controller)
):
    """Get diagnostic data storage statistics"""
    return await controller.get_storage_statistics()


# Development/Debug Endpoints
@app.get("/dev/container-status")
async def get_container_status(
    controller: DiagnosticController = Depends(get_controller)
):
    """Get dependency injection container status"""
    return await controller.get_container_status()


@app.get("/dev/health-report")
async def get_detailed_health_report(
    controller: DiagnosticController = Depends(get_controller)
):
    """Get detailed health report for all services"""
    return await controller.get_detailed_health_report()


@app.post("/dev/reset-service")
async def reset_service_state(
    controller: DiagnosticController = Depends(get_controller)
):
    """Reset service state (development endpoint)"""
    return await controller.reset_service_state()


@app.get("/dev/service-info")
async def get_service_info(
    controller: DiagnosticController = Depends(get_controller)
):
    """Get diagnostic service information"""
    return controller.get_service_info()


# Test Scenarios Endpoints (Legacy compatibility)
@app.get("/test/scenarios")
async def get_test_scenarios():
    """Get available test scenarios (legacy compatibility)"""
    return {
        "success": True,
        "scenarios": [
            {
                "name": "analysis_test",
                "description": "Test analysis module connectivity and response",
                "test_type": "communication",
                "target_module": "analysis_module"
            },
            {
                "name": "portfolio_test", 
                "description": "Test portfolio module with sample data",
                "test_type": "message",
                "target_module": "portfolio_module"
            },
            {
                "name": "trading_test",
                "description": "Test trading module communication",
                "test_type": "ping",
                "target_module": "trading_module"
            },
            {
                "name": "system_health_test",
                "description": "Comprehensive system health evaluation",
                "test_type": "custom",
                "target_module": "all_modules"
            }
        ]
    }


@app.post("/test/scenario/{scenario_name}")
async def run_test_scenario(
    scenario_name: str = Path(..., description="Test scenario name"),
    controller: DiagnosticController = Depends(get_controller)
):
    """Run predefined test scenario (legacy compatibility)"""
    scenario_configs = {
        "analysis_test": {
            "test_name": "Analysis Module Scenario Test",
            "test_type": "communication",
            "target_module": "analysis_module",
            "test_data": {"symbol": "AAPL", "scenario": True}
        },
        "portfolio_test": {
            "test_name": "Portfolio Module Scenario Test", 
            "test_type": "message",
            "target_module": "portfolio_module",
            "test_data": {"portfolio_test": True}
        },
        "trading_test": {
            "test_name": "Trading Module Scenario Test",
            "test_type": "ping", 
            "target_module": "trading_module",
            "test_data": {"trading_ping": True}
        }
    }
    
    if scenario_name not in scenario_configs:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_name}")
    
    config = scenario_configs[scenario_name]
    request = CreateTestRequest(**config)
    
    result = await controller.create_test(request)
    
    return {
        "success": result.success,
        "scenario": scenario_name,
        "executed": True,
        "test_id": result.test_id,
        "result": result.test_result
    }


# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if os.getenv('DEBUG') == 'true' else "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="🔧 Diagnostic Service API",
        version="6.0.0",
        description="""
        Clean Architecture v6.0.0 - Event Bus Monitoring & Testing Service
        
        Complete diagnostic capabilities with modern architecture patterns.
        """,
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("DIAGNOSTIC_SERVICE_PORT", "8013"))
    
    logger.info(f"🚀 Starting Diagnostic Service v6.0.0 on port {port}")
    logger.info("🏗️ Clean Architecture Implementation")
    logger.info("📊 Event Bus Monitoring & System Diagnostics")
    
    uvicorn.run(
        "main_v6_0_0:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )