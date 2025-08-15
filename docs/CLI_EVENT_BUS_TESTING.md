# CLI Event-Bus Testing & Monitoring Guide

## 🎯 Überblick

Das **Redis Event-Bus CLI Tool** bietet eine benutzerfreundliche Kommandozeilen-Schnittstelle für das Testen, Überwachen und Validieren der Event-Bus Infrastruktur im aktienanalyse-ökosystem.

### 🚀 Features

- **🏥 Health Checks**: Schnelle System-Gesundheitsprüfung
- **⚡ Performance Tests**: Basic und umfassende Load Tests
- **📊 Live-Monitoring**: Real-time System-Überwachung
- **📋 System Reports**: Detaillierte Performance-Berichte
- **📈 Status Monitoring**: Aktueller System-Zustand

---

## 🛠️ Installation & Setup

### Voraussetzungen
```bash
# System Requirements
- Python 3.11+
- Redis Server (läuft)
- aktienanalyse-ökosystem Services
```

### CLI Tool bereitstellen
```bash
# In aktienanalyse-ökosystem Verzeichnis
cd /home/mdoehler/aktienanalyse-ökosystem

# CLI Tool ist bereits verfügbar als:
./eventbus-cli [command]

# Oder direkter Python-Aufruf:
python3 cli_event_bus_tester.py [command]
```

---

## 📋 Befehle & Verwendung

### 🏥 Health Check
**Zweck**: Schneller System-Gesundheitscheck für tägliche Validierung

```bash
# Quick Health Check
./eventbus-cli health

# Output Beispiel:
🚀 Initialisiere Redis Event-Bus System...
✅ Event-Bus System erfolgreich initialisiert
🏥 Führe schnellen System Health Check durch...
✅ System Health Check: ERFOLGREICH
   Durchsatz: 124.5 events/sec
   Latenz P99: 45.2ms
   Fehlerrate: 0.001
```

**Wann verwenden**: 
- Vor wichtigen Trading-Operationen
- Nach System-Updates
- Bei Performance-Problemen

---

### ⚡ Performance Tests

#### Basic Performance Test
**Zweck**: Schnelle Performance-Validierung (30-60 Sekunden)

```bash
# Basic Test (empfohlen für tägliche Checks)
./eventbus-cli test
./eventbus-cli test basic

# Output zu JSON-Datei
./eventbus-cli test basic --output results.json
```

#### Comprehensive Performance Tests
**Zweck**: Umfassende Systemvalidierung mit allen Test-Szenarien

```bash
# Comprehensive Tests (10-15 Minuten)
./eventbus-cli test full
./eventbus-cli test comprehensive

# Mit Report-Speicherung
./eventbus-cli test full --output comprehensive_results.json
```

**Test-Szenarien umfassen**:
- Basic Performance Baseline
- High Throughput Stress Test
- Mixed Workload Simulation
- Service Recovery Test

**Performance Targets**:
- **Durchsatz**: >400 events/sec unter Last
- **Latenz P99**: <100ms für Standard-Operationen
- **Fehlerrate**: <1% unter normaler Last
- **Verfügbarkeit**: >99.9% mit Circuit Breaker Protection

---

### 📊 Live-Monitoring

**Zweck**: Real-time Überwachung der System-Performance

```bash
# Standard-Monitoring (60 Minuten)
./eventbus-cli monitor

# Custom Duration
./eventbus-cli monitor 30    # 30 Minuten
./eventbus-cli monitor 120   # 2 Stunden

# Stoppen mit Ctrl+C
```

**Live-Output Beispiel**:
```
📊 Starte Live-Monitoring für 60 Minuten...
📈 Drücke Ctrl+C zum Stoppen
[14:30:15] ✅ System: healthy | Alerts: 0
           📈 Durchsatz: 156.3 eps
           ⏱️ Latenz: 42.1ms
           💾 Memory: 384MB
[14:30:45] ✅ System: healthy | Alerts: 0
           📈 Durchsatz: 163.7 eps
           ⏱️ Latenz: 38.9ms
           💾 Memory: 392MB
```

**Monitoring Metriken**:
- System Health Status
- Aktive Alerts Count
- Gesamtdurchsatz (events/sec)
- Durchschnittliche Latenz (ms)
- Memory Usage (MB)

---

### 📋 System Reports

**Zweck**: Detaillierte Performance-Analyse und Trend-Reporting

```bash
# Standard-Report (24 Stunden)
./eventbus-cli report

# Custom Zeitraum
./eventbus-cli report 48    # 48 Stunden
./eventbus-cli report 168   # 1 Woche

# Mit JSON-Export
./eventbus-cli report 24 --output system_report.json
```

**Report Inhalte**:
- System Health Overview
- Service-spezifische Performance-Metriken
- Top-performing Services Ranking
- Ecosystem-spezifische Empfehlungen
- Alert-Zusammenfassung
- Performance-Trends

**Sample Report Output**:
```
📋 SYSTEM REPORT ZUSAMMENFASSUNG
======================================================================
✅ System Health: healthy
🔧 Services: 6/6 gesund
📈 Gesamtdurchsatz: 245.7 events/sec
⏱️ Durchschnittliche Latenz: 52.3ms
💾 Gesamter Memory: 1,247MB
✅ Keine aktiven Alerts

🏆 Top Services:
   1. market-data-service - A+
   2. intelligent-core-service - A
   3. order-service - A
======================================================================
```

---

