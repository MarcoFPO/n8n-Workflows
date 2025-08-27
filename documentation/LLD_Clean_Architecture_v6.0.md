# 🏗️ Low-Level Design (LLD) - Clean Architecture Integration v7.1

## 🎯 **Enhanced Service Architecture - Clean Architecture Principles**

### 📊 **Unified Profit Engine Enhanced - Port 8025**

#### 🏛️ **Clean Architecture Layers**

```python
# Domain Layer - Core Business Logic
class MarketSymbol:
    """Value Object für Aktien-Symbole"""
    def __init__(self, symbol: str, company_name: str, market_region: str):
        self.symbol = symbol
        self.company_name = company_name
        self.market_region = market_region
        self.validate()

class ProfitPrediction:
    """Entity für Gewinnvorhersagen"""
    def __init__(self, symbol: str, horizon: str, target_date: date, 
                 profit_forecast: Decimal, confidence: float):
        self.id = uuid4()
        self.symbol = symbol
        self.horizon = horizon
        self.target_date = target_date
        self.profit_forecast = profit_forecast
        self.confidence = confidence
        self.created_at = datetime.now()

class SOLLISTTracking:
    """Aggregate Root für SOLL-IST Performance Tracking"""
    def __init__(self, datum: date, symbol: str, unternehmen: str):
        self.datum = datum
        self.symbol = symbol
        self.unternehmen = unternehmen
        self.ist_gewinn: Optional[Decimal] = None
        self.soll_gewinn_1w: Optional[Decimal] = None
        self.soll_gewinn_1m: Optional[Decimal] = None
        self.soll_gewinn_3m: Optional[Decimal] = None
        self.soll_gewinn_12m: Optional[Decimal] = None
        
    def calculate_target_date(self, horizon: str) -> date:
        """Berechnet Zieldatum basierend auf Horizont"""
        horizon_days = {"1W": 7, "1M": 30, "3M": 90, "12M": 365}
        return self.datum + timedelta(days=horizon_days[horizon])
        
    def update_soll_gewinn(self, horizon: str, profit: Decimal):
        """Domain Logic für SOLL-Gewinn Updates"""
        setattr(self, f"soll_gewinn_{horizon.lower()}", profit)
        
    def calculate_performance_diff(self, horizon: str) -> Optional[Decimal]:
        """Berechnet IST-SOLL Differenz"""
        if self.ist_gewinn is None:
            return None
        soll_value = getattr(self, f"soll_gewinn_{horizon.lower()}")
        return self.ist_gewinn - soll_value if soll_value else None
```

#### 🔧 **Application Layer - Use Cases**

```python
class GenerateMultiHorizonPredictionsUseCase:
    """Use Case für Multi-Horizon Vorhersage-Generierung"""
    
    def __init__(self, 
                 market_data_repo: MarketDataRepository,
                 prediction_repo: PredictionRepository,
                 soll_ist_repo: SOLLISTTrackingRepository,
                 event_publisher: EventPublisher):
        self.market_data_repo = market_data_repo
        self.prediction_repo = prediction_repo
        self.soll_ist_repo = soll_ist_repo
        self.event_publisher = event_publisher
    
    async def execute(self, symbols: List[str]) -> List[SOLLISTTracking]:
        """
        Generiert Multi-Horizon Predictions für alle Symbole
        Integriert mit bestehender Event-Architecture
        """
        results = []
        
        for symbol in symbols:
            # 1. Market Data beschaffen
            market_data = await self.market_data_repo.get_current_data(symbol)
            
            # 2. Predictions für alle Horizonte generieren
            horizons = ["1W", "1M", "3M", "12M"]
            tracking = SOLLISTTracking(
                datum=date.today(),
                symbol=symbol,
                unternehmen=market_data.company_name
            )
            
            for horizon in horizons:
                # ML-basierte Vorhersage
                prediction = await self._generate_prediction(market_data, horizon)
                tracking.update_soll_gewinn(horizon, prediction.profit_forecast)
                
                # Prediction in Repository speichern
                await self.prediction_repo.save(prediction)
                
            # 3. SOLL-IST Tracking speichern
            await self.soll_ist_repo.save(tracking)
            results.append(tracking)
            
            # 4. Event publizieren
            await self.event_publisher.publish(
                "analysis.prediction.generated",
                {
                    "symbol": symbol,
                    "predictions": tracking.to_dict(),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        return results
    
    async def _generate_prediction(self, market_data: MarketData, 
                                  horizon: str) -> ProfitPrediction:
        """Private ML-Prediction Logik"""
        # Yahoo Finance Daten analysieren
        # Ensemble Learning anwenden
        # Confidence Score berechnen
        pass

class CalculateISTPerformanceUseCase:
    """Use Case für IST-Performance Berechnung"""
    
    def __init__(self, 
                 portfolio_repo: PortfolioRepository,
                 soll_ist_repo: SOLLISTTrackingRepository,
                 event_publisher: EventPublisher):
        self.portfolio_repo = portfolio_repo
        self.soll_ist_repo = soll_ist_repo
        self.event_publisher = event_publisher
    
    async def execute(self, symbols: List[str]) -> Dict[str, Decimal]:
        """Berechnet aktuelle IST-Performance für Symbole"""
        results = {}
        
        for symbol in symbols:
            # Portfolio Performance ermitteln
            ist_gewinn = await self._calculate_ist_profit(symbol)
            
            # SOLL-IST Tracking aktualisieren
            tracking = await self.soll_ist_repo.get_by_symbol_and_date(
                symbol, date.today()
            )
            
            if tracking:
                tracking.ist_gewinn = ist_gewinn
                await self.soll_ist_repo.update(tracking)
                
                # Event publizieren
                await self.event_publisher.publish(
                    "profit.calculation.completed",
                    {
                        "symbol": symbol,
                        "ist_gewinn": float(ist_gewinn),
                        "soll_ist_tracking": tracking.to_dict(),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            results[symbol] = ist_gewinn
            
        return results
```

