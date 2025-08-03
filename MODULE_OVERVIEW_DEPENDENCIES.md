# 📋 Modulare Frontend-Architektur - Übersicht & Abhängigkeiten

## 🏗️ **Architektur-Übersicht**

```
Modulares Frontend-Service (Port 8005)
├── 🎯 Frontend Service Orchestrator
├── 📦 6 Spezialisierte Module
├── 🔄 Event-Bus Integration
└── 🌐 REST API + WebSocket Support
```

---

## 📦 **Module-Katalog**

### **1. 📊 Dashboard Module**
**Datei**: `modules/dashboard_module.py`  
**Zweck**: Live-Metriken und System-Übersicht  
**Port/Service**: Intern (über Event-Bus)

#### **Kernfunktionen**
- 📈 Portfolio-Wert-Aggregation
- 🔥 Live-System-Health-Display
- 📅 Tagesänderungen und Performance-Tracking
- 🚨 Alert-Management und Benachrichtigungen
- 📊 Dashboard-Metriken-Sammlung

#### **API-Endpoints**
```http
GET  /api/content/dashboard     # Dashboard-Daten abrufen
POST /api/actions/dashboard     # Dashboard-Aktionen ausführen
```

#### **Event-Abhängigkeiten** (EINGEHEND)
```yaml
PORTFOLIO_PERFORMANCE_UPDATED:
  - Quelle: Portfolio Module, Backend Services
  - Zweck: Portfolio-Wert-Updates für Dashboard

ANALYSIS_STATE_CHANGED:
  - Quelle: Intelligent Core Service
  - Zweck: Analyse-Status für Dashboard

TRADING_STATE_CHANGED:
  - Quelle: Trading Module, Broker Gateway
  - Zweck: Trading-Status für Dashboard

SYSTEM_ALERT_RAISED:
  - Quelle: Monitoring Module, Alle Services
  - Zweck: System-Alerts anzeigen

DATA_SYNCHRONIZED:
  - Quelle: Event-Bus Service
  - Zweck: Daten-Synchronisation bestätigen
```

#### **Event-Publizierung** (AUSGEHEND)
```yaml
USER_INTERACTION_LOGGED:
  - Trigger: Dashboard-Aktionen
  - Ziel: Monitoring Module, API Gateway
```

---

### **2. 📈 Market Data Module**
**Datei**: `modules/market_data_module.py`  
**Zweck**: Marktdaten-Management und Watchlist  
**Port/Service**: Intern (über Event-Bus)

#### **Kernfunktionen**
- 📋 Watchlist-Management (hinzufügen/entfernen)
- 💰 Echtzeit-Kurse und Market-Updates
- 🏷️ Symbol-Management und Suche
- 💾 Marktdaten-Caching und -Optimierung
- 📊 Technische Indikatoren-Integration

#### **API-Endpoints**
```http
GET  /api/content/market-data   # Marktdaten und Watchlist
POST /api/actions/market-data   # Watchlist-Management
```

#### **Event-Abhängigkeiten** (EINGEHEND)
```yaml
ANALYSIS_STATE_CHANGED:
  - Quelle: Intelligent Core Service
  - Zweck: Analyse-Updates für Marktdaten

DATA_SYNCHRONIZED:
  - Quelle: Event-Bus Service
  - Zweck: Marktdaten-Synchronisation

INTELLIGENCE_TRIGGERED:
  - Quelle: Intelligent Core Service
  - Zweck: KI-basierte Marktdaten-Empfehlungen

CONFIG_UPDATED:
  - Quelle: Frontend Service, Admin
  - Zweck: Konfiguration für Data-Sources
```

#### **Event-Publizierung** (AUSGEHEND)
```yaml
DATA_SYNCHRONIZED:
  - Trigger: Marktdaten-Updates
  - Ziel: Dashboard Module, Portfolio Module

USER_INTERACTION_LOGGED:
  - Trigger: Watchlist-Änderungen
  - Ziel: Monitoring Module
```

---

### **3. 💼 Portfolio Module**
**Datei**: `modules/portfolio_module.py`  
**Zweck**: Portfolio-Management und Performance-Tracking  
**Port/Service**: Intern (über Event-Bus)

#### **Kernfunktionen**
- 📊 Positionen-Management und -Übersicht
- 📈 Performance-Berechnung (1D, 7D, 30D, YTD)
- ⚠️ Risk-Metriken und Volatilitäts-Analyse
- 🔄 Rebalancing-Vorschläge und -Simulation
- 💰 P&L-Tracking und Reporting

