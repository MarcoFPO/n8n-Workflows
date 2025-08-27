# 🔧 Low-Level Design (LLD) - Timeframe Aggregation v7.0

## 🎯 **Zeitintervall-spezifische Aggregation - Clean Architecture Integration**

### 🏗️ **System Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                   📊 Aggregation Domain Layer                   │
│              Clean Architecture Core Business Logic             │
└─┬───────────────────────────────────────────────────────────┬───┘
  │                                                           │
┌─▼──────────────────────────────────────┐ ┌─▼───────────────────┐
│        🔍 Application Layer            │ │   🌐 Presentation    │
│    Use Cases & Service Orchestration   │ │      Layer API       │
└─┬──────────────────────────────────────┘ └─┬───────────────────┘
  │                                          │
┌─▼──────────────────────────────────────────▼───────────────────┐
│              🗄️ Infrastructure Layer                           │
│     PostgreSQL + Redis + Event Bus Integration                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ **Domain Layer - Core Business Logic**

### 📊 **Domain Entities**

```python
# domain/entities/aggregated_prediction.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional
from uuid import uuid4, UUID

@dataclass(frozen=True)
class TimeframeConfiguration:
    """Value Object für Zeitintervall-Konfiguration"""
    interval_type: str  # "minutes", "hours", "days", "weeks", "months"
    interval_value: int  # 1, 5, 15, 30, 60, etc.
    display_name: str    # "1M", "1W", "3M", "12M"
    horizon_days: int    # Tage bis zum Zieldatum
    
    def __post_init__(self):
        if self.interval_value <= 0:
            raise ValueError("Interval value must be positive")
        if self.interval_type not in ["minutes", "hours", "days", "weeks", "months"]:
            raise ValueError("Invalid interval type")

@dataclass
class AggregatedPrediction:
    """Entity für aggregierte Vorhersagen"""
    id: UUID
    symbol: str
    company_name: str
    market_region: str
    timeframe_config: TimeframeConfiguration
    aggregation_date: date
    target_date: date
    
    # Aggregierte Werte
    predicted_value: Decimal
    confidence_score: float  # 0.0 - 1.0
    quality_score: float     # 0.0 - 1.0
    
    # Statistische Metriken
    data_points_count: int
    variance: float
    standard_deviation: float
    
    # Metadaten
    aggregation_strategy: str  # "weighted_average", "median", "ensemble"
    created_at: datetime
    last_updated: datetime
    
    def __post_init__(self):
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if self.quality_score < 0.0 or self.quality_score > 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")
        if self.data_points_count <= 0:
            raise ValueError("Data points count must be positive")

@dataclass
class AggregationStrategy:
    """Strategy Pattern für verschiedene Aggregationsmethoden"""
    strategy_type: str  # "weighted_average", "median", "mode", "ensemble"
    parameters: Dict[str, float]  # Konfigurationsparameter
    quality_threshold: float  # Mindestqualität für Akzeptanz
    
    def is_valid(self) -> bool:
        """Validiert Strategy-Konfiguration"""
        return (
            self.strategy_type in ["weighted_average", "median", "mode", "ensemble"] and
            self.quality_threshold >= 0.0 and 
            self.quality_threshold <= 1.0
        )

@dataclass
class AggregationResult:
    """Immutable Result Value Object"""
    symbol: str
    timeframe_config: TimeframeConfiguration
    aggregated_prediction: AggregatedPrediction
    quality_metrics: 'QualityMetrics'
    processing_metadata: Dict[str, any]
    
    def to_dto(self) -> 'AggregatedPredictionDTO':
        """Konvertiert zu Application Layer DTO"""
        from application.dtos.aggregated_prediction_dto import AggregatedPredictionDTO
        return AggregatedPredictionDTO(
            id=str(self.aggregated_prediction.id),
            symbol=self.symbol,
            company_name=self.aggregated_prediction.company_name,
            market_region=self.aggregated_prediction.market_region,
            timeframe_display=self.timeframe_config.display_name,
            predicted_value=float(self.aggregated_prediction.predicted_value),
            confidence_score=self.aggregated_prediction.confidence_score,
            quality_score=self.aggregated_prediction.quality_score,
            target_date=self.aggregated_prediction.target_date.isoformat(),
            data_points_count=self.aggregated_prediction.data_points_count,
            aggregation_strategy=self.aggregated_prediction.aggregation_strategy
        )
```