#### 🗄️ **Infrastructure Layer - Data Access**

```python
class PostgreSQLSOLLISTTrackingRepository(SOLLISTTrackingRepository):
    """PostgreSQL Implementation für SOLL-IST Tracking"""
    
    def __init__(self, connection_pool):
        self.pool = connection_pool
    
    async def save(self, tracking: SOLLISTTracking) -> None:
        """Speichert SOLL-IST Tracking mit UPSERT"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO soll_ist_gewinn_tracking 
                (datum, symbol, unternehmen, ist_gewinn, 
                 soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (datum, symbol) 
                DO UPDATE SET
                    unternehmen = EXCLUDED.unternehmen,
                    ist_gewinn = EXCLUDED.ist_gewinn,
                    soll_gewinn_1w = EXCLUDED.soll_gewinn_1w,
                    soll_gewinn_1m = EXCLUDED.soll_gewinn_1m,
                    soll_gewinn_3m = EXCLUDED.soll_gewinn_3m,
                    soll_gewinn_12m = EXCLUDED.soll_gewinn_12m
            """, 
            tracking.datum, tracking.symbol, tracking.unternehmen,
            tracking.ist_gewinn, tracking.soll_gewinn_1w, 
            tracking.soll_gewinn_1m, tracking.soll_gewinn_3m, 
            tracking.soll_gewinn_12m)

class YahooFinanceMarketDataRepository(MarketDataRepository):
    """Yahoo Finance Implementation für Market Data"""
    
    def __init__(self):
        self.retry_count = 3
        self.timeout = 10.0
    
    async def get_current_data(self, symbol: str) -> MarketData:
        """Lädt aktuelle Marktdaten von Yahoo Finance"""
        for attempt in range(self.retry_count):
            try:
                ticker = yf.Ticker(symbol)
                
                # Historische Daten für Analyse
                hist = ticker.history(period="5d", interval="1d")
                if hist.empty:
                    raise ValueError(f"No data available for {symbol}")
                
                # Company Info
                info = ticker.info
                company_name = info.get('longName', symbol)
                market_region = self._determine_market_region(symbol)
                
                # Market Data Point erstellen
                latest_data = hist.iloc[-1]
                return MarketData(
                    symbol=symbol,
                    company_name=company_name,
                    market_region=market_region,
                    current_price=Decimal(str(latest_data['Close'])),
                    volume=int(latest_data['Volume']),
                    historical_data=hist.to_dict(),
                    timestamp=datetime.now()
                )
                
            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

class RedisEventPublisher(EventPublisher):
    """Redis Event-Bus Integration"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publiziert Event über Redis Event-Bus (Port 8014)"""
        event = {
            "event_type": event_type,
            "event_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "event_data": event_data,
            "metadata": {
                "service": "unified-profit-engine-enhanced",
                "version": "v6.0"
            },
            "created_at": datetime.now().isoformat()
        }
        
        # Event in Redis Channel publizieren
        await self.redis.publish(f"events:{event_type}", json.dumps(event))
        
        # Event in PostgreSQL Event Store persistieren
        await self._persist_event(event)
```

#### 🌐 **Presentation Layer - FastAPI Integration**

```python
class UnifiedProfitEngineController:
    """REST API Controller für Unified Profit Engine Enhanced"""
    
    def __init__(self, 
                 prediction_use_case: GenerateMultiHorizonPredictionsUseCase,
                 ist_calculation_use_case: CalculateISTPerformanceUseCase):
        self.prediction_use_case = prediction_use_case
        self.ist_calculation_use_case = ist_calculation_use_case
    
    async def generate_multi_horizon_predictions(
        self, 
        request: MultiHorizonPredictionRequest
    ) -> MultiHorizonPredictionResponse:
        """
        POST /api/v1/profit-engine/predictions/multi-horizon
        Generiert SOLL-Gewinn Vorhersagen für alle Horizonte
        """
        try:
            tracking_results = await self.prediction_use_case.execute(
                request.symbols
            )
            
            return MultiHorizonPredictionResponse(
                success=True,
                predictions=tracking_results,
                processed_count=len(tracking_results),
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return MultiHorizonPredictionResponse(
                success=False,
                error=str(e),
                processed_count=0
            )
    
    async def calculate_ist_performance(
        self, 
        request: ISTCalculationRequest
    ) -> ISTCalculationResponse:
        """
        POST /api/v1/profit-engine/ist/calculate
        Berechnet aktuelle IST-Performance
        """
        ist_results = await self.ist_calculation_use_case.execute(
            request.symbols
        )
        
        return ISTCalculationResponse(
            success=True,
            ist_profits=ist_results,
            calculated_count=len(ist_results)
        )

# FastAPI App Setup mit Dependency Injection
app = FastAPI(title="Unified Profit Engine Enhanced v6.0")

@app.on_event("startup")
async def startup_event():
    # Dependency Container Setup
    container = Container()
    
    # Infrastructure
    container.wire(modules=[
        PostgreSQLSOLLISTTrackingRepository,
        YahooFinanceMarketDataRepository,
        RedisEventPublisher
    ])
    
    # Use Cases
    container.wire(modules=[
        GenerateMultiHorizonPredictionsUseCase,
        CalculateISTPerformanceUseCase
    ])
    
    # Controllers
    container.wire(modules=[UnifiedProfitEngineController])
```