#### **API-Endpoints**
```http
GET  /api/content/portfolio     # Portfolio-Daten und Positionen
POST /api/actions/portfolio     # Portfolio-Aktionen
```

#### **Event-Abhängigkeiten** (EINGEHEND)
```yaml
TRADING_STATE_CHANGED:
  - Quelle: Trading Module, Broker Gateway
  - Zweck: Position-Updates nach Trades

ANALYSIS_STATE_CHANGED:
  - Quelle: Intelligent Core Service
  - Zweck: Analyse-Updates für Portfolio

DATA_SYNCHRONIZED:
  - Quelle: Event-Bus Service
  - Zweck: Portfolio-Daten-Synchronisation

INTELLIGENCE_TRIGGERED:
  - Quelle: Intelligent Core Service
  - Zweck: KI-basierte Portfolio-Empfehlungen
```

#### **Event-Publizierung** (AUSGEHEND)
```yaml
PORTFOLIO_PERFORMANCE_UPDATED:
  - Trigger: Performance-Berechnungen
  - Ziel: Dashboard Module, Monitoring Module

USER_INTERACTION_LOGGED:
  - Trigger: Portfolio-Änderungen
  - Ziel: Monitoring Module
```

---

### **4. 🔄 Trading Module**
**Datei**: `modules/trading_module.py`  
**Zweck**: Order-Management und Auto-Trading  
**Port/Service**: Intern (über Event-Bus)

#### **Kernfunktionen**
- 📝 Order-Erstellung und -Verwaltung
- ⚡ Auto-Trading-Strategien und -Ausführung
- 🛡️ Risk-Management und Position-Sizing
- 📊 Trade-History und -Analytics
- 🔄 Order-Status-Tracking

#### **API-Endpoints**
```http
GET  /api/content/trading       # Trading-Daten und Orders
POST /api/actions/trading       # Order-Management
```

#### **Event-Abhängigkeiten** (EINGEHEND)
```yaml
INTELLIGENCE_TRIGGERED:
  - Quelle: Intelligent Core Service
  - Zweck: KI-basierte Trading-Signale

ANALYSIS_STATE_CHANGED:
  - Quelle: Intelligent Core Service
  - Zweck: Analyse-Updates für Trading

DATA_SYNCHRONIZED:
  - Quelle: Event-Bus Service
  - Zweck: Trading-Daten-Synchronisation

TRADING_STATE_CHANGED:
  - Quelle: Broker Gateway Service
  - Zweck: Order-Status-Updates
```

#### **Event-Publizierung** (AUSGEHEND)
```yaml
TRADING_STATE_CHANGED:
  - Trigger: Order-Ausführung
  - Ziel: Portfolio Module, Dashboard Module

USER_INTERACTION_LOGGED:
  - Trigger: Manual Trading-Aktionen
  - Ziel: Monitoring Module
```

---

### **5. 🖥️ Monitoring Module**
**Datei**: `modules/monitoring_module.py`  
**Zweck**: System-Monitoring und Health-Checks  
**Port/Service**: Intern (über Event-Bus)

#### **Kernfunktionen**
- 📊 System-Metriken-Sammlung (CPU, Memory, Disk)
- 🏥 Health-Checks für alle Services
- ⚡ Performance-Monitoring und -Alerting
- 📋 Log-Aggregation und -Analyse
- 🚨 Alert-Management und Notifications

#### **API-Endpoints**
```http
GET  /api/content/monitoring    # System-Metriken und Health
POST /api/actions/monitoring    # Monitoring-Aktionen
```

#### **Event-Abhängigkeiten** (EINGEHEND)
```yaml
SYSTEM_ALERT_RAISED:
  - Quelle: Alle Services
  - Zweck: System-Alerts sammeln

DATA_SYNCHRONIZED:
  - Quelle: Event-Bus Service
  - Zweck: Monitoring-Daten-Sync

TRADING_STATE_CHANGED:
  - Quelle: Trading Module
  - Zweck: Trading-Performance-Monitoring

ANALYSIS_STATE_CHANGED:
  - Quelle: Intelligent Core Service
  - Zweck: Analysis-Performance-Monitoring

PORTFOLIO_PERFORMANCE_UPDATED:
  - Quelle: Portfolio Module
  - Zweck: Portfolio-Performance-Tracking
```