### 🎯 **Domain Services**

```python
# domain/services/timeframe_aggregation_service.py
from typing import List, Dict, Optional
from decimal import Decimal
import numpy as np
from statistics import median, mode
from .mathematical_validation_service import MathematicalValidationService

class TimeframeAggregationService:
    """
    Core Business Logic für Zeitintervall-Aggregation
    SINGLE RESPONSIBILITY: Nur Aggregations-Logik
    OPEN/CLOSED: Erweiterbar durch Strategy Pattern
    """
    
    def __init__(self, validation_service: MathematicalValidationService):
        self._validation_service = validation_service
        self._strategies = {
            "weighted_average": self._weighted_average_strategy,
            "median": self._median_strategy,
            "ensemble": self._ensemble_strategy
        }
    
    def calculate_aggregated_prediction(
        self, 
        raw_predictions: List[Dict],
        timeframe_config: TimeframeConfiguration,
        strategy: AggregationStrategy
    ) -> AggregatedPrediction:
        """
        CORE BUSINESS LOGIC: Berechnet aggregierte Vorhersage
        """
        # 1. Validierung der Eingabedaten
        validated_data = self._validation_service.validate_prediction_data(raw_predictions)
        
        if len(validated_data) == 0:
            raise ValueError("No valid prediction data available for aggregation")
        
        # 2. Strategy Pattern Anwendung
        if strategy.strategy_type not in self._strategies:
            raise ValueError(f"Unknown aggregation strategy: {strategy.strategy_type}")
        
        aggregation_func = self._strategies[strategy.strategy_type]
        
        # 3. Aggregation durchführen
        aggregation_result = aggregation_func(validated_data, strategy.parameters)
        
        # 4. Quality Metrics berechnen
        quality_metrics = self._calculate_quality_metrics(
            raw_predictions, aggregation_result, strategy
        )
        
        # 5. Domain Entity erstellen
        return AggregatedPrediction(
            id=uuid4(),
            symbol=validated_data[0]["symbol"],
            company_name=validated_data[0]["company_name"],
            market_region=validated_data[0]["market_region"],
            timeframe_config=timeframe_config,
            aggregation_date=date.today(),
            target_date=date.today() + timedelta(days=timeframe_config.horizon_days),
            predicted_value=Decimal(str(aggregation_result["predicted_value"])),
            confidence_score=aggregation_result["confidence_score"],
            quality_score=quality_metrics.overall_quality,
            data_points_count=len(validated_data),
            variance=aggregation_result["variance"],
            standard_deviation=aggregation_result["std_dev"],
            aggregation_strategy=strategy.strategy_type,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
    
    def _weighted_average_strategy(self, data: List[Dict], params: Dict) -> Dict:
        """Gewichtete Durchschnitts-Strategie"""
        total_weight = 0.0
        weighted_sum = 0.0
        confidence_values = []
        
        for prediction in data:
            weight = prediction.get("confidence", 1.0) * params.get("base_weight", 1.0)
            weighted_sum += prediction["predicted_value"] * weight
            total_weight += weight
            confidence_values.append(prediction.get("confidence", 0.5))
        
        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")
        
        predicted_value = weighted_sum / total_weight
        values = [p["predicted_value"] for p in data]
        
        return {
            "predicted_value": predicted_value,
            "confidence_score": np.mean(confidence_values),
            "variance": np.var(values),
            "std_dev": np.std(values)
        }
    
    def _median_strategy(self, data: List[Dict], params: Dict) -> Dict:
        """Median-basierte robuste Aggregation"""
        values = [p["predicted_value"] for p in data]
        confidence_values = [p.get("confidence", 0.5) for p in data]
        
        predicted_value = median(values)
        
        return {
            "predicted_value": predicted_value,
            "confidence_score": median(confidence_values),
            "variance": np.var(values),
            "std_dev": np.std(values)
        }
    
    def _ensemble_strategy(self, data: List[Dict], params: Dict) -> Dict:
        """Ensemble-Methode kombiniert mehrere Strategien"""
        # Gewichteter Durchschnitt (60%)
        weighted_result = self._weighted_average_strategy(data, params)
        
        # Median (40%)
        median_result = self._median_strategy(data, params)
        
        # Ensemble Kombination
        ensemble_weight_avg = params.get("weighted_avg_weight", 0.6)
        ensemble_weight_median = 1.0 - ensemble_weight_avg
        
        predicted_value = (
            weighted_result["predicted_value"] * ensemble_weight_avg +
            median_result["predicted_value"] * ensemble_weight_median
        )
        
        confidence_score = (
            weighted_result["confidence_score"] * ensemble_weight_avg +
            median_result["confidence_score"] * ensemble_weight_median
        )
        
        values = [p["predicted_value"] for p in data]
        
        return {
            "predicted_value": predicted_value,
            "confidence_score": confidence_score,
            "variance": np.var(values),
            "std_dev": np.std(values)
        }
    
    def _calculate_quality_metrics(
        self, 
        raw_data: List[Dict], 
        aggregation_result: Dict,
        strategy: AggregationStrategy
    ) -> 'QualityMetrics':
        """Berechnet umfassende Qualitätsmetriken"""
        from domain.value_objects.quality_metrics import QualityMetrics
        
        values = [p["predicted_value"] for p in raw_data]
        
        # Data Quality Score (0.0 - 1.0)
        data_completeness = len(raw_data) / max(len(raw_data), 10)  # Normiert auf min. 10 Datenpunkte
        data_consistency = 1.0 - (aggregation_result["std_dev"] / abs(aggregation_result["predicted_value"]) if aggregation_result["predicted_value"] != 0 else 0.0)
        data_quality = min(1.0, max(0.0, (data_completeness + data_consistency) / 2.0))
        
        # Prediction Quality Score
        avg_confidence = np.mean([p.get("confidence", 0.5) for p in raw_data])
        prediction_spread = aggregation_result["std_dev"] / (abs(aggregation_result["predicted_value"]) + 1e-6)
        prediction_quality = min(1.0, max(0.0, avg_confidence * (1.0 - min(1.0, prediction_spread))))
        
        # Overall Quality Score
        overall_quality = (data_quality * 0.4) + (prediction_quality * 0.6)
        
        return QualityMetrics(
            data_quality_score=data_quality,
            prediction_quality_score=prediction_quality,
            overall_quality=overall_quality,
            data_completeness=data_completeness,
            data_consistency=data_consistency,
            confidence_distribution=np.std([p.get("confidence", 0.5) for p in raw_data]),
            outlier_count=self._count_outliers(values),
            quality_threshold_met=overall_quality >= strategy.quality_threshold
        )
    
    def _count_outliers(self, values: List[float]) -> int:
        """Zählt Ausreißer mit IQR-Methode"""
        if len(values) < 4:
            return 0
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        return len(outliers)
```