---

## 🔄 **Event-Driven Integration Pattern**

### **📡 Event Flow Sequence**

```python
# 1. Externe Trigger (Scheduler/User Request)
async def daily_prediction_workflow():
    """Täglicher Multi-Horizon Prediction Workflow"""
    
    # Market Data Sync Event
    await event_bus.publish("market.data.synchronized", {
        "source": "yahoo_finance",
        "regions": ["US", "EU", "ASIA"], 
        "symbols_count": 220
    })
    
    # Prediction Generation Event
    prediction_results = await unified_profit_engine.generate_predictions(
        symbols=GLOBAL_SYMBOL_DIRECTORY
    )
    
    # SOLL-IST Calculation Event
    ist_results = await unified_profit_engine.calculate_ist_performance(
        symbols=ACTIVE_PORTFOLIO_SYMBOLS
    )
    
    # Portfolio Update Event
    await event_bus.publish("portfolio.state.changed", {
        "total_predictions": len(prediction_results),
        "ist_calculations": len(ist_results),
        "performance_update": True
    })

# 2. Event Handler für Cross-Service Integration
class EventHandlers:
    
    @event_handler("analysis.prediction.generated")
    async def on_prediction_generated(self, event_data):
        """Reagiert auf neue Predictions"""
        # ML Analytics Service benachrichtigen
        await ml_analytics_service.update_model_feedback(event_data)
        
        # Prediction Tracking Service aktualisieren
        await prediction_tracking_service.register_prediction(event_data)
        
        # Frontend Dashboard aktualisieren
        await frontend_service.update_prediction_dashboard(event_data)
    
    @event_handler("profit.calculation.completed")
    async def on_profit_calculated(self, event_data):
        """Reagiert auf IST-Gewinn Berechnungen"""
        # Intelligent Core für Performance-Analyse
        await intelligent_core_service.analyze_performance_gap(event_data)
        
        # Monitoring Service für Alerts
        await monitoring_service.check_performance_thresholds(event_data)
```

---

## 🗄️ **Database Integration Patterns**

### **📊 SOLL-IST Tracking Table - Enhanced**

```sql
-- Enhanced soll_ist_gewinn_tracking table
CREATE TABLE IF NOT EXISTS soll_ist_gewinn_tracking (
    id SERIAL PRIMARY KEY,
    datum DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    unternehmen VARCHAR(255) NOT NULL,
    market_region VARCHAR(50),
    ist_gewinn DECIMAL(12,4),
    soll_gewinn_1w DECIMAL(12,4),
    soll_gewinn_1m DECIMAL(12,4), 
    soll_gewinn_3m DECIMAL(12,4),
    soll_gewinn_12m DECIMAL(12,4),
    
    -- Calculated columns für Performance Analysis
    diff_1w DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_1w) STORED,
    diff_1m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_1m) STORED,
    diff_3m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_3m) STORED,
    diff_12m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_12m) STORED,
    
    -- Metadata
    confidence_1w DECIMAL(5,4),
    confidence_1m DECIMAL(5,4),
    confidence_3m DECIMAL(5,4),
    confidence_12m DECIMAL(5,4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT soll_ist_gewinn_tracking_datum_symbol_unique UNIQUE (datum, symbol)
);

-- Performance-Optimized Indexes
CREATE INDEX idx_soll_ist_symbol_datum ON soll_ist_gewinn_tracking (symbol, datum DESC);
CREATE INDEX idx_soll_ist_datum ON soll_ist_gewinn_tracking (datum DESC);
CREATE INDEX idx_soll_ist_region ON soll_ist_gewinn_tracking (market_region);

-- Trigger für updated_at
CREATE TRIGGER update_soll_ist_tracking_updated_at
    BEFORE UPDATE ON soll_ist_gewinn_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### **🎯 Performance Analysis Views**

```sql
-- Multi-Horizon Performance View
CREATE OR REPLACE VIEW v_multi_horizon_performance AS
SELECT 
    symbol,
    unternehmen,
    market_region,
    datum,
    ist_gewinn,
    
    -- SOLL Values
    soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
    
    -- Performance Differences
    diff_1w, diff_1m, diff_3m, diff_12m,
    
    -- Performance Percentages
    CASE WHEN soll_gewinn_1w != 0 THEN (diff_1w / soll_gewinn_1w) * 100 END as perf_1w_pct,
    CASE WHEN soll_gewinn_1m != 0 THEN (diff_1m / soll_gewinn_1m) * 100 END as perf_1m_pct,
    CASE WHEN soll_gewinn_3m != 0 THEN (diff_3m / soll_gewinn_3m) * 100 END as perf_3m_pct,
    CASE WHEN soll_gewinn_12m != 0 THEN (diff_12m / soll_gewinn_12m) * 100 END as perf_12m_pct,
    
    -- Confidence Metrics
    confidence_1w, confidence_1m, confidence_3m, confidence_12m,
    
    updated_at
FROM soll_ist_gewinn_tracking
WHERE ist_gewinn IS NOT NULL;

