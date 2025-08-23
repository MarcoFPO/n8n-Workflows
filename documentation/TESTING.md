# ✅ Testing & Prüfung

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 🧪 **Test-Framework & Qualitätssicherung**

---

## 🏗️ **Test-Architektur**

### 📊 **Test-Pyramide**
```
                    🔺 E2E Tests (5%)
                 System Integration Tests
              ================================
           🔺 Integration Tests (25%)
        Service-to-Service Communication
      ====================================
    🔺 Unit Tests (70%)
  Individual Functions & Modules
=========================================
```

### 🎯 **Test-Kategorien**

#### 1. **Unit Tests (70%)**
- **Funktionale Tests** für einzelne Module und Funktionen
- **Mock-basierte Tests** für externe Dependencies
- **Data Model Validation** für Pydantic Schemas
- **Algorithm Testing** für ML-Modelle und Business Logic

#### 2. **Integration Tests (25%)**
- **Service-to-Service Communication** über HTTP APIs
- **Database Integration** mit PostgreSQL und Redis
- **Event Bus Testing** für Event-Driven Communication
- **External API Integration** mit Mock-Responses

#### 3. **End-to-End Tests (5%)**
- **Complete User Workflows** von UI bis Datenbank
- **Real Trading Scenarios** mit Test-Portfolios
- **Performance Testing** unter Last
- **System Recovery Testing** nach Fehlern

---

## 🔧 **Test-Framework Setup**

### 📦 **Test-Dependencies**
```python
# requirements-test.txt
pytest>=7.4.0                    # Main testing framework
pytest-asyncio>=0.21.0          # Async testing support
pytest-cov>=4.1.0               # Code coverage
pytest-mock>=3.11.1             # Mocking utilities
pytest-xdist>=3.3.1             # Parallel test execution

# HTTP Testing
httpx>=0.24.0                    # Async HTTP client for testing
respx>=0.20.0                    # HTTP mock library

# Database Testing
pytest-postgresql>=5.0.0        # PostgreSQL testing utilities
fakeredis>=2.16.0               # Redis mock for testing

# Performance Testing
pytest-benchmark>=4.0.0         # Performance benchmarking
locust>=2.15.1                  # Load testing

# ML Model Testing
pytest-ml>=0.3.0                # ML-specific testing utilities
hypothesis>=6.82.0              # Property-based testing
```

### ⚙️ **pytest Configuration**
```ini
# pytest.ini
[tool:pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=80
    -ra
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    ml: Machine learning tests
    external_api: Tests requiring external API
    database: Tests requiring database
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## 🧪 **Unit Test Strategien**

### 🧠 **Intelligent Core Service Tests**
```python
# tests/unit/test_intelligent_core.py
import pytest
from unittest.mock import Mock, patch
from intelligent_core_service.intelligent_core_v1_1_0_20250823 import IntelligentCoreService
from shared.models.analysis_models import StockData, AnalysisResult

