# 🏗️ LLD IMPLEMENTIERUNGS-SPECIFICATIONS v7.0

**Dokument**: Detaillierte technische Implementierungs-Specifications  
**Version**: 7.0 (Korrigierte Realitäts-basierte Specs)  
**Datum**: 24. August 2025  
**Status**: ✅ KRITISCHE KORREKTUR-SPECS für tatsächliche LLD-Umsetzung

---

## 🎯 **EXECUTIVE SUMMARY**

Diese Specifications definieren die **tatsächliche Implementierung** der LLD-Anforderungen, basierend auf der **schonungslosen End-to-End Analyse**. Die vorherigen Agent-Behauptungen waren falsch - diese Specs zeigen **WIE** die LLD wirklich umzusetzen ist.

---

## 📋 **1. SERVICE-IMPLEMENTIERUNGS-SPECIFICATIONS**

### 🧠 **Intelligent Core Service (Port 8001)**

#### **STRUKTUR-REQUIREMENT:**
```
/opt/aktienanalyse-ökosystem/services/intelligent-core-service/
├── main.py                          # FastAPI Entry Point (VERPFLICHTEND)
├── domain/                          # Domain Layer (FEHLT - MUSS ERSTELLT WERDEN)
│   ├── __init__.py
│   ├── entities/
│   │   ├── stock_analysis.py        # StockAnalysis Entity
│   │   └── analysis_result.py       # AnalysisResult Value Object
│   ├── repositories/
│   │   └── analysis_repository.py   # Repository Interface
│   └── services/
│       └── stock_analyzer.py        # Domain Service
├── application/                     # Application Layer (FEHLT)
│   ├── __init__.py
│   ├── use_cases/
│   │   ├── process_stock_analysis.py
│   │   └── cross_system_intelligence.py
│   └── interfaces/
│       └── event_publisher.py
├── infrastructure/                  # Infrastructure Layer (FEHLT)
│   ├── __init__.py
│   ├── persistence/
│   │   └── postgres_analysis_repo.py
│   ├── external/
│   │   └── redis_event_publisher.py
│   └── config/
│       └── database_config.py
├── presentation/                    # Presentation Layer (FEHLT)
│   ├── __init__.py
│   ├── controllers/
│   │   └── analysis_controller.py
│   └── schemas/
│       └── analysis_schemas.py
├── container.py                     # DI Container (FEHLT)
└── requirements.txt
```

#### **IMPLEMENTATION CODE-TEMPLATE:**

**main.py (VERPFLICHTEND):**
```python
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from container import Container
from presentation.controllers.analysis_controller import AnalysisController

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    container = Container()
    container.wire(modules=["presentation.controllers.analysis_controller"])
    app.state.container = container
    yield
    # Shutdown
    await container.unwire()

app = FastAPI(
    title="Intelligent Core Service v7.0",
    description="Clean Architecture AI Analytics Service",
    version="7.0.0",
    lifespan=lifespan
)

# Health Check VERPFLICHTEND
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "intelligent-core", "port": 8001}

# Include Controllers
app.include_router(AnalysisController.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
```

#### **COMPLIANCE REQUIREMENTS:**
- ✅ **Domain Layer**: Business Logic MUSS von Infrastructure getrennt sein
- ✅ **Dependency Injection**: Container MUSS alle Dependencies verwalten  
- ✅ **Event Publishing**: MUSS über Infrastructure Layer an Redis Event-Bus
- ✅ **Health Check**: MUSS `/health` Endpoint bereitstellen
- ✅ **Error Handling**: MUSS strukturierte Error Responses

---

### 🚌 **Event Bus Service (Port 8014) - KRITISCH**

#### **STRUKTUR-REQUIREMENT (FEHLT KOMPLETT):**
```
/opt/aktienanalyse-ökosystem/services/event-bus-service/
├── main.py                          # FastAPI Entry Point
├── domain/
│   ├── events/
│   │   ├── base_event.py           # Base Event Interface
│   │   └── event_types.py          # 8 Core Event Types aus HLD
│   └── repositories/
│       └── event_repository.py
├── application/
│   ├── event_handlers/
│   │   └── event_dispatcher.py
│   └── use_cases/
│       ├── publish_event.py
│       └── subscribe_to_events.py
├── infrastructure/
│   ├── redis/
│   │   ├── redis_publisher.py      # Redis Pub/Sub
│   │   └── redis_subscriber.py
│   ├── postgres/
│   │   └── event_store_repo.py     # PostgreSQL Persistence
│   └── monitoring/
│       └── event_metrics.py
├── presentation/
│   ├── controllers/
│   │   └── event_controller.py
│   └── websocket/
│       └── websocket_handler.py    # Real-time Event Stream
└── container.py
```

