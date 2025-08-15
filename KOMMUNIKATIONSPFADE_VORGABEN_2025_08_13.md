# KOMMUNIKATIONSPFADE & STANDARDS - VORGABEN DOKUMENTATION
**Datum**: 2025-08-13  
**Projekt**: Aktienanalyse-Ökosystem Data Processing Integration  
**Zweck**: Standardisierte Kommunikationsvorgaben für alle Module

---

## 🌐 **KOMMUNIKATIONS-ARCHITEKTUR DIAGRAMM**

```
                    🏗️ AKTIENANALYSE-ÖKOSYSTEM KOMMUNIKATIONSPFADE
                                    (Data Processing Service Integration)

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   📊 EVENT-BUS LAYER                                    │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐                   │
│  │   Event-Router  │    │  Event-Store     │    │  Event-Monitor  │                   │
│  │ (Smart-Routing) │◄──►│ (Redis+RabbitMQ) │◄──►│ (Health+Metrics)│                   │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
           ▲                           ▲                           ▲
           │ Events                    │ Events                    │ Events
           ▼                           ▼                           ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 🖥️ Frontend     │  │ 📊 Data         │  │ 🧠 Intelligent  │  │ 🔗 Broker       │
│    Service      │  │ Processing      │  │    Core         │  │ Gateway         │
│  (Port 8013)    │  │ Service (NEW)   │  │  (Port 8011)    │  │  (Port 8012)    │
│                 │  │  (Port 8017)    │  │                 │  │                 │
│ • GUI (4-Funcs) │  │ • CSV Generator │  │ • Analysis      │  │ • Trading       │
│ • WebSocket     │  │ • DB Listener   │  │ • ML Prediction │  │ • Market Data   │
│ • CSV Proxy     │  │ • Performance   │  │ • Intelligence  │  │ • Account Mgmt  │
│ • Real-Time UI  │  │ • Cache Manager │  │ • Orchestration │  │ • Order Mgmt    │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
           │                  │                  │                  │
           │ REST APIs        │ NOTIFY/LISTEN    │ Event-Store      │ Event-Store
           │ WebSocket        │ Queries          │ Writes           │ Writes
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            🗄️ POSTGRESQL EVENT-STORE LAYER                              │
│                                                                                         │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐                   │
│  │   Event Store   │    │ Materialized     │    │  CSV Metadata   │                   │
│  │ • events table  │    │ Views            │    │ • Generation    │                   │
│  │ • append_event()│    │ • stock_analysis │    │ • Performance   │                   │
│  │ • triggers      │    │ • portfolio      │    │ • Tracking      │                   │
│  │ • NOTIFY/LISTEN │    │ • trading        │    │ • Status        │                   │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘                   │
│                                                                                         │
│  🚀 PERFORMANCE: <0.12s Queries │ 🔔 NOTIFY: Real-time Updates │ 📈 SCALING: Event-Sourcing │
└─────────────────────────────────────────────────────────────────────────────────────────┘

           Supporting Services:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 📊 Monitoring   │  │ 🔍 Diagnostic   │  │ 📁 File System  │  │ 🐳 Redis Cache  │
│  (Port 8015)    │  │  (Port 8016)    │  │ • CSV Files     │  │ • Event Cache   │
│ • Health Checks │  │ • System Tests  │  │ • Templates     │  │ • Performance   │
│ • Metrics       │  │ • Integration   │  │ • Static Assets │  │ • Session Data  │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 📋 **STANDARDISIERTE KOMMUNIKATIONS-VORGABEN**

### **1. Event-Bus Kommunikations-Standard**

**Pflichtfelder für alle Events:**
```json
{
  "event_type": "domain.action.state",
  "stream_id": "domain-aggregate-timestamp",
  "data": {
    "mandatory_fields": ["source", "timestamp", "correlation_id"],
    "domain_specific": "varies_by_event_type"
  },
  "source": "service-name",
  "correlation_id": "uuid4",
  "metadata": {
    "causation_id": "parent_event_id",
    "user_context": "optional",
    "tracing_id": "distributed_tracing"
  }
}
```

**Event-Type Namenskonventionen:**
- `analysis.state.changed` - Analyse-Zustandsänderungen
- `data.synchronized` - Datenverarbeitung abgeschlossen
- `user.interaction.logged` - Benutzerinteraktionen
- `system.alert.raised` - System-Alerts und Fehler
- `trading.state.changed` - Trading-Aktivitäten
- `portfolio.state.changed` - Portfolio-Updates

**Event-Router Standard-Konfiguration:**
```python
ROUTING_RULES = {
    "analysis_to_data_processing": {
        "source_pattern": "intelligent-core-*",
        "target_services": ["data-processing", "frontend"],
        "event_types": ["analysis.state.changed"],
        "enabled": True
    },
    "data_processing_to_frontend": {
        "source_pattern": "data-processing",
        "target_services": ["frontend", "monitoring"],
        "event_types": ["data.synchronized"],
        "enabled": True
    },
    "csv_updates_broadcast": {
        "source_pattern": "data-processing",
        "target_services": ["*"],
        "event_types": ["user.interaction.logged", "system.alert.raised"],
        "enabled": True
    }
}
```

### **2. REST API Kommunikations-Standard**

**URL-Struktur:**
```
/api/v{version}/{service}/{resource}/{action}