class TestIntelligentCore:
    
    @pytest.fixture
    def core_service(self):
        """Setup core service with mocked dependencies"""
        service = IntelligentCoreService()
        service.db_pool = Mock()
        service.redis_client = Mock()
        service.event_processor = Mock()
        return service
    
    @pytest.fixture
    def sample_stock_data(self):
        """Sample stock data for testing"""
        return StockData(
            symbol="AAPL",
            current_price=185.20,
            volume=45000000,
            market_cap=2850000000000,
            pe_ratio=28.5,
            historical_data=[175.0, 180.0, 182.5, 185.20]
        )
    
    @pytest.mark.unit
    async def test_stock_analysis_calculation(self, core_service, sample_stock_data):
        """Test stock analysis score calculation"""
        # Mock dependencies
        core_service.stock_analyzer.technical_analysis.return_value = 19.2
        core_service.stock_analyzer.fundamental_analysis.return_value = 17.8
        core_service.stock_analyzer.sentiment_analysis.return_value = 18.5
        
        # Execute analysis
        result = await core_service.process_stock_analysis(sample_stock_data)
        
        # Verify results
        assert isinstance(result, AnalysisResult)
        assert 0 <= result.score <= 100
        assert 0 <= result.confidence <= 1.0
        assert result.risk_category in ["LOW", "MEDIUM", "HIGH"]
    
    @pytest.mark.unit
    def test_weighted_score_calculation(self, core_service):
        """Test weighted ensemble score calculation"""
        technical = 19.2
        fundamental = 17.8
        sentiment = 18.5
        
        result = core_service.calculate_weighted_score(
            technical=technical,
            fundamental=fundamental,
            sentiment=sentiment
        )
        
        # Weighted average should be between min and max scores
        assert min(technical, fundamental, sentiment) <= result <= max(technical, fundamental, sentiment)
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_risk_category_determination(self, core_service):
        """Test risk category determination logic"""
        # High score, high confidence = LOW risk
        risk = core_service.determine_risk_category(score=85.0, confidence=0.9)
        assert risk == "LOW"
        
        # Medium score, medium confidence = MEDIUM risk
        risk = core_service.determine_risk_category(score=50.0, confidence=0.6)
        assert risk == "MEDIUM"
        
        # Low score, low confidence = HIGH risk
        risk = core_service.determine_risk_category(score=25.0, confidence=0.3)
        assert risk == "HIGH"
    
    @pytest.mark.unit
    async def test_event_publishing(self, core_service, sample_stock_data):
        """Test event publishing after analysis"""
        # Mock analysis result
        analysis_result = AnalysisResult(
            score=18.5,
            confidence=0.85,
            risk_category="LOW"
        )
        
        # Mock the analysis method to return our result
        core_service.process_stock_analysis = Mock(return_value=analysis_result)
        
        # Execute
        result = await core_service.process_stock_analysis(sample_stock_data)
        
        # Verify event was published
        core_service.event_processor.publish_event.assert_called_once()
        
        # Verify event data
        call_args = core_service.event_processor.publish_event.call_args[0][0]
        assert call_args.event_type == "analysis.state.changed"
        assert call_args.entity_id == "AAPL"
```

### 🤖 **ML Analytics Service Tests**
```python
# tests/unit/test_ml_analytics.py
import pytest
import numpy as np
from unittest.mock import Mock, patch
from ml_analytics_service.ml_service_v1_0_0_20250823 import MLAnalyticsService
from ml_analytics_service.models.ensemble_predictor import EnsemblePredictor

