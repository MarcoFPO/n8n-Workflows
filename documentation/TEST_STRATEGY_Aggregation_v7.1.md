# 🧪 Test Strategy: Timeframe Aggregation v7.1

## 📋 **Executive Summary**

**Zweck:** Umfassende Test-Strategie für die qualitätssichere Implementierung der Timeframe Aggregation Engine v7.1  
**Scope:** Clean Architecture Compliance, SOLID Principles Validation, Performance SLA Testing  
**Qualitätsziel:** >95% Test Coverage, 99.9% Mathematical Accuracy, <1% Error Rate  
**Performance Ziele:** <300ms (1M), <150ms (1W), 50+ concurrent requests, >85% Cache Hit Rate  

### **Testing Philosophy: Quality First Approach**
- **Code-Qualität hat höchste Priorität** vor allen anderen Anforderungen
- **Test-Driven Development (TDD)** für alle Domain Layer Components
- **Mathematical Correctness** durch umfassende Algorithm Validation
- **Performance Testing** mit realistischen Production-Load Scenarios
- **Integration Testing** mit vollständiger Cross-Service Validation

---

## 🏗️ **Test Architecture Overview**

### **Test Pyramid Strategy**

```
                    🔺 E2E Tests (5%)
                   Cross-Service Integration
                  Production-Like Scenarios
                 
               🔺🔺 Integration Tests (25%)
              Database, Cache, Event Bus
             API Endpoints, Service Layer
            
         🔺🔺🔺🔺 Unit Tests (70%)
        Domain Logic, Algorithms, Validation
       Business Rules, Mathematical Correctness
      Value Objects, Entities, Services
```

### **Test Layer Responsibilities**

#### **Unit Tests (70% Coverage Target: >95%)**
- **Domain Layer**: Business Logic, Mathematical Algorithms, Entity Behavior
- **Application Layer**: Use Cases, DTOs, Service Orchestration
- **Infrastructure Layer**: Repository Logic, Cache Operations, Event Publishing
- **Presentation Layer**: API Controllers, Request/Response Validation

#### **Integration Tests (25% Coverage Target: >90%)**
- **Database Integration**: Repository Operations, Query Performance, Transaction Handling
- **Cache Integration**: Redis Operations, TTL Management, Cache Invalidation
- **Event Bus Integration**: Event Publishing, Cross-Service Communication
- **API Integration**: End-to-End API Workflows, Error Handling

#### **End-to-End Tests (5% Coverage Target: >80%)**
- **Complete Workflow Testing**: Full Aggregation Pipeline from Request to Response
- **Cross-Service Integration**: Multi-Service Event-Driven Workflows
- **Performance Testing**: Load Testing, SLA Validation, Concurrent Request Handling
- **Production Scenario Testing**: Real-world Usage Patterns, Error Recovery

---

## 🧪 **Unit Testing Strategy**

### **Domain Layer Testing - HIGHEST PRIORITY**

#### **Test Framework & Tools**
```python
# Testing Stack für Domain Layer
import pytest                    # Test Framework
import pytest-asyncio           # Async Testing Support
import pytest-benchmark        # Performance Testing
import hypothesis              # Property-Based Testing
import numpy as np             # Mathematical Validation
import scipy.stats             # Statistical Correctness
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import date, datetime, timedelta
```

#### **Domain Entity Testing**

```python
# tests/unit/domain/entities/test_aggregated_prediction.py
class TestAggregatedPrediction:
    """
    Comprehensive Unit Tests für AggregatedPrediction Entity
    
    Testing Areas:
    1. Entity Creation & Validation
    2. Business Rule Enforcement
    3. Domain Behavior Verification
    4. Edge Cases & Error Conditions
    """
    
    @pytest.fixture
    def valid_timeframe_config(self):
        return TimeframeConfiguration(
            interval_type="weeks",
            interval_value=1,
            display_name="1W",
            horizon_days=7
        )
    
    @pytest.fixture
    def valid_quality_metrics(self):
        return QualityMetrics(
            data_quality_score=0.9,
            prediction_quality_score=0.85,
            overall_quality_score=0.87,
            data_completeness=0.95,
            data_consistency=0.82,
            confidence_distribution=0.15,
            outlier_count=2,
            quality_threshold_met=True
        )
    
    def test_entity_creation_with_valid_data(self, valid_timeframe_config, valid_quality_metrics):
        """Test successful entity creation with valid data"""
        prediction = AggregatedPrediction(
            id=uuid4(),
            symbol="AAPL",
            company_name="Apple Inc.",
            market_region="US",
            timeframe_config=valid_timeframe_config,
            aggregation_date=date.today(),
            target_date=date.today() + timedelta(days=7),
            predicted_value=Decimal("175.45"),
            confidence_score=0.87,
            quality_metrics=valid_quality_metrics,
            data_points_count=15,
            variance=2.34,
            standard_deviation=1.53,
            aggregation_strategy="ensemble",
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        assert prediction.symbol == "AAPL"
        assert prediction.confidence_score == 0.87
        assert prediction.is_high_quality(threshold=0.8) is True
        assert prediction.is_prediction_expired() is False
    
    def test_confidence_score_validation(self, valid_timeframe_config, valid_quality_metrics):
        """Test confidence score validation rules"""
        with pytest.raises(ValueError, match="Confidence score must be between 0.0 and 1.0"):
            AggregatedPrediction(
                id=uuid4(),
                symbol="AAPL",
                company_name="Apple Inc.",
                market_region="US",
                timeframe_config=valid_timeframe_config,
                aggregation_date=date.today(),
                target_date=date.today() + timedelta(days=7),
                predicted_value=Decimal("175.45"),
                confidence_score=1.5,  # Invalid: > 1.0
                quality_metrics=valid_quality_metrics,
                data_points_count=15,
                variance=2.34,
                standard_deviation=1.53,
                aggregation_strategy="ensemble",
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
    
    def test_accuracy_calculation_against_actual(self, valid_timeframe_config, valid_quality_metrics):
        """Test accuracy calculation business logic"""
        prediction = AggregatedPrediction(
            # ... (entity setup)
            predicted_value=Decimal("175.00")
            # ...
        )
        
        # Test perfect accuracy
        perfect_accuracy = prediction.calculate_accuracy_against_actual(Decimal("175.00"))
        assert perfect_accuracy == 1.0
        
        # Test partial accuracy
        partial_accuracy = prediction.calculate_accuracy_against_actual(Decimal("170.00"))
        expected_accuracy = 1.0 - (5.0 / 175.0)  # 97.14%
        assert abs(partial_accuracy - expected_accuracy) < 0.001
        
        # Test zero predicted value edge case
        prediction.predicted_value = Decimal("0.00")
        zero_accuracy = prediction.calculate_accuracy_against_actual(Decimal("100.00"))
        assert zero_accuracy == 0.0
    
    @pytest.mark.parametrize("threshold,expected", [
        (0.5, True),   # Below quality score
        (0.8, True),   # Equal to quality score  
        (0.9, False),  # Above quality score
    ])
    def test_high_quality_assessment(self, threshold, expected, valid_timeframe_config):
        """Test high quality assessment with different thresholds"""
        quality_metrics = QualityMetrics(
            data_quality_score=0.8,
            prediction_quality_score=0.8,
            overall_quality_score=0.8,
            data_completeness=0.8,
            data_consistency=0.8,
            confidence_distribution=0.2,
            outlier_count=1,
            quality_threshold_met=True
        )
        
        prediction = AggregatedPrediction(
            # ... (entity setup with quality_metrics)
            quality_metrics=quality_metrics
            # ...
        )
        
        assert prediction.is_high_quality(threshold) == expected
```

