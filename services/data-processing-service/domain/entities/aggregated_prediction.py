"""
Data Processing Service - Aggregated Prediction Entity
Timeframe-Specific Aggregation v7.1 - Clean Architecture Domain Layer

Rich Domain Entity für aggregierte, zeitintervall-spezifische Vorhersagen
SOLID Principles: Single Responsibility, Mathematical Validation, Domain Behavior
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid
from .quality_metrics import QualityMetrics


class AggregationStrategy(Enum):
    """Verfügbare Aggregations-Strategien"""
    EQUAL_WEIGHT = "equal_weight"
    RECENCY_WEIGHT = "recency_weight" 
    VOLATILITY_WEIGHT = "volatility_weight"
    TREND_WEIGHT = "trend_weight"
    SEASONAL_WEIGHT = "seasonal_weight"
    HIERARCHICAL_AVERAGE = "hierarchical_average"


class TimeframeType(Enum):
    """Unterstützte Zeitintervall-Typen"""
    WEEKLY = "1W"
    MONTHLY = "1M"
    QUARTERLY = "3M"
    SEMI_ANNUAL = "6M"
    ANNUAL = "1Y"


@dataclass(frozen=True)
class TimeframeConfiguration:
    """Immutable Value Object für Zeitintervall-Konfiguration"""
    
    timeframe_type: TimeframeType
    data_collection_period_days: int  # Datensammlung-Zeitraum
    measurement_frequency: str        # "3x_daily", "daily", "weekly", "monthly"
    aggregation_strategy: AggregationStrategy
    min_data_threshold: int          # Minimum erforderliche Datenpunkte
    display_name: str
    
    def __post_init__(self):
        if self.data_collection_period_days <= 0:
            raise ValueError("Data collection period must be positive")
        if self.min_data_threshold <= 0:
            raise ValueError("Minimum data threshold must be positive")
    
    @classmethod
    def create_standard_configurations(cls) -> Dict[str, 'TimeframeConfiguration']:
        """Factory für Standard-Timeframe-Konfigurationen"""
        return {
            "1W": cls(
                timeframe_type=TimeframeType.WEEKLY,
                data_collection_period_days=7,
                measurement_frequency="3x_daily",
                aggregation_strategy=AggregationStrategy.EQUAL_WEIGHT,
                min_data_threshold=14,
                display_name="1 Woche"
            ),
            "1M": cls(
                timeframe_type=TimeframeType.MONTHLY,
                data_collection_period_days=30,
                measurement_frequency="daily",
                aggregation_strategy=AggregationStrategy.RECENCY_WEIGHT,
                min_data_threshold=20,
                display_name="1 Monat"
            ),
            "3M": cls(
                timeframe_type=TimeframeType.QUARTERLY,
                data_collection_period_days=90,
                measurement_frequency="daily",
                aggregation_strategy=AggregationStrategy.VOLATILITY_WEIGHT,
                min_data_threshold=60,
                display_name="3 Monate"
            ),
            "6M": cls(
                timeframe_type=TimeframeType.SEMI_ANNUAL,
                data_collection_period_days=180,
                measurement_frequency="weekly",
                aggregation_strategy=AggregationStrategy.TREND_WEIGHT,
                min_data_threshold=18,
                display_name="6 Monate"
            ),
            "1Y": cls(
                timeframe_type=TimeframeType.ANNUAL,
                data_collection_period_days=365,
                measurement_frequency="monthly",
                aggregation_strategy=AggregationStrategy.SEASONAL_WEIGHT,
                min_data_threshold=8,
                display_name="1 Jahr"
            )
        }


@dataclass
class AggregatedPrediction:
    """
    Core Domain Entity für zeitintervall-spezifische Prediction Aggregation
    
    DOMAIN RESPONSIBILITIES:
    - Mathematical validation der Aggregations-Ergebnisse
    - Quality Assessment und Confidence Calculation
    - Expiration und Staleness Detection
    - Statistical Analysis und Outlier Detection
    """
    
    # Identity & Context
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    company_name: str = ""
    market_region: str = "US"
    
    # Timeframe Configuration
    timeframe: str = "1M"
    timeframe_config: Optional[TimeframeConfiguration] = None
    aggregation_date: date = field(default_factory=date.today)
    target_prediction_date: date = field(default_factory=date.today)
    
    # Aggregated Values (Core Business Logic)
    aggregated_value: Decimal = Decimal('0.0')  # Hauptvorhersage in %
    confidence_score: float = 0.0               # 0.0 - 1.0 Vertrauen
    
    # Quality Assessment (Domain Validation)
    quality_metrics: Optional[QualityMetrics] = None
    
    # Statistical Metadata
    source_prediction_count: int = 0           # Anzahl aggregierter Predictions
    statistical_variance: Decimal = Decimal('0.0')
    standard_deviation: Decimal = Decimal('0.0')
    outlier_count: int = 0
    outlier_percentage: Decimal = Decimal('0.0')
    
    # Processing & Caching Metadata
    aggregation_strategy_used: AggregationStrategy = AggregationStrategy.HIERARCHICAL_AVERAGE
    calculation_timestamp: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=datetime.now)
    cache_hit: bool = False
    
    # Raw Data Metadata (für Debugging und Audit)
    source_data_summary: Dict[str, Any] = field(default_factory=dict)
    calculation_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Domain Validation nach Initialisierung"""
        self._validate_confidence_score()
        self._validate_aggregated_value()
        self._validate_source_count()
        
        # Default TimeframeConfiguration falls nicht gesetzt
        if self.timeframe_config is None:
            standard_configs = TimeframeConfiguration.create_standard_configurations()
            self.timeframe_config = standard_configs.get(self.timeframe)
        
        # Quality Metrics initialisieren falls nicht gesetzt
        if self.quality_metrics is None:
            self.quality_metrics = QualityMetrics.create_default()
    
    def _validate_confidence_score(self) -> None:
        """Validiere Confidence Score Bereich"""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
    
    def _validate_aggregated_value(self) -> None:
        """Validiere aggregierten Wert (Business Rules)"""
        if abs(self.aggregated_value) > Decimal('1000.0'):
            raise ValueError("Aggregated value exceeds reasonable bounds (±1000%)")
    
    def _validate_source_count(self) -> None:
        """Validiere Mindestanzahl Datenquellen"""
        min_threshold = (self.timeframe_config.min_data_threshold 
                        if self.timeframe_config else 5)
        if self.source_prediction_count < min_threshold:
            raise ValueError(f"Insufficient source predictions: {self.source_prediction_count} < {min_threshold}")
    
    # DOMAIN BEHAVIOR METHODS
    
    def is_expired(self) -> bool:
        """Prüfe ob Aggregation abgelaufen ist"""
        return datetime.now() > self.expires_at
    
    def is_high_quality(self) -> bool:
        """Prüfe ob Aggregation hohe Qualität hat"""
        if not self.quality_metrics:
            return False
        
        return (
            self.confidence_score >= 0.7 and
            self.quality_metrics.data_completeness >= Decimal('0.85') and
            self.quality_metrics.statistical_validity >= Decimal('0.80') and
            self.outlier_percentage <= Decimal('0.15')
        )
    
    def is_mathematically_valid(self) -> bool:
        """Validiere mathematische Konsistenz"""
        try:
            # Variance-Standardabweichung Konsistenz
            calculated_std = self.statistical_variance.sqrt() if self.statistical_variance > 0 else Decimal('0')
            std_deviation_check = abs(calculated_std - self.standard_deviation) < Decimal('0.001')
            
            # Outlier Percentage Konsistenz
            if self.source_prediction_count > 0:
                expected_outlier_pct = Decimal(str(self.outlier_count)) / Decimal(str(self.source_prediction_count))
                outlier_check = abs(expected_outlier_pct - self.outlier_percentage) < Decimal('0.01')
            else:
                outlier_check = self.outlier_percentage == Decimal('0')
            
            # Quality Score Konsistenz
            quality_check = (self.quality_metrics is not None and 
                           0 <= self.quality_metrics.confidence_score <= 1)
            
            return std_deviation_check and outlier_check and quality_check
            
        except Exception:
            return False
    
    def calculate_prediction_accuracy(self, actual_result: Decimal) -> Decimal:
        """Berechne Genauigkeit gegen tatsächliches Ergebnis"""
        if self.aggregated_value == 0:
            return Decimal('0')
        
        prediction_error = abs(actual_result - self.aggregated_value)
        relative_error = prediction_error / abs(self.aggregated_value)
        accuracy = Decimal('1.0') - relative_error
        
        return max(Decimal('0'), accuracy)  # Nie negativ
    
    def get_staleness_factor(self) -> float:
        """Berechne wie "veraltet" diese Aggregation ist (0.0 = frisch, 1.0 = sehr alt)"""
        age_seconds = (datetime.now() - self.calculation_timestamp).total_seconds()
        max_age_seconds = 24 * 60 * 60  # 24 Stunden als Maximum
        
        staleness = min(1.0, age_seconds / max_age_seconds)
        return staleness
    
    def get_comprehensive_quality_score(self) -> Decimal:
        """Berechne umfassenden Qualitäts-Score (0.0 - 1.0)"""
        if not self.quality_metrics:
            return Decimal('0.0')
        
        # Basis-Quality Metrics (40%)
        base_quality = (
            self.quality_metrics.data_completeness * Decimal('0.15') +
            self.quality_metrics.statistical_validity * Decimal('0.15') +
            Decimal(str(self.confidence_score)) * Decimal('0.10')
        )
        
        # Outlier Penalty (20%)
        outlier_score = max(Decimal('0'), Decimal('0.2') - self.outlier_percentage)
        
        # Data Volume Score (20%)
        min_threshold = Decimal(str(self.timeframe_config.min_data_threshold if self.timeframe_config else 10))
        volume_score = min(Decimal('0.2'), 
                          Decimal(str(self.source_prediction_count)) / min_threshold * Decimal('0.2'))
        
        # Staleness Penalty (20%)
        staleness_penalty = Decimal(str(self.get_staleness_factor())) * Decimal('0.2')
        freshness_score = Decimal('0.2') - staleness_penalty
        
        comprehensive_score = base_quality + outlier_score + volume_score + freshness_score
        return min(Decimal('1.0'), max(Decimal('0.0'), comprehensive_score))
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Export für Audit und Debugging"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "aggregated_value": str(self.aggregated_value),
            "confidence_score": self.confidence_score,
            "comprehensive_quality_score": str(self.get_comprehensive_quality_score()),
            "source_prediction_count": self.source_prediction_count,
            "outlier_percentage": str(self.outlier_percentage),
            "aggregation_strategy": self.aggregation_strategy_used.value,
            "calculation_timestamp": self.calculation_timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired(),
            "is_high_quality": self.is_high_quality(),
            "is_mathematically_valid": self.is_mathematically_valid(),
            "staleness_factor": self.get_staleness_factor()
        }
    
    @classmethod 
    def create_from_raw_predictions(cls, 
                                   symbol: str, 
                                   company_name: str,
                                   timeframe: str,
                                   raw_predictions: List[Dict[str, Any]],
                                   aggregation_strategy: AggregationStrategy = AggregationStrategy.HIERARCHICAL_AVERAGE) -> 'AggregatedPrediction':
        """Factory Method für Erstellung aus Raw Prediction Data"""
        
        if not raw_predictions:
            raise ValueError("Raw predictions cannot be empty")
        
        # Basis-Aggregation (vereinfacht für Factory)
        prediction_values = [Decimal(str(pred.get('predicted_profit', 0))) for pred in raw_predictions]
        aggregated_value = sum(prediction_values) / len(prediction_values)
        
        # Statistische Kennzahlen
        variance = sum((val - aggregated_value) ** 2 for val in prediction_values) / len(prediction_values)
        std_dev = variance.sqrt() if variance > 0 else Decimal('0')
        
        # Outlier Detection (IQR-basiert)
        sorted_values = sorted(prediction_values)
        n = len(sorted_values)
        q1_idx, q3_idx = n // 4, 3 * n // 4
        if n > 4:
            q1, q3 = sorted_values[q1_idx], sorted_values[q3_idx]
            iqr = q3 - q1
            outlier_threshold = iqr * Decimal('1.5')
            outliers = [v for v in prediction_values if abs(v - aggregated_value) > outlier_threshold]
            outlier_count = len(outliers)
        else:
            outlier_count = 0
        
        outlier_percentage = Decimal(str(outlier_count)) / Decimal(str(len(prediction_values)))
        
        # Confidence basierend auf Konsensus
        confidence = float(1.0 - min(1.0, float(std_dev) / max(0.01, float(abs(aggregated_value)))))
        
        return cls(
            symbol=symbol,
            company_name=company_name,
            timeframe=timeframe,
            aggregated_value=aggregated_value,
            confidence_score=confidence,
            source_prediction_count=len(raw_predictions),
            statistical_variance=variance,
            standard_deviation=std_dev,
            outlier_count=outlier_count,
            outlier_percentage=outlier_percentage,
            aggregation_strategy_used=aggregation_strategy,
            source_data_summary={
                "raw_prediction_count": len(raw_predictions),
                "min_value": str(min(prediction_values)),
                "max_value": str(max(prediction_values)),
                "median_value": str(sorted_values[n // 2])
            }
        )