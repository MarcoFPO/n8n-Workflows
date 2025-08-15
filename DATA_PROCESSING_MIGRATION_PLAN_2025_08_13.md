# DATA PROCESSING SERVICE - VOLLSTÄNDIGER MIGRATIONS- UND IMPLEMENTIERUNGSPLAN
**Datum**: 2025-08-13  
**Projekt**: Aktienanalyse-Ökosystem  
**Zweck**: Integration Data Processing Service für CSV-basierte Datenaufbereitung

---

## 🏗️ **EXECUTIVE SUMMARY**

**Ziel**: Integration eines **Data Processing Service** als Zwischenmodul zwischen Intelligent-Core und Frontend-Service für CSV-basierte Datenaufbereitung und Event-triggered Updates.

**Bestehende Architektur**: Vollständig implementierte Event-Store-basierte Mikroservices-Architektur mit:
- ✅ PostgreSQL Event-Store mit Materialized Views (0.12s Query-Performance)
- ✅ Real Event-Bus (Redis + RabbitMQ) mit Smart-Routing
- ✅ Modularisierte Services mit Shared Libraries
- ✅ Event-Bus-Compliance in allen Services

**Migrations-Strategie**: **Erweiterte Integration** statt Refactoring - bestehende Architektur ist hochwertig und Event-Store-kompatibel.

---

## 🎯 **IMPLEMENTIERUNGSSTRATEGIE**

### **Phase 1: Data Processing Service (3-5 Tage)**
- **Ansatz**: Native Integration in bestehende Event-Store-Architektur
- **Architektur**: ModularService + DatabaseMixin + EventBusMixin Pattern
- **Datenbasis**: PostgreSQL Event-Store Materialized Views als Datenquelle
- **Integration**: Event-Bus-Compliance für alle Kommunikation

### **Phase 2: Frontend Integration (2-3 Tage)**
- **CSV-Endpoints**: Native FastAPI Integration im Frontend-Service
- **Update-Mechanismus**: PostgreSQL NOTIFY/LISTEN für Real-Time Updates
- **GUI-Modernisierung**: 4-Funktionen-Struktur mit Bootstrap 5

### **Phase 3: Event-Integration & Testing (2 Tage)**
- **Event-Triggered Updates**: Database-Write → Event-Bus → CSV-Regeneration
- **System-Testing**: End-to-End Integration Tests
- **Performance-Validierung**: <0.12s Query-Zeiten beibehalten

---

## 🔄 **KOMMUNIKATIONSBEZIEHUNGEN - BESTEHEND VS. GEPLANT**

### **🏗️ BESTEHENDE ARCHITEKTUR (Event-Store Pattern)**
```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ Frontend-Service│◄──►│   Event-Bus      │◄──►│ Intelligent-Core  │
│    (Port 8013)  │    │  (Port 8014)     │    │   (Port 8011)     │
└─────────────────┘    └──────────────────┘    └───────────────────┘
         │                        ▲                        │
         │                        │                        │
         ▼                        │                        ▼
┌─────────────────┐              │              ┌───────────────────┐
│ Broker-Gateway  │──────────────┘              │  PostgreSQL       │
│   (Port 8012)   │                             │  Event-Store      │
└─────────────────┘                             └───────────────────┘
         │                                                │
         ▼                                                │
┌─────────────────┐    ┌──────────────────┐             │
│ Monitoring      │    │ Diagnostic       │             │
│   (Port 8015)   │    │   (Port 8016)    │             │
└─────────────────┘    └──────────────────┘             │
                                                          ▼
                                              ┌───────────────────┐
                                              │ Materialized Views│
                                              │ - stock_analysis  │
                                              │ - portfolio       │
                                              │ - trading_activity│
                                              │ - system_health   │
                                              └───────────────────┘
```

### **🚀 ERWEITERTE ARCHITEKTUR (Data Processing Service Integration)**
```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ Frontend-Service│◄──►│   Event-Bus      │◄──►│ Intelligent-Core  │
│   + CSV APIs    │    │  + Event-Router  │    │   (Port 8011)     │
│   (Port 8013)   │    │  (Port 8014)     │    └───────────────────┘
└─────────────────┘    └──────────────────┘              │
         │                        ▲                      │
         │ CSV Files              │ Events               ▼
         ▼                        │              ┌───────────────────┐
┌─────────────────┐              │              │  PostgreSQL       │
│ Data Processing │──────────────┘              │  Event-Store      │
│ Service (NEW)   │                             │ + NOTIFY/LISTEN   │
│   (Port 8017)   │                             └───────────────────┘
└─────────────────┘                                       │
         │                                                │
         ▼                                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   CSV Files     │    │ Event-Triggered  │    │ Enhanced Matviews │
│ - top15.csv     │    │ Update Mechanism │    │ + CSV Triggers    │
│ - soll_ist.csv  │    │ (NOTIFY/LISTEN)  │    │ + Performance     │
└─────────────────┘    └──────────────────┘    └───────────────────┘
```