#### **Domain Service Testing - Mathematical Correctness**

```python
# tests/unit/domain/services/test_timeframe_aggregation_service.py
class TestTimeframeAggregationService:
    """
    Mathematical Algorithm Testing für Timeframe Aggregation Service
    
    Critical Testing Areas:
    1. Strategy Pattern Implementation
    2. Mathematical Correctness of Algorithms  
    3. Statistical Validation Accuracy
    4. Error Handling & Edge Cases
    5. Performance Characteristics
    """
    
    @pytest.fixture
    def aggregation_service(self):
        validation_service = Mock(spec=MathematicalValidationService)
        return TimeframeAggregationService(validation_service)
    
    @pytest.fixture
    def sample_predictions(self):
        """Sample prediction data for testing"""
        return [
            {"predicted_value": 175.0, "confidence": 0.9, "created_at": "2025-08-27T10:00:00Z"},
            {"predicted_value": 172.5, "confidence": 0.85, "created_at": "2025-08-27T10:15:00Z"},
            {"predicted_value": 178.2, "confidence": 0.92, "created_at": "2025-08-27T10:30:00Z"},
            {"predicted_value": 174.8, "confidence": 0.88, "created_at": "2025-08-27T10:45:00Z"},
            {"predicted_value": 176.1, "confidence": 0.91, "created_at": "2025-08-27T11:00:00Z"}
        ]
    
    def test_weighted_average_strategy_mathematical_correctness(self, aggregation_service, sample_predictions):
        """Test weighted average algorithm mathematical accuracy"""
        parameters = {"base_weight": 1.0}
        
        result = aggregation_service._weighted_average_strategy(sample_predictions, parameters)
        
        # Manual calculation for verification
        weights = [0.9, 0.85, 0.92, 0.88, 0.91]  # confidence scores
        values = [175.0, 172.5, 178.2, 174.8, 176.1]
        
        expected_weighted_avg = sum(w * v for w, v in zip(weights, values)) / sum(weights)
        expected_variance = np.var(values)
        expected_std = np.std(values)
        
        assert abs(float(result["predicted_value"]) - expected_weighted_avg) < 0.01
        assert abs(result["variance"] - expected_variance) < 0.01
        assert abs(result["standard_deviation"] - expected_std) < 0.01
        assert result["method_details"]["strategy"] == "weighted_average"
        assert result["method_details"]["total_weight"] == sum(weights)
    
    def test_median_strategy_statistical_correctness(self, aggregation_service, sample_predictions):
        """Test median strategy statistical accuracy"""
        parameters = {}
        
        result = aggregation_service._median_strategy(sample_predictions, parameters)
        
        values = [175.0, 172.5, 178.2, 174.8, 176.1]
        expected_median = np.median(values)
        expected_q1 = np.percentile(values, 25)
        expected_q3 = np.percentile(values, 75)
        
        assert abs(float(result["predicted_value"]) - expected_median) < 0.01
        assert abs(result["method_details"]["quartiles"]["q1"] - expected_q1) < 0.01
        assert abs(result["method_details"]["quartiles"]["q2"] - expected_median) < 0.01
        assert abs(result["method_details"]["quartiles"]["q3"] - expected_q3) < 0.01
    
    def test_ensemble_strategy_combination_logic(self, aggregation_service, sample_predictions):
        """Test ensemble strategy proper combination of methods"""
        parameters = {"weighted_avg_weight": 0.7}
        
        result = aggregation_service._ensemble_strategy(sample_predictions, parameters)
        
        # Verify ensemble combines weighted average (70%) and median (30%)
        weighted_result = aggregation_service._weighted_average_strategy(sample_predictions, parameters)
        median_result = aggregation_service._median_strategy(sample_predictions, parameters)
        
        expected_ensemble = (
            float(weighted_result["predicted_value"]) * 0.7 + 
            float(median_result["predicted_value"]) * 0.3
        )
        
        assert abs(float(result["predicted_value"]) - expected_ensemble) < 0.01
        assert result["method_details"]["strategy"] == "ensemble"
        assert result["method_details"]["ensemble_composition"]["weighted_average_contribution"] == 0.7
        assert result["method_details"]["ensemble_composition"]["median_contribution"] == 0.3
    
    @pytest.mark.parametrize("strategy_type,expected_exception", [
        ("invalid_strategy", UnsupportedStrategyError),
        ("", UnsupportedStrategyError),
        (None, UnsupportedStrategyError),
    ])
    def test_unsupported_strategy_error_handling(self, aggregation_service, strategy_type, expected_exception):
        """Test proper error handling for unsupported strategies"""
        with pytest.raises(expected_exception):
            aggregation_service._get_strategy_function(strategy_type)
    
    @pytest.mark.benchmark
    def test_aggregation_performance_benchmarks(self, aggregation_service, sample_predictions, benchmark):
        """Performance benchmarking für aggregation algorithms"""
        timeframe_config = TimeframeConfiguration(
            interval_type="weeks",
            interval_value=1, 
            display_name="1W",
            horizon_days=7
        )
        
        # Mock validation service to return predictions as-is
        aggregation_service._validation_service.validate_prediction_data.return_value = sample_predictions
        
        # Benchmark ensemble strategy (most complex)
        result = benchmark(
            aggregation_service.calculate_aggregated_prediction,
            sample_predictions,
            timeframe_config,
            "ensemble",
            {"weighted_avg_weight": 0.7}
        )
        
        assert result is not None
        assert isinstance(result, AggregatedPrediction)
```

