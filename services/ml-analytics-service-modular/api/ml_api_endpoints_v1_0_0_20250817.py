#!/usr/bin/env python3
"""
ML API Endpoints v1.0.0
FastAPI Endpoints für ML Analytics Service

Autor: Claude Code
Datum: 17. August 2025
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Pydantic Models für API
class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    horizons: Optional[List[int]] = Field([7, 30, 150, 365], description="Prediction horizons in days")
    model_types: Optional[List[str]] = Field(["technical"], description="Model types to use")

class PredictionResponse(BaseModel):
    symbol: str
    predictions: Dict[str, Any]
    ensemble_confidence: float
    timestamp: datetime
    model_info: Dict[str, Any]

class TrainingRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to train")
    model_types: Optional[List[str]] = Field(["technical"], description="Model types to train")
    horizons: Optional[List[int]] = Field([7, 30, 150, 365], description="Horizons to train for")

class TrainingResponse(BaseModel):
    session_id: str
    symbols: List[str]
    total_trainings: int
    status: str
    started_at: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    service_name: str
    uptime_seconds: float
    system_metrics: Dict[str, Any]

class ModelPerformanceResponse(BaseModel):
    model_id: str
    performance_summary: Dict[str, Any]
    recent_evaluations: int
    avg_metrics: Dict[str, float]


def create_ml_api_router(ml_service) -> APIRouter:
    """
    Erstellt FastAPI Router für ML Analytics Service
    """
    router = APIRouter(prefix="/api/v1", tags=["ML Analytics"])
    
    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        """
        Service Health Check
        """
        try:
            health_metrics = await ml_service.performance_tracker.get_service_health_metrics()
            
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(),
                version="1.0.0",
                service_name="ml-analytics",
                uptime_seconds=ml_service.get_uptime_seconds(),
                system_metrics=health_metrics['system']
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Service unhealthy")
    
    @router.post("/predictions", response_model=PredictionResponse)
    async def generate_predictions(request: PredictionRequest):
        """
        Generiert ML-Vorhersagen für Symbol
        """
        try:
            prediction_result = await ml_service.prediction_orchestrator.generate_ensemble_prediction(
                symbol=request.symbol,
                horizons=request.horizons,
                model_types=request.model_types
            )
            
            return PredictionResponse(
                symbol=request.symbol,
                predictions=prediction_result['predictions'],
                ensemble_confidence=prediction_result['ensemble_confidence'],
                timestamp=datetime.now(),
                model_info=prediction_result['model_info']
            )
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
    @router.get("/predictions/{symbol}")
    async def get_latest_predictions(symbol: str):
        """
        Holt letzte Vorhersagen für Symbol
        """
        try:
            # Letzte Vorhersagen aus DB holen
            query = """
            SELECT prediction_data, ensemble_confidence, created_at
            FROM ml_predictions 
            WHERE symbol = $1 
            ORDER BY created_at DESC 
            LIMIT 1
            """
            
            row = await ml_service.database_connection.fetchrow(query, symbol)
            
            if not row:
                raise HTTPException(status_code=404, detail=f"No predictions found for {symbol}")
            
            return {
                "symbol": symbol,
                "predictions": row['prediction_data'],
                "ensemble_confidence": float(row['ensemble_confidence']),
                "timestamp": row['created_at']
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get predictions: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve predictions")
    
    @router.post("/training", response_model=TrainingResponse)
    async def start_training(request: TrainingRequest):
        """
        Startet Training-Session
        """
        try:
            session_id = await ml_service.training_orchestrator.start_training_session(
                symbols=request.symbols,
                model_types=request.model_types,
                horizons=request.horizons
            )
            
            training_config = ml_service.training_orchestrator.active_trainings[session_id]
            
            return TrainingResponse(
                session_id=session_id,
                symbols=request.symbols,
                total_trainings=training_config['total_trainings'],
                status=training_config['status'],
                started_at=training_config['started_at']
            )
            
        except Exception as e:
            logger.error(f"Training start failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")
    
    @router.get("/training/{session_id}")
    async def get_training_status(session_id: str):
        """
        Gibt Training-Status zurück
        """
        try:
            status = await ml_service.training_orchestrator.get_training_status(session_id)
            
            if not status:
                raise HTTPException(status_code=404, detail=f"Training session {session_id} not found")
            
            return {
                "session_id": session_id,
                "status": status['status'],
                "progress": f"{status['completed_trainings']}/{status['total_trainings']}",
                "started_at": status['started_at'],
                "symbols": status['symbols'],
                "errors": status['errors']
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get training status: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve training status")
    
    @router.get("/training")
    async def list_active_trainings():
        """
        Listet aktive Training-Sessions auf
        """
        try:
            trainings = await ml_service.training_orchestrator.list_active_trainings()
            return {"active_trainings": trainings}
            
        except Exception as e:
            logger.error(f"Failed to list trainings: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to list trainings")
    
    @router.get("/models")
    async def list_models(
        model_type: Optional[str] = Query(None, description="Filter by model type"),
        horizon_days: Optional[int] = Query(None, description="Filter by horizon"),
        status: str = Query("active", description="Model status filter")
    ):
        """
        Listet verfügbare Modelle auf
        """
        try:
            conditions = ["status = $1"]
            params = [status]
            param_count = 1
            
            if model_type:
                param_count += 1
                conditions.append(f"model_type = ${param_count}")
                params.append(model_type)
            
            if horizon_days:
                param_count += 1
                conditions.append(f"horizon_days = ${param_count}")
                params.append(horizon_days)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
            SELECT model_id, model_type, model_version, horizon_days, 
                   performance_metrics, created_at, updated_at
            FROM ml_model_metadata 
            WHERE {where_clause}
            ORDER BY model_type, horizon_days, created_at DESC
            """
            
            rows = await ml_service.database_connection.fetch(query, *params)
            
            models = [
                {
                    "model_id": row['model_id'],
                    "model_type": row['model_type'],
                    "model_version": row['model_version'],
                    "horizon_days": row['horizon_days'],
                    "performance_metrics": row['performance_metrics'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                }
                for row in rows
            ]
            
            return {"models": models, "count": len(models)}
            
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to list models")
    
    @router.get("/models/{model_id}/performance", response_model=ModelPerformanceResponse)
    async def get_model_performance(
        model_id: str,
        days_back: int = Query(30, description="Days to analyze", ge=1, le=365)
    ):
        """
        Gibt Model-Performance zurück
        """
        try:
            performance_summary = await ml_service.performance_tracker.get_model_performance_summary(
                model_id, days_back
            )
            
            return ModelPerformanceResponse(
                model_id=model_id,
                performance_summary=performance_summary,
                recent_evaluations=performance_summary.get('evaluation_count', 0),
                avg_metrics={
                    'mae': performance_summary.get('avg_mae', 0.0),
                    'directional_accuracy': performance_summary.get('avg_directional_accuracy', 0.0),
                    'r2_score': performance_summary.get('avg_r2_score', 0.0)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get model performance: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get model performance")
    
    @router.get("/features/{symbol}")
    async def get_latest_features(symbol: str, feature_type: str = Query("technical")):
        """
        Gibt letzte berechnete Features für Symbol zurück
        """
        try:
            query = """
            SELECT features_json, quality_score, calculation_timestamp, feature_count
            FROM ml_features 
            WHERE symbol = $1 AND feature_type = $2
            ORDER BY calculation_timestamp DESC 
            LIMIT 1
            """
            
            row = await ml_service.database_connection.fetchrow(query, symbol, feature_type)
            
            if not row:
                raise HTTPException(status_code=404, detail=f"No features found for {symbol}")
            
            return {
                "symbol": symbol,
                "feature_type": feature_type,
                "features": row['features_json'],
                "quality_score": float(row['quality_score']),
                "feature_count": row['feature_count'],
                "calculated_at": row['calculation_timestamp']
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get features: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve features")
    
    @router.get("/performance/dashboard")
    async def get_performance_dashboard():
        """
        Gibt Performance-Dashboard-Daten zurück
        """
        try:
            dashboard_data = await ml_service.performance_tracker.get_performance_dashboard_data()
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get dashboard data")
    
    @router.get("/performance/ranking/{symbol}")
    async def get_symbol_performance_ranking(
        symbol: str,
        model_type: Optional[str] = Query(None),
        horizon_days: Optional[int] = Query(None)
    ):
        """
        Gibt Performance-Ranking für Symbol zurück
        """
        try:
            ranking = await ml_service.performance_tracker.get_symbol_performance_ranking(
                symbol, model_type, horizon_days
            )
            
            return {
                "symbol": symbol,
                "model_ranking": ranking,
                "filters": {
                    "model_type": model_type,
                    "horizon_days": horizon_days
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance ranking: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get performance ranking")
    
    @router.post("/features/calculate/{symbol}")
    async def calculate_features_for_symbol(symbol: str):
        """
        Triggert Feature-Berechnung für Symbol
        """
        try:
            feature_result = await ml_service.feature_engine.calculate_technical_features(symbol)
            
            return {
                "symbol": symbol,
                "features_calculated": feature_result['feature_count'],
                "quality_score": feature_result['quality_score'],
                "calculation_time": feature_result['calculation_time'],
                "feature_id": feature_result['feature_id']
            }
            
        except Exception as e:
            logger.error(f"Feature calculation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Feature calculation failed: {str(e)}")
    
    @router.get("/metrics")
    async def get_service_metrics():
        """
        Gibt Service-Metriken zurück
        """
        try:
            metrics = {
                "service_info": {
                    "name": "ml-analytics",
                    "version": "1.0.0",
                    "uptime_seconds": ml_service.get_uptime_seconds()
                },
                "database_stats": await ml_service._get_database_stats(),
                "model_stats": await ml_service._get_model_stats(),
                "training_stats": await ml_service.training_orchestrator.get_training_statistics()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get metrics")
    
    return router


# Zusätzliche Utility-Endpoints
def create_admin_router(ml_service) -> APIRouter:
    """
    Erstellt Admin-Router für erweiterte ML-Service-Operationen
    """
    router = APIRouter(prefix="/admin", tags=["Admin"])
    
    @router.post("/cleanup/training-sessions")
    async def cleanup_training_sessions(max_age_hours: int = Query(24)):
        """
        Räumt alte Training-Sessions auf
        """
        try:
            await ml_service.training_orchestrator.cleanup_old_training_sessions(max_age_hours)
            return {"message": f"Cleaned up training sessions older than {max_age_hours} hours"}
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Cleanup failed")
    
    @router.post("/maintenance/performance-check")
    async def run_performance_check():
        """
        Führt manuellen Performance-Check durch
        """
        try:
            await ml_service.performance_tracker.run_periodic_performance_checks()
            return {"message": "Performance check completed"}
            
        except Exception as e:
            logger.error(f"Performance check failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Performance check failed")
    
    @router.get("/logs/recent")
    async def get_recent_logs(lines: int = Query(100, ge=1, le=1000)):
        """
        Gibt kürzliche Service-Logs zurück
        """
        try:
            # In einer echten Implementierung würde man Logs aus einem zentralen Log-System holen
            return {"message": f"Recent {lines} log lines", "logs": []}
            
        except Exception as e:
            logger.error(f"Failed to get logs: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get logs")
    
    return router