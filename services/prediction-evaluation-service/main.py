#!/usr/bin/env python3
"""
Prediction Evaluation Service - Automatische IST-Berechnung
Clean Architecture Service für tägliche IST-Wert Erfassung

ANFORDERUNGEN:
- Tag der Berechnung tracking (calculation_date)
- Vorhersage-Zieldatum tracking (target_date)  
- IST-Wert zum Fälligkeitsdatum (actual_value mit evaluation_date)

Autor: Claude Code
Datum: 25. August 2025
Version: 1.0.0
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
import asyncpg
import redis.asyncio as aioredis
import yfinance as yf
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
import json

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===============================================================================
# DOMAIN LAYER - Entities und Value Objects
# ===============================================================================

class PendingEvaluation(BaseModel):
    """Domain Entity für ausstehende Evaluierungen"""
    prediction_id: str
    symbol: str
    company_name: Optional[str]
    predicted_value: Decimal
    target_date: date
    horizon_type: str
    calculation_date: datetime
    
class EvaluationResult(BaseModel):
    """Value Object für Evaluierungs-Ergebnis"""
    prediction_id: str
    symbol: str
    actual_value: Decimal
    evaluation_date: datetime
    market_price: Decimal
    data_source: str = "yahoo_finance"
    success: bool = True
    error_message: Optional[str] = None

# ===============================================================================
# APPLICATION LAYER - Use Cases
# ===============================================================================

class EvaluationUseCase:
    """Use Case für Vorhersage-Evaluierung"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: aioredis.Redis):
        self.db_pool = db_pool
        self.redis_client = redis_client
        
    async def get_pending_evaluations(self, evaluation_date: date = None) -> List[PendingEvaluation]:
        """Hole alle fälligen Evaluierungen"""
        if evaluation_date is None:
            evaluation_date = date.today()
            
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT 
                    prediction_id, symbol, company_name, predicted_value,
                    target_date, horizon_type, calculation_date
                FROM get_pending_evaluations($1)
            """
            rows = await conn.fetch(query, evaluation_date)
            
            return [
                PendingEvaluation(
                    prediction_id=row['prediction_id'],
                    symbol=row['symbol'],
                    company_name=row['company_name'],
                    predicted_value=row['predicted_value'],
                    target_date=row['target_date'],
                    horizon_type=row['horizon_type'],
                    calculation_date=row['calculation_date']
                )
                for row in rows
            ]
    
    async def evaluate_prediction(self, evaluation: PendingEvaluation) -> EvaluationResult:
        """Evaluiere eine einzelne Vorhersage"""
        try:
            # Hole aktuellen Marktwert
            market_price = await self._fetch_market_price(evaluation.symbol)
            
            # Berechne IST-Gewinn (vereinfacht: Prozentuale Änderung)
            # In Production: Komplexere Berechnung basierend auf Portfolio-Position
            actual_value = market_price  # Vereinfacht für Demo
            
            # Speichere in Datenbank
            async with self.db_pool.acquire() as conn:
                success = await conn.fetchval(
                    "SELECT evaluate_prediction($1, $2)",
                    evaluation.prediction_id,
                    actual_value
                )
                
            if success:
                # Publiziere Event
                await self._publish_evaluation_event(evaluation, actual_value)
                
                return EvaluationResult(
                    prediction_id=evaluation.prediction_id,
                    symbol=evaluation.symbol,
                    actual_value=actual_value,
                    evaluation_date=datetime.now(),
                    market_price=market_price,
                    success=True
                )
            else:
                raise Exception("Failed to update database")
                
        except Exception as e:
            logger.error(f"Evaluation failed for {evaluation.symbol}: {e}")
            
            # Update error status in queue
            await self._mark_evaluation_failed(evaluation.prediction_id, str(e))
            
            return EvaluationResult(
                prediction_id=evaluation.prediction_id,
                symbol=evaluation.symbol,
                actual_value=Decimal("0"),
                evaluation_date=datetime.now(),
                market_price=Decimal("0"),
                success=False,
                error_message=str(e)
            )
    
    async def _fetch_market_price(self, symbol: str) -> Decimal:
        """Hole aktuellen Marktpreis von Yahoo Finance"""
        try:
            # Cache-Check
            cache_key = f"market_price:{symbol}:{date.today()}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                return Decimal(cached.decode())
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            
            if current_price:
                price = Decimal(str(current_price))
                # Cache für 1 Stunde
                await self.redis_client.setex(cache_key, 3600, str(price))
                return price
            else:
                raise ValueError(f"No price data for {symbol}")
                
        except Exception as e:
            logger.error(f"Failed to fetch market price for {symbol}: {e}")
            raise
    
    async def _publish_evaluation_event(self, evaluation: PendingEvaluation, actual_value: Decimal):
        """Publiziere Evaluation-Event über Redis"""
        event = {
            "event_type": "prediction.evaluation.completed",
            "event_data": {
                "prediction_id": evaluation.prediction_id,
                "symbol": evaluation.symbol,
                "calculation_date": evaluation.calculation_date.isoformat(),
                "target_date": evaluation.target_date.isoformat(),
                "evaluation_date": datetime.now().isoformat(),
                "predicted_value": float(evaluation.predicted_value),
                "actual_value": float(actual_value),
                "horizon_type": evaluation.horizon_type,
                "accuracy": float(self._calculate_accuracy(evaluation.predicted_value, actual_value))
            },
            "metadata": {
                "service": "prediction-evaluation-service",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await self.redis_client.publish(
            "events:prediction.evaluation.completed",
            json.dumps(event)
        )
    
    def _calculate_accuracy(self, predicted: Decimal, actual: Decimal) -> Decimal:
        """Berechne Genauigkeit der Vorhersage"""
        if predicted == 0:
            return Decimal("0")
        error = abs(actual - predicted) / abs(predicted)
        accuracy = max(0, 1 - error) * 100
        return Decimal(str(round(float(accuracy), 2)))
    
    async def _mark_evaluation_failed(self, prediction_id: str, error_message: str):
        """Markiere Evaluierung als fehlgeschlagen"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE prediction_evaluation_queue
                SET 
                    processing_status = 'failed',
                    last_error = $2,
                    last_error_at = CURRENT_TIMESTAMP,
                    retry_count = retry_count + 1
                WHERE prediction_id = $1
            """, prediction_id, error_message)

# ===============================================================================
# INFRASTRUCTURE LAYER - External Services
# ===============================================================================

class DatabaseConnection:
    """Database Connection Manager"""
    
    def __init__(self):
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "10.1.1.174"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "aktienanalyse_events"),
            user=os.getenv("POSTGRES_USER", "aktienanalyse"),
            password=os.getenv("POSTGRES_PASSWORD"),
            min_size=2,
            max_size=10
        )
        logger.info("Database connection pool initialized")
        
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

class RedisConnection:
    """Redis Connection Manager"""
    
    def __init__(self):
        self.client = None
        
    async def initialize(self):
        """Initialize Redis connection"""
        self.client = await aioredis.from_url(
            f"redis://{os.getenv('REDIS_HOST', '10.1.1.174')}:{os.getenv('REDIS_PORT', '6379')}",
            encoding="utf-8",
            decode_responses=False
        )
        logger.info("Redis connection initialized")
        
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

# ===============================================================================
# PRESENTATION LAYER - API
# ===============================================================================

class EvaluationRequest(BaseModel):
    """Request model für manuelle Evaluierung"""
    symbol: Optional[str] = None
    date: Optional[date] = Field(default_factory=date.today)
    force: bool = False

class EvaluationResponse(BaseModel):
    """Response model für Evaluierung"""
    evaluated_count: int
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]

# FastAPI App mit Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Prediction Evaluation Service...")
    
    # Initialize connections
    app.state.db = DatabaseConnection()
    await app.state.db.initialize()
    
    app.state.redis = RedisConnection()
    await app.state.redis.initialize()
    
    # Initialize use case
    app.state.evaluation_use_case = EvaluationUseCase(
        app.state.db.pool,
        app.state.redis.client
    )
    
    # Start background evaluation task
    app.state.background_task = asyncio.create_task(
        background_evaluation_loop(app.state.evaluation_use_case)
    )
    
    logger.info("Prediction Evaluation Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Prediction Evaluation Service...")
    
    # Cancel background task
    if hasattr(app.state, 'background_task'):
        app.state.background_task.cancel()
        try:
            await app.state.background_task
        except asyncio.CancelledError:
            pass
    
    # Close connections
    await app.state.db.close()
    await app.state.redis.close()
    
    logger.info("Prediction Evaluation Service shut down")

# Create FastAPI app
app = FastAPI(
    title="Prediction Evaluation Service",
    description="Automatische IST-Berechnung für SOLL-IST Tracking",
    version="1.0.0",
    lifespan=lifespan
)

# ===============================================================================
# API ENDPOINTS
# ===============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "prediction-evaluation-service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/pending-evaluations")
async def get_pending_evaluations(date: Optional[date] = None):
    """Hole alle ausstehenden Evaluierungen"""
    try:
        evaluations = await app.state.evaluation_use_case.get_pending_evaluations(date)
        return {
            "count": len(evaluations),
            "date": str(date or date.today()),
            "evaluations": [e.dict() for e in evaluations]
        }
    except Exception as e:
        logger.error(f"Failed to get pending evaluations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/evaluate", response_model=EvaluationResponse)
async def trigger_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks):
    """Trigger manuelle Evaluierung"""
    try:
        # Hole ausstehende Evaluierungen
        evaluations = await app.state.evaluation_use_case.get_pending_evaluations(request.date)
        
        # Filter nach Symbol wenn angegeben
        if request.symbol:
            evaluations = [e for e in evaluations if e.symbol == request.symbol]
        
        # Evaluiere alle
        results = []
        success_count = 0
        failed_count = 0
        
        for evaluation in evaluations:
            result = await app.state.evaluation_use_case.evaluate_prediction(evaluation)
            results.append({
                "prediction_id": result.prediction_id,
                "symbol": result.symbol,
                "actual_value": float(result.actual_value),
                "success": result.success,
                "error": result.error_message
            })
            
            if result.success:
                success_count += 1
            else:
                failed_count += 1
        
        return EvaluationResponse(
            evaluated_count=len(evaluations),
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/statistics")
async def get_statistics():
    """Hole Evaluierungs-Statistiken"""
    try:
        async with app.state.db.pool.acquire() as conn:
            # Statistiken aus der Datenbank
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE status = 'evaluated') as evaluated_count,
                    COUNT(*) FILTER (WHERE status = 'error') as error_count,
                    AVG(performance_accuracy) FILTER (WHERE status = 'evaluated') as avg_accuracy,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    MIN(target_date) as oldest_pending_date,
                    MAX(target_date) as newest_pending_date
                FROM prediction_tracking_unified
            """)
            
            return {
                "pending_evaluations": stats['pending_count'],
                "completed_evaluations": stats['evaluated_count'],
                "failed_evaluations": stats['error_count'],
                "average_accuracy": float(stats['avg_accuracy']) if stats['avg_accuracy'] else None,
                "unique_symbols": stats['unique_symbols'],
                "date_range": {
                    "oldest": str(stats['oldest_pending_date']) if stats['oldest_pending_date'] else None,
                    "newest": str(stats['newest_pending_date']) if stats['newest_pending_date'] else None
                }
            }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================================================
