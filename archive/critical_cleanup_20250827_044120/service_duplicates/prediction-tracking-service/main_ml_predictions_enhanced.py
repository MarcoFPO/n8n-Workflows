#!/usr/bin/env python3
"""
Enhanced Prediction Tracking Service v6.2.0 - ml_predictions Integration
KI-Prognosen mit Durchschnittswerte-Integration für GUI

ANGEPASST FÜR: ml_predictions Tabelle (Produktionsserver 10.1.1.174)

CLEAN ARCHITECTURE LAYERS:
- Domain: ML Prediction entities mit Durchschnittswerte-Support
- Application: Enhanced SOLL-IST comparison + Averages Use Cases
- Infrastructure: PostgreSQL mit ml_predictions Integration
- Presentation: FastAPI REST endpoints für GUI-Integration

NEUE FEATURES:
- Durchschnittswerte-Berechnung aus ml_predictions JSONB data
- Timeline-Navigation kompatible API-Endpoints
- Performance-optimierte Database Queries für mv_ki_prognosen_averages
- Materialized Views für <2s GUI-Ladezeit

Autor: Claude Code
Datum: 26. August 2025
Version: 6.2.0 - ML Predictions Enhanced Averages für KI-Prognosen GUI
"""

import asyncio
import asyncpg
import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
from dataclasses import dataclass
from abc import ABC, abstractmethod

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# =============================================================================
# CONFIGURATION (Environment-based, No Hard-coded Values)
# =============================================================================

