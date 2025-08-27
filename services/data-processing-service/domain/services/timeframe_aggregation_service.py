"""
Data Processing Service - Timeframe Aggregation Domain Service
Timeframe-Specific Aggregation v7.1 - Clean Architecture Domain Layer

Domain Service für mathematische Aggregation und Quality Control
SOLID Principles: Single Responsibility, Dependency Inversion, Mathematical Accuracy
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
import statistics
import math
from ..entities.aggregated_prediction import AggregatedPrediction, TimeframeConfiguration, AggregationStrategy
from ..value_objects.quality_metrics import QualityMetrics


class TimeframeAggregationService:
    """
    Domain Service für zeitintervall-spezifische Prediction Aggregation
    
    DOMAIN RESPONSIBILITIES:
    - Hierarchical Averaging mit mathematischer Validierung
    - IQR-based Statistical Outlier Detection  
    - Multi-dimensional Quality Assessment
    - Strategy Pattern für verschiedene Aggregations-Algorithmen
    - Mathematical Correctness Validation (>99.9% Accuracy)
    """
    
    def __init__(self):
        self._outlier_detection_multiplier = Decimal('1.5')  # IQR multiplier
        self._minimum_sample_size = 3
        self._quality_threshold = Decimal('0.70')
        
    def calculate_hierarchical_average(self,
                                     raw_data: List[Dict[str, Any]],
                                     timeframe_config: TimeframeConfiguration) -> AggregatedPrediction:
        """
        Berechne hierarchical average mit umfassender Quality Control
        
        ALGORITHMUS:
        1. Input Validation
        2. Statistical Outlier Detection (IQR-based)
        3. Weighted Aggregation basierend auf Strategy
        4. Quality Metrics Calculation
        5. Mathematical Correctness Validation
        6. Domain Entity Creation
        """
        if not raw_data:
            raise ValueError("Raw data cannot be empty")
        
        if len(raw_data) < self._minimum_sample_size:
            raise ValueError(f"Insufficient data points: {len(raw_data)} < {self._minimum_sample_size}")
        
        # Extract und validate prediction values
        prediction_values = self._extract_prediction_values(raw_data)
        
        # Statistical Outlier Detection
        cleaned_values, outlier_info = self._detect_and_handle_outliers(prediction_values)
        
        # Strategy-based Aggregation
        aggregated_value = self._apply_aggregation_strategy(
            cleaned_values, raw_data, timeframe_config.aggregation_strategy
        )
        
        # Statistical Calculations
        stats = self._calculate_statistical_metrics(cleaned_values, outlier_info)
        
        # Quality Assessment
        quality_metrics = self._assess_aggregation_quality(
            raw_data, cleaned_values, outlier_info, stats
        )
        
        # Mathematical Validation
        self._validate_mathematical_correctness(aggregated_value, stats, quality_metrics)
        
        # Create Domain Entity
        symbol = raw_data[0].get('symbol', 'UNKNOWN')
        company_name = raw_data[0].get('company_name', 'Unknown Company')
        
        aggregated_prediction = AggregatedPrediction(
            symbol=symbol,
            company_name=company_name,
            timeframe=timeframe_config.timeframe_type.value,
            timeframe_config=timeframe_config,
            aggregated_value=aggregated_value,
            confidence_score=float(quality_metrics.confidence_score),
            quality_metrics=quality_metrics,
            source_prediction_count=len(raw_data),
            statistical_variance=stats['variance'],
            standard_deviation=stats['std_deviation'],
            outlier_count=outlier_info['outlier_count'],
            outlier_percentage=outlier_info['outlier_percentage'],
            aggregation_strategy_used=timeframe_config.aggregation_strategy,
            calculation_timestamp=datetime.now(),
            source_data_summary=self._create_data_summary(raw_data, cleaned_values, outlier_info),
            calculation_metadata={
                'algorithm_version': 'v7.1',
                'outlier_detection_method': 'IQR',
                'quality_assessment_dimensions': 8,
                'mathematical_validation_passed': True
            }
        )
        
        return aggregated_prediction
    
    def _extract_prediction_values(self, raw_data: List[Dict[str, Any]]) -> List[Decimal]:
        """Extrahiere und validiere Prediction Values"""
        prediction_values = []
        
        for data_point in raw_data:
            # Try multiple potential field names
            value = None
            for field_name in ['predicted_profit', 'aggregated_value', 'prediction_value', 'value']:
                if field_name in data_point:
                    value = data_point[field_name]
                    break
            
            if value is None:
                raise ValueError(f"No prediction value found in data point: {data_point.keys()}")
            
            try:
                decimal_value = Decimal(str(value))
                if abs(decimal_value) > Decimal('1000'):  # Sanity check
                    raise ValueError(f"Prediction value outside reasonable bounds: {decimal_value}")
                prediction_values.append(decimal_value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid prediction value '{value}': {e}")
        
        return prediction_values
    
    def _detect_and_handle_outliers(self, 
                                   prediction_values: List[Decimal]) -> Tuple[List[Decimal], Dict[str, Any]]:
        """
        IQR-based Statistical Outlier Detection
        
        ALGORITHMUS:
        1. Sortiere Werte
        2. Berechne Q1, Q3, IQR
        3. Identifiziere Outliers (> Q3 + 1.5*IQR oder < Q1 - 1.5*IQR)
        4. Return cleaned values und outlier info
        """
        if len(prediction_values) < 4:
            # Zu wenige Werte für IQR-Analyse
            return prediction_values, {
                'outlier_count': 0,
                'outlier_percentage': Decimal('0.0'),
                'outlier_values': [],
                'outlier_threshold_lower': None,
                'outlier_threshold_upper': None
            }
        
        sorted_values = sorted(prediction_values)
        n = len(sorted_values)
        
        # Quartile berechnen
        q1_index = n // 4
        q3_index = 3 * n // 4
        q1 = sorted_values[q1_index]
        q3 = sorted_values[q3_index]
        iqr = q3 - q1
        
        # Outlier Thresholds
        lower_threshold = q1 - self._outlier_detection_multiplier * iqr
        upper_threshold = q3 + self._outlier_detection_multiplier * iqr
        
        # Identifiziere Outliers
        outliers = []
        cleaned_values = []
        
        for value in prediction_values:
            if value < lower_threshold or value > upper_threshold:
                outliers.append(value)
            else:
                cleaned_values.append(value)
        
        # Mindestens 50% der Daten behalten
        if len(cleaned_values) < len(prediction_values) * 0.5:
            cleaned_values = prediction_values  # Behalte alle bei aggressiver Outlier Detection
            outliers = []
        
        outlier_count = len(outliers)
        outlier_percentage = Decimal(str(outlier_count)) / Decimal(str(len(prediction_values)))
        
        outlier_info = {
            'outlier_count': outlier_count,
            'outlier_percentage': outlier_percentage,
            'outlier_values': [float(v) for v in outliers],
            'outlier_threshold_lower': float(lower_threshold),
            'outlier_threshold_upper': float(upper_threshold),
            'q1': float(q1),
            'q3': float(q3),
            'iqr': float(iqr)
        }
        
        return cleaned_values, outlier_info
    
    def _apply_aggregation_strategy(self,
                                  cleaned_values: List[Decimal],
                                  raw_data: List[Dict[str, Any]],
                                  strategy: AggregationStrategy) -> Decimal:
        """Apply gewählte Aggregations-Strategie"""
        
        if strategy == AggregationStrategy.EQUAL_WEIGHT:
            return self._calculate_simple_average(cleaned_values)
        
        elif strategy == AggregationStrategy.RECENCY_WEIGHT:
            return self._calculate_recency_weighted_average(cleaned_values, raw_data)
        
        elif strategy == AggregationStrategy.VOLATILITY_WEIGHT:
            return self._calculate_volatility_weighted_average(cleaned_values, raw_data)
        
        elif strategy == AggregationStrategy.TREND_WEIGHT:
            return self._calculate_trend_weighted_average(cleaned_values, raw_data)
        
        elif strategy == AggregationStrategy.SEASONAL_WEIGHT:
            return self._calculate_seasonal_weighted_average(cleaned_values, raw_data)
        
        elif strategy == AggregationStrategy.HIERARCHICAL_AVERAGE:
            return self._calculate_hierarchical_weighted_average(cleaned_values, raw_data)
        
        else:
            # Fallback zu simple average
            return self._calculate_simple_average(cleaned_values)
    
    def _calculate_simple_average(self, values: List[Decimal]) -> Decimal:
        """Berechne einfachen arithmetischen Mittelwert"""
        if not values:
            return Decimal('0.0')
        
        total = sum(values)
        count = Decimal(str(len(values)))
        return (total / count).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def _calculate_recency_weighted_average(self, 
                                          values: List[Decimal],
                                          raw_data: List[Dict[str, Any]]) -> Decimal:
        """Gewichteter Durchschnitt basierend auf Recency (neuere Daten = höheres Gewicht)"""
        if not values or len(values) != len(raw_data):
            return self._calculate_simple_average(values)
        
        weighted_sum = Decimal('0.0')
        total_weight = Decimal('0.0')
        
        # Sortiere nach timestamp (falls verfügbar)
        data_with_values = list(zip(raw_data, values))
        data_with_values.sort(key=lambda x: x[0].get('timestamp', '1970-01-01'), reverse=True)
        
        for i, (data_point, value) in enumerate(data_with_values):
            # Exponential decay weight: neuer = höheres Gewicht
            weight = Decimal(str(math.exp(-i * 0.1)))  # Decay factor 0.1
            weighted_sum += value * weight
            total_weight += weight
        
        if total_weight > 0:
            return (weighted_sum / total_weight).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        else:
            return self._calculate_simple_average(values)
    
    def _calculate_volatility_weighted_average(self,
                                             values: List[Decimal],
                                             raw_data: List[Dict[str, Any]]) -> Decimal:
        """Gewichteter Durchschnitt basierend auf inverser Volatilität (niedrige Volatilität = höheres Gewicht)"""
        if not values:
            return Decimal('0.0')
        
        # Berechne lokale Volatilität für jeden Wert (basierend auf Abweichung vom Median)
        median_value = Decimal(str(statistics.median([float(v) for v in values])))
        
        weighted_sum = Decimal('0.0')
        total_weight = Decimal('0.0')
        
        for value in values:
            # Inverse Volatilitäts-Gewichtung
            deviation = abs(value - median_value)
            volatility = max(deviation, Decimal('0.01'))  # Minimum um Division by Zero zu vermeiden
            weight = Decimal('1.0') / volatility
            
            weighted_sum += value * weight
            total_weight += weight
        
        if total_weight > 0:
            return (weighted_sum / total_weight).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        else:
            return self._calculate_simple_average(values)
    
    def _calculate_trend_weighted_average(self,
                                        values: List[Decimal],
                                        raw_data: List[Dict[str, Any]]) -> Decimal:
        """Gewichteter Durchschnitt mit Trend-Berücksichtigung"""
        if len(values) < 3:
            return self._calculate_simple_average(values)
        
        # Einfache Trend-Erkennung über Moving Average
        trend_weights = []
        
        for i in range(len(values)):
            if i < 2:
                trend_weights.append(Decimal('1.0'))  # Neutrales Gewicht
            else:
                # Trend basierend auf letzten 3 Werten
                recent_values = values[max(0, i-2):i+1]
                if len(recent_values) >= 2:
                    trend = recent_values[-1] - recent_values[0]
                    # Positive Trends erhalten höhere Gewichte
                    trend_weight = Decimal('1.0') + (trend / Decimal('100'))  # Normalisiert
                    trend_weight = max(Decimal('0.1'), min(Decimal('2.0'), trend_weight))  # Begrenze Gewichte
                    trend_weights.append(trend_weight)
                else:
                    trend_weights.append(Decimal('1.0'))
        
        # Gewichteter Durchschnitt
        weighted_sum = sum(v * w for v, w in zip(values, trend_weights))
        total_weight = sum(trend_weights)
        
        if total_weight > 0:
            return (weighted_sum / total_weight).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        else:
            return self._calculate_simple_average(values)
    
    def _calculate_seasonal_weighted_average(self,
                                           values: List[Decimal],
                                           raw_data: List[Dict[str, Any]]) -> Decimal:
        """Gewichteter Durchschnitt mit saisonaler Berücksichtigung"""
        # Vereinfachte saisonale Gewichtung basierend auf Monat
        current_month = datetime.now().month
        
        weighted_sum = Decimal('0.0')
        total_weight = Decimal('0.0')
        
        for i, value in enumerate(values):
            # Saisonales Gewicht basierend auf "Entfernung" zum aktuellen Monat
            if i < len(raw_data):
                timestamp_str = raw_data[i].get('timestamp', datetime.now().isoformat())
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    month_diff = abs(current_month - timestamp.month)
                    month_diff = min(month_diff, 12 - month_diff)  # Berücksichtige Jahr-Wrap
                    seasonal_weight = Decimal('2.0') - (Decimal(str(month_diff)) / Decimal('6'))  # Max 6 Monate Differenz
                    seasonal_weight = max(Decimal('0.5'), seasonal_weight)
                except:
                    seasonal_weight = Decimal('1.0')  # Fallback
            else:
                seasonal_weight = Decimal('1.0')
            
            weighted_sum += value * seasonal_weight
            total_weight += seasonal_weight
        
        if total_weight > 0:
            return (weighted_sum / total_weight).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        else:
            return self._calculate_simple_average(values)
    
    def _calculate_hierarchical_weighted_average(self,
                                               values: List[Decimal],
                                               raw_data: List[Dict[str, Any]]) -> Decimal:
        """
        Hierarchical Weighted Average - Kombination aller Strategien
        
        ALGORITHMUS:
        1. Berechne alle Strategy-Werte
        2. Gewichte Strategien basierend auf Data Quality
        3. Berechne Meta-Ensemble Durchschnitt
        """
        if not values:
            return Decimal('0.0')
        
        # Berechne alle Strategy Results
        strategies_results = {
            'simple': self._calculate_simple_average(values),
            'recency': self._calculate_recency_weighted_average(values, raw_data),
            'volatility': self._calculate_volatility_weighted_average(values, raw_data),
            'trend': self._calculate_trend_weighted_average(values, raw_data),
            'seasonal': self._calculate_seasonal_weighted_average(values, raw_data)
        }
        
        # Strategy Gewichte basierend auf Datenqualität und -größe
        data_size = len(values)
        strategy_weights = {
            'simple': Decimal('0.30'),     # Basis-Gewicht
            'recency': Decimal('0.25'),    # Wichtig für aktuelle Trends
            'volatility': Decimal('0.20'), # Risiko-Adjustierung
            'trend': Decimal('0.15') if data_size >= 5 else Decimal('0.05'),  # Trend braucht mehr Daten
            'seasonal': Decimal('0.10') if data_size >= 10 else Decimal('0.05')  # Seasonal braucht viele Daten
        }
        
        # Normalisiere Gewichte
        total_strategy_weight = sum(strategy_weights.values())
        strategy_weights = {k: v / total_strategy_weight for k, v in strategy_weights.items()}
        
        # Berechne Hierarchical Average
        hierarchical_sum = sum(result * strategy_weights[strategy] 
                              for strategy, result in strategies_results.items())
        
        return hierarchical_sum.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def _calculate_statistical_metrics(self, 
                                     values: List[Decimal],
                                     outlier_info: Dict[str, Any]) -> Dict[str, Decimal]:
        """Berechne umfassende statistische Kennzahlen"""
        if not values:
            return {
                'variance': Decimal('0.0'),
                'std_deviation': Decimal('0.0'),
                'mean': Decimal('0.0'),
                'median': Decimal('0.0'),
                'min': Decimal('0.0'),
                'max': Decimal('0.0')
            }
        
        mean = sum(values) / len(values)
        
        # Variance Calculation
        if len(values) > 1:
            variance_sum = sum((v - mean) ** 2 for v in values)
            variance = variance_sum / Decimal(str(len(values) - 1))  # Sample variance
            std_deviation = variance.sqrt() if variance > 0 else Decimal('0.0')
        else:
            variance = Decimal('0.0')
            std_deviation = Decimal('0.0')
        
        sorted_values = sorted(values)
        median = sorted_values[len(sorted_values) // 2]
        
        return {
            'variance': variance.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
            'std_deviation': std_deviation.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
            'mean': mean.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            'median': median.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            'min': min(values).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            'max': max(values).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        }
    
    def _assess_aggregation_quality(self,
                                   raw_data: List[Dict[str, Any]],
                                   cleaned_values: List[Decimal],
                                   outlier_info: Dict[str, Any],
                                   stats: Dict[str, Decimal]) -> QualityMetrics:
        """Umfassende Quality Assessment"""
        
        # Data Completeness Score
        expected_min_data = 10  # Business Rule
        data_completeness = min(Decimal('1.0'), Decimal(str(len(raw_data))) / Decimal(str(expected_min_data)))
        
        # Statistical Validity basierend auf Sample Size und Variance
        sample_size_score = min(Decimal('1.0'), Decimal(str(len(cleaned_values))) / Decimal('5'))
        variance_score = Decimal('1.0') - min(Decimal('1.0'), stats['variance'] / Decimal('100'))
        statistical_validity = (sample_size_score + variance_score) / Decimal('2')
        
        # Confidence Score basierend auf Consensus und Data Quality
        if stats['std_deviation'] > 0 and stats['mean'] != 0:
            coefficient_of_variation = abs(stats['std_deviation'] / stats['mean'])
            confidence_score = Decimal('1.0') - min(Decimal('1.0'), coefficient_of_variation)
        else:
            confidence_score = Decimal('0.5')  # Default
        
        # Temporal Consistency (vereinfacht)
        temporal_consistency = Decimal('0.8')  # Standard-Annahme
        
        # Cross-Model Agreement (basierend auf Variance)
        if stats['variance'] > 0:
            cross_model_agreement = Decimal('1.0') - min(Decimal('1.0'), stats['variance'] / Decimal('50'))
        else:
            cross_model_agreement = Decimal('1.0')
        
        # Data Freshness Score (vereinfacht - könnte aus timestamp berechnet werden)
        data_freshness_score = Decimal('0.9')  # Standard-Annahme für aktuelle Implementation
        
        # Convergence Stability
        convergence_stability = min(Decimal('1.0'), Decimal('1.0') - stats['variance'] / Decimal('200'))
        
        return QualityMetrics(
            confidence_score=confidence_score,
            data_completeness=data_completeness,
            statistical_validity=statistical_validity,
            outlier_percentage=outlier_info['outlier_percentage'],
            temporal_consistency=temporal_consistency,
            cross_model_agreement=cross_model_agreement,
            data_freshness_score=data_freshness_score,
            convergence_stability=convergence_stability,
            assessment_timestamp=datetime.now().isoformat()
        )
    
    def _validate_mathematical_correctness(self,
                                         aggregated_value: Decimal,
                                         stats: Dict[str, Decimal],
                                         quality_metrics: QualityMetrics) -> None:
        """Validiere mathematische Korrektheit (>99.9% Accuracy Requirement)"""
        
        # Sanity Checks
        if abs(aggregated_value) > Decimal('1000'):
            raise ValueError(f"Aggregated value outside reasonable bounds: {aggregated_value}")
        
        # Variance-StandardDeviation Consistency
        if stats['variance'] > 0:
            expected_std = stats['variance'].sqrt()
            std_diff = abs(expected_std - stats['std_deviation'])
            if std_diff > Decimal('0.001'):
                raise ValueError(f"Statistical inconsistency: variance-std mismatch {std_diff}")
        
        # Quality Metrics Bounds
        if not (Decimal('0.0') <= quality_metrics.confidence_score <= Decimal('1.0')):
            raise ValueError(f"Confidence score out of bounds: {quality_metrics.confidence_score}")
        
        # Aggregated Value vs. Mean Plausibility
        mean_diff = abs(aggregated_value - stats['mean'])
        if mean_diff > stats['std_deviation'] * Decimal('3'):  # 3-Sigma Rule
            raise ValueError(f"Aggregated value too far from mean: {mean_diff} > 3σ")
    
    def _create_data_summary(self,
                            raw_data: List[Dict[str, Any]],
                            cleaned_values: List[Decimal],
                            outlier_info: Dict[str, Any]) -> Dict[str, Any]:
        """Erstelle umfassendes Data Summary für Audit"""
        
        return {
            'raw_data_count': len(raw_data),
            'cleaned_data_count': len(cleaned_values),
            'outlier_detection_summary': {
                'outlier_count': outlier_info['outlier_count'],
                'outlier_percentage': float(outlier_info['outlier_percentage']),
                'outlier_threshold_range': [
                    outlier_info.get('outlier_threshold_lower'),
                    outlier_info.get('outlier_threshold_upper')
                ]
            },
            'value_range': {
                'min_cleaned': float(min(cleaned_values)) if cleaned_values else 0.0,
                'max_cleaned': float(max(cleaned_values)) if cleaned_values else 0.0,
                'raw_value_range': [
                    min(float(d.get('predicted_profit', 0)) for d in raw_data),
                    max(float(d.get('predicted_profit', 0)) for d in raw_data)
                ]
            },
            'processing_timestamp': datetime.now().isoformat(),
            'algorithm_version': 'v7.1_hierarchical_aggregation'
        }