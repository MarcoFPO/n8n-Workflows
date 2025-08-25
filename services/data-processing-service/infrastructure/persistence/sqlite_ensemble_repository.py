"""
Data Processing Service - SQLite Ensemble Repository
Clean Architecture v6.0.0

SQLite Implementation für Ensemble Prediction Repository
"""
import aiosqlite
import json
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal

from domain.entities.prediction_entities import (
    EnsemblePrediction, ModelPrediction, PredictionModelType, EnsembleWeightStrategy
)
from domain.repositories.prediction_repository import IEnsemblePredictionRepository

logger = structlog.get_logger(__name__)


class SQLiteEnsemblePredictionRepository(IEnsemblePredictionRepository):
    """SQLite Implementation für Ensemble Prediction Repository"""
    
    def __init__(self, db_path: str = "prediction_ensembles.db"):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Ensemble predictions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ensemble_predictions (
                    ensemble_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    ensemble_price DECIMAL(10,4),
                    ensemble_confidence REAL,
                    weight_strategy TEXT NOT NULL,
                    model_weights TEXT,
                    created_at TEXT NOT NULL,
                    prediction_horizon_days INTEGER NOT NULL,
                    data_quality_score TEXT,
                    model_count INTEGER NOT NULL DEFAULT 0,
                    consensus_strength REAL DEFAULT 0.0
                )
            """)
            
            # Individual predictions within ensembles
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ensemble_individual_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ensemble_id TEXT NOT NULL,
                    prediction_id TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    predicted_price DECIMAL(10,4) NOT NULL,
                    confidence_score REAL NOT NULL,
                    model_weight REAL DEFAULT 1.0,
                    FOREIGN KEY (ensemble_id) REFERENCES ensemble_predictions(ensemble_id)
                )
            """)
            
            # Create optimized indices
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ens_symbol ON ensemble_predictions(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ens_created_at ON ensemble_predictions(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ens_confidence ON ensemble_predictions(ensemble_confidence)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ens_quality ON ensemble_predictions(data_quality_score)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ens_ind_ensemble_id ON ensemble_individual_predictions(ensemble_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ens_ind_model_type ON ensemble_individual_predictions(model_type)")
            
            await db.commit()

    async def store_ensemble_prediction(self, ensemble: EnsemblePrediction) -> bool:
        """Store ensemble prediction with individual predictions"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Store main ensemble record
                await db.execute("""
                    INSERT OR REPLACE INTO ensemble_predictions 
                    (ensemble_id, symbol, ensemble_price, ensemble_confidence,
                     weight_strategy, model_weights, created_at, prediction_horizon_days,
                     data_quality_score, model_count, consensus_strength)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ensemble.ensemble_id,
                    ensemble.symbol,
                    str(ensemble.ensemble_price) if ensemble.ensemble_price else None,
                    ensemble.ensemble_confidence,
                    ensemble.weight_strategy.value,
                    json.dumps(ensemble.model_weights) if ensemble.model_weights else None,
                    ensemble.created_at.isoformat(),
                    ensemble.prediction_horizon_days,
                    ensemble.data_quality_score.value if ensemble.data_quality_score else None,
                    ensemble.get_model_count(),
                    ensemble.get_consensus_strength()
                ))
                
                # Delete existing individual predictions for this ensemble
                await db.execute(
                    "DELETE FROM ensemble_individual_predictions WHERE ensemble_id = ?",
                    (ensemble.ensemble_id,)
                )
                
                # Store individual predictions
                for prediction in ensemble.individual_predictions:
                    model_weight = ensemble._get_model_weight(prediction) if hasattr(ensemble, '_get_model_weight') else 1.0
                    
                    await db.execute("""
                        INSERT INTO ensemble_individual_predictions 
                        (ensemble_id, prediction_id, model_type, predicted_price, 
                         confidence_score, model_weight)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        ensemble.ensemble_id,
                        prediction.prediction_id,
                        prediction.model_type.value,
                        str(prediction.predicted_price),
                        prediction.confidence_score,
                        model_weight
                    ))
                
                await db.commit()
                logger.info(f"Stored ensemble prediction {ensemble.ensemble_id} with {len(ensemble.individual_predictions)} individual predictions")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store ensemble prediction: {str(e)}")
            return False

    async def get_ensemble_by_id(self, ensemble_id: str) -> Optional[EnsemblePrediction]:
        """Get ensemble prediction by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get ensemble record
                cursor = await db.execute("""
                    SELECT ensemble_id, symbol, ensemble_price, ensemble_confidence,
                           weight_strategy, model_weights, created_at, prediction_horizon_days,
                           data_quality_score
                    FROM ensemble_predictions 
                    WHERE ensemble_id = ?
                """, (ensemble_id,))
                
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # Get individual predictions
                pred_cursor = await db.execute("""
                    SELECT prediction_id, model_type, predicted_price, confidence_score
                    FROM ensemble_individual_predictions 
                    WHERE ensemble_id = ?
                """, (ensemble_id,))
                
                pred_rows = await pred_cursor.fetchall()
                
                # Reconstruct individual predictions
                individual_predictions = []
                for pred_row in pred_rows:
                    prediction = ModelPrediction(
                        prediction_id=pred_row[0],
                        model_type=PredictionModelType(pred_row[1]),
                        symbol=row[1],  # symbol from ensemble
                        predicted_price=Decimal(pred_row[2]),
                        confidence_score=pred_row[3],
                        prediction_horizon_days=row[7],  # horizon from ensemble
                        created_at=datetime.fromisoformat(row[6])  # created_at from ensemble
                    )
                    individual_predictions.append(prediction)
                
                # Create ensemble object
                from domain.entities.prediction_entities import DataQuality
                
                ensemble = EnsemblePrediction(
                    ensemble_id=row[0],
                    symbol=row[1],
                    individual_predictions=individual_predictions,
                    ensemble_price=Decimal(row[2]) if row[2] else None,
                    ensemble_confidence=row[3],
                    weight_strategy=EnsembleWeightStrategy(row[4]),
                    model_weights=json.loads(row[5]) if row[5] else None,
                    created_at=datetime.fromisoformat(row[6]),
                    prediction_horizon_days=row[7],
                    data_quality_score=DataQuality(row[8]) if row[8] else None
                )
                
                return ensemble
                
        except Exception as e:
            logger.error(f"Failed to get ensemble by ID: {str(e)}")
            return None

    async def get_ensemble_predictions_by_symbol(
        self, 
        symbol: str,
        limit: int = 50
    ) -> List[EnsemblePrediction]:
        """Get ensemble predictions for symbol"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT ensemble_id
                    FROM ensemble_predictions 
                    WHERE symbol = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (symbol, limit))
                
                rows = await cursor.fetchall()
                
                ensembles = []
                for row in rows:
                    ensemble = await self.get_ensemble_by_id(row[0])
                    if ensemble:
                        ensembles.append(ensemble)
                
                return ensembles
                
        except Exception as e:
            logger.error(f"Failed to get ensemble predictions by symbol: {str(e)}")
            return []

    async def get_latest_ensemble_prediction(self, symbol: str) -> Optional[EnsemblePrediction]:
        """Get most recent ensemble prediction for symbol"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT ensemble_id
                    FROM ensemble_predictions 
                    WHERE symbol = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (symbol,))
                
                row = await cursor.fetchone()
                
                if row:
                    return await self.get_ensemble_by_id(row[0])
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get latest ensemble prediction: {str(e)}")
            return None

    async def get_ensemble_performance_comparison(
        self, 
        symbols: List[str],
        days: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """Compare ensemble performance across symbols"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            performance_data = {}
            
            async with aiosqlite.connect(self.db_path) as db:
                for symbol in symbols:
                    cursor = await db.execute("""
                        SELECT 
                            AVG(ensemble_confidence) as avg_confidence,
                            AVG(consensus_strength) as avg_consensus,
                            COUNT(*) as total_ensembles,
                            MAX(ensemble_confidence) as max_confidence,
                            MIN(ensemble_confidence) as min_confidence,
                            AVG(model_count) as avg_model_count
                        FROM ensemble_predictions 
                        WHERE symbol = ? AND created_at >= ?
                    """, (symbol, start_date.isoformat()))
                    
                    row = await cursor.fetchone()
                    
                    if row and row[2] > 0:  # If we have data
                        performance_data[symbol] = {
                            "average_confidence": row[0] or 0.0,
                            "average_consensus": row[1] or 0.0,
                            "total_ensembles": row[2] or 0,
                            "max_confidence": row[3] or 0.0,
                            "min_confidence": row[4] or 0.0,
                            "average_model_count": row[5] or 0.0
                        }
                    else:
                        performance_data[symbol] = {
                            "average_confidence": 0.0,
                            "average_consensus": 0.0,
                            "total_ensembles": 0,
                            "max_confidence": 0.0,
                            "min_confidence": 0.0,
                            "average_model_count": 0.0
                        }
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Failed to get ensemble performance comparison: {str(e)}")
            return {}

    async def get_consensus_strength_statistics(self) -> Dict[str, float]:
        """Get overall consensus strength statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 
                        AVG(consensus_strength) as avg_consensus,
                        MAX(consensus_strength) as max_consensus,
                        MIN(consensus_strength) as min_consensus,
                        COUNT(*) as total_ensembles,
                        COUNT(CASE WHEN consensus_strength > 0.7 THEN 1 END) as high_consensus_count
                    FROM ensemble_predictions 
                    WHERE consensus_strength IS NOT NULL
                """)
                
                row = await cursor.fetchone()
                
                if row:
                    total = row[3] or 1  # Avoid division by zero
                    return {
                        "average_consensus_strength": row[0] or 0.0,
                        "max_consensus_strength": row[1] or 0.0,
                        "min_consensus_strength": row[2] or 0.0,
                        "total_ensembles": total,
                        "high_consensus_percentage": (row[4] or 0) / total * 100
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get consensus strength statistics: {str(e)}")
            return {}

    async def cleanup_old_ensembles(self, days_to_keep: int = 180) -> int:
        """Clean up old ensemble predictions, return number of deleted records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                # First get ensemble IDs to be deleted
                cursor = await db.execute(
                    "SELECT ensemble_id FROM ensemble_predictions WHERE created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                ensemble_ids = [row[0] for row in await cursor.fetchall()]
                
                if not ensemble_ids:
                    return 0
                
                # Delete individual predictions
                placeholders = ','.join(['?' for _ in ensemble_ids])
                await db.execute(
                    f"DELETE FROM ensemble_individual_predictions WHERE ensemble_id IN ({placeholders})",
                    ensemble_ids
                )
                
                # Delete ensemble records
                cursor = await db.execute(
                    "DELETE FROM ensemble_predictions WHERE created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                await db.commit()
                
                logger.info(f"Cleaned up {deleted_count} old ensemble predictions")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old ensembles: {str(e)}")
            return 0