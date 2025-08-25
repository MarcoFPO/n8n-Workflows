"""
Data Processing Service - Clean Architecture v6.0.0
ML-basierte Stock Prediction Pipeline

Haupt-FastAPI-Anwendung mit vollständiger Clean Architecture Implementation
"""
import asyncio
import structlog
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional

# Presentation Layer
from presentation.controllers.data_processing_controller import DataProcessingController
from presentation.models.data_processing_models import (
    StockDataIngestionRequest, StockDataIngestionResponse,
    PredictionJobRequest, PredictionJobResponse,
    PredictionAnalysisRequest, PredictionAnalysisResponse,
    MaintenanceCleanupResponse, SystemStatisticsResponse,
    JobProcessingRequest, JobProcessingResponse,
    BatchJobRequest, BatchJobResponse,
    HealthCheckResponse, ErrorResponse
)

# Infrastructure
from infrastructure.container import DataProcessingServiceContainer

# Configure logging
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global container instance
data_processing_container = DataProcessingServiceContainer()
data_processing_controller: Optional[DataProcessingController] = None
periodic_processing_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global data_processing_controller, periodic_processing_task
    
    logger.info("🔧 Data Processing Service v6.0.0 starting up...")
    
    try:
        # Configuration
        config = {
            "stock_data_db": "prediction_stock_data.db",
            "model_predictions_db": "prediction_models.db",
            "ensemble_predictions_db": "prediction_ensembles.db",
            "prediction_jobs_db": "prediction_jobs.db",
            "processing_metrics_db": "processing_metrics.db",
            "ml_models_db": "ml_models.db",
            "use_real_ml_service": False,
            "use_real_event_bus": False,
            "simulate_ml_failures": False,
            "ml_failure_rate": 0.0
        }
        
        # Initialize container
        data_processing_container.configure(config)
        initialization_success = await data_processing_container.initialize()
        
        if not initialization_success:
            logger.error("❌ Container initialization failed")
            raise Exception("Service initialization failed")
        
        # Initialize controller
        data_processing_controller = DataProcessingController(data_processing_container)
        
        # Start background processing
        periodic_processing_task = asyncio.create_task(periodic_job_processing())
        
        logger.info("✅ Data Processing Service v6.0.0 startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    finally:
        # Cleanup
        logger.info("🔧 Data Processing Service shutting down...")
        
        if periodic_processing_task:
            periodic_processing_task.cancel()
            try:
                await periodic_processing_task
            except asyncio.CancelledError:
                pass
        
        await data_processing_container.cleanup()
        logger.info("✅ Shutdown completed")


async def periodic_job_processing():
    """Background task für periodic job processing"""
    logger.info("🔄 Starting periodic job processing")
    
    while True:
        try:
            await asyncio.sleep(30)  # Process every 30 seconds
            
            if data_processing_controller and data_processing_container.is_initialized:
                result = await data_processing_controller.process_pending_jobs(max_jobs=3)
                
                if result["jobs_processed"] > 0:
                    logger.info(f"📊 Processed {result['jobs_processed']} jobs ({result['successful_jobs']} successful)")
            
        except asyncio.CancelledError:
            logger.info("🔄 Periodic processing cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Periodic processing error: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error


# FastAPI Application
app = FastAPI(
    title="Data Processing Service",
    description="ML-basierte Stock Prediction Pipeline mit Clean Architecture v6.0.0",
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für private Nutzung
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error Handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"❌ Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


# Root Endpoint
@app.get("/", summary="Service Information")
async def root():
    """Get service information and status"""
    return {
        "service": "Data Processing Service",
        "version": "6.0.0",
        "architecture": "Clean Architecture",
        "description": "ML-basierte Stock Prediction Pipeline",
        "status": "operational" if data_processing_container.is_initialized else "initializing",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "stock_data": "/stock-data",
            "predictions": "/predictions",
            "analysis": "/analysis",
            "maintenance": "/maintenance"
        },
        "timestamp": datetime.now().isoformat()
    }


# Health Check
@app.get("/health", response_model=HealthCheckResponse, summary="Health Check")
async def health_check():
    """Comprehensive health check"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")
    
    return await data_processing_controller.health_check()


# Stock Data Endpoints
@app.post("/stock-data/ingest", response_model=StockDataIngestionResponse, summary="Ingest Stock Data")
async def ingest_stock_data(request: StockDataIngestionRequest):
    """Ingest stock market data with quality assessment"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.ingest_stock_data(request)


@app.get("/stock-data/symbols", response_model=List[str], summary="Get Available Symbols")
async def get_available_symbols():
    """Get list of available stock symbols"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.get_available_symbols()


@app.get("/stock-data/{symbol}/latest", summary="Get Latest Stock Data")
async def get_latest_stock_data(
    symbol: str = Path(..., description="Stock symbol")
):
    """Get latest stock data for symbol"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.get_latest_stock_data(symbol)


# Prediction Endpoints
@app.post("/predictions/jobs", response_model=PredictionJobResponse, summary="Create Prediction Job")
async def create_prediction_job(request: PredictionJobRequest):
    """Create new prediction job"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.create_prediction_job(request)


@app.post("/predictions/jobs/batch", response_model=BatchJobResponse, summary="Create Batch Prediction Jobs")
async def create_batch_prediction_jobs(request: BatchJobRequest):
    """Create multiple prediction jobs for batch processing"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    job_ids = []
    
    for symbol in request.symbols:
        job_request = PredictionJobRequest(
            symbol=symbol,
            requested_models=request.model_types,
            prediction_horizon_days=request.prediction_horizon_days
        )
        
        response = await data_processing_controller.create_prediction_job(job_request)
        job_ids.append(response.job_id)
    
    return BatchJobResponse(
        job_ids=job_ids,
        symbols_processed=len(request.symbols),
        total_jobs_created=len(job_ids),
        message=f"Created {len(job_ids)} batch prediction jobs"
    )


@app.post("/predictions/jobs/process", response_model=JobProcessingResponse, summary="Process Pending Jobs")
async def process_pending_jobs(
    max_jobs: int = Query(5, ge=1, le=20, description="Maximum jobs to process")
):
    """Manually trigger processing of pending jobs"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    result = await data_processing_controller.process_pending_jobs(max_jobs)
    
    return JobProcessingResponse(
        jobs_processed=result["jobs_processed"],
        successful_jobs=result["successful_jobs"],
        failed_jobs=result["failed_jobs"],
        processing_timestamp=result["processing_timestamp"],
        message=result["message"]
    )


@app.get("/predictions/{symbol}/latest", summary="Get Latest Ensemble Prediction")
async def get_latest_ensemble_prediction(
    symbol: str = Path(..., description="Stock symbol")
):
    """Get latest ensemble prediction for symbol"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.get_latest_ensemble_prediction(symbol)


# Analysis Endpoints
@app.post("/analysis/performance", response_model=PredictionAnalysisResponse, summary="Analyze Prediction Performance")
async def analyze_prediction_performance(request: PredictionAnalysisRequest):
    """Analyze prediction performance and accuracy metrics"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.get_prediction_analysis(request)


@app.get("/analysis/{symbol}/performance", response_model=PredictionAnalysisResponse, summary="Get Symbol Performance Analysis")
async def get_symbol_performance_analysis(
    symbol: str = Path(..., description="Stock symbol"),
    days: int = Query(30, ge=1, le=365, description="Analysis period in days")
):
    """Get prediction performance analysis for specific symbol"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    request = PredictionAnalysisRequest(
        symbol=symbol,
        analysis_period_days=days
    )
    
    return await data_processing_controller.get_prediction_analysis(request)


# Maintenance Endpoints
@app.post("/maintenance/cleanup", response_model=MaintenanceCleanupResponse, summary="Perform Data Cleanup")
async def perform_maintenance_cleanup():
    """Perform routine data maintenance and cleanup"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.perform_maintenance_cleanup()


@app.get("/maintenance/statistics", response_model=SystemStatisticsResponse, summary="Get System Statistics")
async def get_system_statistics():
    """Get comprehensive system statistics"""
    if not data_processing_controller:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await data_processing_controller.get_system_statistics()


# Development Endpoints
@app.get("/dev/container-status", summary="Container Status")
async def get_container_status():
    """Get detailed container and service status"""
    return {
        "container_health": data_processing_container.get_health_status(),
        "service_statistics": data_processing_container.get_service_statistics(),
        "controller_initialized": data_processing_controller is not None,
        "background_tasks": {
            "periodic_processing": periodic_processing_task is not None and not periodic_processing_task.done()
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/dev/supported-models", summary="Get Supported ML Models")
async def get_supported_models():
    """Get list of supported ML model types"""
    try:
        if not data_processing_container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        supported_models = await data_processing_container.ml_service_provider.get_supported_models()
        
        return {
            "supported_models": [model.value for model in supported_models],
            "model_count": len(supported_models),
            "model_details": {
                model.value: {
                    "type": model.value,
                    "description": f"{model.value.replace('_', ' ').title()} ML Model"
                }
                for model in supported_models
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supported models: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Data Processing Service v6.0.0...")
    
    uvicorn.run(
        "main_v6_0_0:app",
        host="0.0.0.0",
        port=8014,
        reload=False,
        log_level="info"
    )