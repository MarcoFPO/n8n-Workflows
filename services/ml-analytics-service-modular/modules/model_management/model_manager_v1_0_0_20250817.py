#!/usr/bin/env python3
"""
Model Manager v1.0.0
ML-Modell-Lebenszyklus-Management für aktienanalyse-ökosystem

Integration: Event-Driven Model Management
Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import os
import pickle
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import uuid
from dataclasses import dataclass

import numpy as np
import tensorflow as tf
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Import shared modules
from shared.database import DatabaseConnection
from shared.event_bus import EventBusConnection
from config.ml_service_config import ML_SERVICE_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Model Metadata Information"""
    model_id: str
    model_type: str
    model_version: str
    horizon_days: int
    created_at: datetime
    performance_metrics: Dict[str, float]
    status: str  # 'training', 'active', 'deprecated', 'failed'
    file_path: str
    scaler_path: Optional[str] = None


@dataclass
class ModelPerformance:
    """Model Performance Metrics"""
    mae_score: float
    mse_score: float
    directional_accuracy: float
    r2_score: float
    sharpe_ratio: Optional[float] = None


class ModelManager:
    """
    Model Manager für ML-Modell-Lebenszyklus
    Verwaltet Training, Deployment und Performance-Tracking
    """
    
    def __init__(self, database: DatabaseConnection, event_bus: EventBusConnection):
        self.database = database
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Konfiguration
        self.model_config = ML_SERVICE_CONFIG['models']
        self.storage_config = ML_SERVICE_CONFIG['storage']
        self.performance_thresholds = ML_SERVICE_CONFIG['performance_thresholds']
        
        # Model Storage
        self.model_storage_path = Path(self.storage_config['model_storage_path'])
        self.backup_path = Path(self.storage_config['backup_path'])
        
        # In-Memory Model Cache
        self.active_models = {}  # {model_type}_{horizon} -> loaded model
        self.model_metadata_cache = {}
        
        # TensorFlow Configuration
        self._configure_tensorflow()
        
        self.is_initialized = False
    
    async def initialize(self):
        """Initialisiert Model Manager"""
        try:
            self.logger.info("Initializing Model Manager...")
            
            # Verzeichnisse erstellen
            await self._ensure_directories()
            
            # Aktive Modelle laden
            await self._load_active_models()
            
            # Model Registry synchronisieren
            await self._sync_model_registry()
            
            self.is_initialized = True
            self.logger.info("Model Manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Manager: {str(e)}")
            raise
    
    def _configure_tensorflow(self):
        """Konfiguriert TensorFlow Settings"""
        try:
            # GPU-Konfiguration
            if ML_SERVICE_CONFIG['tensorflow']['gpu_enabled']:
                gpus = tf.config.experimental.list_physical_devices('GPU')
                if gpus:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    self.logger.info(f"TensorFlow configured with {len(gpus)} GPU(s)")
                else:
                    self.logger.warning("No GPUs found, using CPU")
            
            # CPU-Threading
            tf.config.threading.set_intra_op_parallelism_threads(
                ML_SERVICE_CONFIG['tensorflow']['intra_op_parallelism']
            )
            tf.config.threading.set_inter_op_parallelism_threads(
                ML_SERVICE_CONFIG['tensorflow']['inter_op_parallelism']
            )
            
            # Logging
            tf.get_logger().setLevel(logging.ERROR)
            
        except Exception as e:
            self.logger.error(f"Failed to configure TensorFlow: {str(e)}")
    
    async def get_model_for_prediction(self, model_type: str, horizon_days: int) -> Tuple[Any, StandardScaler]:
        """
        Lädt aktives Modell für Prediction
        Gibt (model, scaler) zurück
        """
        model_key = f"{model_type}_{horizon_days}"
        
        # Aus Cache laden wenn verfügbar
        if model_key in self.active_models:
            return self.active_models[model_key]
        
        # Aktives Modell aus Datenbank laden
        metadata = await self._get_active_model_metadata(model_type, horizon_days)
        if not metadata:
            raise ValueError(f"No active model found for {model_type} {horizon_days}d")
        
        # Modell-Dateien laden
        model, scaler = await self._load_model_from_files(metadata)
        
        # In Cache speichern
        self.active_models[model_key] = (model, scaler)
        
        return model, scaler
    
    async def register_new_model(self, model_type: str, horizon_days: int, 
                                model_artifact: Any, scaler: StandardScaler,
                                performance_metrics: ModelPerformance,
                                training_config: Dict[str, Any]) -> str:
        """
        Registriert neues trainiertes Modell
        Führt Performance-Vergleich durch und aktiviert bei Verbesserung
        """
        try:
            model_id = str(uuid.uuid4())
            model_version = f"v{int(time.time())}"
            
            self.logger.info(f"Registering new model {model_type} {horizon_days}d: {model_id}")
            
            # Modell-Dateien speichern
            model_path, scaler_path = await self._save_model_artifacts(
                model_id, model_type, horizon_days, model_artifact, scaler
            )
            
            # Metadata in Datenbank speichern
            await self._save_model_metadata(
                model_id, model_type, model_version, horizon_days,
                performance_metrics, model_path, scaler_path, training_config
            )
            
            # Performance-Vergleich mit aktivem Modell
            should_deploy = await self._evaluate_model_for_deployment(
                model_type, horizon_days, performance_metrics
            )
            
            if should_deploy:
                await self._deploy_model(model_id, model_type, horizon_days)
                
                # ml.model.deployed Event publizieren
                await self._publish_model_deployed_event(
                    model_id, model_type, horizon_days, performance_metrics
                )
            
            return model_id
            
        except Exception as e:
            self.logger.error(f"Failed to register model: {str(e)}")
            raise
    
    async def _evaluate_model_for_deployment(self, model_type: str, horizon_days: int,
                                           new_performance: ModelPerformance) -> bool:
        """
        Bewertet ob neues Modell deployed werden soll
        Basiert auf Performance-Verbesserung
        """
        try:
            # Aktuelle Performance laden
            current_metadata = await self._get_active_model_metadata(model_type, horizon_days)
            
            if not current_metadata:
                self.logger.info(f"No active model for {model_type} {horizon_days}d, deploying new model")
                return True
            
            current_performance = current_metadata.performance_metrics
            improvement_threshold = ML_SERVICE_CONFIG['training']['deployment_improvement_threshold']
            
            # Hauptmetrik: Directional Accuracy
            current_da = current_performance.get('directional_accuracy', 0.0)
            new_da = new_performance.directional_accuracy
            
            da_improvement = (new_da - current_da)
            
            # Zusätzliche Metriken prüfen
            current_mae = current_performance.get('mae_score', float('inf'))
            mae_improvement = (current_mae - new_performance.mae_score) / current_mae if current_mae > 0 else 0
            
            # Deployment-Entscheidung
            should_deploy = (da_improvement > improvement_threshold or 
                           mae_improvement > improvement_threshold)
            
            self.logger.info(f"Model evaluation for {model_type} {horizon_days}d:")
            self.logger.info(f"  DA improvement: {da_improvement:.4f} (threshold: {improvement_threshold})")
            self.logger.info(f"  MAE improvement: {mae_improvement:.4f}")
            self.logger.info(f"  Deploy decision: {should_deploy}")
            
            return should_deploy
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate model for deployment: {str(e)}")
            return False
    
    async def _deploy_model(self, model_id: str, model_type: str, horizon_days: int):
        """Aktiviert neues Modell und deaktiviert vorheriges"""
        try:
            # Aktuelles aktives Modell deaktivieren
            await self.database.execute("""
                UPDATE ml_model_metadata 
                SET status = 'deprecated', updated_at = %s
                WHERE model_type = %s AND horizon_days = %s AND status = 'active'
            """, [datetime.utcnow(), model_type, horizon_days])
            
            # Neues Modell aktivieren
            await self.database.execute("""
                UPDATE ml_model_metadata 
                SET status = 'active', updated_at = %s
                WHERE model_id = %s
            """, [datetime.utcnow(), model_id])
            
            # Cache invalidieren
            model_key = f"{model_type}_{horizon_days}"
            if model_key in self.active_models:
                del self.active_models[model_key]
            
            self.logger.info(f"Model {model_id} deployed for {model_type} {horizon_days}d")
            
        except Exception as e:
            self.logger.error(f"Failed to deploy model {model_id}: {str(e)}")
            raise
    
    async def _save_model_artifacts(self, model_id: str, model_type: str, horizon_days: int,
                                   model: Any, scaler: StandardScaler) -> Tuple[str, str]:
        """Speichert Modell-Artefakte"""
        
        # Verzeichnis für dieses Modell
        model_dir = self.model_storage_path / model_type / f"{horizon_days}d" / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Modell speichern
        if model_type == 'technical':  # LSTM TensorFlow Model
            model_path = model_dir / "model.h5"
            model.save(str(model_path))
        else:  # XGBoost/Scikit-learn Models
            model_path = model_dir / "model.pkl"
            joblib.dump(model, model_path)
        
        # Scaler speichern
        scaler_path = model_dir / "scaler.pkl"
        joblib.dump(scaler, scaler_path)
        
        # Metadata-Datei
        metadata_path = model_dir / "metadata.json"
        metadata = {
            'model_id': model_id,
            'model_type': model_type,
            'horizon_days': horizon_days,
            'created_at': datetime.utcnow().isoformat(),
            'files': {
                'model': str(model_path),
                'scaler': str(scaler_path)
            }
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(model_path), str(scaler_path)
    
    async def _save_model_metadata(self, model_id: str, model_type: str, model_version: str,
                                  horizon_days: int, performance: ModelPerformance,
                                  model_path: str, scaler_path: str, training_config: Dict[str, Any]):
        """Speichert Model-Metadata in Datenbank"""
        
        query = """
            INSERT INTO ml_model_metadata (
                model_id, model_type, model_version, horizon_days,
                status, file_path, scaler_path, performance_metrics,
                training_config, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        performance_dict = {
            'mae_score': performance.mae_score,
            'mse_score': performance.mse_score,
            'directional_accuracy': performance.directional_accuracy,
            'r2_score': performance.r2_score,
            'sharpe_ratio': performance.sharpe_ratio
        }
        
        await self.database.execute(query, [
            model_id, model_type, model_version, horizon_days,
            'training', model_path, scaler_path, performance_dict,
            training_config, datetime.utcnow(), datetime.utcnow()
        ])
    
    async def _load_model_from_files(self, metadata: ModelMetadata) -> Tuple[Any, StandardScaler]:
        """Lädt Modell und Scaler von Dateien"""
        try:
            # Modell laden
            if metadata.model_type == 'technical':
                model = tf.keras.models.load_model(metadata.file_path)
            else:
                model = joblib.load(metadata.file_path)
            
            # Scaler laden
            scaler = joblib.load(metadata.scaler_path) if metadata.scaler_path else None
            
            return model, scaler
            
        except Exception as e:
            self.logger.error(f"Failed to load model {metadata.model_id}: {str(e)}")
            raise
    
    async def _get_active_model_metadata(self, model_type: str, horizon_days: int) -> Optional[ModelMetadata]:
        """Lädt aktive Model-Metadata aus Datenbank"""
        query = """
            SELECT model_id, model_type, model_version, horizon_days,
                   status, file_path, scaler_path, performance_metrics,
                   created_at
            FROM ml_model_metadata
            WHERE model_type = %s AND horizon_days = %s AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await self.database.fetch_one(query, [model_type, horizon_days])
        
        if not result:
            return None
        
        return ModelMetadata(
            model_id=result[0],
            model_type=result[1],
            model_version=result[2],
            horizon_days=result[3],
            status=result[4],
            file_path=result[5],
            scaler_path=result[6],
            performance_metrics=result[7],
            created_at=result[8]
        )
    
    async def _load_active_models(self):
        """Lädt alle aktiven Modelle in Memory-Cache"""
        try:
            query = """
                SELECT model_type, horizon_days, model_id, file_path, scaler_path
                FROM ml_model_metadata
                WHERE status = 'active'
            """
            
            results = await self.database.fetch_all(query)
            
            for row in results:
                model_type, horizon_days, model_id, file_path, scaler_path = row
                
                try:
                    # Modell-Metadaten für Cache laden
                    metadata = ModelMetadata(
                        model_id=model_id,
                        model_type=model_type,
                        model_version='',
                        horizon_days=horizon_days,
                        status='active',
                        file_path=file_path,
                        scaler_path=scaler_path,
                        performance_metrics={},
                        created_at=datetime.now()
                    )
                    
                    # Lazy loading - Modelle werden bei Bedarf geladen
                    model_key = f"{model_type}_{horizon_days}"
                    self.model_metadata_cache[model_key] = metadata
                    
                except Exception as e:
                    self.logger.error(f"Failed to cache model {model_id}: {str(e)}")
            
            self.logger.info(f"Cached metadata for {len(results)} active models")
            
        except Exception as e:
            self.logger.error(f"Failed to load active models: {str(e)}")
    
    async def _sync_model_registry(self):
        """Synchronisiert Model Registry mit Dateisystem"""
        try:
            # Prüfe ob alle registrierten Modelle existieren
            query = "SELECT model_id, file_path, scaler_path FROM ml_model_metadata WHERE status != 'deleted'"
            results = await self.database.fetch_all(query)
            
            missing_models = []
            for model_id, file_path, scaler_path in results:
                if not Path(file_path).exists():
                    missing_models.append(model_id)
                elif scaler_path and not Path(scaler_path).exists():
                    missing_models.append(model_id)
            
            if missing_models:
                self.logger.warning(f"Found {len(missing_models)} models with missing files")
                
                # Markiere als deleted
                for model_id in missing_models:
                    await self.database.execute(
                        "UPDATE ml_model_metadata SET status = 'deleted' WHERE model_id = %s",
                        [model_id]
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to sync model registry: {str(e)}")
    
    async def _ensure_directories(self):
        """Erstellt notwendige Verzeichnisse"""
        directories = [
            self.model_storage_path,
            self.backup_path,
            self.model_storage_path / 'technical',
            self.model_storage_path / 'sentiment',
            self.model_storage_path / 'fundamental'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def _publish_model_deployed_event(self, model_id: str, model_type: str, 
                                          horizon_days: int, performance: ModelPerformance):
        """Publiziert ml.model.deployed Event"""
        payload = {
            'model_id': model_id,
            'model_type': model_type,
            'horizon_days': horizon_days,
            'deployment_timestamp': datetime.utcnow().isoformat(),
            'performance_metrics': {
                'directional_accuracy': performance.directional_accuracy,
                'mae_score': performance.mae_score,
                'r2_score': performance.r2_score
            },
            'previous_model_deprecated': True
        }
        
        await self.event_bus.publish_ml_event('ml.model.deployed', payload)
    
    async def get_model_performance_summary(self) -> Dict[str, Any]:
        """Erstellt Performance-Summary aller aktiven Modelle"""
        query = """
            SELECT model_type, horizon_days, performance_metrics, created_at
            FROM ml_model_metadata
            WHERE status = 'active'
            ORDER BY model_type, horizon_days
        """
        
        results = await self.database.fetch_all(query)
        
        summary = {
            'total_active_models': len(results),
            'models_by_type': {},
            'performance_overview': {}
        }
        
        for model_type, horizon_days, metrics, created_at in results:
            key = f"{model_type}_{horizon_days}d"
            
            if model_type not in summary['models_by_type']:
                summary['models_by_type'][model_type] = []
            
            summary['models_by_type'][model_type].append({
                'horizon_days': horizon_days,
                'directional_accuracy': metrics.get('directional_accuracy', 0.0),
                'created_at': created_at.isoformat()
            })
            
            summary['performance_overview'][key] = {
                'directional_accuracy': metrics.get('directional_accuracy', 0.0),
                'mae_score': metrics.get('mae_score', 0.0),
                'r2_score': metrics.get('r2_score', 0.0)
            }
        
        return summary
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Model Manager"""
        try:
            # Aktive Modelle zählen
            active_models_count = len(self.model_metadata_cache)
            loaded_models_count = len(self.active_models)
            
            # Speicherplatz prüfen
            total_storage_mb = sum(f.stat().st_size for f in self.model_storage_path.rglob('*') if f.is_file()) / (1024 * 1024)
            
            # Model Registry Konsistenz
            registry_consistent = await self._check_registry_consistency()
            
            return {
                'status': 'healthy' if self.is_initialized and registry_consistent else 'warning',
                'initialized': self.is_initialized,
                'active_models_registered': active_models_count,
                'models_loaded_in_memory': loaded_models_count,
                'total_storage_mb': round(total_storage_mb, 1),
                'registry_consistent': registry_consistent,
                'tensorflow_available': tf.test.is_built_with_cuda() if ML_SERVICE_CONFIG['tensorflow']['gpu_enabled'] else True
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }
    
    async def _check_registry_consistency(self) -> bool:
        """Prüft Konsistenz zwischen Registry und Dateisystem"""
        try:
            query = "SELECT COUNT(*) FROM ml_model_metadata WHERE status = 'active'"
            result = await self.database.fetch_one(query)
            db_count = result[0] if result else 0
            
            cache_count = len(self.model_metadata_cache)
            
            return db_count == cache_count
            
        except Exception:
            return False
    
    async def shutdown(self):
        """Graceful Shutdown"""
        try:
            self.logger.info("Shutting down Model Manager...")
            
            # Memory-Cache leeren
            self.active_models.clear()
            self.model_metadata_cache.clear()
            
            # TensorFlow Session cleanup
            tf.keras.backend.clear_session()
            
            self.is_initialized = False
            self.logger.info("Model Manager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during Model Manager shutdown: {str(e)}")