Beispiele:
• /api/v1/data/top15-predictions          # CSV-Download
• /api/v1/data/soll-ist-vergleich         # CSV-Download  
• /api/v1/data/status                     # Service-Status
• /api/v1/data/refresh                    # Manuelle Aktualisierung
• /api/v1/health                          # Health-Check (alle Services)
• /api/v1/metrics                         # Performance-Metriken
```

**Standard HTTP Headers:**
```http
# Request Headers (Client → Server)
Content-Type: application/json
Accept: application/json,text/csv
X-Correlation-ID: uuid4
X-Request-ID: uuid4
User-Agent: aktienanalyse-frontend/1.0

# Response Headers (Server → Client)
Content-Type: application/json|text/csv
Cache-Control: public,max-age=300
X-Generated-By: service-name-version
X-Processing-Time-Ms: 123
X-Event-ID: uuid4
```

**CSV-Proxy Integration Pattern:**
```python
# Frontend Service CSV Proxy Pattern
class CSVProxyHandler:
    """CSV-Proxy mit Error-Handling und Caching"""
    
    @app.get("/api/frontend/csv-data/{csv_type}")
    async def proxy_csv_data(self, csv_type: str, request: Request):
        """Proxy CSV-Request mit Event-Bus-Compliance"""
        try:
            # Event-Bus-Compliance: Log request
            request_event = Event(
                event_type=EventType.DASHBOARD_REQUEST.value,
                stream_id=f"csv-proxy-{csv_type}-{int(time.time())}",
                data={
                    "request_type": "csv_proxy",
                    "csv_type": csv_type,
                    "client_ip": get_client_ip(request),
                    "user_agent": request.headers.get("user-agent", "unknown")
                },
                source="frontend-proxy"
            )
            await self.event_bus.publish(request_event)
            
            # Proxy request zu Data Processing Service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/data/{csv_type}")
                
                return Response(
                    content=response.content,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename={csv_type}.csv",
                        "Cache-Control": f"public, max-age={self.cache_timeout}",
                        "X-Generated-By": "aktienanalyse-data-processing-v1.0"
                    }
                )
                        
        except Exception as e:
            # Error event via Event-Bus
            error_event = Event(
                event_type=EventType.SYSTEM_ALERT_RAISED.value,
                stream_id=f"csv-error-{csv_type}-{int(time.time())}",
                data={
                    "alert_type": "proxy_error",
                    "severity": "ERROR", 
                    "message": f"CSV proxy error: {str(e)}",
                    "csv_type": csv_type
                },
                source="frontend-proxy"
            )
            await self.event_bus.publish(error_event)
            
            raise HTTPException(status_code=500, detail="Internal proxy error")
```

### **3. WebSocket Kommunikations-Standard**

**WebSocket Channels:**
```javascript
// Frontend WebSocket Connections
const connections = {
  csv_updates: 'ws://localhost:8013/ws/csv-updates',
  system_health: 'ws://localhost:8013/ws/system-health',
  trading_updates: 'ws://localhost:8013/ws/trading-updates',
  analysis_progress: 'ws://localhost:8013/ws/analysis-progress'
};

// Standardisiertes Message Format
const message_format = {
  type: "message_type",
  data: {
    // Type-spezifische Daten
  },
  timestamp: "ISO8601",
  source: "service-name",
  correlation_id: "uuid4"
};
```

**WebSocket Message Types:**
- `csv_updated` - CSV-Dateien wurden regeneriert
- `performance_alert` - Performance-Warnungen
- `system_health` - System-Health-Updates
- `analysis_completed` - Analyse abgeschlossen
- `trading_executed` - Trading-Order ausgeführt

**WebSocket Integration Beispiel:**
```javascript
// Frontend WebSocket Integration
class CSVUpdateManager {
    constructor() {
        this.websocket = new WebSocket('ws://localhost:8013/ws/csv-updates');
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'csv_updated':
                    this.handleCSVUpdate(data);
                    break;
                case 'performance_alert':
                    this.handlePerformanceAlert(data);
                    break;
                case 'system_health':
                    this.handleSystemHealth(data);
                    break;
            }
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showNotification('Verbindungsfehler zu Real-Time Updates', 'error');
        };
    }
    
    async handleCSVUpdate(data) {
        // Show user notification
        this.showNotification('CSV-Daten wurden aktualisiert', 'success');
        
        // Auto-refresh if relevant tab is active
        const activeTab = document.querySelector('.nav-link.active').id;
        if (activeTab === 'gewinnprognose-tab' && data.csv_types.includes('top15_predictions')) {
            await this.refreshTop15Table();
        } else if (activeTab === 'soll-ist-tab' && data.csv_types.includes('soll_ist_vergleich')) {
            await this.refreshSollIstTable();
        }
        
        // Update status indicators
        this.updateStatusIndicators(data);
    }
}
```

### **4. Database Kommunikations-Standard**

**Event-Store Query-Pattern:**
```sql
-- Standardisierte Query-Templates für alle Services

-- 1. Event-Append (Thread-safe mit Optimistic Locking)
SELECT append_event(
    $1::VARCHAR,  -- stream_id (domain-aggregate-id)
    $2::VARCHAR,  -- stream_type (domain)
    $3::VARCHAR,  -- event_type
    $4::JSONB,    -- event_data
    $5::JSONB,    -- event_metadata
    $6::BIGINT    -- expected_version (NULL = any)
);

-- 2. Materialized View Query (Performance-optimiert)
SELECT * FROM {domain}_unified 
WHERE {filter_conditions}
ORDER BY {sort_field} DESC
LIMIT {limit_count};

-- 3. Real-time Listening (NOTIFY/LISTEN)
LISTEN 'csv_update_needed';
LISTEN 'system_health_changed';
LISTEN 'trading_event_occurred';
```

**Connection Pool Standards:**
```python
# PostgreSQL Connection Pool Konfiguration
POSTGRES_POOL_CONFIG = {
    'min_size': 5,
    'max_size': 20,
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 300,
    'timeout': 30,
    'command_timeout': 60
}

# Redis Connection Pool Konfiguration  
REDIS_POOL_CONFIG = {
    'max_connections': 10,
    'retry_on_timeout': True,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'health_check_interval': 30
}
```

**Standardisierte Event-Store-Integration:**
```python
# Standardisierte Event-Store-Integration für alle Services
class EventStoreService:
    """Standardisierte Event-Store-Integration"""
    
    async def append_domain_event(self, domain: str, aggregate_id: str, 
                                 event_type: str, event_data: Dict[str, Any],
                                 expected_version: int = None):
        """Append Event mit automatischer Materialized View Refresh"""
        try:
            # Event in Event-Store schreiben
            event_id = await self.db_pool.fetchval(
                "SELECT append_event($1, $2, $3, $4, $5, $6)",
                f"{domain}-{aggregate_id}",  # stream_id
                domain,                      # stream_type  
                event_type,
                json.dumps(event_data),
                json.dumps({}),              # metadata
                expected_version
            )
            
            # Event-Bus-Notification (automatisch via Trigger)
            logger.info(f"Event appended: {event_type}", event_id=event_id)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            raise
