"""
Data Processing Service - SQLite Repository Implementations
Clean Architecture v6.0.0

SQLite-based Implementation für Prediction Data Persistence
"""
import aiosqlite
import json
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal

from domain.entities.prediction_entities import (
    StockData, ModelPrediction, EnsemblePrediction, PredictionJob,
    DataProcessingMetrics, PredictionModelType, PredictionStatus,
    EnsembleWeightStrategy, DataQuality
)
from domain.repositories.prediction_repository import (
    IStockDataRepository, IModelPredictionRepository, IEnsemblePredictionRepository,
    IPredictionJobRepository, IDataProcessingMetricsRepository, IMLModelRepository
)

logger = structlog.get_logger(__name__)


class SQLiteStockDataRepository(IStockDataRepository):
    """SQLite Implementation für Stock Data Repository"""
    
    def __init__(self, db_path: str = "prediction_stock_data.db"):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open_price DECIMAL(10,4) NOT NULL,
                    high_price DECIMAL(10,4) NOT NULL,
                    low_price DECIMAL(10,4) NOT NULL,
                    close_price DECIMAL(10,4) NOT NULL,
                    volume INTEGER NOT NULL,
                    adjusted_close DECIMAL(10,4),
                    created_at TEXT NOT NULL,
                    UNIQUE(symbol, date)
                )
            """)
            
            # Create optimized indices
            await db.execute("CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_data(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_data(date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_stock_symbol_date ON stock_data(symbol, date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_stock_volume ON stock_data(volume)")
            
            await db.commit()

    async def store_stock_data(self, stock_data_list: List[StockData]) -> bool:
        """Store multiple stock data points"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for data in stock_data_list:
                    await db.execute("""
                        INSERT OR REPLACE INTO stock_data 
                        (symbol, date, open_price, high_price, low_price, close_price, 
                         volume, adjusted_close, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.symbol,
                        data.date.isoformat(),
                        str(data.open_price),
                        str(data.high_price),
                        str(data.low_price),
                        str(data.close_price),
                        data.volume,
                        str(data.adjusted_close) if data.adjusted_close else None,
                        datetime.now().isoformat()
                    ))
                
                await db.commit()
                logger.info(f"Stored {len(stock_data_list)} stock data records")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store stock data: {str(e)}")
            return False

    async def get_stock_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[StockData]:
        """Get stock data for symbol within date range"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT symbol, date, open_price, high_price, low_price, close_price, 
                           volume, adjusted_close
                    FROM stock_data 
                    WHERE symbol = ? AND date >= ? AND date <= ?
                    ORDER BY date ASC
                """, (symbol, start_date.isoformat(), end_date.isoformat()))
                
                rows = await cursor.fetchall()
                
                stock_data_list = []
                for row in rows:
                    stock_data = StockData(
                        symbol=row[0],
                        date=datetime.fromisoformat(row[1]),
                        open_price=Decimal(row[2]),
                        high_price=Decimal(row[3]),
                        low_price=Decimal(row[4]),
                        close_price=Decimal(row[5]),
                        volume=row[6],
                        adjusted_close=Decimal(row[7]) if row[7] else None
                    )
                    stock_data_list.append(stock_data)
                
                return stock_data_list
                
        except Exception as e:
            logger.error(f"Failed to get stock data: {str(e)}")
            return []

    async def get_latest_stock_data(self, symbol: str) -> Optional[StockData]:
        """Get most recent stock data for symbol"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT symbol, date, open_price, high_price, low_price, close_price, 
                           volume, adjusted_close
                    FROM stock_data 
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT 1
                """, (symbol,))
                
                row = await cursor.fetchone()
                
                if row:
                    return StockData(
                        symbol=row[0],
                        date=datetime.fromisoformat(row[1]),
                        open_price=Decimal(row[2]),
                        high_price=Decimal(row[3]),
                        low_price=Decimal(row[4]),
                        close_price=Decimal(row[5]),
                        volume=row[6],
                        adjusted_close=Decimal(row[7]) if row[7] else None
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get latest stock data: {str(e)}")
            return None

    async def get_stock_data_count(self, symbol: str) -> int:
        """Get total count of stock data points for symbol"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM stock_data WHERE symbol = ?", 
                    (symbol,)
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
                
        except Exception as e:
            logger.error(f"Failed to get stock data count: {str(e)}")
            return 0

    async def cleanup_old_stock_data(self, days_to_keep: int = 365) -> int:
        """Clean up old stock data, return number of deleted records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM stock_data WHERE date < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                await db.commit()
                
                logger.info(f"Cleaned up {deleted_count} old stock data records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old stock data: {str(e)}")
            return 0

    async def get_available_symbols(self) -> List[str]:
        """Get list of all available stock symbols"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get available symbols: {str(e)}")
            return []

    async def get_data_quality_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get data quality metrics for symbol"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get basic statistics
                cursor = await db.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        AVG(volume) as avg_volume,
                        COUNT(CASE WHEN volume = 0 THEN 1 END) as zero_volume_days
                    FROM stock_data 
                    WHERE symbol = ?
                """, (symbol,))
                
                row = await cursor.fetchone()
                
                if row:
                    return {
                        "symbol": symbol,
                        "total_records": row[0],
                        "earliest_date": row[1],
                        "latest_date": row[2],
                        "average_volume": row[3],
                        "zero_volume_days": row[4],
                        "data_completeness_score": max(0.0, 1.0 - (row[4] / row[0])) if row[0] > 0 else 0.0
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get data quality metrics: {str(e)}")
            return {}


class SQLiteModelPredictionRepository(IModelPredictionRepository):
    """SQLite Implementation für Model Prediction Repository"""
    
    def __init__(self, db_path: str = "prediction_models.db"):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS model_predictions (
                    prediction_id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    predicted_price DECIMAL(10,4) NOT NULL,
                    confidence_score REAL NOT NULL,
                    prediction_horizon_days INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    model_accuracy REAL,
                    feature_importance TEXT,
                    training_data_size INTEGER
                )
            """)
            
            # Create optimized indices
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pred_symbol ON model_predictions(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pred_model_type ON model_predictions(model_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pred_created_at ON model_predictions(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pred_confidence ON model_predictions(confidence_score)")
            
            await db.commit()

    async def store_prediction(self, prediction: ModelPrediction) -> bool:
        """Store individual model prediction"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO model_predictions 
                    (prediction_id, model_type, symbol, predicted_price, confidence_score,
                     prediction_horizon_days, created_at, model_accuracy, feature_importance,
                     training_data_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction.prediction_id,
                    prediction.model_type.value,
                    prediction.symbol,
                    str(prediction.predicted_price),
                    prediction.confidence_score,
                    prediction.prediction_horizon_days,
                    prediction.created_at.isoformat(),
                    prediction.model_accuracy,
                    json.dumps(prediction.feature_importance) if prediction.feature_importance else None,
                    prediction.training_data_size
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store model prediction: {str(e)}")
            return False

    async def get_predictions_by_symbol(
        self, 
        symbol: str, 
        model_type: Optional[PredictionModelType] = None,
        limit: int = 100
    ) -> List[ModelPrediction]:
        """Get predictions for symbol, optionally filtered by model type"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if model_type:
                    cursor = await db.execute("""
                        SELECT prediction_id, model_type, symbol, predicted_price, 
                               confidence_score, prediction_horizon_days, created_at,
                               model_accuracy, feature_importance, training_data_size
                        FROM model_predictions 
                        WHERE symbol = ? AND model_type = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (symbol, model_type.value, limit))
                else:
                    cursor = await db.execute("""
                        SELECT prediction_id, model_type, symbol, predicted_price, 
                               confidence_score, prediction_horizon_days, created_at,
                               model_accuracy, feature_importance, training_data_size
                        FROM model_predictions 
                        WHERE symbol = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (symbol, limit))
                
                rows = await cursor.fetchall()
                
                predictions = []
                for row in rows:
                    feature_importance = json.loads(row[8]) if row[8] else None
                    
                    prediction = ModelPrediction(
                        prediction_id=row[0],
                        model_type=PredictionModelType(row[1]),
                        symbol=row[2],
                        predicted_price=Decimal(row[3]),
                        confidence_score=row[4],
                        prediction_horizon_days=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        model_accuracy=row[7],
                        feature_importance=feature_importance,
                        training_data_size=row[9]
                    )
                    predictions.append(prediction)
                
                return predictions
                
        except Exception as e:
            logger.error(f"Failed to get predictions by symbol: {str(e)}")
            return []

    async def get_prediction_by_id(self, prediction_id: str) -> Optional[ModelPrediction]:
        """Get specific prediction by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT prediction_id, model_type, symbol, predicted_price, 
                           confidence_score, prediction_horizon_days, created_at,
                           model_accuracy, feature_importance, training_data_size
                    FROM model_predictions 
                    WHERE prediction_id = ?
                """, (prediction_id,))
                
                row = await cursor.fetchone()
                
                if row:
                    feature_importance = json.loads(row[8]) if row[8] else None
                    
                    return ModelPrediction(
                        prediction_id=row[0],
                        model_type=PredictionModelType(row[1]),
                        symbol=row[2],
                        predicted_price=Decimal(row[3]),
                        confidence_score=row[4],
                        prediction_horizon_days=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        model_accuracy=row[7],
                        feature_importance=feature_importance,
                        training_data_size=row[9]
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get prediction by ID: {str(e)}")
            return None

    async def get_recent_predictions(
        self, 
        hours: int = 24,
        model_type: Optional[PredictionModelType] = None
    ) -> List[ModelPrediction]:
        """Get recent predictions within specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            async with aiosqlite.connect(self.db_path) as db:
                if model_type:
                    cursor = await db.execute("""
                        SELECT prediction_id, model_type, symbol, predicted_price, 
                               confidence_score, prediction_horizon_days, created_at,
                               model_accuracy, feature_importance, training_data_size
                        FROM model_predictions 
                        WHERE created_at >= ? AND model_type = ?
                        ORDER BY created_at DESC
                    """, (cutoff_time.isoformat(), model_type.value))
                else:
                    cursor = await db.execute("""
                        SELECT prediction_id, model_type, symbol, predicted_price, 
                               confidence_score, prediction_horizon_days, created_at,
                               model_accuracy, feature_importance, training_data_size
                        FROM model_predictions 
                        WHERE created_at >= ?
                        ORDER BY created_at DESC
                    """, (cutoff_time.isoformat(),))
                
                rows = await cursor.fetchall()
                
                predictions = []
                for row in rows:
                    feature_importance = json.loads(row[8]) if row[8] else None
                    
                    prediction = ModelPrediction(
                        prediction_id=row[0],
                        model_type=PredictionModelType(row[1]),
                        symbol=row[2],
                        predicted_price=Decimal(row[3]),
                        confidence_score=row[4],
                        prediction_horizon_days=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        model_accuracy=row[7],
                        feature_importance=feature_importance,
                        training_data_size=row[9]
                    )
                    predictions.append(prediction)
                
                return predictions
                
        except Exception as e:
            logger.error(f"Failed to get recent predictions: {str(e)}")
            return []

    async def get_model_performance_statistics(
        self, 
        model_type: PredictionModelType,
        symbol: Optional[str] = None
    ) -> Dict[str, float]:
        """Get performance statistics for specific model type"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if symbol:
                    cursor = await db.execute("""
                        SELECT 
                            AVG(confidence_score) as avg_confidence,
                            AVG(model_accuracy) as avg_accuracy,
                            COUNT(*) as total_predictions,
                            MAX(confidence_score) as max_confidence,
                            MIN(confidence_score) as min_confidence
                        FROM model_predictions 
                        WHERE model_type = ? AND symbol = ?
                    """, (model_type.value, symbol))
                else:
                    cursor = await db.execute("""
                        SELECT 
                            AVG(confidence_score) as avg_confidence,
                            AVG(model_accuracy) as avg_accuracy,
                            COUNT(*) as total_predictions,
                            MAX(confidence_score) as max_confidence,
                            MIN(confidence_score) as min_confidence
                        FROM model_predictions 
                        WHERE model_type = ?
                    """, (model_type.value,))
                
                row = await cursor.fetchone()
                
                if row:
                    return {
                        "average_confidence": row[0] or 0.0,
                        "average_accuracy": row[1] or 0.0,
                        "total_predictions": row[2] or 0,
                        "max_confidence": row[3] or 0.0,
                        "min_confidence": row[4] or 0.0
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get model performance statistics: {str(e)}")
            return {}

    async def cleanup_old_predictions(self, days_to_keep: int = 90) -> int:
        """Clean up old predictions, return number of deleted records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM model_predictions WHERE created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                await db.commit()
                
                logger.info(f"Cleaned up {deleted_count} old model predictions")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old predictions: {str(e)}")
            return 0

    async def get_prediction_accuracy_trend(
        self, 
        model_type: PredictionModelType,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get accuracy trend for model over time"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 
                        DATE(created_at) as prediction_date,
                        AVG(confidence_score) as avg_confidence,
                        AVG(model_accuracy) as avg_accuracy,
                        COUNT(*) as prediction_count
                    FROM model_predictions 
                    WHERE model_type = ? AND created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY prediction_date DESC
                """, (model_type.value, start_date.isoformat()))
                
                rows = await cursor.fetchall()
                
                trend_data = []
                for row in rows:
                    trend_data.append({
                        "date": row[0],
                        "average_confidence": row[1] or 0.0,
                        "average_accuracy": row[2] or 0.0,
                        "prediction_count": row[3] or 0
                    })
                
                return trend_data
                
        except Exception as e:
            logger.error(f"Failed to get prediction accuracy trend: {str(e)}")
            return []