### 📈 System Status

**Zweck**: Schneller Status-Check ohne vollständige System-Initialisierung

```bash
# Aktueller Status
./eventbus-cli status
```

**Status Output**:
```
📊 AKTUELLER SYSTEM STATUS
==================================================
✅ System Status: healthy
📝 Details: All services operational
==================================================
```

---

## 🎯 Anwendungsszenarien

### 👨‍💼 Tägliche Routine (System Administrator)
```bash
# Morgens: Quick Health Check
./eventbus-cli health

# Bei Problemen: Basic Performance Test
./eventbus-cli test

# Ende der Woche: Comprehensive Report
./eventbus-cli report 168
```

### 🔧 Troubleshooting (DevOps)
```bash
# Problem erkannt - System Status prüfen
./eventbus-cli status

# Performance-Problem analysieren
./eventbus-cli test comprehensive

# Live-Monitoring für Problemanalyse
./eventbus-cli monitor 60
```

### 📊 Performance Monitoring (Business)
```bash
# Wöchentliche Performance-Reviews
./eventbus-cli report 168 --output weekly_performance.json

# Trading-Peak Monitoring
./eventbus-cli monitor 240  # 4 Stunden während Trading-Zeiten
```

### 🚀 Deployment Validation
```bash
# Nach Deployment: Comprehensive Test
./eventbus-cli test full

# Monitoring nach Deployment
./eventbus-cli monitor 120
```

---

## 📁 Output & Reports

### Report-Speicherung
- **Automatisch**: Reports werden in `/home/mdoehler/aktienanalyse-ökosystem/reports/` gespeichert
- **Timestamp-basiert**: Alle Reports haben Zeitstempel für Versionierung
- **JSON Format**: Maschinenlesbar für weitere Verarbeitung

### Datei-Struktur
```
reports/
├── system_report_24h_20250108_143022.json
├── redis_event_bus_performance_report_20250108_141544.json
└── comprehensive_test_results_20250108_140233.json
```

---

## 🚨 Alert-Management

### Alert-Levels
- **INFO**: Informative Meldungen
- **WARNING**: Aufmerksamkeit erforderlich
- **ERROR**: Sofortige Maßnahmen empfohlen  
- **CRITICAL**: Sofortige Intervention erforderlich

### Alert-Thresholds (Standard)
- **Throughput**: Warning <100 eps, Critical <50 eps
- **Latency**: Warning >100ms, Critical >500ms
- **Error Rate**: Warning >5%, Critical >10%
- **Memory**: Warning >512MB, Critical >1GB
- **CPU**: Warning >70%, Critical >90%

---

## 🔧 Troubleshooting

### Häufige Probleme

#### CLI Tool startet nicht
```bash
# Python-Path prüfen
python3 --version

# Permissions prüfen
ls -la eventbus-cli
chmod +x eventbus-cli

# Dependencies prüfen
python3 -c "import sys; print(sys.path)"
```

#### Event-Bus System nicht erreichbar
```bash
# Redis Status prüfen
systemctl status redis-server

# Services Status prüfen
./eventbus-cli status

# Vollständige Initialisierung
./eventbus-cli health
```

#### Performance Tests schlagen fehl
```bash
# System Health prüfen
./eventbus-cli health

# Redis Memory prüfen
redis-cli info memory

# Service Status einzeln prüfen
./eventbus-cli status
```

---

## 📊 Performance Benchmarks

### Ziel-Performance (Production)
- **Durchsatz**: >400 events/sec sustained
- **Latenz P99**: <100ms 
- **Verfügbarkeit**: >99.9%
- **Fehlerrate**: <1%
- **Memory Effizienz**: <512MB optimized

### Test-Umgebung Performance
- **Basic Test**: 30-60 Sekunden
- **Comprehensive Test**: 10-15 Minuten
- **Health Check**: 5-10 Sekunden
- **Status Check**: 1-2 Sekunden

---

## 🎯 Best Practices

### Performance Testing
1. **Regelmäßigkeit**: Täglich Basic Tests, wöchentlich Comprehensive
2. **Timing**: Tests außerhalb der Trading-Hauptzeiten
3. **Baseline**: Performance-Baseline nach jedem Update etablieren
4. **Trending**: Wöchentliche Reports für Performance-Trends

### Monitoring
1. **Kontinuität**: Live-Monitoring während kritischer Trading-Zeiten
2. **Alerting**: Alert-Handler für kritische Performance-Probleme
3. **Capacity Planning**: Memory- und CPU-Trends für Skalierung

### Troubleshooting
1. **Systematisch**: Status → Health → Test → Monitor
2. **Logging**: CLI Output für spätere Analyse speichern
3. **Eskalation**: Bei CRITICAL Alerts sofortige Eskalation

---

## 🔮 Zukünftige Erweiterungen

- **🤖 Automated Reporting**: Automatische tägliche/wöchentliche Reports
- **📱 Mobile Alerts**: Push-Notifications für kritische Alerts
- **🎯 Predictive Analytics**: ML-basierte Performance-Vorhersagen
- **🔧 Auto-Recovery**: Automatische Service-Recovery bei Fehlern
- **📊 Grafische Dashboards**: Web-basierte Real-time Dashboards

---

**🎉 Das CLI Event-Bus Testing Tool ist produktionsbereit und bietet umfassende Funktionalität für die Überwachung und Validierung der aktienanalyse-ökosystem Event-Bus Infrastruktur!**