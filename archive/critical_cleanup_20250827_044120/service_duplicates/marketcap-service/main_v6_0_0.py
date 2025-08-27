#!/usr/bin/env python3
"""
MarketCap Service - Clean Architecture v6.0.0 Main Application
FastAPI Service Entry Point

CLEAN ARCHITECTURE - COMPOSITION ROOT:
- Dependency injection container configuration
- FastAPI application setup and routing
- Service lifecycle management

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Clean Architecture Imports
from .infrastructure.container import container
from .presentation.controllers.marketcap_controller import MarketCapController
from .presentation.models.market_data_models import (
    MarketDataRequest,
    MarketDataResponse,
    AllMarketDataRequest,
    AllMarketDataResponse,
    SymbolsResponse,
    CapDistributionResponse,
    HealthResponse,
    ErrorResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Manages startup and shutdown procedures
    """
    # Startup
    logger.info("MarketCap Service v6.0.0 starting up...")
    
    # Initialize container with configuration
    container.configure({
        'use_mock_provider': True,
        'cache_enabled': True,
        'event_publishing_enabled': True,
        'provider_latency_ms': 50,  # Fast for development
        'provider_availability': 0.98
    })
    
    # Pre-populate some test data
    controller = container.get_controller()
    test_symbols = ['AAPL', 'GOOGL', 'MSFT']
    
    for symbol in test_symbols:
        try:
            await controller.get_market_data(symbol, use_cache=False)
            logger.debug(f"Pre-populated test data for: {symbol}")
        except Exception as e:
            logger.warning(f"Failed to pre-populate {symbol}: {e}")
    
    logger.info("MarketCap Service v6.0.0 startup complete")
    
    yield
    
    # Shutdown
    logger.info("MarketCap Service v6.0.0 shutting down...")
    container.reset()
    logger.info("MarketCap Service v6.0.0 shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MarketCap Service",
    description="Clean Architecture v6.0.0 - Stock Market Data Service",
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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
    """
    Dependency injection for controller
    
    Returns:
        MarketCapController instance from DI container
    """
    return container.get_controller()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """
    Global exception handler for unhandled errors
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
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
    """
    Root endpoint with service information
    """
    return {
        "success": True,
        "data": {
            "service": "MarketCap Service",
            "version": "6.0.0",
            "architecture": "Clean Architecture",
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


@app.get("/market-data/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    use_cache: bool = True,
    source: str = "marketcap_service",
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
        Market data response
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
            
    except Exception as e:
        logger.error(f"Error in get_market_data endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/market-data/query", response_model=AllMarketDataResponse)
async def query_market_data(
    request: AllMarketDataRequest,
    controller: MarketCapController = Depends(get_controller)
):
    """
    Query all market data with filtering options
    
    Args:
        request: Query request with filtering options
        controller: Injected controller instance
    
    Returns:
        All market data response
    """
    try:
        result = await controller.get_all_market_data(
            cap_classification=request.cap_classification,
            fresh_only=request.fresh_only
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        logger.error(f"Error in query_market_data endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/market-data/all", response_model=AllMarketDataResponse)
async def get_all_market_data(
    cap_classification: str = None,
    fresh_only: bool = True,
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get all available market data
    
    Args:
        cap_classification: Optional filter by cap size
        fresh_only: Only return fresh data
        controller: Injected controller instance
    
    Returns:
        All market data response
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
            
    except Exception as e:
        logger.error(f"Error in get_all_market_data endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/symbols", response_model=SymbolsResponse)
async def get_symbols(
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get all available symbols
    
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
            
    except Exception as e:
        logger.error(f"Error in get_symbols endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/cap-distribution", response_model=CapDistributionResponse)
async def get_cap_distribution(
    controller: MarketCapController = Depends(get_controller)
):
    """
    Get market cap distribution statistics
    
    Args:
        controller: Injected controller instance
    
    Returns:
        Cap distribution response
    """
    try:
        result = await controller.get_cap_distribution()
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        logger.error(f"Error in get_cap_distribution endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", response_model=HealthResponse)
async def health_check(
    controller: MarketCapController = Depends(get_controller)
):
    """
    Service health check
    
    Args:
        controller: Injected controller instance
    
    Returns:
        Health check response
    """
    try:
        # Get controller health
        controller_health = await controller.health_check()
        
        # Get container health
        container_health = container.get_health_status()
        
        # Get repository health
        repository = container.get_repository()
        repo_health = await repository.get_health_status()
        
        # Get cache stats if available
        cache_stats = None
        if container.get_cache():
            cache_stats = await container.get_cache().get_cache_stats()
        
        # Get provider info if available
        provider_info = None
        if container.get_provider():
            provider_info = await container.get_provider().get_provider_info()
        
        return {
            "success": True,
            "data": {
                "service": "MarketCap Service",
                "version": "6.0.0",
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "controller": controller_health['data'],
                    "container": container_health,
                    "repository": repo_health,
                    "cache": cache_stats,
                    "provider": provider_info
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in health_check endpoint: {e}")
        return {
            "success": False,
            "error": {
                "message": "Health check failed",
                "code": "HEALTH_CHECK_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        }


# === DEVELOPMENT ENDPOINTS ===

@app.get("/dev/container-status")
async def get_container_status():
    """
    Get detailed container status (development only)
    """
    return container.get_health_status()


@app.post("/dev/reset-service")
async def reset_service():
    """
    Reset service state (development only)
    """
    try:
        container.reset()
        
        # Re-configure
        container.configure({
            'use_mock_provider': True,
            'cache_enabled': True,
            'event_publishing_enabled': True
        })
        
        return {
            "success": True,
            "message": "Service reset successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting service: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset service")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_v6_0_0:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )