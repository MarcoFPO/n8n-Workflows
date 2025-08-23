#!/usr/bin/env python3
"""
Unified Profit Engine FastAPI Service v3.0.0
FastAPI Service-Wrapper für die Unified Profit Calculation Engine
Ersetzt die 4 duplizierten Service-Implementierungen

FEATURES:
- Backward compatible APIs mit bestehenden Services
- Multi-Mode Support (Full/Standalone/Simple)
- ML-Pipeline Integration Ready
- Comprehensive Error Handling
- Performance Monitoring
- SOLL-IST Vergleichsdaten für Frontend

PORTS:
- Default: 8025 (aus original profit_calculation_engine v2.0.0)
- Configurable via environment variables

API ENDPOINTS:
- POST /api/v1/profit/calculate - Create profit prediction
- GET /api/v1/profit/soll-ist-comparison - SOLL-IST comparison data
- GET /api/v1/profit/analytics - Performance analytics
- GET /api/v1/profit/health - Health check
- GET /api/v1/profit/metrics - Engine metrics

Code-Qualität: HÖCHSTE PRIORITÄT
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import json
import logging
from contextlib import asynccontextmanager

# FastAPI Dependencies
try:
    from fastapi import FastAPI, HTTPException, Depends, Query, Body
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field, ValidationError
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.error("FastAPI dependencies not available")

# Import Unified Engine
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/services/calculation-engine')
try:
    from unified_profit_calculation_engine_v3_0_0_20250823 import (
        UnifiedProfitCalculationEngine, 
        EngineMode, 
        PredictionSource,
        UnifiedProfitPrediction
    )
    UNIFIED_ENGINE_AVAILABLE = True
except ImportError as e:
    UNIFIED_ENGINE_AVAILABLE = False
    logging.error(f"Unified Engine not available: {e}")

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic Models für API
class ProfitPredictionRequest(BaseModel):
    """Request model for profit prediction calculation"""
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    company_name: Optional[str] = Field(None, description="Company name")
    market_data: Dict[str, Any] = Field(..., description="Market data for calculation")
    source: Optional[str] = Field("internal_model", description="Prediction source")
    mode: Optional[str] = Field("advanced", description="Calculation mode: simple, advanced")


class ProfitPredictionResponse(BaseModel):
    """Response model for profit prediction"""
    success: bool
    prediction_id: Optional[str] = None
    symbol: str
    company_name: str
    profit_forecast: float
    confidence_level: float
    recommendation: str
    trend: str
    score: float
    forecast_period_days: int
    target_date: str
    created_at: str
    calculation_method: str
    risk_assessment: str
    error: Optional[str] = None


class SollIstComparisonRequest(BaseModel):
    """Request model for SOLL-IST comparison"""
    symbol: Optional[str] = Field(None, description="Filter by symbol")
    timeframe_days: int = Field(30, ge=1, le=365, description="Timeframe in days")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")


class SollIstComparisonResponse(BaseModel):
    """Response model for SOLL-IST comparison"""
    success: bool
    data: List[Dict[str, Any]]
    count: int
    timeframe_days: int
    generated_at: str
    error: Optional[str] = None


class PerformanceAnalyticsResponse(BaseModel):
    """Response model for performance analytics"""
    success: bool
    analytics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    mode: str
    uptime: str
    version: str
    components: Dict[str, str]
    metrics: Dict[str, Any]


# Global Engine Instance
engine: Optional[UnifiedProfitCalculationEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global engine
    
    try:
        # Startup
        logger.info("Starting Unified Profit Engine Service")
        
        if not UNIFIED_ENGINE_AVAILABLE:
            raise Exception("Unified Engine not available")
        
        # Determine mode from environment
        mode_str = os.getenv('PROFIT_ENGINE_MODE', 'standalone').lower()
        try:
            mode = EngineMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid mode '{mode_str}', using STANDALONE")
            mode = EngineMode.STANDALONE
        
        # Initialize engine
        config = {
            'database_path': os.getenv('PROFIT_ENGINE_DB_PATH', 
                                     '/home/mdoehler/aktienanalyse-ökosystem/data/unified_profit_engine.db'),
            'ist_calculation_enabled': os.getenv('IST_CALCULATION_ENABLED', 'true').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }
        
        engine = UnifiedProfitCalculationEngine(mode, config)
        success = await engine.initialize()
        
        if not success:
            raise Exception("Engine initialization failed")
        
        logger.info(f"Unified Profit Engine Service started in {mode.value} mode")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise
    finally:
        # Shutdown
        if engine:
            logger.info("Shutting down Unified Profit Engine Service")
            await engine.shutdown()
            logger.info("Service shutdown complete")


# Create FastAPI app
if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Unified Profit Calculation Engine API",
        description="Consolidated API for profit prediction calculation with ML-Pipeline integration",
        version="3.0.0",
        lifespan=lifespan
    )
    
    # CORS Configuration für private Entwicklungsumgebung
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Private Umgebung - Security nachrangig
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Dependency für Engine Verfügbarkeit
async def get_engine() -> UnifiedProfitCalculationEngine:
    """Dependency to get engine instance"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not available")
    return engine


