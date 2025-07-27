# 🌐 Vereinfachte GUI-Anforderungen - Single-User Frontend

## 🎯 **Übersicht**

**Ziel**: Einfaches, robustes Web-Frontend für einen Benutzer (mdoehler)  
**Architektur**: React/TypeScript SPA mit Session-basierter Authentifizierung  
**Zugang**: NUR über Port 443 (HTTPS) von außen erreichbar

---

## 🏗️ **Frontend-Architektur (Vereinfacht)**

### **Deployment-Modell**
```
NGINX (Port 443) → React SPA (Port 8004)
├── Statische Assets (bundled)
├── API-Proxy zu Backend-Services
└── WebSocket-Proxy für Real-time Updates

Externe Erreichbarkeit: NUR Port 443 (HTTPS)
Backend-Services: 8001-8005 (intern, nicht extern erreichbar)
```

### **Authentication-Modell (Single-User)**
```
Authentifizierung:
├── Linux-User: mdoehler
├── Session-basiert (HTTP Cookies)
├── Keine JWT/API-Keys
├── Keine Multi-User/Role-Management
└── Automatisches Login bei Browser-Start (optional)
```

---

## 📋 **Frontend-Module (6 Module vereinfacht)**

### **Modul 17: 🎨 frontend-core (Basis-Framework)**

#### **React SPA Framework**
- **Single-Page Application**: React 18 mit TypeScript
- **Routing**: React Router für Navigation zwischen Bereichen
- **State Management**: React Context + useState/useReducer
- **Component Library**: Shared UI-Components (Button, Card, Table, Modal)
- **Theme System**: Einfaches CSS-in-JS oder CSS Modules
- **Responsive Design**: Mobile-first für Desktop/Tablet/Mobile

#### **Authentication (Single-User)**
- **Session-Cookie**: Einfache Session-basierte Auth für mdoehler
- **Auto-Login**: Persistente Session (kein Re-Login erforderlich)
- **Logout-Funktion**: Session-Invalidierung
- **KEINE**: SSO, Multi-User, Role-Management, JWT

#### **Navigation (Enhanced GUI v2.0)**
- **Sidebar-Navigation**: 5 Bereiche (Dashboard, Events, Monitoring, API, Admin)
- **Dynamic Content Loading**: SPA mit `/api/content/{section}` ohne Page-Reload
- **Bootstrap 5 Design**: Responsive Layout mit FontAwesome Icons
- **Active-State-Management**: Visual Feedback für aktuelle Sektion
- **Mobile-First**: Collapsible Sidebar für alle Bildschirmgrößen

### **Modul 18: 📈 aktienanalyse-ui (Enhanced Dashboard v2.0)**

#### **Dashboard-Bereich (Neue Hauptseite)**
- **System-Übersicht**: Live-Metriken für CPU, Memory, Services in Status-Cards
- **Service-Status**: Real-time Health-Check für alle Backend-Services
- **Quick-Links**: Direkte Navigation zu Service-Dokumentationen
- **Performance-Anzeige**: Visuelle Progress-Bars für System-Ressourcen
- **Refresh-Funktionen**: Manuelle und automatische Datenaktualisierung

#### **Configuration Interface**
- **API-Konfiguration**: Formular für Alpha Vantage, Yahoo Finance API-Keys
- **Parameter-Tuning**: Slider/Input-Felder für ML-Model-Parameter
- **Alert-Setup**: E-Mail/Push-Benachrichtigungen für Signale
- **Export-Tools**: CSV/Excel-Export für Analysedaten

### **Modul 19: 🧮 analytics-ui (Performance Analytics)**

#### **Performance Dashboard**
- **Portfolio-Overview**: Portfolio-Performance-Charts (Line/Area-Charts)
- **Risk-Metrics**: VaR, Sharpe Ratio als Gauge-Komponenten
- **Benchmark-Vergleich**: Performance vs. DAX/S&P500
- **Zeitraum-Selektor**: 1M/3M/6M/1Y/YTD Buttons

#### **Report-Interface**
- **Report-Viewer**: PDF-Report-Viewer im Browser
- **Report-Generator**: Einfache Report-Konfiguration (wöchentlich/monatlich)
- **Export-Optionen**: PDF/Excel-Download
- **Report-Historie**: Liste der generierten Reports

### **Modul 20: 💼 depot-ui (Portfolio Trading)**

#### **Portfolio Management**
- **Depot-Übersicht**: Tabelle mit allen Positionen (Real-time Updates)
- **Position-Details**: Modal/Drawer mit detaillierter Position-Info
- **Performance-Ranking**: Sortierbare Performance-Liste
- **Tax-Calculator**: Steuerberechnung mit Brutto/Netto-Anzeige

#### **Trading Interface (Bitpanda Integration)**
- **Order-Interface**: Buy/Sell-Formulare mit Bitpanda API
- **Order-History**: Tabelle mit Order-Status und Historie
- **Watchlist**: 0-Bestand-Positionen für Observation
- **Live-Updates**: WebSocket für Real-time Portfolio-Updates

### **Modul 21: 🔄 integration-layer (API Integration)**

#### **Backend-Integration (Vereinfacht)**
- **REST-API-Clients**: Axios-basierte API-Clients für alle 4 Backend-Services
- **WebSocket-Client**: Single WebSocket-Connection für Real-time Updates
- **Error-Handling**: Toast-Notifications für API-Fehler
- **Loading-States**: Spinner/Skeleton für asynchrone Operationen

#### **Data-Synchronization**
- **Polling-Updates**: Regelmäßige Daten-Updates (alle 30s/60s)
- **Real-time Events**: WebSocket für Live-Updates (Preise, Orders)
- **Cache-Management**: Browser-Cache für statische Daten
- **Offline-Handling**: Basic Offline-Detection und -Message