#### **Event-Publizierung** (AUSGEHEND)
```yaml
SYSTEM_ALERT_RAISED:
  - Trigger: Health-Check-Failures
  - Ziel: Dashboard Module, API Gateway

DATA_SYNCHRONIZED:
  - Trigger: Monitoring-Daten-Updates
  - Ziel: Dashboard Module
```

---

### **6. 🚪 API Gateway Module**
**Datei**: `modules/api_gateway_module.py`  
**Zweck**: API-Routing und Service-Integration  
**Port/Service**: Intern (über Event-Bus)

#### **Kernfunktionen**
- 🔄 Request-Routing zu Backend-Services
- ⏱️ Rate-Limiting und Throttling
- 🏛️ Service-Registry und Discovery
- 💾 Response-Caching und Optimization
- 📊 API-Statistics und Performance-Tracking

#### **API-Endpoints**
```http
GET  /api/content/api           # Gateway-Statistiken
POST /api/actions/api           # Gateway-Management

# Proxy-Endpoints
GET  /api/proxy/intelligent-core
GET  /api/proxy/broker-gateway
GET  /api/proxy/monitoring
```

#### **Event-Abhängigkeiten** (EINGEHEND)
```yaml
USER_INTERACTION_LOGGED:
  - Quelle: Alle Module
  - Zweck: API-Usage-Tracking

CONFIG_UPDATED:
  - Quelle: Frontend Service
  - Zweck: Gateway-Konfiguration-Updates

SYSTEM_ALERT_RAISED:
  - Quelle: Backend Services
  - Zweck: Service-Health-Tracking
```

#### **Event-Publizierung** (AUSGEHEND)
```yaml
USER_INTERACTION_LOGGED:
  - Trigger: API-Requests
  - Ziel: Monitoring Module

SYSTEM_ALERT_RAISED:
  - Trigger: Service-Failures
  - Ziel: Monitoring Module, Dashboard Module
```

---

## 🔄 **Event-Flow-Matrix**

| Event Type | Publisher | Subscribers | Zweck |
|------------|-----------|-------------|--------|
| `PORTFOLIO_PERFORMANCE_UPDATED` | Portfolio Module | Dashboard, Monitoring | Portfolio-Updates |
| `ANALYSIS_STATE_CHANGED` | Intelligent Core | Dashboard, Market Data, Portfolio, Trading, Monitoring | Analyse-Updates |
| `TRADING_STATE_CHANGED` | Trading Module, Broker Gateway | Dashboard, Portfolio, Monitoring | Trading-Updates |
| `INTELLIGENCE_TRIGGERED` | Intelligent Core | Market Data, Portfolio, Trading | KI-Empfehlungen |
| `DATA_SYNCHRONIZED` | Event-Bus Service | Alle Module | Daten-Sync |
| `SYSTEM_ALERT_RAISED` | Monitoring, Alle Services | Dashboard, API Gateway | System-Alerts |
| `USER_INTERACTION_LOGGED` | Alle Module | Monitoring, API Gateway | User-Tracking |
| `CONFIG_UPDATED` | Frontend Service | Market Data, API Gateway | Konfiguration |

---

## 📁 **Datei-Struktur & Abhängigkeiten**

### **Core-Infrastructure**
```
core/
├── base_module.py              # Basis-Klasse für alle Module
│   ├── 🔄 Event-Bus-Integration
│   ├── 📝 Standard-Module-Interface
│   ├── 🏥 Health-Check-Framework
│   └── 📊 Logging und Monitoring
```

### **Module-Files**
```
modules/
├── dashboard_module.py         # 550 Zeilen
│   ├── 📊 Dashboard-Metriken
│   ├── 📈 Performance-Aggregation
│   └── 🚨 Alert-Management
│
├── market_data_module.py       # 480 Zeilen
│   ├── 📋 Watchlist-Management
│   ├── 💰 Echtzeit-Kurse
│   └── 💾 Data-Caching
│
├── portfolio_module.py         # 520 Zeilen
│   ├── 📊 Positionen-Management
│   ├── 📈 Performance-Berechnung
│   └── ⚠️ Risk-Management
│
├── trading_module.py           # 580 Zeilen
│   ├── 📝 Order-Management
│   ├── ⚡ Auto-Trading
│   └── 🛡️ Risk-Controls
│
├── monitoring_module.py        # 450 Zeilen
│   ├── 📊 System-Metriken
│   ├── 🏥 Health-Checks
│   └── 🚨 Alerting
│
└── api_gateway_module.py       # 645 Zeilen
    ├── 🔄 Request-Routing
    ├── ⏱️ Rate-Limiting
    └── 💾 Response-Caching
```