#### **Mathematical Validation Service Testing**

```python
# tests/unit/domain/services/test_mathematical_validation_service.py
class TestMathematicalValidationService:
    """
    Statistical Algorithm Testing für Mathematical Validation
    
    Focus Areas:
    1. IQR Outlier Detection Mathematical Correctness
    2. Confidence Calculation Algorithm Accuracy
    3. Data Validation Pipeline Effectiveness
    4. Statistical Edge Cases Handling
    """
    
    @pytest.fixture
    def validation_service(self):
        return MathematicalValidationService()
    
    @pytest.fixture
    def predictions_with_outliers(self):
        """Predictions with known outliers for testing"""
        return [
            {"predicted_value": 175.0, "confidence": 0.9, "created_at": "2025-08-27T10:00:00Z"},
            {"predicted_value": 172.5, "confidence": 0.85, "created_at": "2025-08-27T10:15:00Z"},
            {"predicted_value": 250.0, "confidence": 0.7, "created_at": "2025-08-27T10:30:00Z"},  # Outlier
            {"predicted_value": 174.8, "confidence": 0.88, "created_at": "2025-08-27T10:45:00Z"},
            {"predicted_value": 176.1, "confidence": 0.91, "created_at": "2025-08-27T11:00:00Z"},
            {"predicted_value": 90.0, "confidence": 0.6, "created_at": "2025-08-27T11:15:00Z"},   # Outlier
            {"predicted_value": 173.2, "confidence": 0.87, "created_at": "2025-08-27T11:30:00Z"},
        ]
    
    def test_iqr_outlier_detection_accuracy(self, validation_service, predictions_with_outliers):
        """Test IQR outlier detection mathematical correctness"""
        clean_predictions = validation_service._remove_statistical_outliers(predictions_with_outliers)
        
        values = [float(p["predicted_value"]) for p in predictions_with_outliers]
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Verify outliers are removed
        clean_values = [float(p["predicted_value"]) for p in clean_predictions]
        
        for value in clean_values:
            assert lower_bound <= value <= upper_bound, f"Value {value} should be within IQR bounds"
        
        # Verify known outliers (250.0, 90.0) are removed
        assert 250.0 not in clean_values
        assert 90.0 not in clean_values
        
        # Verify normal values are retained
        normal_values = [175.0, 172.5, 174.8, 176.1, 173.2]
        for value in normal_values:
            assert value in clean_values
    
    def test_confidence_calculation_algorithm(self, validation_service):
        """Test confidence calculation multi-factor algorithm"""
        predictions = [
            {"predicted_value": 175.0, "confidence": 0.9},
            {"predicted_value": 174.5, "confidence": 0.85},
            {"predicted_value": 175.5, "confidence": 0.88},
            {"predicted_value": 174.8, "confidence": 0.92},
        ]
        
        aggregation_result = {"predicted_value": Decimal("175.0")}
        
        calculated_confidence = validation_service.calculate_aggregation_confidence(
            predictions, aggregation_result
        )
        
        # Verify confidence is between 0 and 1
        assert 0.0 <= calculated_confidence <= 1.0
        
        # Verify high individual confidences + low variance = high overall confidence
        assert calculated_confidence > 0.8  # Should be high due to good individual scores and agreement
        
    def test_edge_case_insufficient_data(self, validation_service):
        """Test handling of insufficient data scenarios"""
        insufficient_predictions = [
            {"predicted_value": 175.0, "confidence": 0.9, "created_at": "2025-08-27T10:00:00Z"},
            {"predicted_value": 172.0, "confidence": 0.5, "created_at": "2025-08-27T10:15:00Z"}  # Below threshold
        ]
        
        with pytest.raises(InsufficientQualityDataError):
            validation_service.validate_prediction_data(insufficient_predictions)
    
    def test_data_validation_pipeline_comprehensive(self, validation_service):
        """Test complete data validation pipeline"""
        mixed_quality_predictions = [
            # Valid predictions
            {"predicted_value": 175.0, "confidence": 0.9, "created_at": "2025-08-27T10:00:00Z"},
            {"predicted_value": 174.5, "confidence": 0.85, "created_at": "2025-08-27T10:15:00Z"},
            {"predicted_value": 175.8, "confidence": 0.88, "created_at": "2025-08-27T10:30:00Z"},
            
            # Low quality (should be filtered)
            {"predicted_value": 176.2, "confidence": 0.4, "created_at": "2025-08-27T10:45:00Z"},
            
            # Outlier (should be filtered)  
            {"predicted_value": 250.0, "confidence": 0.8, "created_at": "2025-08-27T11:00:00Z"},
            
            # Invalid structure (should be filtered)
            {"predicted_value": "invalid", "confidence": 0.9, "created_at": "2025-08-27T11:15:00Z"},
            
            # Future date (should be filtered)
            {"predicted_value": 174.0, "confidence": 0.9, "created_at": "2025-12-31T10:00:00Z"},
        ]
        
        validated_predictions = validation_service.validate_prediction_data(mixed_quality_predictions)
        
        # Should retain only the 3 valid predictions
        assert len(validated_predictions) == 3
        
        # Verify all retained predictions meet quality standards
        for pred in validated_predictions:
            assert pred["confidence"] >= validation_service.quality_threshold
            assert isinstance(pred["predicted_value"], (int, float))
            assert float(pred["predicted_value"]) < 200.0  # No outliers
```

