#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Libraries für aktienanalyse-ökosystem
Zentralisiert gemeinsame Komponenten und eliminiert Code-Duplikation
"""

# Import der wichtigsten Klassen für einfache Nutzung
from .common_imports import *
from .security_config import SecurityConfig, PrivateSecurityMiddleware
from .logging_config import setup_logging, LoggerMixin
from .service_base import BaseService, ModularService, DatabaseMixin, EventBusMixin

# Version des Shared-Moduls
__version__ = "1.0.0"

# Export der wichtigsten Komponenten
__all__ = [
    # Basis-Klassen
    'BaseService',
    'ModularService', 
    'DatabaseMixin',
    'EventBusMixin',
    'LoggerMixin',
    
    # Security
    'SecurityConfig',
    'PrivateSecurityMiddleware',
    
    # Logging
    'setup_logging',
    
    # Alle common_imports (über *)
    'datetime', 'timedelta', 'Dict', 'Any', 'List', 'Optional', 'Union',
    'FastAPI', 'HTTPException', 'Request', 'BackgroundTasks', 'Depends',
    'CORSMiddleware', 'JSONResponse', 'HTMLResponse', 'StaticFiles',
    'BaseModel', 'Field', 'validator',
    'asyncpg', 'redis', 'aio_pika',
    'uvicorn', 'structlog', 'load_dotenv', 'np', 'pd',
    'BaseResponse', 'HealthResponse', 'EventData',
    'ServiceConfig', 'EventHandler', 'ModuleRegistry',
    'get_current_timestamp', 'format_timestamp', 'safe_json_loads', 'safe_get_env',
    'DEFAULT_PORT', 'DEFAULT_HOST', 'DEFAULT_LOG_LEVEL', 'DEFAULT_CORS_ORIGINS'
]