#### **KRITISCHE EVENT TYPES (aus HLD):**
```python
# domain/events/event_types.py
from enum import Enum

class EventType(str, Enum):
    ANALYSIS_STATE_CHANGED = "analysis.state.changed"
    ANALYSIS_PREDICTION_GENERATED = "analysis.prediction.generated"  
    PORTFOLIO_STATE_CHANGED = "portfolio.state.changed"
    PROFIT_CALCULATION_COMPLETED = "profit.calculation.completed"
    TRADING_STATE_CHANGED = "trading.state.changed"
    INTELLIGENCE_TRIGGERED = "intelligence.triggered"
    DATA_SYNCHRONIZED = "data.synchronized"
    MARKET_DATA_SYNCHRONIZED = "market.data.synchronized"
    SYSTEM_ALERT_RAISED = "system.alert.raised"
    USER_INTERACTION_LOGGED = "user.interaction.logged"
    CONFIG_UPDATED = "config.updated"
```

#### **PERFORMANCE REQUIREMENTS:**
- ✅ **Response Time**: <0.12s für Event Publishing (HLD Requirement)
- ✅ **Throughput**: 1000+ Events/sec (HLD Requirement)  
- ✅ **Persistence**: Alle Events MÜSSEN in PostgreSQL Event Store
- ✅ **Correlation IDs**: Für Event-Tracking zwischen Services

---

### 💰 **Unified Profit Engine Enhanced (Port 8025)**

#### **CLEAN ARCHITECTURE STRUCTURE (KOMPLETT FEHLT):**
```
/opt/aktienanalyse-ökosystem/services/unified-profit-engine-enhanced/
├── main.py
├── domain/                          # Domain Layer FEHLT
│   ├── entities/
│   │   ├── market_symbol.py        # MarketSymbol Value Object
│   │   ├── profit_prediction.py    # ProfitPrediction Entity
│   │   └── soll_ist_tracking.py    # SOLLISTTracking Aggregate
│   ├── value_objects/
│   │   └── horizon.py              # 1W, 1M, 3M, 12M Horizons
│   ├── repositories/
│   │   ├── market_data_repository.py
│   │   ├── prediction_repository.py
│   │   └── soll_ist_repository.py
│   └── services/
│       └── profit_calculator.py
├── application/                     # Application Layer FEHLT
│   ├── use_cases/
│   │   ├── generate_multi_horizon_predictions.py
│   │   ├── calculate_ist_performance.py
│   │   └── analyze_soll_ist_gap.py
│   └── interfaces/
│       ├── ml_prediction_service.py
│       └── event_publisher.py
├── infrastructure/                  # Infrastructure Layer FEHLT  
│   ├── persistence/
│   │   ├── postgres_soll_ist_repo.py
│   │   └── postgres_prediction_repo.py
│   ├── external/
│   │   ├── yahoo_finance_adapter.py
│   │   └── ml_service_client.py
│   └── events/
│       └── redis_event_publisher.py
├── presentation/                    # Presentation Layer FEHLT
│   ├── controllers/
│   │   ├── prediction_controller.py
│   │   └── soll_ist_controller.py
│   └── schemas/
│       ├── prediction_schemas.py
│       └── soll_ist_schemas.py
├── database_setup.sql              # Database Schema
└── container.py                    # DI Container
```