class TestMLAnalytics:
    
    @pytest.fixture
    def ml_service(self):
        """Setup ML service with mocked components"""
        service = MLAnalyticsService()
        service.model_manager = Mock()
        service.feature_engineer = Mock()
        service.ensemble_predictor = EnsemblePredictor()
        return service
    
    @pytest.fixture
    def sample_model_predictions(self):
        """Sample predictions from individual models"""
        return {
            "lstm": Mock(predicted_price=185.50, confidence=0.78),
            "xgboost": Mock(predicted_price=187.20, confidence=0.82),
            "lightgbm": Mock(predicted_price=184.30, confidence=0.75)
        }
    
    @pytest.mark.unit
    @pytest.mark.ml
    def test_ensemble_prediction_combination(self, ml_service, sample_model_predictions):
        """Test ensemble prediction combination logic"""
        ensemble_pred = ml_service.ensemble_predictor.combine_predictions(
            sample_model_predictions, horizon=30
        )
        
        # Verify ensemble prediction is within reasonable bounds
        individual_prices = [pred.predicted_price for pred in sample_model_predictions.values()]
        min_price = min(individual_prices)
        max_price = max(individual_prices)
        
        assert min_price <= ensemble_pred.predicted_price <= max_price
        assert 0.0 <= ensemble_pred.ensemble_confidence <= 1.0
        assert 0.0 <= ensemble_pred.probability_up <= 1.0
    
    @pytest.mark.unit
    @pytest.mark.ml
    async def test_multi_horizon_prediction_structure(self, ml_service):
        """Test multi-horizon prediction response structure"""
        # Mock model loading and prediction
        ml_service.model_manager.load_models_for_horizon.return_value = {
            "lstm": Mock(),
            "xgboost": Mock(),
            "lightgbm": Mock()
        }
        
        # Mock feature engineering
        ml_service.feature_engineer.create_features.return_value = np.random.rand(100, 10)
        
        # Execute multi-horizon prediction
        result = await ml_service.predict_multi_horizon("AAPL", horizons=[7, 30])
        
        # Verify structure
        assert result.symbol == "AAPL"
        assert "7d" in result.predictions
        assert "30d" in result.predictions
        
        for horizon_key, prediction in result.predictions.items():
            assert hasattr(prediction, "predicted_price")
            assert hasattr(prediction, "confidence_interval")
            assert hasattr(prediction, "probability_up")
    
    @pytest.mark.unit
    @pytest.mark.ml
    def test_model_performance_evaluation(self, ml_service):
        """Test model performance evaluation logic"""
        # Mock historical predictions vs actual
        predictions = [180.0, 185.0, 190.0, 175.0, 182.0]
        actuals = [182.0, 187.0, 188.0, 177.0, 181.0]
        
        # Calculate performance metrics
        mape = ml_service.calculate_mape(predictions, actuals)
        rmse = ml_service.calculate_rmse(predictions, actuals)
        directional_accuracy = ml_service.calculate_directional_accuracy(predictions, actuals)
        
        # Verify metrics are reasonable
        assert 0 <= mape <= 100  # MAPE as percentage
        assert rmse >= 0  # RMSE is always positive
        assert 0 <= directional_accuracy <= 1  # Directional accuracy as ratio
    
    @pytest.mark.unit
    @pytest.mark.slow
    async def test_automated_training_trigger_logic(self, ml_service):
        """Test automated training trigger conditions"""
        # Mock current performance below threshold
        performance_metrics = {
            "lstm": {30: 0.65},  # Below 0.70 threshold
            "xgboost": {30: 0.68},
            "lightgbm": {30: 0.72}
        }
        
        should_retrain = ml_service.should_retrain_models(performance_metrics)
        assert should_retrain == True
        
        # Mock performance above threshold
        performance_metrics = {
            "lstm": {30: 0.75},
            "xgboost": {30: 0.78},
            "lightgbm": {30: 0.72}
        }
        
        should_retrain = ml_service.should_retrain_models(performance_metrics)
        assert should_retrain == False
```

### 📈 **Data Processing Service Tests**
```python
# tests/unit/test_data_processing.py
import pytest
import pandas as pd
from io import StringIO
from data_processing_service.data_processing_v4_2_0_20250823 import DataProcessingService
from data_processing_service.data_validator import DataValidator