-- Best Performing Predictions View
CREATE OR REPLACE VIEW v_best_predictions AS
SELECT 
    symbol,
    unternehmen, 
    datum,
    
    -- Best performing horizon
    CASE 
        WHEN ABS(diff_1w) = LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1W'
        WHEN ABS(diff_1m) = LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1M'
        WHEN ABS(diff_3m) = LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '3M'
        ELSE '12M'
    END as best_horizon,
    
    LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) as best_accuracy,
    
    -- Worst performing horizon
    CASE 
        WHEN ABS(diff_1w) = GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1W'
        WHEN ABS(diff_1m) = GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1M'
        WHEN ABS(diff_3m) = GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '3M'
        ELSE '12M'
    END as worst_horizon,
    
    GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) as worst_accuracy
    
FROM soll_ist_gewinn_tracking
WHERE ist_gewinn IS NOT NULL
  AND (diff_1w IS NOT NULL OR diff_1m IS NOT NULL OR diff_3m IS NOT NULL OR diff_12m IS NOT NULL);
```

---

## 🚀 **Deployment Integration**

### **🔧 systemd Service Enhanced**

```ini
[Unit]
Description=Unified Profit Engine Enhanced v6.0 - Clean Architecture
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service
Requires=event-bus-service.service

[Service]
Type=exec
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/home/mdoehler/aktienanalyse-ökosystem/services/unified-profit-engine
Environment=PATH=/home/mdoehler/aktienanalyse-venv/bin
Environment=POSTGRES_URL=postgresql://aktienanalyse:@localhost/aktienanalyse_events?sslmode=disable
Environment=REDIS_URL=redis://localhost:6379/0
Environment=SERVICE_PORT=8025
Environment=LOG_LEVEL=INFO
ExecStart=/home/mdoehler/aktienanalyse-venv/bin/python unified_profit_engine_enhanced_v6.0.0_20250824.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=unified-profit-engine-enhanced

# Health Check
ExecStartPost=/bin/sleep 10
ExecStartPost=/bin/curl -f http://localhost:8025/api/v1/health || /bin/systemctl stop %n

[Install]
WantedBy=multi-user.target
```

---

---

## 📊 **Data Processing Service Enhanced - Port 8017 - Timeframe Aggregation Engine v7.1**

### 🏛️ **Clean Architecture Layers für Aggregation**

#### **Domain Layer - Aggregation Core Business Logic**

```python
# Domain Entities & Value Objects
from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
import numpy as np

@dataclass
class TimeframeConfiguration:
    """Value Object für Zeitintervall-Konfiguration"""
    interval_type: str      # "minutes", "hours", "days", "weeks", "months"
    interval_value: int     # 1, 5, 15, 30, 60, etc.
    display_name: str       # "1M", "1W", "3M", "12M"
    horizon_days: int       # Berechnete Tage bis Zieldatum
    
    def __post_init__(self):
        valid_types = ["minutes", "hours", "days", "weeks", "months"]
        if self.interval_type not in valid_types:
            raise ValueError(f"Invalid interval_type. Must be one of: {valid_types}")
        if self.interval_value <= 0:
            raise ValueError("interval_value must be positive")
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
    
    def calculate_target_date(self, base_date: date = None) -> date:
        """Berechnet Zieldatum basierend auf Konfiguration"""
        base = base_date or date.today()
        return base + timedelta(days=self.horizon_days)

@dataclass
class QualityMetrics:
    """Value Object für Quality Assessment"""
    data_quality_score: float          # 0.0 - 1.0
    prediction_quality_score: float    # 0.0 - 1.0
    overall_quality_score: float       # 0.0 - 1.0
    data_completeness: float           # 0.0 - 1.0
    data_consistency: float            # 0.0 - 1.0
    confidence_distribution: float     # Variance of individual confidences
    outlier_count: int                 # Number of outliers removed
    quality_threshold_met: bool        # Whether quality standards are met
    
    def __post_init__(self):
        # Validate score ranges
        scores = [self.data_quality_score, self.prediction_quality_score, 
                 self.overall_quality_score, self.data_completeness, self.data_consistency]
        for score in scores:
            if not (0.0 <= score <= 1.0):
                raise ValueError("All quality scores must be between 0.0 and 1.0")

@dataclass
class AggregatedPrediction:
    """Core Domain Entity für aggregierte Vorhersagen"""
    
    # Identity & Context
    id: UUID
    symbol: str
    company_name: str
    market_region: str
    
    # Temporal Configuration
    timeframe_config: TimeframeConfiguration
    aggregation_date: date
    target_date: date
    
    # Aggregated Values
    predicted_value: Decimal        # Hauptvorhersage
    confidence_score: float         # 0.0 - 1.0 Confidence
    quality_metrics: QualityMetrics # Quality Assessment
    
    # Statistical Metadata
    data_points_count: int         # Anzahl aggregierter Predictions
    variance: float                # Statistische Varianz
    standard_deviation: float      # Standardabweichung
    
    # Processing Metadata  
    aggregation_strategy: str      # "weighted_average", "median", "ensemble"
    created_at: datetime
    last_updated: datetime
    
    def __post_init__(self):
        self._validate_confidence_score()
        self._validate_data_points_count()
        
    def _validate_confidence_score(self):
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
    
    def _validate_data_points_count(self):
        if self.data_points_count <= 0:
            raise ValueError("Data points count must be positive")
        
    # Domain Behavior
    def is_prediction_expired(self) -> bool:
        return datetime.now().date() > self.target_date
        
    def calculate_accuracy_against_actual(self, actual_value: Decimal) -> float:
        """Berechnet Genauigkeit gegen tatsächlichen Wert"""
        if self.predicted_value == 0:
            return 0.0
        diff = abs(actual_value - self.predicted_value)
        return float(1.0 - (diff / abs(self.predicted_value)))
    
    def is_high_quality(self, threshold: float = 0.8) -> bool:
        """Prüft ob Prediction hohe Qualität hat"""
        return self.quality_metrics.overall_quality_score >= threshold