### 🔬 **Mathematical Validation Service**

```python
# domain/services/mathematical_validation_service.py
from typing import List, Dict
import numpy as np

class MathematicalValidationService:
    """
    Mathematische Validierung und Qualitätssicherung
    SINGLE RESPONSIBILITY: Nur Datenvalidierung
    """
    
    def __init__(self, 
                 min_data_points: int = 3,
                 max_std_dev_ratio: float = 0.5,
                 confidence_threshold: float = 0.1):
        self.min_data_points = min_data_points
        self.max_std_dev_ratio = max_std_dev_ratio
        self.confidence_threshold = confidence_threshold
    
    def validate_prediction_data(self, predictions: List[Dict]) -> List[Dict]:
        """
        Umfassende Datenvalidierung mit Qualitätskriterien
        """
        if not predictions:
            raise ValueError("No prediction data provided")
        
        # 1. Struktur-Validierung
        valid_predictions = []
        for pred in predictions:
            if self._is_valid_prediction_structure(pred):
                valid_predictions.append(pred)
        
        if len(valid_predictions) < self.min_data_points:
            raise ValueError(f"Insufficient valid predictions. Need at least {self.min_data_points}, got {len(valid_predictions)}")
        
        # 2. Ausreißer-Entfernung
        cleaned_predictions = self._remove_statistical_outliers(valid_predictions)
        
        # 3. Konsistenz-Check
        if not self._check_data_consistency(cleaned_predictions):
            raise ValueError("Data consistency check failed")
        
        return cleaned_predictions
    
    def _is_valid_prediction_structure(self, prediction: Dict) -> bool:
        """Validiert Strukturanforderungen einzelner Predictions"""
        required_fields = ["symbol", "predicted_value", "company_name", "market_region"]
        
        # Basis-Struktur prüfen
        if not all(field in prediction for field in required_fields):
            return False
        
        # Datentyp-Validierung
        try:
            predicted_value = float(prediction["predicted_value"])
            if np.isnan(predicted_value) or np.isinf(predicted_value):
                return False
        except (ValueError, TypeError):
            return False
        
        # Confidence-Validierung (optional)
        if "confidence" in prediction:
            try:
                confidence = float(prediction["confidence"])
                if confidence < 0.0 or confidence > 1.0:
                    return False
            except (ValueError, TypeError):
                return False
        
        # Symbol-Validierung
        symbol = prediction.get("symbol", "")
        if not symbol or len(symbol) > 10 or not symbol.replace("-", "").replace(".", "").isalnum():
            return False
        
        return True
    
    def _remove_statistical_outliers(self, predictions: List[Dict]) -> List[Dict]:
        """Entfernt statistische Ausreißer mit IQR-Methode"""
        if len(predictions) < 4:  # IQR braucht mindestens 4 Datenpunkte
            return predictions
        
        values = [p["predicted_value"] for p in predictions]
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Filtere Ausreißer
        filtered_predictions = []
        for pred in predictions:
            value = pred["predicted_value"]
            if lower_bound <= value <= upper_bound:
                filtered_predictions.append(pred)
        
        # Behalte mindestens min_data_points
        if len(filtered_predictions) < self.min_data_points:
            # Sortiere nach Distanz zum Median und nimm die besten
            median_value = np.median(values)
            predictions_with_distance = [
                (pred, abs(pred["predicted_value"] - median_value)) 
                for pred in predictions
            ]
            predictions_with_distance.sort(key=lambda x: x[1])
            filtered_predictions = [pred for pred, _ in predictions_with_distance[:self.min_data_points]]
        
        return filtered_predictions
    
    def _check_data_consistency(self, predictions: List[Dict]) -> bool:
        """Prüft Datenkonsistenz über alle Predictions"""
        if not predictions:
            return False
        
        # Einheitlichkeit der Symbole prüfen
        symbols = set(pred["symbol"] for pred in predictions)
        if len(symbols) > 1:
            return False  # Alle Predictions müssen für das gleiche Symbol sein
        
        # Standard-Abweichungs-Test
        values = [pred["predicted_value"] for pred in predictions]
        if len(values) > 1:
            mean_value = np.mean(values)
            std_dev = np.std(values)
            
            if mean_value != 0 and (std_dev / abs(mean_value)) > self.max_std_dev_ratio:
                return False  # Zu hohe Variabilität
        
        # Confidence-Konsistenz (falls vorhanden)
        confidences = [pred.get("confidence", 0.5) for pred in predictions if "confidence" in pred]
        if confidences:
            avg_confidence = np.mean(confidences)
            if avg_confidence < self.confidence_threshold:
                return False  # Zu niedrige durchschnittliche Confidence
        
        return True
    
    def calculate_aggregation_quality_score(
        self, 
        raw_predictions: List[Dict],
        aggregated_result: Dict
    ) -> float:
        """
        Berechnet Qualitäts-Score für Aggregation (0.0 - 1.0)
        """
        if not raw_predictions or not aggregated_result:
            return 0.0
        
        # Komponenten des Quality Scores
        scores = []
        
        # 1. Data Completeness Score (Anzahl valider Predictions)
        completeness_score = min(1.0, len(raw_predictions) / 10.0)  # Normiert auf 10 als optimal
        scores.append(completeness_score * 0.2)
        
        # 2. Consistency Score (niedrige Standardabweichung = besser)
        values = [p["predicted_value"] for p in raw_predictions]
        if len(values) > 1:
            std_dev = np.std(values)
            mean_val = abs(np.mean(values))
            consistency_score = 1.0 - min(1.0, (std_dev / (mean_val + 1e-6)))
            scores.append(consistency_score * 0.3)
        else:
            scores.append(0.0)
        
        # 3. Confidence Score (durchschnittliche Confidence)
        confidences = [p.get("confidence", 0.5) for p in raw_predictions]
        avg_confidence = np.mean(confidences) if confidences else 0.5
        scores.append(avg_confidence * 0.3)
        
        # 4. Mathematical Validity Score
        predicted_value = aggregated_result.get("predicted_value", 0.0)
        if np.isnan(predicted_value) or np.isinf(predicted_value):
            math_validity_score = 0.0
        else:
            math_validity_score = 1.0
        scores.append(math_validity_score * 0.2)
        
        return sum(scores)
```

