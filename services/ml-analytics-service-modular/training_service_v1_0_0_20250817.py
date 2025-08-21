#!/usr/bin/env python3
"""
Training Service v1.0.0
Standalone Training Service für ML-Modelle

Führt Model-Training getrennt vom ML Analytics Service aus
Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import sys
import signal
from datetime import datetime
from typing import Dict, Any, Optional

# Import shared modules
from shared.database import DatabaseConnection
from shared.event_bus import EventBusConnection
from shared.service_base import ServiceBase
from config.ml_service_config import ML_SERVICE_CONFIG

# Import ML modules
from modules.feature_engineering.technical_feature_engine_v1_0_0_20250817 import TechnicalFeatureEngine
from modules.model_management.model_manager_v1_0_0_20250817 import ModelManager
from modules.training.technical_lstm_trainer_v1_0_0_20250817 import TechnicalLSTMTrainer

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingService(ServiceBase):
    """
    Training Service für ML-Modell-Training
    Separater Service für rechenintensive Training-Aufgaben
    """
    
    def __init__(self):
        super().__init__(
            service_name="ml-training",
            service_port=ML_SERVICE_CONFIG['service']['training_port']
        )
        
        # Core Dependencies
        self.database = None
        self.event_bus = None
        
        # ML Components
        self.feature_engine = None
        self.model_manager = None
        self.lstm_trainer = None
        
        # Training State
        self.active_training_jobs = {}
        self.training_queue = asyncio.Queue()
        self.is_training = False
        
        # Shutdown Event
        self.shutdown_event = asyncio.Event()
    
    async def initialize_service(self) -> bool:
        """Initialisiert Training Service"""
        try:
            logger.info("Initializing ML Training Service...")
            
            # Database Connection
            self.database = DatabaseConnection(ML_SERVICE_CONFIG['database'])
            await self.database.connect()
            
            # Event Bus Connection
            self.event_bus = EventBusConnection(ML_SERVICE_CONFIG['event_bus'])
            await self.event_bus.connect()
            
            # ML Components initialisieren
            await self._initialize_ml_components()
            
            # Event Handlers registrieren
            await self._register_event_handlers()
            
            # Training Queue Worker starten
            asyncio.create_task(self._training_queue_worker())
            
            logger.info("ML Training Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Training Service: {str(e)}")
            return False
    
    async def _initialize_ml_components(self):
        """Initialisiert ML-Komponenten"""
        
        # Feature Engine
        self.feature_engine = TechnicalFeatureEngine(self.database, self.event_bus)
        await self.feature_engine.initialize()
        
        # Model Manager
        self.model_manager = ModelManager(self.database, self.event_bus)
        await self.model_manager.initialize()
        
        # LSTM Trainer
        self.lstm_trainer = TechnicalLSTMTrainer(
            self.database, self.event_bus, self.feature_engine, self.model_manager
        )
        await self.lstm_trainer.initialize()
        
        logger.info("ML components initialized")
    
    async def _register_event_handlers(self):
        """Registriert Event-Handler"""
        
        # Training Request Handler
        await self.event_bus.subscribe(
            'ml.model.training.requested',
            self._handle_training_request
        )
        
        # Scheduled Training Handler
        await self.event_bus.subscribe(
            'ml.training.scheduled',
            self._handle_scheduled_training
        )
        
        logger.info("Event handlers registered")
    
    async def _handle_training_request(self, event_data: Dict[str, Any]):
        """Behandelt Training-Anfragen"""
        try:
            symbol = event_data.get('symbol')
            model_type = event_data.get('model_type', 'technical')
            horizon_days = event_data.get('horizon_days', 7)
            priority = event_data.get('priority', 'normal')
            
            if not symbol:
                logger.error("Training request missing symbol")
                return
            
            # Training Job zur Queue hinzufügen
            training_job = {
                'job_id': event_data.get('correlation_id', 'unknown'),
                'symbol': symbol,
                'model_type': model_type,
                'horizon_days': horizon_days,
                'priority': priority,
                'requested_at': datetime.utcnow(),
                'event_data': event_data
            }
            
            await self.training_queue.put(training_job)
            logger.info(f"Training job queued: {symbol} {model_type} {horizon_days}d")
            
        except Exception as e:
            logger.error(f"Failed to handle training request: {str(e)}")
    
    async def _handle_scheduled_training(self, event_data: Dict[str, Any]):
        """Behandelt geplante Training-Aufgaben"""
        try:
            # Batch-Training für alle aktiven Symbole
            symbols = event_data.get('symbols', ['AAPL'])  # Default für PoC
            model_types = event_data.get('model_types', ['technical'])
            horizons = event_data.get('horizons', [7, 30])
            
            for symbol in symbols:
                for model_type in model_types:
                    for horizon_days in horizons:
                        training_job = {
                            'job_id': f'scheduled_{symbol}_{model_type}_{horizon_days}',
                            'symbol': symbol,
                            'model_type': model_type,
                            'horizon_days': horizon_days,
                            'priority': 'scheduled',
                            'requested_at': datetime.utcnow(),
                            'event_data': event_data
                        }
                        
                        await self.training_queue.put(training_job)
            
            logger.info(f"Scheduled training jobs queued: {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to handle scheduled training: {str(e)}")
    
    async def _training_queue_worker(self):
        """Training Queue Worker - Arbeitet Training Jobs ab"""
        logger.info("Training queue worker started")
        
        while not self.shutdown_event.is_set():
            try:
                # Auf Training Job warten (mit Timeout)
                try:
                    training_job = await asyncio.wait_for(
                        self.training_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Training durchführen
                await self._execute_training_job(training_job)
                
                # Job als abgeschlossen markieren
                self.training_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in training queue worker: {str(e)}")
                await asyncio.sleep(1)
        
        logger.info("Training queue worker stopped")
    
    async def _execute_training_job(self, training_job: Dict[str, Any]):
        """Führt einzelnen Training Job aus"""
        job_id = training_job['job_id']
        symbol = training_job['symbol']
        model_type = training_job['model_type']
        horizon_days = training_job['horizon_days']
        
        logger.info(f"Executing training job {job_id}: {symbol} {model_type} {horizon_days}d")
        
        # Training als aktiv markieren
        self.active_training_jobs[job_id] = {
            'status': 'running',
            'started_at': datetime.utcnow(),
            'symbol': symbol,
            'model_type': model_type,
            'horizon_days': horizon_days
        }
        self.is_training = True
        
        try:
            if model_type == 'technical':
                # LSTM Training ausführen
                model_id = await self.lstm_trainer.train_model_for_symbol(symbol, horizon_days)
                
                # Training erfolgreich
                self.active_training_jobs[job_id].update({
                    'status': 'completed',
                    'completed_at': datetime.utcnow(),
                    'model_id': model_id
                })
                
                logger.info(f"Training job {job_id} completed successfully: {model_id}")
                
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
                
        except Exception as e:
            # Training fehlgeschlagen
            self.active_training_jobs[job_id].update({
                'status': 'failed',
                'completed_at': datetime.utcnow(),
                'error': str(e)
            })
            
            logger.error(f"Training job {job_id} failed: {str(e)}")
        
        finally:
            # Training Status zurücksetzen
            self.is_training = len([job for job in self.active_training_jobs.values() 
                                 if job['status'] == 'running']) > 0
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Service Status für Health Check"""
        try:
            # Active Jobs
            active_jobs = [job for job in self.active_training_jobs.values() 
                          if job['status'] == 'running']
            
            # Queue Size
            queue_size = self.training_queue.qsize()
            
            # Recent Jobs (letzte 10)
            recent_jobs = list(self.active_training_jobs.values())[-10:]
            
            return {
                'service_name': self.service_name,
                'status': 'healthy',
                'is_training': self.is_training,
                'active_training_jobs': len(active_jobs),
                'training_queue_size': queue_size,
                'total_jobs_processed': len(self.active_training_jobs),
                'recent_jobs': [
                    {
                        'symbol': job['symbol'],
                        'model_type': job['model_type'],
                        'horizon_days': job['horizon_days'],
                        'status': job['status'],
                        'started_at': job['started_at'].isoformat()
                    }
                    for job in recent_jobs
                ],
                'ml_components': {
                    'feature_engine': await self.feature_engine.health_check(),
                    'model_manager': await self.model_manager.health_check(),
                    'lstm_trainer': await self.lstm_trainer.health_check()
                }
            }
            
        except Exception as e:
            return {
                'service_name': self.service_name,
                'status': 'critical',
                'error': str(e)
            }
    
    async def trigger_manual_training(self, symbol: str, model_type: str = 'technical', 
                                    horizon_days: int = 7) -> str:
        """Triggert manuelles Training"""
        try:
            job_id = f'manual_{symbol}_{model_type}_{horizon_days}_{int(datetime.utcnow().timestamp())}'
            
            training_job = {
                'job_id': job_id,
                'symbol': symbol,
                'model_type': model_type,
                'horizon_days': horizon_days,
                'priority': 'manual',
                'requested_at': datetime.utcnow(),
                'event_data': {}
            }
            
            await self.training_queue.put(training_job)
            
            logger.info(f"Manual training triggered: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to trigger manual training: {str(e)}")
            raise
    
    async def shutdown_service(self):
        """Graceful Shutdown"""
        try:
            logger.info("Shutting down ML Training Service...")
            
            # Shutdown Event setzen
            self.shutdown_event.set()
            
            # Warten auf aktive Training Jobs
            if self.is_training:
                logger.info("Waiting for active training jobs to complete...")
                
                timeout = 300  # 5 Minuten Maximum
                start_time = datetime.utcnow()
                
                while self.is_training and (datetime.utcnow() - start_time).seconds < timeout:
                    await asyncio.sleep(5)
                
                if self.is_training:
                    logger.warning("Training jobs still running after timeout, forcing shutdown")
            
            # ML Components shutdown
            if self.lstm_trainer:
                await self.lstm_trainer.shutdown()
            
            if self.model_manager:
                await self.model_manager.shutdown()
            
            if self.feature_engine:
                await self.feature_engine.shutdown()
            
            # Connections schließen
            if self.event_bus:
                await self.event_bus.disconnect()
            
            if self.database:
                await self.database.disconnect()
            
            logger.info("ML Training Service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


async def main():
    """Main Training Service Entry Point"""
    
    # Signal Handler für Graceful Shutdown
    training_service = None
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if training_service:
            asyncio.create_task(training_service.shutdown_service())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Training Service starten
        training_service = TrainingService()
        
        if await training_service.initialize_service():
            logger.info("=== ML Training Service Started ===")
            logger.info(f"Service Port: {training_service.service_port}")
            logger.info(f"Process ID: {sys.argv[0]}")
            
            # Service am Leben halten
            try:
                await training_service.shutdown_event.wait()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
        else:
            logger.error("Failed to initialize Training Service")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Training Service error: {str(e)}")
        sys.exit(1)
    
    finally:
        if training_service:
            await training_service.shutdown_service()


if __name__ == "__main__":
    asyncio.run(main())