# Domain Services
class TimeframeAggregationService:
    """
    CORE DOMAIN SERVICE für Aggregations-Business-Logic
    
    SOLID Principles Implementation:
    - Single Responsibility: Nur Aggregation Logic
    - Open/Closed: Erweiterbar durch Strategy Pattern
    - Liskov Substitution: Strategy Interface compliance
    - Interface Segregation: Separate Validation Service
    - Dependency Inversion: Abhängig von Interfaces
    """
    
    def __init__(self, 
                 validation_service: 'MathematicalValidationService'):
        self._validation_service = validation_service
        self._strategies = self._initialize_strategies()
        self.min_required_predictions = 3
    
    def calculate_aggregated_prediction(
        self, 
        raw_predictions: List[Dict],
        timeframe_config: TimeframeConfiguration,
        strategy_type: str = "ensemble",
        strategy_parameters: Dict = None
    ) -> AggregatedPrediction:
        """
        MAIN BUSINESS LOGIC: Aggregation Calculation
        
        Process Flow:
        1. Data Validation & Cleaning
        2. Strategy Pattern Application
        3. Quality Metrics Calculation
        4. Domain Entity Creation
        """
        
        if strategy_parameters is None:
            strategy_parameters = {}
        
        # Step 1: Comprehensive Data Validation
        validated_predictions = self._validation_service.validate_prediction_data(
            raw_predictions
        )
        
        if len(validated_predictions) == 0:
            raise InsufficientDataError("No valid predictions available for aggregation")
        
        # Step 2: Strategy Pattern Execution
        aggregation_func = self._get_strategy_function(strategy_type)
        statistical_result = aggregation_func(validated_predictions, strategy_parameters)
        
        # Step 3: Quality Assessment
        quality_metrics = self._calculate_quality_metrics(
            raw_predictions=raw_predictions,
            validated_predictions=validated_predictions,
            statistical_result=statistical_result,
            strategy_type=strategy_type
        )
        
        # Step 4: Domain Entity Construction
        return self._build_aggregated_prediction(
            validated_predictions=validated_predictions,
            timeframe_config=timeframe_config,
            statistical_result=statistical_result,
            quality_metrics=quality_metrics,
            strategy_type=strategy_type
        )
    
    def _get_strategy_function(self, strategy_type: str):
        """Strategy Pattern: Dynamic strategy selection"""
        if strategy_type not in self._strategies:
            raise UnsupportedStrategyError(f"Strategy not supported: {strategy_type}")
        return self._strategies[strategy_type]
    
    def _initialize_strategies(self) -> Dict[str, callable]:
        """Initialize available aggregation strategies"""
        return {
            "weighted_average": self._weighted_average_strategy,
            "median": self._median_strategy,
            "ensemble": self._ensemble_strategy
        }
    
    def _weighted_average_strategy(self, predictions: List[Dict], parameters: Dict) -> Dict:
        """Weighted Average Aggregation Strategy"""
        weights = [p.get("confidence", 1.0) * parameters.get("base_weight", 1.0) 
                  for p in predictions]
        values = [float(p["predicted_value"]) for p in predictions]
        
        total_weight = sum(weights)
        if total_weight == 0:
            raise ValueError("Total weight cannot be zero")
            
        weighted_value = sum(w * v for w, v in zip(weights, values)) / total_weight
        
        return {
            "predicted_value": Decimal(str(round(weighted_value, 6))),
            "variance": float(np.var(values)),
            "standard_deviation": float(np.std(values)),
            "method_details": {
                "strategy": "weighted_average",
                "total_weight": total_weight,
                "weight_distribution": weights
            }
        }
    
    def _median_strategy(self, predictions: List[Dict], parameters: Dict) -> Dict:
        """Median-based Aggregation Strategy"""
        values = [float(p["predicted_value"]) for p in predictions]
        median_value = float(np.median(values))
        
        return {
            "predicted_value": Decimal(str(round(median_value, 6))),
            "variance": float(np.var(values)),
            "standard_deviation": float(np.std(values)),
            "method_details": {
                "strategy": "median",
                "quartiles": {
                    "q1": float(np.percentile(values, 25)),
                    "q2": median_value,
                    "q3": float(np.percentile(values, 75))
                }
            }
        }
    
    def _ensemble_strategy(self, predictions: List[Dict], parameters: Dict) -> Dict:
        """Advanced Ensemble Aggregation Strategy"""
        # Combine weighted average (70%) and median (30%) for robustness
        weighted_result = self._weighted_average_strategy(predictions, parameters)
        median_result = self._median_strategy(predictions, parameters)
        
        ensemble_weight = parameters.get("weighted_avg_weight", 0.7)
        median_weight = 1.0 - ensemble_weight
        
        ensemble_value = (
            float(weighted_result["predicted_value"]) * ensemble_weight +
            float(median_result["predicted_value"]) * median_weight
        )
        
        values = [float(p["predicted_value"]) for p in predictions]
        
        return {
            "predicted_value": Decimal(str(round(ensemble_value, 6))),
            "variance": float(np.var(values)),
            "standard_deviation": float(np.std(values)),
            "method_details": {
                "strategy": "ensemble",
                "ensemble_composition": {
                    "weighted_average_contribution": ensemble_weight,
                    "median_contribution": median_weight
                },
                "component_results": {
                    "weighted_average": float(weighted_result["predicted_value"]),
                    "median": float(median_result["predicted_value"])
                }
            }
        }