---

## 🔧 **Application Layer - Use Cases**

### 🎯 **Primary Use Cases**

```python
# application/use_cases/calculate_aggregated_predictions.py
from typing import List, Dict, Optional
from domain.entities.aggregated_prediction import AggregatedPrediction, TimeframeConfiguration, AggregationStrategy
from domain.services.timeframe_aggregation_service import TimeframeAggregationService
from domain.repositories.aggregation_repository import AggregationRepositoryInterface
from application.dtos.aggregation_request_dto import AggregationRequestDTO
from application.dtos.aggregated_prediction_dto import AggregatedPredictionDTO

class CalculateAggregatedPredictionsUseCase:
    """
    Primary Use Case für Aggregation Calculation
    SINGLE RESPONSIBILITY: Nur Aggregations-Workflow
    DEPENDENCY INVERSION: Abhängig von Interfaces, nicht Konkretionen
    """
    
    def __init__(
        self,
        aggregation_service: TimeframeAggregationService,  # Domain Service
        aggregation_repository: AggregationRepositoryInterface,  # Repository Interface
        prediction_repository: 'PredictionRepositoryInterface',  # Data Source
        cache_service: 'CacheServiceInterface',  # Cache Interface
        event_publisher: 'EventPublisherInterface'  # Event Interface
    ):
        self._aggregation_service = aggregation_service
        self._aggregation_repository = aggregation_repository
        self._prediction_repository = prediction_repository
        self._cache_service = cache_service
        self._event_publisher = event_publisher
    
    async def execute(self, request: AggregationRequestDTO) -> List[AggregatedPredictionDTO]:
        """
        Main execution flow für Aggregated Predictions
        """
        results = []
        
        try:
            # 1. Validate Request
            self._validate_request(request)
            
            # 2. Check Cache First (Performance Optimization)
            cache_key = self._build_cache_key(request)
            cached_result = await self._cache_service.get(cache_key)
            
            if cached_result and not request.force_recalculation:
                # Publish cache hit event
                await self._event_publisher.publish(
                    "aggregation.cache.hit",
                    {"cache_key": cache_key, "request_id": request.request_id}
                )
                return cached_result
            
            # 3. Process each symbol
            for symbol in request.symbols:
                try:
                    # Get raw prediction data
                    raw_predictions = await self._prediction_repository.get_predictions_for_aggregation(
                        symbol=symbol,
                        timeframe_hours=request.timeframe_hours,
                        limit=request.max_predictions_per_symbol
                    )
                    
                    if not raw_predictions:
                        continue
                    
                    # Create timeframe configuration
                    timeframe_config = TimeframeConfiguration(
                        interval_type=request.timeframe_type,
                        interval_value=request.timeframe_value,
                        display_name=request.timeframe_display_name,
                        horizon_days=self._calculate_horizon_days(request)
                    )
                    
                    # Create aggregation strategy
                    strategy = AggregationStrategy(
                        strategy_type=request.aggregation_strategy,
                        parameters=request.strategy_parameters,
                        quality_threshold=request.quality_threshold
                    )
                    
                    # Execute domain aggregation logic
                    aggregated_prediction = self._aggregation_service.calculate_aggregated_prediction(
                        raw_predictions=raw_predictions,
                        timeframe_config=timeframe_config,
                        strategy=strategy
                    )
                    
                    # Store in repository
                    await self._aggregation_repository.save(aggregated_prediction)
                    
                    # Convert to DTO
                    dto = AggregatedPredictionDTO.from_entity(aggregated_prediction)
                    results.append(dto)
                    
                    # Publish individual completion event
                    await self._event_publisher.publish(
                        "aggregation.calculation.completed",
                        {
                            "symbol": symbol,
                            "aggregation_id": str(aggregated_prediction.id),
                            "quality_score": aggregated_prediction.quality_score,
                            "timeframe": timeframe_config.display_name
                        }
                    )
                    
                except Exception as e:
                    # Log individual symbol error but continue processing
                    await self._event_publisher.publish(
                        "aggregation.calculation.error",
                        {
                            "symbol": symbol,
                            "error": str(e),
                            "request_id": request.request_id
                        }
                    )
                    continue
            
            # 4. Cache results (if successful)
            if results:
                await self._cache_service.set(
                    key=cache_key, 
                    value=results, 
                    ttl_seconds=request.cache_ttl_seconds
                )
            
            # 5. Publish batch completion event
            await self._event_publisher.publish(
                "aggregation.batch.completed",
                {
                    "request_id": request.request_id,
                    "symbols_processed": len(results),
                    "total_symbols_requested": len(request.symbols),
                    "success_rate": len(results) / len(request.symbols) if request.symbols else 0.0
                }
            )
            
            return results
            
        except Exception as e:
            # Publish failure event
            await self._event_publisher.publish(
                "aggregation.calculation.failed",
                {
                    "request_id": request.request_id,
                    "error": str(e),
                    "symbols_requested": len(request.symbols) if request.symbols else 0
                }
            )
            raise
    
    def _validate_request(self, request: AggregationRequestDTO) -> None:
        """Validates aggregation request"""
        if not request.symbols:
            raise ValueError("At least one symbol must be specified")
        
        if request.timeframe_hours <= 0:
            raise ValueError("Timeframe hours must be positive")
        
        if request.quality_threshold < 0.0 or request.quality_threshold > 1.0:
            raise ValueError("Quality threshold must be between 0.0 and 1.0")
        
        valid_strategies = ["weighted_average", "median", "ensemble"]
        if request.aggregation_strategy not in valid_strategies:
            raise ValueError(f"Invalid aggregation strategy. Must be one of: {valid_strategies}")
    
    def _build_cache_key(self, request: AggregationRequestDTO) -> str:
        """Builds deterministic cache key"""
        symbols_hash = hash(tuple(sorted(request.symbols)))
        params_hash = hash(tuple(sorted(request.strategy_parameters.items())))
        
        return f"aggregation:{request.aggregation_strategy}:{request.timeframe_hours}:{symbols_hash}:{params_hash}"
    
    def _calculate_horizon_days(self, request: AggregationRequestDTO) -> int:
        """Calculates target horizon in days"""
        if request.timeframe_type == "hours":
            return max(1, request.timeframe_value // 24)
        elif request.timeframe_type == "days":
            return request.timeframe_value
        elif request.timeframe_type == "weeks":
            return request.timeframe_value * 7
        elif request.timeframe_type == "months":
            return request.timeframe_value * 30
        else:
            return 1
```

