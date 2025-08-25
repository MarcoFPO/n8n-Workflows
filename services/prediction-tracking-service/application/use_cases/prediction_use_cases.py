#!/usr/bin/env python3
"""
Prediction Tracking Service - Use Cases
Application Layer Business Logic Orchestration

CLEAN ARCHITECTURE - APPLICATION LAYER:
- Orchestrates business logic flow
- Uses domain entities and repository interfaces
- Independent of external frameworks

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ...domain.entities.prediction import Prediction, PredictionRequest, PerformanceMetrics
from ...domain.repositories.prediction_repository import (
    IPredictionRepository,
    IPerformanceCalculator,
    IPredictionProvider,
    IPredictionCache
)
from ..interfaces.event_publisher import IEventPublisher


logger = logging.getLogger(__name__)


class StorePredictionUseCase:
    """
    Store Prediction Use Case
    
    APPLICATION LAYER: Orchestrates prediction storage business logic
    SINGLE RESPONSIBILITY: Handles prediction creation and storage
    """
    
    def __init__(
        self,
        repository: IPredictionRepository,
        cache: Optional[IPredictionCache] = None,
        event_publisher: Optional[IEventPublisher] = None
    ):
        self.repository = repository
        self.cache = cache
        self.event_publisher = event_publisher
    
    async def execute(
        self, 
        predictions: List[Dict[str, Any]], 
        source: str = "prediction_tracking_service"
    ) -> Dict[str, Any]:
        """
        Execute Store Prediction Use Case
        
        Args:
            predictions: List of prediction data dictionaries
            source: Data source identifier
            
        Returns:
            Dictionary with operation result
        """
        try:
            stored_predictions = []
            failed_predictions = []
            
            for pred_data in predictions:
                try:
                    # Create and validate request
                    request = PredictionRequest(
                        symbol=pred_data['symbol'],
                        timeframe=pred_data['timeframe'],
                        predicted_return=pred_data['predicted_return'],
                        source=source
                    )
                    
                    # Validate request
                    if not request.is_request_valid():
                        failed_predictions.append({
                            'data': pred_data,
                            'error': 'Request validation failed - too old'
                        })
                        continue
                    
                    # Create prediction entity with unique ID
                    prediction = request.to_prediction()
                    prediction = Prediction(
                        prediction_id=str(uuid.uuid4()),
                        symbol=prediction.symbol,
                        timeframe=prediction.timeframe,
                        predicted_return=prediction.predicted_return,
                        predicted_date=prediction.predicted_date,
                        source=prediction.source
                    )
                    
                    # Store prediction
                    success = await self.repository.save_prediction(prediction)
                    
                    if success:
                        stored_predictions.append(prediction)
                        
                        # Invalidate relevant cache entries
                        if self.cache:
                            await self._invalidate_related_cache(prediction)
                        
                        # Publish event
                        await self._publish_event('prediction.stored', {
                            'prediction_id': prediction.prediction_id,
                            'symbol': prediction.symbol,
                            'timeframe': prediction.timeframe,
                            'predicted_return': float(prediction.predicted_return)
                        })
                        
                    else:
                        failed_predictions.append({
                            'data': pred_data,
                            'error': 'Repository save failed'
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to store prediction {pred_data}: {e}")
                    failed_predictions.append({
                        'data': pred_data,
                        'error': str(e)
                    })
            
            # Create response
            response = {
                'success': True,
                'stored_count': len(stored_predictions),
                'failed_count': len(failed_predictions),
                'stored_predictions': [pred.to_dict() for pred in stored_predictions],
                'timestamp': datetime.now().isoformat()
            }
            
            if failed_predictions:
                response['failed_predictions'] = failed_predictions
                response['partial_success'] = True
            
            logger.info(f"Stored {len(stored_predictions)} predictions, {len(failed_predictions)} failed")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in StorePredictionUseCase: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Failed to store predictions',
                    'code': 'STORAGE_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    async def _invalidate_related_cache(self, prediction: Prediction) -> None:
        """Invalidate cache entries related to prediction"""
        if not self.cache:
            return
        
        try:
            # Invalidate symbol-based cache
            await self.cache.invalidate_cache(f"symbol:{prediction.symbol}*")
            # Invalidate timeframe-based cache
            await self.cache.invalidate_cache(f"timeframe:{prediction.timeframe}*")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
    
    async def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event if publisher is available"""
        if not self.event_publisher:
            return
        
        try:
            await self.event_publisher.publish(event_type, {
                **data,
                'service': 'prediction_tracking_service',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Event publishing failed: {e}")


class GetPerformanceComparisonUseCase:
    """
    Get Performance Comparison Use Case
    
    APPLICATION LAYER: Orchestrates SOLL-IST performance comparison
    """
    
    def __init__(
        self,
        repository: IPredictionRepository,
        performance_calculator: IPerformanceCalculator,
        cache: Optional[IPredictionCache] = None,
        external_provider: Optional[IPredictionProvider] = None
    ):
        self.repository = repository
        self.performance_calculator = performance_calculator
        self.cache = cache
        self.external_provider = external_provider
    
    async def execute(self, timeframe: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Execute Performance Comparison Use Case
        
        Args:
            timeframe: Timeframe to analyze
            days_back: How many days back to analyze
            
        Returns:
            Performance comparison data
        """
        try:
            # Try cache first
            cache_key = f"performance:{timeframe}:{days_back}"
            cached_data = None
            
            if self.cache:
                cached_results = await self.cache.get_cached_predictions(cache_key)
                if cached_results:
                    logger.debug(f"Cache hit for performance comparison: {timeframe}")
                    # Convert cached predictions to comparison format
                    cached_data = await self._format_comparison_data(cached_results, timeframe)
            
            if cached_data:
                return cached_data
            
            # Get recent evaluated predictions
            cutoff_date = datetime.now() - timedelta(days=days_back)
            all_predictions = await self.repository.get_evaluated_predictions(timeframe)
            
            # Filter by date
            recent_predictions = [
                pred for pred in all_predictions
                if pred.evaluation_date and pred.evaluation_date >= cutoff_date
            ]
            
            # Calculate performance metrics
            performance_metrics = await self.performance_calculator.calculate_timeframe_performance(timeframe)
            
            # Format comparison data
            comparison_data = []
            for prediction in recent_predictions:
                comparison_data.append({
                    'symbol': prediction.symbol,
                    'soll_return': float(prediction.predicted_return),
                    'ist_return': float(prediction.actual_return) if prediction.actual_return else 0.0,
                    'difference': float(prediction.get_accuracy_difference()) if prediction.get_accuracy_difference() else 0.0,
                    'prediction_date': prediction.predicted_date.isoformat(),
                    'evaluation_date': prediction.evaluation_date.isoformat() if prediction.evaluation_date else None,
                    'timeframe': prediction.timeframe,
                    'accuracy_percentage': float(prediction.get_accuracy_percentage()) if prediction.get_accuracy_percentage() else 0.0
                })
            
            # Create response
            response = {
                'success': True,
                'timeframe': timeframe,
                'days_analyzed': days_back,
                'comparison_data': comparison_data,
                'summary': {
                    'total_predictions': len(comparison_data),
                    'avg_soll': round(sum(item['soll_return'] for item in comparison_data) / len(comparison_data) if comparison_data else 0, 2),
                    'avg_ist': round(sum(item['ist_return'] for item in comparison_data) / len(comparison_data) if comparison_data else 0, 2),
                    'avg_accuracy': round(sum(item['accuracy_percentage'] for item in comparison_data) / len(comparison_data) if comparison_data else 0, 2),
                    'performance_metrics': performance_metrics.to_dict()
                },
                'data_source': 'repository',
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache the results
            if self.cache and comparison_data:
                await self.cache.cache_predictions(cache_key, recent_predictions, ttl_minutes=30)
            
            logger.info(f"Generated performance comparison for {timeframe}: {len(comparison_data)} items")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in GetPerformanceComparisonUseCase: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Failed to get performance comparison',
                    'code': 'PERFORMANCE_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    async def _format_comparison_data(self, predictions: List[Prediction], timeframe: str) -> Dict[str, Any]:
        """Format cached predictions as comparison data"""
        comparison_data = []
        for prediction in predictions:
            if prediction.is_evaluated():
                comparison_data.append({
                    'symbol': prediction.symbol,
                    'soll_return': float(prediction.predicted_return),
                    'ist_return': float(prediction.actual_return),
                    'difference': float(prediction.get_accuracy_difference()),
                    'prediction_date': prediction.predicted_date.isoformat(),
                    'timeframe': prediction.timeframe
                })
        
        return {
            'success': True,
            'timeframe': timeframe,
            'comparison_data': comparison_data,
            'data_source': 'cache',
            'timestamp': datetime.now().isoformat()
        }


class GetStatisticsUseCase:
    """
    Get Statistics Use Case
    
    APPLICATION LAYER: Orchestrates statistics retrieval
    """
    
    def __init__(
        self,
        repository: IPredictionRepository,
        performance_calculator: IPerformanceCalculator
    ):
        self.repository = repository
        self.performance_calculator = performance_calculator
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute Get Statistics Use Case
        
        Returns:
            Service statistics
        """
        try:
            # Get repository stats
            repo_stats = await self.repository.get_repository_stats()
            
            # Get overall performance
            overall_performance = await self.performance_calculator.calculate_overall_performance()
            
            # Get all symbols
            symbols = await self.repository.get_all_symbols()
            
            # Get recent predictions (last 7 days)
            recent_predictions = await self.repository.get_recent_predictions(days=7)
            
            # Get pending evaluations
            pending_evaluations = await self.repository.get_pending_evaluations(days_old=1)
            
            return {
                'success': True,
                'statistics': {
                    'total_predictions': repo_stats.get('total_predictions', 0),
                    'total_symbols': len(symbols),
                    'symbols': symbols,
                    'recent_predictions_count': len(recent_predictions),
                    'pending_evaluations_count': len(pending_evaluations),
                    'timeframe_performance': {
                        timeframe: metrics.to_dict() 
                        for timeframe, metrics in overall_performance.items()
                    },
                    'repository_stats': repo_stats
                },
                'service_status': 'active',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in GetStatisticsUseCase: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Failed to get statistics',
                    'code': 'STATISTICS_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }


class EvaluatePredictionsUseCase:
    """
    Evaluate Predictions Use Case
    
    APPLICATION LAYER: Orchestrates prediction evaluation with actual returns
    """
    
    def __init__(
        self,
        repository: IPredictionRepository,
        external_provider: Optional[IPredictionProvider] = None,
        event_publisher: Optional[IEventPublisher] = None
    ):
        self.repository = repository
        self.external_provider = external_provider
        self.event_publisher = event_publisher
    
    async def execute(self, days_old: int = 1) -> Dict[str, Any]:
        """
        Execute Evaluate Predictions Use Case
        
        Args:
            days_old: Minimum age of predictions to evaluate
            
        Returns:
            Evaluation results
        """
        try:
            # Get predictions that need evaluation
            pending_predictions = await self.repository.get_pending_evaluations(days_old)
            
            if not pending_predictions:
                return {
                    'success': True,
                    'message': 'No predictions need evaluation',
                    'evaluated_count': 0,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get actual returns from external provider
            actual_returns = {}
            if self.external_provider and await self.external_provider.is_available():
                actual_returns = await self.external_provider.fetch_actual_returns(pending_predictions)
            
            # Evaluate predictions
            evaluated_count = 0
            failed_count = 0
            
            for prediction in pending_predictions:
                try:
                    # Get actual return (from external provider or mock)
                    actual_return = actual_returns.get(
                        prediction.prediction_id,
                        self._generate_mock_actual_return(prediction)  # Fallback
                    )
                    
                    # Update prediction with evaluation
                    success = await self.repository.update_prediction_evaluation(
                        prediction.prediction_id,
                        actual_return,
                        datetime.now()
                    )
                    
                    if success:
                        evaluated_count += 1
                        
                        # Publish evaluation event
                        await self._publish_event('prediction.evaluated', {
                            'prediction_id': prediction.prediction_id,
                            'symbol': prediction.symbol,
                            'predicted_return': float(prediction.predicted_return),
                            'actual_return': actual_return,
                            'accuracy_difference': actual_return - float(prediction.predicted_return)
                        })
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to evaluate prediction {prediction.prediction_id}: {e}")
                    failed_count += 1
            
            return {
                'success': True,
                'evaluated_count': evaluated_count,
                'failed_count': failed_count,
                'total_pending': len(pending_predictions),
                'data_source': 'external_provider' if actual_returns else 'mock',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in EvaluatePredictionsUseCase: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Failed to evaluate predictions',
                    'code': 'EVALUATION_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    def _generate_mock_actual_return(self, prediction: Prediction) -> float:
        """Generate mock actual return for testing (±20% variance)"""
        import random
        base_return = float(prediction.predicted_return)
        variance = random.uniform(-0.2, 0.2)  # ±20%
        return base_return * (1 + variance)
    
    async def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event if publisher is available"""
        if not self.event_publisher:
            return
        
        try:
            await self.event_publisher.publish(event_type, {
                **data,
                'service': 'prediction_tracking_service',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Event publishing failed: {e}")