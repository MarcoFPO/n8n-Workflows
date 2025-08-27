"""
Data Processing Service - Prediction Repository Interface
Timeframe-Specific Aggregation v7.1 - Clean Architecture Application Layer

Repository Interface für Raw Prediction Data Access (Dependency Inversion Principle)
SOLID Principles: Interface Segregation, Dependency Inversion, Single Responsibility
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date
from decimal import Decimal


class PredictionRepositoryInterface(ABC):
    """
    Repository Interface für Raw Prediction Data Access
    
    SOLID PRINCIPLES:
    - Interface Segregation: Spezifische Methods für Prediction Data Operations
    - Dependency Inversion: Application Layer hängt von Interface ab, nicht Implementation
    - Single Responsibility: Ausschließlich Raw Prediction Data Access
    """
    
    @abstractmethod
    async def fetch_predictions_for_timeframe(self,
                                            start_date: date,
                                            end_date: date,
                                            symbol_filter: Optional[str] = None,
                                            limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch Raw Prediction Data für Timeframe Aggregation
        
        Args:
            start_date: Start date für data collection
            end_date: End date für data collection
            symbol_filter: Optional symbol filter (e.g., 'AAPL')
            limit: Maximum number of predictions to return
            
        Returns:
            List[Dict[str, Any]]: Raw prediction data
            
        Expected Dictionary Structure:
            {
                'symbol': str,
                'company_name': str,
                'predicted_profit': float/Decimal,
                'confidence_level': float,
                'forecast_period_days': int,
                'recommendation': str,
                'created_at': datetime,
                'timestamp': datetime,
                'source_model': str,
                'data_quality_score': float
            }
        """
        pass
    
    @abstractmethod
    async def get_prediction_count_by_symbol(self,
                                           start_date: date,
                                           end_date: date,
                                           symbol: str) -> int:
        """
        Get Count of Predictions für Symbol in Timeframe
        
        Args:
            start_date: Start date
            end_date: End date  
            symbol: Stock symbol
            
        Returns:
            int: Number of predictions available
        """
        pass
    
    @abstractmethod
    async def get_available_symbols_for_timeframe(self,
                                                start_date: date,
                                                end_date: date,
                                                min_prediction_count: int = 5) -> List[str]:
        """
        Get Available Symbols mit Sufficient Prediction Data
        
        Args:
            start_date: Start date
            end_date: End date
            min_prediction_count: Minimum required predictions per symbol
            
        Returns:
            List[str]: Available symbols with sufficient data
        """
        pass
    
    @abstractmethod
    async def get_prediction_data_quality_summary(self,
                                                start_date: date,
                                                end_date: date,
                                                symbol_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Data Quality Summary für Predictions
        
        Args:
            start_date: Start date
            end_date: End date
            symbol_filter: Optional symbol filter
            
        Returns:
            Dict[str, Any]: Data quality summary containing:
                - total_predictions: int
                - unique_symbols: int
                - average_confidence: float
                - data_completeness_score: float
                - temporal_distribution: Dict[str, int]
                - model_source_distribution: Dict[str, int]
        """
        pass
    
    @abstractmethod
    async def fetch_predictions_with_quality_filter(self,
                                                   start_date: date,
                                                   end_date: date,
                                                   min_confidence: float = 0.5,
                                                   min_data_quality: float = 0.6,
                                                   symbol_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch Predictions mit Quality Filtering
        
        Args:
            start_date: Start date
            end_date: End date
            min_confidence: Minimum confidence threshold
            min_data_quality: Minimum data quality threshold
            symbol_filter: Optional symbol filter
            
        Returns:
            List[Dict[str, Any]]: High-quality prediction data
        """
        pass
    
    @abstractmethod
    async def get_prediction_variance_by_symbol(self,
                                              symbol: str,
                                              start_date: date,
                                              end_date: date) -> Dict[str, Any]:
        """
        Get Prediction Variance Statistics für Symbol
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict[str, Any]: Variance statistics containing:
                - mean_prediction: Decimal
                - variance: Decimal
                - standard_deviation: Decimal
                - min_value: Decimal
                - max_value: Decimal
                - prediction_count: int
        """
        pass
    
    @abstractmethod
    async def fetch_recent_predictions_for_symbol(self,
                                                symbol: str,
                                                days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch Most Recent Predictions für Specific Symbol
        
        Args:
            symbol: Stock symbol
            days_back: Number of days to look back
            
        Returns:
            List[Dict[str, Any]]: Recent prediction data sorted by timestamp desc
        """
        pass
    
    @abstractmethod
    async def get_model_performance_metrics(self,
                                          start_date: date,
                                          end_date: date) -> Dict[str, Any]:
        """
        Get Model Performance Metrics für Period
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict[str, Any]: Model performance metrics containing:
                - model_accuracy_by_type: Dict[str, float]
                - prediction_count_by_model: Dict[str, int]
                - average_confidence_by_model: Dict[str, float]
                - temporal_performance_trend: List[Dict]
        """
        pass
    
    @abstractmethod
    async def validate_prediction_data_consistency(self,
                                                 start_date: date,
                                                 end_date: date) -> Dict[str, Any]:
        """
        Validate Data Consistency für Predictions
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict[str, Any]: Consistency validation results containing:
                - missing_required_fields: List[str]
                - invalid_value_ranges: Dict[str, List]
                - temporal_gaps: List[Dict]
                - duplicate_predictions: int
                - data_integrity_score: float
        """
        pass
    
    @abstractmethod
    async def fetch_predictions_for_backtesting(self,
                                               symbols: List[str],
                                               start_date: date,
                                               end_date: date) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch Prediction Data Optimized für Backtesting
        
        Args:
            symbols: List of symbols to fetch
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Predictions grouped by symbol
        """
        pass