### ✅ **Validation Use Case**

```python
# application/use_cases/validate_aggregation_quality.py
class ValidateAggregationQualityUseCase:
    """
    Quality validation and monitoring use case
    SINGLE RESPONSIBILITY: Nur Qualitätsprüfung
    """
    
    def __init__(
        self,
        aggregation_repository: AggregationRepositoryInterface,
        quality_service: 'QualityAssessmentService',
        monitoring_service: 'MonitoringServiceInterface',
        event_publisher: EventPublisherInterface
    ):
        self._aggregation_repository = aggregation_repository
        self._quality_service = quality_service
        self._monitoring_service = monitoring_service
        self._event_publisher = event_publisher
    
    async def execute(self, aggregation_id: str) -> 'QualityReportDTO':
        """
        Validates quality of aggregated prediction
        """
        # 1. Retrieve aggregation
        aggregation = await self._aggregation_repository.get_by_id(aggregation_id)
        if not aggregation:
            raise ValueError(f"Aggregation not found: {aggregation_id}")
        
        # 2. Perform comprehensive quality assessment
        quality_report = await self._quality_service.assess_aggregation_quality(aggregation)
        
        # 3. Update monitoring metrics
        await self._monitoring_service.record_quality_metrics(
            symbol=aggregation.symbol,
            timeframe=aggregation.timeframe_config.display_name,
            quality_score=quality_report.overall_quality_score
        )
        
        # 4. Check quality thresholds and generate alerts
        if quality_report.overall_quality_score < aggregation.quality_score:
            await self._event_publisher.publish(
                "aggregation.quality.degraded",
                {
                    "aggregation_id": aggregation_id,
                    "symbol": aggregation.symbol,
                    "previous_quality": aggregation.quality_score,
                    "current_quality": quality_report.overall_quality_score,
                    "degradation_percentage": (aggregation.quality_score - quality_report.overall_quality_score) * 100
                }
            )
        
        # 5. Publish validation completed event
        await self._event_publisher.publish(
            "aggregation.quality.validated",
            {
                "aggregation_id": aggregation_id,
                "quality_score": quality_report.overall_quality_score,
                "validation_passed": quality_report.meets_quality_threshold,
                "issues_found": len(quality_report.quality_issues)
            }
        )
        
        return quality_report
```