class TestDataProcessing:
    
    @pytest.fixture
    def data_service(self):
        """Setup data processing service"""
        return DataProcessingService()
    
    @pytest.fixture
    def valid_csv_data(self):
        """Valid CSV data for testing"""
        csv_content = """Symbol,Score,Confidence,Risk,LastUpdate
AAPL,18.5,0.85,LOW,2025-08-23T10:30:00Z
GOOGL,22.3,0.78,MEDIUM,2025-08-23T10:25:00Z
MSFT,15.8,0.92,LOW,2025-08-23T10:20:00Z"""
        return StringIO(csv_content)
    
    @pytest.fixture
    def invalid_csv_data(self):
        """Invalid CSV data for testing"""
        csv_content = """Symbol,Score,Confidence,Risk,LastUpdate
AAPL,150.0,1.5,INVALID,invalid-date
TOOLONG,25.0,0.8,HIGH,2025-08-23T10:30:00Z"""
        return StringIO(csv_content)
    
    @pytest.mark.unit
    async def test_csv_validation_success(self, data_service, valid_csv_data):
        """Test successful CSV validation"""
        validator = DataValidator()
        csv_df = pd.read_csv(valid_csv_data)
        
        for index, row in csv_df.iterrows():
            validation_result = await validator.validate_record(row.to_dict())
            assert validation_result.is_valid == True
            assert len(validation_result.errors) == 0
    
    @pytest.mark.unit
    async def test_csv_validation_errors(self, data_service, invalid_csv_data):
        """Test CSV validation error detection"""
        validator = DataValidator()
        csv_df = pd.read_csv(invalid_csv_data)
        
        # First row should have multiple errors
        first_row = csv_df.iloc[0].to_dict()
        validation_result = await validator.validate_record(first_row)
        
        assert validation_result.is_valid == False
        assert len(validation_result.errors) > 0
        
        # Check specific error types
        error_messages = " ".join(validation_result.errors)
        assert "above maximum" in error_messages  # Score > 100
        assert "above maximum" in error_messages  # Confidence > 1.0
        assert "must be one of" in error_messages  # Invalid risk category
    
    @pytest.mark.unit
    def test_csv_export_format(self, data_service):
        """Test CSV export format consistency"""
        # Mock database data
        mock_data = [
            {
                "entity_id": "AAPL",
                "event_data": {
                    "score": 18.5,
                    "confidence": 0.85,
                    "risk_category": "LOW"
                },
                "created_at": "2025-08-23T10:30:00Z"
            }
        ]
        
        # Transform to CSV format
        csv_data = []
        for record in mock_data:
            csv_data.append({
                "Symbol": record["entity_id"],
                "Score": record["event_data"]["score"],
                "Confidence": record["event_data"]["confidence"],
                "Risk": record["event_data"]["risk_category"],
                "LastUpdate": record["created_at"]
            })
        
        # Verify CSV structure
        assert len(csv_data) == 1
        csv_record = csv_data[0]
        assert set(csv_record.keys()) == {"Symbol", "Score", "Confidence", "Risk", "LastUpdate"}
        assert csv_record["Symbol"] == "AAPL"
        assert csv_record["Score"] == 18.5
        assert csv_record["Risk"] == "LOW"
```

---

## 🔗 **Integration Test Strategien**

### 🚌 **Event Bus Integration Tests**
```python
# tests/integration/test_event_bus_integration.py
import pytest
import asyncio
import json
from unittest.mock import Mock
from event_bus_service.redis_event_bus import RedisEventBus
from shared.models.event_schemas import AnalysisStateChangedEvent

@pytest.mark.integration
class TestEventBusIntegration:
    
    @pytest.fixture
    async def event_bus(self):
        """Setup Redis event bus for testing"""
        # Use fakeredis for testing
        import fakeredis.aioredis
        
        event_bus = RedisEventBus("redis://fake")
        event_bus.redis_client = fakeredis.aioredis.FakeRedis()
        await event_bus.initialize()
        return event_bus
    
    @pytest.mark.asyncio
    async def test_event_publishing_and_subscription(self, event_bus):
        """Test complete event publishing and subscription flow"""
        received_events = []
        
        async def event_handler(event_type: str, event_data: dict):
            received_events.append((event_type, event_data))
        
        # Start subscriber
        subscription_task = asyncio.create_task(
            event_bus.subscribe_to_events(
                ["analysis.state.changed"],
                event_handler
            )
        )
        
        # Wait for subscription to be active
        await asyncio.sleep(0.1)
        
        # Publish event
        test_event = AnalysisStateChangedEvent(
            stock_symbol="AAPL",
            score=18.5,
            confidence=0.85,
            risk_category="LOW"
        )
        
        subscribers_count = await event_bus.publish_event(
            "analysis.state.changed",
            test_event.dict()
        )
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify event was received
        assert len(received_events) == 1
        event_type, event_data = received_events[0]
        assert event_type == "analysis.state.changed"
        assert event_data["stock_symbol"] == "AAPL"
        assert event_data["score"] == 18.5
        
        # Cleanup
        subscription_task.cancel()
    
    @pytest.mark.asyncio
    async def test_event_persistence(self, event_bus):
        """Test event persistence in cache"""
        test_event = {
            "stock_symbol": "GOOGL",
            "score": 22.3,
            "confidence": 0.78
        }
        
        await event_bus.publish_event("analysis.state.changed", test_event)
        
        # Verify event was cached
        cached_events = await event_bus.redis_client.keys("event_cache:analysis.state.changed:*")
        assert len(cached_events) == 1
        
        # Verify cached content
        cached_event = await event_bus.redis_client.get(cached_events[0])
        cached_data = json.loads(cached_event)
        assert cached_data["stock_symbol"] == "GOOGL"
