"""
Data Processing Service - SQLite Job Repository
Clean Architecture v6.0.0

SQLite Implementation für Prediction Job Repository
"""
import aiosqlite
import json
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from domain.entities.prediction_entities import (
    PredictionJob, PredictionStatus, PredictionModelType, EnsemblePrediction
)
from domain.repositories.prediction_repository import IPredictionJobRepository

logger = structlog.get_logger(__name__)


class SQLitePredictionJobRepository(IPredictionJobRepository):
    """SQLite Implementation für Prediction Job Repository"""
    
    def __init__(self, db_path: str = "prediction_jobs.db"):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS prediction_jobs (
                    job_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    requested_models TEXT NOT NULL,
                    prediction_horizon_days INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    input_data_size INTEGER,
                    processing_duration_seconds REAL,
                    ensemble_prediction_id TEXT
                )
            """)
            
            # Create optimized indices
            await db.execute("CREATE INDEX IF NOT EXISTS idx_job_symbol ON prediction_jobs(symbol)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON prediction_jobs(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_job_created_at ON prediction_jobs(created_at)")
            
            await db.commit()

    async def create_job(self, job: PredictionJob) -> bool:
        """Create new prediction job"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO prediction_jobs 
                    (job_id, symbol, requested_models, prediction_horizon_days, status,
                     created_at, started_at, completed_at, error_message, input_data_size,
                     processing_duration_seconds, ensemble_prediction_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    job.symbol,
                    json.dumps([model.value for model in job.requested_models]),
                    job.prediction_horizon_days,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error_message,
                    job.input_data_size,
                    job.processing_duration_seconds,
                    job.ensemble_prediction.ensemble_id if job.ensemble_prediction else None
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to create job: {str(e)}")
            return False

    async def update_job(self, job: PredictionJob) -> bool:
        """Update existing prediction job"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE prediction_jobs 
                    SET status = ?, started_at = ?, completed_at = ?, error_message = ?,
                        input_data_size = ?, processing_duration_seconds = ?, ensemble_prediction_id = ?
                    WHERE job_id = ?
                """, (
                    job.status.value,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.error_message,
                    job.input_data_size,
                    job.processing_duration_seconds,
                    job.ensemble_prediction.ensemble_id if job.ensemble_prediction else None,
                    job.job_id
                ))
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update job: {str(e)}")
            return False

    async def get_job_by_id(self, job_id: str) -> Optional[PredictionJob]:
        """Get job by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT job_id, symbol, requested_models, prediction_horizon_days, status,
                           created_at, started_at, completed_at, error_message, input_data_size,
                           processing_duration_seconds, ensemble_prediction_id
                    FROM prediction_jobs 
                    WHERE job_id = ?
                """, (job_id,))
                
                row = await cursor.fetchone()
                
                if row:
                    requested_models = [PredictionModelType(model) for model in json.loads(row[2])]
                    
                    return PredictionJob(
                        job_id=row[0],
                        symbol=row[1],
                        requested_models=requested_models,
                        prediction_horizon_days=row[3],
                        status=PredictionStatus(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        started_at=datetime.fromisoformat(row[6]) if row[6] else None,
                        completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        error_message=row[8],
                        input_data_size=row[9],
                        processing_duration_seconds=row[10],
                        ensemble_prediction=None  # Would need to load from ensemble repository
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get job by ID: {str(e)}")
            return None

    async def get_jobs_by_status(self, status: PredictionStatus) -> List[PredictionJob]:
        """Get all jobs with specific status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT job_id
                    FROM prediction_jobs 
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status.value,))
                
                rows = await cursor.fetchall()
                
                jobs = []
                for row in rows:
                    job = await self.get_job_by_id(row[0])
                    if job:
                        jobs.append(job)
                
                return jobs
                
        except Exception as e:
            logger.error(f"Failed to get jobs by status: {str(e)}")
            return []

    async def get_jobs_by_symbol(self, symbol: str, limit: int = 20) -> List[PredictionJob]:
        """Get jobs for specific symbol"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT job_id
                    FROM prediction_jobs 
                    WHERE symbol = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (symbol, limit))
                
                rows = await cursor.fetchall()
                
                jobs = []
                for row in rows:
                    job = await self.get_job_by_id(row[0])
                    if job:
                        jobs.append(job)
                
                return jobs
                
        except Exception as e:
            logger.error(f"Failed to get jobs by symbol: {str(e)}")
            return []

    async def get_pending_jobs(self, limit: int = 10) -> List[PredictionJob]:
        """Get pending jobs ready for processing"""
        return await self.get_jobs_by_status(PredictionStatus.PENDING)

    async def get_expired_jobs(self, expiry_hours: int = 24) -> List[PredictionJob]:
        """Get expired jobs for cleanup"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=expiry_hours)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT job_id
                    FROM prediction_jobs 
                    WHERE status IN (?, ?) AND created_at < ?
                """, (PredictionStatus.PENDING.value, PredictionStatus.PROCESSING.value, cutoff_time.isoformat()))
                
                rows = await cursor.fetchall()
                
                jobs = []
                for row in rows:
                    job = await self.get_job_by_id(row[0])
                    if job:
                        jobs.append(job)
                
                return jobs
                
        except Exception as e:
            logger.error(f"Failed to get expired jobs: {str(e)}")
            return []

    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get overall job processing statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Status distribution
                cursor = await db.execute("""
                    SELECT status, COUNT(*) as count
                    FROM prediction_jobs 
                    GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}
                
                # Processing times
                cursor = await db.execute("""
                    SELECT 
                        AVG(processing_duration_seconds) as avg_processing_time,
                        MAX(processing_duration_seconds) as max_processing_time,
                        MIN(processing_duration_seconds) as min_processing_time
                    FROM prediction_jobs 
                    WHERE processing_duration_seconds IS NOT NULL
                """)
                
                time_stats = await cursor.fetchone()
                
                return {
                    "status_distribution": status_counts,
                    "processing_times": {
                        "average_seconds": time_stats[0] or 0.0,
                        "max_seconds": time_stats[1] or 0.0,
                        "min_seconds": time_stats[2] or 0.0
                    },
                    "total_jobs": sum(status_counts.values())
                }
                
        except Exception as e:
            logger.error(f"Failed to get job statistics: {str(e)}")
            return {}

    async def cleanup_completed_jobs(self, days_to_keep: int = 30) -> int:
        """Clean up old completed jobs, return number of deleted records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM prediction_jobs WHERE status = ? AND completed_at < ?",
                    (PredictionStatus.COMPLETED.value, cutoff_date.isoformat())
                )
                deleted_count = cursor.rowcount
                await db.commit()
                
                logger.info(f"Cleaned up {deleted_count} old completed jobs")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup completed jobs: {str(e)}")
            return 0