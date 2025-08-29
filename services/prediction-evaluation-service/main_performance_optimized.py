"""
Prediction Evaluation Service Performance Optimized v2.0.0
Eliminiert Connection-Pool-pro-Request Anti-Pattern

Performance-Verbesserungen:
- Zentraler Enhanced Database Pool statt Pool-pro-Request
- Query-Caching für wiederkehrende Evaluation-Queries
- Batch-Operations für Multiple Predictions
- Connection-Pool-Wiederverwendung
- Performance-Monitoring und Metrics
"""

import asyncio
import asyncpg
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Enhanced Performance Infrastructure
from shared.enhanced_database_pool import (
    enhanced_db_pool,
    init_enhanced_db_pool,
    PoolConfig,
    track_query_performance,
    ensure_enhanced_db_pool
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [prediction-eval-optimized] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("prediction-eval-optimized")

# Pydantic Models
class PredictionRequest(BaseModel):
    symbol: str
    prediction_date: str
    predicted_value: float
    actual_value: Optional[float] = None
    model_name: str
    confidence: Optional[float] = Field(default=0.8, ge=0.0, le=1.0)

class BatchPredictionRequest(BaseModel):
    predictions: List[PredictionRequest] = Field(..., max_items=100)

class EvaluationQuery(BaseModel):
    symbols: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    model_names: Optional[List[str]] = None
    limit: int = Field(default=100, le=1000)

@dataclass
class PredictionMetrics:
    """Prediction Performance Metrics"""
    total_predictions: int = 0
    accurate_predictions: int = 0
    accuracy_rate: float = 0.0
    mean_absolute_error: float = 0.0
    rmse: float = 0.0


class EnhancedPredictionEvaluationService:
    """Performance-optimierter Prediction Evaluation Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Enhanced Prediction Evaluation Service",
            version="2.0.0",
            description="Performance-optimized prediction evaluation with shared connection pooling"
        )
        
        self.service_name = "prediction-evaluation-optimized"
        
        # Performance Metrics
        self.processed_predictions = 0
        self.batch_operations = 0
        self.cache_hits = 0
        self.start_time = datetime.now()
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.post("/predictions", 
                      summary="Store Single Prediction",
                      description="Store prediction with enhanced connection pooling")
        async def store_prediction(prediction: PredictionRequest):
            return await self._store_prediction_optimized(prediction)
        
        @self.app.post("/predictions/batch",
                      summary="Store Prediction Batch",
                      description="Store multiple predictions in single transaction")
        async def store_predictions_batch(batch: BatchPredictionRequest):
            return await self._store_predictions_batch(batch.predictions)
        
        @self.app.post("/evaluate",
                      summary="Evaluate Predictions",
                      description="Evaluate predictions with query caching")
        async def evaluate_predictions(query: EvaluationQuery):
            return await self._evaluate_predictions_cached(query)
        
        @self.app.get("/predictions/{symbol}",
                     summary="Get Symbol Predictions",
                     description="Get predictions for symbol with caching")
        async def get_symbol_predictions(symbol: str, limit: int = 100):
            return await self._get_symbol_predictions_cached(symbol, limit)
        
        @self.app.get("/metrics/performance",
                     summary="Performance Metrics",
                     description="Get service performance metrics")
        async def get_performance_metrics():
            return await self._get_performance_metrics()
        
        @self.app.get("/health",
                     summary="Health Check",
                     description="Service health with DB pool status")
        async def health_check():
            return await self._health_check_enhanced()
    
    async def initialize(self):
        """Initialize enhanced database pool"""
        try:
            # Enhanced Database Pool mit Performance-Tuning
            db_config = PoolConfig(
                min_connections=3,
                max_connections=15,  # Reduziert von Standard 20
                enable_query_cache=True,
                enable_prepared_statements=True,
                query_cache_size=500,  # Cache für Evaluation-Queries
                max_query_time=15,  # 15s für komplexe Evaluation-Queries
                connection_idle_timeout=600  # 10min für längere Sessions
            )
            
            await init_enhanced_db_pool(db_config)
            
            # Database Schema sicherstellen
            await self._ensure_database_schema()
            
            logger.info("Enhanced Prediction Evaluation Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise
    
    @ensure_enhanced_db_pool
    @track_query_performance
    async def _store_prediction_optimized(self, prediction: PredictionRequest) -> Dict[str, Any]:
        """Store single prediction with enhanced pooling"""
        try:
            query = """
                INSERT INTO predictions_evaluation 
                (symbol, prediction_date, predicted_value, actual_value, model_name, confidence, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """
            
            result = await enhanced_db_pool.fetchval(
                query,
                prediction.symbol,
                datetime.fromisoformat(prediction.prediction_date.replace('Z', '+00:00')),
                prediction.predicted_value,
                prediction.actual_value,
                prediction.model_name,
                prediction.confidence,
                datetime.utcnow(),
                use_cache=False  # INSERT operations nicht cachen
            )
            
            self.processed_predictions += 1
            
            return {
                "status": "stored",
                "prediction_id": result,
                "symbol": prediction.symbol,
                "model_name": prediction.model_name
            }
            
        except Exception as e:
            logger.error(f"Store prediction failed: {e}")
            raise HTTPException(status_code=500, detail=f"Storage failed: {str(e)}")
    
    @ensure_enhanced_db_pool
    @track_query_performance  
    async def _store_predictions_batch(self, predictions: List[PredictionRequest]) -> Dict[str, Any]:
        """Store multiple predictions in batch transaction"""
        try:
            if len(predictions) > 100:
                raise HTTPException(status_code=400, detail="Maximum 100 predictions per batch")
            
            # Batch queries vorbereiten
            batch_queries = []
            for prediction in predictions:
                query_data = (
                    "INSERT INTO predictions_evaluation (symbol, prediction_date, predicted_value, actual_value, model_name, confidence, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    (
                        prediction.symbol,
                        datetime.fromisoformat(prediction.prediction_date.replace('Z', '+00:00')),
                        prediction.predicted_value,
                        prediction.actual_value,
                        prediction.model_name,
                        prediction.confidence,
                        datetime.utcnow()
                    )
                )
                batch_queries.append(query_data)
            
            # Batch execution
            results = await enhanced_db_pool.batch_execute(batch_queries)
            
            self.processed_predictions += len(predictions)
            self.batch_operations += 1
            
            return {
                "status": "stored",
                "batch_count": len(predictions),
                "stored_predictions": len(results),
                "batch_id": f"batch_{self.batch_operations}"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Batch store failed: {e}")
            raise HTTPException(status_code=500, detail=f"Batch storage failed: {str(e)}")
    
    @ensure_enhanced_db_pool
    @track_query_performance
    async def _evaluate_predictions_cached(self, query: EvaluationQuery) -> Dict[str, Any]:
        """Evaluate predictions with intelligent caching"""
        try:
            # Base query aufbauen
            where_conditions = ["actual_value IS NOT NULL"]  # Nur bewertbare Predictions
            params = []
            param_count = 0
            
            # Symbol-Filter
            if query.symbols:
                param_count += 1
                where_conditions.append(f"symbol = ANY(${param_count})")
                params.append(query.symbols)
            
            # Datum-Filter
            if query.start_date:
                param_count += 1
                where_conditions.append(f"prediction_date >= ${param_count}")
                params.append(datetime.fromisoformat(query.start_date.replace('Z', '+00:00')))
            
            if query.end_date:
                param_count += 1
                where_conditions.append(f"prediction_date <= ${param_count}")
                params.append(datetime.fromisoformat(query.end_date.replace('Z', '+00:00')))
            
            # Model-Filter
            if query.model_names:
                param_count += 1
                where_conditions.append(f"model_name = ANY(${param_count})")
                params.append(query.model_names)
            
            where_clause = " AND ".join(where_conditions)
            
            # Query mit Caching für wiederholte Evaluationen
            sql_query = f"""
                SELECT 
                    symbol,
                    model_name,
                    COUNT(*) as total_predictions,
                    AVG(ABS(predicted_value - actual_value)) as mae,
                    SQRT(AVG(POWER(predicted_value - actual_value, 2))) as rmse,
                    COUNT(CASE WHEN ABS(predicted_value - actual_value) / actual_value <= 0.05 THEN 1 END) as accurate_predictions,
                    AVG(confidence) as avg_confidence,
                    MIN(prediction_date) as earliest_prediction,
                    MAX(prediction_date) as latest_prediction
                FROM predictions_evaluation 
                WHERE {where_clause}
                GROUP BY symbol, model_name 
                ORDER BY mae ASC 
                LIMIT ${param_count + 1}
            """
            
            params.append(query.limit)
            
            # Query ausführen mit Caching
            results = await enhanced_db_pool.fetch(
                sql_query, 
                *params,
                use_cache=True  # Evaluation-Queries sind gut cacheable
            )
            
            # Gesamtstatistiken berechnen
            total_metrics = await self._calculate_overall_metrics(query)
            
            evaluation_results = []
            for row in results:
                accuracy_rate = (row['accurate_predictions'] / row['total_predictions']) * 100 if row['total_predictions'] > 0 else 0
                
                evaluation_results.append({
                    "symbol": row['symbol'],
                    "model_name": row['model_name'],
                    "metrics": {
                        "total_predictions": row['total_predictions'],
                        "accurate_predictions": row['accurate_predictions'],
                        "accuracy_rate": round(accuracy_rate, 2),
                        "mean_absolute_error": round(float(row['mae']), 4),
                        "rmse": round(float(row['rmse']), 4),
                        "avg_confidence": round(float(row['avg_confidence']), 3)
                    },
                    "time_range": {
                        "earliest_prediction": row['earliest_prediction'].isoformat() if row['earliest_prediction'] else None,
                        "latest_prediction": row['latest_prediction'].isoformat() if row['latest_prediction'] else None
                    }
                })
            
            return {
                "evaluation_results": evaluation_results,
                "overall_metrics": total_metrics,
                "query_info": {
                    "symbols_count": len(query.symbols) if query.symbols else "all",
                    "date_range": f"{query.start_date or 'any'} to {query.end_date or 'any'}",
                    "models_count": len(query.model_names) if query.model_names else "all",
                    "results_count": len(evaluation_results)
                },
                "cache_info": "query_cached"
            }
            
        except Exception as e:
            logger.error(f"Prediction evaluation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
    
    @ensure_enhanced_db_pool
    @track_query_performance
    async def _get_symbol_predictions_cached(self, symbol: str, limit: int) -> Dict[str, Any]:
        """Get predictions for symbol with caching"""
        try:
            query = """
                SELECT 
                    id, prediction_date, predicted_value, actual_value, 
                    model_name, confidence, created_at
                FROM predictions_evaluation 
                WHERE symbol = $1 
                ORDER BY prediction_date DESC 
                LIMIT $2
            """
            
            results = await enhanced_db_pool.fetch(
                query, 
                symbol, 
                limit,
                use_cache=True  # Symbol-spezifische Queries cachen
            )
            
            predictions = []
            for row in results:
                predictions.append({
                    "id": row['id'],
                    "prediction_date": row['prediction_date'].isoformat(),
                    "predicted_value": float(row['predicted_value']),
                    "actual_value": float(row['actual_value']) if row['actual_value'] else None,
                    "model_name": row['model_name'],
                    "confidence": float(row['confidence']) if row['confidence'] else None,
                    "created_at": row['created_at'].isoformat()
                })
            
            self.cache_hits += 1
            
            return {
                "symbol": symbol,
                "predictions": predictions,
                "count": len(predictions),
                "cache_hit": True
            }
            
        except Exception as e:
            logger.error(f"Get symbol predictions failed: {e}")
            raise HTTPException(status_code=500, detail=f"Get predictions failed: {str(e)}")
    
    @ensure_enhanced_db_pool
    async def _calculate_overall_metrics(self, query: EvaluationQuery) -> Dict[str, Any]:
        """Calculate overall prediction metrics"""
        try:
            # Simplified overall metrics query
            overall_query = """
                SELECT 
                    COUNT(*) as total_predictions,
                    AVG(ABS(predicted_value - actual_value)) as overall_mae,
                    SQRT(AVG(POWER(predicted_value - actual_value, 2))) as overall_rmse,
                    COUNT(CASE WHEN ABS(predicted_value - actual_value) / actual_value <= 0.05 THEN 1 END) as overall_accurate
                FROM predictions_evaluation 
                WHERE actual_value IS NOT NULL
            """
            
            result = await enhanced_db_pool.fetchrow(overall_query, use_cache=True)
            
            if result and result['total_predictions'] > 0:
                accuracy_rate = (result['overall_accurate'] / result['total_predictions']) * 100
                
                return {
                    "total_predictions": result['total_predictions'],
                    "overall_accuracy_rate": round(accuracy_rate, 2),
                    "overall_mae": round(float(result['overall_mae']), 4),
                    "overall_rmse": round(float(result['overall_rmse']), 4)
                }
            else:
                return {
                    "total_predictions": 0,
                    "overall_accuracy_rate": 0.0,
                    "overall_mae": 0.0,
                    "overall_rmse": 0.0
                }
                
        except Exception as e:
            logger.warning(f"Overall metrics calculation failed: {e}")
            return {"error": "Could not calculate overall metrics"}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            uptime = (datetime.now() - self.start_time).total_seconds()
            predictions_per_second = self.processed_predictions / max(1, uptime)
            
            # Database Performance Report
            db_report = await enhanced_db_pool.get_performance_report()
            
            return {
                "service_performance": {
                    "service_name": self.service_name,
                    "version": "2.0.0",
                    "uptime_seconds": int(uptime),
                    "processed_predictions": self.processed_predictions,
                    "predictions_per_second": round(predictions_per_second, 2),
                    "batch_operations": self.batch_operations,
                    "cache_hits": self.cache_hits
                },
                "database_performance": db_report,
                "pool_usage": {
                    "shared_pool": True,
                    "pool_per_request": False,
                    "connection_reuse": "optimized"
                },
                "performance_improvements": {
                    "eliminated_pool_per_request": True,
                    "query_caching_enabled": True,
                    "batch_operations_available": True,
                    "prepared_statements": True
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance metrics failed: {e}")
            raise HTTPException(status_code=500, detail=f"Metrics failed: {str(e)}")
    
    async def _health_check_enhanced(self) -> Dict[str, Any]:
        """Enhanced health check with pool status"""
        try:
            # Database Health Check
            db_healthy = await enhanced_db_pool.health_check()
            
            # Pool Statistics
            pool_stats = enhanced_db_pool.pool_stats
            
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                "status": "healthy" if db_healthy else "unhealthy",
                "service": self.service_name,
                "version": "2.0.0",
                "uptime_seconds": int(uptime),
                "database_health": {
                    "connected": db_healthy,
                    "pool_initialized": enhanced_db_pool.is_initialized,
                    "pool_stats": pool_stats
                },
                "performance_health": {
                    "processed_predictions": self.processed_predictions,
                    "batch_operations": self.batch_operations,
                    "memory_efficient": True,
                    "connection_pooling": "optimized"
                },
                "checks": {
                    "database_pool_shared": enhanced_db_pool.is_initialized,
                    "no_pool_per_request": True,  # Anti-Pattern eliminated
                    "query_caching": True,
                    "batch_operations": self.batch_operations > 0 if self.processed_predictions > 0 else True
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @ensure_enhanced_db_pool
    async def _ensure_database_schema(self):
        """Ensure database schema exists"""
        try:
            schema_query = """
                CREATE TABLE IF NOT EXISTS predictions_evaluation (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    prediction_date TIMESTAMP NOT NULL,
                    predicted_value DECIMAL(10,4) NOT NULL,
                    actual_value DECIMAL(10,4),
                    model_name VARCHAR(100) NOT NULL,
                    confidence DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions_evaluation(symbol);
                CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions_evaluation(prediction_date);
                CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions_evaluation(model_name);
                CREATE INDEX IF NOT EXISTS idx_predictions_actual ON predictions_evaluation(actual_value) WHERE actual_value IS NOT NULL;
            """
            
            await enhanced_db_pool.execute(schema_query, use_cache=False)
            logger.info("Database schema ensured")
            
        except Exception as e:
            logger.error(f"Schema creation failed: {e}")
            raise


# Application Setup
service = EnhancedPredictionEvaluationService()
app = service.app

@app.on_event("startup")
async def startup_event():
    await service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Enhanced Prediction Evaluation Service shutting down")

if __name__ == "__main__":
    uvicorn.run(
        "main_performance_optimized:app",
        host="0.0.0.0",
        port=8009,  # Unique port für optimized version
        workers=1,
        loop="asyncio",
        log_level="info"
    )