# BACKGROUND TASKS
# ===============================================================================

async def background_evaluation_loop(use_case: EvaluationUseCase):
    """Background loop für automatische tägliche Evaluierung"""
    logger.info("Starting background evaluation loop")
    
    while True:
        try:
            # Warte bis zur nächsten vollen Stunde
            now = datetime.now()
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            wait_seconds = (next_hour - now).total_seconds()
            
            logger.info(f"Waiting {wait_seconds:.0f} seconds until next evaluation run")
            await asyncio.sleep(wait_seconds)
            
            # Führe Evaluierung durch
            logger.info("Starting automatic evaluation run")
            evaluations = await use_case.get_pending_evaluations()
            
            success_count = 0
            failed_count = 0
            
            for evaluation in evaluations:
                result = await use_case.evaluate_prediction(evaluation)
                if result.success:
                    success_count += 1
                    logger.info(f"Successfully evaluated {evaluation.symbol}: {result.actual_value}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to evaluate {evaluation.symbol}: {result.error_message}")
                
                # Kleine Pause zwischen Evaluierungen
                await asyncio.sleep(1)
            
            logger.info(f"Evaluation run completed: {success_count} success, {failed_count} failed")
            
        except asyncio.CancelledError:
            logger.info("Background evaluation loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background evaluation loop: {e}")
            await asyncio.sleep(60)  # Warte 1 Minute bei Fehler

# ===============================================================================
# MAIN
# ===============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SERVICE_PORT", "8026"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )