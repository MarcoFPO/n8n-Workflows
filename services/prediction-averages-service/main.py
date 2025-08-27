#!/usr/bin/env python3
"""
Prediction Averages Service v1.0.0
Clean Architecture Service für Mittelwert-Berechnungen der Vorhersage-Zeiträume

CLEAN ARCHITECTURE LAYERS:
- Presentation: FastAPI Controllers (REST API)
- Application: Use Cases & Business Logic 
- Domain: Entities & Business Rules
- Infrastructure: Database & External Services

PERFORMANCE TARGET: < 50ms für Mittelwert-Abfragen
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# ===============================================================================
# LOGGING SETUP
# ===============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===============================================================================
# DOMAIN MODELS (Clean Architecture - Domain Layer)
# ===============================================================================

class PredictionAverages(BaseModel):
    """Domain Entity: Prediction Averages für ein Symbol"""
    symbol: str = Field(..., max_length=10)
    datum: date
    unternehmen: Optional[str] = None
    
    # Aktuelle Vorhersagen
    soll_gewinn_1w: Optional[Decimal] = None
    soll_gewinn_1m: Optional[Decimal] = None
    soll_gewinn_3m: Optional[Decimal] = None
    soll_gewinn_12m: Optional[Decimal] = None
    
    # Mittelwerte
    avg_prediction_1w: Optional[Decimal] = None
    avg_prediction_1m: Optional[Decimal] = None
    avg_prediction_3m: Optional[Decimal] = None
    avg_prediction_12m: Optional[Decimal] = None
    
    # Metadaten
    avg_calculation_date: Optional[datetime] = None
    avg_sample_count_1w: Optional[int] = 0
    avg_sample_count_1m: Optional[int] = 0
    avg_sample_count_3m: Optional[int] = 0
    avg_sample_count_12m: Optional[int] = 0
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }

class PredictionAveragesSummary(BaseModel):
    """Zusammenfassung der Mittelwert-Berechnungen"""
    symbol: str
    datum: date
    
    # Performance-Metriken
    deviation_1w: Optional[Decimal] = None
    deviation_1m: Optional[Decimal] = None
    deviation_3m: Optional[Decimal] = None
    deviation_12m: Optional[Decimal] = None
    
    # Trend-Analyse
    trend_1w: Optional[str] = None  # ABOVE_AVERAGE, BELOW_AVERAGE, NEAR_AVERAGE, INSUFFICIENT_DATA
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }

class PredictionAveragesCalculation(BaseModel):
    """Response Model für Mittelwert-Berechnungen"""
    avg_1w: Optional[Decimal] = None
    avg_1m: Optional[Decimal] = None
    avg_3m: Optional[Decimal] = None
    avg_12m: Optional[Decimal] = None
    samples_1w: int = 0
    samples_1m: int = 0
    samples_3m: int = 0
    samples_12m: int = 0
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }

class PerformanceMetrics(BaseModel):
    """Performance-Metriken für die API"""
    query_time_ms: float
    record_count: int
    cache_hit: bool = False
    database_pool_status: str = "healthy"

# ===============================================================================
# APPLICATION LAYER - Use Cases
# ===============================================================================

class PredictionAveragesUseCase:
    """Business Logic für Prediction Averages"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        
    async def get_averages_for_symbol(
        self, 
        symbol: str, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[PredictionAverages]:
        """Hole Mittelwerte für ein Symbol"""
        
        start_time = datetime.now()
        
        async with self.db_pool.acquire() as conn:
            # Dynamische Query basierend auf Parametern
            where_conditions = ["symbol = $1"]
            params = [symbol]
            param_counter = 2
            
            if start_date:
                where_conditions.append(f"datum >= ${param_counter}")
                params.append(start_date)
                param_counter += 1
                
            if end_date:
                where_conditions.append(f"datum <= ${param_counter}")
                params.append(end_date)
                param_counter += 1
            
            query = f"""
                SELECT 
                    symbol, datum, unternehmen,
                    soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
                    avg_prediction_1w, avg_prediction_1m, avg_prediction_3m, avg_prediction_12m,
                    avg_calculation_date,
                    avg_sample_count_1w, avg_sample_count_1m, avg_sample_count_3m, avg_sample_count_12m
                FROM soll_ist_gewinn_tracking
                WHERE {' AND '.join(where_conditions)}
                ORDER BY datum DESC
                LIMIT ${param_counter}
            """
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            result = [
                PredictionAverages(
                    symbol=row['symbol'],
                    datum=row['datum'],
                    unternehmen=row['unternehmen'],
                    soll_gewinn_1w=row['soll_gewinn_1w'],
                    soll_gewinn_1m=row['soll_gewinn_1m'], 
                    soll_gewinn_3m=row['soll_gewinn_3m'],
                    soll_gewinn_12m=row['soll_gewinn_12m'],
                    avg_prediction_1w=row['avg_prediction_1w'],
                    avg_prediction_1m=row['avg_prediction_1m'],
                    avg_prediction_3m=row['avg_prediction_3m'],
                    avg_prediction_12m=row['avg_prediction_12m'],
                    avg_calculation_date=row['avg_calculation_date'],
                    avg_sample_count_1w=row['avg_sample_count_1w'],
                    avg_sample_count_1m=row['avg_sample_count_1m'],
                    avg_sample_count_3m=row['avg_sample_count_3m'],
                    avg_sample_count_12m=row['avg_sample_count_12m']
                )
                for row in rows
            ]
            
            query_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Query completed in {query_time:.2f}ms for symbol {symbol}")
            
            return result
    
    async def calculate_averages_for_symbol(
        self, 
        symbol: str, 
        target_date: Optional[date] = None
    ) -> PredictionAveragesCalculation:
        """Berechne Mittelwerte für ein Symbol zu einem bestimmten Datum"""
        
        if not target_date:
            target_date = date.today()
            
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM calculate_prediction_averages($1, $2)",
                symbol, target_date
            )
            
            return PredictionAveragesCalculation(
                avg_1w=row['avg_1w'],
                avg_1m=row['avg_1m'],
                avg_3m=row['avg_3m'],
                avg_12m=row['avg_12m'],
                samples_1w=row['samples_1w'],
                samples_1m=row['samples_1m'],
                samples_3m=row['samples_3m'],
                samples_12m=row['samples_12m']
            )
    
    async def update_averages_for_symbol(
        self, 
        symbol: str, 
        datum: Optional[date] = None
    ) -> bool:
        """Update Mittelwerte für ein Symbol"""
        
        if not datum:
            datum = date.today()
            
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT update_prediction_averages($1, $2)",
                symbol, datum
            )
            
            return bool(result)
    
    async def get_summary_view(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[PredictionAveragesSummary]:
        """Hole Summary-View mit Performance-Metriken"""
        
        async with self.db_pool.acquire() as conn:
            if symbols:
                # Spezifische Symbole
                placeholders = ",".join(f"${i+1}" for i in range(len(symbols)))
                query = f"""
                    SELECT symbol, datum, deviation_1w, deviation_1m, deviation_3m, deviation_12m, trend_1w
                    FROM v_prediction_averages_summary
                    WHERE symbol = ANY(${len(symbols)+1}::text[])
                    ORDER BY datum DESC, symbol
                    LIMIT ${len(symbols)+2}
                """
                rows = await conn.fetch(query, *symbols, symbols, limit)
            else:
                # Alle Symbole
                query = """
                    SELECT symbol, datum, deviation_1w, deviation_1m, deviation_3m, deviation_12m, trend_1w
                    FROM v_prediction_averages_summary
                    ORDER BY datum DESC, symbol
                    LIMIT $1
                """
                rows = await conn.fetch(query, limit)
            
            return [
                PredictionAveragesSummary(
                    symbol=row['symbol'],
                    datum=row['datum'],
                    deviation_1w=row['deviation_1w'],
                    deviation_1m=row['deviation_1m'],
                    deviation_3m=row['deviation_3m'],
                    deviation_12m=row['deviation_12m'],
                    trend_1w=row['trend_1w']
                )
                for row in rows
            ]

# ===============================================================================
# INFRASTRUCTURE LAYER - Database Connection
# ===============================================================================

DATABASE_CONFIG = {
    "host": "10.1.1.174",
    "port": 5432,
    "database": "aktienanalyse",
    "user": "aktienuser",
    "password": "aktienpass",  # In Production: Environment Variable
    "min_size": 10,
    "max_size": 20
}

db_pool: Optional[asyncpg.Pool] = None

async def get_database_pool() -> asyncpg.Pool:
    """Database Connection Pool Dependency"""
    global db_pool
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return db_pool

async def get_use_case(pool: asyncpg.Pool = Depends(get_database_pool)) -> PredictionAveragesUseCase:
    """Use Case Dependency Injection"""
    return PredictionAveragesUseCase(pool)

# ===============================================================================
# PRESENTATION LAYER - FastAPI Controllers
# ===============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application Lifespan Management"""
    global db_pool
    
    # Startup
    logger.info("Starting Prediction Averages Service v1.0.0")
    try:
        db_pool = await asyncpg.create_pool(**DATABASE_CONFIG)
        logger.info("Database connection pool created successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise
    finally:
        # Shutdown
        if db_pool:
            await db_pool.close()
            logger.info("Database connection pool closed")

# FastAPI App
app = FastAPI(
    title="Prediction Averages Service",
    description="Clean Architecture Service für Mittelwert-Berechnungen der Vorhersage-Zeiträume",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware (für private Entwicklungsumgebung)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private/interne Nutzung
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================================================================
# API ENDPOINTS
# ===============================================================================

@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    global db_pool
    
    pool_status = "healthy" if db_pool and not db_pool._closed else "unhealthy"
    
    return {
        "status": "healthy",
        "service": "prediction-averages-service",
        "version": "1.0.0",
        "database_pool": pool_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get(
    "/averages/{symbol}",
    response_model=List[PredictionAverages],
    summary="Mittelwerte für Symbol abrufen",
    description="Hole Prediction Averages für ein spezifisches Symbol mit optionalen Zeitraum-Filtern"
)
async def get_averages_for_symbol(
    symbol: str = Path(..., description="Aktiensymbol (z.B. AAPL)"),
    start_date: Optional[date] = Query(None, description="Start-Datum (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End-Datum (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl Ergebnisse"),
    use_case: PredictionAveragesUseCase = Depends(get_use_case)
):
    """Hole Mittelwerte für ein Symbol"""
    start_time = datetime.now()
    
    try:
        result = await use_case.get_averages_for_symbol(
            symbol=symbol.upper(),
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Performance-Header hinzufügen
        return result
        
    except Exception as e:
        logger.error(f"Error fetching averages for symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post(
    "/calculate/{symbol}",
    response_model=PredictionAveragesCalculation,
    summary="Mittelwerte berechnen",
    description="Berechne neue Mittelwerte für ein Symbol zu einem bestimmten Datum"
)
async def calculate_averages_for_symbol(
    symbol: str = Path(..., description="Aktiensymbol"),
    target_date: Optional[date] = Query(None, description="Ziel-Datum für Berechnung"),
    use_case: PredictionAveragesUseCase = Depends(get_use_case)
):
    """Berechne Mittelwerte für Symbol"""
    try:
        result = await use_case.calculate_averages_for_symbol(
            symbol=symbol.upper(),
            target_date=target_date
        )
        return result
        
    except Exception as e:
        logger.error(f"Error calculating averages for symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@app.put(
    "/update/{symbol}",
    summary="Mittelwerte aktualisieren",
    description="Update gespeicherte Mittelwerte für ein Symbol"
)
async def update_averages_for_symbol(
    symbol: str = Path(..., description="Aktiensymbol"),
    datum: Optional[date] = Query(None, description="Datum für Update"),
    use_case: PredictionAveragesUseCase = Depends(get_use_case)
):
    """Update Mittelwerte für Symbol"""
    try:
        success = await use_case.update_averages_for_symbol(
            symbol=symbol.upper(),
            datum=datum
        )
        
        return {
            "success": success,
            "symbol": symbol.upper(),
            "datum": datum or date.today(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating averages for symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@app.get(
    "/summary",
    response_model=List[PredictionAveragesSummary],
    summary="Summary-View mit Performance-Metriken",
    description="Hole aggregierte Summary-View mit Trend-Analyse und Performance-Metriken"
)
async def get_averages_summary(
    symbols: Optional[str] = Query(None, description="Komma-getrennte Liste von Symbolen"),
    limit: int = Query(50, ge=1, le=500, description="Maximale Anzahl Ergebnisse"),
    use_case: PredictionAveragesUseCase = Depends(get_use_case)
):
    """Summary-View abrufen"""
    try:
        symbols_list = None
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",")]
        
        result = await use_case.get_summary_view(
            symbols=symbols_list,
            limit=limit
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail=f"Summary fetch failed: {str(e)}")

@app.post(
    "/refresh-materialized-view",
    summary="Materialized View aktualisieren",
    description="Refresh der Performance-optimierten Materialized View"
)
async def refresh_materialized_view(
    pool: asyncpg.Pool = Depends(get_database_pool)
):
    """Refresh Materialized View für Performance"""
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT refresh_prediction_averages_materialized_view()"
            )
            
        return {
            "success": bool(result),
            "timestamp": datetime.now().isoformat(),
            "message": "Materialized view refreshed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing materialized view: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

# ===============================================================================
# MAIN ENTRY POINT
# ===============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8008,  # Neuer Port für Prediction Averages Service
        reload=False,
        log_level="info",
        access_log=True
    )