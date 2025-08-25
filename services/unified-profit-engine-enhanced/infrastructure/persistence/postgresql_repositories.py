#!/usr/bin/env python3
"""
Infrastructure Layer - PostgreSQL Repository Implementations
Unified Profit Engine Enhanced v6.0 - Clean Architecture

INFRASTRUCTURE RESPONSIBILITIES:
- Concrete Repository Implementations
- Database-specific Logic
- Data Mapping zwischen Domain und Database
- Performance Optimization

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist
Datum: 24. August 2025
"""

import asyncpg
import json
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging

from ...domain.entities import (
    ProfitPrediction,
    SOLLISTTracking, 
    MarketSymbol,
    PredictionHorizon,
    ProfitForecast
)
from ...domain.repositories import (
    ProfitPredictionRepository,
    SOLLISTTrackingRepository,
    MarketDataRepository,
    MarketData,
    PerformanceMetrics
)


logger = logging.getLogger(__name__)


class PostgreSQLProfitPredictionRepository(ProfitPredictionRepository):
    """PostgreSQL Implementation für Profit Predictions"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
    
    async def save(self, prediction: ProfitPrediction) -> None:
        """Speichert Profit Prediction mit JSON-Serialisierung für Forecasts"""
        try:
            # Forecasts zu JSON konvertieren für Speicherung
            forecasts_json = {}
            for horizon, forecast in prediction.forecasts.items():
                forecasts_json[horizon.value] = {
                    "amount": str(forecast.amount),
                    "confidence": forecast.confidence,
                    "horizon": horizon.value
                }
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO profit_predictions 
                    (id, symbol, company_name, market_region, target_date, 
                     forecasts_json, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) 
                    DO UPDATE SET
                        forecasts_json = EXCLUDED.forecasts_json,
                        updated_at = EXCLUDED.updated_at
                """, 
                prediction.id,
                prediction.symbol.symbol,
                prediction.symbol.company_name,
                prediction.symbol.market_region,
                prediction.target_date,
                json.dumps(forecasts_json),
                prediction.created_at,
                prediction.updated_at)
                
                logger.info(f"Saved prediction {prediction.id} for {prediction.symbol.symbol}")
                
        except Exception as e:
            logger.error(f"Failed to save prediction {prediction.id}: {e}")
            raise
    
    async def get_by_id(self, prediction_id: str) -> Optional[ProfitPrediction]:
        """Lädt Prediction by ID mit JSON-Deserialisierung"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, symbol, company_name, market_region, target_date,
                           forecasts_json, created_at, updated_at
                    FROM profit_predictions 
                    WHERE id = $1
                """, prediction_id)
                
                if not row:
                    return None
                
                return self._row_to_prediction(row)
                
        except Exception as e:
            logger.error(f"Failed to load prediction {prediction_id}: {e}")
            raise
    
    async def get_by_symbol(self, symbol: str) -> List[ProfitPrediction]:
        """Lädt alle Predictions für Symbol"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, symbol, company_name, market_region, target_date,
                           forecasts_json, created_at, updated_at
                    FROM profit_predictions 
                    WHERE symbol = $1
                    ORDER BY created_at DESC
                """, symbol)
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to load predictions for symbol {symbol}: {e}")
            raise
    
    async def get_by_date_range(self, start_date: date, end_date: date) -> List[ProfitPrediction]:
        """Lädt Predictions in Datumsbereich"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, symbol, company_name, market_region, target_date,
                           forecasts_json, created_at, updated_at
                    FROM profit_predictions 
                    WHERE target_date BETWEEN $1 AND $2
                    ORDER BY target_date DESC
                """, start_date, end_date)
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to load predictions for date range {start_date}-{end_date}: {e}")
            raise
    
    async def update(self, prediction: ProfitPrediction) -> None:
        """Aktualisiert bestehende Prediction (verwendet save mit UPSERT)"""
        await self.save(prediction)
    
    async def delete(self, prediction_id: str) -> bool:
        """Löscht Prediction"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM profit_predictions WHERE id = $1
                """, prediction_id)
                
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"Deleted prediction {prediction_id}")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete prediction {prediction_id}: {e}")
            raise
    
    def _row_to_prediction(self, row) -> ProfitPrediction:
        """Konvertiert Database Row zu Domain Entity"""
        # JSON zu Forecasts konvertieren
        forecasts_data = json.loads(row['forecasts_json'])
        forecasts = {}
        
        for horizon_str, forecast_data in forecasts_data.items():
            horizon = PredictionHorizon(horizon_str)
            forecast = ProfitForecast(
                amount=Decimal(forecast_data['amount']),
                confidence=forecast_data['confidence'],
                horizon=horizon
            )
            forecasts[horizon] = forecast
        
        # MarketSymbol erstellen
        symbol = MarketSymbol(
            symbol=row['symbol'],
            company_name=row['company_name'],
            market_region=row['market_region']
        )
        
        # Domain Entity erstellen
        prediction = ProfitPrediction(
            symbol=symbol,
            target_date=row['target_date'],
            forecasts=forecasts
        )
        
        # IDs und Timestamps setzen
        prediction.id = row['id']
        prediction.created_at = row['created_at']
        prediction.updated_at = row['updated_at']
        
        return prediction


