#!/usr/bin/env python3
"""
Performance Evaluation Domain Service v1.0.0
Clean Architecture Domain Layer - ML Model Performance Business Logic

DOMAIN SERVICE RESPONSIBILITIES:
- Implements business logic for ML model performance evaluation
- Orchestrates SOLL-IST comparison workflows
- Manages performance metrics calculation and validation
- Implements model degradation detection and alerts

BUSINESS RULES IMPLEMENTED:
- Performance Thresholds: Min 70% accuracy for production models
- SOLL-IST Analysis: Predicted vs Actual price comparison
- Model Degradation Detection: Performance trend analysis
- Benchmark Comparisons: Model vs market baseline performance
- Quality Gates: Performance-based model promotion/demotion

CLEAN ARCHITECTURE COMPLIANCE:
- No Infrastructure dependencies (database, external APIs)
- Pure business logic implementation
- Domain Entity orchestration
- Value Object validation
- Repository pattern abstraction

SUCCESS TEMPLATE: Based on ML-Analytics Clean Architecture Migration
Integration: Event-Driven Architecture for Performance Monitoring

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0 - Domain Service Implementation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import numpy as np
from statistics import mean, median, stdev

# Domain Layer Imports
from ..entities.ml_engine import MLEngine, ModelConfiguration
from ..entities.prediction import PredictionHorizon, ModelPerformanceMetrics, PredictionResult
from ..value_objects.model_confidence import ModelConfidence
from ..value_objects.performance_metrics import PerformanceMetrics
from ..exceptions.ml_exceptions import (
    PerformanceEvaluationError,
    InsufficientDataError,
    ModelDegradationError
)


class PerformanceGrade(Enum):
    """Performance Grade Enumeration - Domain Value Object"""
    EXCELLENT = "A+"  # >95% accuracy
    VERY_GOOD = "A"   # 90-95% accuracy
    GOOD = "B"        # 80-90% accuracy
    ACCEPTABLE = "C"  # 70-80% accuracy
    POOR = "D"        # 60-70% accuracy
    FAILING = "F"     # <60% accuracy


class ModelStatus(Enum):
    """Model Status Enumeration - Domain Value Object"""
    CHAMPION = "champion"        # Best performing model
    CHALLENGER = "challenger"    # Good alternative model
    PRODUCTION = "production"    # Currently deployed
    TESTING = "testing"         # Under evaluation
    DEPRECATED = "deprecated"   # Performance degraded
    RETIRED = "retired"         # No longer used


class TrendDirection(Enum):
    """Performance Trend Direction - Domain Value Object"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


@dataclass
class PerformanceMetric:
    """Performance Metric Value Object - Domain Layer"""
    metric_name: str
    value: float
    threshold: float
    grade: PerformanceGrade
    trend: TrendDirection
    calculated_at: datetime
    
    def is_passing(self) -> bool:
        """Check if metric meets threshold"""
        return self.value >= self.threshold
    
    def get_performance_ratio(self) -> float:
        """Get performance as ratio of threshold"""
        return self.value / self.threshold if self.threshold > 0 else 0.0


@dataclass
class SollIstComparison:
    """SOLL-IST Comparison Value Object - Domain Layer"""
    symbol: str
    horizon: PredictionHorizon
    predicted_price: float
    actual_price: float
    prediction_date: datetime
    evaluation_date: datetime
    accuracy_percentage: float
    absolute_error: float
    relative_error_percentage: float
    direction_correct: bool
    model_used: str


@dataclass
class PerformanceReport:
    """Performance Report Value Object - Domain Layer"""
    model_id: str
    evaluation_period: Tuple[datetime, datetime]
    overall_grade: PerformanceGrade
    performance_metrics: Dict[str, PerformanceMetric]
    soll_ist_comparisons: List[SollIstComparison]
    trend_analysis: Dict[str, TrendDirection]
    recommendations: List[str]
    next_evaluation_date: datetime
    model_status: ModelStatus