---

## 📊 **DETAILLIERTE KOMMUNIKATIONSPFADE**

### **1. Event-Driven Data Flow**
```
Database Write → PostgreSQL NOTIFY → Data Processing Service → CSV Generation → Frontend Update
```

**Spezifikation:**
- **Trigger**: INSERT/UPDATE auf `events` Tabelle 
- **Event-Types**: `analysis.state.changed`, `portfolio.state.changed`, `trading.state.changed`
- **Response-Time**: <1s für CSV-Regeneration
- **Delivery**: Event-Bus garantierte Zustellung

### **2. Frontend → Data Processing Communication**
```
Frontend API Call → Data Processing Service → Materialized View Query → CSV Response
```

**API Endpoints:**
- `GET /api/v1/data/top15-predictions` → CSV mit Top 15 Aktien-Vorhersagen
- `GET /api/v1/data/soll-ist-vergleich` → CSV mit Soll-Ist-Vergleich Top 5
- `GET /api/v1/data/status` → Service Health & Letzte Updates
- `POST /api/v1/data/refresh` → Manuelle CSV-Regeneration

### **3. Event-Bus Integration Pattern**
```python
# Event-Bus-Compliance Pattern für Data Processing Service
event = Event(
    event_type=EventType.DATA_PROCESSING_REQUEST.value,
    stream_id=f"csv-generation-{timestamp}",
    data={
        "request_type": "generate_csv",
        "csv_type": "top15_predictions",
        "trigger": "database_update"
    },
    source="data-processing"
)
await self.event_bus.publish(event)
```

---

## 🛠️ **MIGRATIONS-IMPLEMENTIERUNG**

### **📁 Neue Dateistruktur**
```
services/data-processing-service-modular/
├── data_processing_orchestrator.py      # Hauptorchestrator
├── modules/
│   ├── csv_generator_module.py          # CSV-Generierung
│   ├── database_listener_module.py      # NOTIFY/LISTEN Handler
│   ├── performance_tracker_module.py    # Performance-Monitoring
│   └── cache_manager_module.py          # CSV-Cache Management
├── templates/
│   ├── top15_predictions.csv.template   # CSV-Templates
│   └── soll_ist_vergleich.csv.template  
├── output/
│   ├── top15_predictions.csv            # Generated CSV Files
│   └── soll_ist_vergleich.csv
└── requirements.txt
```

### **🗄️ Datenbank-Erweiterungen**

**1. Event-Store Schema Ergänzungen:**
```sql
-- CSV-Metadaten-Tabelle für Tracking
CREATE TABLE csv_generation_metadata (
    id SERIAL PRIMARY KEY,
    csv_type VARCHAR(100) NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    file_path VARCHAR(500) NOT NULL,
    row_count INTEGER NOT NULL,
    trigger_event_id UUID REFERENCES events(id),
    generation_duration_ms INTEGER,
    status VARCHAR(50) DEFAULT 'SUCCESS'
);

-- NOTIFY Trigger für Data Processing Updates
CREATE OR REPLACE FUNCTION notify_csv_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Nur bei relevanten Event-Types notifizieren
    IF NEW.event_type IN (
        'analysis.state.changed',
        'portfolio.state.changed', 
        'trading.state.changed'
    ) THEN
        PERFORM pg_notify(
            'csv_update_needed',
            json_build_object(
                'event_id', NEW.id,
                'event_type', NEW.event_type,
                'stream_id', NEW.stream_id,
                'timestamp', NEW.timestamp
            )::text
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger aktivieren
CREATE TRIGGER csv_update_notify_trigger
    AFTER INSERT ON events
    FOR EACH ROW
    EXECUTE FUNCTION notify_csv_update();
```