class PostgreSQLSOLLISTTrackingRepository(SOLLISTTrackingRepository):
    """PostgreSQL Implementation für SOLL-IST Tracking"""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
    
    async def save(self, tracking: SOLLISTTracking) -> None:
        """Speichert SOLL-IST Tracking mit UPSERT Logic"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO soll_ist_gewinn_tracking 
                    (id, datum, symbol, unternehmen, market_region, ist_gewinn,
                     soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
                     created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (datum, symbol) 
                    DO UPDATE SET
                        unternehmen = EXCLUDED.unternehmen,
                        market_region = EXCLUDED.market_region,
                        ist_gewinn = EXCLUDED.ist_gewinn,
                        soll_gewinn_1w = EXCLUDED.soll_gewinn_1w,
                        soll_gewinn_1m = EXCLUDED.soll_gewinn_1m,
                        soll_gewinn_3m = EXCLUDED.soll_gewinn_3m,
                        soll_gewinn_12m = EXCLUDED.soll_gewinn_12m,
                        updated_at = EXCLUDED.updated_at
                """,
                tracking.id,
                tracking.datum,
                tracking.symbol.symbol,
                tracking.symbol.company_name,
                tracking.symbol.market_region,
                tracking.ist_gewinn,
                tracking.get_soll_gewinn(PredictionHorizon.ONE_WEEK),
                tracking.get_soll_gewinn(PredictionHorizon.ONE_MONTH),
                tracking.get_soll_gewinn(PredictionHorizon.THREE_MONTHS),
                tracking.get_soll_gewinn(PredictionHorizon.TWELVE_MONTHS),
                tracking.created_at,
                tracking.updated_at)
                
                logger.info(f"Saved SOLL-IST tracking for {tracking.symbol.symbol} on {tracking.datum}")
                
        except Exception as e:
            logger.error(f"Failed to save SOLL-IST tracking: {e}")
            raise
    
    async def get_by_symbol_and_date(self, symbol: str, datum: date) -> Optional[SOLLISTTracking]:
        """Lädt Tracking für Symbol und Datum"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, datum, symbol, unternehmen, market_region, ist_gewinn,
                           soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
                           created_at, updated_at
                    FROM soll_ist_gewinn_tracking
                    WHERE symbol = $1 AND datum = $2
                """, symbol, datum)
                
                if not row:
                    return None
                
                return self._row_to_tracking(row)
                
        except Exception as e:
            logger.error(f"Failed to load tracking for {symbol} on {datum}: {e}")
            raise
    
    async def get_by_symbol(self, symbol: str) -> List[SOLLISTTracking]:
        """Lädt alle Tracking-Einträge für Symbol"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, datum, symbol, unternehmen, market_region, ist_gewinn,
                           soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
                           created_at, updated_at
                    FROM soll_ist_gewinn_tracking
                    WHERE symbol = $1
                    ORDER BY datum DESC
                """, symbol)
                
                return [self._row_to_tracking(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to load tracking for symbol {symbol}: {e}")
            raise
    
    async def get_by_date_range(self, start_date: date, end_date: date) -> List[SOLLISTTracking]:
        """Lädt Tracking-Einträge in Datumsbereich"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, datum, symbol, unternehmen, market_region, ist_gewinn,
                           soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
                           created_at, updated_at
                    FROM soll_ist_gewinn_tracking
                    WHERE datum BETWEEN $1 AND $2
                    ORDER BY datum DESC
                """, start_date, end_date)
                
                return [self._row_to_tracking(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to load tracking for date range {start_date}-{end_date}: {e}")
            raise
    
    async def get_performance_analysis(self, 
                                     symbol: Optional[str] = None,
                                     horizon: Optional[PredictionHorizon] = None) -> List[Dict[str, Any]]:
        """Lädt Performance-Analyse Daten mit berechneten Metriken"""
        try:
            base_query = """
                SELECT 
                    symbol, unternehmen, market_region, datum, ist_gewinn,
                    soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
                    
                    -- Performance Differences (IST - SOLL)
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_1w IS NOT NULL 
                         THEN ist_gewinn - soll_gewinn_1w END as diff_1w,
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_1m IS NOT NULL 
                         THEN ist_gewinn - soll_gewinn_1m END as diff_1m,
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_3m IS NOT NULL 
                         THEN ist_gewinn - soll_gewinn_3m END as diff_3m,
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_12m IS NOT NULL 
                         THEN ist_gewinn - soll_gewinn_12m END as diff_12m,
                    
                    -- Accuracy Percentages
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_1w IS NOT NULL AND soll_gewinn_1w != 0
                         THEN 1 - (ABS(ist_gewinn - soll_gewinn_1w) / ABS(soll_gewinn_1w)) END as accuracy_1w,
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_1m IS NOT NULL AND soll_gewinn_1m != 0
                         THEN 1 - (ABS(ist_gewinn - soll_gewinn_1m) / ABS(soll_gewinn_1m)) END as accuracy_1m,
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_3m IS NOT NULL AND soll_gewinn_3m != 0
                         THEN 1 - (ABS(ist_gewinn - soll_gewinn_3m) / ABS(soll_gewinn_3m)) END as accuracy_3m,
                    CASE WHEN ist_gewinn IS NOT NULL AND soll_gewinn_12m IS NOT NULL AND soll_gewinn_12m != 0
                         THEN 1 - (ABS(ist_gewinn - soll_gewinn_12m) / ABS(soll_gewinn_12m)) END as accuracy_12m
                
                FROM soll_ist_gewinn_tracking
                WHERE ist_gewinn IS NOT NULL
            """
            
            params = []
            conditions = []
            
            if symbol:
                conditions.append(f"AND symbol = ${len(params) + 1}")
                params.append(symbol)
            
            query = base_query + " " + " ".join(conditions) + " ORDER BY datum DESC"
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                # Zu Dict konvertieren für einfache Bearbeitung
                results = []
                for row in rows:
                    row_dict = dict(row)
                    
                    # Best/Worst Horizon berechnen
                    accuracies = {
                        "1W": row_dict.get('accuracy_1w'),
                        "1M": row_dict.get('accuracy_1m'), 
                        "3M": row_dict.get('accuracy_3m'),
                        "12M": row_dict.get('accuracy_12m')
                    }
                    
                    # Nur non-None Accuracies betrachten
                    valid_accuracies = {k: v for k, v in accuracies.items() if v is not None}
                    
                    if valid_accuracies:
                        row_dict['best_horizon'] = max(valid_accuracies, key=valid_accuracies.get)
                        row_dict['worst_horizon'] = min(valid_accuracies, key=valid_accuracies.get)
                        row_dict['overall_accuracy'] = sum(valid_accuracies.values()) / len(valid_accuracies)
                    else:
                        row_dict['best_horizon'] = None
                        row_dict['worst_horizon'] = None
                        row_dict['overall_accuracy'] = None
                    
                    results.append(row_dict)
                
                logger.info(f"Loaded {len(results)} performance analysis records")
                return results
                
        except Exception as e:
            logger.error(f"Failed to load performance analysis: {e}")
            raise
    
    async def update(self, tracking: SOLLISTTracking) -> None:
        """Aktualisiert bestehende Tracking-Einträge (verwendet save mit UPSERT)"""
        await self.save(tracking)
    
    async def delete(self, tracking_id: str) -> bool:
        """Löscht Tracking-Eintrag"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM soll_ist_gewinn_tracking WHERE id = $1
                """, tracking_id)
                
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"Deleted SOLL-IST tracking {tracking_id}")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete tracking {tracking_id}: {e}")
            raise
    
    def _row_to_tracking(self, row) -> SOLLISTTracking:
        """Konvertiert Database Row zu Domain Entity"""
        # MarketSymbol erstellen
        symbol = MarketSymbol(
            symbol=row['symbol'],
            company_name=row['unternehmen'],
            market_region=row['market_region']
        )
        
        # Domain Entity erstellen
        tracking = SOLLISTTracking(
            datum=row['datum'],
            symbol=symbol
        )
        
        # IDs und Timestamps setzen
        tracking.id = row['id']
        tracking.created_at = row['created_at'] 
        tracking.updated_at = row['updated_at']
        
        # SOLL-Werte setzen
        if row['soll_gewinn_1w']:
            tracking.update_soll_gewinn(PredictionHorizon.ONE_WEEK, row['soll_gewinn_1w'])
        if row['soll_gewinn_1m']:
            tracking.update_soll_gewinn(PredictionHorizon.ONE_MONTH, row['soll_gewinn_1m'])
        if row['soll_gewinn_3m']:
            tracking.update_soll_gewinn(PredictionHorizon.THREE_MONTHS, row['soll_gewinn_3m'])
        if row['soll_gewinn_12m']:
            tracking.update_soll_gewinn(PredictionHorizon.TWELVE_MONTHS, row['soll_gewinn_12m'])
        
        # IST-Wert setzen
        if row['ist_gewinn']:
            tracking.update_ist_gewinn(row['ist_gewinn'])
        
        # Domain Events löschen (da aus DB geladen)
        tracking.clear_domain_events()
        
        return tracking