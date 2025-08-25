#!/usr/bin/env python3
"""
Data Processing Service v6.1.0 - PostgreSQL Clean Architecture
Clean Architecture v6.1.0 - Database Manager Integration

Service Lifecycle Management mit PostgreSQL Integration
- Database Manager für Verbindungsmanagement
- Clean Architecture Compliance
- Async Repository Pattern
- Comprehensive Error Handling

Autor: Claude Code
Datum: 25. August 2025
Version: 6.1.0
"""

import asyncio
import structlog
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Response
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConfiguration

# Infrastructure Import
from infrastructure.container_v6_1_0 import DataProcessingServiceContainer

logger = structlog.get_logger(__name__)

# Global container instance
container: Optional[DataProcessingServiceContainer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Service Lifecycle Management"""
    global container
    
    try:
        logger.info("Starting Data Processing Service v6.1.0...")
        
        # Initialize Container
        container = DataProcessingServiceContainer()
        
        # Configure and initialize with PostgreSQL
        config = {
            'database_manager': {
                'auto_initialize_schema': True,
                'enable_connection_pooling': True,
                'pool_health_check_interval': 300
            },
            'ml_service_provider': {
                'use_mock': True,
                'timeout_seconds': 30
            },
            'event_publisher': {
                'enabled': True,
                'max_events': 1000
            }
        }
        
        success = await container.configure_and_initialize(config)
        
        if not success:
            logger.error("Failed to initialize Data Processing Service")
            raise RuntimeError("Service initialization failed")
        
        logger.info("Data Processing Service v6.1.0 started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Error during service startup", error=str(e))
        raise
    finally:
        # Cleanup
        if container:
            try:
                await container.shutdown()
                logger.info("Data Processing Service v6.1.0 shutdown completed")
            except Exception as e:
                logger.error("Error during service shutdown", error=str(e))


# FastAPI Application with PostgreSQL Clean Architecture
app = FastAPI(
    title="Data Processing Service v6.1.0",
    version="6.1.0",
    description="Clean Architecture Data Processing Service with PostgreSQL Integration",
    lifespan=lifespan
)


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


@app.get("/api/v1/data/predictions")
async def get_predictions_by_timeframe(
    symbol: str = Query(default=None, description="Stock symbol filter"),
    limit: int = Query(default=20, description="Maximum number of predictions")
):
    """Get ensemble predictions"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        ensemble_repository = container.get_ensemble_repository()
        
        if symbol:
            predictions = await ensemble_repository.get_ensemble_predictions_by_symbol(symbol, limit)
        else:
            # Get latest predictions for multiple symbols
            # This would need to be implemented based on business requirements
            predictions = []
            
        # Convert to response format
        prediction_data = []
        for prediction in predictions:
            prediction_data.append({
                "ensemble_id": prediction.ensemble_id,
                "symbol": prediction.symbol,
                "ensemble_price": float(prediction.ensemble_price) if prediction.ensemble_price else None,
                "ensemble_confidence": prediction.ensemble_confidence,
                "prediction_horizon_days": prediction.prediction_horizon_days,
                "created_at": prediction.created_at.isoformat(),
                "model_count": prediction.get_model_count(),
                "consensus_strength": prediction.get_consensus_strength()
            })
        
        return {
            "predictions": prediction_data,
            "total_count": len(prediction_data),
            "database": "PostgreSQL",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting predictions", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/data/predictions/csv")
async def get_predictions_csv(
    symbol: str = Query(default=None, description="Stock symbol filter"),
    limit: int = Query(default=20, description="Maximum number of predictions")
):
    """Get predictions as CSV format"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        ensemble_repository = container.get_ensemble_repository()
        
        if symbol:
            predictions = await ensemble_repository.get_ensemble_predictions_by_symbol(symbol, limit)
        else:
            predictions = []
        
        # Generate CSV content
        csv_lines = ["Symbol,Ensemble_Price,Confidence,Horizon_Days,Created_At"]
        
        for prediction in predictions:
            csv_lines.append(
                f"{prediction.symbol},"
                f"{prediction.ensemble_price or 'N/A'},"
                f"{prediction.ensemble_confidence},"
                f"{prediction.prediction_horizon_days},"
                f"{prediction.created_at.isoformat()}"
            )
        
        csv_content = "\n".join(csv_lines)
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=predictions_{symbol or 'all'}.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating CSV", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/data/stock-data/{symbol}")
async def get_stock_data(symbol: str):
    """Get stock data for symbol"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        stock_repository = container.get_stock_data_repository()
        stock_data_list = await stock_repository.get_stock_data_by_symbol(symbol)
        
        if not stock_data_list:
            raise HTTPException(status_code=404, detail=f"No stock data found for symbol {symbol}")
        
        # Convert to response format
        data_points = []
        for stock_data in stock_data_list:
            data_points.append({
                "symbol": stock_data.symbol,
                "date": stock_data.date.isoformat(),
                "open_price": float(stock_data.open_price),
                "high_price": float(stock_data.high_price),
                "low_price": float(stock_data.low_price),
                "close_price": float(stock_data.close_price),
                "volume": stock_data.volume,
                "adjusted_close": float(stock_data.adjusted_close) if stock_data.adjusted_close else None
            })
        
        return {
            "symbol": symbol,
            "data_points": data_points,
            "total_count": len(data_points),
            "database": "PostgreSQL"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting stock data", error=str(e), symbol=symbol)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/jobs/prediction")
async def create_prediction_job(
    symbol: str,
    prediction_horizon_days: int = Query(default=30, description="Prediction horizon in days")
):
    """Create new prediction job"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        # Use the prediction processing use case
        prediction_use_case = container.get_prediction_processing_use_case()
        
        # Create prediction job
        job_result = await prediction_use_case.create_prediction_job(
            symbol=symbol,
            prediction_horizon_days=prediction_horizon_days
        )
        
        if not job_result.success:
            raise HTTPException(status_code=400, detail=job_result.error_message)
        
        return {
            "job_id": job_result.job_id,
            "symbol": symbol,
            "prediction_horizon_days": prediction_horizon_days,
            "status": "created",
            "database": "PostgreSQL"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating prediction job", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/jobs/{job_id}")
async def get_prediction_job(job_id: str):
    """Get prediction job status"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        job_repository = container.get_job_repository()
        job = await job_repository.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "job_id": job.job_id,
            "symbol": job.symbol,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "processing_duration_seconds": job.processing_duration_seconds,
            "error_message": job.error_message,
            "database": "PostgreSQL"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting prediction job", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/maintenance/stats")
async def get_service_statistics():
    """Get comprehensive service statistics"""
    try:
        if not container or not container.is_initialized:
            raise HTTPException(status_code=503, detail="Service not available")
        
        # Get statistics from repositories
        stats = {
            "service": {
                "version": "6.1.0",
                "database": "PostgreSQL",
                "architecture": "Clean Architecture",
                "initialized": container.is_initialized,
                "initialized_at": container._initialized_at.isoformat() if container._initialized_at else None
            }
        }
        
        # Get job statistics
        try:
            job_repository = container.get_job_repository()
            job_stats = await job_repository.get_job_statistics()
            stats["jobs"] = job_stats
        except Exception as e:
            logger.warning("Could not get job statistics", error=str(e))
            stats["jobs"] = {"error": str(e)}
        
        # Get ensemble performance
        try:
            ensemble_repository = container.get_ensemble_repository()
            consensus_stats = await ensemble_repository.get_consensus_strength_statistics()
            stats["ensemble_performance"] = consensus_stats
        except Exception as e:
            logger.warning("Could not get ensemble statistics", error=str(e))
            stats["ensemble_performance"] = {"error": str(e)}
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting service statistics", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)