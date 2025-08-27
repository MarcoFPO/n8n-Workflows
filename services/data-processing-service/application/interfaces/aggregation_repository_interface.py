"""
Data Processing Service - Aggregation Repository Interface
Timeframe-Specific Aggregation v7.1 - Clean Architecture Application Layer

Repository Interface für Aggregation Persistence (Dependency Inversion Principle)
SOLID Principles: Interface Segregation, Dependency Inversion, Single Responsibility
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from ...domain.entities.aggregated_prediction import AggregatedPrediction


class AggregationRepositoryInterface(ABC):
    """
    Repository Interface für Aggregation Persistence
    
    SOLID PRINCIPLES:
    - Interface Segregation: Spezifische Methods für Aggregation Operations
    - Dependency Inversion: Application Layer hängt von Interface ab, nicht Implementation
    - Single Responsibility: Ausschließlich Aggregation Persistence
    """
    
    @abstractmethod
    async def store_aggregation_result(self, aggregation: AggregatedPrediction) -> bool:
        """
        Store Aggregation Result in Persistence Layer
        
        Args:
            aggregation: AggregatedPrediction Domain Entity
            
        Returns:
            bool: Success status
            
        Raises:
            PersistenceException: Wenn Storage fehlschlägt
        """
        pass
    
    @abstractmethod
    async def get_cached_aggregation(self, 
                                   symbol: str, 
                                   timeframe: str, 
                                   max_age_minutes: int = 60) -> Optional[AggregatedPrediction]:
        """
        Get Cached Aggregation Result
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe (1W, 1M, etc.)
            max_age_minutes: Maximum age in minutes für validity
            
        Returns:
            Optional[AggregatedPrediction]: Cached aggregation oder None
        """
        pass
    
    @abstractmethod
    async def get_aggregations_for_timeframe(self,
                                           timeframe: str,
                                           limit: int = 15,
                                           symbol_filter: Optional[str] = None) -> List[AggregatedPrediction]:
        """
        Get All Valid Aggregations für Timeframe
        
        Args:
            timeframe: Requested timeframe
            limit: Maximum number of results
            symbol_filter: Optional symbol filter
            
        Returns:
            List[AggregatedPrediction]: Valid aggregation results
        """
        pass
    
    @abstractmethod
    async def update_aggregation_expiry(self, 
                                      aggregation_id: str, 
                                      new_expiry: datetime) -> bool:
        """
        Update Aggregation Expiry Timestamp
        
        Args:
            aggregation_id: Unique aggregation identifier
            new_expiry: New expiry timestamp
            
        Returns:
            bool: Update success status
        """
        pass
    
    @abstractmethod
    async def delete_expired_aggregations(self, cutoff_timestamp: datetime) -> int:
        """
        Delete Expired Aggregations für Cleanup
        
        Args:
            cutoff_timestamp: Timestamp für expiry cutoff
            
        Returns:
            int: Number of deleted aggregations
        """
        pass
    
    @abstractmethod
    async def get_aggregation_statistics(self, 
                                       timeframe: Optional[str] = None,
                                       since_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get Aggregation Statistics für Monitoring
        
        Args:
            timeframe: Optional timeframe filter
            since_date: Optional date filter
            
        Returns:
            Dict[str, Any]: Statistics summary
        """
        pass
    
    @abstractmethod
    async def bulk_store_aggregations(self, aggregations: List[AggregatedPrediction]) -> Dict[str, Any]:
        """
        Bulk Store Multiple Aggregations für Performance
        
        Args:
            aggregations: List of aggregations zu store
            
        Returns:
            Dict[str, Any]: Bulk operation results
            
        Raises:
            BulkOperationException: Wenn bulk operation fehlschlägt
        """
        pass
    
    @abstractmethod
    async def get_quality_report_data(self, 
                                    symbol: str, 
                                    timeframe: str, 
                                    history_days: int = 30) -> Dict[str, Any]:
        """
        Get Historical Quality Data für Quality Reports
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            history_days: Days of history zu include
            
        Returns:
            Dict[str, Any]: Historical quality data
        """
        pass
    
    @abstractmethod
    async def find_aggregations_by_quality_threshold(self,
                                                   timeframe: str,
                                                   min_quality_score: float) -> List[AggregatedPrediction]:
        """
        Find Aggregations Above Quality Threshold
        
        Args:
            timeframe: Target timeframe
            min_quality_score: Minimum required quality score (0.0-1.0)
            
        Returns:
            List[AggregatedPrediction]: High-quality aggregations
        """
        pass
    
    @abstractmethod
    async def update_aggregation_cache_status(self,
                                            aggregation_id: str,
                                            cache_hit: bool,
                                            cache_key: str) -> bool:
        """
        Update Cache Status Metadata für Monitoring
        
        Args:
            aggregation_id: Aggregation identifier
            cache_hit: Whether this was a cache hit
            cache_key: Cache key used
            
        Returns:
            bool: Update success status
        """
        pass