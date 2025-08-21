"""
Automated Model Retraining Scheduler v1.0.0
Vollautomatisches Retraining und Performance-Monitoring für alle ML-Modelle

Features:
- Scheduled Retraining (täglich, wöchentlich, monatlich)
- Performance Monitoring mit Auto-Retrain Triggers
- Model Performance Decay Detection
- Multi-Model koordiniertes Retraining
- Rollback bei Performance-Verschlechterung

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncpg
from dataclasses import dataclass
from enum import Enum

# Scheduler Dependencies
try:
    import schedule
    import threading
    import time
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

logger = logging.getLogger(__name__)

class RetrainingTrigger(Enum):
    """Verschiedene Trigger für automatisches Retraining"""
    SCHEDULED = "scheduled"
    PERFORMANCE_DECAY = "performance_decay"
    DATA_DRIFT = "data_drift"
    MANUAL = "manual"
    ERROR_RATE = "error_rate"
    STALENESS = "staleness"

@dataclass
class ModelRetrainingConfig:
    """Konfiguration für Model-Retraining"""
    model_type: str
    model_id: str
    retraining_frequency: str  # daily, weekly, monthly
    performance_threshold: float  # Minimum acceptable performance
    staleness_days: int  # Max days without retraining
    auto_retrain_enabled: bool = True
    rollback_enabled: bool = True
    max_retrain_attempts: int = 3

@dataclass 
class RetrainingJob:
    """Einzelner Retraining Job"""
    job_id: str
    model_type: str
    symbol: str
    trigger: RetrainingTrigger
    scheduled_time: datetime
    priority: int = 1  # 1=high, 2=medium, 3=low
    parameters: Dict[str, Any] = None

class AutomatedRetrainingScheduler:
    """
    Vollautomatischer Model Retraining Scheduler
    
    Koordiniert das Retraining aller ML-Modelle basierend auf:
    - Zeit-basierten Schedules 
    - Performance-Monitoring
    - Data Drift Detection
    - Error Rate Monitoring
    """
    
    def __init__(self, database_pool: asyncpg.Pool, ml_service_instance):
        self.database_pool = database_pool
        self.ml_service = ml_service_instance
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Scheduler State
        self.is_running = False
        self.scheduler_thread = None
        self.active_jobs = {}
        self.job_history = []
        
        # Default Retraining Configs
        self.default_configs = {
            "technical": ModelRetrainingConfig(
                model_type="technical",
                model_id="lstm_7d",
                retraining_frequency="weekly", 
                performance_threshold=0.15,  # Max MSE
                staleness_days=7,
                auto_retrain_enabled=True
            ),
            "sentiment": ModelRetrainingConfig(
                model_type="sentiment", 
                model_id="xgboost_7d",
                retraining_frequency="weekly",
                performance_threshold=0.2,
                staleness_days=7,
                auto_retrain_enabled=True
            ),
            "fundamental": ModelRetrainingConfig(
                model_type="fundamental",
                model_id="xgboost_7d", 
                retraining_frequency="monthly",
                performance_threshold=0.25,
                staleness_days=30,
                auto_retrain_enabled=True
            ),
            "meta": ModelRetrainingConfig(
                model_type="meta",
                model_id="lightgbm_ensemble",
                retraining_frequency="weekly",
                performance_threshold=0.12,
                staleness_days=14,
                auto_retrain_enabled=True
            )
        }
        
        # Multi-Horizon Configs
        for horizon in [7, 30, 150, 365]:
            self.default_configs[f"multi_horizon_{horizon}d"] = ModelRetrainingConfig(
                model_type="multi_horizon_lstm",
                model_id=f"lstm_{horizon}d",
                retraining_frequency="monthly" if horizon > 30 else "weekly",
                performance_threshold=0.18,
                staleness_days=horizon // 2,
                auto_retrain_enabled=True
            )
        
        if not SCHEDULER_AVAILABLE:
            self.logger.warning("Scheduler dependencies not available - limited functionality")
    
    async def initialize(self):
        """Initialisiert den Retraining Scheduler"""
        try:
            self.logger.info("Initializing Automated Retraining Scheduler")
            
            # Database Tables erstellen
            await self._create_retraining_tables()
            
            # Load persisted configs
            await self._load_retraining_configs()
            
            # Performance Baselines erstellen
            await self._establish_performance_baselines()
            
            self.logger.info("Automated Retraining Scheduler initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize retraining scheduler: {str(e)}")
            raise
    
    async def start_scheduler(self):
        """Startet den automatischen Scheduler"""
        try:
            if not SCHEDULER_AVAILABLE:
                self.logger.warning("Scheduler not available - running in monitoring-only mode")
                return
                
            if self.is_running:
                self.logger.warning("Scheduler already running")
                return
            
            self.logger.info("Starting Automated Retraining Scheduler")
            
            # Setup Schedules
            await self._setup_scheduled_jobs()
            
            # Start scheduler in background thread
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            self.logger.info("Automated Retraining Scheduler started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {str(e)}")
            raise
    
    async def stop_scheduler(self):
        """Stoppt den Scheduler gracefully"""
        if self.is_running:
            self.logger.info("Stopping Automated Retraining Scheduler")
            self.is_running = False
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=10)
            self.logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Background thread für Scheduler execution"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Scheduler error: {str(e)}")
                time.sleep(300)  # Wait 5 minutes on error
    
    async def _setup_scheduled_jobs(self):
        """Setup aller scheduled retraining jobs"""
        for model_type, config in self.default_configs.items():
            if not config.auto_retrain_enabled:
                continue
                
            # Schedule basierend auf Frequenz
            if config.retraining_frequency == "daily":
                schedule.every().day.at("02:00").do(
                    self._schedule_retraining_job, model_type, RetrainingTrigger.SCHEDULED
                )
            elif config.retraining_frequency == "weekly":
                schedule.every().sunday.at("01:00").do(
                    self._schedule_retraining_job, model_type, RetrainingTrigger.SCHEDULED
                )
            elif config.retraining_frequency == "monthly":
                schedule.every().day.at("00:30").do(
                    self._check_monthly_retraining, model_type
                )
        
        # Performance Monitoring (alle 6 Stunden)
        schedule.every(6).hours.do(self._performance_monitoring_job)
        
        # Staleness Check (täglich)
        schedule.every().day.at("03:00").do(self._staleness_monitoring_job)
        
        self.logger.info(f"Setup {len(schedule.jobs)} scheduled jobs")
    
    def _schedule_retraining_job(self, model_type: str, trigger: RetrainingTrigger):
        """Schedule ein Retraining Job (synchroner Wrapper)"""
        asyncio.create_task(self.schedule_retraining_job(model_type, trigger))
    
    def _performance_monitoring_job(self):
        """Performance Monitoring Job (synchroner Wrapper)"""
        asyncio.create_task(self.performance_monitoring_job())
    
    def _staleness_monitoring_job(self):
        """Staleness Monitoring Job (synchroner Wrapper)"""
        asyncio.create_task(self.staleness_monitoring_job())
    
    def _check_monthly_retraining(self, model_type: str):
        """Prüft ob Monthly Retraining fällig ist"""
        if datetime.now().day == 1:  # Erster des Monats
            self._schedule_retraining_job(model_type, RetrainingTrigger.SCHEDULED)
    
    async def schedule_retraining_job(self, model_type: str, trigger: RetrainingTrigger, 
                                    symbol: str = "AAPL", priority: int = 1) -> str:
        """
        Schedult einen Retraining Job
        
        Returns:
            Job ID
        """
        try:
            import uuid
            job_id = str(uuid.uuid4())
            
            job = RetrainingJob(
                job_id=job_id,
                model_type=model_type,
                symbol=symbol,
                trigger=trigger,
                scheduled_time=datetime.utcnow(),
                priority=priority
            )
            
            # Job in Queue
            self.active_jobs[job_id] = job
            
            # Persistiere Job
            await self._persist_retraining_job(job)
            
            # Execute Job asynchron
            asyncio.create_task(self._execute_retraining_job(job))
            
            self.logger.info(f"Scheduled retraining job {job_id} for {model_type} (trigger: {trigger.value})")
            return job_id
            
        except Exception as e:
            self.logger.error(f"Failed to schedule retraining job: {str(e)}")
            raise
    
    async def _execute_retraining_job(self, job: RetrainingJob):
        """Führt einen Retraining Job aus"""
        try:
            self.logger.info(f"Executing retraining job {job.job_id} for {job.model_type}")
            
            # Update Job Status
            await self._update_job_status(job.job_id, "running")
            
            # Pre-training validation
            current_performance = await self._get_current_model_performance(job.model_type)
            
            # Execute retraining basierend auf model type
            retrain_result = await self._execute_model_retraining(job)
            
            if retrain_result.get("error"):
                raise Exception(retrain_result["error"])
            
            # Post-training validation
            new_performance = retrain_result.get("model_metrics", {})
            
            # Performance Comparison
            should_rollback = await self._should_rollback_model(
                current_performance, new_performance, job.model_type
            )
            
            if should_rollback:
                self.logger.warning(f"Performance degradation detected for {job.model_type}, initiating rollback")
                await self._rollback_model(job.model_type)
                await self._update_job_status(job.job_id, "completed_with_rollback")
            else:
                self.logger.info(f"Retraining successful for {job.model_type}")
                await self._update_job_status(job.job_id, "completed_successfully")
            
            # Cleanup
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            
            self.job_history.append({
                "job_id": job.job_id,
                "model_type": job.model_type,
                "trigger": job.trigger.value,
                "completed_at": datetime.utcnow().isoformat(),
                "result": "rollback" if should_rollback else "success",
                "metrics": new_performance
            })
            
        except Exception as e:
            self.logger.error(f"Retraining job {job.job_id} failed: {str(e)}")
            await self._update_job_status(job.job_id, "failed")
            
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
    
    async def _execute_model_retraining(self, job: RetrainingJob) -> Dict[str, Any]:
        """Führt das eigentliche Model Retraining aus"""
        try:
            symbol = job.symbol
            model_type = job.model_type
            
            # Route zu entsprechendem Model Training
            if model_type == "technical":
                return await self.ml_service.lstm_model.train_model(symbol)
            elif model_type == "sentiment":
                return await self.ml_service.sentiment_model.train_model(symbol)
            elif model_type == "fundamental": 
                return await self.ml_service.fundamental_model.train_model(symbol)
            elif model_type == "meta":
                return await self.ml_service.meta_model.train_ensemble_model(symbol)
            elif model_type.startswith("multi_horizon"):
                # Extract horizon from model_type 
                horizon = int(model_type.split("_")[-1].replace("d", ""))
                if horizon in self.ml_service.multi_horizon_models:
                    return await self.ml_service.multi_horizon_models[horizon].train_model(symbol)
                else:
                    return {"error": f"Unknown horizon: {horizon}"}
            else:
                return {"error": f"Unknown model type: {model_type}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def performance_monitoring_job(self):
        """Überwacht Model Performance und triggert Retraining bei Decay"""
        try:
            self.logger.info("Starting performance monitoring job")
            
            for model_type, config in self.default_configs.items():
                try:
                    current_performance = await self._get_current_model_performance(model_type)
                    baseline_performance = await self._get_baseline_performance(model_type)
                    
                    if not current_performance or not baseline_performance:
                        continue
                    
                    # Performance Decay Detection
                    performance_ratio = current_performance.get("val_mse", 1.0) / baseline_performance.get("val_mse", 1.0)
                    
                    if performance_ratio > 1.5:  # 50% Performance-Verschlechterung
                        self.logger.warning(f"Performance decay detected for {model_type}: {performance_ratio:.2f}x worse")
                        await self.schedule_retraining_job(
                            model_type, RetrainingTrigger.PERFORMANCE_DECAY, priority=1
                        )
                    elif performance_ratio > 1.2:  # 20% Verschlechterung - Warning
                        self.logger.warning(f"Performance warning for {model_type}: {performance_ratio:.2f}x worse")
                
                except Exception as e:
                    self.logger.error(f"Performance monitoring failed for {model_type}: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Performance monitoring job failed: {str(e)}")
    
    async def staleness_monitoring_job(self):
        """Prüft Model Staleness und triggert Retraining"""
        try:
            self.logger.info("Starting staleness monitoring job")
            
            for model_type, config in self.default_configs.items():
                try:
                    last_training = await self._get_last_training_time(model_type)
                    if not last_training:
                        continue
                    
                    days_since_training = (datetime.utcnow() - last_training).days
                    
                    if days_since_training > config.staleness_days:
                        self.logger.warning(f"Model staleness detected for {model_type}: {days_since_training} days")
                        await self.schedule_retraining_job(
                            model_type, RetrainingTrigger.STALENESS, priority=2
                        )
                
                except Exception as e:
                    self.logger.error(f"Staleness monitoring failed for {model_type}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Staleness monitoring job failed: {str(e)}")
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Returns aktuellen Scheduler Status"""
        return {
            "is_running": self.is_running,
            "scheduler_available": SCHEDULER_AVAILABLE,
            "active_jobs": len(self.active_jobs),
            "scheduled_jobs": len(schedule.jobs) if SCHEDULER_AVAILABLE else 0,
            "job_history_count": len(self.job_history),
            "last_performance_check": "monitoring_active" if self.is_running else "stopped",
            "configurations": {
                model_type: {
                    "frequency": config.retraining_frequency,
                    "auto_retrain": config.auto_retrain_enabled,
                    "staleness_days": config.staleness_days,
                    "performance_threshold": config.performance_threshold
                } for model_type, config in self.default_configs.items()
            }
        }
    
    async def get_retraining_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns Retraining History"""
        try:
            async with self.database_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT job_id, model_type, trigger_type, status, 
                           created_at, completed_at, metrics
                    FROM retraining_jobs 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """, limit)
                
                return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get retraining history: {str(e)}")
            return []
    
    # Database Helper Methods
    
    async def _create_retraining_tables(self):
        """Erstellt Retraining Database Tables"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS retraining_jobs (
                        job_id UUID PRIMARY KEY,
                        model_type VARCHAR(50) NOT NULL,
                        symbol VARCHAR(10) NOT NULL,
                        trigger_type VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        priority INTEGER DEFAULT 1,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        started_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ,
                        metrics JSONB,
                        error_message TEXT
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS model_performance_baselines (
                        model_type VARCHAR(50) PRIMARY KEY,
                        baseline_metrics JSONB NOT NULL,
                        established_at TIMESTAMPTZ DEFAULT NOW(),
                        sample_count INTEGER DEFAULT 0
                    )
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_retraining_jobs_status 
                    ON retraining_jobs(status)
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_retraining_jobs_created 
                    ON retraining_jobs(created_at)
                """)
                
        except Exception as e:
            self.logger.error(f"Failed to create retraining tables: {str(e)}")
            raise
    
    async def _load_retraining_configs(self):
        """Lädt persisted retraining configs"""
        # Placeholder - könnte aus DB oder Config-File geladen werden
        pass
    
    async def _establish_performance_baselines(self):
        """Erstellt Performance Baselines für alle Modelle"""
        try:
            for model_type in self.default_configs.keys():
                current_perf = await self._get_current_model_performance(model_type)
                if current_perf:
                    await self._update_performance_baseline(model_type, current_perf)
        except Exception as e:
            self.logger.error(f"Failed to establish baselines: {str(e)}")
    
    async def _get_current_model_performance(self, model_type: str) -> Optional[Dict[str, float]]:
        """Holt aktuelle Model Performance"""
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT performance_metrics 
                    FROM ml_model_metadata 
                    WHERE model_type = $1 AND status = 'active'
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, model_type)
                
                if row and row['performance_metrics']:
                    return json.loads(row['performance_metrics'])
                return None
        except Exception as e:
            self.logger.error(f"Failed to get performance for {model_type}: {str(e)}")
            return None
    
    async def _get_baseline_performance(self, model_type: str) -> Optional[Dict[str, float]]:
        """Holt Baseline Performance"""
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT baseline_metrics 
                    FROM model_performance_baselines 
                    WHERE model_type = $1
                """, model_type)
                
                if row and row['baseline_metrics']:
                    return json.loads(row['baseline_metrics'])
                return None
        except Exception as e:
            self.logger.error(f"Failed to get baseline for {model_type}: {str(e)}")
            return None
    
    async def _update_performance_baseline(self, model_type: str, metrics: Dict[str, float]):
        """Updated Performance Baseline"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO model_performance_baselines (model_type, baseline_metrics)
                    VALUES ($1, $2)
                    ON CONFLICT (model_type) 
                    DO UPDATE SET 
                        baseline_metrics = $2,
                        established_at = NOW()
                """, model_type, json.dumps(metrics))
        except Exception as e:
            self.logger.error(f"Failed to update baseline for {model_type}: {str(e)}")
    
    async def _get_last_training_time(self, model_type: str) -> Optional[datetime]:
        """Holt letzte Training Zeit"""
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT created_at 
                    FROM ml_model_metadata 
                    WHERE model_type = $1 AND status = 'active'
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, model_type)
                
                return row['created_at'] if row else None
        except Exception as e:
            self.logger.error(f"Failed to get last training time for {model_type}: {str(e)}")
            return None
    
    async def _should_rollback_model(self, old_perf: Dict, new_perf: Dict, model_type: str) -> bool:
        """Entscheidet ob Model Rollback nötig ist"""
        if not old_perf or not new_perf:
            return False
        
        config = self.default_configs.get(model_type)
        if not config or not config.rollback_enabled:
            return False
        
        # Compare MSE - rollback wenn neue Performance schlechter ist
        old_mse = old_perf.get("val_mse", float('inf'))
        new_mse = new_perf.get("val_mse", float('inf'))
        
        return new_mse > old_mse * 1.1  # 10% Verschlechterung triggert Rollback
    
    async def _rollback_model(self, model_type: str):
        """Führt Model Rollback aus"""
        try:
            async with self.database_pool.acquire() as conn:
                # Deaktiviere aktuelles Modell
                await conn.execute("""
                    UPDATE ml_model_metadata 
                    SET status = 'deprecated' 
                    WHERE model_type = $1 AND status = 'active'
                """, model_type)
                
                # Aktiviere vorheriges Modell
                await conn.execute("""
                    UPDATE ml_model_metadata 
                    SET status = 'active' 
                    WHERE model_type = $1 AND status = 'deprecated'
                    AND created_at = (
                        SELECT MAX(created_at) 
                        FROM ml_model_metadata 
                        WHERE model_type = $1 AND status = 'deprecated'
                    )
                """, model_type)
                
            self.logger.info(f"Model rollback completed for {model_type}")
        except Exception as e:
            self.logger.error(f"Model rollback failed for {model_type}: {str(e)}")
    
    async def _persist_retraining_job(self, job: RetrainingJob):
        """Persistiert Retraining Job in DB"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO retraining_jobs 
                    (job_id, model_type, symbol, trigger_type, priority, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, job.job_id, job.model_type, job.symbol, 
                job.trigger.value, job.priority, job.scheduled_time)
        except Exception as e:
            self.logger.error(f"Failed to persist job {job.job_id}: {str(e)}")
    
    async def _update_job_status(self, job_id: str, status: str):
        """Updated Job Status in DB"""
        try:
            async with self.database_pool.acquire() as conn:
                if status == "running":
                    await conn.execute("""
                        UPDATE retraining_jobs 
                        SET status = $2, started_at = NOW()
                        WHERE job_id = $1
                    """, job_id, status)
                elif status.startswith("completed") or status == "failed":
                    await conn.execute("""
                        UPDATE retraining_jobs 
                        SET status = $2, completed_at = NOW()
                        WHERE job_id = $1
                    """, job_id, status)
                else:
                    await conn.execute("""
                        UPDATE retraining_jobs 
                        SET status = $2
                        WHERE job_id = $1
                    """, job_id, status)
        except Exception as e:
            self.logger.error(f"Failed to update job status {job_id}: {str(e)}")

# Export
__all__ = ['AutomatedRetrainingScheduler', 'RetrainingTrigger', 'ModelRetrainingConfig']