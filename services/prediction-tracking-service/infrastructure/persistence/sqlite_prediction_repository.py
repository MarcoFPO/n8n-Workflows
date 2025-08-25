#!/usr/bin/env python3
"""
Prediction Tracking Service - SQLite Repository Implementation
Infrastructure Layer Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements domain repository interfaces
- SQLite database persistence
- Data access implementation

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
import os

from ...domain.entities.prediction import Prediction
from ...domain.repositories.prediction_repository import IPredictionRepository


logger = logging.getLogger(__name__)


class SQLitePredictionRepository(IPredictionRepository):
    """
    SQLite-based Prediction Repository Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation of repository interface
    SQLITE STORAGE: File-based database for development and production
    THREAD-SAFE: Uses connection per operation for safety
    """
    
    def __init__(self, db_path: str = "predictions.db"):
        """
        Initialize SQLite repository
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._initialized_at = datetime.now()
        self._operation_count = 0
        
        # Initialize database
        asyncio.create_task(self._initialize_database())
        logger.info(f"SQLite Prediction Repository initialized: {db_path}")
    
    async def _initialize_database(self) -> None:
        """Initialize database with required tables"""
        async with self._lock:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Create predictions table with enhanced schema
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS predictions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            prediction_id TEXT UNIQUE NOT NULL,
                            symbol TEXT NOT NULL,
                            timeframe TEXT NOT NULL,
                            predicted_return REAL NOT NULL,
                            predicted_date TIMESTAMP NOT NULL,
                            actual_return REAL DEFAULT NULL,
                            evaluation_date TIMESTAMP DEFAULT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            source TEXT DEFAULT 'prediction_tracking_service',
                            status TEXT DEFAULT 'pending'
                        )
                    ''')
                    
                    # Create indices for performance
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON predictions(symbol)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timeframe ON predictions(timeframe)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prediction_id ON predictions(prediction_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_predicted_date ON predictions(predicted_date)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON predictions(status)')
                    
                    conn.commit()
                
                logger.info("Database initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise
    
    async def save_prediction(self, prediction: Prediction) -> bool:
        """
        Save prediction to SQLite database
        
        Args:
            prediction: Prediction entity to save
            
        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO predictions (
                            prediction_id, symbol, timeframe, predicted_return,
                            predicted_date, actual_return, evaluation_date, 
                            created_at, source, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        prediction.prediction_id,
                        prediction.symbol,
                        prediction.timeframe,
                        float(prediction.predicted_return),
                        prediction.predicted_date.isoformat(),
                        float(prediction.actual_return) if prediction.actual_return else None,
                        prediction.evaluation_date.isoformat() if prediction.evaluation_date else None,
                        prediction.created_at.isoformat(),
                        prediction.source,
                        prediction.get_status().value
                    ))
                    
                    conn.commit()
                
                logger.debug(f"Saved prediction: {prediction.prediction_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save prediction {prediction.prediction_id}: {e}")
                return False
    
    async def get_prediction(self, prediction_id: str) -> Optional[Prediction]:
        """
        Retrieve prediction by ID
        
        Args:
            prediction_id: Unique prediction identifier
            
        Returns:
            Prediction entity or None if not found
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT * FROM predictions WHERE prediction_id = ?',
                        (prediction_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_prediction(row)
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to get prediction {prediction_id}: {e}")
                return None
    
    async def get_predictions_by_symbol(self, symbol: str, limit: int = 100) -> List[Prediction]:
        """
        Get predictions for a specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of predictions to return
            
        Returns:
            List of Prediction entities
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM predictions 
                        WHERE symbol = ? 
                        ORDER BY predicted_date DESC 
                        LIMIT ?
                    ''', (symbol.upper(), limit))
                    
                    rows = cursor.fetchall()
                    return [self._row_to_prediction(row) for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to get predictions for symbol {symbol}: {e}")
                return []
    
    async def get_predictions_by_timeframe(self, timeframe: str, limit: int = 100) -> List[Prediction]:
        """
        Get predictions for a specific timeframe
        
        Args:
            timeframe: Prediction timeframe
            limit: Maximum number of predictions to return
            
        Returns:
            List of Prediction entities
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM predictions 
                        WHERE timeframe = ? 
                        ORDER BY predicted_date DESC 
                        LIMIT ?
                    ''', (timeframe, limit))
                    
                    rows = cursor.fetchall()
                    return [self._row_to_prediction(row) for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to get predictions for timeframe {timeframe}: {e}")
                return []
    
    async def get_recent_predictions(self, days: int = 7, limit: int = 100) -> List[Prediction]:
        """
        Get recent predictions within specified days
        
        Args:
            days: Number of days to look back
            limit: Maximum number of predictions to return
            
        Returns:
            List of recent Prediction entities
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM predictions 
                        WHERE predicted_date >= ? 
                        ORDER BY predicted_date DESC 
                        LIMIT ?
                    ''', (cutoff_date.isoformat(), limit))
                    
                    rows = cursor.fetchall()
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
        """
        Update prediction with actual return data
        
        Args:
            prediction_id: Prediction identifier
            actual_return: Actual return achieved
            evaluation_date: When evaluation was performed
            
        Returns:
            True if updated successfully, False otherwise
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                eval_date = evaluation_date or datetime.now()
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE predictions 
                        SET actual_return = ?, evaluation_date = ?, status = 'evaluated'
                        WHERE prediction_id = ?
                    ''', (actual_return, eval_date.isoformat(), prediction_id))
                    
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        logger.debug(f"Updated prediction evaluation: {prediction_id}")
                        return True
                    else:
                        logger.warning(f"No prediction found to update: {prediction_id}")
                        return False
                        
            except Exception as e:
                logger.error(f"Failed to update prediction evaluation {prediction_id}: {e}")
                return False
    
    async def get_evaluated_predictions(self, timeframe: Optional[str] = None) -> List[Prediction]:
        """
        Get predictions that have been evaluated
        
        Args:
            timeframe: Optional timeframe filter
            
        Returns:
            List of evaluated Prediction entities
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    if timeframe:
                        cursor.execute('''
                            SELECT * FROM predictions 
                            WHERE actual_return IS NOT NULL 
                            AND evaluation_date IS NOT NULL 
                            AND timeframe = ?
                            ORDER BY evaluation_date DESC
                        ''', (timeframe,))
                    else:
                        cursor.execute('''
                            SELECT * FROM predictions 
                            WHERE actual_return IS NOT NULL 
                            AND evaluation_date IS NOT NULL
                            ORDER BY evaluation_date DESC
                        ''')
                    
                    rows = cursor.fetchall()
                    return [self._row_to_prediction(row) for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to get evaluated predictions: {e}")
                return []
    
    async def get_pending_evaluations(self, days_old: int = 1) -> List[Prediction]:
        """
        Get predictions that need evaluation
        
        Args:
            days_old: Minimum age in days for pending evaluation
            
        Returns:
            List of Prediction entities pending evaluation
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM predictions 
                        WHERE actual_return IS NULL 
                        AND predicted_date <= ?
                        ORDER BY predicted_date ASC
                    ''', (cutoff_date.isoformat(),))
                    
                    rows = cursor.fetchall()
                    return [self._row_to_prediction(row) for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to get pending evaluations: {e}")
                return []
    
    async def delete_old_predictions(self, days_old: int = 365) -> int:
        """
        Delete old predictions
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of predictions deleted
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        DELETE FROM predictions 
                        WHERE created_at < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    conn.commit()
                    deleted_count = cursor.rowcount
                    
                logger.info(f"Deleted {deleted_count} old predictions")
                return deleted_count
                
            except Exception as e:
                logger.error(f"Failed to delete old predictions: {e}")
                return 0
    
    async def get_all_symbols(self) -> List[str]:
        """
        Get all symbols that have predictions
        
        Returns:
            List of unique symbols
        """
        async with self._lock:
            self._operation_count += 1
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT DISTINCT symbol FROM predictions ORDER BY symbol')
                    rows = cursor.fetchall()
                    return [row[0] for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to get all symbols: {e}")
                return []
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get repository statistics
        
        Returns:
            Statistics dictionary
        """
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Total predictions
                    cursor.execute('SELECT COUNT(*) FROM predictions')
                    total_predictions = cursor.fetchone()[0]
                    
                    # Evaluated predictions
                    cursor.execute('SELECT COUNT(*) FROM predictions WHERE actual_return IS NOT NULL')
                    evaluated_predictions = cursor.fetchone()[0]
                    
                    # By timeframe
                    cursor.execute('SELECT timeframe, COUNT(*) FROM predictions GROUP BY timeframe')
                    timeframe_counts = dict(cursor.fetchall())
                    
                    # By status
                    cursor.execute('SELECT status, COUNT(*) FROM predictions GROUP BY status')
                    status_counts = dict(cursor.fetchall())
                    
                    uptime = datetime.now() - self._initialized_at
                    
                return {
                    'repository_type': 'sqlite',
                    'database_path': self.db_path,
                    'total_predictions': total_predictions,
                    'evaluated_predictions': evaluated_predictions,
                    'pending_predictions': total_predictions - evaluated_predictions,
                    'timeframe_distribution': timeframe_counts,
                    'status_distribution': status_counts,
                    'operation_count': self._operation_count,
                    'uptime_seconds': int(uptime.total_seconds()),
                    'initialized_at': self._initialized_at.isoformat(),
                    'last_check': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to get repository stats: {e}")
                return {'error': str(e)}
    
    def _row_to_prediction(self, row) -> Prediction:
        """
        Convert database row to Prediction entity
        
        Args:
            row: Database row tuple
            
        Returns:
            Prediction entity
        """
        # Row format: (id, prediction_id, symbol, timeframe, predicted_return, 
        #              predicted_date, actual_return, evaluation_date, created_at, source, status)
        return Prediction(
            prediction_id=row[1],
            symbol=row[2],
            timeframe=row[3],
            predicted_return=Decimal(str(row[4])),
            predicted_date=datetime.fromisoformat(row[5]),
            actual_return=Decimal(str(row[6])) if row[6] is not None else None,
            evaluation_date=datetime.fromisoformat(row[7]) if row[7] else None,
            created_at=datetime.fromisoformat(row[8]),
            source=row[9] if row[9] else 'prediction_tracking_service'
        )