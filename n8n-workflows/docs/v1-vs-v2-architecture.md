# Zabbix Workflow Architektur: V1 vs V2

## Übersicht

Dieses Dokument vergleicht die ursprüngliche Polling-basierte Architektur (V1) mit der neuen Event-basierten Architektur (V2).

## Architektur-Vergleich

### V1: Polling-Based (Schedule)

```
┌─────────────────────┐
│   Schedule Trigger  │
│   (Every 5 Minutes) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Master         │
│   Orchestrator      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Sub-1: Problem    │
│    Erfassung        │
│  (Zabbix API Poll)  │
└──────────┬──────────┘
           │
     [Batch of Problems]
           │
           ▼
    ┌─────┴─────┐
    │   Loop    │
    └─────┬─────┘
          │
    [For Each Problem]
          │
          ▼
    Sub-2 → Sub-3 → Sub-4 → Sub-5
```

**Eigenschaften:**
- ⏰ Schedule-basiert (alle 5 Minuten)
- 📦 Batch-Verarbeitung aller Probleme
- ⏳ Verzögerung: 0-5 Minuten bis zur Erkennung
- 📊 Hohe Last auf Zabbix API alle 5 Minuten
- 🔁 Loop über alle gefundenen Probleme

### V2: Event-Based (Webhook)

```
┌─────────────────────┐
│  Zabbix Problem     │
│  Event (Real-time)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Zabbix Action     │
│  (Webhook Trigger)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Sub-1 V2: Webhook  │
│   Event Receiver    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Redis Queue       │
│  (Event Buffer)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Master V2: Event   │
│  Processor (RPOP)   │
└──────────┬──────────┘
           │
     [Single Event]
           │
           ▼
    Sub-2 → Sub-3 → Sub-4 → Sub-5
```

**Eigenschaften:**
- ⚡ Event-basiert (Echtzeit)
- 📨 Single-Event-Verarbeitung
- ⏱️ Verzögerung: <1 Sekunde bis zur Erkennung
- 📉 Niedrige Last auf Zabbix (nur bei Events)
- 🔒 Lock-Mechanismus gegen Concurrent Processing
- 📦 Queue-Buffer für Event-Bursts

## Detaillierter Vergleich

### 1. Trigger-Mechanismus

| Aspekt | V1 (Schedule) | V2 (Event) |
|--------|---------------|------------|
| Trigger | Zeitgesteuert (5 Min) | Event-gesteuert (Webhook) |
| Reaktionszeit | 0-5 Minuten | <1 Sekunde |
| API-Last | Hoch (alle 5 Min) | Niedrig (nur bei Events) |
| Zabbix-Konfiguration | Keine | Action + Webhook nötig |

### 2. Problem-Erfassung (Sub-1)

#### V1: sub1-problem-erfassung.json
```
Webhook Trigger (manuell)
    ↓
Zabbix Login
    ↓
Get Problems (last 5 minutes)
    ↓
Get Host Names
    ↓
Format Batch Output
    ↓
Return: { problems: [array] }
```

#### V2: sub1-problem-erfassung-v2.json
```
Webhook Trigger (von Zabbix)
    ↓
Extract Event Data
    ↓
Push to Redis Queue (LPUSH)
    ↓
Increment Counter
    ↓
Trigger Master (Fire & Forget)
    ↓
Immediate Response to Zabbix
```

**Unterschiede:**
- V1: Polling-basiert, benötigt Zabbix-Login
- V2: Push-basiert, kein Login nötig
- V1: Gibt Problem-Array zurück
- V2: Speichert in Queue, antwortet sofort

### 3. Master-Workflow

#### V1: master-zabbix-orchestrator.json
```
Schedule Trigger (Every 5 Min)
    ↓
Config
    ↓
Call Sub-1 (Get Problems)
    ↓
Check: Problems Found?
├─ Yes: Split to Items
│       ↓
│   Loop Over Items
│       ↓
│   Process Each: Sub-2 → Sub-3 → Sub-4
│       ↓
│   Wait 2s Between Items
│       ↓
│   Aggregate All Results
│       ↓
│   Call Sub-5 (Batch Report)
│
└─ No: "No Problems Found" Message
```

#### V2: master-zabbix-orchestrator-v2.json
```
Webhook Trigger (von Sub-1 V2)
    ↓
Check Lock (Prevent Concurrent)
├─ Locked: Return "Already Processing"
└─ Not Locked:
    ↓
    Acquire Lock (5min TTL)
    ↓
    Pop Event from Queue (RPOP)
    ↓
    Check: Event Found?
    ├─ Yes: Parse Event
    │       ↓
    │   Mark as Processing
    │       ↓
    │   Format Problem Data
    │       ↓
    │   Sub-2 → Sub-3 → Sub-4
    │       ↓
    │   Format for Notification
    │       ↓
    │   Call Sub-5 (Single Event)
    │       ↓
    │   Mark as Completed
    │       ↓
    │   Release Lock
    │
    └─ No: Release Lock, Return "Queue Empty"
```

**Unterschiede:**
- V1: Schedule-Trigger, Batch-Processing
- V2: Webhook-Trigger, Single-Event-Processing
- V1: Loop mit Wait
- V2: Lock-Mechanismus, kein Loop
- V1: Aggregiert alle Probleme für einen Report
- V2: Erstellt Report pro Event

### 4. User-Benachrichtigung (Sub-5)

#### V1: Email mit Batch-Report
```
Input: { problems: [array], total_count: N }

Report enthält:
- Alle automatisch gelösten Probleme
- Alle fehlgeschlagenen Remote-Lösungen
- Alle manuellen Interventionen

1 Email pro Batch (alle 5 Minuten)
```