### **Application Layer Testing**

#### **Use Case Testing**

```python
# tests/unit/application/use_cases/test_calculate_aggregated_predictions_use_case.py
class TestCalculateAggregatedPredictionsUseCase:
    """
    Application Layer Use Case Testing
    
    Testing Focus:
    1. Use Case Orchestration Logic
    2. Error Handling & Recovery
    3. Cache Strategy Implementation
    4. Event Publishing Integration
    5. Performance Monitoring Integration
    """
    
    @pytest.fixture
    def use_case_dependencies(self):
        return {
            "aggregation_service": Mock(spec=TimeframeAggregationService),
            "aggregation_repository": Mock(spec=AggregationRepositoryInterface), 
            "prediction_repository": Mock(spec=PredictionRepositoryInterface),
            "cache_service": Mock(spec=CacheServiceInterface),
            "event_publisher": Mock(spec=EventPublisherInterface),
            "performance_monitor": Mock(spec=PerformanceMonitorInterface)
        }
    
    @pytest.fixture 
    def use_case(self, use_case_dependencies):
        return CalculateAggregatedPredictionsUseCase(**use_case_dependencies)
    
    @pytest.fixture
    def sample_request(self):
        return AggregationRequestDTO(
            request_id="test_request_001",
            symbols=["AAPL"],
            timeframe_type="weeks",
            timeframe_value=1,
            timeframe_display_name="1W",
            timeframe_hours=168,
            aggregation_strategy="ensemble",
            strategy_parameters={"weighted_avg_weight": 0.7},
            quality_threshold=0.8,
            max_predictions_per_symbol=50,
            min_prediction_quality=0.6,
            cache_ttl_seconds=3600,
            force_recalculation=False
        )
    
    @pytest.mark.asyncio
    async def test_successful_aggregation_workflow(self, use_case, sample_request, use_case_dependencies):
        """Test complete successful aggregation workflow"""
        # Setup mocks
        raw_predictions = [
            {"predicted_value": 175.0, "confidence": 0.9, "created_at": "2025-08-27T10:00:00Z"}
        ]
        
        aggregated_prediction = Mock(spec=AggregatedPrediction)
        aggregated_prediction.id = uuid4()
        aggregated_prediction.symbol = "AAPL"
        
        use_case_dependencies["cache_service"].get.return_value = None  # Cache miss
        use_case_dependencies["prediction_repository"].get_predictions_for_aggregation.return_value = raw_predictions
        use_case_dependencies["aggregation_service"].calculate_aggregated_prediction.return_value = aggregated_prediction
        use_case_dependencies["performance_monitor"].start_execution.return_value = Mock()
        
        # Execute use case
        result = await use_case.execute(sample_request)
        
        # Verify workflow
        assert len(result) == 1
        use_case_dependencies["prediction_repository"].get_predictions_for_aggregation.assert_called_once()
        use_case_dependencies["aggregation_service"].calculate_aggregated_prediction.assert_called_once()
        use_case_dependencies["aggregation_repository"].save.assert_called_once()
        use_case_dependencies["event_publisher"].publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_cache_hit_scenario(self, use_case, sample_request, use_case_dependencies):
        """Test cache hit scenario bypasses processing"""
        cached_result = [Mock(spec=AggregatedPredictionDTO)]
        use_case_dependencies["cache_service"].get.return_value = cached_result
        use_case_dependencies["performance_monitor"].start_execution.return_value = Mock()
        
        result = await use_case.execute(sample_request)
        
        assert result == cached_result
        # Verify processing is bypassed
        use_case_dependencies["prediction_repository"].get_predictions_for_aggregation.assert_not_called()
        use_case_dependencies["aggregation_service"].calculate_aggregated_prediction.assert_not_called()
    
    @pytest.mark.asyncio 
    async def test_error_handling_with_partial_success(self, use_case, use_case_dependencies):
        """Test error handling with partial success for batch processing"""
        request = AggregationRequestDTO(
            request_id="test_request_002",
            symbols=["AAPL", "GOOGL", "INVALID"],
            timeframe_type="weeks",
            timeframe_value=1,
            timeframe_display_name="1W",
            timeframe_hours=168,
            aggregation_strategy="ensemble"
        )
        
        # Setup: AAPL succeeds, GOOGL fails, INVALID fails
        def mock_get_predictions(symbol, **kwargs):
            if symbol == "AAPL":
                return [{"predicted_value": 175.0, "confidence": 0.9, "created_at": "2025-08-27T10:00:00Z"}]
            elif symbol == "GOOGL":
                raise Exception("Data source error")
            else:
                return []  # No data for INVALID
        
        use_case_dependencies["cache_service"].get.return_value = None
        use_case_dependencies["prediction_repository"].get_predictions_for_aggregation.side_effect = mock_get_predictions
        use_case_dependencies["aggregation_service"].calculate_aggregated_prediction.return_value = Mock(spec=AggregatedPrediction)
        use_case_dependencies["performance_monitor"].start_execution.return_value = Mock()
        
        result = await use_case.execute(request)
        
        # Should return partial success (only AAPL)
        assert len(result) == 1
        
        # Verify error events published for failed symbols
        published_events = [call.args[0] for call in use_case_dependencies["event_publisher"].publish.call_args_list]
        assert "aggregation.calculation.symbol_failed" in published_events
        assert "aggregation.batch.processed" in published_events
```

---

## 🔧 **Integration Testing Strategy**

### **Database Integration Tests**

```python
# tests/integration/infrastructure/test_postgresql_aggregation_repository.py
class TestPostgreSQLAggregationRepository:
    """
    Database Integration Testing
    
    Testing Areas:
    1. CRUD Operations
    2. Query Performance  
    3. Transaction Handling
    4. Index Effectiveness
    5. Concurrent Access
    """
    
    @pytest.fixture
    async def repository(self, test_db_connection):
        return PostgreSQLAggregationRepository(test_db_connection)
    
    @pytest.fixture
    def sample_aggregation(self):
        return AggregatedPrediction(
            id=uuid4(),
            symbol="AAPL",
            company_name="Apple Inc.",
            market_region="US",
            timeframe_config=TimeframeConfiguration(
                interval_type="weeks",
                interval_value=1,
                display_name="1W", 
                horizon_days=7
            ),
            aggregation_date=date.today(),
            target_date=date.today() + timedelta(days=7),
            predicted_value=Decimal("175.45"),
            confidence_score=0.87,
            quality_metrics=QualityMetrics(
                data_quality_score=0.9,
                prediction_quality_score=0.85,
                overall_quality_score=0.87,
                data_completeness=0.95,
                data_consistency=0.82,
                confidence_distribution=0.15,
                outlier_count=2,
                quality_threshold_met=True
            ),
            data_points_count=15,
            variance=2.34,
            standard_deviation=1.53,
            aggregation_strategy="ensemble",
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_aggregation(self, repository, sample_aggregation):
        """Test basic CRUD operations"""
        # Save
        await repository.save(sample_aggregation)
        
        # Retrieve
        retrieved = await repository.get_by_id(sample_aggregation.id)
        
        assert retrieved is not None
        assert retrieved.symbol == sample_aggregation.symbol
        assert retrieved.predicted_value == sample_aggregation.predicted_value
        assert retrieved.confidence_score == sample_aggregation.confidence_score
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_query_performance_with_indexes(self, repository, benchmark):
        """Test query performance meets SLA requirements"""
        # Create test data
        test_aggregations = []
        for i in range(100):
            aggregation = AggregatedPrediction(
                # ... create 100 test aggregations
            )
            test_aggregations.append(aggregation)
        
        # Bulk insert
        for aggregation in test_aggregations:
            await repository.save(aggregation)
        
        # Benchmark query performance
        async def query_by_symbol_and_timeframe():
            return await repository.get_by_symbol_and_timeframe("AAPL", "1W", limit=10)
        
        result = await benchmark(query_by_symbol_and_timeframe)
        
        assert len(result) <= 10
        # Verify performance target (<50ms)
        assert benchmark.stats.mean < 0.050  # 50ms
    
    @pytest.mark.asyncio
    async def test_concurrent_access_handling(self, repository, sample_aggregation):
        """Test concurrent access to repository"""
        
        async def concurrent_save(aggregation_id):
            modified_aggregation = sample_aggregation
            modified_aggregation.id = aggregation_id
            modified_aggregation.predicted_value = Decimal(f"{170 + (hash(str(aggregation_id)) % 10)}.00")
            await repository.save(modified_aggregation)
        
        # Execute 10 concurrent saves
        tasks = [concurrent_save(uuid4()) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0
```

### **Cache Integration Tests**

```python
# tests/integration/infrastructure/test_redis_cache_service.py
class TestRedisCacheService:
    """
    Redis Cache Integration Testing
    
    Focus:
    1. Cache Operations
    2. TTL Management
    3. Cache Key Strategy
    4. Performance Characteristics
    """
    
    @pytest.fixture
    async def cache_service(self, test_redis_client):
        return RedisCacheService(test_redis_client)
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_target(self, cache_service):
        """Test cache hit rate meets >85% target"""
        cache_key = "test:aggregation:AAPL:1W"
        test_data = {"predicted_value": 175.45, "confidence_score": 0.87}
        
        # Cache miss first time
        result = await cache_service.get(cache_key)
        assert result is None
        
        # Set cache
        await cache_service.set(cache_key, test_data, ttl=3600)
        
        # Cache hit
        result = await cache_service.get(cache_key)
        assert result == test_data
        
        # Verify TTL is set correctly
        ttl = await cache_service.redis.ttl(cache_key)
        assert 3500 < ttl <= 3600  # Account for processing time
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_performance_characteristics(self, cache_service, benchmark):
        """Test cache operations meet performance requirements"""
        cache_key = "perf:test:key"
        test_data = {"large_data": "x" * 10000}  # 10KB data
        
        # Benchmark cache set operation
        async def cache_set():
            await cache_service.set(cache_key, test_data, ttl=3600)
        
        await benchmark(cache_set)
        
        # Verify cache set performance (<10ms)
        assert benchmark.stats.mean < 0.010
        
        # Benchmark cache get operation
        async def cache_get():
            return await cache_service.get(cache_key)
        
        result = await benchmark(cache_get)
        
        assert result == test_data
        # Verify cache get performance (<5ms)
        assert benchmark.stats.mean < 0.005
```

