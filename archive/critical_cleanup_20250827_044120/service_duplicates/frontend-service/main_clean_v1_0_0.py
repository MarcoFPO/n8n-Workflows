#!/usr/bin/env python3
"""
Frontend Service Clean Architecture Entry Point v1.0.0
Modernized Frontend Service Implementation

CLEAN ARCHITECTURE MIGRATION:
- 1,500+ Lines God Object → Clean Architecture 4-Layer Pattern
- SOLID Principles Implementation
- Dependency Injection Container
- Zero-Downtime Migration Ready

ARCHITECTURE LAYERS:
- Domain: Entities, Value Objects, Domain Services
- Application: Use Cases, Interfaces, DTOs
- Infrastructure: HTTP Clients, Configuration, External Services  
- Presentation: Controllers, Templates, HTTP Layer

SUCCESS TEMPLATE: Based on ML-Analytics Migration (3,496 → Clean Architecture v3.0)

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0 - Clean Architecture Implementation
"""

import asyncio
import logging
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root to Python path for imports
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Clean Architecture Imports
from infrastructure.container import FrontendServiceContainer, FrontendContainerFactory
from domain.value_objects.timeframe_vo import TimeframeValueObject
from application.use_cases.dashboard_use_cases import GetDashboardUseCase, GetSystemStatusUseCase
from application.interfaces.http_client_interface import IHTTPClient
from application.interfaces.template_service_interface import ITemplateService


# =============================================================================
# GLOBAL CONTAINER & LOGGER
# =============================================================================

