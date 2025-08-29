#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common Imports für alle Services - Minimale Implementation
Zentrale Import-Definitionen zur Code-Vereinfachung
Issue #65 Integration-Fix
"""

# Standard Library Imports
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

# FastAPI Core
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

# Async Database & Messaging
try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    import aio_pika
except ImportError:
    aio_pika = None

# Server & Logging
try:
    import uvicorn
except ImportError:
    uvicorn = None

try:
    import structlog
except ImportError:
    structlog = None

# Environment
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *args, **kwargs: None

# Data Processing (optional)
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pandas as pd
except ImportError:
    pd = None


# Common Response Models
@dataclass
class BaseResponse:
    """Base Response Model"""
    status: str
    message: str
    data: Any = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class HealthResponse:
    """Health Check Response"""
    service: str
    status: str
    components: Dict[str, str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.components is None:
            self.components = {}


@dataclass
class EventData:
    """Event Data Structure"""
    event_type: str
    payload: Dict[str, Any]
    timestamp: str = None
    source: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


# Service Configuration
@dataclass
class ServiceConfig:
    """Service Configuration"""
    name: str
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


# Event Handler Type
EventHandler = Callable[[EventData], Any]


# Module Registry Type
class ModuleRegistry(dict):
    """Module Registry für Service Module"""
    
    def register(self, name: str, module: Any):
        """Register Module"""
        self[name] = module
    
    def get_module(self, name: str):
        """Get Module"""
        return self.get(name)


# Utility Functions
def get_current_timestamp() -> str:
    """Get Current Timestamp ISO Format"""
    return datetime.utcnow().isoformat()


def format_timestamp(dt: datetime) -> str:
    """Format Timestamp"""
    return dt.isoformat()


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safe JSON Loads"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_get_env(key: str, default: str = "") -> str:
    """Safe Environment Variable Get"""
    return os.getenv(key, default)


# Constants
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_CORS_ORIGINS = ["*"]