class MathematicalValidationService:
    """
    DOMAIN SERVICE für mathematische Validierung
    Implements advanced statistical validation algorithms
    """
    
    def __init__(self):
        self.min_required_predictions = 3
        self.outlier_method = "iqr"  # IQR-based outlier detection
        self.quality_threshold = 0.6
    
    def validate_prediction_data(self, predictions: List[Dict]) -> List[Dict]:
        """
        Comprehensive Data Validation Pipeline:
        1. Structural Validation
        2. Statistical Outlier Detection (IQR Method)
        3. Consistency Checks
        4. Quality Thresholding
        """
        
        # Phase 1: Basic Structure Validation
        structurally_valid = self._validate_structure(predictions)
        
        # Phase 2: Statistical Outlier Removal
        outlier_cleaned = self._remove_statistical_outliers(structurally_valid)
        
        # Phase 3: Data Consistency Validation
        consistency_validated = self._validate_consistency(outlier_cleaned)
        
        # Phase 4: Quality Threshold Application
        quality_filtered = self._apply_quality_thresholds(consistency_validated)
        
        if len(quality_filtered) < self.min_required_predictions:
            raise InsufficientQualityDataError(
                f"Only {len(quality_filtered)} valid predictions, need minimum {self.min_required_predictions}"
            )
        
        return quality_filtered
    
    def _validate_structure(self, predictions: List[Dict]) -> List[Dict]:
        """Validates basic structure and required fields"""
        valid_predictions = []
        required_fields = ["predicted_value", "confidence", "created_at"]
        
        for pred in predictions:
            if all(field in pred for field in required_fields):
                try:
                    # Validate data types
                    float(pred["predicted_value"])
                    float(pred["confidence"])
                    valid_predictions.append(pred)
                except (ValueError, TypeError):
                    continue  # Skip invalid predictions
        
        return valid_predictions
    
    def _remove_statistical_outliers(self, predictions: List[Dict]) -> List[Dict]:
        """
        IQR-based Outlier Detection Algorithm
        
        Mathematical Formula:
        - Q1 = 25th percentile
        - Q3 = 75th percentile
        - IQR = Q3 - Q1
        - Lower Bound = Q1 - 1.5 * IQR
        - Upper Bound = Q3 + 1.5 * IQR
        - Outlier: value < Lower Bound OR value > Upper Bound
        """
        if len(predictions) < 4:  # IQR needs minimum 4 points
            return predictions
            
        values = [float(p["predicted_value"]) for p in predictions]
        
        # Calculate IQR bounds
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Filter outliers
        filtered_predictions = []
        
        for pred in predictions:
            value = float(pred["predicted_value"])
            if lower_bound <= value <= upper_bound:
                filtered_predictions.append(pred)
        
        # Ensure minimum data retention
        if len(filtered_predictions) < self.min_required_predictions:
            # Sort by distance to median and retain best predictions
            median_value = np.median(values)
            predictions_with_distance = [
                (pred, abs(float(pred["predicted_value"]) - median_value))
                for pred in predictions
            ]
            predictions_with_distance.sort(key=lambda x: x[1])
            filtered_predictions = [
                pred for pred, _ in predictions_with_distance[:self.min_required_predictions]
            ]
        
        return filtered_predictions
    
    def _validate_consistency(self, predictions: List[Dict]) -> List[Dict]:
        """Validates temporal and logical consistency"""
        # Remove predictions with future creation dates
        now = datetime.now()
        consistent_predictions = [
            p for p in predictions 
            if datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) <= now
        ]
        
        return consistent_predictions
    
    def _apply_quality_thresholds(self, predictions: List[Dict]) -> List[Dict]:
        """Applies minimum quality thresholds"""
        return [
            p for p in predictions 
            if p.get("confidence", 0.0) >= self.quality_threshold
        ]
    
    def calculate_aggregation_confidence(
        self, 
        predictions: List[Dict],
        aggregation_result: Dict
    ) -> float:
        """
        Advanced Confidence Calculation Algorithm
        
        Factors:
        1. Individual prediction confidences
        2. Prediction agreement (low std dev = high agreement)
        3. Data completeness ratio
        4. Mathematical validity
        """
        
        # Factor 1: Average Individual Confidences
        individual_confidences = [p.get("confidence", 0.5) for p in predictions]
        avg_individual_confidence = np.mean(individual_confidences)
        
        # Factor 2: Prediction Agreement Score
        predicted_values = [float(p["predicted_value"]) for p in predictions]
        if len(predicted_values) > 1:
            std_dev = np.std(predicted_values)
            mean_value = abs(np.mean(predicted_values))
            agreement_score = 1.0 - min(1.0, std_dev / (mean_value + 1e-6))
        else:
            agreement_score = 1.0
        
        # Factor 3: Data Completeness Score
        completeness_score = min(1.0, len(predictions) / 10.0)  # Normalized to 10 predictions
        
        # Factor 4: Mathematical Validity
        predicted_value = aggregation_result.get("predicted_value", 0.0)
        math_validity = 0.0 if (np.isnan(float(predicted_value)) or np.isinf(float(predicted_value))) else 1.0
        
        # Weighted Combination
        confidence = (
            avg_individual_confidence * 0.35 +  # Individual confidences
            agreement_score * 0.25 +            # Prediction agreement  
            completeness_score * 0.20 +         # Data completeness
            math_validity * 0.20                # Mathematical validity
        )
        
        return max(0.0, min(1.0, confidence))

