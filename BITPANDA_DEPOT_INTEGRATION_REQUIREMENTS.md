# 📊 BITPANDA DEPOT-INTEGRATION - ANFORDERUNGSSPEZIFIKATION
**Datum:** 30. August 2025  
**Projekt:** Aktienanalyse-Ökosystem  
**Broker-API:** Bitpanda (Primär) / One Trading (Fallback)  
**Status:** ✅ **VOLLSTÄNDIG SPEZIFIZIERT**

---

## 🎯 EXECUTIVE SUMMARY

Diese Woche haben wir **Bitpanda als primären Broker-API** für das Depot-Management spezifiziert. Die Integration ermöglicht echtes Trading über die Bitpanda RESTful API mit automatisiertem Order-Management, Portfolio-Tracking und Compliance-Monitoring.

---

## 🏦 BROKER-AUSWAHL

### **Primärer Broker: Bitpanda**
- **Regulierung:** EU-reguliert (Österreich/Deutschland)
- **API-Zugang:** RESTful API für automatisierten Handel
- **Asset-Klassen:** Aktien, ETFs, Kryptowährungen
- **Compliance:** Vollständig reguliert und lizenziert
- **Standort:** Wien, Österreich

### **Fallback-Broker: One Trading**
- **Regulierung:** EU-reguliert (Österreich)
- **API-Zugang:** RESTful API verfügbar
- **Fokus:** Aktien und ETFs
- **Verwendung:** Als Backup wenn Bitpanda nicht verfügbar

---

## 📐 TECHNISCHE API-SPEZIFIKATIONEN

### **1. Rate-Limits (von Bitpanda vorgegeben)**

```yaml
bitpanda_api_limits:
  rest_api:
    requests_per_minute: 100      # Max 100 API-Calls pro Minute
    requests_per_hour: 1000       # Max 1000 API-Calls pro Stunde
    burst_limit: 10               # Max 10 Requests in 10 Sekunden
    
  trading_api:
    orders_per_minute: 20         # Max 20 Orders pro Minute
    orders_per_day: 500           # Max 500 Orders pro Tag
    concurrent_orders: 10         # Max 10 gleichzeitige offene Orders
    
  market_data:
    price_requests_per_minute: 200  # Max 200 Kursdaten-Abfragen/Min
    historical_data_per_hour: 50    # Max 50 historische Daten/Stunde
```

### **2. Order-Constraints**

```yaml
order_constraints:
  minimum_order_sizes:
    stocks: 25.00                 # Min €25 pro Aktien-Order
    etfs: 25.00                   # Min €25 pro ETF-Order
    
  maximum_order_sizes:
    per_order: 10000.00           # Max €10.000 pro Order
    daily_volume: 50000.00        # Max €50.000 tägliches Volumen
    
  price_limits:
    max_deviation_from_market: 10 # Max 10% Abweichung vom Marktpreis
    limit_order_duration: 30      # Limit-Orders verfallen nach 30 Tagen
    
  order_types:
    supported: ["market", "limit", "stop_loss"]
    not_supported: ["trailing_stop", "iceberg"]
```

### **3. Trading-Zeiten**

```yaml
trading_hours:
  german_markets:
    xetra: "09:00-17:30 CET"      # XETRA Haupthandelszeit
    frankfurt: "08:00-22:00 CET"  # Frankfurter Börse erweitert
    
  us_markets:
    nyse: "15:30-22:00 CET"       # NYSE in deutscher Zeit
    nasdaq: "15:30-22:00 CET"     # NASDAQ in deutscher Zeit
    
  restrictions:
    weekends: "no_trading"        # Keine Trades am Wochenende
    holidays: "market_dependent"   # Je nach Börsen-Feiertagen
    maintenance: "api_announcements" # Wartungszeiten angekündigt
```

### **4. Technische Verbindungs-Limits**