---

## 🗄️ **Infrastructure Layer - Data Access & External Services**

### 📊 **Repository Implementations**

```python
# infrastructure/repositories/postgresql_aggregation_repository.py
from typing import List, Optional
import asyncpg
from domain.entities.aggregated_prediction import AggregatedPrediction, TimeframeConfiguration
from domain.repositories.aggregation_repository import AggregationRepositoryInterface

class PostgreSQLAggregationRepository(AggregationRepositoryInterface):
    """
    PostgreSQL implementation für Aggregation Repository
    DEPENDENCY INVERSION: Implementiert Domain Interface
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self._pool = connection_pool
    
    async def save(self, aggregation: AggregatedPrediction) -> None:
        """Saves aggregated prediction with UPSERT logic"""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO aggregated_predictions (
                    id, symbol, company_name, market_region,
                    timeframe_type, timeframe_value, timeframe_display, horizon_days,
                    aggregation_date, target_date,
                    predicted_value, confidence_score, quality_score,
                    data_points_count, variance, standard_deviation,
                    aggregation_strategy, created_at, last_updated
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
                )
                ON CONFLICT (id) 
                DO UPDATE SET
                    predicted_value = EXCLUDED.predicted_value,
                    confidence_score = EXCLUDED.confidence_score,
                    quality_score = EXCLUDED.quality_score,
                    data_points_count = EXCLUDED.data_points_count,
                    variance = EXCLUDED.variance,
                    standard_deviation = EXCLUDED.standard_deviation,
                    last_updated = EXCLUDED.last_updated
            """,
            str(aggregation.id), aggregation.symbol, aggregation.company_name, aggregation.market_region,
            aggregation.timeframe_config.interval_type, aggregation.timeframe_config.interval_value,
            aggregation.timeframe_config.display_name, aggregation.timeframe_config.horizon_days,
            aggregation.aggregation_date, aggregation.target_date,
            aggregation.predicted_value, aggregation.confidence_score, aggregation.quality_score,
            aggregation.data_points_count, aggregation.variance, aggregation.standard_deviation,
            aggregation.aggregation_strategy, aggregation.created_at, aggregation.last_updated
            )
    
    async def get_by_id(self, aggregation_id: str) -> Optional[AggregatedPrediction]:
        """Retrieves aggregation by ID"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM aggregated_predictions WHERE id = $1
            """, aggregation_id)
            
            if row:
                return self._row_to_entity(row)
            return None
    
    async def get_by_symbol_and_timeframe(
        self, 
        symbol: str, 
        timeframe_display: str,
        limit: int = 10
    ) -> List[AggregatedPrediction]:
        """Retrieves aggregations by symbol and timeframe"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM aggregated_predictions 
                WHERE symbol = $1 AND timeframe_display = $2
                ORDER BY created_at DESC
                LIMIT $3
            """, symbol, timeframe_display, limit)
            
            return [self._row_to_entity(row) for row in rows]
    
    def _row_to_entity(self, row) -> AggregatedPrediction:
        """Converts database row to domain entity"""
        timeframe_config = TimeframeConfiguration(
            interval_type=row['timeframe_type'],
            interval_value=row['timeframe_value'],
            display_name=row['timeframe_display'],
            horizon_days=row['horizon_days']
        )
        
        return AggregatedPrediction(
            id=UUID(row['id']),
            symbol=row['symbol'],
            company_name=row['company_name'],
            market_region=row['market_region'],
            timeframe_config=timeframe_config,
            aggregation_date=row['aggregation_date'],
            target_date=row['target_date'],
            predicted_value=row['predicted_value'],
            confidence_score=row['confidence_score'],
            quality_score=row['quality_score'],
            data_points_count=row['data_points_count'],
            variance=row['variance'],
            standard_deviation=row['standard_deviation'],
            aggregation_strategy=row['aggregation_strategy'],
            created_at=row['created_at'],
            last_updated=row['last_updated']
        )
```