# Custom Domain Exceptions
class AggregationDomainError(Exception):
    """Base exception for aggregation domain errors"""
    pass

class InsufficientDataError(AggregationDomainError):
    """Raised when insufficient data is available for aggregation"""
    pass

class InsufficientQualityDataError(AggregationDomainError):
    """Raised when data doesn't meet quality requirements"""
    pass

class UnsupportedStrategyError(AggregationDomainError):
    """Raised when unsupported aggregation strategy is requested"""
    pass
```

#### **Application Layer - Use Cases & DTOs**

```python
# Application DTOs
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID

class AggregationRequestDTO(BaseModel):
    """DTO für Aggregation Requests"""
    request_id: str = Field(..., description="Eindeutige Request-ID")
    symbols: List[str] = Field(..., min_items=1, max_items=50, description="Zu aggregierende Symbole")
    timeframe_type: str = Field(..., description="Zeitintervall-Typ")
    timeframe_value: int = Field(..., ge=1, le=365, description="Zeitintervall-Wert")
    timeframe_display_name: str = Field(..., description="Anzeigename für Zeitintervall")
    timeframe_hours: int = Field(..., ge=1, description="Zeitintervall in Stunden")
    aggregation_strategy: str = Field("ensemble", description="Aggregationsstrategie")
    strategy_parameters: Optional[Dict[str, float]] = Field(default_factory=dict)
    quality_threshold: float = Field(0.8, ge=0.0, le=1.0)
    max_predictions_per_symbol: int = Field(50, ge=1, le=1000)
    min_prediction_quality: float = Field(0.6, ge=0.0, le=1.0)
    cache_ttl_seconds: int = Field(3600, ge=60, le=86400)
    force_recalculation: bool = Field(False)
    
    @validator("timeframe_type")
    def validate_timeframe_type(cls, v):
        valid_types = ["minutes", "hours", "days", "weeks", "months"]
        if v not in valid_types:
            raise ValueError(f"timeframe_type must be one of: {valid_types}")
        return v
    
    @validator("aggregation_strategy")
    def validate_strategy(cls, v):
        valid_strategies = ["weighted_average", "median", "ensemble"]
        if v not in valid_strategies:
            raise ValueError(f"aggregation_strategy must be one of: {valid_strategies}")
        return v

class AggregatedPredictionDTO(BaseModel):
    """DTO für Aggregated Predictions Response"""
    id: UUID
    symbol: str
    company_name: str
    market_region: str
    timeframe_display: str
    predicted_value: float
    confidence_score: float
    quality_score: float
    target_date: date
    data_points_count: int
    aggregation_strategy: str
    created_at: datetime
    
    @classmethod
    def from_entity(cls, entity: AggregatedPrediction) -> 'AggregatedPredictionDTO':
        """Converts Domain Entity to DTO"""
        return cls(
            id=entity.id,
            symbol=entity.symbol,
            company_name=entity.company_name,
            market_region=entity.market_region,
            timeframe_display=entity.timeframe_config.display_name,
            predicted_value=float(entity.predicted_value),
            confidence_score=entity.confidence_score,
            quality_score=entity.quality_metrics.overall_quality_score,
            target_date=entity.target_date,
            data_points_count=entity.data_points_count,
            aggregation_strategy=entity.aggregation_strategy,
            created_at=entity.created_at
        )

class QualityReportDTO(BaseModel):
    """DTO für Quality Assessment Reports"""
    aggregation_id: UUID
    overall_quality_score: float
    quality_status: str
    validation_passed: bool
    quality_dimensions: Dict[str, float]
    issues_found: int
    recommendations: List[str]

