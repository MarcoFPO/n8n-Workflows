#!/usr/bin/env python3
"""
Prediction Tracking Service - Performance Calculator Implementation
Infrastructure Layer Service Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements domain performance calculator interface
- Performance metrics calculation service
- Statistical analysis implementation

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime

from ...domain.entities.prediction import PerformanceMetrics, TimeframeType
from ...domain.repositories.prediction_repository import IPerformanceCalculator, IPredictionRepository


logger = logging.getLogger(__name__)


class PerformanceCalculatorService(IPerformanceCalculator):
    """
    Performance Calculator Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation of performance calculator
    DOMAIN SERVICE: Encapsulates performance calculation business logic
    STATISTICAL ANALYSIS: Advanced metrics calculation
    """
    
    def __init__(self, repository: IPredictionRepository, accuracy_threshold: float = 5.0):
        """
        Initialize performance calculator
        
        Args:
            repository: Prediction repository for data access
            accuracy_threshold: Accuracy threshold in percentage points
        """
        self.repository = repository
        self.accuracy_threshold = accuracy_threshold
        self.initialized_at = datetime.now()
        
        logger.info(f"Performance Calculator initialized (threshold: {accuracy_threshold}%)")
    
    async def calculate_timeframe_performance(self, timeframe: str) -> PerformanceMetrics:
        """
        Calculate performance metrics for a timeframe
        
        Args:
            timeframe: Timeframe to analyze
            
        Returns:
            PerformanceMetrics value object
        """
        try:
            # Get all evaluated predictions for timeframe
            evaluated_predictions = await self.repository.get_evaluated_predictions(timeframe)
            
            if not evaluated_predictions:
                return PerformanceMetrics(
                    timeframe=timeframe,
                    calculated_at=datetime.now()
                )
            
            # Calculate metrics
            total_predictions = len(evaluated_predictions)
            accurate_predictions = sum(
                1 for pred in evaluated_predictions 
                if pred.is_accurate(self.accuracy_threshold) is True
            )
            
            # Calculate averages
            avg_predicted = sum(pred.predicted_return for pred in evaluated_predictions) / total_predictions
            avg_actual = sum(pred.actual_return for pred in evaluated_predictions) / total_predictions
            
            # Calculate average error (absolute difference)
            avg_error = sum(
                abs(pred.get_accuracy_difference()) for pred in evaluated_predictions
                if pred.get_accuracy_difference() is not None
            ) / total_predictions
            
            # Calculate accuracy rate
            accuracy_rate = Decimal(accurate_predictions) / Decimal(total_predictions) * 100
            
            metrics = PerformanceMetrics(
                timeframe=timeframe,
                total_predictions=total_predictions,
                evaluated_predictions=total_predictions,  # All are evaluated in this context
                accurate_predictions=accurate_predictions,
                accuracy_rate=round(accuracy_rate, 2),
                average_predicted_return=round(avg_predicted, 2),
                average_actual_return=round(avg_actual, 2),
                average_error=round(avg_error, 2),
                calculated_at=datetime.now()
            )
            
            logger.debug(f"Calculated performance for {timeframe}: {accuracy_rate:.2f}% accuracy")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate performance for timeframe {timeframe}: {e}")
            return PerformanceMetrics(
                timeframe=timeframe,
                calculated_at=datetime.now()
            )
    
    async def calculate_symbol_performance(self, symbol: str) -> Dict[str, PerformanceMetrics]:
        """
        Calculate performance metrics for a symbol across all timeframes
        
        Args:
            symbol: Stock symbol to analyze
            
        Returns:
            Dictionary mapping timeframe to PerformanceMetrics
        """
        try:
            # Get all predictions for symbol
            all_predictions = await self.repository.get_predictions_by_symbol(symbol, limit=1000)
            evaluated_predictions = [pred for pred in all_predictions if pred.is_evaluated()]
            
            # Group by timeframe
            timeframe_groups = {}
            for prediction in evaluated_predictions:
                tf = prediction.timeframe
                if tf not in timeframe_groups:
                    timeframe_groups[tf] = []
                timeframe_groups[tf].append(prediction)
            
            # Calculate metrics for each timeframe
            symbol_performance = {}
            for timeframe, predictions in timeframe_groups.items():
                if not predictions:
                    continue
                
                total_predictions = len(predictions)
                accurate_predictions = sum(
                    1 for pred in predictions 
                    if pred.is_accurate(self.accuracy_threshold) is True
                )
                
                # Calculate averages
                avg_predicted = sum(pred.predicted_return for pred in predictions) / total_predictions
                avg_actual = sum(pred.actual_return for pred in predictions) / total_predictions
                avg_error = sum(
                    abs(pred.get_accuracy_difference()) for pred in predictions
                    if pred.get_accuracy_difference() is not None
                ) / total_predictions
                
                accuracy_rate = Decimal(accurate_predictions) / Decimal(total_predictions) * 100
                
                symbol_performance[timeframe] = PerformanceMetrics(
                    timeframe=timeframe,
                    total_predictions=total_predictions,
                    evaluated_predictions=total_predictions,
                    accurate_predictions=accurate_predictions,
                    accuracy_rate=round(accuracy_rate, 2),
                    average_predicted_return=round(avg_predicted, 2),
                    average_actual_return=round(avg_actual, 2),
                    average_error=round(avg_error, 2),
                    calculated_at=datetime.now()
                )
            
            logger.debug(f"Calculated symbol performance for {symbol}: {len(symbol_performance)} timeframes")
            return symbol_performance
            
        except Exception as e:
            logger.error(f"Failed to calculate symbol performance for {symbol}: {e}")
            return {}
    
    async def calculate_overall_performance(self) -> Dict[str, PerformanceMetrics]:
        """
        Calculate overall performance across all timeframes
        
        Returns:
            Dictionary mapping timeframe to PerformanceMetrics
        """
        try:
            # Get all evaluated predictions
            all_evaluated = await self.repository.get_evaluated_predictions()
            
            if not all_evaluated:
                logger.warning("No evaluated predictions found for overall performance calculation")
                return {}
            
            # Group by timeframe
            timeframe_groups = {}
            for prediction in all_evaluated:
                tf = prediction.timeframe
                if tf not in timeframe_groups:
                    timeframe_groups[tf] = []
                timeframe_groups[tf].append(prediction)
            
            # Calculate performance for each timeframe
            overall_performance = {}
            for timeframe in timeframe_groups.keys():
                metrics = await self.calculate_timeframe_performance(timeframe)
                overall_performance[timeframe] = metrics
            
            logger.info(f"Calculated overall performance for {len(overall_performance)} timeframes")
            return overall_performance
            
        except Exception as e:
            logger.error(f"Failed to calculate overall performance: {e}")
            return {}
    
    async def get_performance_trends(self, timeframe: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get performance trends over time
        
        Args:
            timeframe: Timeframe to analyze
            days_back: How many days back to analyze
            
        Returns:
            Trend analysis dictionary
        """
        try:
            # Get recent predictions
            recent_predictions = await self.repository.get_recent_predictions(days=days_back)
            timeframe_predictions = [
                pred for pred in recent_predictions 
                if pred.timeframe == timeframe and pred.is_evaluated()
            ]
            
            if not timeframe_predictions:
                return {
                    'timeframe': timeframe,
                    'trend': 'no_data',
                    'message': 'Insufficient data for trend analysis'
                }
            
            # Sort by evaluation date
            timeframe_predictions.sort(key=lambda x: x.evaluation_date or x.predicted_date)
            
            # Calculate rolling accuracy (weekly windows)
            window_size = min(7, len(timeframe_predictions) // 3)  # Adaptive window size
            if window_size < 2:
                return {
                    'timeframe': timeframe,
                    'trend': 'insufficient_data',
                    'message': 'Not enough data points for trend analysis'
                }
            
            accuracies = []
            for i in range(len(timeframe_predictions) - window_size + 1):
                window = timeframe_predictions[i:i + window_size]
                accurate_count = sum(
                    1 for pred in window 
                    if pred.is_accurate(self.accuracy_threshold) is True
                )
                accuracy = accurate_count / len(window) * 100
                accuracies.append(accuracy)
            
            # Determine trend
            if len(accuracies) < 2:
                trend = 'stable'
            else:
                first_half = sum(accuracies[:len(accuracies)//2]) / (len(accuracies)//2)
                second_half = sum(accuracies[len(accuracies)//2:]) / (len(accuracies) - len(accuracies)//2)
                
                diff = second_half - first_half
                if diff > 5:
                    trend = 'improving'
                elif diff < -5:
                    trend = 'declining'
                else:
                    trend = 'stable'
            
            return {
                'timeframe': timeframe,
                'trend': trend,
                'current_accuracy': round(accuracies[-1] if accuracies else 0, 2),
                'average_accuracy': round(sum(accuracies) / len(accuracies) if accuracies else 0, 2),
                'data_points': len(timeframe_predictions),
                'analysis_period_days': days_back,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate performance trends for {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'trend': 'error',
                'message': f'Error calculating trends: {str(e)}'
            }
    
    async def get_calculator_stats(self) -> Dict[str, Any]:
        """
        Get calculator statistics and health
        
        Returns:
            Calculator statistics dictionary
        """
        try:
            uptime = datetime.now() - self.initialized_at
            
            # Get repository stats
            repo_stats = await self.repository.get_repository_stats()
            
            return {
                'calculator': 'PerformanceCalculatorService',
                'version': '6.0.0',
                'accuracy_threshold': self.accuracy_threshold,
                'uptime_seconds': int(uptime.total_seconds()),
                'initialized_at': self.initialized_at.isoformat(),
                'supported_timeframes': [tf.value for tf in TimeframeType],
                'repository_stats': repo_stats,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get calculator stats: {e}")
            return {'error': str(e)}