#### **DOMAIN ENTITIES (VERPFLICHTEND):**
```python
# domain/entities/soll_ist_tracking.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

@dataclass
class SOLLISTTracking:
    """Aggregate Root für SOLL-IST Performance Tracking"""
    datum: date
    symbol: str
    unternehmen: str
    ist_gewinn: Optional[Decimal] = None
    soll_gewinn_1w: Optional[Decimal] = None
    soll_gewinn_1m: Optional[Decimal] = None
    soll_gewinn_3m: Optional[Decimal] = None
    soll_gewinn_12m: Optional[Decimal] = None
    
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

#### **DATABASE INTEGRATION (VERPFLICHTEND):**
```sql
-- database_setup.sql
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
    
    -- Generated Columns für Performance Analysis
    diff_1w DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_1w) STORED,
    diff_1m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_1m) STORED,
    diff_3m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_3m) STORED,
    diff_12m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_12m) STORED,
    
    -- Confidence Metrics
    confidence_1w DECIMAL(5,4),
    confidence_1m DECIMAL(5,4),
    confidence_3m DECIMAL(5,4),
    confidence_12m DECIMAL(5,4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT soll_ist_tracking_datum_symbol_unique UNIQUE (datum, symbol)
);

-- Performance Indexes
CREATE INDEX idx_soll_ist_symbol_datum ON soll_ist_gewinn_tracking (symbol, datum DESC);
CREATE INDEX idx_soll_ist_datum ON soll_ist_gewinn_tracking (datum DESC);
```

---

## 📊 **2. CLEAN ARCHITECTURE STRUKTUR-TEMPLATES**

### **UNIVERSAL SERVICE TEMPLATE:**
```
service-name/
├── main.py                          # Entry Point mit FastAPI
├── domain/                          # Business Logic Layer
│   ├── __init__.py
│   ├── entities/                    # Domain Entities
│   ├── value_objects/               # Value Objects  
│   ├── repositories/                # Repository Interfaces
│   └── services/                    # Domain Services
├── application/                     # Application Logic Layer
│   ├── __init__.py
│   ├── use_cases/                   # Use Case Implementations
│   └── interfaces/                  # External Service Interfaces
├── infrastructure/                  # External Concerns Layer
│   ├── __init__.py
│   ├── persistence/                 # Database Implementations
│   ├── external/                    # External API Clients
│   └── events/                      # Event Bus Integration
├── presentation/                    # Interface Layer
│   ├── __init__.py
│   ├── controllers/                 # REST API Controllers
│   └── schemas/                     # Request/Response Schemas
├── container.py                     # Dependency Injection Container
├── requirements.txt                 # Python Dependencies
└── tests/                           # Unit & Integration Tests
    ├── unit/
    ├── integration/
    └── conftest.py
```

### **DEPENDENCY INJECTION CONTAINER (VERPFLICHTEND):**
```python
# container.py
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide
from infrastructure.persistence.postgres_repo import PostgresRepository
from infrastructure.events.redis_publisher import RedisEventPublisher
from application.use_cases.service_use_case import ServiceUseCase

class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Configuration()
    
    # Database
    database = providers.Singleton(
        PostgresRepository,
        db_url=config.database_url
    )
    
    # Event Publisher
    event_publisher = providers.Singleton(
        RedisEventPublisher,
        redis_url=config.redis_url
    )
    
    # Use Cases
    service_use_case = providers.Factory(
        ServiceUseCase,
        repository=database,
        event_publisher=event_publisher
    )
    
    wiring_config = containers.WiringConfiguration(
        modules=["presentation.controllers"]
    )
```

---

## 🔄 **3. EVENT-DRIVEN INTEGRATION PATTERNS**

### **EVENT PUBLISHING PATTERN (VERPFLICHTEND):**
```python
# infrastructure/events/redis_event_publisher.py
import json
import uuid
from datetime import datetime
from typing import Dict, Any
import aioredis
from application.interfaces.event_publisher import EventPublisher

