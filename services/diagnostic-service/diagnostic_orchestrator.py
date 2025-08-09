#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic Service Orchestrator
FastAPI Service für Event-Bus Diagnostics und Testing
"""

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog
import sys
import os

# Event-Bus und Diagnostic Module importieren
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from event_bus import EventBusConnector, EventBusConfig
from diagnostic_module import DiagnosticModule

logger = structlog.get_logger(__name__)

# Pydantic Models für API
class TestMessageRequest(BaseModel):
    message_type: str = "analysis"  # analysis, trading, portfolio, custom
    target_module: Optional[str] = None
    event_type: Optional[str] = None
    custom_data: Dict[str, Any] = {}

class DiagnosticCommand(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}


class DiagnosticOrchestrator:
    """
    Orchestrator für Diagnostic Service
    Verwaltet das Diagnostic Module und stellt REST-API bereit
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="Aktienanalyse Diagnostic Service",
            description="Event-Bus Monitoring and Testing Service",
            version="1.0.0"
        )
        self.diagnostic_module: Optional[DiagnosticModule] = None
        self.event_bus: Optional[EventBusConnector] = None
        self.service_healthy = False
        
        # CORS Middleware hinzufügen
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # API Routes registrieren
        self._register_routes()
    
    def _register_routes(self):
        """Registriere alle API Routes"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Service startup"""
            await self._initialize_service()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Service shutdown"""
            await self._shutdown_service()
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            if not self.service_healthy:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "service": "diagnostic_service",
                        "diagnostic_module": False
                    }
                )
            
            # Get detailed health from diagnostic module
            health_result = await self.diagnostic_module.process_business_logic({
                'command': 'get_system_health'
            })
            
            return {
                "status": "healthy",
                "service": "diagnostic_service",
                "diagnostic_module": True,
                "system_health": health_result.get('data', {})
            }
        
        @self.app.get("/")
        async def root():
            """Root endpoint with service info"""
            return HTMLResponse(content="""
            <html>
                <head><title>Diagnostic Service</title></head>
                <body>
                    <h1>🔧 Aktienanalyse Diagnostic Service</h1>
                    <h2>Event-Bus Monitoring & Testing</h2>
                    <ul>
                        <li><a href="/docs">API Documentation</a></li>
                        <li><a href="/health">Health Check</a></li>
                        <li><a href="/monitor/statistics">Monitor Statistics</a></li>
                        <li><a href="/monitor/events">Recent Events</a></li>
                    </ul>
                    <p>Service Status: """ + ("✅ Healthy" if self.service_healthy else "❌ Unhealthy") + """</p>
                </body>
            </html>
            """)
        
        @self.app.get("/monitor/statistics")
        async def get_monitoring_statistics():
            """Get current event monitoring statistics"""
            if not self.service_healthy:
                raise HTTPException(status_code=503, detail="Service not healthy")
            
            result = await self.diagnostic_module.process_business_logic({
                'command': 'get_statistics'
            })
            
            if result.get('success'):
                return result['data']
            else:
                raise HTTPException(status_code=500, detail=result.get('error'))
        
        @self.app.get("/monitor/events")
        async def get_recent_events(limit: int = 50):
            """Get recent captured events"""
            if not self.service_healthy:
                raise HTTPException(status_code=503, detail="Service not healthy")
            
            result = await self.diagnostic_module.process_business_logic({
                'command': 'get_recent_events',
                'limit': limit
            })
            
            if result.get('success'):
                return result['data']
            else:
                raise HTTPException(status_code=500, detail=result.get('error'))
        
        @self.app.post("/test/send-message")
        async def send_test_message(request: TestMessageRequest):
            """Send test message to modules"""
            if not self.service_healthy:
                raise HTTPException(status_code=503, detail="Service not healthy")
                
            result = await self.diagnostic_module.process_business_logic({
                'command': 'send_test_message',
                'message_type': request.message_type,
                'target_module': request.target_module,
                'event_type': request.event_type,
                'custom_data': request.custom_data
            })
            
            if result.get('success'):
                return result['data']
            else:
                raise HTTPException(status_code=500, detail=result.get('error'))
        
        @self.app.post("/test/module-communication/{module_name}")
        async def test_module_communication(module_name: str):
            """Test communication with specific module"""
            if not self.service_healthy:
                raise HTTPException(status_code=503, detail="Service not healthy")
            
            result = await self.diagnostic_module.process_business_logic({
                'command': 'test_module_communication',
                'target_module': module_name
            })
            
            if result.get('success'):
                return result['data']
            else:
                raise HTTPException(status_code=500, detail=result.get('error'))
        
        @self.app.post("/monitor/control/{action}")
        async def control_monitoring(action: str):
            """Control event monitoring (start/stop/clear)"""
            if not self.service_healthy:
                raise HTTPException(status_code=503, detail="Service not healthy")
            
            if action == "start":
                await self.diagnostic_module.start_monitoring()
                return {"status": "monitoring_started"}
            elif action == "stop":
                await self.diagnostic_module.stop_monitoring()
                return {"status": "monitoring_stopped"}
            elif action == "clear":
                await self.diagnostic_module.clear_captured_events()
                return {"status": "events_cleared"}
            else:
                raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
        
        @self.app.get("/test/scenarios")
        async def get_test_scenarios():
            """Get available test scenarios"""
            return {
                "scenarios": [
                    {
                        "name": "analysis_test",
                        "description": "Test analysis module with AAPL data",
                        "message_type": "analysis",
                        "target_module": "analysis_module"
                    },
                    {
                        "name": "trading_test", 
                        "description": "Test trading module with market order",
                        "message_type": "trading",
                        "target_module": "order_module"
                    },
                    {
                        "name": "portfolio_test",
                        "description": "Test portfolio module with sample portfolio",
                        "message_type": "portfolio", 
                        "target_module": "portfolio_module"
                    },
                    {
                        "name": "intelligence_test",
                        "description": "Test intelligence module with trigger event",
                        "message_type": "custom",
                        "event_type": "intelligence.triggered",
                        "target_module": "intelligence_module"
                    }
                ]
            }
        
        @self.app.post("/test/scenario/{scenario_name}")
        async def run_test_scenario(scenario_name: str):
            """Run predefined test scenario"""
            if not self.service_healthy:
                raise HTTPException(status_code=503, detail="Service not healthy")
            
            scenarios = {
                "analysis_test": {
                    "message_type": "analysis",
                    "target_module": "analysis_module",
                    "custom_data": {"symbol": "AAPL"}
                },
                "trading_test": {
                    "message_type": "trading", 
                    "target_module": "order_module",
                    "custom_data": {"order_type": "TEST_MARKET"}
                },
                "portfolio_test": {
                    "message_type": "portfolio",
                    "target_module": "portfolio_module"
                },
                "intelligence_test": {
                    "message_type": "custom",
                    "event_type": "intelligence.triggered",
                    "target_module": "intelligence_module",
                    "custom_data": {"test_intelligence": "recommendation_test"}
                }
            }
            
            if scenario_name not in scenarios:
                raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_name}")
            
            scenario = scenarios[scenario_name]
            result = await self.diagnostic_module.process_business_logic({
                'command': 'send_test_message',
                **scenario
            })
            
            if result.get('success'):
                return {
                    "scenario": scenario_name,
                    "executed": True,
                    "result": result['data']
                }
            else:
                raise HTTPException(status_code=500, detail=result.get('error'))

    async def _initialize_service(self):
        """Initialize diagnostic service"""
        try:
            logger.info("🔧 Initializing Diagnostic Service...")
            
            # Event-Bus Connection initialisieren
            config = EventBusConfig()
            self.event_bus = EventBusConnector("diagnostic_service", config)
            
            # Diagnostic Module initialisieren
            self.diagnostic_module = DiagnosticModule(self.event_bus)
            initialization_success = await self.diagnostic_module._initialize_module()
            
            if initialization_success:
                self.service_healthy = True
                logger.info("✅ Diagnostic Service initialized successfully")
            else:
                logger.error("❌ Diagnostic Module initialization failed")
                
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            self.service_healthy = False

    async def _shutdown_service(self):
        """Shutdown diagnostic service"""
        try:
            logger.info("🔧 Shutting down Diagnostic Service...")
            
            if self.diagnostic_module:
                await self.diagnostic_module.stop_monitoring()
            
            if self.event_bus:
                # Cleanup event bus connection if needed
                pass
                
            logger.info("✅ Diagnostic Service shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Service shutdown error: {e}")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    orchestrator = DiagnosticOrchestrator()
    return orchestrator.app


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("DIAGNOSTIC_SERVICE_PORT", "8013"))
    
    logger.info(f"🚀 Starting Diagnostic Service on port {port}")
    
    uvicorn.run(
        "diagnostic_orchestrator:create_app",
        host="0.0.0.0",
        port=port,
        factory=True,
        reload=False,
        log_level="info"
    )