**2. Erweiterte Materialized Views:**
```sql
-- Spezielle View für Top 15 Predictions CSV
CREATE MATERIALIZED VIEW csv_top15_predictions AS
SELECT 
    symbol,
    latest_score,
    recommendation,
    confidence,
    target_price,
    -- Zeitraumspezifische Prognosen
    technical_indicators->'prediction_7d' as prediction_7d,
    technical_indicators->'prediction_14d' as prediction_14d,
    technical_indicators->'prediction_31d' as prediction_31d,
    technical_indicators->'prediction_6m' as prediction_6m,
    technical_indicators->'prediction_12m' as prediction_12m,
    last_updated
FROM stock_analysis_unified
ORDER BY latest_score DESC
LIMIT 15;

-- Spezielle View für Soll-Ist Vergleich CSV
CREATE MATERIALIZED VIEW csv_soll_ist_vergleich AS
SELECT 
    symbol,
    -- Soll-Werte (Prognosen)
    technical_indicators->'prediction_7d'->>'expected_return' as soll_7d,
    technical_indicators->'prediction_14d'->>'expected_return' as soll_14d,
    technical_indicators->'prediction_31d'->>'expected_return' as soll_31d,
    technical_indicators->'prediction_6m'->>'expected_return' as soll_6m,
    technical_indicators->'prediction_12m'->>'expected_return' as soll_12m,
    -- Ist-Werte (Tatsächliche Performance)
    total_return as ist_actual,
    sharpe_ratio,
    max_drawdown,
    volatility,
    -- Berechnete Abweichungen
    COALESCE(total_return, 0) - COALESCE((technical_indicators->'prediction_7d'->>'expected_return')::numeric, 0) as abweichung_7d,
    last_updated
FROM stock_analysis_unified
WHERE total_return IS NOT NULL
ORDER BY ABS(COALESCE(total_return, 0) - COALESCE((technical_indicators->'prediction_7d'->>'expected_return')::numeric, 0))
LIMIT 5;
```

---

## 🔧 **DETAILLIERTE SERVICE-IMPLEMENTIERUNG**

### **Data Processing Service Orchestrator:**
```python
# data_processing_orchestrator.py
from shared import ModularService, DatabaseMixin, EventBusMixin
from shared.event_bus import EventBusConnector, Event, EventType

class DataProcessingService(ModularService, DatabaseMixin, EventBusMixin):
    """
    Data Processing Service für CSV-Generierung und Event-triggered Updates
    Folgt dem etablierten Event-Store Pattern
    """
    
    def __init__(self):
        super().__init__(
            service_name="data-processing",
            version="1.0.0", 
            port=8017
        )
        
        # Module Setup
        self.csv_generator = None
        self.db_listener = None
        self.performance_tracker = None
        self.cache_manager = None
        
        # CSV-Ausgabepfade
        self.csv_output_dir = "/home/mdoehler/aktienanalyse-ökosystem/services/data-processing-service-modular/output"
        
    async def _setup_service(self):
        """Service-spezifische Initialisierung"""
        # Database Connections (Inherited from DatabaseMixin)
        await self.setup_postgres()
        await self.setup_redis()
        
        # Event-Bus Connection (Inherited from EventBusMixin)
        await self.setup_event_bus("data-processing")
        
        # Initialize Modules
        await self._initialize_modules()
        
        # Setup API Routes
        self._setup_api_routes()
        
        # Setup Database NOTIFY Listener
        await self._setup_notify_listener()
        
        self.logger.info("Data Processing Service fully initialized")
```

---

## 🎨 **FRONTEND INTEGRATION**

### **Erweiterte Frontend-Service APIs:**
```python
# frontend_service_v2.py - Ergänzung für CSV-Integration

# Neue Route für CSV-Daten
@app.get("/api/frontend/csv-data/{data_type}")
async def get_csv_data(data_type: str):
    """Proxy für CSV-Daten vom Data Processing Service"""
    try:
        # Event-Bus-Compliance: Request via Event-Bus
        request_event = Event(
            event_type=EventType.DASHBOARD_REQUEST.value,
            stream_id=f"csv-request-{data_type}-{int(time.time())}",
            data={
                "request_type": "csv_data",
                "data_type": data_type,
                "source": "frontend_gui"
            },
            source="frontend"
        )
        await event_bus.publish(request_event)
        
        # Direct API call als Fallback
        data_processing_url = f"http://localhost:8017/api/v1/data/{data_type}"
        async with httpx.AsyncClient() as client:
            response = await client.get(data_processing_url)
            
        return Response(
            content=response.content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={data_type}.csv"}
        )
        
    except Exception as e:
        logger.error(f"CSV data error for {data_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### **GUI-Modernisierung (4-Funktionen-Struktur):**
```html
<!-- Neue index.html mit vereinfachter 4-Funktionen-Struktur -->
<nav class="sidebar">
  <ul class="nav nav-pills flex-column">
    <li class="nav-item">
      <a class="nav-link" id="gewinnprognose-tab">
        <i class="fas fa-chart-line"></i> Gewinnprognose
      </a>
    </li>
    <li class="nav-item">
      <a class="nav-link" id="soll-ist-tab">
        <i class="fas fa-balance-scale"></i> Soll-Ist Vergleich  
      </a>
    </li>
    <li class="nav-item">
      <a class="nav-link" id="depot-tab">
        <i class="fas fa-wallet"></i> Depot-Verwaltung
      </a>
    </li>
    <li class="nav-item">
      <a class="nav-link" id="admin-tab">
        <i class="fas fa-cog"></i> Setup/Admin/Status
      </a>
    </li>
  </ul>