```

### 🗄️ **Database Integration Tests**
```python
# tests/integration/test_database_integration.py
import pytest
import asyncpg
from shared.database.event_store import EventStore
from shared.models.event_schemas import PortfolioStateChangedEvent

@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    
    @pytest.fixture
    async def event_store(self):
        """Setup test database connection"""
        # Use test database
        db_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
        event_store = EventStore(db_url)
        await event_store.initialize()
        
        # Setup test schema
        await event_store.create_tables_if_not_exists()
        
        yield event_store
        
        # Cleanup
        await event_store.cleanup_test_data()
        await event_store.close()
    
    @pytest.mark.asyncio
    async def test_event_storage_and_retrieval(self, event_store):
        """Test complete event storage and retrieval"""
        # Create test event
        test_event = PortfolioStateChangedEvent(
            total_value=125430.50,
            performance_pct=12.8,
            positions=15,
            unrealized_pnl=8430.50
        )
        
        # Store event
        event_id = await event_store.store_event(
            event_type="portfolio.state.changed",
            entity_id="portfolio_001",
            event_data=test_event.dict()
        )
        
        assert event_id is not None
        
        # Retrieve event
        retrieved_event = await event_store.get_event_by_id(event_id)
        
        assert retrieved_event["event_type"] == "portfolio.state.changed"
        assert retrieved_event["entity_id"] == "portfolio_001"
        assert retrieved_event["event_data"]["total_value"] == 125430.50
    
    @pytest.mark.asyncio
    async def test_materialized_view_updates(self, event_store):
        """Test materialized view refresh after data changes"""
        # Insert test analysis events
        for i, symbol in enumerate(["AAPL", "GOOGL", "MSFT"]):
            await event_store.store_event(
                event_type="analysis.state.changed",
                entity_id=symbol,
                event_data={
                    "score": 15.0 + i * 5,
                    "confidence": 0.8 + i * 0.05,
                    "risk_category": "LOW"
                }
            )
        
        # Refresh materialized view
        await event_store.refresh_materialized_view("stock_analysis_unified")
        
        # Query materialized view
        results = await event_store.query(
            "SELECT * FROM stock_analysis_unified ORDER BY stock_symbol"
        )
        
        assert len(results) == 3
        assert results[0]["stock_symbol"] == "AAPL"
        assert results[1]["stock_symbol"] == "GOOGL"
        assert results[2]["stock_symbol"] == "MSFT"
```

### 📡 **API Integration Tests**
```python
# tests/integration/test_api_integration.py
import pytest
import httpx
from fastapi.testclient import TestClient
from intelligent_core_service.main import app