class EnhancedMLPredictionsConfig:
    """
    Configuration Management für ML Predictions Enhanced Service
    
    CLEAN ARCHITECTURE: Environment-based Configuration
    """
    
    def __init__(self):
        # Database Configuration
        self.database_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "aktienanalyse"),
            "user": os.getenv("DB_USER", "postgres"),  # Produktionsserver verwendet postgres
            "password": os.getenv("DB_PASSWORD", ""),
            "port": int(os.getenv("DB_PORT", "5432"))
        }
        
        # Service Configuration
        self.service_config = {
            "host": os.getenv("SERVICE_HOST", "0.0.0.0"),
            "port": int(os.getenv("SERVICE_PORT", "8018")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "enable_cors": os.getenv("ENABLE_CORS", "true").lower() == "true"
        }
        
        # Performance Configuration
        self.performance_config = {
            "default_limit": int(os.getenv("DEFAULT_LIMIT", "50")),
            "max_limit": int(os.getenv("MAX_LIMIT", "200")),
            "query_timeout": int(os.getenv("QUERY_TIMEOUT", "30")),
            "connection_pool_size": int(os.getenv("CONNECTION_POOL_SIZE", "10"))
        }

# Global Configuration Instance
config = EnhancedMLPredictionsConfig()

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=getattr(logging, config.service_config["log_level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced-ml-predictions-service")

# =============================================================================
# DOMAIN LAYER - Business Entities
# =============================================================================

class MLPredictionWithAverages(BaseModel):
    """Domain Entity: ML Prediction mit integrierten Durchschnittswerten"""
    prediction_id: str = Field(..., description="Eindeutige Prediction ID")
    symbol: str = Field(..., description="Aktiensymbol")
    prediction_type: str = Field(..., description="Art der Vorhersage")
    calculation_date: str = Field(..., description="Berechnungszeitpunkt (Date)")
    predicted_value: float = Field(..., description="Prognostizierter Wert")
    target_price: Optional[float] = Field(None, description="Zielpreis")
    confidence_score: float = Field(..., description="Konfidenz-Score")
    timeframe: str = Field(..., description="Zeitrahmen (1W, 1M, 3M, 12M)")
    horizon_days: int = Field(..., description="Vorhersage-Horizont in Tagen")
    
    # Durchschnittswerte (Kernfunktionalität für GUI)
    avg_prediction: Optional[float] = Field(None, description="Durchschnittswert")
    avg_confidence: Optional[float] = Field(None, description="Durchschnitts-Konfidenz")
    deviation_percent: Optional[float] = Field(None, description="Abweichung vom Durchschnitt in %")
    performance_indicator: str = Field("UNKNOWN", description="Performance-Indikator")
    data_basis_count: Optional[int] = Field(None, description="Datenbasis für Durchschnitt")
    
class AveragesSummary(BaseModel):
    """Domain Entity: Durchschnittswerte-Übersicht für GUI"""
    symbol: str
    timeframe: str
    prediction_count: int
    avg_predicted_value: Optional[float]
    avg_target_price: Optional[float]
    avg_confidence: Optional[float]
    predicted_value_stddev: Optional[float]
    earliest_prediction: datetime
    latest_prediction: datetime
    last_updated: datetime

class EnhancedMLPredictionResponse(BaseModel):
    """Application Response: Erweiterte ML Prediction-Antwort für GUI"""
    predictions: List[MLPredictionWithAverages]
    timeframe: str
    total_count: int
    averages_available: bool
    symbols_with_averages: int
    navigation_info: Dict[str, Any]
    enhanced_features: Dict[str, Any]

# =============================================================================
# INFRASTRUCTURE LAYER - Database Repository
# =============================================================================

class IMLPredictionAveragesRepository(ABC):
    """Interface für ML Prediction Averages Repository (Interface Segregation)"""
    
    @abstractmethod
    async def get_ml_predictions_with_averages(
        self, 
        timeframe: str, 
        limit: int, 
        symbol: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Lade ML Predictions mit Durchschnittswerten"""
        pass
    
    @abstractmethod
    async def get_averages_summary(self, timeframe: Optional[str]) -> List[Dict[str, Any]]:
        """Lade Durchschnittswerte-Übersicht"""
        pass
    
    @abstractmethod
    async def refresh_averages_materialized_view(self) -> bool:
        """Refresh Materialized View für Performance"""
        pass

class PostgreSQLMLPredictionsRepository(IMLPredictionAveragesRepository):
    """
    Concrete Implementation für ML Predictions mit PostgreSQL
    
    SOLID Principle: Single Responsibility für ML Predictions Data Access
    """
    
    def __init__(self, connection_pool: Optional[asyncpg.Pool] = None):
        self.connection_pool = connection_pool
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection mit Error Handling"""
        if self.connection_pool:
            return await self.connection_pool.acquire()
        
        try:
            return await asyncpg.connect(
                host=config.database_config["host"],
                database=config.database_config["database"],
                user=config.database_config["user"],
                password=config.database_config["password"],
                port=config.database_config["port"],
                command_timeout=config.performance_config["query_timeout"]
            )
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database connection failed"
            )
    
    async def get_ml_predictions_with_averages(
        self, 
        timeframe: str, 
        limit: int, 
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lade ML Predictions mit Durchschnittswerten aus PostgreSQL
        
        Verwendet die neue v_ki_prognosen_with_averages View für Performance
        """
        conn = await self.get_connection()
        try:
            # Query für ML Predictions mit Durchschnittswerten
            query = """
            SELECT 
                prediction_id,
                symbol,
                calculation_date,
                predicted_value,
                target_price,
                confidence_score,
                timeframe,
                horizon_days,
                avg_prediction,
                avg_confidence,
                deviation_percent,
                performance_indicator,
                data_basis_count,
                'ml_prediction' as prediction_type
            FROM v_ki_prognosen_with_averages
            WHERE 
                ($1::text IS NULL OR timeframe = $1)
                AND ($2::text IS NULL OR symbol = $2)
            ORDER BY calculation_date DESC, symbol
            LIMIT $3
            """
            
            rows = await conn.fetch(query, timeframe, symbol, limit)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching ML predictions with averages: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch predictions: {str(e)}"
            )
        finally:
            if self.connection_pool:
                await self.connection_pool.release(conn)
            else:
                await conn.close()
    
    async def get_averages_summary(self, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lade Durchschnittswerte-Übersicht aus Materialized View
        
        Performance-optimiert für GUI Dashboard
        """
        conn = await self.get_connection()
        try:
            query = """
            SELECT 
                symbol,
                timeframe,
                prediction_count,
                avg_predicted_value,
                avg_target_price,
                avg_confidence,
                predicted_value_stddev,
                earliest_prediction,
                latest_prediction,
                last_updated
            FROM mv_ki_prognosen_averages
            WHERE ($1::text IS NULL OR timeframe = $1)
            ORDER BY symbol, timeframe
            """
            
            rows = await conn.fetch(query, timeframe)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching averages summary: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch averages summary: {str(e)}"
            )
        finally:
            if self.connection_pool:
                await self.connection_pool.release(conn)
            else:
                await conn.close()
    
    async def refresh_averages_materialized_view(self) -> bool:
        """
        Refresh Materialized View für aktuelle Durchschnittswerte
        
        Performance-Optimierung für GUI
        """
        conn = await self.get_connection()
        try:
            await conn.execute("SELECT refresh_ki_prognosen_averages_mv();")
            logger.info("Materialized view refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing materialized view: {e}")
            return False
        finally:
            if self.connection_pool:
                await self.connection_pool.release(conn)
            else:
                await conn.close()

# =============================================================================
# APPLICATION LAYER - Use Cases
# =============================================================================

class EnhancedMLPredictionUseCase:
    """
    Application Layer: Use Case für Enhanced ML Predictions
    
    SOLID Principle: Single Responsibility für Business Logic
    """
    
    def __init__(self, repository: IMLPredictionAveragesRepository):
        self.repository = repository
    
    async def get_enhanced_predictions(
        self, 
        timeframe: str = "1M", 
        limit: int = 50,
        symbol: Optional[str] = None
    ) -> EnhancedMLPredictionResponse:
        """
        Core Use Case: Lade Enhanced ML Predictions für GUI
        
        Business Logic für Durchschnittswerte-Integration
        """
        try:
            # Lade ML Predictions mit Durchschnittswerten
            predictions_data = await self.repository.get_ml_predictions_with_averages(
                timeframe=timeframe,
                limit=limit,
                symbol=symbol
            )
            
            # Lade Durchschnittswerte-Übersicht
            averages_summary = await self.repository.get_averages_summary(timeframe)
            
            # Domain Entities erstellen
            predictions = []
            for data in predictions_data:
                prediction = MLPredictionWithAverages(
                    prediction_id=data["prediction_id"],
                    symbol=data["symbol"],
                    prediction_type=data.get("prediction_type", "ml_prediction"),
                    calculation_date=str(data["calculation_date"]),
                    predicted_value=float(data["predicted_value"]) if data["predicted_value"] else 0.0,
                    target_price=float(data["target_price"]) if data.get("target_price") else None,
                    confidence_score=float(data["confidence_score"]) if data["confidence_score"] else 0.0,
                    timeframe=data["timeframe"],
                    horizon_days=int(data["horizon_days"]) if data.get("horizon_days") else 30,
                    avg_prediction=float(data["avg_prediction"]) if data.get("avg_prediction") else None,
                    avg_confidence=float(data["avg_confidence"]) if data.get("avg_confidence") else None,
                    deviation_percent=float(data["deviation_percent"]) if data.get("deviation_percent") else None,
                    performance_indicator=data.get("performance_indicator", "UNKNOWN"),
                    data_basis_count=int(data["data_basis_count"]) if data.get("data_basis_count") else None
                )
                predictions.append(prediction)
            
            # Navigation Info für Timeline-Kompatibilität
            navigation_info = {
                "timeframe": timeframe,
                "total_predictions": len(predictions),
                "symbols_available": len(set(p.symbol for p in predictions)),
                "has_previous": False,  # Implementierung für Timeline-Navigation
                "has_next": len(predictions) >= limit
            }
            
            # Enhanced Features Info für GUI
            enhanced_features = {
                "averages_support": True,
                "deviation_calculation": True,
                "performance_indicators": True,
                "timeline_navigation": True,
                "real_time_updates": False
            }
            
            return EnhancedMLPredictionResponse(
                predictions=predictions,
                timeframe=timeframe,
                total_count=len(predictions),
                averages_available=len(averages_summary) > 0,
                symbols_with_averages=len(averages_summary),
                navigation_info=navigation_info,
                enhanced_features=enhanced_features
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced predictions use case: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process enhanced predictions: {str(e)}"
            )

# =============================================================================
# PRESENTATION LAYER - FastAPI Controllers
# =============================================================================

# FastAPI App mit Enhanced Features
app = FastAPI(
    title="Enhanced ML Predictions Tracking Service",
    version="6.2.0",
    description="KI-Prognosen mit Durchschnittswerte-Integration für GUI"
)

# CORS Configuration
if config.service_config["enable_cors"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Repository Instance (Singleton Pattern)
ml_predictions_repository = PostgreSQLMLPredictionsRepository()

# Use Case Instance
enhanced_use_case = EnhancedMLPredictionUseCase(ml_predictions_repository)

# =============================================================================
# API ENDPOINTS - GUI Integration
# =============================================================================

@app.get("/health")
async def health_check():
    """Health Check für Service Monitoring"""
    return {
        "status": "healthy",
        "version": "6.2.0",
        "service": "enhanced-ml-predictions-tracking",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "averages_support": True,
            "ml_predictions_integration": True,
            "performance_optimized": True
        }
    }

@app.get("/api/v1/data/predictions", response_model=EnhancedMLPredictionResponse)
async def get_enhanced_predictions(
    timeframe: str = Query("1M", description="Zeitrahmen (1W, 1M, 3M, 12M)"),
    limit: int = Query(50, description="Anzahl Datensätze", ge=1, le=200),
    symbol: Optional[str] = Query(None, description="Spezifisches Symbol (optional)")
):
    """
    Enhanced ML Predictions mit Durchschnittswerten für GUI
    
    KERNFUNKTION für KI-Prognosen GUI:
    - Durchschnittswerte pro Symbol und Zeitrahmen
    - Abweichungs-Berechnung
    - Performance-Indikatoren
    - Timeline-Navigation kompatibel
    """
    return await enhanced_use_case.get_enhanced_predictions(
        timeframe=timeframe,
        limit=limit,
        symbol=symbol
    )

@app.get("/api/v1/data/averages-summary", response_model=List[AveragesSummary])
async def get_averages_summary(
    timeframe: Optional[str] = Query(None, description="Filter nach Zeitrahmen (optional)")
):
    """
    Durchschnittswerte-Übersicht für Dashboard
    
    Performance-optimierte Abfrage der Materialized View
    """
    summary_data = await ml_predictions_repository.get_averages_summary(timeframe)
    
    return [
        AveragesSummary(
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            prediction_count=data["prediction_count"],
            avg_predicted_value=float(data["avg_predicted_value"]) if data["avg_predicted_value"] else None,
            avg_target_price=float(data["avg_target_price"]) if data.get("avg_target_price") else None,
            avg_confidence=float(data["avg_confidence"]) if data["avg_confidence"] else None,
            predicted_value_stddev=float(data["predicted_value_stddev"]) if data.get("predicted_value_stddev") else None,
            earliest_prediction=data["earliest_prediction"],
            latest_prediction=data["latest_prediction"],
            last_updated=data["last_updated"]
        )
        for data in summary_data
    ]

@app.post("/api/v1/maintenance/refresh-averages")
async def refresh_averages_view():
    """
    Refresh Materialized View für aktuelle Durchschnittswerte
    
    Maintenance Endpoint für Performance-Optimierung
    """
    success = await ml_predictions_repository.refresh_averages_materialized_view()
    
    if success:
        return {
            "status": "success",
            "message": "Materialized view refreshed successfully",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh materialized view"
        )

@app.get("/api/v1/data/timeline/{symbol}")
async def get_symbol_timeline(
    symbol: str,
    timeframe: str = Query("1M", description="Zeitrahmen"),
    days_back: int = Query(30, description="Tage zurück", ge=1, le=365)
):
    """
    Timeline-Navigation für spezifisches Symbol
    
    Für detaillierte Analyse einzelner Aktien
    """
    predictions_data = await ml_predictions_repository.get_ml_predictions_with_averages(
        timeframe=timeframe,
        limit=days_back * 2,  # Puffer für mehrere Predictions pro Tag
        symbol=symbol
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data_points": len(predictions_data),
        "predictions": predictions_data,
        "timeline_info": {
            "start_date": predictions_data[-1]["calculation_date"] if predictions_data else None,
            "end_date": predictions_data[0]["calculation_date"] if predictions_data else None,
            "total_days": days_back
        }
    }

# =============================================================================
# SERVICE STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Service Startup mit Initialization"""
    logger.info("Enhanced ML Predictions Tracking Service v6.2.0 starting up...")
    logger.info(f"Database: {config.database_config['host']}:{config.database_config['port']}")
    logger.info(f"Service: {config.service_config['host']}:{config.service_config['port']}")
    
    # Test Database Connection
    try:
        test_conn = await ml_predictions_repository.get_connection()
        if ml_predictions_repository.connection_pool:
            await ml_predictions_repository.connection_pool.release(test_conn)
        else:
            await test_conn.close()
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Service Shutdown mit Cleanup"""
    logger.info("Enhanced ML Predictions Tracking Service shutting down...")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Service starten
    logger.info("🚀 Starting Enhanced ML Predictions Tracking Service v6.2.0")
    logger.info("📊 Features: ML Predictions + Durchschnittswerte + Timeline-Navigation")
    
    uvicorn.run(
        app,
        host=config.service_config["host"],
        port=config.service_config["port"],
        log_level=config.service_config["log_level"].lower(),
        access_log=True,
        server_header=False
    )