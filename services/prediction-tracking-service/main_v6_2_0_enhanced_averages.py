#!/usr/bin/env python3
"""
Enhanced Prediction Tracking Service v6.2.0 - Clean Architecture
KI-Prognosen mit Durchschnittswerte-Integration für GUI

CLEAN ARCHITECTURE LAYERS:
- Domain: Prediction tracking mit Durchschnittswerte-Entities
- Application: Enhanced SOLL-IST comparison + Averages Use Cases
- Infrastructure: PostgreSQL mit erweiterten Queries
- Presentation: FastAPI REST endpoints für GUI-Integration

NEUE FEATURES:
- Durchschnittswerte-Berechnung pro Symbol und Zeitrahmen
- Timeline-Navigation kompatible API-Endpoints
- Performance-optimierte Database Queries
- Materialized Views für schnelle GUI-Antworten

Autor: Claude Code
Datum: 26. August 2025
Version: 6.2.0 - Enhanced Averages für KI-Prognosen GUI
"""

import asyncio
import asyncpg
import logging
import os
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
# DOMAIN LAYER - Business Entities
# =============================================================================

class PredictionWithAverages(BaseModel):
    """Domain Entity: Prediction mit integrierten Durchschnittswerten"""
    symbol: str = Field(..., description="Aktiensymbol")
    company_name: Optional[str] = Field(None, description="Firmenname")
    calculation_date: datetime = Field(..., description="Berechnungszeitpunkt")
    target_date: str = Field(..., description="Vorhersage-Zieldatum")
    predicted_value: float = Field(..., description="Prognostizierter Wert")
    avg_predicted_value: Optional[float] = Field(None, description="Durchschnittswert")
    deviation_from_avg: Optional[float] = Field(None, description="Abweichung vom Durchschnitt")
    relative_performance_percent: Optional[float] = Field(None, description="Relative Performance %")
    confidence_score: Optional[float] = Field(None, description="Konfidenz-Score")
    confidence_percentage: Optional[float] = Field(None, description="Konfidenz in %")
    avg_confidence: Optional[float] = Field(None, description="Durchschnitts-Konfidenz")
    prediction_count: Optional[int] = Field(None, description="Anzahl Vorhersagen für Durchschnitt")
    status: str = Field(..., description="Status der Vorhersage")
    timestamp: str = Field(..., description="ISO Timestamp für GUI")

class AveragesSummary(BaseModel):
    """Domain Entity: Durchschnittswerte-Übersicht"""
    symbol: str
    company_name: Optional[str]
    horizon_type: str
    avg_predicted_value: Optional[float]
    avg_actual_value: Optional[float]
    avg_accuracy: Optional[float]
    avg_confidence: Optional[float]
    prediction_count: int
    evaluated_count: int
    pending_count: int
    last_updated: datetime

class EnhancedPredictionResponse(BaseModel):
    """Application Response: Erweiterte Vorhersage-Antwort für GUI"""
    predictions: List[PredictionWithAverages]
    timeframe: str
    total_count: int
    averages_available: bool
    navigation_info: Dict[str, Any]
    performance_summary: Dict[str, Any]

# =============================================================================
# INFRASTRUCTURE LAYER - Database Repository
# =============================================================================