### **Service-Orchestrator**
```
frontend_service_modular.py     # 475 Zeilen
├── 🎯 FastAPI-Application
├── 📦 Module-Registry-Management
├── 🔄 Event-Bus-Orchestration
├── 🌐 REST-API-Endpoints
└── 🚀 Service-Lifecycle-Management
```

### **Frontend-Templates**
```
templates/
└── dashboard.html              # 505 Zeilen
    ├── 🎨 Bootstrap 5 UI
    ├── 📱 Responsive Design
    ├── ⚡ Real-time Updates
    └── 🔄 WebSocket-Integration
```

---

## 🔗 **Service-Abhängigkeiten**

### **Externe Service-Abhängigkeiten**
```yaml
Intelligent Core Service (Port 8001):
  - Events: ANALYSIS_STATE_CHANGED, INTELLIGENCE_TRIGGERED
  - HTTP API: /api/analysis, /api/intelligence

Broker Gateway Service (Port 8002):
  - Events: TRADING_STATE_CHANGED
  - HTTP API: /api/orders, /api/trades

Event-Bus Service (Port 8003):
  - Events: Alle Event-Types
  - HTTP API: /api/events, /api/subscriptions

Monitoring Service (Port 8004):
  - Events: SYSTEM_ALERT_RAISED
  - HTTP API: /api/metrics, /api/health
```

### **Infrastructure-Abhängigkeiten**
```yaml
Python-Packages:
  - fastapi>=0.104.1
  - uvicorn[standard]>=0.24.0
  - structlog>=23.2.0
  - psutil>=5.9.6
  - aiofiles>=23.2.1

Event-Bus:
  - Redis: Event-Pub/Sub und Caching
  - RabbitMQ: Message-Queue (optional)

Web-Server:
  - NGINX: Reverse-Proxy (Port 443 → 8005)
  - SSL/TLS: Automatische Zertifikate

System:
  - systemd: Service-Management
  - Linux: LXC-Container-Umgebung
```

---

## 📊 **Komplexitäts-Analyse**

### **Modul-Komplexität**
| Modul | Zeilen | Funktionen | Events | Komplexität |
|-------|--------|------------|--------|-------------|
| Dashboard | 550 | 12 | 5 | Mittel |
| Market Data | 480 | 10 | 4 | Niedrig |
| Portfolio | 520 | 14 | 4 | Mittel |
| Trading | 580 | 16 | 4 | Hoch |
| Monitoring | 450 | 11 | 5 | Niedrig |
| API Gateway | 645 | 18 | 3 | Hoch |

### **Event-Kopplung**
```yaml
Stark gekoppelt:
  - Dashboard Module (5 eingehende Events)
  - Monitoring Module (5 eingehende Events)

Moderat gekoppelt:
  - Portfolio Module (4 eingehende Events)
  - Market Data Module (4 eingehende Events)
  - Trading Module (4 eingehende Events)

Schwach gekoppelt:
  - API Gateway Module (3 eingehende Events)
```

### **Performance-Charakteristika**
```yaml
Hochfrequent:
  - Market Data Module (Echtzeit-Updates)
  - Monitoring Module (System-Metriken)

Normalfrequent:
  - Dashboard Module (Dashboard-Updates)
  - Portfolio Module (Performance-Berechnung)

Niedrigfrequent:
  - Trading Module (Order-Ausführung)
  - API Gateway Module (Proxy-Requests)
```

---

## 🎯 **Architektur-Qualität**

### **Modularität** ✅
- ✅ Klare Verantwortungstrennung
- ✅ Lose Kopplung über Events
- ✅ Hohe Kohäsion in Modulen
- ✅ Einfache Testbarkeit

### **Skalierbarkeit** ✅
- ✅ Event-driven Architecture
- ✅ Asynchrone Verarbeitung
- ✅ Caching-Strategien
- ✅ Load-balancing-ready

### **Wartbarkeit** ✅
- ✅ Ein File pro Modul
- ✅ Standardisierte Interfaces
- ✅ Umfassendes Logging
- ✅ Health-Monitoring

### **Sicherheit** ✅
- ✅ HTTPS-Only-Zugang
- ✅ Input-Validation
- ✅ Rate-Limiting
- ✅ Error-Handling

---

**Dokument-Version**: 1.0  
**Letzte Aktualisierung**: 2025-08-03  
**Deployment-Status**: 🚀 Produktiv auf 10.1.1.174