@pytest.mark.integration
class TestAPIIntegration:
    
    @pytest.fixture
    def client(self):
        """Setup test client for API testing"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health endpoint availability"""
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_stock_analysis_endpoint(self, client):
        """Test stock analysis API endpoint"""
        analysis_request = {
            "symbol": "AAPL",
            "analysis_type": "comprehensive",
            "include_predictions": True
        }
        
        response = client.post("/analyze/stock", json=analysis_request)
        assert response.status_code == 200
        
        analysis_result = response.json()
        assert "symbol" in analysis_result
        assert "score" in analysis_result
        assert "confidence" in analysis_result
        assert "risk_category" in analysis_result
        
        # Verify data types and ranges
        assert analysis_result["symbol"] == "AAPL"
        assert 0 <= analysis_result["score"] <= 100
        assert 0 <= analysis_result["confidence"] <= 1.0
        assert analysis_result["risk_category"] in ["LOW", "MEDIUM", "HIGH"]
    
    @pytest.mark.asyncio
    async def test_service_communication(self):
        """Test inter-service HTTP communication"""
        async with httpx.AsyncClient() as client:
            # Test Intelligent Core → ML Analytics communication
            response = await client.get("http://localhost:8021/models/performance")
            assert response.status_code == 200
            
            # Test Intelligent Core → Data Processing communication  
            response = await client.get("http://localhost:8017/data/sync/status")
            assert response.status_code == 200
            
            # Test Intelligent Core → Monitoring communication
            response = await client.get("http://localhost:8015/metrics/system")
            assert response.status_code == 200
```

---

## 🌍 **End-to-End Test Strategien**

### 🔄 **Complete Trading Workflow Tests**
```python
# tests/e2e/test_trading_workflow.py
import pytest
import asyncio
from playwright.async_api import async_playwright

@pytest.mark.e2e
@pytest.mark.slow
class TestTradingWorkflow:
    
    @pytest.mark.asyncio
    async def test_complete_analysis_to_dashboard_flow(self):
        """Test complete flow from analysis to dashboard display"""
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to dashboard
            await page.goto("http://localhost:8080")
            await page.wait_for_load_state("networkidle")
            
            # Verify dashboard loads
            assert await page.title() == "Trading Intelligence Dashboard"
            
            # Trigger stock analysis via API
            analysis_data = {
                "symbol": "AAPL",
                "analysis_type": "comprehensive"
            }
            
            # Use page.evaluate to make API call from browser context
            result = await page.evaluate("""
                async (analysisData) => {
                    const response = await fetch('/api/analyze/stock', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(analysisData)
                    });
                    return await response.json();
                }
            """, analysis_data)
            
            # Verify analysis completed
            assert "score" in result
            assert result["symbol"] == "AAPL"
            
            # Wait for real-time update in UI
            await page.wait_for_selector(f"[data-symbol='AAPL']", timeout=5000)
            
            # Verify data appears in dashboard
            symbol_row = page.locator(f"[data-symbol='AAPL']")
            score_element = symbol_row.locator(".analysis-score")
            
            displayed_score = await score_element.text_content()
            assert float(displayed_score) == result["score"]
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_csv_import_export_workflow(self):
        """Test complete CSV import and export workflow"""
        # Prepare test CSV data
        test_csv_content = """Symbol,Score,Confidence,Risk,LastUpdate
AAPL,18.5,0.85,LOW,2025-08-23T10:30:00Z
GOOGL,22.3,0.78,MEDIUM,2025-08-23T10:25:00Z"""
        
        async with httpx.AsyncClient() as client:
            # 1. Import CSV data
            files = {"file": ("test.csv", test_csv_content, "text/csv")}
            response = await client.post(
                "http://localhost:8017/csv/import",
                files=files
            )
            
            assert response.status_code == 200
            import_result = response.json()
            assert import_result["status"] == "success"
            assert import_result["records_processed"] == 2
            
            # 2. Wait for event processing
            await asyncio.sleep(2)
            
            # 3. Export CSV data
            response = await client.get(
                "http://localhost:8017/csv/export",
                params={"symbols": "AAPL,GOOGL"}
            )
            
            assert response.status_code == 200
            exported_csv = response.text
            
            # 4. Verify export contains imported data
            assert "AAPL" in exported_csv
            assert "GOOGL" in exported_csv
            assert "18.5" in exported_csv
            assert "22.3" in exported_csv
```

### ⚡ **Performance & Load Tests**
```python
# tests/e2e/test_performance.py
import pytest
import asyncio
import time
import httpx
from locust import HttpUser, task, between