```

**Optimierte Query-Pattern für CSV-Generierung:**
```python
# Optimierte Query-Pattern für CSV-Generierung
class CSVDataQueries:
    """Optimierte Materialized View Queries"""
    
    async def get_top15_predictions(self) -> List[Dict[str, Any]]:
        """Top 15 Predictions mit <0.12s Performance"""
        query = """
        SELECT 
            symbol,
            latest_score,
            recommendation, 
            confidence,
            technical_indicators->'prediction_7d' as prediction_7d,
            technical_indicators->'prediction_14d' as prediction_14d,
            technical_indicators->'prediction_31d' as prediction_31d,
            technical_indicators->'prediction_6m' as prediction_6m,
            technical_indicators->'prediction_12m' as prediction_12m,
            last_updated
        FROM csv_top15_predictions  -- Materialized View
        ORDER BY latest_score DESC
        LIMIT 15
        """
        
        start_time = time.time()
        results = await self.db_pool.fetch(query)
        query_time = time.time() - start_time
        
        # Performance-Logging
        logger.info(f"Top15 query completed in {query_time:.3f}s")
        
        if query_time > 0.12:
            logger.warning(f"Slow query detected: {query_time:.3f}s > 0.12s")
        
        return [dict(row) for row in results]
```

---

## 🔒 **SECURITY & ERROR HANDLING VORGABEN**

### **Error Handling Standard:**
```python
# Standardisiertes Error-Response Format
error_response = {
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {
            "service": "service-name",
            "timestamp": "ISO8601",
            "correlation_id": "uuid4",
            "stack_trace": "Only in DEBUG mode"
        },
        "retry_after": 30,  # Sekunden bis Retry möglich
        "documentation_url": "https://docs.example.com/errors/ERROR_CODE"
    }
}

# Event-Bus Error Event
error_event = Event(
    event_type=EventType.SYSTEM_ALERT_RAISED.value,
    stream_id=f"error-{service}-{timestamp}",
    data={
        "alert_type": "service_error",
        "severity": "ERROR|WARNING|INFO",
        "error_code": "HTTP_500|DB_TIMEOUT|VALIDATION_ERROR",
        "message": "Detailed error description",
        "affected_services": ["service1", "service2"],
        "metrics": {"response_time": 1234, "memory_usage": 85}
    },
    source="error-handler"
)
```

### **Timeout & Retry Standards:**
```python
# Service-zu-Service Kommunikation Timeouts
TIMEOUT_CONFIG = {
    'database_query': 30,      # PostgreSQL Queries
    'event_bus_publish': 5,    # Event-Bus Publish
    'http_request': 30,        # REST API Calls
    'websocket_send': 10,      # WebSocket Messages
    'file_generation': 60,     # CSV Generation
    'health_check': 10         # Health Check Requests
}