</nav>

<script>
// Real-Time CSV Update Handler
const csvWebSocket = new WebSocket('ws://localhost:8013/ws/csv-updates');

csvWebSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'csv_updated') {
        // Show notification
        showNotification('CSV-Daten wurden aktualisiert', 'success');
        
        // Auto-refresh aktive Tabelle
        if (data.update_type === 'csv_regeneration') {
            refreshActiveTable();
        }
    }
};
</script>
```

---

## 📈 **PERFORMANCE & MONITORING**

### **Performance-Ziele:**
- **CSV-Generierung**: <1s für beide CSV-Dateien
- **Database-Query**: <0.12s (bestehende Materialized View Performance beibehalten)
- **Event-Processing**: <100ms für Event-Bus-Nachrichten
- **API-Response**: <500ms für CSV-Download-Endpoints

### **Monitoring-Integration:**
```python
# performance_tracker_module.py
class PerformanceTrackerModule(BackendBaseModule):
    """Performance-Tracking für CSV-Generierung"""
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("performance-tracker", event_bus)
        self.generation_times = []
        self.error_counts = defaultdict(int)
    
    async def track_csv_generation(self, csv_type: str, start_time: float, end_time: float, success: bool):
        """Track CSV-Generierungsperformance"""
        duration = end_time - start_time
        
        # Event-Bus-Compliance: Publish Performance Metrics
        perf_event = Event(
            event_type=EventType.SYSTEM_ALERT_RAISED.value if duration > 1.0 else EventType.DATA_SYNCHRONIZED.value,
            stream_id=f"perf-{csv_type}-{int(time.time())}",
            data={
                "csv_type": csv_type,
                "generation_duration_ms": duration * 1000,
                "success": success,
                "alert_type": "performance" if duration > 1.0 else "metrics",
                "severity": "WARNING" if duration > 1.0 else "INFO"
            },
            source="performance-tracker"
        )
        await self.event_bus.publish(perf_event)
```

---

## 🧪 **TESTING-STRATEGIE**

### **Integration Tests:**
```python
# tests/integration/test_data_processing_integration.py
class TestDataProcessingIntegration:
    """Integration Tests für Data Processing Service"""
    
    @pytest.mark.asyncio
    async def test_event_triggered_csv_update(self):
        """Test Event-triggered CSV Update Flow"""
        # 1. Insert analysis event in database
        event_id = await append_event(
            'stock-TSLA',
            'stock',
            'analysis.state.changed',
            {'symbol': 'TSLA', 'score': 19.2, 'state': 'completed'}
        )
        
        # 2. Wait für NOTIFY trigger
        await asyncio.sleep(0.5)
        
        # 3. Verify CSV regeneration
        top15_path = "/home/mdoehler/aktienanalyse-ökosystem/services/data-processing-service-modular/output/top15_predictions.csv"
        assert os.path.exists(top15_path)
        
        # 4. Verify CSV content
        with open(top15_path, 'r') as f:
            content = f.read()
            assert 'TSLA' in content
            assert '19.2' in content
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """Test Performance-Anforderungen"""
        start_time = time.time()
        
        # Trigger CSV generation
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8017/api/v1/data/top15-predictions")
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Assert <1s generation time
        assert generation_time < 1.0, f"CSV generation took {generation_time:.2f}s, expected <1s"
        assert response.status_code == 200
