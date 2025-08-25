#!/usr/bin/env python3
"""
Prediction Tracking Service - Presentation Controller
Clean Architecture Presentation Layer

CLEAN ARCHITECTURE - PRESENTATION LAYER:
- HTTP request/response handling
- FastAPI integration
- Request validation and response formatting

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...application.use_cases.prediction_use_cases import (
    StorePredictionUseCase,
    GetPerformanceComparisonUseCase,
    GetStatisticsUseCase,
    EvaluatePredictionsUseCase
)


logger = logging.getLogger(__name__)


class PredictionController:
    """
    Prediction Tracking Service Presentation Controller
    
    PRESENTATION LAYER: Handles HTTP requests and responses
    SINGLE RESPONSIBILITY: Coordinates between HTTP layer and application layer
    DEPENDENCY INJECTION: Receives use cases via constructor
    """
    
    def __init__(
        self,
        store_prediction_use_case: StorePredictionUseCase,
        performance_comparison_use_case: GetPerformanceComparisonUseCase,
        statistics_use_case: GetStatisticsUseCase,
        evaluation_use_case: EvaluatePredictionsUseCase
    ):
        self.store_prediction_use_case = store_prediction_use_case
        self.performance_comparison_use_case = performance_comparison_use_case
        self.statistics_use_case = statistics_use_case
        self.evaluation_use_case = evaluation_use_case
    
    async def store_predictions(
        self,
        predictions: List[Dict[str, Any]],
        source: str = "prediction_tracking_service"
    ) -> Dict[str, Any]:
        """
        Store predictions for later performance tracking
        
        Args:
            predictions: List of prediction data dictionaries
            source: Data source identifier
            
        Returns:
            Storage operation response
        """
        try:
            logger.info(f"Controller processing store request for {len(predictions)} predictions")
            
            # Execute use case
            result = await self.store_prediction_use_case.execute(
                predictions=predictions,
                source=source
            )
            
            # Add controller metadata
            result['controller_info'] = {
                'processed_at': datetime.now().isoformat(),
                'controller': 'PredictionController.store_predictions',
                'version': '6.0.0'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Controller error storing predictions: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'PredictionController.store_predictions',
                    'version': '6.0.0'
                }
            }
    
    async def get_performance_comparison(
        self,
        timeframe: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get SOLL-IST performance comparison for timeframe
        
        Args:
            timeframe: Timeframe to analyze
            days_back: How many days back to analyze
            
        Returns:
            Performance comparison response
        """
        try:
            logger.info(f"Controller processing performance comparison request for {timeframe}")
            
            # Execute use case
            result = await self.performance_comparison_use_case.execute(
                timeframe=timeframe,
                days_back=days_back
            )
            
            # Add controller metadata
            result['controller_info'] = {
                'processed_at': datetime.now().isoformat(),
                'controller': 'PredictionController.get_performance_comparison',
                'version': '6.0.0'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Controller error getting performance comparison: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'PredictionController.get_performance_comparison',
                    'version': '6.0.0'
                }
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall prediction statistics
        
        Returns:
            Statistics response
        """
        try:
            logger.info("Controller processing statistics request")
            
            # Execute use case
            result = await self.statistics_use_case.execute()
            
            # Add controller metadata
            result['controller_info'] = {
                'processed_at': datetime.now().isoformat(),
                'controller': 'PredictionController.get_statistics',
                'version': '6.0.0'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Controller error getting statistics: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'PredictionController.get_statistics',
                    'version': '6.0.0'
                }
            }
    
    async def evaluate_predictions(
        self,
        days_old: int = 1
    ) -> Dict[str, Any]:
        """
        Evaluate pending predictions with actual returns
        
        Args:
            days_old: Minimum age of predictions to evaluate
            
        Returns:
            Evaluation results response
        """
        try:
            logger.info(f"Controller processing evaluation request (days_old: {days_old})")
            
            # Execute use case
            result = await self.evaluation_use_case.execute(days_old=days_old)
            
            # Add controller metadata
            result['controller_info'] = {
                'processed_at': datetime.now().isoformat(),
                'controller': 'PredictionController.evaluate_predictions',
                'version': '6.0.0'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Controller error evaluating predictions: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'PredictionController.evaluate_predictions',
                    'version': '6.0.0'
                }
            }
    
    async def get_prediction_trends(
        self,
        timeframe: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get prediction performance trends over time
        
        Args:
            timeframe: Timeframe to analyze
            days_back: How many days back to analyze
            
        Returns:
            Trend analysis response
        """
        try:
            logger.info(f"Controller processing trends request for {timeframe}")
            
            # Use performance calculator through use case
            from ...infrastructure.container import container
            performance_calculator = container.get_performance_calculator()
            
            # Get trends data
            trends_data = await performance_calculator.get_performance_trends(
                timeframe=timeframe,
                days_back=days_back
            )
            
            return {
                'success': True,
                'data': trends_data,
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'PredictionController.get_prediction_trends',
                    'version': '6.0.0'
                }
            }
            
        except Exception as e:
            logger.error(f"Controller error getting prediction trends: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Controller-level health check
        
        Returns:
            Health check response
        """
        try:
            return {
                'success': True,
                'data': {
                    'controller': 'PredictionController',
                    'status': 'healthy',
                    'version': '6.0.0',
                    'capabilities': [
                        'store_predictions',
                        'get_performance_comparison',
                        'get_statistics',
                        'evaluate_predictions',
                        'get_prediction_trends',
                        'health_check'
                    ],
                    'use_cases': [
                        'StorePredictionUseCase',
                        'GetPerformanceComparisonUseCase',
                        'GetStatisticsUseCase',
                        'EvaluatePredictionsUseCase'
                    ]
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'PredictionController.health_check',
                    'version': '6.0.0'
                }
            }
            
        except Exception as e:
            logger.error(f"Controller health check error: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller health check failed',
                    'code': 'HEALTH_CHECK_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }