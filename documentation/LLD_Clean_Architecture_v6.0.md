# 🏗️ Low-Level Design (LLD) - Clean Architecture Integration v6.0

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

*Low-Level Design - Clean Architecture Integration v6.0*  
*Event-Driven Trading Intelligence System - Enhanced Implementation Details*  
*Letzte Aktualisierung: 24. August 2025*