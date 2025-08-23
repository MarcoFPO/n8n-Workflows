# 📡 Kommunikationspfade

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 🌐 **API-Endpoints & Kommunikationsschnittstellen**

---

## 🚌 **Event Bus Communication (Port 8014)**

### 📊 **Event-Driven Architecture Overview**
```
┌─────────────────────────────────────────────────────────────────┐
│                    🚌 Redis Event Bus (8014)                   │
│              Central Event Communication Hub                   │
└─┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────┬──┘
  │      │      │      │      │      │      │      │      │    │
  │ Pub  │ Pub  │ Sub  │ Sub  │ Sub  │ Sub  │ Sub  │ Sub  │Sub │Sub
  │      │      │      │      │      │      │      │      │    │
┌─▼──┐ ┌▼───┐ ┌▼───┐ ┌▼────┐ ┌▼────┐ ┌▼───┐ ┌▼───┐ ┌▼───┐ ┌▼─┐ ┌▼──┐
│Core│ │Data│ │Broker│Diag │ │Mon │ │Pred│ │ML  │ │Cap │ │PE│ │UI │
│8001│ │8017│ │8012 │8013 │ │8015│ │8018│ │8021│ │8011│ │8025│8080│
└────┘ └────┘ └─────┘ └─────┘ └────┘ └────┘ └────┘ └────┘ └───┘ └────┘
```

### 🔄 **Core Event Types & Channels**

#### 📋 **Event Channel Structure**
```python
# Redis Pub/Sub Channel Pattern: events.{event_type}

EVENT_CHANNELS = {
    # 1. Stock Analysis Events
    "events.analysis.state.changed": {
        "publishers": ["intelligent-core-service"],
        "subscribers": ["prediction-tracking-service", "ml-analytics-service", "frontend-service"],
        "frequency": "Real-time (on analysis completion)",
        "payload_example": {
            "stock_symbol": "AAPL",
            "score": 18.5,
            "confidence": 0.85,
            "risk_category": "LOW",
            "timestamp": "2025-08-23T10:30:00Z"
        }
    },
    
    # 2. Portfolio Performance Events
    "events.portfolio.state.changed": {
        "publishers": ["broker-gateway-service", "unified-profit-engine"],
        "subscribers": ["intelligent-core-service", "monitoring-service", "frontend-service"],
        "frequency": "Real-time (on portfolio update)",
        "payload_example": {
            "total_value": 125430.50,
            "performance_pct": 12.8,
            "positions": 15,
            "unrealized_pnl": 8430.50,
            "timestamp": "2025-08-23T10:30:00Z"
        }
    },
    
    # 3. Trading Activity Events
    "events.trading.state.changed": {
        "publishers": ["broker-gateway-service"],
        "subscribers": ["intelligent-core-service", "unified-profit-engine", "prediction-tracking-service"],
        "frequency": "Real-time (on order execution)",
        "payload_example": {
            "symbol": "NVDA",
            "order_type": "BUY",
            "quantity": 10.0,
            "price": 445.30,
            "status": "EXECUTED",
            "broker": "bitpanda"
        }
    },
    
    # 4. Cross-System Intelligence Events
    "events.intelligence.triggered": {
        "publishers": ["intelligent-core-service"],
        "subscribers": ["data-processing-service", "ml-analytics-service", "frontend-service"],
        "frequency": "On-demand (pattern detection)",
        "payload_example": {
            "intelligence_type": "correlation_detected",
            "correlation_strength": 0.78,
            "recommendation": "NVDA outperforms worst position",
            "confidence": 0.92
        }
    },
    
    # 5. Data Synchronization Events
    "events.data.synchronized": {
        "publishers": ["data-processing-service", "marketcap-service", "broker-gateway-service"],
        "subscribers": ["intelligent-core-service", "monitoring-service"],
        "frequency": "Scheduled + Real-time",
        "payload_example": {
            "data_source": "alpha_vantage",
            "symbols_updated": ["AAPL", "GOOGL", "MSFT"],
            "update_type": "market_data",
            "records_processed": 150
        }
    },
    
    # 6. System Alert Events
    "events.system.alert.raised": {
        "publishers": ["monitoring-service", "diagnostic-service"],
        "subscribers": ["intelligent-core-service", "frontend-service"],
        "frequency": "Threshold-based",
        "payload_example": {
            "alert_type": "high_cpu_usage",
            "service_name": "ml-analytics-service",
            "severity": "WARNING",
            "cpu_usage_pct": 85.5,
            "threshold": 80.0
        }
    },
    
    # 7. User Interaction Events
    "events.user.interaction.logged": {
        "publishers": ["frontend-service"],
        "subscribers": ["intelligent-core-service", "monitoring-service"],
        "frequency": "User-driven",
        "payload_example": {
            "action": "csv_export_requested",
            "user_id": "system",
            "parameters": {"filter": "last_7_days"},
            "session_id": "sess_12345"
        }
    },
    
    # 8. Configuration Update Events
    "events.config.updated": {
        "publishers": ["ALL_SERVICES"],
        "subscribers": ["ALL_SERVICES"],
        "frequency": "Administrative",
        "payload_example": {
            "config_section": "ml_models",
            "updated_keys": ["lstm_weights", "ensemble_threshold"],
            "updated_by": "automated_trainer"
        }
    }
}
```

---

## 🔌 **HTTP API Endpoints**

### 🧠 **Intelligent Core Service (Port 8001)**

#### 📊 **Stock Analysis APIs**
```python
# Base URL: http://10.1.1.174:8001

GET /health
# Response: {"status": "healthy", "uptime": 3600, "version": "1.1.0"}

POST /analyze/stock
# Request Body:
{
    "symbol": "AAPL",
    "analysis_type": "comprehensive",
    "include_predictions": true
}
# Response:
{
    "symbol": "AAPL",
    "score": 18.5,
    "confidence": 0.85,
    "risk_category": "LOW",
    "analysis_details": {
        "technical_score": 19.2,
        "fundamental_score": 17.8,
        "sentiment_score": 18.5
    },
    "predictions": {
        "7d": {"price": 185.50, "probability_up": 0.72},
        "30d": {"price": 192.30, "probability_up": 0.68}
    }
}

GET /analysis/history/{symbol}
# Query Parameters: ?days=30&limit=100
# Response: Historical analysis results

POST /intelligence/correlations
# Request Body:
{
    "symbols": ["AAPL", "GOOGL", "MSFT"],
    "timeframe": "30d"
}
# Response: Cross-asset correlation matrix

GET /performance/tracking
# Response: SOLL-IST performance comparison data
```

### 📈 **Data Processing Service (Port 8017)**

#### 📄 **CSV Processing APIs**
```python
# Base URL: http://10.1.1.174:8017

GET /health
# Response: {"status": "healthy", "csv_processor": "active"}

POST /csv/import
# Content-Type: multipart/form-data
# File: 5-column CSV format (Symbol, Score, Confidence, Risk, LastUpdate)
# Response:
{
    "status": "success",
    "records_processed": 150,
    "validation_errors": [],
    "processing_time_ms": 1250
}

GET /csv/export
# Query Parameters: ?format=csv&filter=last_30_days&symbols=AAPL,GOOGL
# Response: CSV file download (StreamingResponse)

POST /csv/validate
# Request Body: CSV data for validation
# Response: Validation results with errors/warnings

GET /data/sync/status
# Response: Current data synchronization status
```

### 🤖 **ML Analytics Service (Port 8021)**

#### 🔮 **ML Prediction APIs**
```python
# Base URL: http://10.1.1.174:8021

GET /docs
# Response: Swagger/OpenAPI documentation (20+ endpoints)

POST /predict/multi-horizon
# Request Body:
{
    "symbol": "AAPL",
    "horizons": [7, 30, 150, 365],
    "models": ["ensemble", "lstm", "xgboost"]
}
# Response:
{
    "symbol": "AAPL",
    "predictions": {
        "7d": {
            "predicted_price": 185.50,
            "confidence_interval": [180.20, 190.80],
            "probability_up": 0.72,
            "ensemble_confidence": 0.85
        },
        "30d": {...},
        "150d": {...},
        "365d": {...}
    },
    "model_versions": {
        "ensemble": "1.0.0",
        "lstm": "1.2.1",
        "xgboost": "1.1.0"
    }
}

POST /models/train
# Request Body:
{
    "model_type": "lstm",
    "horizon": 30,
    "training_config": {
        "epochs": 100,
        "batch_size": 32
    }
}
# Response: Training job status and results

GET /models/performance
# Response: Current model performance metrics

POST /models/evaluate
# Request Body: Model evaluation parameters
# Response: Comprehensive model evaluation results

GET /predictions/history/{symbol}
# Response: Historical predictions with accuracy tracking
```

### 📡 **Broker Gateway Service (Port 8012)**

#### 💱 **Trading APIs**
```python
# Base URL: http://10.1.1.174:8012

GET /health
# Response: {"status": "healthy", "broker_connections": ["bitpanda"]}

GET /portfolio/summary
# Response:
{
    "total_value": 125430.50,
    "positions": [
        {
            "symbol": "AAPL",
            "quantity": 50.0,
            "current_price": 185.20,
            "unrealized_pnl": 1250.30
        }
    ],
    "performance": {
        "daily_pnl": 430.50,
        "total_return_pct": 12.8
    }
}

POST /orders/create
# Request Body:
{
    "symbol": "NVDA",
    "order_type": "BUY",
    "quantity": 10.0,
    "order_kind": "MARKET"
}
# Response: Order confirmation with order_id

GET /orders/status/{order_id}
# Response: Current order status and execution details

GET /market-data/{symbol}
# Response: Real-time market data from multiple sources

POST /sync/portfolio
# Response: Portfolio synchronization status
```

### 🔍 **Monitoring Service (Port 8015)**

#### 🏥 **System Health APIs**
```python
# Base URL: http://10.1.1.174:8015

GET /health
# Response: {"status": "healthy", "monitoring": "active"}

GET /system/status
# Response:
{
    "system_health": "HEALTHY",
    "services": {
        "intelligent-core-service": {
            "status": "UP",
            "response_time_ms": 120,
            "memory_usage_mb": 185,
            "cpu_usage_pct": 15.2
        },
        "ml-analytics-service": {...},
        "broker-gateway-service": {...}
    },
    "overall_performance": {
        "avg_response_time_ms": 145,
        "event_processing_rate": 950,
        "system_uptime_hours": 72.5
    }
}

GET /metrics/performance
# Response: Detailed performance metrics over time

GET /alerts/active
# Response: Current active system alerts

POST /alerts/acknowledge/{alert_id}
# Response: Alert acknowledgment confirmation

GET /metrics/events
# Response: Event processing statistics
```

### 🎯 **Prediction Tracking Service (Port 8018)**

#### 📊 **SOLL-IST Analysis APIs**
```python
# Base URL: http://10.1.1.174:8018

GET /health
# Response: {"status": "healthy", "tracking": "active"}

GET /predictions/accuracy
# Query Parameters: ?symbol=AAPL&horizon=30&days=90
# Response:
{
    "symbol": "AAPL",
    "horizon_days": 30,
    "accuracy_metrics": {
        "mape": 8.5,  # Mean Absolute Percentage Error
        "rmse": 12.3,  # Root Mean Square Error
        "directional_accuracy": 0.72  # Correct direction predictions
    },
    "soll_ist_comparison": [
        {
            "prediction_date": "2025-07-24",
            "predicted_price": 180.50,
            "actual_price": 185.20,
            "error_pct": 2.6
        }
    ]
}

GET /models/performance-tracking
# Response: Model performance tracking over time

POST /validate/prediction
# Request Body: Prediction validation request
# Response: Validation results and feedback for model improvement
```

### 📊 **MarketCap Service (Port 8011)**

#### 🏢 **Market Data APIs**
```python
# Base URL: http://10.1.1.174:8011

GET /health
# Response: {"status": "healthy", "data_providers": ["alpha_vantage", "yahoo"]}

GET /marketcap/{symbol}
# Response:
{
    "symbol": "AAPL",
    "market_cap": 2850000000000,
    "shares_outstanding": 15400000000,
    "current_price": 185.20,
    "last_updated": "2025-08-23T10:30:00Z"
}

GET /marketcap/top/{limit}
# Response: Top market cap companies list

GET /marketcap/sector/{sector}
# Response: Market cap data for specific sector

POST /marketcap/bulk
# Request Body: List of symbols for bulk market cap data
# Response: Bulk market capitalization data
```

### 💰 **Unified Profit Engine (Port 8025)**

#### 💵 **Profit Analysis APIs**
```python
# Base URL: http://10.1.1.174:8025

GET /health
# Response: {"status": "healthy", "profit_engine": "active"}

GET /profit/summary
# Response:
{
    "total_profit": 15430.50,
    "realized_profit": 8250.30,
    "unrealized_profit": 7180.20,
    "profit_by_symbol": {
        "AAPL": {"realized": 2450.30, "unrealized": 1250.20},
        "GOOGL": {"realized": 1850.50, "unrealized": 950.30}
    },
    "performance_metrics": {
        "total_return_pct": 12.8,
        "sharpe_ratio": 1.45,
        "max_drawdown_pct": -5.2
    }
}

GET /profit/tax-report
# Query Parameters: ?year=2025&format=csv
# Response: Tax calculation report

POST /profit/calculate
# Request Body: Portfolio data for profit calculation
# Response: Detailed profit calculation results
```

### 🎨 **Frontend Service (Port 8080)**

#### 🌐 **Web Interface APIs**
```python
# Base URL: http://10.1.1.174:8080

GET /
# Response: Main dashboard HTML

GET /health
# Response: {"status": "healthy", "ui_version": "7.0.1"}

GET /api/dashboard/data
# Response: Real-time dashboard data (JSON)

WebSocket /ws/updates
# Real-time updates for dashboard components

GET /api/csv/table-data
# Query Parameters: ?page=1&limit=100&filter={}
# Response: Paginated CSV table data for UI

POST /api/user/interaction
# Request Body: User interaction logging
# Response: Interaction logged confirmation
```

---

## 🔗 **Service-to-Service Communication Patterns**

### 🔄 **Event-Driven Communication Flow**

#### 📊 **Typical Analysis-to-Dashboard Flow**
```mermaid
sequenceDiagram
    participant IC as Intelligent Core (8001)
    participant EB as Event Bus (8014)
    participant PT as Prediction Tracking (8018)
    participant ML as ML Analytics (8021)
    participant UI as Frontend (8080)
    
    IC->>EB: Publish analysis.state.changed
    EB->>PT: Forward analysis event
    EB->>ML: Forward analysis event
    EB->>UI: Forward analysis event
    
    PT->>EB: Publish prediction validation
    ML->>EB: Publish model performance update
    
    UI->>UI: Update dashboard in real-time
```

#### 💹 **Trading Decision Flow**
```mermaid
sequenceDiagram
    participant IC as Intelligent Core (8001)
    participant BG as Broker Gateway (8012)
    participant PE as Profit Engine (8025)
    participant EB as Event Bus (8014)
    participant UI as Frontend (8080)
    
    IC->>IC: Generate trading signal
    IC->>BG: POST /orders/create
    BG->>EB: Publish trading.state.changed
    
    EB->>PE: Forward trading event
    EB->>UI: Forward trading event
    
    PE->>PE: Calculate profit impact
    PE->>EB: Publish portfolio.state.changed
    
    UI->>UI: Update portfolio display
```

### 🔌 **HTTP Communication Patterns**

#### 🤖 **ML Model Training Request Flow**
```python
# Automated Training Trigger (Intelligent Core → ML Analytics)
async def trigger_model_retraining():
    """Example of service-to-service HTTP communication"""
    
    # 1. Check current model performance
    performance = await http_client.get("http://localhost:8021/models/performance")
    
    if performance["accuracy"] < 0.70:  # Performance threshold
        # 2. Trigger retraining
        training_request = {
            "model_type": "ensemble",
            "trigger_reason": "performance_degradation",
            "current_accuracy": performance["accuracy"]
        }
        
        training_response = await http_client.post(
            "http://localhost:8021/models/train",
            json=training_request
        )
        
        # 3. Publish training event
        await event_bus.publish_event(
            "config.updated",
            {
                "service": "ml-analytics",
                "action": "model_retraining_started",
                "training_job_id": training_response["job_id"]
            }
        )
```

#### 📊 **Data Synchronization Pattern**
```python
# Data Processing → Multiple Services Sync
async def sync_market_data():
    """Multi-service data synchronization example"""
    
    # 1. Fetch from external API
    market_data = await alpha_vantage_client.get_market_data(symbols)
    
    # 2. Process and validate
    processed_data = await process_csv_data(market_data)
    
    # 3. Sync with MarketCap service
    await http_client.post(
        "http://localhost:8011/marketcap/bulk",
        json=processed_data["market_caps"]
    )
    
    # 4. Update Intelligent Core
    await http_client.post(
        "http://localhost:8001/data/update",
        json=processed_data["stock_data"]
    )
    
    # 5. Publish sync event
    await event_bus.publish_event(
        "data.synchronized",
        {
            "data_source": "alpha_vantage",
            "symbols_updated": list(symbols),
            "sync_timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

## 📡 **External API Integration**

### 🔌 **External API Communication Patterns**

#### 📊 **Multi-Provider Data Fetching**
```python
# Broker Gateway → External Trading APIs
EXTERNAL_API_ENDPOINTS = {
    "bitpanda": {
        "base_url": "https://api.bitpanda.com/v1",
        "endpoints": {
            "portfolio": "/account/balances",
            "orders": "/account/orders",
            "market_data": "/market/ticker/{symbol}"
        },
        "rate_limit": "100 requests/minute",
        "authentication": "API_KEY + SIGNATURE"
    },
    
    "alpha_vantage": {
        "base_url": "https://www.alphavantage.co/query",
        "endpoints": {
            "time_series": "?function=TIME_SERIES_DAILY&symbol={symbol}",
            "fundamentals": "?function=COMPANY_OVERVIEW&symbol={symbol}",
            "earnings": "?function=EARNINGS&symbol={symbol}"
        },
        "rate_limit": "5 requests/minute",
        "authentication": "API_KEY"
    },
    
    "yahoo_finance": {
        "base_url": "https://query1.finance.yahoo.com/v8/finance",
        "endpoints": {
            "quotes": "/chart/{symbol}",
            "historical": "/chart/{symbol}?period1={start}&period2={end}",
            "news": "/news/{symbol}"
        },
        "rate_limit": "2000 requests/hour",
        "authentication": "None"
    }
}
```

#### 🛡️ **API Error Handling & Fallbacks**
```python
async def fetch_stock_data_with_fallback(symbol: str) -> StockData:
    """Resilient external API communication with fallbacks"""
    
    providers = ["alpha_vantage", "yahoo_finance", "iex_cloud"]
    
    for provider in providers:
        try:
            # Rate limiting check
            if not await check_rate_limit(provider):
                continue
            
            # Primary API call
            data = await external_api_client.get_stock_data(provider, symbol)
            
            if data and validate_stock_data(data):
                # Cache successful response
                await redis_client.setex(
                    f"stock_data:{provider}:{symbol}",
                    300,  # 5 minute cache
                    json.dumps(data)
                )
                return data
                
        except APIError as e:
            logger.warning(f"Provider {provider} failed: {e}")
            continue
        
        except RateLimitExceeded:
            logger.info(f"Rate limit exceeded for {provider}")
            continue
    
    # All providers failed - return cached data if available
    cached_data = await redis_client.get(f"stock_data:*:{symbol}")
    if cached_data:
        logger.warning(f"Using cached data for {symbol}")
        return json.loads(cached_data)
    
    raise DataUnavailableError(f"No data available for {symbol}")