#### V2: Email pro Event
```
Input: { problems: [single], total_count: 1 }

Report enthält:
- Status des einzelnen Events
- Durchgeführte Aktionen
- Ergebnis

1 Email pro Event (Echtzeit)
```

**Hinweis:** Sub-5 V2 könnte erweitert werden um:
- Email-Aggregation (max 1 Email pro 5 Min)
- Severity-basierte Filterung
- Stille Verarbeitung für niedrige Severities

## Vor- und Nachteile

### V1: Polling-Based

**Vorteile:**
- ✅ Einfache Konfiguration (keine Zabbix-Änderungen)
- ✅ Batch-Processing reduziert Einzelverarbeitungen
- ✅ Ein Report pro Zeitfenster
- ✅ Keine externe Abhängigkeiten (Redis)

**Nachteile:**
- ❌ Verzögerung von 0-5 Minuten
- ❌ Hohe API-Last auf Zabbix
- ❌ Verarbeitet auch wenn keine Probleme
- ❌ Alle Probleme erst am Ende der 5-Min-Periode

### V2: Event-Based

**Vorteile:**
- ✅ Echtzeit-Reaktion (<1 Sekunde)
- ✅ Niedrige API-Last (nur bei Events)
- ✅ Event-Buffer für Bursts
- ✅ Lock verhindert Concurrent Processing
- ✅ Event-Status-Tracking in Redis

**Nachteile:**
- ❌ Komplexere Konfiguration (Zabbix Action)
- ❌ Redis-Abhängigkeit
- ❌ Potenziell viele Emails bei vielen Events
- ❌ Mehr bewegliche Teile (mehr Fehlerquellen)

## Performance-Vergleich

### Scenario: 10 Probleme in 5 Minuten

#### V1: Polling
```
T+0:00  Schedule Trigger
T+0:05  Verarbeitung startet
T+0:06  Sub-1: 10 Probleme gefunden
T+0:06  Loop startet
T+0:07  Problem 1 verarbeitet
T+0:09  Problem 2 verarbeitet (2s Wait)
...
T+0:25  Problem 10 verarbeitet
T+0:25  Sub-5: 1 Email mit 10 Problemen

Gesamt-Latenz: 25 Minuten (5 + 20)
API-Calls: 1x Problem-Erfassung
Emails: 1
```

#### V2: Event-Based
```
T+0:00  Problem 1 → Webhook → Queue → Processing
T+0:03  Problem 1 fertig (Email 1)
T+0:05  Problem 2 → Webhook → Queue → Processing
T+0:08  Problem 2 fertig (Email 2)
...
T+1:30  Problem 10 → Webhook → Queue → Processing
T+1:33  Problem 10 fertig (Email 10)

Gesamt-Latenz: ~1:33 Minuten
API-Calls: 0 (Push-basiert)
Emails: 10
```

### Scenario: Keine Probleme

#### V1: Polling
```
Alle 5 Minuten:
- Schedule Trigger
- Sub-1 Query
- "Keine Probleme" → Ende

Resourcen-Verbrauch: Kontinuierlich
```

#### V2: Event-Based
```
Keine Events = Keine Aktivität

Resourcen-Verbrauch: 0
```

## Migration V1 → V2

### Schritt 1: Neue Workflows anlegen

```bash
# V2 Workflows in n8n importieren
cd /opt/Projekte/n8n-workflows
./scripts/upload-v2-workflows.sh
```

### Schritt 2: Redis Queue vorbereiten

```bash
# Redis-Verbindung testen
redis-cli ping

# Queue-Keys erstellen (automatisch beim ersten Event)
# Kein manueller Eingriff nötig
```

### Schritt 3: Zabbix Action konfigurieren

Siehe: [zabbix-action-configuration.md](zabbix-action-configuration.md)

### Schritt 4: Parallel-Betrieb

- V1: Bleibt aktiv (Schedule)
- V2: Wird aktiviert (Webhook)
- Beide laufen parallel für Test-Phase

### Schritt 5: Monitoring

```bash
# V1 Ausführungen prüfen
# n8n UI → Workflow "Zabbix MASTER: Problem Manager Orchestrator"

# V2 Events prüfen
redis-cli LLEN zabbix:event:queue
redis-cli GET zabbix:event:counter
```

### Schritt 6: V1 deaktivieren

Wenn V2 stabil läuft:
- Master V1: Schedule-Trigger deaktivieren
- Optional: V1 Workflows als Backup behalten

## Empfehlung

### Für Production: V2 (Event-Based)

**Gründe:**
1. ⚡ Echtzeit-Reaktion kritisch für Monitoring
2. 📉 Reduzierte Last auf Zabbix-Server
3. 📊 Bessere Skalierbarkeit bei vielen Events
4. 🔍 Event-Tracking in Redis

**Optimierungen:**
- Email-Batching in Sub-5 V2 implementieren
- Master V2: Self-Triggering-Loop für kontinuierliche Queue-Verarbeitung
- Monitoring-Dashboard für Queue-Metriken

### Für Testing/Development: V1 (Polling)

**Gründe:**
1. ✅ Einfacher Setup (keine Zabbix-Konfiguration)
2. ✅ Keine externe Abhängigkeiten
3. ✅ Deterministisches Verhalten

## Nächste Schritte

1. ✅ V2 Workflows erstellt
2. ⏳ V2 Workflows in n8n importieren
3. ⏳ Zabbix Action konfigurieren
4. ⏳ Test-Events senden
5. ⏳ Parallel-Betrieb etablieren
6. ⏳ Monitoring aufsetzen
7. ⏳ V1 deaktivieren nach erfolgreicher Test-Phase
