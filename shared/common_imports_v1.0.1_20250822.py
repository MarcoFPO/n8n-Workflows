#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common Imports für aktienanalyse-ökosystem
Eliminiert Code-Duplikation durch zentrale Import-Sammlung
"""

# Standard Library Imports (am häufigsten dupliziert)
import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Third-Party Imports (häufig dupliziert)
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
import uvicorn
import structlog
from dotenv import load_dotenv

# Database Imports
import asyncpg
import redis
import aio_pika

# Utilities
import numpy as np
import pandas as pd

# Load environment variables
load_dotenv('/opt/aktienanalyse-ökosystem/.env')

# Common Pydantic Base Models
class BaseResponse(BaseModel):
    """Base Response Model für alle API-Responses"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None

class HealthResponse(BaseResponse):
    """Standard Health Check Response"""
    service: str
    version: str = "1.0.0"
    uptime_seconds: Optional[float] = None
    database_connected: bool = False
    event_bus_connected: bool = False

class EventData(BaseModel):
    """Standard Event Data Structure"""
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

# Common Type Definitions
ServiceConfig = Dict[str, Any]
EventHandler = callable
ModuleRegistry = Dict[str, Any]

# Utility Functions
def get_current_timestamp() -> datetime:
    """Standard Timestamp-Funktion"""
    return datetime.now()

def format_timestamp(dt: datetime) -> str:
    """Standard Timestamp-Formatierung"""
    return dt.isoformat()

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Sichere JSON-Deserialisierung"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_get_env(key: str, default: str = "", cast_type: type = str):
    """Sichere Environment Variable Getter"""
    value = os.getenv(key, default)
    try:
        return cast_type(value)
    except (ValueError, TypeError):
        return cast_type(default) if default else None

# Common Constants
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_CORS_ORIGINS = ["https://10.1.1.174", "http://10.1.1.174:8005"]

# Export frequently used items
__all__ = [
    # Standard Library
    'os', 'sys', 'asyncio', 'json', 'datetime', 'timedelta', 'Path',
    
    # Typing
    'Dict', 'Any', 'List', 'Optional', 'Union',
    
    # FastAPI
    'FastAPI', 'HTTPException', 'Request', 'BackgroundTasks', 'Depends',
    'CORSMiddleware', 'JSONResponse', 'HTMLResponse', 'StaticFiles',
    
    # Pydantic
    'BaseModel', 'Field', 'validator',
    
    # Database
    'asyncpg', 'redis', 'aio_pika',
    
    # Utilities
    'uvicorn', 'structlog', 'load_dotenv', 'np', 'pd',
    
    # Common Models
    'BaseResponse', 'HealthResponse', 'EventData',
    
    # Types
    'ServiceConfig', 'EventHandler', 'ModuleRegistry',
    
    # Functions
    'get_current_timestamp', 'format_timestamp', 'safe_json_loads', 'safe_get_env',
    
    # Constants
    'DEFAULT_PORT', 'DEFAULT_HOST', 'DEFAULT_LOG_LEVEL', 'DEFAULT_CORS_ORIGINS'
]