```

---

## 🔧 **Internal Communication Configuration**

### ⚙️ **Service Discovery & Configuration**
```python
# /opt/aktienanalyse-ökosystem/.env
# Service Communication Configuration

# Internal Service URLs
INTELLIGENT_CORE_URL=http://localhost:8001
BROKER_GATEWAY_URL=http://localhost:8012
DIAGNOSTIC_SERVICE_URL=http://localhost:8013
EVENT_BUS_URL=http://localhost:8014
MONITORING_SERVICE_URL=http://localhost:8015
DATA_PROCESSING_URL=http://localhost:8017
PREDICTION_TRACKING_URL=http://localhost:8018
MARKETCAP_SERVICE_URL=http://localhost:8011
ML_ANALYTICS_URL=http://localhost:8021
UNIFIED_PROFIT_ENGINE_URL=http://localhost:8025
FRONTEND_SERVICE_URL=http://localhost:8080

# Redis Event Bus Configuration
REDIS_URL=redis://localhost:6379
REDIS_EVENT_DB=0
REDIS_CACHE_DB=1

# Database Configuration
POSTGRES_URL=postgresql://aktienanalyse:password@localhost/event_store_db
POSTGRES_POOL_SIZE=20
POSTGRES_TIMEOUT=30

# HTTP Client Configuration
HTTP_TIMEOUT=10
HTTP_MAX_CONNECTIONS=100
HTTP_RETRY_COUNT=3

# Event Bus Configuration
EVENT_BUS_BATCH_SIZE=100
EVENT_CACHE_TTL=300
EVENT_PROCESSING_TIMEOUT=5
```

### 🔗 **Communication Middleware**
```python
# shared/communication_client.py
class ServiceCommunicationClient:
    """Unified communication client for inter-service calls"""
    
    def __init__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100)
        )
        
    async def call_service(self, service_name: str, 
                           endpoint: str, 
                           method: str = "GET",
                           data: dict = None) -> dict:
        """
        Standardized service-to-service communication
        Includes retry logic, error handling, and monitoring
        """
        service_url = self.get_service_url(service_name)
        url = f"{service_url}{endpoint}"
        
        # Add correlation ID for request tracking
        headers = {
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Service-Name": self.service_name,
            "Content-Type": "application/json"
        }
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with self.session.request(
                    method, url, 
                    json=data, 
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Log successful call
                        logger.info(f"Service call success: {service_name}{endpoint}")
                        return result
                    
                    elif response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 5))
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    
                    else:
                        error_text = await response.text()
                        raise ServiceCommunicationError(
                            f"HTTP {response.status}: {error_text}"
                        )
                        
            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count >= max_retries:
                    raise ServiceTimeoutError(f"Timeout calling {service_name}{endpoint}")
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            
            except aiohttp.ClientError as e:
                raise ServiceCommunicationError(f"Network error: {e}")
        
        raise ServiceCommunicationError(f"Max retries exceeded for {service_name}{endpoint}")
```

---

*Kommunikationspfade - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*