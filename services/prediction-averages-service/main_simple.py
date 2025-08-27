#!/usr/bin/env python3
"""
Enhanced Predictions Averages Service - Simplified Version
Clean Architecture v6.0 Compliant Service für Mittelwert-Berechnungen
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_CONFIG = {
    "host": "10.1.1.174",
    "port": 5432,
    "database": "aktienanalyse_events", 
    "user": "aktienanalyse",
    "password": "secure_password_2025"
}

# FastAPI App
app = FastAPI(
    title="Enhanced Predictions Averages Service",
    description="Service für erweiterte Vorhersage-Mittelwerte mit Clean Architecture v6.0",
    version="1.0.0"
)

# Pydantic Models
class PredictionAveragesResponse(BaseModel):
    symbol: str
    averages: Dict[str, float]
    last_updated: datetime
    
class HealthResponse(BaseModel):
    status: str
    service: str
    database_connected: bool
    timestamp: datetime

class DatabaseService:
    """Database Service für PostgreSQL Operationen"""
    
    def __init__(self):
        self.pool = None
    
    async def initialize(self):
        """Database Pool initialisieren"""
        try:
            self.pool = await asyncpg.create_pool(
                host=DATABASE_CONFIG["host"],
                port=DATABASE_CONFIG["port"],
                database=DATABASE_CONFIG["database"],
                user=DATABASE_CONFIG["user"],
                password=DATABASE_CONFIG["password"],
                min_size=1,
                max_size=10
            )
            logger.info("Database pool initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    async def get_prediction_averages(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Hole Vorhersage-Mittelwerte für ein Symbol"""
        if not self.pool:
            return None
        
        query = """
        SELECT 
            symbol,
            avg_prediction_1w,
            avg_prediction_1m,
            avg_prediction_3m,
            avg_prediction_12m,
            avg_calculation_date
        FROM soll_ist_gewinn_tracking 
        WHERE symbol = $1 
        ORDER BY avg_calculation_date DESC 
        LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(query, symbol)
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"Error fetching prediction averages: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Database Health Check"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Global Database Service Instance
db_service = DatabaseService()

@app.on_event("startup")
async def startup_event():
    """Application Startup"""
    logger.info("Enhanced Predictions Averages Service starting up...")
    success = await db_service.initialize()
    if not success:
        logger.error("Failed to initialize database connection")
        raise RuntimeError("Database initialization failed")
    logger.info("Service startup completed successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application Shutdown"""
    logger.info("Enhanced Predictions Averages Service shutting down...")
    if db_service.pool:
        await db_service.pool.close()
    logger.info("Service shutdown completed")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health Check Endpoint"""
    db_connected = await db_service.health_check()
    
    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        service="Enhanced Predictions Averages Service",
        database_connected=db_connected,
        timestamp=datetime.utcnow()
    )

@app.get("/prediction-averages/{symbol}", response_model=PredictionAveragesResponse)
async def get_prediction_averages(symbol: str):
    """Hole Vorhersage-Mittelwerte für ein Symbol"""
    
    # Symbol validieren
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol ist erforderlich")
    
    # Daten aus Database holen
    result = await db_service.get_prediction_averages(symbol)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"Keine Vorhersage-Mittelwerte für Symbol {symbol} gefunden"
        )
    
    # Response zusammenbauen
    averages = {}
    if result.get('avg_prediction_1w'):
        averages['1W'] = float(result['avg_prediction_1w'])
    if result.get('avg_prediction_1m'):
        averages['1M'] = float(result['avg_prediction_1m'])
    if result.get('avg_prediction_3m'):
        averages['3M'] = float(result['avg_prediction_3m'])
    if result.get('avg_prediction_12m'):
        averages['12M'] = float(result['avg_prediction_12m'])
    
    return PredictionAveragesResponse(
        symbol=symbol,
        averages=averages,
        last_updated=result.get('avg_calculation_date', datetime.utcnow())
    )

@app.get("/prediction-averages")
async def list_available_symbols():
    """Liste verfügbare Symbole mit Vorhersage-Mittelwerten"""
    
    query = """
    SELECT DISTINCT symbol, avg_calculation_date
    FROM soll_ist_gewinn_tracking 
    WHERE avg_prediction_1w IS NOT NULL 
       OR avg_prediction_1m IS NOT NULL
       OR avg_prediction_3m IS NOT NULL  
       OR avg_prediction_12m IS NOT NULL
    ORDER BY avg_calculation_date DESC
    """
    
    try:
        async with db_service.pool.acquire() as conn:
            results = await conn.fetch(query)
            symbols = [
                {
                    "symbol": row['symbol'], 
                    "last_updated": row['avg_calculation_date']
                } 
                for row in results
            ]
            return {"symbols": symbols, "count": len(symbols)}
            
    except Exception as e:
        logger.error(f"Error fetching available symbols: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Symbole")

if __name__ == "__main__":
    # Service direkt starten für Testing
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8087,
        log_level="info",
        access_log=True
    )