class PerformanceEvaluationService:
    """
    Performance Evaluation Domain Service - Clean Architecture
    
    DOMAIN LAYER RESPONSIBILITIES:
    - Implements core ML model performance evaluation business logic
    - Orchestrates SOLL-IST comparison workflows
    - Manages performance metrics calculation and validation
    - Implements model degradation detection and alerting
    
    BUSINESS RULES:
    - Performance threshold validation (min 70% for production)
    - SOLL-IST analysis with multiple metrics
    - Model performance trend analysis
    - Performance-based model lifecycle management
    - Benchmark comparison against market baseline
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._performance_history: Dict[str, List[PerformanceMetric]] = {}
        self._benchmark_performance: Dict[str, float] = {
            'market_baseline': 0.52,  # Random walk baseline
            'buy_hold_strategy': 0.65,  # Simple buy and hold
            'moving_average_strategy': 0.68  # Moving average crossover
        }
        
    async def evaluate_model_performance(
        self,
        model_id: str,
        prediction_results: List[PredictionResult],
        actual_prices: List[Tuple[datetime, str, float]],  # (date, symbol, price)
        evaluation_period_days: int = 30
    ) -> PerformanceReport:
        """
        Comprehensive model performance evaluation
        
        BUSINESS LOGIC:
        1. Perform SOLL-IST comparisons
        2. Calculate performance metrics
        3. Analyze performance trends
        4. Grade model performance
        5. Generate recommendations
        """
        try:
            self.logger.info(f"Evaluating performance for model {model_id}")
            self.logger.info(f"Evaluation period: {evaluation_period_days} days")
            
            # Define evaluation period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=evaluation_period_days)
            evaluation_period = (start_date, end_date)
            
            # Filter predictions within evaluation period
            period_predictions = [
                pred for pred in prediction_results
                if start_date <= pred.created_at <= end_date
            ]
            
            if not period_predictions:
                raise InsufficientDataError(f"No predictions found for model {model_id} in evaluation period")
            
            # Perform SOLL-IST comparisons
            soll_ist_comparisons = await self._perform_soll_ist_analysis(
                period_predictions, actual_prices
            )
            
            if not soll_ist_comparisons:
                raise InsufficientDataError(f"No matching actual prices found for SOLL-IST analysis")
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(soll_ist_comparisons)
            
            # Analyze performance trends
            trend_analysis = self._analyze_performance_trends(model_id, performance_metrics)
            
            # Grade overall performance
            overall_grade = self._calculate_overall_grade(performance_metrics)
            
            # Determine model status
            model_status = self._determine_model_status(overall_grade, trend_analysis)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                performance_metrics, trend_analysis, overall_grade
            )
            
            # Schedule next evaluation
            next_evaluation = self._calculate_next_evaluation_date(overall_grade, trend_analysis)
            
            # Update performance history
            self._update_performance_history(model_id, performance_metrics)
            
            report = PerformanceReport(
                model_id=model_id,
                evaluation_period=evaluation_period,
                overall_grade=overall_grade,
                performance_metrics=performance_metrics,
                soll_ist_comparisons=soll_ist_comparisons,
                trend_analysis=trend_analysis,
                recommendations=recommendations,
                next_evaluation_date=next_evaluation,
                model_status=model_status
            )
            
            self.logger.info(f"Performance evaluation completed: Grade {overall_grade.value}")
            return report
            
        except Exception as e:
            self.logger.error(f"Performance evaluation failed: {str(e)}")
            raise PerformanceEvaluationError(f"Evaluation failed for model {model_id}: {str(e)}")
    
    async def _perform_soll_ist_analysis(
        self,
        predictions: List[PredictionResult],
        actual_prices: List[Tuple[datetime, str, float]]
    ) -> List[SollIstComparison]:
        """Perform SOLL-IST (predicted vs actual) analysis"""
        comparisons = []
        
        # Create lookup dictionary for actual prices
        price_lookup = {}
        for date, symbol, price in actual_prices:
            key = f"{symbol}_{date.date()}"
            price_lookup[key] = price
        
        for prediction in predictions:
            # Calculate target date based on prediction horizon
            target_date = self._calculate_prediction_target_date(
                prediction.created_at, 
                prediction.horizon
            )
            
            # Look for actual price on target date
            lookup_key = f"{prediction.symbol}_{target_date.date()}"
            
            if lookup_key in price_lookup:
                actual_price = price_lookup[lookup_key]
                predicted_price = getattr(prediction, 'predicted_price', None)
                
                if predicted_price is not None:
                    comparison = self._create_soll_ist_comparison(
                        prediction, actual_price, predicted_price, target_date
                    )
                    comparisons.append(comparison)
        
        self.logger.info(f"Created {len(comparisons)} SOLL-IST comparisons")
        return comparisons
    
    def _create_soll_ist_comparison(
        self,
        prediction: PredictionResult,
        actual_price: float,
        predicted_price: float,
        target_date: datetime
    ) -> SollIstComparison:
        """Create SOLL-IST comparison object"""
        
        # Calculate accuracy metrics
        absolute_error = abs(predicted_price - actual_price)
        relative_error = absolute_error / actual_price * 100
        accuracy_percentage = max(0, 100 - relative_error)
        
        # Check direction correctness
        current_price = getattr(prediction, 'current_price', predicted_price * 0.95)  # Estimate
        predicted_direction = predicted_price > current_price
        actual_direction = actual_price > current_price
        direction_correct = predicted_direction == actual_direction
        
        return SollIstComparison(
            symbol=prediction.symbol,
            horizon=prediction.horizon,
            predicted_price=predicted_price,
            actual_price=actual_price,
            prediction_date=prediction.created_at,
            evaluation_date=target_date,
            accuracy_percentage=accuracy_percentage,
            absolute_error=absolute_error,
            relative_error_percentage=relative_error,
            direction_correct=direction_correct,
            model_used=getattr(prediction, 'model_type', 'unknown')
        )
    
    def _calculate_performance_metrics(self, comparisons: List[SollIstComparison]) -> Dict[str, PerformanceMetric]:
        """Calculate comprehensive performance metrics"""
        
        if not comparisons:
            return {}
        
        # Calculate basic metrics
        accuracy_scores = [comp.accuracy_percentage for comp in comparisons]
        absolute_errors = [comp.absolute_error for comp in comparisons]
        relative_errors = [comp.relative_error_percentage for comp in comparisons]
        direction_correct = [comp.direction_correct for comp in comparisons]
        
        # Mean Accuracy
        mean_accuracy = mean(accuracy_scores) / 100
        accuracy_metric = PerformanceMetric(
            metric_name="accuracy",
            value=mean_accuracy,
            threshold=0.70,  # 70% threshold
            grade=self._calculate_metric_grade(mean_accuracy, 0.70),
            trend=TrendDirection.STABLE,  # Will be updated in trend analysis
            calculated_at=datetime.now()
        )
        
        # Precision (for positive predictions)
        positive_predictions = [comp for comp in comparisons if comp.predicted_price > (comp.actual_price * 0.95)]
        precision = len([comp for comp in positive_predictions if comp.direction_correct]) / len(positive_predictions) if positive_predictions else 0
        precision_metric = PerformanceMetric(
            metric_name="precision",
            value=precision,
            threshold=0.65,
            grade=self._calculate_metric_grade(precision, 0.65),
            trend=TrendDirection.STABLE,
            calculated_at=datetime.now()
        )
        
        # Recall (for actual positive movements)
        actual_positives = [comp for comp in comparisons if comp.actual_price > (comp.predicted_price * 0.95)]
        recall = len([comp for comp in actual_positives if comp.direction_correct]) / len(actual_positives) if actual_positives else 0
        recall_metric = PerformanceMetric(
            metric_name="recall",
            value=recall,
            threshold=0.65,
            grade=self._calculate_metric_grade(recall, 0.65),
            trend=TrendDirection.STABLE,
            calculated_at=datetime.now()
        )
        
        # F1 Score
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        f1_metric = PerformanceMetric(
            metric_name="f1_score",
            value=f1_score,
            threshold=0.65,
            grade=self._calculate_metric_grade(f1_score, 0.65),
            trend=TrendDirection.STABLE,
            calculated_at=datetime.now()
        )
        
        # Mean Absolute Error
        mae = mean(absolute_errors)
        mae_metric = PerformanceMetric(
            metric_name="mean_absolute_error",
            value=mae,
            threshold=10.0,  # Lower is better, so we'll invert for grading
            grade=self._calculate_error_metric_grade(mae, 10.0),
            trend=TrendDirection.STABLE,
            calculated_at=datetime.now()
        )
        
        # Direction Accuracy
        direction_accuracy = sum(direction_correct) / len(direction_correct)
        direction_metric = PerformanceMetric(
            metric_name="direction_accuracy",
            value=direction_accuracy,
            threshold=0.65,
            grade=self._calculate_metric_grade(direction_accuracy, 0.65),
            trend=TrendDirection.STABLE,
            calculated_at=datetime.now()
        )
        
        # Benchmark Comparison
        benchmark_score = self._calculate_benchmark_comparison(comparisons)
        benchmark_metric = PerformanceMetric(
            metric_name="benchmark_outperformance",
            value=benchmark_score,
            threshold=0.10,  # 10% better than benchmark
            grade=self._calculate_metric_grade(benchmark_score, 0.10),
            trend=TrendDirection.STABLE,
            calculated_at=datetime.now()
        )
        
        return {
            "accuracy": accuracy_metric,
            "precision": precision_metric,
            "recall": recall_metric,
            "f1_score": f1_metric,
            "mean_absolute_error": mae_metric,
            "direction_accuracy": direction_metric,
            "benchmark_outperformance": benchmark_metric
        }
    
    def _analyze_performance_trends(self, model_id: str, current_metrics: Dict[str, PerformanceMetric]) -> Dict[str, TrendDirection]:
        """Analyze performance trends over time"""
        trends = {}
        
        historical_metrics = self._performance_history.get(model_id, [])
        
        if len(historical_metrics) < 3:
            # Not enough history, assume stable
            return {name: TrendDirection.STABLE for name in current_metrics.keys()}
        
        # Analyze last 5 periods for trend
        recent_periods = 5
        
        for metric_name in current_metrics.keys():
            # Get historical values for this metric
            historical_values = [
                metric.value for metric in historical_metrics[-recent_periods:]
                if metric.metric_name == metric_name
            ]
            
            if len(historical_values) < 3:
                trends[metric_name] = TrendDirection.STABLE
                continue
            
            # Calculate trend
            trend = self._calculate_trend_direction(historical_values)
            trends[metric_name] = trend
            
            # Update current metric with trend
            current_metrics[metric_name].trend = trend
        
        return trends
    
    def _calculate_trend_direction(self, values: List[float]) -> TrendDirection:
        """Calculate trend direction from historical values"""
        if len(values) < 3:
            return TrendDirection.STABLE
        
        # Calculate linear regression slope
        x = list(range(len(values)))
        y = values
        
        n = len(values)
        slope = (n * sum(xi * yi for xi, yi in zip(x, y)) - sum(x) * sum(y)) / (n * sum(xi * xi for xi in x) - sum(x) ** 2)
        
        # Calculate volatility
        if len(values) > 1:
            volatility = stdev(values) / mean(values) if mean(values) != 0 else 0
        else:
            volatility = 0
        
        # Determine trend based on slope and volatility
        if volatility > 0.2:  # High volatility
            return TrendDirection.VOLATILE
        elif slope > 0.02:  # Improving
            return TrendDirection.IMPROVING
        elif slope < -0.02:  # Declining
            return TrendDirection.DECLINING
        else:  # Stable
            return TrendDirection.STABLE
    
    def _calculate_metric_grade(self, value: float, threshold: float) -> PerformanceGrade:
        """Calculate performance grade for a metric"""
        ratio = value / threshold if threshold > 0 else 0
        
        if ratio >= 1.35:  # 135% of threshold
            return PerformanceGrade.EXCELLENT
        elif ratio >= 1.2:  # 120% of threshold
            return PerformanceGrade.VERY_GOOD
        elif ratio >= 1.05:  # 105% of threshold
            return PerformanceGrade.GOOD
        elif ratio >= 1.0:  # At threshold
            return PerformanceGrade.ACCEPTABLE
        elif ratio >= 0.85:  # 85% of threshold
            return PerformanceGrade.POOR
        else:
            return PerformanceGrade.FAILING
    
    def _calculate_error_metric_grade(self, value: float, threshold: float) -> PerformanceGrade:
        """Calculate grade for error metrics (lower is better)"""
        ratio = threshold / value if value > 0 else 0  # Inverted ratio
        
        if ratio >= 2.0:  # Error is less than half the threshold
            return PerformanceGrade.EXCELLENT
        elif ratio >= 1.5:
            return PerformanceGrade.VERY_GOOD
        elif ratio >= 1.2:
            return PerformanceGrade.GOOD
        elif ratio >= 1.0:
            return PerformanceGrade.ACCEPTABLE
        elif ratio >= 0.7:
            return PerformanceGrade.POOR
        else:
            return PerformanceGrade.FAILING
    
    def _calculate_overall_grade(self, metrics: Dict[str, PerformanceMetric]) -> PerformanceGrade:
        """Calculate overall performance grade"""
        if not metrics:
            return PerformanceGrade.FAILING
        
        # Weight different metrics
        metric_weights = {
            "accuracy": 0.30,
            "precision": 0.15,
            "recall": 0.15,
            "f1_score": 0.20,
            "direction_accuracy": 0.15,
            "benchmark_outperformance": 0.05
        }
        
        # Grade to numeric score mapping
        grade_scores = {
            PerformanceGrade.EXCELLENT: 5.0,
            PerformanceGrade.VERY_GOOD: 4.0,
            PerformanceGrade.GOOD: 3.0,
            PerformanceGrade.ACCEPTABLE: 2.0,
            PerformanceGrade.POOR: 1.0,
            PerformanceGrade.FAILING: 0.0
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric_name, metric in metrics.items():
            weight = metric_weights.get(metric_name, 0.1)
            score = grade_scores[metric.grade]
            weighted_score += weight * score
            total_weight += weight
        
        if total_weight == 0:
            return PerformanceGrade.FAILING
        
        final_score = weighted_score / total_weight
        
        # Convert back to grade
        if final_score >= 4.5:
            return PerformanceGrade.EXCELLENT
        elif final_score >= 3.5:
            return PerformanceGrade.VERY_GOOD
        elif final_score >= 2.5:
            return PerformanceGrade.GOOD
        elif final_score >= 1.5:
            return PerformanceGrade.ACCEPTABLE
        elif final_score >= 0.5:
            return PerformanceGrade.POOR
        else:
            return PerformanceGrade.FAILING
    
    def _determine_model_status(self, overall_grade: PerformanceGrade, trends: Dict[str, TrendDirection]) -> ModelStatus:
        """Determine model status based on performance and trends"""
        
        # Count improving vs declining trends
        improving_trends = sum(1 for trend in trends.values() if trend == TrendDirection.IMPROVING)
        declining_trends = sum(1 for trend in trends.values() if trend == TrendDirection.DECLINING)
        
        # Status logic
        if overall_grade in [PerformanceGrade.EXCELLENT, PerformanceGrade.VERY_GOOD]:
            if declining_trends > improving_trends:
                return ModelStatus.PRODUCTION  # Good but declining
            else:
                return ModelStatus.CHAMPION  # Excellent and stable/improving
        
        elif overall_grade == PerformanceGrade.GOOD:
            if improving_trends > declining_trends:
                return ModelStatus.CHALLENGER  # Good and improving
            else:
                return ModelStatus.PRODUCTION  # Good but stable/declining
        
        elif overall_grade == PerformanceGrade.ACCEPTABLE:
            if declining_trends > 2:
                return ModelStatus.TESTING  # Acceptable but declining
            else:
                return ModelStatus.PRODUCTION  # Acceptable and stable
        
        else:  # POOR or FAILING
            if declining_trends > improving_trends:
                return ModelStatus.DEPRECATED  # Poor and declining
            else:
                return ModelStatus.TESTING  # Poor but maybe improving
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, PerformanceMetric],
        trends: Dict[str, TrendDirection],
        overall_grade: PerformanceGrade
    ) -> List[str]:
        """Generate actionable recommendations based on performance"""
        recommendations = []
        
        # Overall performance recommendations
        if overall_grade == PerformanceGrade.FAILING:
            recommendations.append("CRITICAL: Model performance below acceptable threshold - immediate retraining required")
        elif overall_grade == PerformanceGrade.POOR:
            recommendations.append("Model performance declining - schedule retraining within 1 week")
        elif overall_grade == PerformanceGrade.EXCELLENT:
            recommendations.append("Excellent performance - consider promoting to champion model")
        
        # Specific metric recommendations
        for metric_name, metric in metrics.items():
            if not metric.is_passing():
                if metric_name == "accuracy":
                    recommendations.append(f"Low accuracy ({metric.value:.1%}) - review training data quality")
                elif metric_name == "precision":
                    recommendations.append(f"Low precision ({metric.value:.1%}) - reduce false positives")
                elif metric_name == "recall":
                    recommendations.append(f"Low recall ({metric.value:.1%}) - improve positive case detection")
                elif metric_name == "direction_accuracy":
                    recommendations.append(f"Poor direction prediction ({metric.value:.1%}) - review trend analysis")
        
        # Trend-based recommendations
        declining_trends = [name for name, trend in trends.items() if trend == TrendDirection.DECLINING]
        if len(declining_trends) > 2:
            recommendations.append("Multiple metrics declining - comprehensive model review recommended")
        
        volatile_trends = [name for name, trend in trends.items() if trend == TrendDirection.VOLATILE]
        if len(volatile_trends) > 1:
            recommendations.append("Performance volatility detected - increase evaluation frequency")
        
        # Default recommendations if none specific
        if not recommendations:
            if overall_grade in [PerformanceGrade.GOOD, PerformanceGrade.VERY_GOOD]:
                recommendations.append("Continue monitoring - performance within acceptable ranges")
            else:
                recommendations.append("Monitor performance trends closely")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _calculate_next_evaluation_date(self, grade: PerformanceGrade, trends: Dict[str, TrendDirection]) -> datetime:
        """Calculate when next evaluation should occur"""
        base_days = {
            PerformanceGrade.EXCELLENT: 14,  # 2 weeks
            PerformanceGrade.VERY_GOOD: 10,  # 10 days
            PerformanceGrade.GOOD: 7,       # 1 week
            PerformanceGrade.ACCEPTABLE: 5, # 5 days
            PerformanceGrade.POOR: 3,       # 3 days
            PerformanceGrade.FAILING: 1     # Daily
        }
        
        days = base_days.get(grade, 7)
        
        # Adjust based on trends
        declining_trends = sum(1 for trend in trends.values() if trend == TrendDirection.DECLINING)
        if declining_trends > 2:
            days = max(1, days - 2)  # Evaluate more frequently
        
        volatile_trends = sum(1 for trend in trends.values() if trend == TrendDirection.VOLATILE)
        if volatile_trends > 1:
            days = max(1, days - 1)  # Evaluate more frequently
        
        return datetime.now() + timedelta(days=days)
    
    def _calculate_benchmark_comparison(self, comparisons: List[SollIstComparison]) -> float:
        """Calculate how much better the model performs vs benchmark"""
        if not comparisons:
            return 0.0
        
        model_accuracy = mean([comp.accuracy_percentage for comp in comparisons]) / 100
        benchmark_accuracy = self._benchmark_performance.get('market_baseline', 0.52)
        
        return model_accuracy - benchmark_accuracy
    
    def _calculate_prediction_target_date(self, prediction_date: datetime, horizon: PredictionHorizon) -> datetime:
        """Calculate when the prediction should be evaluated"""
        horizon_days = {
            PredictionHorizon.ONE_WEEK: 7,
            PredictionHorizon.ONE_MONTH: 30,
            PredictionHorizon.THREE_MONTHS: 90,
            PredictionHorizon.TWELVE_MONTHS: 365
        }
        
        days = horizon_days.get(horizon, 30)
        return prediction_date + timedelta(days=days)
    
    def _update_performance_history(self, model_id: str, metrics: Dict[str, PerformanceMetric]) -> None:
        """Update performance history for trend analysis"""
        if model_id not in self._performance_history:
            self._performance_history[model_id] = []
        
        # Add all metrics to history
        for metric in metrics.values():
            self._performance_history[model_id].append(metric)
        
        # Keep only last 100 metrics per model (about 10 evaluation periods)
        if len(self._performance_history[model_id]) > 100:
            self._performance_history[model_id] = self._performance_history[model_id][-100:]
    
    def get_model_degradation_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for models showing performance degradation"""
        alerts = []
        
        for model_id, metrics in self._performance_history.items():
            recent_metrics = metrics[-20:]  # Last 20 metrics
            
            if len(recent_metrics) < 10:
                continue
            
            # Check for consistent degradation
            accuracy_metrics = [m for m in recent_metrics if m.metric_name == "accuracy"]
            
            if len(accuracy_metrics) >= 5:
                recent_accuracy = [m.value for m in accuracy_metrics[-5:]]
                older_accuracy = [m.value for m in accuracy_metrics[-10:-5]] if len(accuracy_metrics) >= 10 else recent_accuracy
                
                if len(older_accuracy) > 0:
                    recent_avg = mean(recent_accuracy)
                    older_avg = mean(older_accuracy)
                    
                    degradation = older_avg - recent_avg
                    
                    if degradation > 0.05:  # 5% degradation
                        alerts.append({
                            'model_id': model_id,
                            'alert_type': 'performance_degradation',
                            'severity': 'high' if degradation > 0.10 else 'medium',
                            'degradation_percentage': degradation * 100,
                            'recommended_action': 'retrain' if degradation > 0.10 else 'monitor',
                            'detected_at': datetime.now()
                        })
        
        return alerts
    
    def get_performance_summary_by_horizon(self) -> Dict[PredictionHorizon, Dict[str, float]]:
        """Get performance summary grouped by prediction horizon"""
        # This would typically analyze all models' performance by horizon
        # For now, return a simulated summary
        return {
            PredictionHorizon.ONE_WEEK: {
                'avg_accuracy': 0.78,
                'avg_precision': 0.75,
                'model_count': 5
            },
            PredictionHorizon.ONE_MONTH: {
                'avg_accuracy': 0.72,
                'avg_precision': 0.70,
                'model_count': 8
            },
            PredictionHorizon.THREE_MONTHS: {
                'avg_accuracy': 0.68,
                'avg_precision': 0.65,
                'model_count': 6
            },
            PredictionHorizon.TWELVE_MONTHS: {
                'avg_accuracy': 0.62,
                'avg_precision': 0.58,
                'model_count': 4
            }
        }