# Global dependency injection container
_container: FrontendServiceContainer = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/opt/aktienanalyse-ökosystem/logs/frontend-service-clean.log')
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# FASTAPI LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Manager - Clean Architecture Pattern
    
    RESPONSIBILITIES:
    - Initialize Dependency Injection Container
    - Setup all service dependencies
    - Graceful shutdown coordination
    """
    global _container
    
    try:
        # Startup Phase
        logger.info("🚀 Starting Frontend Service Clean Architecture v1.0.0")
        
        # Create and initialize container
        _container = FrontendContainerFactory.create_production_container()
        await _container.initialize()
        
        config = _container.get_config()
        
        logger.info(f"✅ Container initialized successfully")
        logger.info(f"📊 Services configured: {len(config.get_service_configurations())}")
        logger.info(f"⚙️ Environment: {config.get_environment().value}")
        logger.info(f"🔧 Version: {config.get_version()}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Container initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise
        
    finally:
        # Shutdown Phase
        logger.info("🛑 Shutting down Frontend Service Clean Architecture")
        
        if _container:
            try:
                await _container.shutdown()
                logger.info("✅ Container shutdown completed")
            except Exception as e:
                logger.error(f"❌ Container shutdown error: {str(e)}")


# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="Frontend Service - Clean Architecture",
    version="1.0.0",
    description="Clean Architecture Implementation - Modernized from 1,500 Line God Object",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware (will be configured from container)
# Temporarily add basic CORS - will be replaced by configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# DEPENDENCY PROVIDERS (Clean Architecture Pattern)
# =============================================================================

async def get_container() -> FrontendServiceContainer:
    """Get dependency injection container"""
    if _container is None or not _container.is_initialized():
        raise HTTPException(status_code=503, detail="Service initializing")
    return _container


async def get_dashboard_use_case(container: FrontendServiceContainer = Depends(get_container)) -> GetDashboardUseCase:
    """Get Dashboard Use Case dependency"""
    return container.get_dashboard_use_case()


async def get_system_status_use_case(container: FrontendServiceContainer = Depends(get_container)) -> GetSystemStatusUseCase:
    """Get System Status Use Case dependency"""
    return container.get_system_status_use_case()


async def get_http_client(container: FrontendServiceContainer = Depends(get_container)) -> IHTTPClient:
    """Get HTTP Client dependency"""
    return container.get_http_client()


async def get_template_service(container: FrontendServiceContainer = Depends(get_container)) -> ITemplateService:
    """Get Template Service dependency"""
    return container.get_template_service()


# =============================================================================
# ROUTE HANDLERS (Clean Architecture Controllers)
# =============================================================================

@app.get("/", response_class=HTMLResponse, summary="Dashboard Homepage - Clean Architecture")
async def dashboard(
    timeframe: str = "1M",
    dashboard_use_case: GetDashboardUseCase = Depends(get_dashboard_use_case),
    container: FrontendServiceContainer = Depends(get_container)
) -> str:
    """
    Dashboard Homepage Handler - Clean Architecture Implementation
    
    CLEAN ARCHITECTURE FLOW:
    Controller → Use Case → Domain Service → Entity → Value Object
    """
    try:
        logger.info(f"Dashboard request received - timeframe: {timeframe}")
        
        # Get dashboard entity from container
        dashboard_entity = container.get_dashboard_entity()
        
        # Execute dashboard use case
        dashboard_html = await dashboard_use_case.execute(
            dashboard_entity=dashboard_entity,
            timeframe_code=timeframe
        )
        
        logger.info("Dashboard rendered successfully")
        return dashboard_html
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@app.get("/prognosen", response_class=HTMLResponse, summary="KI-Prognosen Interface - Clean Architecture")
async def prognosen(
    timeframe: str = "1M",
    nav_timestamp: int = None,
    nav_direction: str = None,
    http_client: IHTTPClient = Depends(get_http_client),
    template_service: ITemplateService = Depends(get_template_service),
    container: FrontendServiceContainer = Depends(get_container)
) -> str:
    """
    KI-Prognosen Interface Handler - Clean Architecture Implementation
    
    NOTE: Temporarily using simplified implementation
    TODO: Create dedicated PrognoseUseCase in next iteration
    """
    try:
        logger.info(f"Prognosen request - timeframe: {timeframe}")
        
        # Create timeframe value object
        timeframe_vo = TimeframeValueObject(timeframe)
        nav_periods = timeframe_vo.calculate_navigation_periods(nav_timestamp, nav_direction)
        
        # Get configuration
        config = container.get_config()
        
        # Build prediction URL
        service_urls = config.get_service_urls()
        prediction_url = f"{service_urls['data_processing']}/api/v1/data/predictions?timeframe={timeframe}"
        
        # Fetch prediction data
        prediction_response = await http_client.get(prediction_url)
        
        # Render template (simplified for migration phase)
        content = await _render_prognosen_content(
            timeframe_vo, nav_periods, prediction_response, template_service
        )
        
        dashboard_html = await template_service.render_base_template(
            title="KI-Prognosen",
            content=content
        )
        
        logger.info("Prognosen rendered successfully")
        return dashboard_html
        
    except Exception as e:
        logger.error(f"Prognosen error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Prognosen error: {str(e)}")


@app.get("/vergleichsanalyse", response_class=HTMLResponse, summary="SOLL-IST Vergleichsanalyse - Clean Architecture")
async def vergleichsanalyse(
    timeframe: str = "1M",
    nav_timestamp: int = None,
    nav_direction: str = None,
    http_client: IHTTPClient = Depends(get_http_client),
    template_service: ITemplateService = Depends(get_template_service),
    container: FrontendServiceContainer = Depends(get_container)
) -> str:
    """
    SOLL-IST Vergleichsanalyse Handler - Clean Architecture Implementation
    
    NOTE: Temporarily using simplified implementation
    TODO: Create dedicated VergleichsanalyseUseCase in next iteration
    """
    try:
        logger.info(f"Vergleichsanalyse request - timeframe: {timeframe}")
        
        # Create timeframe value object
        timeframe_vo = TimeframeValueObject(timeframe)
        nav_periods = timeframe_vo.calculate_navigation_periods(nav_timestamp, nav_direction)
        
        # Get timeframe configurations
        config = container.get_config()
        vergleichsanalyse_timeframes = config.get_vergleichsanalyse_timeframes()
        
        if timeframe not in vergleichsanalyse_timeframes:
            timeframe = "1M"  # Fallback
        
        # Fetch comparison data
        comparison_url = vergleichsanalyse_timeframes[timeframe]["url"]
        comparison_response = await http_client.get(comparison_url)
        
        # Render template (simplified for migration phase)
        content = await _render_vergleichsanalyse_content(
            timeframe_vo, nav_periods, comparison_response, template_service
        )
        
        vergleichsanalyse_html = await template_service.render_base_template(
            title="SOLL-IST Vergleichsanalyse",
            content=content
        )
        
        logger.info("Vergleichsanalyse rendered successfully")
        return vergleichsanalyse_html
        
    except Exception as e:
        logger.error(f"Vergleichsanalyse error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Vergleichsanalyse error: {str(e)}")


@app.get("/system", response_class=HTMLResponse, summary="System Status - Clean Architecture")
async def system_status(
    system_status_use_case: GetSystemStatusUseCase = Depends(get_system_status_use_case),
    container: FrontendServiceContainer = Depends(get_container)
) -> str:
    """
    System Status Handler - Clean Architecture Implementation
    
    CLEAN ARCHITECTURE FLOW:
    Controller → Use Case → Domain Service → Dashboard Entity
    """
    try:
        logger.info("System status request received")
        
        # Get dashboard entity
        dashboard_entity = container.get_dashboard_entity()
        
        # Execute system status use case
        system_html = await system_status_use_case.execute(
            dashboard_entity=dashboard_entity,
            include_detailed_metrics=True
        )
        
        logger.info("System status rendered successfully")
        return system_html
        
    except Exception as e:
        logger.error(f"System status error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"System status error: {str(e)}")


@app.get("/depot", response_class=HTMLResponse, summary="Depot-Analyse Interface")
async def depot(template_service: ITemplateService = Depends(get_template_service)) -> str:
    """Depot-Analyse Interface Handler (Placeholder)"""
    content = """
        <h2>💼 Depot-Analyse - Portfolio-Übersicht</h2>
        <div class="alert alert-info">
            <p><strong>Portfolio-Management:</strong> Clean Architecture Implementation in Progress</p>
            <p>Diese Funktion wird in der nächsten Iteration mit dediziertem DepotUseCase implementiert.</p>
        </div>
    """
    return await template_service.render_base_template("Depot-Analyse", content)


@app.get("/prediction-averages", response_class=HTMLResponse, summary="Prediction Averages Interface")
async def prediction_averages(
    symbol: str = None,
    template_service: ITemplateService = Depends(get_template_service)
) -> str:
    """Prediction Averages Interface Handler (Placeholder)"""
    content = """
        <h2>📈 Enhanced Predictions Averages - Vorhersage-Mittelwerte</h2>
        <div class="alert alert-info">
            <p><strong>Enhanced Predictions:</strong> Clean Architecture Implementation in Progress</p>
            <p>Diese Funktion wird in der nächsten Iteration mit dediziertem PredictionAveragesUseCase implementiert.</p>
        </div>
    """
    return await template_service.render_base_template("Vorhersage-Mittelwerte", content)


# =============================================================================
# API ENDPOINTS (Legacy Compatibility)
# =============================================================================

@app.get("/api/content/vergleichsanalyse", response_class=HTMLResponse)
async def api_vergleichsanalyse_content(
    timeframe: str = "1M",
    http_client: IHTTPClient = Depends(get_http_client),
    template_service: ITemplateService = Depends(get_template_service),
    container: FrontendServiceContainer = Depends(get_container)
) -> str:
    """Legacy API endpoint for Vergleichsanalyse content"""
    return await vergleichsanalyse(timeframe, None, None, http_client, template_service, container)


@app.get("/health", response_class=JSONResponse, summary="Health Check - Clean Architecture")
async def health_check(container: FrontendServiceContainer = Depends(get_container)) -> Dict[str, Any]:
    """
    Health Check Endpoint - Clean Architecture Implementation
    
    Returns comprehensive health information from container
    """
    try:
        config = container.get_config()
        health_summary = container.get_service_health_summary()
        
        return {
            "status": "healthy",
            "service": config.get_service_name(),
            "version": config.get_version(),
            "architecture": "clean_architecture_4_layer",
            "timestamp": datetime.utcnow().isoformat(),
            "container_initialized": container.is_initialized(),
            "service_health": health_summary,
            "migration_status": "god_object_migrated_to_clean_architecture"
        }
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# =============================================================================
# TEMPORARY HELPER FUNCTIONS (Migration Phase)
# =============================================================================

async def _render_prognosen_content(timeframe_vo, nav_periods, prediction_data, template_service) -> str:
    """Temporary helper for prognosen content rendering"""
    return f"""
        <h2>📊 KI-Prognosen - Machine Learning Vorhersagen</h2>
        <div class="alert alert-info">
            <p><strong>Zeitraum:</strong> {timeframe_vo.display_name}</p>
            <p><strong>Clean Architecture:</strong> Migration Phase - Vereinfachte Implementierung</p>
            <p><strong>Navigation:</strong> {nav_periods.current_formatted}</p>
        </div>
        
        <div class="alert alert-warning">
            <h3>🚧 Migration in Progress</h3>
            <p>Diese Route wird in der nächsten Phase mit dediziertem PrognoseUseCase implementiert.</p>
            <p><strong>Received Data:</strong> {len(prediction_data) if isinstance(prediction_data, (list, dict)) else 'N/A'} items</p>
        </div>
    """


async def _render_vergleichsanalyse_content(timeframe_vo, nav_periods, comparison_data, template_service) -> str:
    """Temporary helper for vergleichsanalyse content rendering"""
    return f"""
        <h2>⚖️ SOLL-IST Vergleichsanalyse</h2>
        <div class="alert alert-info">
            <p><strong>Zeitraum:</strong> {timeframe_vo.display_name}</p>
            <p><strong>Clean Architecture:</strong> Migration Phase - Vereinfachte Implementierung</p>
            <p><strong>Navigation:</strong> {nav_periods.current_formatted}</p>
        </div>
        
        <div class="alert alert-warning">
            <h3>🚧 Migration in Progress</h3>
            <p>Diese Route wird in der nächsten Phase mit dediziertem VergleichsanalyseUseCase implementiert.</p>
            <p><strong>Received Data:</strong> {len(comparison_data) if isinstance(comparison_data, (list, dict)) else 'N/A'} items</p>
        </div>
    """


# =============================================================================
# SIGNAL HANDLERS (Graceful Shutdown)
# =============================================================================

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("🚀 Starting Frontend Service - Clean Architecture v1.0.0")
    logger.info("📋 Architecture Migration Status:")
    logger.info("   ✅ God Object (1,500 lines) → Clean Architecture")
    logger.info("   ✅ 4-Layer Pattern: Domain/Application/Infrastructure/Presentation")
    logger.info("   ✅ SOLID Principles Implementation")
    logger.info("   ✅ Dependency Injection Container") 
    logger.info("   ✅ Based on ML-Analytics Success Template")
    logger.info("   🚧 Phase 1: Core Architecture + Basic Routes")
    logger.info("   📅 Phase 2: Complete Use Case Implementation (Next)")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8081,  # Different port for parallel deployment
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)