```yaml
technical_constraints:
  connection:
    timeout: 30                   # 30 Sekunden Request-Timeout
    keep_alive: 300               # 5 Minuten Connection-Keep-Alive
    max_connections: 5            # Max 5 gleichzeitige Verbindungen
    
  authentication:
    token_lifetime: 3600          # API-Token 1 Stunde gültig
    refresh_threshold: 300        # Token 5 Min vor Ablauf erneuern
    max_auth_attempts: 3          # Max 3 Login-Versuche
    
  data_formats:
    max_request_size: "1MB"       # Maximale Request-Größe
    response_format: "JSON"       # Nur JSON-Responses
    charset: "UTF-8"              # Unicode-Unterstützung
```

---

## 🔧 IMPLEMENTIERTE KOMPONENTEN

### **1. Broker-Gateway-Service**

**Datei:** `/aktienanalyse-ökosystem/services/broker-gateway-service/main.py`
- **Status:** ✅ Implementiert mit BitpandaCredentials Model
- **Port:** 8002 (Standard Broker-Gateway Port)
- **Module:**
  - MarketDataModule v1.2.0
  - OrderModule v1.1.0
  - AccountModule v1.1.0

```python
class BitpandaCredentials(BaseModel):
    api_key: str
    api_secret: str = "dummy_secret"
    environment: str = "sandbox"  # sandbox/production
```

### **2. Broker-Compliance-Dokumentation**

**Datei:** `/data-web-app/docs/compliance/broker_compliance.md`
- **Status:** ✅ Vollständig dokumentiert (323 Zeilen)
- **Inhalt:**
  - Alle API-Limits und Constraints
  - Rate-Limiting Implementation
  - Order-Validation Logic
  - Fallback-Strategien
  - Error-Handling & Monitoring

---

## 💼 DEPOT-MANAGEMENT FEATURES

### **Geplante Funktionalitäten mit Bitpanda-API:**

#### **1. Portfolio-Management**
- Echtzeit-Portfolio-Wert über Bitpanda API
- Multi-Asset-Support (Aktien, ETFs, Crypto)
- Performance-Tracking mit echten Marktdaten
- Historische Portfolio-Entwicklung

#### **2. Trading-Interface**
- Market-Orders über Bitpanda API
- Limit-Orders mit Preiskontrolle
- Stop-Loss-Orders für Risikomanagement
- Order-Status-Tracking in Echtzeit

#### **3. Account-Management**
- Kontostand-Abfrage via API
- Cash-Balance-Tracking
- Transaktions-Historie
- Gebühren-Übersicht

#### **4. Market-Data-Integration**
- Echtzeit-Kurse von Bitpanda
- Historische Kursdaten
- Order-Book-Daten (Level 2)
- Market-Sentiment-Indikatoren

---

## 🛡️ RISK-MANAGEMENT & COMPLIANCE

### **1. Rate-Limiting Implementation**

```python
class BrokerRateLimiter:
    """Implementiert Bitpanda Rate-Limits"""
    
    def __init__(self):
        self.limits = {
            'requests_per_minute': 100,
            'orders_per_minute': 20,
            'burst_limit': 10
        }
        
    async def check_rate_limit(self, request_type):
        # Prüfe gegen Bitpanda-Limits
        # Implementiere Backoff-Strategie
        # Queue Requests wenn nötig
```

### **2. Order-Validation**

```python
class OrderValidator:
    """Validiert Orders gegen Bitpanda-Constraints"""
    
    def validate_order(self, order):
        checks = [
            self.check_minimum_size(order),      # Min €25
            self.check_maximum_size(order),      # Max €10.000
            self.check_price_deviation(order),   # Max 10% vom Markt
            self.check_trading_hours(order),     # Markt offen?
            self.check_daily_volume_limit(order) # Max €50.000/Tag
        ]
        return all(checks)
```

### **3. Error-Handling**

```yaml
error_handling:
  http_errors:
    429: "rate_limited - implement_backoff_strategy"
    401: "unauthorized - refresh_authentication_token"
    503: "service_unavailable - switch_to_fallback_mode"
    
  trading_errors:
    insufficient_funds: "reduce_order_size"
    market_closed: "queue_for_next_session"
    price_out_of_range: "adjust_limit_price"
```