### **Event Bus Integration Tests**

```python
# tests/integration/infrastructure/test_event_bus_integration.py
class TestEventBusIntegration:
    """
    Event Bus Integration Testing
    
    Coverage:
    1. Event Publishing
    2. Cross-Service Event Handling
    3. Event Schema Validation
    4. Error Recovery
    """
    
    @pytest.fixture
    async def event_publisher(self, test_redis_event_bus):
        return EventBusPublisher(test_redis_event_bus)
    
    @pytest.mark.asyncio
    async def test_aggregation_event_publishing_end_to_end(self, event_publisher):
        """Test complete event publishing workflow"""
        
        # Test aggregation.calculation.completed event
        event_data = {
            "aggregation_id": str(uuid4()),
            "symbol": "AAPL",
            "predicted_value": 175.45,
            "confidence_score": 0.87,
            "quality_score": 0.91,
            "processing_time_ms": 245
        }
        
        # Publish event
        await event_publisher.publish("aggregation.calculation.completed", event_data)
        
        # Verify event was published (would be verified by subscribing services in real integration)
        # Here we verify the event publisher worked without errors
        
        # Test event schema validation  
        invalid_event_data = {"incomplete": "data"}
        
        with pytest.raises(EventValidationError):
            await event_publisher.publish("aggregation.calculation.completed", invalid_event_data)
    
    @pytest.mark.asyncio
    async def test_cross_service_event_integration(self, event_publisher):
        """Test cross-service event integration workflow"""
        
        # Simulate complete aggregation workflow events
        events_to_publish = [
            ("aggregation.calculation.requested", {
                "request_id": "req_001",
                "symbols": ["AAPL"],
                "timeframe_config": {"display_name": "1W"},
                "aggregation_strategy": "ensemble"
            }),
            
            ("aggregation.calculation.completed", {
                "aggregation_id": str(uuid4()),
                "symbol": "AAPL",
                "predicted_value": 175.45,
                "confidence_score": 0.87,
                "quality_score": 0.91
            }),
            
            ("aggregation.quality.validated", {
                "aggregation_id": str(uuid4()),
                "overall_quality_score": 0.91,
                "quality_status": "EXCELLENT",
                "validation_passed": True
            }),
            
            ("aggregation.cache.updated", {
                "cache_key": "aggregation:ensemble:168:hash",
                "operation": "SET",
                "ttl_seconds": 3600
            })
        ]
        
        # Publish all events in sequence
        for event_type, data in events_to_publish:
            await event_publisher.publish(event_type, data)
        
        # Verify no errors occurred during event publishing
        # In real integration, would verify events received by subscribing services
```

---

## 🚀 **End-to-End Testing Strategy**

### **Complete Workflow Testing**

```python
# tests/e2e/test_aggregation_complete_workflow.py
class TestAggregationCompleteWorkflow:
    """
    End-to-End Integration Testing
    
    Scenarios:
    1. Complete Aggregation Workflow (Request → Response)
    2. Cross-Service Integration
    3. Error Recovery & Resilience
    4. Performance Under Load
    """
    
    @pytest.fixture
    async def test_client(self):
        """FastAPI test client with full application setup"""
        from main import create_app
        app = create_app(test_mode=True)
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_complete_aggregation_api_workflow(self, test_client):
        """Test complete API workflow from request to response"""
        
        request_payload = {
            "request_id": "e2e_test_001",
            "symbols": ["AAPL"],
            "timeframe_type": "weeks",
            "timeframe_value": 1,
            "timeframe_display_name": "1W",
            "timeframe_hours": 168,
            "aggregation_strategy": "ensemble",
            "strategy_parameters": {"weighted_avg_weight": 0.7},
            "quality_threshold": 0.8
        }
        
        # Execute aggregation request
        response = await test_client.post("/api/v1/aggregation/calculate", json=request_payload)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        aggregation = data[0]
        
        assert aggregation["symbol"] == "AAPL"
        assert aggregation["timeframe_display"] == "1W"
        assert aggregation["aggregation_strategy"] == "ensemble"
        assert 0.0 <= aggregation["confidence_score"] <= 1.0
        assert 0.0 <= aggregation["quality_score"] <= 1.0
        
    @pytest.mark.asyncio
    async def test_quality_validation_workflow(self, test_client):
        """Test quality validation workflow"""
        
        # First create an aggregation
        aggregation_response = await test_client.post("/api/v1/aggregation/calculate", json={
            "request_id": "quality_test_001",
            "symbols": ["AAPL"],
            "timeframe_type": "weeks",
            "timeframe_value": 1,
            "timeframe_display_name": "1W",
            "timeframe_hours": 168,
            "aggregation_strategy": "ensemble"
        })
        
        aggregation_data = aggregation_response.json()[0]
        aggregation_id = aggregation_data["id"]
        
        # Validate quality
        quality_response = await test_client.get(f"/api/v1/aggregation/quality/{aggregation_id}")
        
        assert quality_response.status_code == 200
        quality_data = quality_response.json()
        
        assert quality_data["aggregation_id"] == aggregation_id
        assert quality_data["quality_status"] in ["EXCELLENT", "GOOD", "ACCEPTABLE", "POOR", "UNACCEPTABLE"]
        assert isinstance(quality_data["validation_passed"], bool)
        assert "quality_dimensions" in quality_data
    
    @pytest.mark.asyncio
    async def test_performance_under_concurrent_load(self, test_client):
        """Test system performance under concurrent load"""
        
        async def single_aggregation_request(request_id):
            payload = {
                "request_id": f"load_test_{request_id}",
                "symbols": ["AAPL"],
                "timeframe_type": "weeks", 
                "timeframe_value": 1,
                "timeframe_display_name": "1W",
                "timeframe_hours": 168,
                "aggregation_strategy": "ensemble"
            }
            
            start_time = time.time()
            response = await test_client.post("/api/v1/aggregation/calculate", json=payload)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "request_id": request_id
            }
        
        # Execute 50 concurrent requests (target throughput)
        concurrent_tasks = [single_aggregation_request(i) for i in range(50)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze results
        successful_requests = [r for r in results if not isinstance(r, Exception) and r["status_code"] == 200]
        failed_requests = [r for r in results if isinstance(r, Exception) or r["status_code"] != 200]
        
        # Verify performance targets
        success_rate = len(successful_requests) / len(results)
        assert success_rate > 0.95  # >95% success rate
        
        response_times = [r["response_time"] for r in successful_requests]
        avg_response_time = sum(response_times) / len(response_times)
        p95_response_time = np.percentile(response_times, 95)
        
        # Verify SLA compliance (1W timeframe: <150ms)
        assert avg_response_time < 0.150
        assert p95_response_time < 0.200  # Allow some tolerance for concurrent load
        
        print(f"Load Test Results:")
        print(f"  Concurrent Requests: 50")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Average Response Time: {avg_response_time:.3f}s")
        print(f"  95th Percentile Response Time: {p95_response_time:.3f}s")
```

