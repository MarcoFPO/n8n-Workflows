#!/usr/bin/env python3
"""
Prediction Tracking Service - Repository Interfaces
Clean Architecture Domain Layer

CLEAN ARCHITECTURE - DOMAIN LAYER:
- Repository interfaces and contracts
- Port definitions for external services
- Data access abstractions

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..entities.prediction import Prediction, PerformanceMetrics, TimeframeType


class IPredictionRepository(ABC):
    """
    Prediction Repository Interface
    
    PORT INTERFACE: Data access abstraction for predictions
    REPOSITORY PATTERN: Encapsulates data access logic
    DEPENDENCY INVERSION: Application layer depends on this abstraction
    """
    
    @abstractmethod
    async def save_prediction(self, prediction: Prediction) -> bool:
        """
        Save prediction to storage
        
        Args:
            prediction: Prediction entity to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_prediction(self, prediction_id: str) -> Optional[Prediction]:
        """
        Retrieve prediction by ID
        
        Args:
            prediction_id: Unique prediction identifier
            
        Returns:
            Prediction entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_predictions_by_symbol(self, symbol: str, limit: int = 100) -> List[Prediction]:
        """
        Get predictions for a specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of predictions to return
            
        Returns:
            List of Prediction entities
        """
        pass
    
    @abstractmethod
    async def get_predictions_by_timeframe(self, timeframe: str, limit: int = 100) -> List[Prediction]:
        """
        Get predictions for a specific timeframe
        
        Args:
            timeframe: Prediction timeframe
            limit: Maximum number of predictions to return
            
        Returns:
            List of Prediction entities
        """
        pass
    
    @abstractmethod
    async def get_recent_predictions(self, days: int = 7, limit: int = 100) -> List[Prediction]:
        """
        Get recent predictions within specified days
        
        Args:
            days: Number of days to look back
            limit: Maximum number of predictions to return
            
        Returns:
            List of recent Prediction entities
        """
        pass
    
    @abstractmethod
    async def update_prediction_evaluation(
        self, 
        prediction_id: str, 
        actual_return: float, 
        evaluation_date: Optional[datetime] = None
    ) -> bool:
        """
        Update prediction with actual return data
        
        Args:
            prediction_id: Prediction identifier
            actual_return: Actual return achieved
            evaluation_date: When evaluation was performed
            
        Returns:
            True if updated successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_evaluated_predictions(self, timeframe: Optional[str] = None) -> List[Prediction]:
        """
        Get predictions that have been evaluated
        
        Args:
            timeframe: Optional timeframe filter
            
        Returns:
            List of evaluated Prediction entities
        """
        pass
    
    @abstractmethod
    async def get_pending_evaluations(self, days_old: int = 1) -> List[Prediction]:
        """
        Get predictions that need evaluation
        
        Args:
            days_old: Minimum age in days for pending evaluation
            
        Returns:
            List of Prediction entities pending evaluation
        """
        pass
    
    @abstractmethod
    async def delete_old_predictions(self, days_old: int = 365) -> int:
        """
        Delete old predictions
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of predictions deleted
        """
        pass
    
    @abstractmethod
    async def get_all_symbols(self) -> List[str]:
        """
        Get all symbols that have predictions
        
        Returns:
            List of unique symbols
        """
        pass
    
    @abstractmethod
    async def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get repository statistics
        
        Returns:
            Statistics dictionary
        """
        pass


class IPerformanceCalculator(ABC):
    """
    Performance Calculator Interface
    
    PORT INTERFACE: Performance metrics calculation
    DOMAIN SERVICE: Encapsulates performance calculation logic
    """
    
    @abstractmethod
    async def calculate_timeframe_performance(self, timeframe: str) -> PerformanceMetrics:
        """
        Calculate performance metrics for a timeframe
        
        Args:
            timeframe: Timeframe to analyze
            
        Returns:
            PerformanceMetrics value object
        """
        pass
    
    @abstractmethod
    async def calculate_symbol_performance(self, symbol: str) -> Dict[str, PerformanceMetrics]:
        """
        Calculate performance metrics for a symbol across all timeframes
        
        Args:
            symbol: Stock symbol to analyze
            
        Returns:
            Dictionary mapping timeframe to PerformanceMetrics
        """
        pass
    
    @abstractmethod
    async def calculate_overall_performance(self) -> Dict[str, PerformanceMetrics]:
        """
        Calculate overall performance across all timeframes
        
        Returns:
            Dictionary mapping timeframe to PerformanceMetrics
        """
        pass


class IPredictionProvider(ABC):
    """
    Prediction Provider Interface
    
    PORT INTERFACE: External prediction source integration
    ADAPTER PATTERN: Adapts external APIs to domain entities
    """
    
    @abstractmethod
    async def fetch_predictions(self, symbols: List[str], timeframe: str) -> List[Prediction]:
        """
        Fetch predictions from external source
        
        Args:
            symbols: List of symbols to get predictions for
            timeframe: Prediction timeframe
            
        Returns:
            List of Prediction entities
        """
        pass
    
    @abstractmethod
    async def fetch_actual_returns(self, predictions: List[Prediction]) -> Dict[str, float]:
        """
        Fetch actual return data for predictions
        
        Args:
            predictions: List of predictions to get actual data for
            
        Returns:
            Dictionary mapping prediction_id to actual_return
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if prediction provider is available
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_supported_symbols(self) -> List[str]:
        """
        Get list of supported symbols
        
        Returns:
            List of supported stock symbols
        """
        pass
    
    @abstractmethod
    async def get_supported_timeframes(self) -> List[str]:
        """
        Get list of supported timeframes
        
        Returns:
            List of supported timeframes
        """
        pass


class IPredictionCache(ABC):
    """
    Prediction Cache Interface
    
    PORT INTERFACE: Caching abstraction for predictions
    PERFORMANCE: Reduces database load through caching
    """
    
    @abstractmethod
    async def get_cached_predictions(self, key: str) -> Optional[List[Prediction]]:
        """
        Get cached predictions by key
        
        Args:
            key: Cache key
            
        Returns:
            List of cached Prediction entities or None
        """
        pass
    
    @abstractmethod
    async def cache_predictions(self, key: str, predictions: List[Prediction], ttl_minutes: int = 15) -> bool:
        """
        Cache predictions with TTL
        
        Args:
            key: Cache key
            predictions: List of predictions to cache
            ttl_minutes: Time to live in minutes
            
        Returns:
            True if cached successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def invalidate_cache(self, pattern: str) -> bool:
        """
        Invalidate cache entries matching pattern
        
        Args:
            pattern: Cache key pattern to invalidate
            
        Returns:
            True if invalidated, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics dictionary
        """
        pass