#!/usr/bin/env python3
"""
Enhanced Data Processing Service v4.3.0 - Mit 4-Modell-Integration
CSV-Middleware mit Individual-Model-Unterstützung und Clean Architecture

NEUE FEATURES v4.3.0:
- Integration mit ML Analytics Service für 4-Modell-Vorhersagen
- Strukturierte Anzeige individueller Modell-Ergebnisse
- Event-Bus Integration für Real-time ML-Prediction Updates
- Clean Architecture mit SOLID Principles

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Data Processing und CSV-Middleware
- Open/Closed: Erweiterbar für neue Datenquellen und Formate
- Dependency Inversion: Interface-basierte Event-Bus Integration
- Interface Segregation: Spezifische Service-Interfaces

Autor: Claude Code
Datum: 23. August 2025
Version: 4.3.0
"""

import sqlite3
import csv
import io
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, Response, HTTPException, Query
from typing import List, Dict, Any, Optional
import sys
import json

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Import shared modules  
from shared.event_bus_v1_0_1_20250822 import EventBusConnection
from shared.ml_prediction_event_types_v1_0_0_20250823 import MLEventType
from ml_prediction_storage_handler_v1_0_0_20250823 import (
    MLPredictionStorageHandlerFactory, 
    MLPredictionEventListener
)

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enhanced Data Processing Service v4.3.0", version="4.3.0")

# Konfiguration
KI_RECOMMENDATIONS_DB = Path("/opt/aktienanalyse-ökosystem/data/ki_recommendations.db")
UNIFIED_PREDICTIONS_DB = Path("/opt/aktienanalyse-ökosystem/data/unified_profit_engine.db")

# Zeitraum-Konfiguration (erweitert)
TIMEFRAME_CONFIG = {
    "1W": {"days": 7, "name": "1 Woche", "filter_logic": "current_predictions_for_timeframe"},
    "1M": {"days": 30, "name": "1 Monat", "filter_logic": "current_predictions_for_timeframe"},
    "3M": {"days": 90, "name": "3 Monate", "filter_logic": "current_predictions_for_timeframe"},
    "6M": {"days": 180, "name": "6 Monate", "filter_logic": "current_predictions_for_timeframe"},
    "1Y": {"days": 365, "name": "1 Jahr", "filter_logic": "current_predictions_for_timeframe"}
}

# Global variables für Event-Bus Integration
event_bus_connection = None
storage_handler = None
event_listener = None