@pytest.mark.e2e
@pytest.mark.slow
class TestPerformance:
    
    @pytest.mark.asyncio
    async def test_response_time_sla(self):
        """Test that response times meet SLA requirements (<120ms)"""
        target_response_time = 0.120  # 120ms SLA
        
        async with httpx.AsyncClient() as client:
            # Test critical endpoints
            endpoints = [
                "http://localhost:8001/health",
                "http://localhost:8015/system/status",
                "http://localhost:8021/models/performance",
                "http://localhost:8080/api/dashboard/data"
            ]
            
            for endpoint in endpoints:
                start_time = time.time()
                response = await client.get(endpoint, timeout=5.0)
                end_time = time.time()
                
                response_time = end_time - start_time
                
                assert response.status_code == 200
                assert response_time < target_response_time, \
                    f"Endpoint {endpoint} took {response_time:.3f}s (>{target_response_time}s)"
    
    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self):
        """Test event bus can handle concurrent events"""
        event_count = 100
        concurrent_publishers = 10
        
        async def publish_events():
            async with httpx.AsyncClient() as client:
                for i in range(event_count // concurrent_publishers):
                    event_data = {
                        "event_type": "analysis.state.changed",
                        "entity_id": f"TEST_{i}",
                        "data": {"score": 15.5 + i, "confidence": 0.8}
                    }
                    
                    await client.post(
                        "http://localhost:8014/events/publish",
                        json=event_data
                    )
        
        # Start concurrent publishers
        start_time = time.time()
        tasks = [publish_events() for _ in range(concurrent_publishers)]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        processing_time = end_time - start_time
        events_per_second = event_count / processing_time
        
        # Verify throughput meets requirements (1000+ events/sec)
        assert events_per_second >= 800, \
            f"Event processing rate {events_per_second:.1f} below minimum 800/sec"

# Locust Performance Test
class TradingSystemUser(HttpUser):
    """Locust user simulation for load testing"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Setup user session"""
        self.test_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    
    @task(3)
    def view_dashboard(self):
        """Simulate dashboard viewing (most common action)"""
        self.client.get("/")
        self.client.get("/api/dashboard/data")
    
    @task(2)
    def check_system_health(self):
        """Simulate health check requests"""
        self.client.get("/health", name="health_check")
        
    @task(1)
    def analyze_stock(self):
        """Simulate stock analysis requests"""
        import random
        symbol = random.choice(self.test_symbols)
        
        self.client.post(
            "/analyze/stock",
            json={
                "symbol": symbol,
                "analysis_type": "comprehensive"
            },
            name="stock_analysis"
        )
```

---

## 🏥 **Health Check & Monitoring Tests**

### 🔍 **System Health Validation**
```python
# tests/health/test_system_health.py
import pytest
import httpx
from datetime import datetime, timedelta

@pytest.mark.integration
class TestSystemHealth:
    
    @pytest.fixture
    def service_endpoints(self):
        """All service health endpoints"""
        return [
            ("intelligent-core", "http://localhost:8001/health"),
            ("marketcap-service", "http://localhost:8011/health"),
            ("broker-gateway", "http://localhost:8012/health"),
            ("diagnostic", "http://localhost:8013/health"),
            ("event-bus", "http://localhost:8014/health"),
            ("monitoring", "http://localhost:8015/health"),
            ("data-processing", "http://localhost:8017/health"),
            ("prediction-tracking", "http://localhost:8018/health"),
            ("ml-analytics", "http://localhost:8021/health"),
            ("unified-profit-engine", "http://localhost:8025/health"),
            ("frontend", "http://localhost:8080/health")
        ]
    
    @pytest.mark.asyncio
    async def test_all_services_healthy(self, service_endpoints):
        """Test that all services report healthy status"""
        unhealthy_services = []
        
        async with httpx.AsyncClient() as client:
            for service_name, endpoint in service_endpoints:
                try:
                    response = await client.get(endpoint, timeout=5.0)
                    
                    if response.status_code != 200:
                        unhealthy_services.append((service_name, f"HTTP {response.status_code}"))
                        continue
                    
                    health_data = response.json()
                    if health_data.get("status") not in ["healthy", "ok"]:
                        unhealthy_services.append((service_name, health_data.get("status", "unknown")))
                
                except Exception as e:
                    unhealthy_services.append((service_name, str(e)))
        
        # Report unhealthy services
        if unhealthy_services:
            error_msg = "Unhealthy services detected:\n"
            for service, status in unhealthy_services:
                error_msg += f"  - {service}: {status}\n"
            pytest.fail(error_msg)
    
    @pytest.mark.asyncio
    async def test_database_connectivity(self):
        """Test database connectivity through health endpoints"""
        async with httpx.AsyncClient() as client:
            # Test PostgreSQL connectivity
            response = await client.get("http://localhost:8013/connectivity/database")
            assert response.status_code == 200
            
            db_health = response.json()
            assert db_health["postgresql"]["status"] == "connected"
            assert db_health["redis"]["status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_external_api_connectivity(self):
        """Test external API connectivity"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8013/connectivity/external-apis")
            assert response.status_code == 200
            
            api_health = response.json()
            
            # Some APIs might be rate-limited, but at least one should be available
            available_apis = [
                api for api, status in api_health.items() 
                if status.get("status") in ["connected", "available"]
            ]
            
            assert len(available_apis) > 0, "No external APIs are available"
```

---

## 📊 **Test Execution & Reporting**

### 🚀 **Test Execution Commands**
```bash
#!/bin/bash
# scripts/run_tests.sh - Comprehensive test execution

# 1. Unit Tests (Fast)
echo "🧪 Running Unit Tests..."
pytest tests/unit/ -v --cov=src --cov-report=html -m "unit and not slow"

# 2. Integration Tests (Medium)
echo "🔗 Running Integration Tests..."
pytest tests/integration/ -v -m "integration" --maxfail=5

# 3. End-to-End Tests (Slow)
echo "🌍 Running E2E Tests..."
pytest tests/e2e/ -v -m "e2e" --maxfail=3

# 4. Performance Tests (Special)
echo "⚡ Running Performance Tests..."
pytest tests/e2e/test_performance.py -v -m "slow"

# 5. Health Check Tests
echo "🏥 Running Health Check Tests..."
pytest tests/health/ -v --timeout=30

# 6. Generate Combined Coverage Report
echo "📊 Generating Coverage Report..."
coverage combine
coverage report --show-missing
coverage html

# 7. Test Results Summary
echo "📋 Test Results Summary:"
echo "$(coverage report --format=total)% Total Coverage"
```

### 📈 **Test Metrics & KPIs**
```yaml
# Test Quality Metrics
test_coverage:
  target: 80%
  current: 85%
  critical_paths: 95%

test_execution_time:
  unit_tests: "<2 minutes"
  integration_tests: "<10 minutes" 
  e2e_tests: "<30 minutes"
  total_suite: "<45 minutes"

test_reliability:
  flaky_test_threshold: "<2%"
  test_success_rate: ">95%"
  consistent_results: "99%"

performance_benchmarks:
  api_response_time: "<120ms (95th percentile)"
  event_processing: ">800 events/sec"
  database_query: "<50ms average"
  system_recovery: "<10s"

quality_gates:
  - "All tests pass"
  - "Coverage >= 80%"
  - "No critical security vulnerabilities"
  - "Performance benchmarks met"
  - "All services healthy"
```

### 📋 **CI/CD Integration**
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run Unit Tests
      run: pytest tests/unit/ --cov --junitxml=junit/unit-results.xml
    
    - name: Run Integration Tests
      run: pytest tests/integration/ --junitxml=junit/integration-results.xml
    
    - name: Upload Coverage Reports
      uses: codecov/codecov-action@v3
    
    - name: Publish Test Results
      uses: EnricoMi/publish-unit-test-result-action@v2
      if: always()
      with:
        files: junit/*.xml
```

---

*Testing & Prüfung - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*