class RedisEventPublisher(EventPublisher):
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
    
    async def initialize(self):
        self.redis_client = await aioredis.from_url(self.redis_url)
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publiziert Event über Redis Event-Bus (Port 8014)"""
        event = {
            "event_type": event_type,
            "event_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "event_data": event_data,
            "metadata": {
                "service": self.__class__.__module__.split('.')[0],
                "timestamp": datetime.now().isoformat()
            },
            "created_at": datetime.now().isoformat()
        }
        
        # Event in Redis Channel publizieren
        await self.redis_client.publish(f"events:{event_type}", json.dumps(event))
        
        # Event in PostgreSQL Event Store persistieren (VERPFLICHTEND)
        await self._persist_event(event)
    
    async def _persist_event(self, event: Dict[str, Any]) -> None:
        """Persistiert Event in PostgreSQL Event Store"""
        # Implementation für PostgreSQL Persistence
        pass
```

### **EVENT SUBSCRIPTION PATTERN:**
```python
# infrastructure/events/redis_event_subscriber.py
import json
import asyncio
from typing import Callable, List
import aioredis

class RedisEventSubscriber:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        self.handlers = {}
    
    async def initialize(self):
        self.redis_client = await aioredis.from_url(self.redis_url)
    
    async def subscribe(self, event_types: List[str], handler: Callable):
        """Subscribe to Event Types"""
        pubsub = self.redis_client.pubsub()
        
        for event_type in event_types:
            await pubsub.subscribe(f"events:{event_type}")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    event_data = json.loads(message['data'])
                    await handler(event_data)
                except Exception as e:
                    # Error handling
                    pass
```

---

## 🗄️ **4. DATABASE SCHEMA IMPLEMENTATION SPECS**

### **POSTGRESQL EVENT STORE (VERPFLICHTEND):**
```sql
-- Enhanced Event Store Schema
CREATE DATABASE IF NOT EXISTS aktienanalyse_events;

-- Core Events Table
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100),
    correlation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    version INTEGER DEFAULT 1,
    source_service VARCHAR(50),
    
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'analysis.state.changed',
            'analysis.prediction.generated',
            'portfolio.state.changed',
            'profit.calculation.completed', 
            'trading.state.changed',
            'intelligence.triggered',
            'data.synchronized',
            'market.data.synchronized',
            'system.alert.raised',
            'user.interaction.logged',
            'config.updated'
        )
    )
);

-- Performance Indexes
CREATE INDEX CONCURRENTLY idx_events_type_time ON events (event_type, created_at DESC);
CREATE INDEX CONCURRENTLY idx_events_entity_time ON events (entity_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_events_correlation ON events (correlation_id);
CREATE INDEX CONCURRENTLY idx_events_data_gin ON events USING GIN (event_data);
```

### **MATERIALIZED VIEWS (PERFORMANCE <50ms):**
```sql
-- Stock Analysis Unified View  
CREATE MATERIALIZED VIEW stock_analysis_unified AS
SELECT DISTINCT ON (entity_id)
    entity_id as stock_symbol,
    (event_data->>'score')::NUMERIC(5,2) as analysis_score,
    (event_data->>'confidence')::NUMERIC(5,4) as confidence_level,
    (event_data->>'risk_category')::VARCHAR(20) as risk_assessment,
    created_at as last_analysis,
    source_service
FROM events 
WHERE event_type = 'analysis.state.changed'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY entity_id, created_at DESC;

CREATE UNIQUE INDEX idx_stock_analysis_symbol ON stock_analysis_unified (stock_symbol);

-- Portfolio Performance View
CREATE MATERIALIZED VIEW portfolio_unified AS
SELECT 
    (event_data->>'total_value')::NUMERIC(15,2) as portfolio_value,
    (event_data->>'performance_pct')::NUMERIC(8,4) as performance_percent,
    (event_data->>'positions')::INTEGER as position_count,
    created_at as last_update
FROM events 
WHERE event_type = 'portfolio.state.changed'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 1;
```

---

## ⚙️ **5. CODE-QUALITÄT STANDARDS & TEMPLATES**

### **PYTHON CODE QUALITY REQUIREMENTS:**

#### **A) IMPORT STANDARDS (VERPFLICHTEND):**
```python
# RICHTIG - Strukturierte Imports:
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Domain Layer Imports
from domain.entities.market_symbol import MarketSymbol
from domain.repositories.prediction_repository import PredictionRepository

# Application Layer Imports  
from application.interfaces.event_publisher import EventPublisher

# Infrastructure Layer Imports
from infrastructure.persistence.postgres_repo import PostgresRepository

# FALSCH - sys.path.append VERBOTEN:
# import sys
# sys.path.append('/opt/aktienanalyse-ökosystem/shared')  # NIEMALS!
```

#### **B) ERROR HANDLING PATTERN:**
```python
from typing import Optional, Union
from dataclasses import dataclass

@dataclass
class ServiceResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

class ServiceError(Exception):
    def __init__(self, message: str, error_code: str = "GENERIC_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

# Use Case Implementation
async def execute_use_case(self, request: RequestModel) -> ServiceResult:
    try:
        result = await self._business_logic(request)
        return ServiceResult(success=True, data=result)
    except ServiceError as e:
        return ServiceResult(success=False, error=e.message, error_code=e.error_code)
    except Exception as e:
        return ServiceResult(success=False, error=str(e), error_code="UNKNOWN_ERROR")
```

#### **C) LOGGING STANDARDS:**
```python
import logging
import structlog

# Structured Logging Configuration
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage in Service
async def process_request(self, request_data: dict):
    logger.info("Processing request", 
                service="intelligent-core", 
                request_id=request_data.get("id"))
    try:
        result = await self._process(request_data)
        logger.info("Request processed successfully",
                   service="intelligent-core",
                   request_id=request_data.get("id"),
                   processing_time=elapsed_time)
        return result
    except Exception as e:
        logger.error("Request processing failed",
                    service="intelligent-core", 
                    request_id=request_data.get("id"),
                    error=str(e))
        raise
```

---

## 🚀 **6. DEPLOYMENT & SYSTEMD SPECIFICATIONS**

### **SYSTEMD SERVICE TEMPLATE (VERPFLICHTEND):**
```ini
# /etc/systemd/system/aktienanalyse-{service}.service
[Unit]
Description=Aktienanalyse {Service Name} v7.0 - Clean Architecture
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/{service-name}
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
Environment=POSTGRES_URL=postgresql://aktienanalyse:@localhost/aktienanalyse_events?sslmode=disable
Environment=REDIS_URL=redis://localhost:6379/0
Environment=SERVICE_PORT={port}
Environment=LOG_LEVEL=INFO
EnvironmentFile=/opt/aktienanalyse-ökosystem/.env

# Service Execution
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

# Auto-Restart Configuration
Restart=always
RestartSec=5
StartLimitBurst=3
StartLimitInterval=60

# Resource Limits
MemoryMax=512M
CPUQuota=50%

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/logs

# Logging
StandardOutput=journal+console
StandardError=journal+console
SyslogIdentifier=aktienanalyse-{service}

# Health Check
ExecStartPost=/bin/sleep 10
ExecStartPost=/bin/bash -c 'curl -f http://localhost:{port}/health || systemctl stop %n'

[Install]
WantedBy=multi-user.target
```

### **SERVICE PORT ASSIGNMENTS (FINAL):**
```yaml
services:
  intelligent-core-service:
    port: 8001
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-intelligent-core.service"
    
  event-bus-service:
    port: 8014
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-event-bus.service"
    
  frontend-service:
    port: 8080
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-frontend.service"
    
  data-processing-service:
    port: 8017
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-data-processing.service"
    
  prediction-tracking-service:
    port: 8018
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-prediction-tracking.service"
    
  ml-analytics-service:
    port: 8021
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-ml-analytics.service"
    
  broker-gateway-service:
    port: 8012
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-broker-gateway.service"
    
  monitoring-service:
    port: 8015
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-monitoring.service"
    
  diagnostic-service:
    port: 8013
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-diagnostic.service"
    
  marketcap-service:
    port: 8011
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-marketcap.service"
    
  unified-profit-engine-enhanced:
    port: 8025
    health_endpoint: "/health"
    systemd_service: "aktienanalyse-unified-profit-engine.service"
```

---

## 📋 **7. IMPLEMENTATION CHECKLIST**

### **PRE-IMPLEMENTATION (KRITISCH):**
- [ ] **Backup aktuelles System** komplett
- [ ] **PostgreSQL Event Store** Database erstellen  
- [ ] **Redis Server** auf Port 6379 verfügbar
- [ ] **Python Virtual Environment** erstellen
- [ ] **systemd Service User** `aktienanalyse` erstellen

### **PER SERVICE IMPLEMENTATION:**
- [ ] **Clean Architecture Ordner** erstellen (domain/, application/, infrastructure/, presentation/)
- [ ] **main.py** mit FastAPI und DI Container
- [ ] **Health Check Endpoint** `/health` implementieren
- [ ] **Domain Entities** und Value Objects definieren
- [ ] **Repository Interfaces** in Domain Layer
- [ ] **Use Cases** in Application Layer implementieren
- [ ] **Infrastructure** Repositories und Event Publisher
- [ ] **Presentation** Controllers und Schemas
- [ ] **systemd Service** Definition erstellen
- [ ] **Unit Tests** für alle Layer schreiben
- [ ] **Integration Tests** für Event Flow

### **POST-IMPLEMENTATION VERIFICATION:**
- [ ] **Alle 11 Services** laufen auf definierten Ports
- [ ] **Event-Bus Service** auf Port 8014 verfügbar
- [ ] **Health Checks** für alle Services funktional
- [ ] **Event Publishing** funktioniert End-to-End
- [ ] **PostgreSQL Event Store** erhält Events
- [ ] **SOLL-IST Tracking** Database funktional
- [ ] **Performance Requirements** <50ms Database Queries
- [ ] **No sys.path.append** in gesamtem Codebase
- [ ] **Clean Architecture** Compliance 100%

---

## 🎯 **COMPLIANCE VALIDIERUNG**

### **HLD COMPLIANCE REQUIREMENTS:**
- ✅ **11 Services** auf exakten Ports wie spezifiziert
- ✅ **Event-Bus Service** funktional auf Port 8014
- ✅ **8 Core Event Types** implementiert und testbar
- ✅ **Redis Pub/Sub** mit PostgreSQL Event Store Integration
- ✅ **Response Time** <0.12s für Event Processing
- ✅ **Throughput** 1000+ Events/sec capability

### **LLD v6.0 COMPLIANCE REQUIREMENTS:**
- ✅ **Clean Architecture** 4-Layer Struktur für alle Services
- ✅ **Domain Layer** mit Entities, Value Objects, Repositories
- ✅ **Application Layer** mit Use Cases und Interfaces
- ✅ **Infrastructure Layer** mit Persistence und External Services
- ✅ **Presentation Layer** mit Controllers und Schemas
- ✅ **Dependency Injection** Container für alle Services
- ✅ **SOLL-IST Tracking** Multi-Horizon Implementation

### **CODE QUALITY REQUIREMENTS:**
- ✅ **SOLID Principles** durchgängig implementiert
- ✅ **Single Responsibility** pro Klasse und Service
- ✅ **DRY Principle** - keine Code-Duplikation
- ✅ **Import Standards** - keine sys.path.append Statements
- ✅ **Error Handling** - strukturierte ServiceResult Pattern
- ✅ **Logging** - strukturiertes Logging mit Context
- ✅ **Testing** - Unit und Integration Tests

---

## 🚨 **KRITISCHE ERFOLGS-FAKTOREN**

### **1. EVENT-BUS SERVICE (HÖCHSTE PRIORITÄT):**
Der Event-Bus Service ist das **kritische Herzstück** des Systems. Ohne funktionsfähigen Event-Bus auf Port 8014 ist das Event-Driven Pattern unmöglich.

### **2. CLEAN ARCHITECTURE DURCHSETZUNG:**
Jeder Service MUSS die 4-Layer Clean Architecture implementieren. Shortcuts führen zu Architecture Violations.

### **3. DATABASE INTEGRATION:**
PostgreSQL Event Store und SOLL-IST Tracking Database sind fundamental für System-Funktionalität.

### **4. SYSTEMATISCHE IMPLEMENTATION:**
Services müssen in korrekter Reihenfolge implementiert werden:
1. **Event-Bus Service** (Port 8014) - ERSTE PRIORITÄT
2. **Database Services** (Event Store, SOLL-IST Tracking)  
3. **Core Services** (Intelligent Core, Unified Profit Engine)
4. **Supporting Services** (Frontend, Monitoring, etc.)

---

**🎯 Diese Specifications sind VERPFLICHTEND für LLD-Compliance. Abweichungen führen zu Architecture Violations und System-Instabilität.**

---

*LLD Implementation Specifications v7.0 - Kritische Korrektur-Specs*  
*24. August 2025 - Realitäts-basierte Implementierungs-Anweisungen*