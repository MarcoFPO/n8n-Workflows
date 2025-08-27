#!/usr/bin/env python3
"""
ML Engine Domain Entity

Autor: Claude Code - Domain-Driven Design Specialist
Datum: 26. August 2025
Clean Architecture v6.0.0 - Domain Layer
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class MLEngineType(Enum):
    """ML Engine Types - Domain Value Object"""
    BASIC_FEATURE = "basic_feature"
    SENTIMENT_FEATURE = "sentiment_feature"  
    FUNDAMENTAL_FEATURE = "fundamental_feature"
    SIMPLE_LSTM = "simple_lstm"
    MULTI_HORIZON_LSTM = "multi_horizon_lstm"
    ENSEMBLE_MANAGER = "ensemble_manager"
    SENTIMENT_XGBOOST = "sentiment_xgboost"
    FUNDAMENTAL_XGBOOST = "fundamental_xgboost"
    META_LIGHTGBM = "meta_lightgbm"
    SYNTHETIC_TRAINER = "synthetic_trainer"
    STREAMING_ANALYTICS = "streaming_analytics"
    PORTFOLIO_RISK = "portfolio_risk"
    PORTFOLIO_OPTIMIZER = "portfolio_optimizer"
    MULTI_ASSET_CORRELATION = "multi_asset_correlation"
    GLOBAL_PORTFOLIO_OPTIMIZER = "global_portfolio_optimizer"
    MARKET_MICROSTRUCTURE = "market_microstructure"
    AI_OPTIONS_PRICING = "ai_options_pricing"
    EXOTIC_DERIVATIVES = "exotic_derivatives"
    ADVANCED_RISK = "advanced_risk"
    ESG_ANALYTICS = "esg_analytics"
    MARKET_INTELLIGENCE = "market_intelligence"
    QUANTUM_ML = "quantum_ml"


class MLEngineStatus(Enum):
    """ML Engine Status - Domain Value Object"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class PredictionHorizon(Enum):
    """Prediction Horizons - Domain Value Object"""
    INTRADAY = "intraday"        # 1 hour
    SHORT_TERM = "short_term"    # 1 week
    MEDIUM_TERM = "medium_term"  # 1 month
    LONG_TERM = "long_term"      # 3 months
    EXTENDED = "extended"        # 12 months


@dataclass(frozen=True)
class MLEngineConfiguration:
    """ML Engine Configuration Value Object"""
    engine_type: MLEngineType
    supported_horizons: List[PredictionHorizon]
    requires_database: bool = True
    requires_model_storage: bool = True
    initialization_priority: int = 1  # 1=highest, 10=lowest
    
    def __post_init__(self):
        """Domain validation rules"""
        if self.initialization_priority < 1 or self.initialization_priority > 10:
            raise ValueError("Initialization priority must be between 1 and 10")
        
        if not self.supported_horizons:
            raise ValueError("Engine must support at least one prediction horizon")


@dataclass
class MLEngineHealth:
    """ML Engine Health Status - Domain Entity"""
    engine_type: MLEngineType
    status: MLEngineStatus
    last_check: datetime
    error_message: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_healthy(self) -> bool:
        """Business Rule: Check if engine is healthy"""
        return self.status == MLEngineStatus.READY
    
    def needs_attention(self) -> bool:
        """Business Rule: Check if engine needs attention"""
        return self.status in [MLEngineStatus.ERROR, MLEngineStatus.MAINTENANCE]
    
    def can_handle_predictions(self) -> bool:
        """Business Rule: Check if engine can handle prediction requests"""
        return self.status == MLEngineStatus.READY


@dataclass
class MLEngine:
    """ML Engine Domain Entity - Rich Domain Model"""
    engine_type: MLEngineType
    configuration: MLEngineConfiguration
    health: MLEngineHealth
    initialized_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    def can_handle_horizon(self, horizon: PredictionHorizon) -> bool:
        """Business Rule: Check if engine supports given prediction horizon"""
        return horizon in self.configuration.supported_horizons
    
    def is_ready_for_predictions(self) -> bool:
        """Business Rule: Check if engine is ready for prediction requests"""
        return (
            self.health.is_healthy() and 
            self.initialized_at is not None
        )
    
    def needs_initialization(self) -> bool:
        """Business Rule: Check if engine needs initialization"""
        return (
            self.health.status == MLEngineStatus.NOT_INITIALIZED or
            self.initialized_at is None
        )
    
    def record_usage(self) -> None:
        """Domain Action: Record engine usage"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()
    
    def mark_as_initialized(self) -> None:
        """Domain Action: Mark engine as successfully initialized"""
        self.initialized_at = datetime.utcnow()
        self.health.status = MLEngineStatus.READY
        self.health.last_check = datetime.utcnow()
        self.health.error_message = None
    
    def mark_as_error(self, error_message: str) -> None:
        """Domain Action: Mark engine as having error"""
        self.health.status = MLEngineStatus.ERROR
        self.health.error_message = error_message
        self.health.last_check = datetime.utcnow()
    
    def update_performance_metrics(self, metrics: Dict[str, float]) -> None:
        """Domain Action: Update engine performance metrics"""
        self.health.performance_metrics.update(metrics)
        self.health.last_check = datetime.utcnow()


@dataclass
class MLEngineRegistry:
    """ML Engine Registry - Aggregate Root"""
    engines: Dict[MLEngineType, MLEngine] = field(default_factory=dict)
    
    def register_engine(self, engine: MLEngine) -> None:
        """Domain Action: Register new ML engine"""
        if engine.engine_type in self.engines:
            raise ValueError(f"Engine {engine.engine_type.value} already registered")
        
        self.engines[engine.engine_type] = engine
    
    def get_engine(self, engine_type: MLEngineType) -> Optional[MLEngine]:
        """Domain Query: Get engine by type"""
        return self.engines.get(engine_type)
    
    def get_healthy_engines(self) -> List[MLEngine]:
        """Domain Query: Get all healthy engines"""
        return [
            engine for engine in self.engines.values() 
            if engine.health.is_healthy()
        ]
    
    def get_engines_for_horizon(self, horizon: PredictionHorizon) -> List[MLEngine]:
        """Domain Query: Get engines that support given horizon"""
        return [
            engine for engine in self.engines.values()
            if engine.can_handle_horizon(horizon) and engine.is_ready_for_predictions()
        ]
    
    def get_engine_count_by_status(self) -> Dict[MLEngineStatus, int]:
        """Domain Query: Get engine count by status"""
        status_counts = {status: 0 for status in MLEngineStatus}
        
        for engine in self.engines.values():
            status_counts[engine.health.status] += 1
            
        return status_counts
    
    def has_critical_issues(self) -> bool:
        """Business Rule: Check if registry has critical issues"""
        error_count = sum(
            1 for engine in self.engines.values()
            if engine.health.status == MLEngineStatus.ERROR
        )
        
        total_engines = len(self.engines)
        
        # Critical if more than 25% of engines have errors
        return error_count > (total_engines * 0.25)
    
    def get_initialization_order(self) -> List[MLEngine]:
        """Business Rule: Get engines sorted by initialization priority"""
        return sorted(
            self.engines.values(),
            key=lambda engine: engine.configuration.initialization_priority
        )