### ⚡ **Redis Cache Service**

```python
# infrastructure/services/redis_cache_service.py
import json
import aioredis
from typing import Any, Optional
from application.interfaces.cache_service_interface import CacheServiceInterface

class RedisCacheService(CacheServiceInterface):
    """
    High-performance Redis cache implementation
    INTERFACE SEGREGATION: Nur Cache-relevante Methoden
    """
    
    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client
        self._default_ttl = 3600  # 1 hour default
        self._key_prefix = "aggregation:"
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieves cached value"""
        try:
            cached_data = await self._redis.get(f"{self._key_prefix}{key}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            # Log error but don't fail the application
            print(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Stores value in cache"""
        try:
            ttl = ttl_seconds or self._default_ttl
            serialized_value = json.dumps(value, default=str)
            
            await self._redis.setex(
                f"{self._key_prefix}{key}",
                ttl,
                serialized_value
            )
            return True
        except Exception as e:
            print(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Removes key from cache"""
        try:
            deleted_count = await self._redis.delete(f"{self._key_prefix}{key}")
            return deleted_count > 0
        except Exception as e:
            print(f"Cache delete error for key {key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidates all keys matching pattern"""
        try:
            keys = await self._redis.keys(f"{self._key_prefix}{pattern}")
            if keys:
                deleted_count = await self._redis.delete(*keys)
                return deleted_count
            return 0
        except Exception as e:
            print(f"Cache invalidate error for pattern {pattern}: {e}")
            return 0
```