### **Modul 22: 🌐 unified-api (Frontend API Gateway)**

#### **API-Proxy (NGINX Integration)**
- **Request-Routing**: Frontend requests → Korrekte Backend-APIs
- **Response-Caching**: Client-side Caching für Performance
- **CORS-Handling**: Correct CORS headers für API-Calls
- **WebSocket-Proxy**: WebSocket-Verbindungen über NGINX

#### **Session Management (Single-User)**
- **Session-Cookie**: HTTP-Only Cookie für Session
- **CSRF-Protection**: CSRF-Token für State-changing Requests
- **HTTPS-Enforcement**: Redirect HTTP → HTTPS
- **Security-Headers**: CSP, X-Frame-Options, X-Content-Type-Options

---

## 🚀 **Deployment-Konfiguration**

### **NGINX-Konfiguration (Port 443)**
```nginx
server {
    listen 443 ssl http2;
    server_name 10.1.1.120;
    
    # SSL Certificate
    ssl_certificate /etc/ssl/certs/aktienanalyse.crt;
    ssl_certificate_key /etc/ssl/private/aktienanalyse.key;
    
    # React SPA (Static Files)
    location / {
        root /opt/aktienanalyse-frontend/build;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }
    
    # API-Proxy zu Backend-Services
    location /api/aktienanalyse/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/auswertung/ {
        proxy_pass http://127.0.0.1:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/verwaltung/ {
        proxy_pass http://127.0.0.1:8003/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket-Proxy
    location /ws/ {
        proxy_pass http://127.0.0.1:8005/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy strict-origin-when-cross-origin;
}
```

### **React Build-Konfiguration**
```json
{
  "name": "aktienanalyse-frontend",
  "build": {
    "outDir": "/opt/aktienanalyse-frontend/build",
    "generateSW": false,
    "skipWaiting": false
  },
  "proxy": {
    "/api": {
      "target": "http://localhost",
      "secure": false,
      "changeOrigin": true
    },
    "/ws": {
      "target": "ws://localhost:8005",
      "ws": true
    }
  }
}
```

---

## 🔒 **Security-Anforderungen (Vereinfacht)**

### **Single-User Authentication**
- **Session-basiert**: HTTP-Only Cookies
- **HTTPS-Only**: Alle Kommunikation verschlüsselt
- **CSRF-Protection**: Token-basierte CSRF-Abwehr
- **Session-Timeout**: Automatischer Logout nach Inaktivität (optional)

### **Network Security**
- **Port-Isolation**: NUR Port 443 extern erreichbar
- **Firewall**: Alle anderen Ports (8001-8005) intern
- **SSL/TLS**: Strong Ciphers, HSTS-Header
- **Rate-Limiting**: Basic Rate-Limiting in NGINX

### **Content Security**
- **CSP-Headers**: Strict Content Security Policy
- **XSS-Protection**: Input-Sanitization im Frontend
- **Static Asset Security**: Integrity-Checks für JS/CSS-Assets

---

## 📊 **Technologie-Stack**

### **Frontend-Technologien**
```
React 18 + TypeScript
├── Routing: React Router v6
├── State: React Context + useReducer
├── Charts: TradingView Lightweight Charts
├── UI Library: Custom Components + Styled Components
├── HTTP Client: Axios
├── WebSocket: native WebSocket API
├── Build Tool: Vite
└── Testing: Vitest + React Testing Library
```

### **Infrastructure**
```
NGINX (Port 443) - Reverse Proxy + Static File Server
├── SSL/TLS: Self-signed oder Let's Encrypt
├── Compression: gzip/brotli
├── Caching: Static Asset Caching
└── Logging: Access + Error Logs
```

---

## 🎯 **Implementation-Prioritäten**

### **Phase 1: Core-Frontend (2-3 Wochen)**
1. React SPA Setup mit TypeScript
2. Basic Authentication (Session-basiert)
3. NGINX-Konfiguration (Port 443)
4. Haupt-Navigation zwischen 4 Bereichen

### **Phase 2: Dashboard-Integration (3-4 Wochen)**
1. Stock Analysis Dashboard (aktienanalyse-ui)
2. Portfolio Management (depot-ui)
3. API-Integration zu Backend-Services
4. Real-time Updates über WebSocket

### **Phase 3: Analytics & Trading (2-3 Wochen)**
1. Performance Analytics (analytics-ui)
2. Trading-Interface mit Bitpanda
3. Configuration-Interface
4. Export/Report-Funktionen

### **Phase 4: Polish & Testing (1-2 Wochen)**
1. Error-Handling & Loading-States
2. Mobile-Responsive Design
3. Performance-Optimierung
4. Security-Hardening

---

## ✅ **Vereinfachungen umgesetzt**

### **Entfernt/Vereinfacht:**
- ❌ Single Sign-On (SSO)
- ❌ Multi-User Management
- ❌ Role-based Access Control
- ❌ JWT-Token Management
- ❌ Docker/Container-Virtualisierung
- ❌ Multi-Project Authentication
- ❌ Service-to-Service API-Keys

### **Beibehalten/Vereinfacht:**
- ✅ Single-User Session Authentication (mdoehler)
- ✅ Port 443 HTTPS-Only External Access
- ✅ Native LXC mit systemd Services
- ✅ React SPA mit einfacher Navigation
- ✅ Basic Security (HTTPS, CSP, CSRF)
- ✅ Real-time Updates über WebSocket
- ✅ Responsive Design für alle Devices

**Status**: 🟢 **Vereinfacht und implementation-ready für Single-User Umgebung**