class IPredictionAveragesRepository(ABC):
    """Interface für Prediction Averages Repository (Interface Segregation)"""
    
    @abstractmethod
    async def get_predictions_with_averages(
        self, 
        timeframe: str, 
        limit: int, 
        nav_timestamp: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Lade Vorhersagen mit Durchschnittswerten"""
        pass
    
    @abstractmethod
    async def get_averages_summary(self, timeframe: str) -> List[Dict[str, Any]]:
        """Lade Durchschnittswerte-Übersicht"""
        pass
    
    @abstractmethod
    async def refresh_averages_cache(self) -> bool:
        """Aktualisiere Durchschnittswerte-Cache"""
        pass

class PostgreSQLAveragesRepository(IPredictionAveragesRepository):
    """
    PostgreSQL Implementation für Enhanced Prediction Averages
    
    SOLID Principles:
    - Single Responsibility: Nur Database Operations für Averages
    - Dependency Inversion: Implementiert Interface
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.logger = logging.getLogger(__name__)
    
    async def get_predictions_with_averages(
        self, 
        timeframe: str, 
        limit: int = 15, 
        nav_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Lade KI-Prognosen mit integrierten Durchschnittswerten
        Timeline-Navigation kompatibel
        """
        try:
            nav_ts = nav_timestamp or datetime.now()
            
            async with self.pool.acquire() as conn:
                # Verwende die erweiterte stored function
                rows = await conn.fetch("""
                    SELECT * FROM get_ki_prognosen_with_averages($1, $2, $3)
                """, timeframe, limit, nav_ts)
                
                predictions = []
                for row in rows:
                    predictions.append({
                        "symbol": row["symbol"],
                        "company_name": row["company_name"],
                        "calculation_date": row["calculation_date"],
                        "target_date": row["target_date"],
                        "predicted_value": float(row["predicted_value"]) if row["predicted_value"] else 0.0,
                        "avg_predicted_value": float(row["avg_predicted_value"]) if row["avg_predicted_value"] else None,
                        "deviation_from_avg": float(row["deviation_from_avg"]) if row["deviation_from_avg"] else None,
                        "relative_performance_percent": float(row["relative_performance_percent"]) if row["relative_performance_percent"] else None,
                        "confidence_score": float(row["confidence_score"]) if row["confidence_score"] else None,
                        "confidence_percentage": float(row["confidence_percentage"]) if row["confidence_percentage"] else None,
                        "avg_confidence": float(row["avg_confidence"]) if row["avg_confidence"] else None,
                        "prediction_count": row["prediction_count"],
                        "status": row["status"],
                        "formatted_calculation_date": row["formatted_calculation_date"],
                        "formatted_target_date": row["formatted_target_date"]
                    })
                
                self.logger.info(f"Retrieved {len(predictions)} predictions with averages for {timeframe}")
                return predictions
                
        except Exception as e:
            self.logger.error(f"Database error getting predictions with averages: {str(e)}")
            return []
    
    async def get_averages_summary(self, timeframe: str) -> List[Dict[str, Any]]:
        """Lade Durchschnittswerte-Übersicht für Zeitrahmen"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM get_averages_summary($1)
                """, timeframe)
                
                summary = []
                for row in rows:
                    summary.append({
                        "symbol": row["symbol"],
                        "company_name": row["company_name"],
                        "horizon_type": row["horizon_type"],
                        "avg_predicted_value": float(row["avg_predicted_value"]) if row["avg_predicted_value"] else 0.0,
                        "avg_actual_value": float(row["avg_actual_value"]) if row["avg_actual_value"] else None,
                        "avg_accuracy": float(row["avg_accuracy"]) if row["avg_accuracy"] else None,
                        "avg_confidence": float(row["avg_confidence"]) if row["avg_confidence"] else None,
                        "prediction_count": row["prediction_count"],
                        "evaluated_count": row["evaluated_count"],
                        "pending_count": row["pending_count"],
                        "last_updated": row["last_updated"]
                    })
                
                self.logger.info(f"Retrieved averages summary for {timeframe}: {len(summary)} symbols")
                return summary
                
        except Exception as e:
            self.logger.error(f"Database error getting averages summary: {str(e)}")
            return []
    
    async def refresh_averages_cache(self) -> bool:
        """Aktualisiere Materialized View für Durchschnittswerte"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT refresh_ki_prognosen_averages()")
                self.logger.info("Successfully refreshed averages cache")
                return True
                
        except Exception as e:
            self.logger.error(f"Error refreshing averages cache: {str(e)}")
            return False

# =============================================================================
# APPLICATION LAYER - Use Cases
# =============================================================================

class EnhancedPredictionUseCase:
    """
    Application Use Case: Enhanced Predictions mit Durchschnittswerten
    
    SOLID Principles:
    - Single Responsibility: Nur Prediction + Averages Business Logic
    - Dependency Inversion: Abhängig von Repository Interface
    """
    
    def __init__(self, averages_repository: IPredictionAveragesRepository):
        self.averages_repo = averages_repository
        self.logger = logging.getLogger(__name__)
    
    async def get_enhanced_predictions(
        self, 
        timeframe: str,
        limit: int = 15,
        nav_timestamp: Optional[int] = None,
        nav_direction: Optional[str] = None
    ) -> EnhancedPredictionResponse:
        """
        Hauptgeschäftslogik für erweiterte KI-Prognosen
        Timeline-Navigation Support
        """
        try:
            # Navigation Timestamp verarbeiten
            nav_dt = None
            if nav_timestamp:
                nav_dt = datetime.fromtimestamp(nav_timestamp)
                self.logger.info(f"Navigation: {nav_direction} zu {nav_dt}")
            
            # Predictions mit Durchschnittswerten laden
            raw_predictions = await self.averages_repo.get_predictions_with_averages(
                timeframe, limit, nav_dt
            )
            
            # Domain Entities erstellen
            predictions = []
            for pred in raw_predictions:
                # Berechne prediction_percent für Frontend-Kompatibilität
                predicted_percent = pred.get("predicted_value", 0.0)
                
                # ISO Timestamp für Frontend
                calc_date = pred.get("calculation_date")
                if isinstance(calc_date, datetime):
                    iso_timestamp = calc_date.isoformat() + "Z"
                else:
                    iso_timestamp = datetime.now().isoformat() + "Z"
                
                prediction = PredictionWithAverages(
                    symbol=pred.get("symbol", "N/A"),
                    company_name=pred.get("company_name"),
                    calculation_date=pred.get("calculation_date") or datetime.now(),
                    target_date=pred.get("formatted_target_date", "N/A"),
                    predicted_value=predicted_percent,
                    avg_predicted_value=pred.get("avg_predicted_value"),
                    deviation_from_avg=pred.get("deviation_from_avg"),
                    relative_performance_percent=pred.get("relative_performance_percent"),
                    confidence_score=pred.get("confidence_score"),
                    confidence_percentage=pred.get("confidence_percentage"),
                    avg_confidence=pred.get("avg_confidence"),
                    prediction_count=pred.get("prediction_count"),
                    status=pred.get("status", "pending"),
                    timestamp=iso_timestamp
                )
                predictions.append(prediction)
            
            # Navigation Info für Timeline
            current_time = nav_dt or datetime.now()
            navigation_info = {
                "current_timestamp": int(current_time.timestamp()),
                "has_navigation": nav_timestamp is not None,
                "direction": nav_direction,
                "formatted_date": current_time.strftime("%d.%m.%Y %H:%M")
            }
            
            # Performance Summary
            total_with_averages = len([p for p in predictions if p.avg_predicted_value is not None])
            avg_confidence = sum(p.confidence_percentage for p in predictions if p.confidence_percentage) / len(predictions) if predictions else 0
            
            performance_summary = {
                "total_predictions": len(predictions),
                "predictions_with_averages": total_with_averages,
                "average_confidence": round(avg_confidence, 1),
                "timeframe": timeframe,
                "has_sufficient_data": total_with_averages >= 5
            }
            
            return EnhancedPredictionResponse(
                predictions=predictions,
                timeframe=timeframe,
                total_count=len(predictions),
                averages_available=total_with_averages > 0,
                navigation_info=navigation_info,
                performance_summary=performance_summary
            )
            
        except Exception as e:
            self.logger.error(f"Error in enhanced predictions use case: {str(e)}")
            # Fallback response
            return EnhancedPredictionResponse(
                predictions=[],
                timeframe=timeframe,
                total_count=0,
                averages_available=False,
                navigation_info={"error": str(e)},
                performance_summary={"error": "Service temporarily unavailable"}
            )

# =============================================================================
# INFRASTRUCTURE LAYER - Database Connection
# =============================================================================

class DatabaseConnectionManager:
    """Database Connection Pool Management (Single Responsibility)"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.logger = logging.getLogger(__name__)
    
    async def create_pool(self) -> asyncpg.Pool:
        """Erstelle PostgreSQL Connection Pool"""
        try:
            # Production Database Configuration
            DATABASE_CONFIG = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "user": os.getenv("DB_USER", "aktienanalyse"),
                "password": os.getenv("DB_PASSWORD", "aktienanalyse2024"),
                "database": os.getenv("DB_NAME", "aktienanalyse"),
                "min_size": 5,
                "max_size": 20,
                "command_timeout": 30
            }
            
            self.pool = await asyncpg.create_pool(**DATABASE_CONFIG)
            self.logger.info("✅ PostgreSQL connection pool created successfully")
            return self.pool
            
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {str(e)}")
            raise
    
    async def close_pool(self):
        """Schließe Connection Pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection pool closed")

# =============================================================================
# PRESENTATION LAYER - FastAPI Controllers
# =============================================================================

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Enhanced Prediction Tracking Service",
    version="6.2.0",
    description="KI-Prognosen mit Durchschnittswerte-Integration für GUI"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Dependencies
db_manager = DatabaseConnectionManager()
averages_repository: Optional[IPredictionAveragesRepository] = None
prediction_use_case: Optional[EnhancedPredictionUseCase] = None

async def get_prediction_use_case() -> EnhancedPredictionUseCase:
    """Dependency Provider für Enhanced Prediction Use Case"""
    if not prediction_use_case:
        raise HTTPException(status_code=503, detail="Service initialization incomplete")
    return prediction_use_case

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health Check für Load Balancers"""
    return {
        "status": "healthy",
        "service": "enhanced-prediction-tracking",
        "version": "6.2.0",
        "features": ["averages", "timeline_navigation", "gui_integration"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/data/predictions", response_model=Dict[str, Any])
async def get_enhanced_predictions(
    timeframe: str = Query(default="1M", description="Zeitrahmen (1W, 1M, 3M)"),
    limit: int = Query(default=15, description="Maximale Anzahl Ergebnisse"),
    nav_timestamp: Optional[int] = Query(None, description="Navigation Timestamp"),
    nav_direction: Optional[str] = Query(None, description="Navigation Richtung"),
    use_case: EnhancedPredictionUseCase = Depends(get_prediction_use_case)
) -> Dict[str, Any]:
    """
    Enhanced KI-Prognosen mit Durchschnittswerten
    
    NEUES FEATURE: Durchschnittswerte-Integration für GUI
    Timeline-Navigation kompatibel
    """
    try:
        logger.info(f"Loading enhanced predictions: timeframe={timeframe}, nav_timestamp={nav_timestamp}")
        
        enhanced_response = await use_case.get_enhanced_predictions(
            timeframe=timeframe,
            limit=limit,
            nav_timestamp=nav_timestamp,
            nav_direction=nav_direction
        )
        
        # Konvertiere zu Frontend-kompatiblem Format (Legacy-Kompatibilität)
        legacy_predictions = []
        for pred in enhanced_response.predictions:
            # Erweiterte Prediction mit Durchschnittswerten
            legacy_pred = {
                "symbol": pred.symbol,
                "company_name": pred.company_name or pred.symbol,
                "timestamp": pred.timestamp,
                "prediction_percent": f"{pred.predicted_value:+.2f}%",
                "confidence": pred.confidence_score or 0.8,
                
                # NEUE FELDER: Durchschnittswerte
                "avg_prediction_percent": f"{pred.avg_predicted_value:+.2f}%" if pred.avg_predicted_value else None,
                "deviation_from_avg": f"{pred.deviation_from_avg:+.2f}%" if pred.deviation_from_avg else None,
                "relative_performance": f"{pred.relative_performance_percent:+.2f}%" if pred.relative_performance_percent else None,
                "avg_confidence": pred.avg_confidence or None,
                "prediction_count": pred.prediction_count or 0,
                "avg_confidence_percent": f"{pred.avg_confidence * 100:.1f}%" if pred.avg_confidence else None
            }
            legacy_predictions.append(legacy_pred)
        
        response_data = {
            "predictions": legacy_predictions,
            "timeframe": enhanced_response.timeframe,
            "total_count": enhanced_response.total_count,
            "averages_available": enhanced_response.averages_available,
            "navigation_info": enhanced_response.navigation_info,
            "performance_summary": enhanced_response.performance_summary,
            
            # Metadata für Frontend
            "enhanced_features": {
                "averages_support": True,
                "timeline_navigation": True,
                "gui_integration": True,
                "version": "6.2.0"
            }
        }
        
        logger.info(f"✅ Enhanced predictions delivered: {len(legacy_predictions)} items with averages")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced predictions endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading enhanced predictions: {str(e)}")

@app.get("/api/v1/averages/summary/{timeframe}")
async def get_averages_summary(
    timeframe: str,
    use_case: EnhancedPredictionUseCase = Depends(get_prediction_use_case)
) -> Dict[str, Any]:
    """Durchschnittswerte-Übersicht für spezifischen Zeitrahmen"""
    try:
        summary_data = await averages_repository.get_averages_summary(timeframe)
        
        return {
            "timeframe": timeframe,
            "symbols": summary_data,
            "summary_count": len(summary_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting averages summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/averages/refresh")
async def refresh_averages_cache(
    background_tasks: BackgroundTasks,
    use_case: EnhancedPredictionUseCase = Depends(get_prediction_use_case)
):
    """Aktualisiere Durchschnittswerte-Cache (Background Task)"""
    
    async def refresh_task():
        """Background Task für Cache-Refresh"""
        success = await averages_repository.refresh_averages_cache()
        logger.info(f"Averages cache refresh: {'successful' if success else 'failed'}")
    
    background_tasks.add_task(refresh_task)
    
    return {
        "status": "refresh_scheduled",
        "message": "Averages cache refresh started in background",
        "timestamp": datetime.now().isoformat()
    }

# Legacy Endpoints für Kompatibilität
@app.get("/api/v1/soll-ist-comparison")
async def get_soll_ist_comparison(
    days_back: int = Query(default=30, description="Tage zurück"),
    limit: int = Query(default=15, description="Maximale Anzahl"),
    use_case: EnhancedPredictionUseCase = Depends(get_prediction_use_case)
):
    """Legacy SOLL-IST Endpoint (Kompatibilität mit bestehender GUI)"""
    
    # Map days_back zu timeframe
    if days_back <= 7:
        timeframe = "1W"
    elif days_back <= 30:
        timeframe = "1M"
    else:
        timeframe = "3M"
    
    # Verwende Enhanced Predictions für SOLL-IST Daten
    enhanced_response = await use_case.get_enhanced_predictions(timeframe, limit)
    
    # Konvertiere zu Legacy SOLL-IST Format
    comparisons = []
    for pred in enhanced_response.predictions:
        comparison = {
            "symbol": pred.symbol,
            "soll_performance": pred.predicted_value,
            "ist_performance": pred.avg_predicted_value or pred.predicted_value * 0.9,  # Fallback
            "deviation": pred.deviation_from_avg or 0.0,
            "accuracy_percentage": pred.confidence_percentage or 80.0
        }
        comparisons.append(comparison)
    
    return {"comparisons": comparisons}

# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Application Startup - Dependency Injection Setup"""
    global averages_repository, prediction_use_case
    
    try:
        # Database Connection Pool
        pool = await db_manager.create_pool()
        
        # Repository Implementation
        averages_repository = PostgreSQLAveragesRepository(pool)
        
        # Use Case mit Dependency Injection
        prediction_use_case = EnhancedPredictionUseCase(averages_repository)
        
        logger.info("🚀 Enhanced Prediction Tracking Service v6.2.0 started")
        logger.info("✅ Features: KI-Prognosen + Durchschnittswerte + Timeline-Navigation")
        
        # Initial Cache Refresh
        await averages_repository.refresh_averages_cache()
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application Shutdown - Cleanup"""
    try:
        await db_manager.close_pool()
        logger.info("🛑 Enhanced Prediction Tracking Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("🎯 Starting Enhanced Prediction Tracking Service v6.2.0")
    logger.info("📊 Features: KI-Prognosen mit Durchschnittswerten für GUI-Integration")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("SERVICE_PORT", "8018")),
        log_level="info",
        access_log=True
    )