# API Endpoints
if FASTAPI_AVAILABLE:
    
    @app.post("/api/v1/profit/calculate", response_model=ProfitPredictionResponse)
    async def calculate_profit_prediction(
        request: ProfitPredictionRequest,
        engine: UnifiedProfitCalculationEngine = Depends(get_engine)
    ):
        """Calculate profit prediction"""
        try:
            logger.info(f"Calculating profit prediction for {request.symbol}")
            
            # Parse source
            try:
                source = PredictionSource(request.source)
            except ValueError:
                source = PredictionSource.INTERNAL_MODEL
            
            # Create prediction
            prediction = await engine.create_profit_prediction(
                symbol=request.symbol,
                company_name=request.company_name or f"Company {request.symbol}",
                market_data=request.market_data,
                source=source
            )
            
            # Convert to response
            response = ProfitPredictionResponse(
                success=True,
                prediction_id=prediction.prediction_id,
                symbol=prediction.symbol,
                company_name=prediction.company_name,
                profit_forecast=prediction.profit_forecast,
                confidence_level=prediction.confidence_level,
                recommendation=prediction.recommendation,
                trend=prediction.trend,
                score=prediction.score,
                forecast_period_days=prediction.forecast_period_days,
                target_date=prediction.target_date,
                created_at=prediction.created_at,
                calculation_method=prediction.calculation_method,
                risk_assessment=prediction.risk_assessment
            )
            
            logger.info(f"Profit prediction calculated successfully for {request.symbol}: "
                       f"{prediction.profit_forecast:.2f}%")
            
            return response
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=f"Validation error: {e}")
        except Exception as e:
            logger.error(f"Error calculating profit prediction: {e}")
            return ProfitPredictionResponse(
                success=False,
                symbol=request.symbol,
                company_name=request.company_name or f"Company {request.symbol}",
                profit_forecast=0.0,
                confidence_level=0.0,
                recommendation="HOLD",
                trend="NEUTRAL",
                score=0.0,
                forecast_period_days=30,
                target_date=datetime.now().isoformat(),
                created_at=datetime.now().isoformat(),
                calculation_method="error_fallback",
                risk_assessment="HIGH",
                error=str(e)
            )
    
    
    @app.get("/api/v1/profit/soll-ist-comparison", response_model=SollIstComparisonResponse)
    async def get_soll_ist_comparison(
        symbol: Optional[str] = Query(None, description="Filter by symbol"),
        timeframe_days: int = Query(30, ge=1, le=365, description="Timeframe in days"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
        engine: UnifiedProfitCalculationEngine = Depends(get_engine)
    ):
        """Get SOLL-IST comparison data for frontend"""
        try:
            logger.info(f"Getting SOLL-IST comparison: symbol={symbol}, timeframe={timeframe_days}d")
            
            # Get comparison data from engine
            comparison_data = await engine.get_soll_ist_comparison(
                symbol=symbol,
                timeframe_days=timeframe_days,
                limit=limit
            )
            
            response = SollIstComparisonResponse(
                success=True,
                data=comparison_data,
                count=len(comparison_data),
                timeframe_days=timeframe_days,
                generated_at=datetime.now().isoformat()
            )
            
            logger.info(f"Retrieved {len(comparison_data)} SOLL-IST comparison records")
            return response
            
        except Exception as e:
            logger.error(f"Error getting SOLL-IST comparison: {e}")
            return SollIstComparisonResponse(
                success=False,
                data=[],
                count=0,
                timeframe_days=timeframe_days,
                generated_at=datetime.now().isoformat(),
                error=str(e)
            )
    
    
    @app.get("/api/v1/profit/analytics", response_model=PerformanceAnalyticsResponse)
    async def get_performance_analytics(
        timeframe_days: int = Query(30, ge=1, le=365, description="Timeframe in days"),
        engine: UnifiedProfitCalculationEngine = Depends(get_engine)
    ):
        """Get performance analytics"""
        try:
            logger.info(f"Getting performance analytics for {timeframe_days} days")
            
            analytics = await engine.get_performance_analytics(timeframe_days)
            
            response = PerformanceAnalyticsResponse(
                success=True,
                analytics=analytics
            )
            
            logger.info("Performance analytics retrieved successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            return PerformanceAnalyticsResponse(
                success=False,
                error=str(e)
            )
    
    
    @app.get("/api/v1/profit/health", response_model=HealthCheckResponse)
    async def health_check(engine: UnifiedProfitCalculationEngine = Depends(get_engine)):
        """Health check endpoint"""
        try:
            uptime_start = datetime.fromisoformat(engine.metrics['uptime_start'])
            uptime = str(datetime.now() - uptime_start)
            
            components = {
                'engine': 'healthy',
                'database': 'healthy' if engine.database_manager else 'not_available',
                'market_data_collectors': f"{len(engine.market_data_collectors)}_available",
                'ist_scheduler': 'running' if engine.ist_calculation_scheduler else 'not_running'
            }
            
            response = HealthCheckResponse(
                status="healthy",
                mode=engine.mode.value,
                uptime=uptime,
                version="3.0.0",
                components=components,
                metrics=engine.metrics
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            raise HTTPException(status_code=503, detail=f"Health check failed: {e}")
    
    
    @app.get("/api/v1/profit/metrics")
    async def get_engine_metrics(engine: UnifiedProfitCalculationEngine = Depends(get_engine)):
        """Get engine metrics"""
        try:
            return {
                "success": True,
                "metrics": engine.metrics,
                "mode": engine.mode.value,
                "config": {
                    "ist_calculation_enabled": engine.config['ist_calculation_enabled'],
                    "ml_pipeline_integration": engine.config['ml_pipeline_integration'],
                    "performance_analytics_enabled": engine.config['performance_analytics_enabled']
                },
                "collectors": list(engine.market_data_collectors.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    
    # Backward Compatibility Endpoints
    
    @app.get("/api/v1/vergleichsanalyse/csv")
    async def get_vergleichsanalyse_csv(
        timeframe: str = Query("1M", description="Timeframe: 1M, 3M, 6M, 1Y"),
        engine: UnifiedProfitCalculationEngine = Depends(get_engine)
    ):
        """Backward compatibility endpoint für SOLL-IST CSV Export"""
        try:
            # Parse timeframe to days
            timeframe_mapping = {
                "1M": 30, "1m": 30,
                "3M": 90, "3m": 90,
                "6M": 180, "6m": 180,
                "1Y": 365, "1y": 365, "1year": 365
            }
            
            timeframe_days = timeframe_mapping.get(timeframe, 30)
            
            logger.info(f"CSV export requested for timeframe: {timeframe} ({timeframe_days} days)")
            
            # Get SOLL-IST comparison data
            comparison_data = await engine.get_soll_ist_comparison(
                symbol=None,
                timeframe_days=timeframe_days,
                limit=1000
            )
            
            # Convert to CSV format expected by frontend
            csv_data = []
            for item in comparison_data:
                csv_data.append({
                    "symbol": item.get('symbol', ''),
                    "company_name": item.get('company_name', ''),
                    "prediction_date": item.get('prediction_date', ''),
                    "target_date": item.get('target_date', ''),
                    "timeframe": item.get('timeframe', ''),
                    "soll_return": item.get('soll_return', 0.0),
                    "ist_return": item.get('ist_return', 0.0),
                    "difference": item.get('difference', 0.0),
                    "accuracy": item.get('accuracy', 0.0),
                    "recommendation": item.get('recommendation', ''),
                    "trend": item.get('trend', ''),
                    "confidence_level": item.get('confidence_level', 0.0)
                })
            
            return {
                "success": True,
                "data": csv_data,
                "count": len(csv_data),
                "timeframe": timeframe,
                "timeframe_days": timeframe_days,
                "generated_at": datetime.now().isoformat(),
                "source": "unified_profit_engine_v3.0.0"
            }
            
        except Exception as e:
            logger.error(f"Error in CSV export: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    
    # Error Handlers
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions"""
        logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
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
    async def general_exception_handler(request, exc):
        """Handle general exceptions"""
        logger.error(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "timestamp": datetime.now().isoformat()
            }
        )


# Service Runner
class UnifiedProfitEngineServiceRunner:
    """Service runner for production deployment"""
    
    def __init__(self):
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = int(os.getenv('PORT', '8025'))  # Default port from original v2.0.0
        self.workers = int(os.getenv('WORKERS', '1'))
        self.log_level = os.getenv('LOG_LEVEL', 'info').lower()
        
    def run(self):
        """Run the service"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI not available - cannot start service")
            return 1
        
        if not UNIFIED_ENGINE_AVAILABLE:
            logger.error("Unified Engine not available - cannot start service")
            return 1
        
        try:
            logger.info(f"Starting Unified Profit Engine Service on {self.host}:{self.port}")
            
            uvicorn.run(
                "unified_profit_engine_service_v3_0_0_20250823:app",
                host=self.host,
                port=self.port,
                workers=self.workers,
                log_level=self.log_level,
                reload=False,
                access_log=True
            )
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return 1


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - run basic functionality test
        logger.info("Running in test mode...")
        # TODO: Implement basic tests
        return 0
    else:
        # Production mode
        runner = UnifiedProfitEngineServiceRunner()
        return runner.run()


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical service error: {e}")
        sys.exit(1)