# Application Use Cases
class CalculateAggregatedPredictionsUseCase:
    """
    PRIMARY USE CASE für Aggregation Workflow
    
    Responsibilities:
    1. Request Validation & Processing
    2. Domain Service Orchestration  
    3. Repository & Cache Management
    4. Event Publishing
    5. Error Handling & Recovery
    """
    
    def __init__(
        self,
        # Domain Services (Injected Dependencies)
        aggregation_service: TimeframeAggregationService,
        
        # Repository Interfaces (DIP Compliance)
        aggregation_repository: 'AggregationRepositoryInterface',
        prediction_repository: 'PredictionRepositoryInterface',
        
        # Infrastructure Services (Interface-based)
        cache_service: 'CacheServiceInterface',
        event_publisher: 'EventPublisherInterface',
        performance_monitor: 'PerformanceMonitorInterface'
    ):
        # Dependency Injection - All dependencies are interfaces
        self._aggregation_service = aggregation_service
        self._aggregation_repository = aggregation_repository
        self._prediction_repository = prediction_repository
        self._cache_service = cache_service
        self._event_publisher = event_publisher
        self._performance_monitor = performance_monitor
    
    async def execute(self, request: AggregationRequestDTO) -> List[AggregatedPredictionDTO]:
        """
        MAIN EXECUTION FLOW for Aggregated Predictions
        
        Performance Targets:
        - Response Time: < 300ms (1M), < 150ms (1W)
        - Cache Hit Rate: > 85%
        - Error Rate: < 1%
        - Throughput: 50+ concurrent requests
        """
        
        # Start performance monitoring
        execution_context = await self._performance_monitor.start_execution(
            operation="calculate_aggregated_predictions",
            request_id=request.request_id
        )
        
        try:
            # Phase 1: Request Validation
            self._validate_request(request)
            
            # Phase 2: Cache Strategy (Performance Optimization)
            cache_key = self._build_deterministic_cache_key(request)
            cached_result = await self._attempt_cache_retrieval(cache_key, request)
            
            if cached_result:
                await execution_context.record_cache_hit()
                return cached_result
            
            # Phase 3: Data Acquisition & Processing
            processing_results = await self._process_symbols_batch(request)
            
            # Phase 4: Result Caching & Event Publishing
            if processing_results:
                await self._cache_and_publish_results(cache_key, processing_results, request)
            
            # Phase 5: Performance Metrics Recording
            await execution_context.complete_successfully(
                symbols_processed=len(processing_results),
                cache_miss=True
            )
            
            return processing_results
            
        except Exception as e:
            # Comprehensive Error Handling
            await execution_context.complete_with_error(error=str(e))
            await self._handle_execution_error(e, request)
            raise
    
    async def _process_symbols_batch(self, request: AggregationRequestDTO) -> List[AggregatedPredictionDTO]:
        """
        Batch processing mit Error Isolation per Symbol
        """
        results = []
        failed_symbols = []
        
        for symbol in request.symbols:
            try:
                # Get raw prediction data
                raw_predictions = await self._prediction_repository.get_predictions_for_aggregation(
                    symbol=symbol,
                    timeframe_hours=request.timeframe_hours,
                    quality_threshold=request.min_prediction_quality,
                    limit=request.max_predictions_per_symbol
                )
                
                if not raw_predictions:
                    failed_symbols.append(symbol)
                    continue
                
                # Domain Layer Processing
                aggregated_prediction = await self._execute_domain_aggregation(
                    symbol=symbol,
                    raw_predictions=raw_predictions,
                    request=request
                )
                
                # Repository Persistence
                await self._aggregation_repository.save(aggregated_prediction)
                
                # DTO Conversion
                dto = AggregatedPredictionDTO.from_entity(aggregated_prediction)
                results.append(dto)
                
                # Individual Success Event
                await self._event_publisher.publish(
                    "aggregation.calculation.completed",
                    self._build_completion_event_data(symbol, aggregated_prediction)
                )
                
            except Exception as symbol_error:
                failed_symbols.append(symbol)
                await self._event_publisher.publish(
                    "aggregation.calculation.symbol_failed", 
                    {
                        "symbol": symbol,
                        "error": str(symbol_error),
                        "request_id": request.request_id
                    }
                )
                # Continue processing other symbols
                continue
        
        # Batch Summary Event
        await self._event_publisher.publish(
            "aggregation.batch.processed",
            {
                "request_id": request.request_id,
                "successful_symbols": len(results),
                "failed_symbols": len(failed_symbols),
                "success_rate": len(results) / len(request.symbols) if request.symbols else 0.0
            }
        )
        
        return results
    
    async def _execute_domain_aggregation(
        self,
        symbol: str,
        raw_predictions: List[Dict],
        request: AggregationRequestDTO
    ) -> AggregatedPrediction:
        """Execute domain aggregation logic"""
        
        # Create timeframe configuration
        timeframe_config = TimeframeConfiguration(
            interval_type=request.timeframe_type,
            interval_value=request.timeframe_value,
            display_name=request.timeframe_display_name,
            horizon_days=request.timeframe_hours // 24
        )
        
        # Execute domain service
        return self._aggregation_service.calculate_aggregated_prediction(
            raw_predictions=raw_predictions,
            timeframe_config=timeframe_config,
            strategy_type=request.aggregation_strategy,
            strategy_parameters=request.strategy_parameters
        )

# Repository Interfaces (Dependency Inversion Principle)
from abc import ABC, abstractmethod

class AggregationRepositoryInterface(ABC):
    """Repository interface for aggregated predictions"""
    
    @abstractmethod
    async def save(self, aggregation: AggregatedPrediction) -> None:
        pass
    
    @abstractmethod
    async def get_by_id(self, aggregation_id: UUID) -> Optional[AggregatedPrediction]:
        pass
    
    @abstractmethod
    async def get_by_symbol_and_timeframe(
        self, 
        symbol: str, 
        timeframe: str,
        limit: int = 10
    ) -> List[AggregatedPrediction]:
        pass

class PredictionRepositoryInterface(ABC):
    """Repository interface for raw predictions"""
    
    @abstractmethod
    async def get_predictions_for_aggregation(
        self,
        symbol: str,
        timeframe_hours: int,
        quality_threshold: float,
        limit: int
    ) -> List[Dict]:
        pass

# Service Interfaces
class CacheServiceInterface(ABC):
    """Cache service interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> None:
        pass

class EventPublisherInterface(ABC):
    """Event publisher interface"""
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        pass
```

---

*Low-Level Design - Clean Architecture Integration v7.1*  
*Event-Driven Trading Intelligence System - Enhanced Implementation Details with Timeframe Aggregation*  
*Letzte Aktualisierung: 27. August 2025*