# Retry-Strategien
RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 2,
    'retry_status_codes': [500, 502, 503, 504],
    'retry_exceptions': ['ConnectionError', 'TimeoutError']
}
```

---

## 📊 **MONITORING & OBSERVABILITY VORGABEN**

### **Logging Standards:**
```python
# Strukturiertes Logging Format (alle Services)
log_entry = {
    "timestamp": "2025-01-15T10:30:00Z",
    "level": "INFO|WARNING|ERROR|DEBUG",
    "service": "service-name",
    "module": "module-name", 
    "message": "Human-readable message",
    "context": {
        "correlation_id": "uuid4",
        "user_id": "optional",
        "session_id": "optional",
        "request_id": "uuid4"
    },
    "metrics": {
        "duration_ms": 123,
        "memory_mb": 45,
        "cpu_percent": 12
    },
    "tags": ["csv", "generation", "performance"]
}
```

### **Metrics Collection Standards:**
```python
# Performance-Metriken (alle Services)
performance_metrics = {
    "response_times": {
        "csv_generation_ms": [245, 189, 267],
        "database_query_ms": [87, 92, 78],
        "event_processing_ms": [12, 15, 9]
    },
    "throughput": {
        "requests_per_second": 45,
        "events_processed_per_minute": 1200,
        "csv_downloads_per_hour": 150
    },
    "error_rates": {
        "http_5xx_percent": 0.1,
        "database_timeout_percent": 0.05,
        "event_bus_failure_percent": 0.02
    },
    "resource_usage": {
        "memory_usage_percent": 68,
        "cpu_usage_percent": 23,
        "disk_usage_percent": 45
    }
}
```

### **Cross-Service Health Checks:**
```python
# Health Check Kommunikationsprotokoll
class HealthCheckOrchestrator:
    """Orchestrierter Health Check über alle Services"""
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Comprehensive Health Check über Event-Bus"""
        health_results = {}
        
        # Send health check requests via Event-Bus
        services = ["frontend", "data-processing", "intelligent-core", "broker-gateway"]
        
        for service in services:
            health_request = Event(
                event_type=EventType.SYSTEM_HEALTH_REQUEST.value,
                stream_id=f"health-check-{service}-{int(time.time())}",
                data={
                    "request_type": "comprehensive_health",
                    "requested_by": "monitoring",
                    "timeout_seconds": 10
                },
                source="monitoring"
            )
            
            # Publish request
            await self.event_bus.publish(health_request)
            
            # Wait für response (mit Timeout)
            try:
                response = await self.wait_for_health_response(service, timeout=10)
                health_results[service] = response
            except asyncio.TimeoutError:
                health_results[service] = {
                    "status": "timeout",
                    "error": f"Health check timeout after 10s",
                    "available": False
                }
        
        # Overall system health
        healthy_services = sum(1 for result in health_results.values() 
                             if result.get("status") == "healthy")
        total_services = len(health_results)
        
        system_health = {
            "system_status": "healthy" if healthy_services >= total_services * 0.75 else "degraded",
            "healthy_services": healthy_services,
            "total_services": total_services,
            "service_details": health_results,
            "csv_data_availability": await self.check_csv_availability(),
            "event_bus_status": await self.check_event_bus_health(),
            "database_status": await self.check_database_health(),
            "timestamp": datetime.now().isoformat()
        }
        
        return system_health
```

---

## 🚀 **PERFORMANCE BENCHMARKS & SLAs**

### **Service Level Agreements:**
```yaml
sla_targets:
  csv_generation:
    duration: "<1000ms"
    availability: "99.9%"
    max_file_size: "10MB"
    
  database_queries:
    materialized_views: "<120ms"
    event_store_writes: "<100ms" 
    connection_pool: "<50ms"
    
  api_responses:
    health_checks: "<100ms"
    csv_downloads: "<500ms"
    status_endpoints: "<200ms"
    
  event_bus:
    publish_latency: "<50ms"
    delivery_guarantee: "at-least-once"
    message_ordering: "per-stream"
    
  real_time_updates:
    websocket_latency: "<100ms"
    notification_delay: "<1000ms"
    connection_recovery: "<5000ms"
```

---

## 🔗 **SPEZIFISCHE KOMMUNIKATIONSPFADE**

### **1. CSV-Generierung Workflow**
```
Intelligent-Core → PostgreSQL (INSERT analysis event) → 
TRIGGER notify_csv_update() → Data-Processing (NOTIFY receive) → 
CSV Generation → Event-Bus (DATA_SYNCHRONIZED event) → 
Frontend (WebSocket notification) → User Interface Update
```

### **2. API-Kommunikation**
```
Frontend → GET /api/frontend/csv-data/{type} → Data Processing Service → 
PostgreSQL (Materialized View Query <0.12s) → CSV File Response → 
Frontend Download
```

### **3. Event-Bus Integration**
```
Service → Event Creation → Event-Bus Publish → Event-Router → 
Target Services → Event Processing → Response/Acknowledgment
```

### **4. Real-Time Updates**
```
Database Change → PostgreSQL NOTIFY → Data Processing → 
CSV Regeneration → Event-Bus → Frontend WebSocket → 
GUI Update Notification
```

---

## 📋 **MODUL-KOMMUNIKATIONS-MATRIX**

| **Von/Nach** | Frontend | Data-Processing | Intelligent-Core | Broker-Gateway | Event-Bus | PostgreSQL |
|--------------|----------|-----------------|------------------|----------------|-----------|------------|
| **Frontend** | - | CSV-APIs | Event-Bus | Event-Bus | Pub/Sub | - |
| **Data-Processing** | CSV-Response | Internal | Event-Listen | - | Pub/Sub | NOTIFY/LISTEN + Query |
| **Intelligent-Core** | Event-Bus | Event-Trigger | - | - | Pub/Sub | Event-Store |
| **Broker-Gateway** | Event-Bus | - | Event-Bus | - | Pub/Sub | Event-Store |
| **Event-Bus** | WebSocket | Events | Events | Events | - | - |
| **PostgreSQL** | - | Notifications | Event-Store | Event-Store | - | - |

---

## ✅ **IMPLEMENTIERUNGS-CHECKLISTE**

### **🔧 Service-Entwicklung Checkliste:**

- ✅ **Shared Libraries Integration** - ModularService, DatabaseMixin, EventBusMixin
- ✅ **Event-Bus-Compliance** - Alle Events über Event-Bus, Standard Event-Schema
- ✅ **Database Integration** - PostgreSQL Event-Store, Materialized Views, NOTIFY/LISTEN
- ✅ **Performance Optimization** - <1s CSV-Generierung, <0.12s DB-Queries
- ✅ **Error Handling** - Strukturierte Error-Events, Retry-Logic, Circuit Breaker
- ✅ **Monitoring Integration** - Structured Logging, Performance Metrics, Health Checks
- ✅ **API Documentation** - OpenAPI Specs, Response Schemas, Error Codes
- ✅ **Testing Strategy** - Unit Tests, Integration Tests, Performance Tests

### **🌐 Integration Checkliste:**

- ✅ **Frontend WebSocket** - Real-Time CSV Updates, Connection Recovery
- ✅ **CSV Proxy Logic** - Error Handling, Caching, Event-Logging  
- ✅ **Database Triggers** - NOTIFY/LISTEN, Materialized View Refresh
- ✅ **Event-Router Config** - Routing Rules, Smart Distribution
- ✅ **systemd Services** - Auto-Start, Dependency Management, Restart Policies
- ✅ **Deployment Scripts** - Database Migration, Service Configuration

### **📋 Kommunikations-Compliance Checkliste:**

- ✅ **Event Schema Standard** - Pflichtfelder, Namenskonventionen, Metadata
- ✅ **REST API Standard** - URL-Struktur, HTTP Headers, Response Format
- ✅ **WebSocket Standard** - Message Types, Channel Naming, Error Handling
- ✅ **Database Standard** - Query Pattern, Connection Pools, Transaction Safety
- ✅ **Error Standard** - Structured Errors, Event-Bus Error Events, Retry Logic
- ✅ **Logging Standard** - Structured Logs, Correlation IDs, Context Data
- ✅ **Monitoring Standard** - Metrics Collection, SLA Targets, Alerting Rules

---

## 🏁 **ZUSAMMENFASSUNG**

Diese Dokumentation definiert **standardisierte Kommunikationsvorgaben** für das gesamte Aktienanalyse-Ökosystem mit Fokus auf die **Data Processing Service Integration**.

**Kernprinzipien:**
- **Event-Bus-First**: Alle Services kommunizieren primär über Event-Bus
- **Standardisierte Schemas**: Einheitliche Event-, API- und Message-Formate
- **Performance-Optimiert**: <0.12s Database-Queries, <1s CSV-Generierung
- **Observability-Ready**: Strukturiertes Logging und Monitoring in allen Services
- **Error-Resilient**: Comprehensive Error-Handling mit Event-Bus-Integration

**Compliance-Status**: Alle bestehenden Services folgen bereits diesen Standards, Data Processing Service wird nach denselben Vorgaben implementiert.