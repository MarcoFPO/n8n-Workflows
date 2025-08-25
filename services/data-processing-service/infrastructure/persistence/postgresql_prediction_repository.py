"""
Data Processing Service - PostgreSQL Repository Implementations
Clean Architecture v6.1.0 - PostgreSQL Migration

PostgreSQL-based Implementation für Prediction Data Persistence mit Database Manager
Migration von 3 SQLite Repositories zu unified PostgreSQL Implementation
"""
import json
import structlog
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from decimal import Decimal

# Database Manager Import - Direct Path Import
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConnectionManager

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


class PostgreSQLStockDataRepository(IStockDataRepository):
    """PostgreSQL Implementation für Stock Data Repository"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._initialized_at = datetime.now(timezone.utc)

    async def initialize_schema(self) -> bool:
        """Initialize stock data schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create stock_data table
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS stock_data (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        date DATE NOT NULL,
                        open_price DECIMAL(10,4) NOT NULL,
                        high_price DECIMAL(10,4) NOT NULL,
                        low_price DECIMAL(10,4) NOT NULL,
                        close_price DECIMAL(10,4) NOT NULL,
                        volume BIGINT NOT NULL,
                        adjusted_close DECIMAL(10,4),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(symbol, date)
                    )
                """)
                
                # Create indexes for performance
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stock_data_symbol 
                    ON stock_data (symbol)
                """)
                
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stock_data_date 
                    ON stock_data (date)
                """)
                
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_date 
                    ON stock_data (symbol, date)
                """)
                
                logger.info("Stock data schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error("Failed to initialize stock data schema", error=str(e))
            return False

    async def store_stock_data(self, data: StockData) -> bool:
        """Store stock data"""
        try:
            async with self.db_manager.get_connection() as connection:
                await connection.execute("""
                    INSERT INTO stock_data (
                        symbol, date, open_price, high_price, low_price,
                        close_price, volume, adjusted_close, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        adjusted_close = EXCLUDED.adjusted_close
                """,
                    data.symbol,
                    data.date,
                    data.open_price,
                    data.high_price,
                    data.low_price,
                    data.close_price,
                    data.volume,
                    data.adjusted_close,
                    data.timestamp
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error("Failed to store stock data", symbol=data.symbol, error=str(e))
            return False

    async def get_stock_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[StockData]:
        """Get stock data for symbol in date range"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch("""
                    SELECT * FROM stock_data 
                    WHERE symbol = $1 AND date >= $2 AND date <= $3
                    ORDER BY date ASC
                """, symbol, start_date.date(), end_date.date())
                
                return [self._row_to_stock_data(row) for row in rows]
                
        except Exception as e:
            logger.error("Failed to get stock data", symbol=symbol, error=str(e))
            return []

    async def get_latest_stock_data(self, symbol: str) -> Optional[StockData]:
        """Get latest stock data for symbol"""
        try:
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow("""
                    SELECT * FROM stock_data 
                    WHERE symbol = $1 
                    ORDER BY date DESC 
                    LIMIT 1
                """, symbol)
                
                return self._row_to_stock_data(row) if row else None
                
        except Exception as e:
            logger.error("Failed to get latest stock data", symbol=symbol, error=str(e))
            return None

    async def get_symbols_with_data(self) -> List[str]:
        """Get all symbols that have data"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch("""
                    SELECT DISTINCT symbol FROM stock_data ORDER BY symbol
                """)
                
                return [row['symbol'] for row in rows]
                
        except Exception as e:
            logger.error("Failed to get symbols", error=str(e))
            return []

    def _row_to_stock_data(self, row) -> StockData:
        """Convert database row to StockData entity"""
        return StockData(
            symbol=row['symbol'],
            date=datetime.combine(row['date'], datetime.min.time()),
            open_price=float(row['open_price']),
            high_price=float(row['high_price']),
            low_price=float(row['low_price']),
            close_price=float(row['close_price']),
            volume=row['volume'],
            adjusted_close=float(row['adjusted_close']) if row['adjusted_close'] else None,
            timestamp=row['created_at']
        )


class PostgreSQLEnsemblePredictionRepository(IEnsemblePredictionRepository):
    """PostgreSQL Implementation für Ensemble Prediction Repository"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._initialized_at = datetime.now(timezone.utc)

    async def initialize_schema(self) -> bool:
        """Initialize ensemble predictions schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create ensemble_predictions table
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS ensemble_predictions (
                        id SERIAL PRIMARY KEY,
                        prediction_id VARCHAR(255) UNIQUE NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        predicted_price DECIMAL(10,4) NOT NULL,
                        confidence_score DECIMAL(5,4) NOT NULL,
                        prediction_horizon VARCHAR(50) NOT NULL,
                        ensemble_strategy VARCHAR(50) NOT NULL,
                        model_weights JSONB NOT NULL,
                        individual_predictions JSONB NOT NULL,
                        prediction_date TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                
                # Create indexes
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ensemble_predictions_symbol 
                    ON ensemble_predictions (symbol)
                """)
                
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ensemble_predictions_date 
                    ON ensemble_predictions (prediction_date)
                """)
                
                logger.info("Ensemble predictions schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error("Failed to initialize ensemble predictions schema", error=str(e))
            return False

    async def store_ensemble_prediction(self, prediction: EnsemblePrediction) -> bool:
        """Store ensemble prediction"""
        try:
            async with self.db_manager.get_connection() as connection:
                model_weights_json = json.dumps({k: v for k, v in prediction.model_weights.items()})
                individual_predictions_json = json.dumps([
                    {
                        'model_type': pred.model_type.value,
                        'predicted_price': float(pred.predicted_price),
                        'confidence_score': float(pred.confidence_score),
                        'prediction_date': pred.prediction_date.isoformat()
                    }
                    for pred in prediction.individual_predictions
                ])
                
                await connection.execute("""
                    INSERT INTO ensemble_predictions (
                        prediction_id, symbol, predicted_price, confidence_score,
                        prediction_horizon, ensemble_strategy, model_weights,
                        individual_predictions, prediction_date, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (prediction_id) DO UPDATE SET
                        predicted_price = EXCLUDED.predicted_price,
                        confidence_score = EXCLUDED.confidence_score,
                        model_weights = EXCLUDED.model_weights,
                        individual_predictions = EXCLUDED.individual_predictions
                """,
                    prediction.prediction_id,
                    prediction.symbol,
                    prediction.predicted_price,
                    prediction.confidence_score,
                    prediction.prediction_horizon,
                    prediction.ensemble_strategy.value,
                    model_weights_json,
                    individual_predictions_json,
                    prediction.prediction_date,
                    prediction.created_at
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error("Failed to store ensemble prediction", prediction_id=prediction.prediction_id, error=str(e))
            return False

    async def get_ensemble_predictions(self, symbol: str, limit: int = 100) -> List[EnsemblePrediction]:
        """Get ensemble predictions for symbol"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch("""
                    SELECT * FROM ensemble_predictions 
                    WHERE symbol = $1 
                    ORDER BY prediction_date DESC 
                    LIMIT $2
                """, symbol, limit)
                
                return [self._row_to_ensemble_prediction(row) for row in rows]
                
        except Exception as e:
            logger.error("Failed to get ensemble predictions", symbol=symbol, error=str(e))
            return []

    async def get_latest_ensemble_prediction(self, symbol: str) -> Optional[EnsemblePrediction]:
        """Get latest ensemble prediction for symbol"""
        try:
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow("""
                    SELECT * FROM ensemble_predictions 
                    WHERE symbol = $1 
                    ORDER BY prediction_date DESC 
                    LIMIT 1
                """, symbol)
                
                return self._row_to_ensemble_prediction(row) if row else None
                
        except Exception as e:
            logger.error("Failed to get latest ensemble prediction", symbol=symbol, error=str(e))
            return None

    def _row_to_ensemble_prediction(self, row) -> EnsemblePrediction:
        """Convert database row to EnsemblePrediction entity"""
        model_weights = {PredictionModelType(k): v for k, v in json.loads(row['model_weights']).items()}
        
        individual_predictions = []
        for pred_data in json.loads(row['individual_predictions']):
            individual_predictions.append(ModelPrediction(
                prediction_id=f"{row['prediction_id']}_individual_{pred_data['model_type']}",
                symbol=row['symbol'],
                model_type=PredictionModelType(pred_data['model_type']),
                predicted_price=pred_data['predicted_price'],
                confidence_score=pred_data['confidence_score'],
                prediction_date=datetime.fromisoformat(pred_data['prediction_date']),
                created_at=row['created_at']
            ))
        
        return EnsemblePrediction(
            prediction_id=row['prediction_id'],
            symbol=row['symbol'],
            predicted_price=float(row['predicted_price']),
            confidence_score=float(row['confidence_score']),
            prediction_horizon=row['prediction_horizon'],
            ensemble_strategy=EnsembleWeightStrategy(row['ensemble_strategy']),
            model_weights=model_weights,
            individual_predictions=individual_predictions,
            prediction_date=row['prediction_date'],
            created_at=row['created_at']
        )


class PostgreSQLPredictionJobRepository(IPredictionJobRepository):
    """PostgreSQL Implementation für Prediction Job Repository"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._initialized_at = datetime.now(timezone.utc)

    async def initialize_schema(self) -> bool:
        """Initialize prediction jobs schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create prediction_jobs table
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_jobs (
                        id SERIAL PRIMARY KEY,
                        job_id VARCHAR(255) UNIQUE NOT NULL,
                        job_type VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        symbols JSONB NOT NULL,
                        model_types JSONB NOT NULL,
                        parameters JSONB,
                        progress_percentage INTEGER NOT NULL DEFAULT 0,
                        results_count INTEGER NOT NULL DEFAULT 0,
                        error_message TEXT,
                        started_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                
                # Create indexes
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_prediction_jobs_status 
                    ON prediction_jobs (status)
                """)
                
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_prediction_jobs_type 
                    ON prediction_jobs (job_type)
                """)
                
                await connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_prediction_jobs_created 
                    ON prediction_jobs (created_at)
                """)
                
                logger.info("Prediction jobs schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error("Failed to initialize prediction jobs schema", error=str(e))
            return False

    async def store_job(self, job: PredictionJob) -> bool:
        """Store prediction job"""
        try:
            async with self.db_manager.get_connection() as connection:
                symbols_json = json.dumps(job.symbols)
                model_types_json = json.dumps([mt.value for mt in job.model_types])
                parameters_json = json.dumps(job.parameters) if job.parameters else None
                
                await connection.execute("""
                    INSERT INTO prediction_jobs (
                        job_id, job_type, status, symbols, model_types,
                        parameters, progress_percentage, results_count,
                        error_message, started_at, completed_at, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (job_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        progress_percentage = EXCLUDED.progress_percentage,
                        results_count = EXCLUDED.results_count,
                        error_message = EXCLUDED.error_message,
                        completed_at = EXCLUDED.completed_at
                """,
                    job.job_id,
                    job.job_type,
                    job.status.value,
                    symbols_json,
                    model_types_json,
                    parameters_json,
                    job.progress_percentage,
                    job.results_count,
                    job.error_message,
                    job.started_at,
                    job.completed_at,
                    job.created_at
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error("Failed to store prediction job", job_id=job.job_id, error=str(e))
            return False

    async def get_job(self, job_id: str) -> Optional[PredictionJob]:
        """Get prediction job by ID"""
        try:
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow("""
                    SELECT * FROM prediction_jobs WHERE job_id = $1
                """, job_id)
                
                return self._row_to_job(row) if row else None
                
        except Exception as e:
            logger.error("Failed to get prediction job", job_id=job_id, error=str(e))
            return None

    async def get_jobs_by_status(self, status: PredictionStatus, limit: int = 100) -> List[PredictionJob]:
        """Get jobs by status"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch("""
                    SELECT * FROM prediction_jobs 
                    WHERE status = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, status.value, limit)
                
                return [self._row_to_job(row) for row in rows]
                
        except Exception as e:
            logger.error("Failed to get jobs by status", status=status.value, error=str(e))
            return []

    async def get_recent_jobs(self, hours: int = 24, limit: int = 100) -> List[PredictionJob]:
        """Get recent jobs"""
        try:
            async with self.db_manager.get_connection() as connection:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                rows = await connection.fetch("""
                    SELECT * FROM prediction_jobs 
                    WHERE created_at >= $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, cutoff_time, limit)
                
                return [self._row_to_job(row) for row in rows]
                
        except Exception as e:
            logger.error("Failed to get recent jobs", error=str(e))
            return []

    def _row_to_job(self, row) -> PredictionJob:
        """Convert database row to PredictionJob entity"""
        symbols = json.loads(row['symbols'])
        model_types = [PredictionModelType(mt) for mt in json.loads(row['model_types'])]
        parameters = json.loads(row['parameters']) if row['parameters'] else {}
        
        return PredictionJob(
            job_id=row['job_id'],
            job_type=row['job_type'],
            status=PredictionStatus(row['status']),
            symbols=symbols,
            model_types=model_types,
            parameters=parameters,
            progress_percentage=row['progress_percentage'],
            results_count=row['results_count'],
            error_message=row['error_message'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            created_at=row['created_at']
        )