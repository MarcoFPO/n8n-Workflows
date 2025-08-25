#!/usr/bin/env python3
"""
Prediction Tracking Service - PostgreSQL Repository Implementation
Infrastructure Layer Implementation - Database Manager Integration

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements domain repository interfaces
- PostgreSQL database persistence with central connection manager
- Data access implementation with connection pooling

MIGRATION v6.0.0 → v6.1.0:
- SQLite zu PostgreSQL Migration
- Central Database Manager Integration
- Connection Pool Utilization

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0 (PostgreSQL Migration)
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
import asyncio

# Database Manager Import - Direct Path Import
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConnectionManager

from ...domain.entities.prediction import Prediction, TimeframeType, PredictionStatus
from ...domain.repositories.prediction_repository import IPredictionRepository


logger = logging.getLogger(__name__)


class PostgreSQLPredictionRepository(IPredictionRepository):
    """
    PostgreSQL-based Prediction Repository Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation of repository interface
    POSTGRESQL STORAGE: Centralized database with connection pooling
    ASYNC OPERATIONS: Full async/await support with connection management
    CLEAN ARCHITECTURE: Pure repository implementation without business logic
    """
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        """
        Initialize PostgreSQL repository with database manager
        
        Args:
            db_manager: Central database connection manager
        """
        self.db_manager = db_manager
        self._initialized_at = datetime.now(timezone.utc)
        self._operation_count = 0
        logger.info("PostgreSQL Prediction Repository initialized with Database Manager")
    
    async def initialize_schema(self) -> bool:
        """
        Initialize prediction database schema
        
        Returns:
            True if schema initialized successfully
        """
        try:
            async with self.db_manager.get_connection() as connection:
                # Create predictions table
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS predictions (
                        prediction_id VARCHAR(255) PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        predicted_return DECIMAL(10, 6) NOT NULL,
                        confidence_score DECIMAL(5, 4) NOT NULL,
                        timeframe VARCHAR(50) NOT NULL,
                        prediction_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        evaluation_date TIMESTAMPTZ NULL,
                        actual_return DECIMAL(10, 6) NULL,
                        is_evaluated BOOLEAN NOT NULL DEFAULT FALSE,
                        status VARCHAR(50) NOT NULL DEFAULT 'active',
                        source_model VARCHAR(100) NULL,
                        high_confidence BOOLEAN NOT NULL DEFAULT FALSE,
                        features_used JSONB NULL,
                        metadata JSONB NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                ''')
                
                # Create indexes for performance
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_predictions_symbol 
                    ON predictions (symbol)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_predictions_timeframe 
                    ON predictions (timeframe)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_predictions_date 
                    ON predictions (prediction_date)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_predictions_evaluation 
                    ON predictions (is_evaluated, evaluation_date)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_predictions_status 
                    ON predictions (status)
                ''')
                
                logger.info("Prediction schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize prediction schema: {e}")
            return False
    
    async def save_prediction(self, prediction: Prediction) -> bool:
        """Save prediction to PostgreSQL database"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Convert prediction to database format
                features_json = json.dumps(prediction.features_used) if prediction.features_used else None
                metadata_json = json.dumps(prediction.to_dict()) if hasattr(prediction, 'to_dict') else None
                
                await connection.execute('''
                    INSERT INTO predictions (
                        prediction_id, symbol, predicted_return, confidence_score,
                        timeframe, prediction_date, evaluation_date, actual_return,
                        is_evaluated, status, source_model, high_confidence,
                        features_used, metadata, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    ON CONFLICT (prediction_id) DO UPDATE SET
                        predicted_return = EXCLUDED.predicted_return,
                        confidence_score = EXCLUDED.confidence_score,
                        timeframe = EXCLUDED.timeframe,
                        evaluation_date = EXCLUDED.evaluation_date,
                        actual_return = EXCLUDED.actual_return,
                        is_evaluated = EXCLUDED.is_evaluated,
                        status = EXCLUDED.status,
                        high_confidence = EXCLUDED.high_confidence,
                        features_used = EXCLUDED.features_used,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                ''', 
                    prediction.prediction_id,
                    prediction.symbol,
                    prediction.predicted_return,
                    prediction.confidence_score,
                    prediction.timeframe.value if isinstance(prediction.timeframe, TimeframeType) else prediction.timeframe,
                    prediction.prediction_date,
                    prediction.evaluation_date,
                    prediction.actual_return,
                    prediction.is_evaluated,
                    prediction.status.value if isinstance(prediction.status, PredictionStatus) else str(prediction.status),
                    prediction.source_model,
                    prediction.high_confidence,
                    features_json,
                    metadata_json,
                    prediction.prediction_date,  # created_at
                    datetime.now(timezone.utc)   # updated_at
                )
                
                self._operation_count += 1
                logger.debug(f"Prediction saved: {prediction.prediction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save prediction {prediction.prediction_id}: {e}")
            return False
    
    async def get_prediction(self, prediction_id: str) -> Optional[Prediction]:
        """Retrieve prediction by ID"""
        try:
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow('''
                    SELECT * FROM predictions WHERE prediction_id = $1
                ''', prediction_id)
                
                if row:
                    return self._row_to_prediction(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get prediction {prediction_id}: {e}")
            return None
    
    async def get_predictions_by_symbol(self, symbol: str, limit: int = 100) -> List[Prediction]:
        """Get predictions for a specific symbol"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM predictions 
                    WHERE symbol = $1 
                    ORDER BY prediction_date DESC 
                    LIMIT $2
                ''', symbol, limit)
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get predictions for symbol {symbol}: {e}")
            return []
    
    async def get_predictions_by_timeframe(self, timeframe: str, limit: int = 100) -> List[Prediction]:
        """Get predictions for a specific timeframe"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM predictions 
                    WHERE timeframe = $1 
                    ORDER BY prediction_date DESC 
                    LIMIT $2
                ''', timeframe, limit)
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get predictions for timeframe {timeframe}: {e}")
            return []
    
    async def get_recent_predictions(self, days: int = 7, limit: int = 100) -> List[Prediction]:
        """Get recent predictions within specified days"""
        try:
            async with self.db_manager.get_connection() as connection:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                rows = await connection.fetch('''
                    SELECT * FROM predictions 
                    WHERE prediction_date >= $1 
                    ORDER BY prediction_date DESC 
                    LIMIT $2
                ''', cutoff_date, limit)
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get recent predictions: {e}")
            return []
    
    async def update_prediction_evaluation(
        self, 
        prediction_id: str, 
        actual_return: float, 
        evaluation_date: Optional[datetime] = None
    ) -> bool:
        """Update prediction with actual return data"""
        try:
            async with self.db_manager.get_connection() as connection:
                eval_date = evaluation_date or datetime.now(timezone.utc)
                
                result = await connection.execute('''
                    UPDATE predictions 
                    SET actual_return = $1, 
                        evaluation_date = $2, 
                        is_evaluated = TRUE,
                        updated_at = NOW()
                    WHERE prediction_id = $3
                ''', actual_return, eval_date, prediction_id)
                
                rows_affected = int(result.split()[-1])
                if rows_affected > 0:
                    logger.debug(f"Prediction {prediction_id} evaluated with return {actual_return}")
                    return True
                    
                logger.warning(f"No prediction found for evaluation: {prediction_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update prediction evaluation {prediction_id}: {e}")
            return False
    
    async def get_evaluated_predictions(self, timeframe: Optional[str] = None) -> List[Prediction]:
        """Get predictions that have been evaluated"""
        try:
            async with self.db_manager.get_connection() as connection:
                if timeframe:
                    rows = await connection.fetch('''
                        SELECT * FROM predictions 
                        WHERE is_evaluated = TRUE AND timeframe = $1
                        ORDER BY evaluation_date DESC
                    ''', timeframe)
                else:
                    rows = await connection.fetch('''
                        SELECT * FROM predictions 
                        WHERE is_evaluated = TRUE
                        ORDER BY evaluation_date DESC
                    ''')
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get evaluated predictions: {e}")
            return []
    
    async def get_pending_evaluations(self, days_old: int = 1) -> List[Prediction]:
        """Get predictions that need evaluation"""
        try:
            async with self.db_manager.get_connection() as connection:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
                
                rows = await connection.fetch('''
                    SELECT * FROM predictions 
                    WHERE is_evaluated = FALSE 
                    AND prediction_date <= $1
                    AND status = 'active'
                    ORDER BY prediction_date ASC
                ''', cutoff_date)
                
                return [self._row_to_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get pending evaluations: {e}")
            return []
    
    async def delete_old_predictions(self, days_old: int = 365) -> int:
        """Delete old predictions"""
        try:
            async with self.db_manager.get_connection() as connection:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
                
                result = await connection.execute('''
                    DELETE FROM predictions 
                    WHERE prediction_date < $1
                ''', cutoff_date)
                
                deleted_count = int(result.split()[-1])
                logger.info(f"Deleted {deleted_count} old predictions older than {days_old} days")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to delete old predictions: {e}")
            return 0
    
    async def get_all_symbols(self) -> List[str]:
        """Get all symbols that have predictions"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT DISTINCT symbol FROM predictions 
                    ORDER BY symbol
                ''')
                
                return [row['symbol'] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get all symbols: {e}")
            return []
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Get basic counts
                total_predictions = await connection.fetchval('SELECT COUNT(*) FROM predictions')
                evaluated_predictions = await connection.fetchval('SELECT COUNT(*) FROM predictions WHERE is_evaluated = TRUE')
                unique_symbols = await connection.fetchval('SELECT COUNT(DISTINCT symbol) FROM predictions')
                
                # Get timeframe distribution
                timeframe_stats = await connection.fetch('''
                    SELECT timeframe, COUNT(*) as count 
                    FROM predictions 
                    GROUP BY timeframe 
                    ORDER BY count DESC
                ''')
                
                return {
                    "total_predictions": total_predictions,
                    "evaluated_predictions": evaluated_predictions,
                    "pending_evaluations": total_predictions - evaluated_predictions,
                    "unique_symbols": unique_symbols,
                    "timeframe_distribution": {row['timeframe']: row['count'] for row in timeframe_stats},
                    "repository_type": "PostgreSQL",
                    "initialized_at": self._initialized_at.isoformat(),
                    "operation_count": self._operation_count,
                    "database_manager": "centralized_pool"
                }
                
        except Exception as e:
            logger.error(f"Failed to get repository stats: {e}")
            return {
                "error": str(e),
                "repository_type": "PostgreSQL",
                "initialized_at": self._initialized_at.isoformat()
            }
    
    def _row_to_prediction(self, row) -> Prediction:
        """Convert database row to Prediction entity"""
        # Parse JSON fields
        features_used = json.loads(row['features_used']) if row['features_used'] else []
        
        return Prediction(
            prediction_id=row['prediction_id'],
            symbol=row['symbol'],
            predicted_return=float(row['predicted_return']),
            confidence_score=float(row['confidence_score']),
            timeframe=TimeframeType(row['timeframe']) if row['timeframe'] in [t.value for t in TimeframeType] else row['timeframe'],
            prediction_date=row['prediction_date'],
            evaluation_date=row['evaluation_date'],
            actual_return=float(row['actual_return']) if row['actual_return'] is not None else None,
            is_evaluated=row['is_evaluated'],
            status=PredictionStatus(row['status']) if row['status'] in [s.value for s in PredictionStatus] else row['status'],
            source_model=row['source_model'],
            high_confidence=row['high_confidence'],
            features_used=features_used
        )