```

---

## 🚀 **DEPLOYMENT-PLAN**

### **Deployment-Reihenfolge:**
1. **Database Migration**: Erweiterte Schema-Implementierung
2. **Data Processing Service**: Service-Deployment auf Port 8017
3. **Frontend-Service Update**: CSV-API-Integration
4. **Event-Bus Configuration**: Routing-Rules für neue Events
5. **systemd Service**: Automatischer Service-Start
6. **Integration Testing**: End-to-End-Tests
7. **Performance Validation**: <0.12s Query-Zeit-Validierung

### **systemd Service Configuration:**
```ini
# /etc/systemd/system/aktienanalyse-data-processing.service
[Unit]
Description=Aktienanalyse Data Processing Service
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=mdoehler
Group=mdoehler
WorkingDirectory=/home/mdoehler/aktienanalyse-ökosystem/services/data-processing-service-modular
Environment=PYTHONPATH=/home/mdoehler/aktienanalyse-ökosystem
ExecStart=/usr/bin/python3 data_processing_orchestrator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## ✅ **ERFOLGS-KRITERIEN**

### **Funktionale Anforderungen:**
- ✅ **CSV-Generierung**: Top 15 Aktien-Vorhersagen + Top 5 Soll-Ist-Vergleich
- ✅ **Event-Triggered Updates**: Database-Write triggert automatische CSV-Updates
- ✅ **API Integration**: Frontend kann CSV-Daten über REST-APIs abrufen
- ✅ **Real-Time Updates**: WebSocket-basierte Update-Benachrichtigungen

### **Nicht-Funktionale Anforderungen:**
- ✅ **Performance**: <1s CSV-Generierung, <0.12s Database-Queries
- ✅ **Skalierbarkeit**: Event-Store-Pattern unterstützt horizontal Scaling
- ✅ **Maintainability**: Shared Libraries Pattern reduziert Code-Duplikation
- ✅ **Observability**: Full Event-Bus-Compliance für Monitoring

### **Architektur-Compliance:**
- ✅ **Event-Store Pattern**: Native Integration in bestehende Event-Store-Architektur
- ✅ **Event-Bus-Compliance**: Alle Kommunikation über Event-Bus
- ✅ **Single Function Module Pattern**: Modulare Service-Struktur
- ✅ **Code-Qualität**: Shared Libraries eliminieren Duplikation

---

## 🔗 **KOMMUNIKATIONSPFADE ÜBERSICHT**

### **📋 MODUL-KOMMUNIKATIONS-MATRIX**

| **Von/Nach** | Frontend | Data-Processing | Intelligent-Core | Broker-Gateway | Event-Bus | PostgreSQL |
|--------------|----------|-----------------|------------------|----------------|-----------|------------|
| **Frontend** | - | CSV-APIs | Event-Bus | Event-Bus | Pub/Sub | - |
| **Data-Processing** | CSV-Response | Internal | Event-Listen | - | Pub/Sub | NOTIFY/LISTEN + Query |
| **Intelligent-Core** | Event-Bus | Event-Trigger | - | - | Pub/Sub | Event-Store |
| **Broker-Gateway** | Event-Bus | - | Event-Bus | - | Pub/Sub | Event-Store |
| **Event-Bus** | WebSocket | Events | Events | Events | - | - |
| **PostgreSQL** | - | Notifications | Event-Store | Event-Store | - | - |

### **🔄 CSV-GENERIERUNG WORKFLOW**
```
Intelligent-Core → PostgreSQL (INSERT event) → TRIGGER notify_csv_update() → 
Data-Processing (NOTIFY receive) → CSV Generation → Event-Bus (DATA_SYNCHRONIZED) → 
Frontend (WebSocket notification) → User Interface Update
```

### **📊 API-KOMMUNIKATION**
```
Frontend → GET /api/frontend/csv-data/{type} → Data Processing Service → 
PostgreSQL (Materialized View Query) → CSV File Response → Frontend Download
```

---

## 🏁 **ZUSAMMENFASSUNG**

**Status**: Vollständiger Migrations- und Implementierungsplan erstellt ✅

**Kernerkenntnisse:**
- Bestehende Architektur ist **hochwertig** und **Event-Store-ready**
- **Erweiterte Integration** ist der optimale Ansatz
- **Performance-Ziele** sind durch Materialized Views erreichbar
- **Event-Bus-Compliance** ist bereits etabliert

**Implementierungszeit**: 7-10 Tage für vollständige Integration

**Architektur-Bewertung**: Das System folgt **höchsten Code-Qualitäts-Standards** und ist **produktionsbereit** für die Data Processing Service Erweiterung.