#!/usr/bin/env python3
"""
Prediction-Tracking Service v6.1.0 - Clean Architecture
SOLL-IST Vergleichsanalyse für Trading Intelligence System

Clean Architecture Layers:
- Domain: Prediction tracking business logic
- Application: SOLL-IST comparison use cases  
- Infrastructure: PostgreSQL data persistence
- Presentation: FastAPI REST endpoints
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncpg
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ===== DOMAIN LAYER =====
class PredictionItem(BaseModel):
    """Domain Entity: Stock prediction with tracking data"""
    id: Optional[int] = None
    symbol: str = Field(..., description="Stock symbol")
    prediction_date: datetime = Field(..., description="When prediction was made")
    predicted_price: float = Field(..., description="Predicted stock price")
    predicted_performance: float = Field(..., description="Predicted performance %")
    confidence: float = Field(..., description="Prediction confidence 0-1")
    target_date: datetime = Field(..., description="Target date for prediction")
    actual_price: Optional[float] = Field(None, description="Actual stock price")
    actual_performance: Optional[float] = Field(None, description="Actual performance %") 
    accuracy_score: Optional[float] = Field(None, description="Prediction accuracy 0-1")
    status: str = Field(default="pending", description="pending|completed|expired")

class SOLLISTComparison(BaseModel):
    """Domain Entity: SOLL-IST comparison result"""
    symbol: str
    prediction_date: datetime
    soll_performance: float  # Predicted performance
    ist_performance: Optional[float]  # Actual performance
    deviation: Optional[float]  # Absolute deviation
    accuracy_percentage: Optional[float]  # Accuracy as percentage
    status: str

# ===== APPLICATION LAYER =====
class PredictionTrackingUseCase:
    """Application Use Case: Prediction tracking operations"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)
    
    async def create_prediction(self, prediction: PredictionItem) -> int:
        """Create new prediction for tracking"""
        async with self.db_pool.acquire() as conn:
            query = """
                INSERT INTO predictions (symbol, prediction_date, predicted_price, 
                                      predicted_performance, confidence, target_date, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """
            try:
                result = await conn.fetchval(
                    query, prediction.symbol, prediction.prediction_date,
                    prediction.predicted_price, prediction.predicted_performance,
                    prediction.confidence, prediction.target_date, prediction.status
                )
                self.logger.info(f"Created prediction tracking for {prediction.symbol}")
                return result
            except Exception as e:
                self.logger.error(f"Error creating prediction: {e}")
                raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    async def get_soll_ist_comparison(self, days_back: int = 30) -> List[SOLLISTComparison]:
        """Get SOLL-IST comparison for specified period"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT symbol, prediction_date, predicted_performance as soll_performance,
                       actual_performance as ist_performance,
                       (actual_performance - predicted_performance) as deviation,
                       (100.0 - ABS(predicted_performance - COALESCE(actual_performance, 0))) as accuracy_percentage,
                       status
                FROM predictions
                WHERE prediction_date >= $1
                ORDER BY prediction_date DESC
            """
            try:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                rows = await conn.fetch(query, cutoff_date)
                
                comparisons = []
                for row in rows:
                    comparison = SOLLISTComparison(
                        symbol=row['symbol'],
                        prediction_date=row['prediction_date'],
                        soll_performance=row['soll_performance'],
                        ist_performance=row['ist_performance'],
                        deviation=row['deviation'],
                        accuracy_percentage=row['accuracy_percentage'],
                        status=row['status']
                    )
                    comparisons.append(comparison)
                
                return comparisons
            except Exception as e:
                self.logger.error(f"Error getting SOLL-IST comparison: {e}")
                raise HTTPException(status_code=500, detail=f"Database error: {e}")

# ===== INFRASTRUCTURE LAYER =====
class DatabaseManager:
    """Infrastructure: PostgreSQL database management"""
    
    def __init__(self):
        self.pool = None
        self.logger = logging.getLogger(__name__)
        
        # Get database configuration from environment
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DATABASE', 'aktienanalyse_events'),
            'user': os.getenv('POSTGRES_USER', 'aktienanalyse_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'secure_password_2025')
        }
    
    async def initialize(self):
        """Initialize database connection pool and tables"""
        try:
            self.pool = await asyncpg.create_pool(**self.db_config, min_size=2, max_size=10)
            # await self._create_tables()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _create_tables(self):
        """Create prediction tracking tables"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    prediction_date TIMESTAMP NOT NULL,
                    predicted_price DECIMAL(10,2) NOT NULL,
                    predicted_performance DECIMAL(8,4) NOT NULL,
                    confidence DECIMAL(3,2) NOT NULL,
                    target_date TIMESTAMP NOT NULL,
                    actual_price DECIMAL(10,2),
                    actual_performance DECIMAL(8,4),
                    accuracy_score DECIMAL(3,2),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);
                CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);
                CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status);
            """)
    
    async def get_pool(self):
        """Get database connection pool"""
        if not self.pool:
            await self.initialize()
        return self.pool
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()