---

## 📊 **Performance Testing Strategy**

### **Load Testing Configuration**

```python
# tests/performance/test_aggregation_performance.py
import asyncio
import time
import statistics
import pytest
from locust import HttpUser, task, between

class AggregationPerformanceTest:
    """
    Performance Testing Suite for Aggregation Service
    
    Testing Scenarios:
    1. Response Time SLA Validation
    2. Throughput Testing
    3. Cache Performance
    4. Concurrent User Simulation
    """
    
    @pytest.mark.performance
    async def test_response_time_sla_compliance(self):
        """Test response time SLA compliance for different timeframes"""
        
        test_scenarios = [
            {"timeframe": "1W", "target_ms": 150, "requests": 100},
            {"timeframe": "1M", "target_ms": 300, "requests": 100},
        ]
        
        for scenario in test_scenarios:
            response_times = []
            
            for i in range(scenario["requests"]):
                payload = {
                    "request_id": f"sla_test_{scenario['timeframe']}_{i}",
                    "symbols": ["AAPL"],
                    "timeframe_display_name": scenario["timeframe"]
                }
                
                start_time = time.time()
                # Execute request (mock or actual API call)
                await self._execute_aggregation_request(payload)
                end_time = time.time()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
            
            # Statistical analysis
            mean_response = statistics.mean(response_times)
            p95_response = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            p99_response = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
            
            # SLA Validation
            sla_compliance = sum(1 for rt in response_times if rt <= scenario["target_ms"]) / len(response_times)
            
            print(f"\nSLA Test Results - {scenario['timeframe']} Timeframe:")
            print(f"  Target: <{scenario['target_ms']}ms")
            print(f"  Mean: {mean_response:.2f}ms")
            print(f"  95th Percentile: {p95_response:.2f}ms") 
            print(f"  99th Percentile: {p99_response:.2f}ms")
            print(f"  SLA Compliance: {sla_compliance:.2%}")
            
            # Assertions
            assert sla_compliance >= 0.95  # 95% of requests must meet SLA
            assert p95_response <= scenario["target_ms"]
    
    @pytest.mark.performance 
    async def test_cache_performance_impact(self):
        """Test cache performance impact on response times"""
        
        test_request = {
            "request_id": "cache_test_001",
            "symbols": ["AAPL"],
            "timeframe_display_name": "1W"
        }
        
        # First request (cache miss)
        start_time = time.time()
        await self._execute_aggregation_request(test_request)
        cache_miss_time = (time.time() - start_time) * 1000
        
        # Second request (cache hit)
        start_time = time.time()
        await self._execute_aggregation_request(test_request)
        cache_hit_time = (time.time() - start_time) * 1000
        
        # Cache should provide significant performance improvement
        cache_improvement_ratio = cache_miss_time / cache_hit_time
        
        print(f"\nCache Performance Impact:")
        print(f"  Cache Miss Time: {cache_miss_time:.2f}ms")
        print(f"  Cache Hit Time: {cache_hit_time:.2f}ms")
        print(f"  Improvement Ratio: {cache_improvement_ratio:.2f}x")
        
        assert cache_hit_time < cache_miss_time
        assert cache_improvement_ratio >= 2.0  # Cache should be at least 2x faster
        
        # Cache hit should be very fast
        assert cache_hit_time < 50  # <50ms for cache hits

# Locust-based Load Testing
class AggregationLoadTest(HttpUser):
    """
    Locust-based load testing for realistic user scenarios
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Setup for each simulated user"""
        self.request_counter = 0
    
    @task(3)
    def test_single_symbol_1w_aggregation(self):
        """Most common scenario: Single symbol, 1W timeframe"""
        self.request_counter += 1
        
        payload = {
            "request_id": f"load_test_1w_{self.request_counter}",
            "symbols": ["AAPL"],
            "timeframe_type": "weeks",
            "timeframe_value": 1,
            "timeframe_display_name": "1W",
            "timeframe_hours": 168,
            "aggregation_strategy": "ensemble"
        }
        
        with self.client.post("/api/v1/aggregation/calculate", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response_data = response.json()
                if len(response_data) == 1 and response_data[0]["symbol"] == "AAPL":
                    response.success()
                else:
                    response.failure("Invalid response data")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def test_single_symbol_1m_aggregation(self):
        """Common scenario: Single symbol, 1M timeframe"""
        self.request_counter += 1
        
        payload = {
            "request_id": f"load_test_1m_{self.request_counter}",
            "symbols": ["GOOGL"],
            "timeframe_type": "months",
            "timeframe_value": 1,
            "timeframe_display_name": "1M",
            "timeframe_hours": 720,
            "aggregation_strategy": "weighted_average"
        }
        
        with self.client.post("/api/v1/aggregation/calculate", json=payload) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def test_multi_symbol_aggregation(self):
        """Less common scenario: Multiple symbols"""
        self.request_counter += 1
        
        payload = {
            "request_id": f"load_test_multi_{self.request_counter}",
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "timeframe_type": "weeks",
            "timeframe_value": 1,
            "timeframe_display_name": "1W",
            "timeframe_hours": 168,
            "aggregation_strategy": "ensemble"
        }
        
        with self.client.post("/api/v1/aggregation/calculate", json=payload) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
```