---

## 🌐 **Presentation Layer - REST API**

### 🎯 **FastAPI Controllers**

```python
# presentation/controllers/aggregation_controller.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
from application.use_cases.calculate_aggregated_predictions import CalculateAggregatedPredictionsUseCase
from application.use_cases.validate_aggregation_quality import ValidateAggregationQualityUseCase
from application.dtos.aggregation_request_dto import AggregationRequestDTO
from application.dtos.aggregated_prediction_dto import AggregatedPredictionDTO
from presentation.dependencies import get_aggregation_use_case, get_quality_validation_use_case

router = APIRouter(prefix="/api/v1/aggregation", tags=["Timeframe Aggregation"])

@router.post("/calculate", response_model=List[AggregatedPredictionDTO])
async def calculate_aggregated_predictions(
    request: AggregationRequestDTO,
    background_tasks: BackgroundTasks,
    use_case: CalculateAggregatedPredictionsUseCase = Depends(get_aggregation_use_case)
) -> List[AggregatedPredictionDTO]:
    """
    POST /api/v1/aggregation/calculate
    
    Berechnet zeitintervall-spezifische aggregierte Vorhersagen
    
    **Performance Targets:**
    - Response Time: < 300ms für 1M, < 150ms für 1W
    - Cache Hit Ratio: > 85%
    - Concurrent Load: 50 req/s
    
    **Quality Assurance:**
    - Minimum Quality Score: 80%
    - Mathematical Validation: Comprehensive
    - Outlier Detection: IQR-based
    """
    try:
        results = await use_case.execute(request)
        
        # Schedule background quality validation
        background_tasks.add_task(
            _validate_results_quality,
            [result.id for result in results]
        )
        
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/quality/{aggregation_id}")
async def validate_aggregation_quality(
    aggregation_id: str,
    use_case: ValidateAggregationQualityUseCase = Depends(get_quality_validation_use_case)
):
    """
    GET /api/v1/aggregation/quality/{aggregation_id}
    
    Validiert Qualität einer aggregierten Vorhersage
    """
    try:
        quality_report = await use_case.execute(aggregation_id)
        return quality_report
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/{symbol}/timeframes/{timeframe}")
async def get_aggregations_by_symbol_timeframe(
    symbol: str,
    timeframe: str,
    limit: int = 10,
    repository: AggregationRepositoryInterface = Depends(get_aggregation_repository)
):
    """
    GET /api/v1/aggregation/symbols/{symbol}/timeframes/{timeframe}
    
    Lädt aggregierte Vorhersagen für Symbol und Zeitintervall
    """
    try:
        aggregations = await repository.get_by_symbol_and_timeframe(
            symbol=symbol.upper(),
            timeframe_display=timeframe.upper(),
            limit=limit
        )
        
        return [AggregatedPredictionDTO.from_entity(agg) for agg in aggregations]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _validate_results_quality(aggregation_ids: List[str]):
    """Background task für Quality Validation"""
    # Implementation für Background Quality Validation
    pass
```

---

*Low-Level Design - Timeframe Aggregation v7.0*  
*Clean Architecture Integration - Event-Driven Trading Intelligence System*  
*Letzte Aktualisierung: 27. August 2025*