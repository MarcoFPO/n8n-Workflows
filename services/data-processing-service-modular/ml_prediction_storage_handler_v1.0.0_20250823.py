#!/usr/bin/env python3
"""
ML Prediction Storage Handler v1.0.0
Event-Handler für ML-Vorhersage-Speicherung mit Clean Architecture

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Nur Speicherung von ML-Vorhersagen
- Dependency Inversion: Interface-basierte Database und Event-Bus Integration
- Open/Closed: Erweiterbar für neue Speicherungslogiken
- Interface Segregation: Spezifische Handler-Interfaces

Autor: Claude Code
Datum: 23. August 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Import shared modules
from shared.event_bus_v1_0_1_20250822 import EventBusConnection
from shared.ml_prediction_event_types_v1_0_0_20250823 import MLEventType

logger = logging.getLogger(__name__)


class IMLPredictionStorageHandler:
    """Interface für ML-Prediction Storage Handler (Interface Segregation Principle)"""
    
    async def handle_ensemble_prediction_event(self, event_data: Dict[str, Any]) -> bool:
        """Behandelt Ensemble-Vorhersage Events"""
        raise NotImplementedError
    
    async def handle_storage_request_event(self, event_data: Dict[str, Any]) -> bool:
        """Behandelt Speicherungsanfrage Events"""
        raise NotImplementedError
    
    async def store_individual_models(self, symbol: str, individual_predictions: Dict[str, Any], 
                                    ensemble_data: Dict[str, Any]) -> bool:
        """Speichert individuelle Modell-Vorhersagen"""
        raise NotImplementedError


class MLPredictionStorageHandler(IMLPredictionStorageHandler):
    """
    Konkrete Implementierung des ML-Prediction Storage Handlers
    
    SOLID PRINCIPLES:
    - Single Responsibility: Nur ML-Vorhersage-Speicherung
    - Open/Closed: Erweiterbar ohne Änderung bestehender Funktionalität
    - Dependency Inversion: Abhängig von Database Interface
    """
    
    def __init__(self, database_path: str, event_bus: EventBusConnection):
        self.database_path = database_path
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.processed_events = []
        self.error_count = 0
        
        # Initialize database schema
        self._initialize_database_schema()
        
    def _initialize_database_schema(self) -> None:
        """Initialisiert Datenbank-Schema falls erforderlich"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Check if unified_predictions_individual table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='unified_predictions_individual'
                """)
                
                if not cursor.fetchone():
                    # Create table if it doesn't exist
                    self._create_individual_predictions_table(cursor)
                    conn.commit()
                    self.logger.info("Created unified_predictions_individual table")
                
        except Exception as e:
            self.logger.error(f"Error initializing database schema: {str(e)}")
    
    def _create_individual_predictions_table(self, cursor: sqlite3.Cursor) -> None:
        """Erstellt unified_predictions_individual Tabelle"""
        cursor.execute("""
            CREATE TABLE unified_predictions_individual (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT UNIQUE NOT NULL,
                ensemble_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                company_name TEXT NOT NULL,
                
                -- Final Ensemble Prediction
                profit_forecast REAL NOT NULL,
                confidence_level REAL NOT NULL,
                forecast_period_days INTEGER NOT NULL,
                recommendation TEXT NOT NULL,
                trend TEXT NOT NULL,
                target_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                
                -- Source Management
                source_count INTEGER DEFAULT 4,
                source_reliability REAL DEFAULT 0.8,
                calculation_method TEXT DEFAULT 'ensemble',
                primary_source TEXT DEFAULT 'ml-analytics',
                
                -- Risk Assessment
                risk_assessment TEXT DEFAULT 'medium',
                score REAL DEFAULT 0.5,
                
                -- Individual Model Predictions (JSON)
                individual_technical_prediction TEXT DEFAULT NULL,
                individual_sentiment_prediction TEXT DEFAULT NULL,
                individual_fundamental_prediction TEXT DEFAULT NULL,
                individual_meta_prediction TEXT DEFAULT NULL,
                
                -- Ensemble Metadata
                ensemble_weights TEXT DEFAULT NULL,
                ensemble_method TEXT DEFAULT 'weighted_average',
                ensemble_confidence REAL DEFAULT 0.0,
                
                -- IST Values for future SOLL-IST analysis
                actual_profit REAL DEFAULT NULL,
                actual_profit_calculated_at TEXT DEFAULT NULL,
                performance_difference REAL DEFAULT NULL,
                performance_accuracy REAL DEFAULT NULL,
                
                -- Extended Data
                base_metrics TEXT DEFAULT NULL,
                source_contributions TEXT DEFAULT NULL,
                ml_pipeline_data TEXT DEFAULT NULL,
                market_data_details TEXT DEFAULT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_symbol_individual ON unified_predictions_individual(symbol)")
        cursor.execute("CREATE INDEX idx_created_at_individual ON unified_predictions_individual(created_at)")
        cursor.execute("CREATE INDEX idx_target_date_individual ON unified_predictions_individual(target_date)")
        cursor.execute("CREATE INDEX idx_ensemble_id_individual ON unified_predictions_individual(ensemble_id)")
    
    async def handle_ensemble_prediction_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Behandelt Ensemble-Vorhersage Events
        
        Args:
            event_data: Event-Daten mit Ensemble-Vorhersage
            
        Returns:
            bool: True wenn erfolgreich gespeichert
        """
        try:
            data = event_data.get('data', {})
            symbol = data.get('symbol')
            ensemble_id = data.get('ensemble_id')
            individual_predictions = data.get('individual_predictions', {})
            final_prediction = data.get('final_prediction', {})
            
            if not symbol or not ensemble_id:
                self.logger.error("Missing required fields: symbol or ensemble_id")
                return False
            
            # Speichere individuelle Modell-Vorhersagen
            success = await self.store_individual_models(
                symbol=symbol,
                individual_predictions=individual_predictions,
                ensemble_data={
                    'ensemble_id': ensemble_id,
                    'final_prediction': final_prediction,
                    'forecast_period_days': data.get('forecast_period_days', 30),
                    'target_date': data.get('target_date'),
                    'created_at': event_data.get('timestamp')
                }
            )
            
            if success:
                self.processed_events.append(event_data.get('event_id'))
                self.logger.info(f"Processed ensemble prediction for {symbol}")
                
                # Update legacy ki_recommendations table for backward compatibility
                await self._update_legacy_recommendations(symbol, final_prediction, data)
                
            return success
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error handling ensemble prediction event: {str(e)}")
            return False
    
    async def handle_storage_request_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Behandelt Speicherungsanfrage Events
        
        Args:
            event_data: Event-Daten mit Speicherungsanfrage
            
        Returns:
            bool: True wenn erfolgreich gespeichert
        """
        try:
            data = event_data.get('data', {})
            prediction_data = data.get('prediction_data', {})
            
            symbol = prediction_data.get('symbol')
            if not symbol:
                self.logger.error("Missing symbol in storage request")
                return False
            
            # Speichere Vorhersagedaten
            success = await self.store_individual_models(
                symbol=symbol,
                individual_predictions=prediction_data.get('individual_models', {}),
                ensemble_data=prediction_data.get('ensemble_prediction', {})
            )
            
            if success:
                self.processed_events.append(event_data.get('event_id'))
                self.logger.info(f"Processed storage request for {symbol}")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error handling storage request event: {str(e)}")
            return False
    
    async def store_individual_models(self, symbol: str, individual_predictions: Dict[str, Any], 
                                    ensemble_data: Dict[str, Any]) -> bool:
        """
        Speichert individuelle Modell-Vorhersagen in strukturierter Form
        
        Args:
            symbol: Aktien-Symbol
            individual_predictions: Dict mit individuellen Modell-Vorhersagen
            ensemble_data: Ensemble-Daten und Metadata
            
        Returns:
            bool: True wenn erfolgreich gespeichert
        """
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Prepare data
                prediction_id = f"pred_{symbol}_{int(datetime.utcnow().timestamp())}"
                ensemble_id = ensemble_data.get('ensemble_id', f"ens_{symbol}_{int(datetime.utcnow().timestamp())}")
                
                # Extract individual model predictions
                technical_pred = json.dumps(individual_predictions.get('technical', {})) if individual_predictions.get('technical') else None
                sentiment_pred = json.dumps(individual_predictions.get('sentiment', {})) if individual_predictions.get('sentiment') else None
                fundamental_pred = json.dumps(individual_predictions.get('fundamental', {})) if individual_predictions.get('fundamental') else None
                meta_pred = json.dumps(individual_predictions.get('meta', {})) if individual_predictions.get('meta') else None
                
                # Extract final prediction data
                final_pred = ensemble_data.get('final_prediction', {})
                profit_forecast = final_pred.get('profit_forecast', 0.0)
                confidence_level = final_pred.get('confidence_level', 0.5)
                recommendation = final_pred.get('recommendation', 'HOLD')
                risk_assessment = final_pred.get('risk_assessment', 'MODERAT')
                
                # Calculate ensemble weights
                ensemble_weights = json.dumps(final_pred.get('model_weights', {
                    'technical': 0.25, 'sentiment': 0.20, 'fundamental': 0.30, 'meta': 0.25
                }))
                
                # Insert data
                cursor.execute("""
                    INSERT OR REPLACE INTO unified_predictions_individual (
                        prediction_id, ensemble_id, symbol, company_name,
                        profit_forecast, confidence_level, forecast_period_days,
                        recommendation, trend, target_date, created_at,
                        individual_technical_prediction, individual_sentiment_prediction,
                        individual_fundamental_prediction, individual_meta_prediction,
                        ensemble_weights, ensemble_method, risk_assessment, score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction_id, ensemble_id, symbol, f"{symbol} Corporation",
                    profit_forecast, confidence_level, ensemble_data.get('forecast_period_days', 30),
                    recommendation, 'BULLISH' if profit_forecast > 0 else 'BEARISH',
                    ensemble_data.get('target_date', datetime.utcnow().isoformat()),
                    ensemble_data.get('created_at', datetime.utcnow().isoformat()),
                    technical_pred, sentiment_pred, fundamental_pred, meta_pred,
                    ensemble_weights, 'weighted_average', risk_assessment, confidence_level
                ))
                
                conn.commit()
                self.logger.info(f"Stored individual models for {symbol} (ID: {prediction_id})")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing individual models for {symbol}: {str(e)}")
            return False
    
    async def _update_legacy_recommendations(self, symbol: str, final_prediction: Dict[str, Any], 
                                          event_data: Dict[str, Any]) -> bool:
        """
        Aktualisiert Legacy ki_recommendations Tabelle für Backward Compatibility
        
        Args:
            symbol: Aktien-Symbol
            final_prediction: Finale Vorhersagedaten
            event_data: Event-Daten
            
        Returns:
            bool: True wenn erfolgreich
        """
        try:
            legacy_db_path = str(Path(self.database_path).parent / "ki_recommendations.db")
            
            with sqlite3.connect(legacy_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ki_recommendations (
                        symbol, company_name, score, profit_forecast, 
                        forecast_period_days, recommendation, created_at,
                        confidence_level, trend, target_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, f"{symbol} Corporation",
                    final_prediction.get('confidence_level', 0.5) * 10,  # Scale to 0-10
                    final_prediction.get('profit_forecast', 0.0),
                    event_data.get('forecast_period_days', 30),
                    final_prediction.get('recommendation', 'HOLD'),
                    datetime.utcnow().isoformat(),
                    final_prediction.get('confidence_level', 0.5),
                    'BULLISH' if final_prediction.get('profit_forecast', 0) > 0 else 'BEARISH',
                    event_data.get('target_date', datetime.utcnow().isoformat())
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.warning(f"Error updating legacy recommendations: {str(e)}")
            return False
    
    def get_handler_stats(self) -> Dict[str, Any]:
        """
        Gibt Handler-Statistiken zurück
        
        Returns:
            Dict mit Statistiken
        """
        return {
            "processed_events_count": len(self.processed_events),
            "error_count": self.error_count,
            "last_processed": self.processed_events[-1] if self.processed_events else None,
            "handler_health": "healthy" if self.error_count == 0 else "degraded"
        }


class MLPredictionEventListener:
    """Event-Listener für ML-Prediction Events"""
    
    def __init__(self, storage_handler: IMLPredictionStorageHandler, event_bus: EventBusConnection):
        self.storage_handler = storage_handler
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.running = False
    
    async def start_listening(self) -> None:
        """Startet Event-Listening für ML-Prediction Events"""
        try:
            self.running = True
            self.logger.info("Started listening for ML prediction events")
            
            # Subscribe to ML prediction events
            await self.event_bus.subscribe(
                event_type=MLEventType.ML_ENSEMBLE_PREDICTION_COMPLETED.value,
                callback=self._handle_ensemble_prediction
            )
            
            await self.event_bus.subscribe(
                event_type=MLEventType.ML_PREDICTION_STORAGE_REQUESTED.value,
                callback=self._handle_storage_request
            )
            
            # Keep listening
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in event listening: {str(e)}")
    
    async def stop_listening(self) -> None:
        """Stoppt Event-Listening"""
        self.running = False
        self.logger.info("Stopped listening for ML prediction events")
    
    async def _handle_ensemble_prediction(self, event_data: Dict[str, Any]) -> None:
        """Callback für Ensemble-Prediction Events"""
        await self.storage_handler.handle_ensemble_prediction_event(event_data)
    
    async def _handle_storage_request(self, event_data: Dict[str, Any]) -> None:
        """Callback für Storage-Request Events"""
        await self.storage_handler.handle_storage_request_event(event_data)


# Factory für Storage Handler
class MLPredictionStorageHandlerFactory:
    """Factory für ML-Prediction Storage Handler"""
    
    @staticmethod
    def create_handler(database_path: str, event_bus: EventBusConnection) -> IMLPredictionStorageHandler:
        """
        Erstellt ML-Prediction Storage Handler
        
        Args:
            database_path: Pfad zur Datenbank
            event_bus: Event-Bus Connection
            
        Returns:
            IMLPredictionStorageHandler: Handler-Instance
        """
        return MLPredictionStorageHandler(database_path, event_bus)