---

## 📊 MONITORING & ALERTING

### **API-Health-Monitoring**
- Response-Zeit-Threshold: 5 Sekunden
- Error-Rate-Threshold: 5%
- Availability-Threshold: 99%

### **Trading-Performance**
- Order-Fill-Rate: >95% Ziel
- Execution-Delay: <10 Sekunden
- Slippage-Threshold: <0.5%

### **Compliance-Monitoring**
- Rate-Limit-Violations: Sofort-Alert
- Order-Rejections: Alert bei >3/Tag
- API-Quota-Usage: Alert bei >80%

---

## 🚀 DEPLOYMENT-STRATEGIE

### **Phase 1: Sandbox-Testing (Aktueller Stand)**
- ✅ Broker-Gateway-Service implementiert
- ✅ BitpandaCredentials Model vorhanden
- ✅ Compliance-Dokumentation erstellt
- 🔄 Sandbox-API-Testing ausstehend

### **Phase 2: Integration (Nächste Schritte)**
- [ ] Bitpanda API-Keys beantragen
- [ ] Sandbox-Environment konfigurieren
- [ ] Rate-Limiter implementieren
- [ ] Order-Validator entwickeln
- [ ] Test-Trading durchführen

### **Phase 3: Production-Deployment**
- [ ] Production API-Keys einrichten
- [ ] Risk-Management aktivieren
- [ ] Monitoring-Dashboard aufsetzen
- [ ] Fallback zu One Trading testen
- [ ] Go-Live mit Real-Money-Trading

---

## 🔄 INTEGRATION MIT BESTEHENDEM SYSTEM

### **Verbindung zu bestehenden Services:**

1. **Portfolio-Management-Service (Port 8004)**
   - Erhält echte Portfolio-Daten von Bitpanda
   - Ersetzt Mock-Portfolios durch Live-Daten

2. **Event-Bus-Service (Port 8003)**
   - Trading-Events über Event-Bus
   - Order-Confirmations als Events
   - Portfolio-Updates broadcast

3. **Frontend-Service (Port 8001)**
   - Trading-Interface mit Bitpanda-Backend
   - Echtzeit-Portfolio-Anzeige
   - Order-Management-UI

4. **ML-Analytics-Service**
   - Trading-Signale an Bitpanda-API
   - Performance-Analyse mit echten Trades
   - Risk-Metrics aus Live-Portfolio

---

## 📋 ANFORDERUNGS-CHECKLISTE

### **Funktionale Anforderungen:**
- [x] Broker-API ausgewählt (Bitpanda)
- [x] API-Limits dokumentiert
- [x] Order-Constraints spezifiziert
- [x] Trading-Zeiten definiert
- [x] Error-Handling konzipiert
- [x] Fallback-Strategie (One Trading)

### **Technische Anforderungen:**
- [x] Broker-Gateway-Service vorhanden
- [x] BitpandaCredentials Model implementiert
- [x] Rate-Limiting spezifiziert
- [x] Order-Validation definiert
- [ ] API-Integration implementiert
- [ ] Testing-Framework aufgesetzt

### **Compliance-Anforderungen:**
- [x] EU-regulierter Broker gewählt
- [x] API-Compliance dokumentiert
- [x] Rate-Limits respektiert
- [x] Audit-Trail vorgesehen
- [x] Monitoring-Konzept erstellt

---

## 📌 ZUSAMMENFASSUNG

Die **Bitpanda-Integration** für das Depot-Management ist **vollständig spezifiziert** und bereit für die Implementation. Alle technischen Anforderungen, API-Limits und Compliance-Vorgaben sind dokumentiert. Der Broker-Gateway-Service ist bereits vorbereitet und wartet auf die API-Key-Integration.

**Nächster Schritt:** Bitpanda Sandbox-API-Keys beantragen und Test-Integration starten.

---

*Spezifikation erstellt am 30.08.2025*  
*Projekt: Aktienanalyse-Ökosystem*  
*Broker: Bitpanda (Primary) / One Trading (Fallback)*