class IDataProcessingService:
    """Interface für Data Processing Service (Interface Segregation Principle)"""
    
    async def get_predictions_for_timeframe(self, timeframe: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Lädt Vorhersagen für Zeitraum"""
        raise NotImplementedError
    
    async def get_individual_model_predictions(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Lädt individuelle Modell-Vorhersagen"""
        raise NotImplementedError
    
    async def generate_csv_for_timeframe(self, timeframe: str, include_individual_models: bool = False) -> str:
        """Generiert CSV für Zeitraum"""
        raise NotImplementedError


class EnhancedDataProcessingService(IDataProcessingService):
    """
    Enhanced Data Processing Service mit 4-Modell-Integration
    
    SOLID PRINCIPLES:
    - Single Responsibility: Data Processing und CSV-Generation
    - Open/Closed: Erweiterbar ohne Änderung bestehender Funktionalität
    - Dependency Inversion: Abhängig von Database und Event-Bus Interfaces
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    async def get_predictions_for_timeframe(self, timeframe: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Lädt AKTUELLE Vorhersagen die FÜR den gewünschten Zeitraum relevant sind
        Priorisiert unified_predictions_individual wenn verfügbar
        """
        try:
            config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1M"])
            target_days = config["days"]
            
            # Versuche zuerst unified_predictions_individual (neue 4-Modell-Daten)
            individual_predictions = await self._get_individual_model_predictions(timeframe, limit)
            if individual_predictions:
                self.logger.info(f"Using individual model predictions for {timeframe}")
                return individual_predictions
            
            # Fallback auf legacy ki_recommendations
            return await self._get_legacy_predictions(timeframe, limit)
            
        except Exception as e:
            self.logger.error(f"Failed to load predictions for timeframe {timeframe}: {e}")
            return []
    
    async def _get_individual_model_predictions(self, timeframe: str, limit: int) -> List[Dict[str, Any]]:
        """Lädt Vorhersagen aus unified_predictions_individual Tabelle"""
        try:
            config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1M"])
            target_days = config["days"]
            
            if not UNIFIED_PREDICTIONS_DB.exists():
                return []
            
            with sqlite3.connect(UNIFIED_PREDICTIONS_DB) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Check if unified_predictions_individual table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='unified_predictions_individual'
                """)
                
                if not cursor.fetchone():
                    return []
                
                # Query individual model predictions
                query = """
                SELECT 
                    symbol,
                    company_name,
                    profit_forecast,
                    confidence_level,
                    forecast_period_days,
                    recommendation,
                    risk_assessment,
                    created_at,
                    target_date,
                    individual_technical_prediction,
                    individual_sentiment_prediction,
                    individual_fundamental_prediction,
                    individual_meta_prediction,
                    ensemble_weights
                FROM unified_predictions_individual 
                WHERE forecast_period_days >= ? OR forecast_period_days <= ?
                ORDER BY 
                    CASE 
                        WHEN forecast_period_days <= ? THEN 0 
                        ELSE 1 
                    END,
                    profit_forecast DESC, 
                    ABS(forecast_period_days - ?) ASC,
                    created_at DESC
                LIMIT ?
                """
                
                cursor.execute(query, (1, target_days * 2, target_days, target_days, limit))
                rows = cursor.fetchall()
                
                predictions = []
                for row in rows:
                    # Parse individual model predictions
                    individual_models = {}
                    for model_type in ['technical', 'sentiment', 'fundamental', 'meta']:
                        prediction_json = row[f"individual_{model_type}_prediction"]
                        if prediction_json:
                            try:
                                individual_models[model_type] = json.loads(prediction_json)
                            except json.JSONDecodeError:
                                individual_models[model_type] = None
                    
                    # Parse ensemble weights
                    ensemble_weights = {}
                    if row["ensemble_weights"]:
                        try:
                            ensemble_weights = json.loads(row["ensemble_weights"])
                        except json.JSONDecodeError:
                            ensemble_weights = {}
                    
                    # Zeitraum-spezifische Gewinn-Anpassung
                    base_profit = float(row["profit_forecast"]) if row["profit_forecast"] else 0.0
                    forecast_days = int(row["forecast_period_days"]) if row["forecast_period_days"] else 30
                    
                    if forecast_days > 0:
                        timeframe_profit = base_profit * (target_days / forecast_days)
                    else:
                        timeframe_profit = base_profit
                    
                    predictions.append({
                        "symbol": row["symbol"],
                        "company_name": row["company_name"], 
                        "score": float(row["confidence_level"]) * 10 if row["confidence_level"] else 0.0,
                        "predicted_profit": timeframe_profit,
                        "original_forecast_days": forecast_days,
                        "target_timeframe_days": target_days,
                        "recommendation": row["recommendation"] or "HOLD",
                        "risk_assessment": row["risk_assessment"] or "MODERAT",
                        "reasoning": f"4-Modell-Ensemble für {config['name']}: {row['recommendation']} (Konfidenz: {row['confidence_level']:.1%})",
                        "timestamp": row["created_at"],
                        "confidence": float(row["confidence_level"]) if row["confidence_level"] else 0.0,
                        "timeframe": timeframe,
                        "individual_models": individual_models,
                        "ensemble_weights": ensemble_weights,
                        "data_source": "4-model-ensemble"
                    })
                
                self.logger.info(f"Loaded {len(predictions)} individual model predictions for {timeframe}")
                return predictions
                
        except Exception as e:
            self.logger.error(f"Error loading individual model predictions: {e}")
            return []
    
    async def _get_legacy_predictions(self, timeframe: str, limit: int) -> List[Dict[str, Any]]:
        """Lädt Vorhersagen aus legacy ki_recommendations Tabelle"""
        try:
            config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1M"])
            target_days = config["days"]
            
            with sqlite3.connect(KI_RECOMMENDATIONS_DB) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    symbol,
                    company_name,
                    score,
                    profit_forecast,
                    forecast_period_days,
                    recommendation,
                    created_at,
                    confidence_level,
                    trend,
                    target_date
                FROM ki_recommendations 
                WHERE forecast_period_days >= ? OR forecast_period_days <= ?
                ORDER BY 
                    CASE 
                        WHEN forecast_period_days <= ? THEN 0 
                        ELSE 1 
                    END,
                    profit_forecast DESC, 
                    ABS(forecast_period_days - ?) ASC,
                    created_at DESC
                LIMIT ?
                """
                
                cursor.execute(query, (1, target_days * 2, target_days, target_days, limit))
                rows = cursor.fetchall()
                
                predictions = []
                for row in rows:
                    # Zeitraum-spezifische Gewinn-Anpassung
                    base_profit = float(row["profit_forecast"]) if row["profit_forecast"] else 0.0
                    forecast_days = int(row["forecast_period_days"]) if row["forecast_period_days"] else 30
                    
                    if forecast_days > 0:
                        timeframe_profit = base_profit * (target_days / forecast_days)
                    else:
                        timeframe_profit = base_profit
                    
                    predictions.append({
                        "symbol": row["symbol"],
                        "company_name": row["company_name"], 
                        "score": float(row["score"]) if row["score"] else 0.0,
                        "predicted_profit": timeframe_profit,
                        "original_forecast_days": forecast_days,
                        "target_timeframe_days": target_days,
                        "recommendation": row["recommendation"] or "HOLD",
                        "reasoning": f"Legacy-Prognose für {config['name']}: {row['trend']} Trend (orig. {forecast_days}d)",
                        "timestamp": row["created_at"],
                        "confidence": float(row["confidence_level"]) if row["confidence_level"] else 0.0,
                        "timeframe": timeframe,
                        "individual_models": {},  # Empty for legacy data
                        "ensemble_weights": {},   # Empty for legacy data
                        "data_source": "legacy"
                    })
                
                self.logger.info(f"Loaded {len(predictions)} legacy predictions for {timeframe}")
                return predictions
                
        except Exception as e:
            self.logger.error(f"Error loading legacy predictions: {e}")
            return []
    
    async def get_individual_model_predictions(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Lädt individuelle Modell-Vorhersagen für ein spezifisches Symbol
        
        Args:
            symbol: Aktien-Symbol
            timeframe: Zeitrahmen (1W, 1M, etc.)
            
        Returns:
            Dict mit individuellen Modell-Vorhersagen
        """
        try:
            if not UNIFIED_PREDICTIONS_DB.exists():
                return {}
            
            with sqlite3.connect(UNIFIED_PREDICTIONS_DB) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        individual_technical_prediction,
                        individual_sentiment_prediction,
                        individual_fundamental_prediction,
                        individual_meta_prediction,
                        ensemble_weights,
                        profit_forecast,
                        confidence_level
                    FROM unified_predictions_individual 
                    WHERE symbol = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (symbol,))
                
                row = cursor.fetchone()
                if not row:
                    return {}
                
                # Parse individual predictions
                individual_models = {}
                for model_type in ['technical', 'sentiment', 'fundamental', 'meta']:
                    prediction_json = row[f"individual_{model_type}_prediction"]
                    if prediction_json:
                        try:
                            individual_models[model_type] = json.loads(prediction_json)
                        except json.JSONDecodeError:
                            individual_models[model_type] = None
                
                # Parse ensemble weights
                ensemble_weights = {}
                if row["ensemble_weights"]:
                    try:
                        ensemble_weights = json.loads(row["ensemble_weights"])
                    except json.JSONDecodeError:
                        ensemble_weights = {}
                
                return {
                    "symbol": symbol,
                    "individual_models": individual_models,
                    "ensemble_weights": ensemble_weights,
                    "final_prediction": {
                        "profit_forecast": row["profit_forecast"],
                        "confidence_level": row["confidence_level"]
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error loading individual predictions for {symbol}: {e}")
            return {}
    
    async def generate_csv_for_timeframe(self, timeframe: str, include_individual_models: bool = False) -> str:
        """
        Generiert zeitraum-spezifischen CSV-Content mit optionalen individuellen Modellen
        
        Args:
            timeframe: Zeitrahmen (1W, 1M, etc.)
            include_individual_models: Ob individuelle Modell-Vorhersagen einbezogen werden sollen
            
        Returns:
            CSV-Content als String
        """
        try:
            config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1M"])
            predictions = await self.get_predictions_for_timeframe(timeframe, 15)
            
            if not predictions:
                self.logger.warning(f"No predictions found for timeframe {timeframe}")
                return f"Symbol,Company,Vorhergesagter_Gewinn,Risiko\nNo data available for {config['name']},,,"
            
            # CSV-Daten erstellen
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header - erweitert für individuelle Modelle wenn gewünscht
            if include_individual_models and any(pred.get('individual_models') for pred in predictions):
                writer.writerow([
                    "Symbol", "Company", "Vorhergesagter_Gewinn", "Risiko", 
                    "Technical_Model", "Sentiment_Model", "Fundamental_Model", "Meta_Model",
                    "Ensemble_Weights", "Data_Source"
                ])
            else:
                writer.writerow([
                    "Symbol", "Company", "Vorhergesagter_Gewinn", "Risiko"
                ])
            
            # Daten-Zeilen
            for pred in predictions:
                # Risiko basierend auf Recommendation und Score bestimmen
                score = float(pred.get('score', 0)) if pred.get('score') else 0.0
                recommendation = pred.get('recommendation', 'HOLD')
                
                # Verwende risk_assessment wenn verfügbar (neue Daten), sonst calculate (legacy)
                if pred.get('risk_assessment'):
                    risk_level = pred['risk_assessment']
                else:
                    if score >= 8.0 and recommendation in ['STRONG_BUY', 'BUY']:
                        risk_level = "NIEDRIG"
                    elif score >= 6.0 and recommendation in ['BUY', 'HOLD']:
                        risk_level = "MODERAT"
                    elif score >= 4.0:
                        risk_level = "HOCH"
                    else:
                        risk_level = "SEHR_HOCH"
                
                base_row = [
                    pred["symbol"],
                    pred["company_name"],
                    f"{pred['predicted_profit']:.1f}%",
                    risk_level
                ]
                
                # Erweiterte Daten für individuelle Modelle
                if include_individual_models and any(pred.get('individual_models') for pred in predictions):
                    individual_models = pred.get('individual_models', {})
                    
                    # Extrahiere Vorhersagewerte der einzelnen Modelle
                    technical_value = "N/A"
                    if individual_models.get('technical') and individual_models['technical'].get('prediction_values'):
                        technical_value = f"{individual_models['technical']['prediction_values'][0]:.1f}%"
                    
                    sentiment_value = "N/A"
                    if individual_models.get('sentiment') and individual_models['sentiment'].get('prediction_values'):
                        sentiment_value = f"{individual_models['sentiment']['prediction_values'][0]:.1f}%"
                    
                    fundamental_value = "N/A"
                    if individual_models.get('fundamental') and individual_models['fundamental'].get('prediction_values'):
                        fundamental_value = f"{individual_models['fundamental']['prediction_values'][0]:.1f}%"
                    
                    meta_value = "N/A"
                    if individual_models.get('meta') and individual_models['meta'].get('prediction_values'):
                        meta_value = f"{individual_models['meta']['prediction_values'][0]:.1f}%"
                    
                    # Ensemble-Gewichte
                    weights = pred.get('ensemble_weights', {})
                    weights_str = f"T:{weights.get('technical', 0):.2f},S:{weights.get('sentiment', 0):.2f},F:{weights.get('fundamental', 0):.2f},M:{weights.get('meta', 0):.2f}"
                    
                    extended_row = base_row + [
                        technical_value, sentiment_value, fundamental_value, meta_value,
                        weights_str, pred.get('data_source', 'unknown')
                    ]
                    writer.writerow(extended_row)
                else:
                    writer.writerow(base_row)
            
            csv_content = output.getvalue()
            self.logger.info(f"Generated {timeframe} CSV: {len(predictions)} predictions (individual_models: {include_individual_models})")
            return csv_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate CSV for timeframe {timeframe}: {e}")
            return f"Symbol,Company,Vorhergesagter_Gewinn,Risiko\nError loading {timeframe} data,,,"


# Global service instance
data_service = EnhancedDataProcessingService()


@app.on_event("startup")
async def startup_event():
    """Initialisierung beim Service-Start"""
    global event_bus_connection, storage_handler, event_listener
    
    try:
        # Event-Bus Connection initialisieren
        from shared.redis_event_bus_v1_1_0_20250822 import RedisEventBus
        event_bus_connection = RedisEventBus()
        
        # Storage Handler initialisieren
        storage_handler = MLPredictionStorageHandlerFactory.create_handler(
            database_path=str(UNIFIED_PREDICTIONS_DB),
            event_bus=event_bus_connection
        )
        
        # Event Listener starten
        event_listener = MLPredictionEventListener(storage_handler, event_bus_connection)
        asyncio.create_task(event_listener.start_listening())
        
        logger.info("Enhanced Data Processing Service v4.3.0 started with 4-model integration")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")


@app.get("/health")
async def health():
    """Health Check mit 4-Modell-Status"""
    return {
        "status": "healthy",
        "service": "enhanced-data-processing-4-model-integration", 
        "version": "4.3.0",
        "db_file": str(KI_RECOMMENDATIONS_DB),
        "unified_db_file": str(UNIFIED_PREDICTIONS_DB),
        "db_exists": KI_RECOMMENDATIONS_DB.exists(),
        "unified_db_exists": UNIFIED_PREDICTIONS_DB.exists(),
        "supported_timeframes": list(TIMEFRAME_CONFIG.keys()),
        "features": {
            "individual_models": True,
            "ensemble_predictions": True,
            "event_bus_integration": event_bus_connection is not None,
            "4_model_support": ["technical", "sentiment", "fundamental", "meta"]
        },
        "logic": "4_model_ensemble_with_fallback"
    }


@app.get("/api/v1/data/predictions")
async def get_predictions_by_timeframe(timeframe: str = Query(default="1M", description="Zeitraum: 1W, 1M, 3M, 6M, 1Y")):
    """Aktuelle Prognosen für Ziel-Zeitraum als CSV"""
    try:
        if timeframe not in TIMEFRAME_CONFIG:
            raise HTTPException(status_code=400, detail=f"Ungültiger Zeitraum: {timeframe}")
        
        csv_content = await data_service.generate_csv_for_timeframe(timeframe, include_individual_models=False)
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=predictions_{timeframe.lower()}.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating predictions for timeframe {timeframe}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/data/predictions-with-models")
async def get_predictions_with_individual_models(timeframe: str = Query(default="1M", description="Zeitraum: 1W, 1M, 3M, 6M, 1Y")):
    """Prognosen mit individuellen 4-Modell-Details als CSV"""
    try:
        if timeframe not in TIMEFRAME_CONFIG:
            raise HTTPException(status_code=400, detail=f"Ungültiger Zeitraum: {timeframe}")
        
        csv_content = await data_service.generate_csv_for_timeframe(timeframe, include_individual_models=True)
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=predictions_with_models_{timeframe.lower()}.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating predictions with models for timeframe {timeframe}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/data/individual-models/{symbol}")
async def get_individual_model_predictions_for_symbol(symbol: str, timeframe: str = Query(default="1M")):
    """Individuelle Modell-Vorhersagen für ein spezifisches Symbol"""
    try:
        predictions = await data_service.get_individual_model_predictions(symbol, timeframe)
        
        if not predictions:
            raise HTTPException(status_code=404, detail=f"No predictions found for symbol {symbol}")
        
        return predictions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting individual predictions for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Legacy endpoint für Backward Compatibility
@app.get("/api/v1/data/top15-predictions")
async def get_top15_predictions_legacy():
    """Legacy: Top 15 Vorhersagen (backward compatibility)"""
    return await get_predictions_by_timeframe("1M")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)