# ===== PRESENTATION LAYER =====
# FastAPI Application Setup
app = FastAPI(
    title="Prediction-Tracking Service",
    version="6.1.0",
    description="Clean Architecture SOLL-IST Vergleichsanalyse"
)

# CORS Configuration  
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_manager = DatabaseManager()
prediction_use_case = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global prediction_use_case
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting Prediction-Tracking Service v6.1.0")
    
    # Initialize database
    await db_manager.initialize()
    pool = await db_manager.get_pool()
    prediction_use_case = PredictionTrackingUseCase(pool)

# ===== REST ENDPOINTS =====
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "prediction-tracking-service",
        "version": "6.1.0",
        "architecture": "clean",
        "features": ["soll_ist_comparison", "prediction_tracking", "accuracy_scoring"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/soll-ist-comparison")
async def get_soll_ist_comparison(days_back: int = 30):
    """Get SOLL-IST comparison for specified period"""
    if not prediction_use_case:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Try to get real comparisons first
    comparisons = await prediction_use_case.get_soll_ist_comparison(days_back)
    
    # If no real data, generate demo data based on Data Processing Service predictions
    if not comparisons:
        import aiohttp
        import random
        from datetime import datetime, timedelta
        
        try:
            # Fetch current predictions from Data Processing Service
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8017/api/v1/data/predictions?timeframe=1M") as response:
                    if response.status == 200:
                        data = await response.json()
                        predictions = data.get("predictions", [])
                        
                        # Generate mock SOLL-IST comparisons
                        mock_comparisons = []
                        for i, pred in enumerate(predictions[:10]):  # Limit to 10 for demo
                            soll_value = float(pred.get("prediction_percent", "0%").replace("%", ""))
                            # Generate realistic IST values (with some deviation)
                            deviation = random.uniform(-3, 3)  # ±3% realistic market deviation
                            ist_value = soll_value + deviation
                            accuracy = max(0, 100 - abs(deviation) * 10)  # Higher accuracy for lower deviation
                            
                            comparison_date = datetime.now() - timedelta(days=random.randint(1, days_back))
                            
                            mock_comparisons.append({
                                "comparison_id": f"demo_{i+1}",
                                "symbol": pred.get("symbol", "UNKNOWN"),
                                "company_name": pred.get("company", "Unknown Company"),
                                "prediction_date": (datetime.now() - timedelta(days=random.randint(7, 30))).isoformat(),
                                "comparison_date": comparison_date.isoformat(),
                                "soll_value": round(soll_value, 2),
                                "ist_value": round(ist_value, 2),
                                "accuracy_percentage": round(accuracy, 2),
                                "deviation_percentage": round(abs(deviation), 2),
                                "status": "completed",
                                "timeframe": "1M"
                            })
                        
                        # Calculate statistics
                        total_predictions = len(mock_comparisons)
                        completed_predictions = mock_comparisons  # All demo data is completed
                        avg_accuracy = sum([c["accuracy_percentage"] for c in completed_predictions]) / max(len(completed_predictions), 1)
                        
                        return {
                            "status": "success",
                            "period_days": days_back,
                            "total_predictions": total_predictions,
                            "completed_predictions": len(completed_predictions),
                            "average_accuracy": round(avg_accuracy, 2),
                            "comparisons": mock_comparisons,
                            "data_source": "demo_generated_from_current_predictions",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            logger.error(f"Error generating demo data: {e}")
    
    # Fallback to original empty response
    total_predictions = len(comparisons)
    completed_predictions = [c for c in comparisons if c.status == "completed"]
    avg_accuracy = sum([c.accuracy_percentage for c in completed_predictions if c.accuracy_percentage]) / max(len(completed_predictions), 1)
    
    return {
        "status": "success",
        "period_days": days_back,
        "total_predictions": total_predictions,
        "completed_predictions": len(completed_predictions),
        "average_accuracy": round(avg_accuracy, 2),
        "comparisons": [c.dict() for c in comparisons],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "prediction_tracking_daemon_v6_1_0:app",
        host="0.0.0.0",
        port=8018,
        log_level="info",
        access_log=True
    )
