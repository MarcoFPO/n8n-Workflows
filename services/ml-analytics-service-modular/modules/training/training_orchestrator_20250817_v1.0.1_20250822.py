#!/usr/bin/env python3
"""
Training Orchestrator v1.0.0
Koordiniert und verwaltet das Training aller ML-Modelle

Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from modules.training.technical_lstm_trainer_v1_0_0_20250817 import TechnicalLSTMTrainer

logger = logging.getLogger(__name__)


class TrainingOrchestrator:
    """
    Zentrale Orchestrierung für ML-Model-Training
    """
    
    def __init__(self, database_connection, event_bus, model_manager):
        self.database_connection = database_connection
        self.event_bus = event_bus
        self.model_manager = model_manager
        
        # Trainer-Instanzen
        self.technical_trainer = TechnicalLSTMTrainer(
            database_connection=database_connection,
            model_storage_path="/opt/aktienanalyse-ökosystem/ml-models"
        )
        
        # Training-Status
        self.active_trainings: Dict[str, Dict] = {}
        
    async def start_training_session(self, 
                                   symbols: List[str], 
                                   model_types: List[str] = None,
                                   horizons: List[int] = None) -> str:
        """
        Startet eine komplette Training-Session für gegebene Symbole
        
        Args:
            symbols: Liste der zu trainierenden Symbole
            model_types: Optional - spezifische Modell-Typen
            horizons: Optional - spezifische Horizonte
            
        Returns:
            Training-Session-ID
        """
        session_id = str(uuid.uuid4())
        
        # Default-Werte
        if model_types is None:
            model_types = ['technical']
        if horizons is None:
            horizons = [7, 30, 150, 365]
            
        training_config = {
            'session_id': session_id,
            'symbols': symbols,
            'model_types': model_types,
            'horizons': horizons,
            'started_at': datetime.now(),
            'status': 'running',
            'completed_trainings': 0,
            'total_trainings': len(symbols) * len(model_types) * len(horizons),
            'errors': []
        }
        
        self.active_trainings[session_id] = training_config
        
        logger.info(f"Training session {session_id} started for {len(symbols)} symbols")
        
        # Event publizieren
        await self.event_bus.publish_event(
            event_type="ml.training.session.started",
            data={
                'session_id': session_id,
                'symbols': symbols,
                'model_types': model_types,
                'horizons': horizons,
                'total_trainings': training_config['total_trainings']
            }
        )
        
        # Training asynchron starten
        asyncio.create_task(self._execute_training_session(session_id))
        
        return session_id
    
    async def _execute_training_session(self, session_id: str):
        """
        Führt eine Training-Session aus
        """
        config = self.active_trainings[session_id]
        
        try:
            for symbol in config['symbols']:
                for model_type in config['model_types']:
                    for horizon in config['horizons']:
                        try:
                            await self._train_single_model(
                                session_id, symbol, model_type, horizon
                            )
                            config['completed_trainings'] += 1
                            
                        except Exception as e:
                            error_msg = f"Training failed for {symbol}-{model_type}-{horizon}d: {str(e)}"
                            logger.error(error_msg)
                            config['errors'].append(error_msg)
            
            # Session abschließen
            config['status'] = 'completed'
            config['completed_at'] = datetime.now()
            
            await self.event_bus.publish_event(
                event_type="ml.training.session.completed",
                data={
                    'session_id': session_id,
                    'completed_trainings': config['completed_trainings'],
                    'total_trainings': config['total_trainings'],
                    'errors': config['errors'],
                    'duration_seconds': (config['completed_at'] - config['started_at']).total_seconds()
                }
            )
            
            logger.info(f"Training session {session_id} completed: {config['completed_trainings']}/{config['total_trainings']} successful")
            
        except Exception as e:
            config['status'] = 'failed'
            config['error'] = str(e)
            logger.error(f"Training session {session_id} failed: {str(e)}")
            
            await self.event_bus.publish_event(
                event_type="ml.training.session.failed",
                data={
                    'session_id': session_id,
                    'error': str(e)
                }
            )
    
    async def _train_single_model(self, session_id: str, symbol: str, 
                                 model_type: str, horizon: int):
        """
        Trainiert ein einzelnes Modell
        """
        training_id = str(uuid.uuid4())
        
        logger.info(f"Starting training: {symbol}-{model_type}-{horizon}d (ID: {training_id})")
        
        # Training-Log in DB erstellen
        await self._log_training_start(training_id, symbol, model_type, horizon)
        
        try:
            if model_type == 'technical':
                model_result = await self.technical_trainer.train_model(
                    symbol=symbol,
                    horizon_days=horizon,
                    training_id=training_id
                )
                
                # Model in Registry registrieren
                await self.model_manager.register_model(
                    model_type=model_type,
                    horizon_days=horizon,
                    model_path=model_result['model_path'],
                    performance_metrics=model_result['performance_metrics'],
                    training_config=model_result['training_config']
                )
                
                # Training-Log aktualisieren
                await self._log_training_completion(
                    training_id, 
                    model_result['model_id'],
                    model_result['performance_metrics']
                )
                
                # Event publizieren
                await self.event_bus.publish_event(
                    event_type="ml.model.training.completed",
                    data={
                        'session_id': session_id,
                        'training_id': training_id,
                        'symbol': symbol,
                        'model_type': model_type,
                        'horizon_days': horizon,
                        'model_id': model_result['model_id'],
                        'performance_metrics': model_result['performance_metrics']
                    }
                )
                
                logger.info(f"Training completed: {symbol}-{model_type}-{horizon}d")
                
            else:
                raise NotImplementedError(f"Model type {model_type} not implemented yet")
                
        except Exception as e:
            await self._log_training_error(training_id, str(e))
            raise
    
    async def _log_training_start(self, training_id: str, symbol: str, 
                                 model_type: str, horizon: int):
        """
        Loggt Training-Start in Database
        """
        query = """
        INSERT INTO ml_training_logs 
        (training_id, model_type, horizon_days, training_symbol, status, training_config)
        VALUES ($1, $2, $3, $4, 'running', $5)
        """
        
        training_config = {
            'batch_size': 32,
            'epochs': 100,
            'early_stopping': True,
            'validation_split': 0.2
        }
        
        await self.database_connection.execute(
            query, training_id, model_type, horizon, symbol, training_config
        )
    
    async def _log_training_completion(self, training_id: str, model_id: str, 
                                     performance_metrics: Dict):
        """
        Loggt Training-Completion in Database
        """
        query = """
        UPDATE ml_training_logs 
        SET training_end = NOW(),
            training_duration_seconds = EXTRACT(EPOCH FROM (NOW() - training_start)),
            status = 'completed',
            model_id = $2,
            training_metrics = $3,
            validation_metrics = $4
        WHERE training_id = $1
        """
        
        await self.database_connection.execute(
            query, 
            training_id, 
            model_id, 
            performance_metrics.get('training_metrics', {}),
            performance_metrics.get('validation_metrics', {})
        )
    
    async def _log_training_error(self, training_id: str, error_message: str):
        """
        Loggt Training-Fehler in Database
        """
        query = """
        UPDATE ml_training_logs 
        SET training_end = NOW(),
            training_duration_seconds = EXTRACT(EPOCH FROM (NOW() - training_start)),
            status = 'failed',
            error_message = $2
        WHERE training_id = $1
        """
        
        await self.database_connection.execute(query, training_id, error_message)
    
    async def get_training_status(self, session_id: str) -> Optional[Dict]:
        """
        Gibt Status einer Training-Session zurück
        """
        return self.active_trainings.get(session_id)
    
    async def list_active_trainings(self) -> List[Dict]:
        """
        Listet alle aktiven Training-Sessions auf
        """
        return [
            {
                'session_id': session_id,
                'status': config['status'],
                'progress': f"{config['completed_trainings']}/{config['total_trainings']}",
                'started_at': config['started_at'].isoformat(),
                'symbols': config['symbols']
            }
            for session_id, config in self.active_trainings.items()
            if config['status'] == 'running'
        ]
    
    async def schedule_daily_training(self, symbols: List[str] = None):
        """
        Plant tägliches Training für Standard-Symbole
        """
        if symbols is None:
            # Default-Symbole für tägliches Training
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        logger.info(f"Scheduling daily training for {len(symbols)} symbols")
        
        session_id = await self.start_training_session(
            symbols=symbols,
            model_types=['technical'],
            horizons=[7, 30, 150, 365]
        )
        
        return session_id
    
    async def cleanup_old_training_sessions(self, max_age_hours: int = 24):
        """
        Räumt alte Training-Sessions auf
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        sessions_to_remove = []
        for session_id, config in self.active_trainings.items():
            if config['started_at'] < cutoff_time and config['status'] in ['completed', 'failed']:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.active_trainings[session_id]
            
        logger.info(f"Cleaned up {len(sessions_to_remove)} old training sessions")
    
    async def get_training_statistics(self) -> Dict:
        """
        Gibt Training-Statistiken zurück
        """
        query = """
        SELECT 
            model_type,
            status,
            COUNT(*) as count,
            AVG(training_duration_seconds) as avg_duration
        FROM ml_training_logs 
        WHERE training_start >= NOW() - INTERVAL '7 days'
        GROUP BY model_type, status
        ORDER BY model_type, status
        """
        
        rows = await self.database_connection.fetch(query)
        
        stats = {
            'last_7_days': [
                {
                    'model_type': row['model_type'],
                    'status': row['status'],
                    'count': row['count'],
                    'avg_duration_seconds': float(row['avg_duration']) if row['avg_duration'] else None
                }
                for row in rows
            ],
            'active_sessions': len([
                s for s in self.active_trainings.values() 
                if s['status'] == 'running'
            ])
        }
        
        return stats


# Utility functions für externes Training
async def trigger_manual_training(orchestrator: TrainingOrchestrator, 
                                 symbol: str, 
                                 model_type: str = 'technical',
                                 horizon: int = 7) -> str:
    """
    Triggert manuelles Training für ein einzelnes Symbol
    """
    session_id = await orchestrator.start_training_session(
        symbols=[symbol],
        model_types=[model_type],
        horizons=[horizon]
    )
    
    return session_id


async def trigger_bulk_training(orchestrator: TrainingOrchestrator,
                               symbols: List[str]) -> str:
    """
    Triggert Bulk-Training für mehrere Symbole
    """
    session_id = await orchestrator.start_training_session(
        symbols=symbols,
        model_types=['technical'],
        horizons=[7, 30, 150, 365]
    )
    
    return session_id