---

## 📋 **Quality Assurance Checklist**

### **Code Quality Standards**

#### **Unit Testing Requirements**
- [ ] **Domain Layer**: >95% test coverage mit mathematical correctness validation
- [ ] **Application Layer**: >90% test coverage mit error scenario testing
- [ ] **Infrastructure Layer**: >85% test coverage mit integration testing
- [ ] **Presentation Layer**: >90% test coverage mit API contract testing

#### **Integration Testing Requirements**
- [ ] **Database Integration**: CRUD operations, query performance, transaction handling
- [ ] **Cache Integration**: Cache hit/miss scenarios, TTL management, performance validation
- [ ] **Event Integration**: Event publishing, cross-service communication, schema validation
- [ ] **API Integration**: End-to-end workflows, error handling, response validation

#### **Performance Testing Requirements**
- [ ] **Response Time SLAs**: <300ms (1M), <150ms (1W) at 95th percentile
- [ ] **Throughput Testing**: 50+ concurrent requests sustained
- [ ] **Cache Performance**: >85% hit rate, <50ms cache hit response time
- [ ] **Load Testing**: System stability under sustained load

### **Testing Automation & CI/CD Integration**

```yaml
# .github/workflows/aggregation-tests.yml
name: Aggregation Service Testing Pipeline

on:
  push:
    branches: [ main, develop ]
    paths: [ 'services/data-processing-enhanced/**' ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python 3.11
      uses: actions/setup-python@v3
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
    
    - name: Run Unit Tests
      run: |
        pytest tests/unit/ -v --cov=aggregation --cov-report=xml --cov-fail-under=90
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: testdb
      redis:
        image: redis:7
        
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python 3.11
      uses: actions/setup-python@v3
      with:
        python-version: 3.11
        
    - name: Run Integration Tests
      run: |
        pytest tests/integration/ -v --durations=10
        
    - name: Performance Benchmark Tests
      run: |
        pytest tests/performance/ -v --benchmark-only --benchmark-json=benchmark.json
        
  e2e-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Start Full Test Environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
        
    - name: Run E2E Tests
      run: |
        pytest tests/e2e/ -v --tb=short
        
    - name: Load Testing with Locust
      run: |
        locust -f tests/performance/locust_tests.py --headless -u 50 -r 10 -t 5m --host=http://localhost:8017
  
  quality-gates:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests]
    
    steps:
    - name: SonarQube Quality Gate
      uses: sonarqube-quality-gate-action@master
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        
    - name: Performance SLA Validation
      run: |
        python scripts/validate_performance_slas.py benchmark.json
```

### **Final Acceptance Criteria**

#### **Functional Requirements**
- ✅ Alle Aggregation Strategies (weighted_average, median, ensemble) funktionieren korrekt
- ✅ Mathematical Validation Algorithms produzieren accurate results (>99.9%)
- ✅ Quality Assessment Framework bewertet Predictions korrekt
- ✅ Cache Strategy erreicht >85% Hit Rate
- ✅ Event-Driven Integration funktioniert cross-service

#### **Non-Functional Requirements**
- ✅ Response Time SLAs eingehalten (<300ms 1M, <150ms 1W)
- ✅ System handhabt 50+ concurrent requests stabil
- ✅ Error Rate <1% unter normaler Last
- ✅ Database Queries <50ms (95th percentile)
- ✅ Cache Operations <10ms (95th percentile)

#### **Quality Requirements**
- ✅ Test Coverage >90% overall, >95% Domain Layer
- ✅ SonarQube Quality Gate: A-Rating oder besser
- ✅ Keine Critical oder High Severity Security Issues
- ✅ Code Review Approval für alle Changes
- ✅ Documentation Complete und Up-to-Date

#### **Integration Requirements**
- ✅ Backward Compatibility mit bestehenden Services
- ✅ Event Schemas kompatibel mit Event Bus
- ✅ Database Migrations erfolgreich
- ✅ Zero-Downtime Deployment möglich
- ✅ Rollback Strategy getestet und funktional

---

*Test Strategy - Timeframe Aggregation v7.1*  
*Quality First Approach - Mathematical Correctness & Performance Excellence*  
*Clean Architecture Testing - SOLID Principles Validation*  
*Erstellt: 27. August 2025*