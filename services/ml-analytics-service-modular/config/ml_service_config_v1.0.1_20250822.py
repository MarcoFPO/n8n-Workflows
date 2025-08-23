"""
ML Service Configuration v1.0.0
Konfiguration für ML Analytics Service

Autor: Claude Code
Datum: 17. August 2025
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MODEL_STORAGE_PATH = os.getenv('ML_MODEL_STORAGE_PATH', str(PROJECT_ROOT / "ml-models"))
LOGS_PATH = PROJECT_ROOT / "logs" / "ml-analytics"

# Ensure directories exist
Path(MODEL_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
LOGS_PATH.mkdir(parents=True, exist_ok=True)

ML_SERVICE_CONFIG = {
    'service': {
        'name': 'ml-analytics',
        'version': '1.0.0',
        'port': int(os.getenv('ML_SERVICE_PORT', 8021)),
        'host': os.getenv('ML_SERVICE_HOST', '0.0.0.0'),
        'workers': int(os.getenv('ML_SERVICE_WORKERS', 1)),
        'max_connections': int(os.getenv('ML_MAX_CONNECTIONS', 100)),
        'debug': os.getenv('ML_DEBUG_MODE', 'false').lower() == 'true'
    },
    
    'database': {
        'host': os.getenv('ML_DATABASE_HOST', 'localhost'),
        'port': int(os.getenv('ML_DATABASE_PORT', 5432)),
        'name': os.getenv('ML_DATABASE_NAME', 'aktienanalyse'),
        'user': os.getenv('ML_DATABASE_USER', 'ml_service'),
        'password': os.getenv('ML_DATABASE_PASSWORD', 'ml_service_secure_2025'),
        'url': os.getenv('ML_DATABASE_URL', 'postgresql://ml_service:ml_service_secure_2025@localhost/aktienanalyse'),
        'pool_size': int(os.getenv('ML_DB_POOL_SIZE', 10)),
        'max_overflow': int(os.getenv('ML_DB_MAX_OVERFLOW', 20)),
        'pool_timeout': int(os.getenv('ML_DB_POOL_TIMEOUT', 30)),
        'min_connections': int(os.getenv('ML_DB_MIN_CONNECTIONS', 5)),
        'max_connections': int(os.getenv('ML_DB_MAX_CONNECTIONS', 20))
    },
    
    'event_bus': {
        'redis_url': os.getenv('EVENT_BUS_REDIS_URL', 'redis://localhost:6379/2'),
        'consumer_group': os.getenv('EVENT_BUS_CONSUMER_GROUP', 'ml-analytics-group'),
        'streams': ['ml-features-stream', 'ml-predictions-stream', 'ml-training-stream'],
        'batch_size': int(os.getenv('ML_EVENT_BATCH_SIZE', 10)),
        'timeout_ms': int(os.getenv('ML_EVENT_TIMEOUT_MS', 5000))
    },
    
    'storage': {
        'model_storage_path': MODEL_STORAGE_PATH,
        'logs_path': str(LOGS_PATH),
        'cache_path': str(PROJECT_ROOT / "cache" / "ml"),
        'backup_path': str(Path(MODEL_STORAGE_PATH) / "backups")
    },
    
    'models': {
        'technical': {
            'architecture': 'lstm',
            'input_sequence_length': int(os.getenv('ML_TECH_SEQUENCE_LENGTH', 60)),
            'feature_count': int(os.getenv('ML_TECH_FEATURE_COUNT', 25)),
            'lstm_units': [128, 64, 32],
            'dropout_rate': float(os.getenv('ML_TECH_DROPOUT', 0.2)),
            'epochs': int(os.getenv('ML_TECH_EPOCHS', 100)),
            'batch_size': int(os.getenv('ML_TECH_BATCH_SIZE', 32)),
            'validation_split': float(os.getenv('ML_TECH_VAL_SPLIT', 0.15)),
            'early_stopping_patience': int(os.getenv('ML_TECH_PATIENCE', 10))
        },
        'sentiment': {
            'architecture': 'xgboost',
            'n_estimators': int(os.getenv('ML_SENT_N_ESTIMATORS', 1000)),
            'max_depth': int(os.getenv('ML_SENT_MAX_DEPTH', 6)),
            'learning_rate': float(os.getenv('ML_SENT_LEARNING_RATE', 0.1)),
            'validation_split': float(os.getenv('ML_SENT_VAL_SPLIT', 0.15)),
            'early_stopping_rounds': int(os.getenv('ML_SENT_EARLY_STOP', 50))
        },
        'fundamental': {
            'architecture': 'xgboost',
            'n_estimators': int(os.getenv('ML_FUND_N_ESTIMATORS', 500)),
            'max_depth': int(os.getenv('ML_FUND_MAX_DEPTH', 8)),
            'learning_rate': float(os.getenv('ML_FUND_LEARNING_RATE', 0.05)),
            'validation_split': float(os.getenv('ML_FUND_VAL_SPLIT', 0.15)),
            'early_stopping_rounds': int(os.getenv('ML_FUND_EARLY_STOP', 30))
        },
        'ensemble': {
            'method': 'weighted_average',  # or 'meta_model'
            'weight_update_frequency_days': int(os.getenv('ML_ENSEMBLE_WEIGHT_UPDATE_DAYS', 7)),
            'min_confidence_threshold': float(os.getenv('ML_ENSEMBLE_MIN_CONFIDENCE', 0.4))
        }
    },
    
    'performance_thresholds': {
        'directional_accuracy': {
            '7d': float(os.getenv('ML_DA_THRESHOLD_7D', 0.60)),
            '30d': float(os.getenv('ML_DA_THRESHOLD_30D', 0.58)),
            '150d': float(os.getenv('ML_DA_THRESHOLD_150D', 0.55)),
            '365d': float(os.getenv('ML_DA_THRESHOLD_365D', 0.52))
        },
        'confidence_score_min': float(os.getenv('ML_CONFIDENCE_MIN', 0.40)),
        'prediction_freshness_hours': int(os.getenv('ML_PREDICTION_FRESHNESS_HOURS', 6)),
        'model_retrain_frequency_days': int(os.getenv('ML_RETRAIN_FREQUENCY_DAYS', 7)),
        'performance_degradation_threshold': float(os.getenv('ML_PERFORMANCE_DEGRADATION_THRESHOLD', 0.05))
    },
    
    'caching': {
        'feature_cache_ttl_hours': int(os.getenv('ML_FEATURE_CACHE_TTL_HOURS', 2)),
        'prediction_cache_ttl_hours': int(os.getenv('ML_PREDICTION_CACHE_TTL_HOURS', 6)),
        'model_cache_max_size': int(os.getenv('ML_MODEL_CACHE_MAX_SIZE', 10)),
        'redis_cache_url': os.getenv('ML_REDIS_CACHE_URL', 'redis://localhost:6379/3')
    },
    
    'training': {
        'data_retention_days': int(os.getenv('ML_TRAINING_DATA_RETENTION_DAYS', 730)),
        'min_training_samples': int(os.getenv('ML_MIN_TRAINING_SAMPLES', 1000)),
        'max_training_duration_hours': int(os.getenv('ML_MAX_TRAINING_DURATION_HOURS', 6)),
        'auto_deployment_enabled': os.getenv('ML_AUTO_DEPLOYMENT', 'true').lower() == 'true',
        'deployment_improvement_threshold': float(os.getenv('ML_DEPLOYMENT_IMPROVEMENT_THRESHOLD', 0.02))
    },
    
    'features': {
        'technical_indicators': {
            'momentum': ['RSI_14', 'MACD_12_26_9', 'STOCH_14_3'],
            'trend': ['SMA_20', 'SMA_50', 'SMA_200', 'EMA_20', 'EMA_50'],
            'volatility': ['BB_UPPER_20', 'BB_LOWER_20', 'ATR_14'],
            'volume': ['VOLUME_SMA_20', 'VOLUME_RATIO'],
            'price_action': ['DAILY_RETURN', 'WEEKLY_RETURN', 'HIGH_LOW_RATIO']
        },
        'quality_thresholds': {
            'min_quality_score': float(os.getenv('ML_MIN_FEATURE_QUALITY', 0.8)),
            'max_missing_values_ratio': float(os.getenv('ML_MAX_MISSING_VALUES_RATIO', 0.1)),
            'outlier_detection_threshold': float(os.getenv('ML_OUTLIER_THRESHOLD', 3.0))
        }
    },
    
    'api': {
        'max_batch_predictions': int(os.getenv('ML_MAX_BATCH_PREDICTIONS', 50)),
        'request_timeout_seconds': int(os.getenv('ML_REQUEST_TIMEOUT', 30)),
        'rate_limit_per_minute': int(os.getenv('ML_RATE_LIMIT_PER_MINUTE', 1000)),
        'cors_origins': os.getenv('ML_CORS_ORIGINS', 'http://localhost:8080,https://10.1.1.174').split(',')
    },
    
    'monitoring': {
        'health_check_interval_seconds': int(os.getenv('ML_HEALTH_CHECK_INTERVAL', 30)),
        'metrics_enabled': os.getenv('ML_METRICS_ENABLED', 'true').lower() == 'true',
        'metrics_port': int(os.getenv('ML_METRICS_PORT', 9090)),
        'alert_webhook_url': os.getenv('ML_ALERT_WEBHOOK_URL', 'http://localhost:8015/api/alerts/ml'),
        'log_level': os.getenv('ML_LOG_LEVEL', 'INFO')
    },
    
    'security': {
        'api_key_required': os.getenv('ML_API_KEY_REQUIRED', 'false').lower() == 'true',
        'api_key': os.getenv('ML_API_KEY', ''),
        'cors_enabled': os.getenv('ML_CORS_ENABLED', 'true').lower() == 'true',
        'rate_limiting_enabled': os.getenv('ML_RATE_LIMITING_ENABLED', 'true').lower() == 'true'
    },
    
    'tensorflow': {
        'gpu_enabled': os.getenv('CUDA_VISIBLE_DEVICES', '0') != '',
        'memory_growth': os.getenv('TF_FORCE_GPU_ALLOW_GROWTH', 'true').lower() == 'true',
        'log_level': int(os.getenv('TF_CPP_MIN_LOG_LEVEL', 2)),
        'intra_op_parallelism': int(os.getenv('ML_TENSORFLOW_INTRA_OP_PARALLELISM', 4)),
        'inter_op_parallelism': int(os.getenv('ML_TENSORFLOW_INTER_OP_PARALLELISM', 2))
    }
}

# Validation der kritischen Konfigurationen
def validate_config():
    """Validiert die ML Service Konfiguration"""
    errors = []
    
    # Port Validation
    if not (1024 <= ML_SERVICE_CONFIG['service']['port'] <= 65535):
        errors.append(f"Invalid port: {ML_SERVICE_CONFIG['service']['port']}")
    
    # Database URL Validation
    if not ML_SERVICE_CONFIG['database']['url'].startswith(('postgresql://', 'sqlite://')):
        errors.append("Invalid database URL format")
    
    # Model Storage Path Validation
    model_path = Path(ML_SERVICE_CONFIG['storage']['model_storage_path'])
    if not model_path.exists():
        try:
            model_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create model storage path: {e}")
    
    # Performance Thresholds Validation
    for horizon, threshold in ML_SERVICE_CONFIG['performance_thresholds']['directional_accuracy'].items():
        if not (0.0 <= threshold <= 1.0):
            errors.append(f"Invalid directional accuracy threshold for {horizon}: {threshold}")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

# Auto-validate on import
validate_config()

# Export für einfache Imports
__all__ = ['ML_SERVICE_CONFIG', 'validate_config']