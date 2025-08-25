#!/usr/bin/env python3
"""
MarketCap Service v6.1.0 - PostgreSQL Clean Architecture
Clean Architecture v6.1.0 - Database Manager Integration

FastAPI Service Entry Point mit PostgreSQL Integration
- Database Manager für Verbindungsmanagement  
- Clean Architecture Compliance
- Async Service Lifecycle Management

Autor: Claude Code
Datum: 25. August 2025
Version: 6.1.0
"""

import asyncio
import structlog
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import sys

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConfiguration

# Infrastructure Import
from infrastructure.container_v6_1_0 import MarketCapServiceContainer

# Presentation Layer
from presentation.controllers.marketcap_controller import MarketCapController
from presentation.models.market_data_models import (
    MarketDataResponse, AllMarketDataResponse, SymbolsResponse,
    CapDistributionResponse, HealthResponse
)

logger = structlog.get_logger(__name__)

# Global container instance
container: Optional[MarketCapServiceContainer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Service Lifecycle Management"""
    global container
    
    try:
        logger.info("Starting MarketCap Service v6.1.0...")
        
        # Initialize Container
        container = MarketCapServiceContainer()
        
        # Configure and initialize with PostgreSQL
        config = {
            'database_manager': {
                'auto_initialize_schema': True,
                'enable_connection_pooling': True,
                'pool_health_check_interval': 300
            },
            'data_provider': {
                'use_mock': True,
                'latency_ms': 50,
                'availability': 0.98
            },
            'cache': {
                'enabled': True,
                'max_entries': 1000
            },
            'event_publisher': {
                'enabled': True,
                'max_events': 1000
            }
        }
        
        success = await container.configure_and_initialize(config)
        
        if not success:
            logger.error("Failed to initialize MarketCap Service")
            raise RuntimeError("Service initialization failed")
        
        # Pre-populate some test data (optional for development)
        controller = container.get_controller()
        test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        
        for symbol in test_symbols:
            try:
                await controller.get_market_data(symbol, use_cache=False)
                logger.debug("Pre-populated test data", symbol=symbol)
            except Exception as e:
                logger.warning("Failed to pre-populate symbol", symbol=symbol, error=str(e))
        
        logger.info("MarketCap Service v6.1.0 started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Error during service startup", error=str(e))
        raise
    finally:
        # Cleanup
        if container:
            try:
                await container.shutdown()
                logger.info("MarketCap Service v6.1.0 shutdown completed")
            except Exception as e:
                logger.error("Error during service shutdown", error=str(e))


# FastAPI Application with PostgreSQL Clean Architecture
app = FastAPI(
    title="MarketCap Service v6.1.0",
    version="6.1.0", 
    description="Clean Architecture MarketCap Service with PostgreSQL Integration",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for private development environment  
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private use - relaxed CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_controller() -> MarketCapController:
    """Dependency injection for controller"""
    if not container or not container.is_initialized:
        raise HTTPException(status_code=503, detail="Service not available")
    return container.get_controller()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error("Unhandled exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


# === API ENDPOINTS ===

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with service information"""
    return {
        "success": True,
        "data": {
            "service": "MarketCap Service",
            "version": "6.1.0",
            "architecture": "Clean Architecture",
            "database": "PostgreSQL",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "endpoints": [
                "/market-data/{symbol}",
                "/market-data/all",
                "/symbols",
                "/cap-distribution",
                "/health",
                "/docs"
            ]
        }
    }


@app.get("/health")
async def health():
    """Comprehensive health check"""
    try:
        if not container or not container.is_initialized:
            return {
                "status": "unhealthy",
                "error": "Container not initialized",
                "version": "6.1.0",
                "database": "PostgreSQL"
            }
        
        health_data = await container.health_check()
        health_data["status"] = "healthy" if health_data.get("container", {}).get("initialized") else "unhealthy"
        return health_data
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "6.1.0",
            "database": "PostgreSQL"
        }


@app.get("/market-data/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    use_cache: bool = Query(default=True, description="Use cached data if available"),
    source: str = Query(default="marketcap_service", description="Data source identifier"),
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get market data for a specific symbol
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        use_cache: Whether to use cached data
        source: Data source identifier
        controller: Injected controller instance
    
    Returns:
        Market data response with PostgreSQL data
    """
    try:
        result = await controller.get_market_data(
            symbol=symbol,
            use_cache=use_cache,
            source=source
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=404, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_market_data endpoint", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/market-data/all", response_model=AllMarketDataResponse)
async def get_all_market_data(
    cap_classification: Optional[str] = Query(default=None, description="Filter by cap size: Large Cap, Mid Cap, Small Cap"),
    fresh_only: bool = Query(default=True, description="Only return fresh data"),
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get all available market data from PostgreSQL
    
    Args:
        cap_classification: Optional filter by cap size
        fresh_only: Only return fresh data
        controller: Injected controller instance
    
    Returns:
        All market data response from PostgreSQL
    """
    try:
        result = await controller.get_all_market_data(
            cap_classification=cap_classification,
            fresh_only=fresh_only
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise  
    except Exception as e:
        logger.error("Error in get_all_market_data endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/symbols", response_model=SymbolsResponse)
async def get_symbols(
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get all available symbols from PostgreSQL
    
    Args:
        controller: Injected controller instance
    
    Returns:
        Available symbols response
    """
    try:
        result = await controller.get_symbols()
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_symbols endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/cap-distribution", response_model=CapDistributionResponse)
async def get_cap_distribution(
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get market cap distribution statistics from PostgreSQL
    
    Args:
        controller: Injected controller instance
    
    Returns:
        Cap distribution response with PostgreSQL statistics
    """
    try:
        result = await controller.get_cap_distribution()
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_cap_distribution endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/repository-stats")
async def get_repository_stats(
    controller: MarketCapController = Depends(get_controller)
):
    """Get detailed PostgreSQL repository statistics"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        repository = container.get_market_data_repository()
        stats = await repository.get_repository_stats()
        
        return {
            "success": True,
            "data": stats,
            "database": "PostgreSQL",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting repository stats", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/maintenance/stale-data")
async def cleanup_stale_data(
    max_age_hours: int = Query(default=24, description="Maximum age of data to keep in hours"),
    controller: MarketCapController = Depends(get_controller)
):
    """Clean up stale market data from PostgreSQL"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        repository = container.get_market_data_repository()
        deleted_count = await repository.delete_stale_data(max_age_hours)
        
        return {
            "success": True,
            "data": {
                "deleted_count": deleted_count,
                "max_age_hours": max_age_hours,
                "database": "PostgreSQL"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cleaning up stale data", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# === DEVELOPMENT ENDPOINTS ===

@app.get("/dev/container-status")
async def get_container_status():
    """Get detailed container status (development only)"""
    if not container:
        raise HTTPException(status_code=503, detail="Container not available")
    
    return await container.health_check()


@app.post("/dev/reset-service")  
async def reset_service():
    """Reset service state (development only)"""
    try:
        if not container:
            raise HTTPException(status_code=503, detail="Container not available")
        
        await container.reset_for_testing()
        
        # Re-initialize
        config = {
            'database_manager': {
                'auto_initialize_schema': True,
                'enable_connection_pooling': True
            },
            'data_provider': {'use_mock': True},
            'cache': {'enabled': True},
            'event_publisher': {'enabled': True}
        }
        
        success = await container.configure_and_initialize(config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reinitialize service")
        
        return {
            "success": True,
            "message": "Service reset and reinitialized successfully",
            "version": "6.1.0",
            "database": "PostgreSQL",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error resetting service", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reset service")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)