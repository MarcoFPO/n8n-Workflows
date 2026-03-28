# Zabbix-osTicket Webhook Integration - Projektübersicht

**Projekt:** Automatische Ticket-Erstellung aus Zabbix Alarms
**Status:** In Entwicklung
**Version:** 1.0
**Datum:** 2025-10-26

---

## Zusammenfassung

Diese Integration automatisiert die Erstellung von Support-Tickets in osTicket direkt aus Zabbix-Alarmen. Der Zabbix-Server ruft einen Webhook auf, der:

1. **Empfängt** Alarm-Daten (WER, WANN, WAS, Eventnummer)
2. **Transformiert** die Daten in das osTicket-Format
3. **Erstellt** automatisch ein neues Ticket mit allen relevanten Informationen

---

## Die 4 Kernattribute

### **WER** - Initiator des Alarms
- Quelle: `user` + `host_name` aus Zabbix
- Ziel: osTicket Requester Name
- Format: `"zabbix-automation (webserver-01)"`

### **WANN** - Zeitpunkt des Alarms
- Quelle: `event_time` aus Zabbix
- Ziel: osTicket Ticket-Erstellungszeit
- Format: ISO 8601 (`2025-10-26T14:32:15Z`)

### **WAS** - Beschreibung des Problems
- Quelle: `trigger_name`, `trigger_description`, `host_name`, `host_ip`, etc.
- Ziel: osTicket Subject + Message Body
- Format: Strukturiertes HTML mit allen Details

### **EVENTNUMMER** - Eindeutige Event-ID
- Quelle: `event_id` aus Zabbix
- Ziel: Custom Field `zabbix_event_id` in osTicket
- Format: String (z.B. `"12345678"`)

---

## Dokumentation

### 📋 **LLD (Low Level Design)**
**Datei:** `LLD-Zabbix-osTicket-Integration.md`

Detailliertes technisches Design mit:
- Webhook-Schnittstelle (Request/Response Schema)
- Datenfluss und Transformationen
- osTicket API Integration
- Fehlerbehandlung und Retry-Logik
- Logging und Audit-Trail
- Deployment-Checklist

**Ideal für:** Architektur-Reviews, Requirement-Erfassung

---

### ⚡ **Quick Reference**
**Datei:** `QUICK_REFERENCE-Zabbix-osTicket.md`

Schnelle Übersicht mit:
- Workflow-Diagramm
- JSON-Struktur (Request/Response)
- Severity Mapping
- Daten-Transformationen
- Test-Befehl (cURL)
- Monitoring-Metriken

**Ideal für:** Schnelle Referenz während der Entwicklung

---

### 🔧 **Implementierungs-Guide**
**Datei:** `IMPLEMENTATION_GUIDE-Zabbix-osTicket.md`

Produktionsreifer Code mit:
- Python/FastAPI Webhook-Implementation
- Docker Dockerfile & docker-compose.yml
- Zabbix Media Type & Action Konfiguration
- Testing & cURL Beispiele
- Logging & Prometheus Metriken
- Deployment-Checklist

**Ideal für:** Entwickler und DevOps-Ingenieure

---

## Workflow-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                    ZABBIX-SERVER                            │
│                                                             │
│  1. Trigger wird ausgelöst (Problem erkannt)              │
│  2. Action sendet Alarm-Daten zum Webhook                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ POST /api/v1/zabbix/alerts
                  │ {event_id, event_time, trigger_name, ...}
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│               WEBHOOK-SERVICE (n8n/FastAPI)                 │
│                                                             │
│  3. Validiere Daten (Pflichtfelder, JSON-Schema)          │
│  4. Transformiere:                                         │
│     - Zeit: "YYYY-MM-DD HH:MM:SS" → ISO 8601             │
│     - Severity: "High" → Priority 3                       │
│     - Body: Template mit allen Details                    │
│  5. Erstelle osTicket Request                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ POST /api/tickets.json
                  │ {name, subject, message, priority, ...}
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    OSTICKET-SERVER                          │
│                                                             │
│  6. Neues Ticket wird erstellt                            │
│  7. Ticket enthält alle Zabbix-Informationen              │
│  8. Support-Team kann sofort reagieren                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Datenfluss (Detailliert)

### Input (Von Zabbix)
```json
{
  "event_id": "12345678",
  "event_time": "2025-10-26 14:32:15",
  "trigger_name": "High CPU usage on webserver-01",
  "trigger_severity": "High",
  "host_name": "webserver-01",
  "host_ip": "192.168.1.100",
  "user": "zabbix-automation"
}
```

### Transformationen

| Schritt | Eingabe | Transformation | Ausgabe |
|---------|---------|----------------|---------|
| 1. Zeit | `2025-10-26 14:32:15` | Datetime Parsing + ISO 8601 | `2025-10-26T14:32:15Z` |
| 2. Severity | `High` | Lookup in Severity Map | `3` (osTicket Priority) |
| 3. Name | `zabbix-automation`, `webserver-01` | String Formatting | `zabbix-automation (webserver-01)` |
| 4. Subject | `High CPU usage on webserver-01` | Add Prefix | `[Zabbix] High CPU usage on webserver-01` |
| 5. Body | Alle Zabbix-Felder | HTML Template Rendering | `<h2>Zabbix Alert Details</h2>...` |

### Output (Nach osTicket)
```json
{
  "name": "zabbix-automation (webserver-01)",
  "email": "zabbix@example.com",
  "subject": "[Zabbix] High CPU usage on webserver-01",
  "message": "<h2>Zabbix Alert Details</h2>...",
  "priority": 3,
  "zabbix_event_id": "12345678",
  "zabbix_event_time": "2025-10-26T14:32:15Z"
}
```

### osTicket Response
```json
{
  "ticket_id": 123456,
  "number": "OST-123456"
}
```

---

## Severity Mapping

| Zabbix | osTicket | Bedeutung |
|--------|----------|-----------|
| Disaster | 4 (Emergency) | Sofortige Eskalation erforderlich |
| High | 3 (High) | Wichtig, zeitnah bearbeiten |
| Average | 2 (Medium) | Normale Bearbeitung |
| Warning | 1 (Low) | Niedrige Priorität |
| Information | 1 (Low) | Informativ |
| Not classified | 2 (Normal) | Standard-Priorität |

---

## Technische Anforderungen

### Services
- **Zabbix Server** mit Webhook-Unterstützung (5.0+)
- **osTicket** mit API aktiviert
- **Webhook-Host** (Docker, Linux Server, o.ä.)

### Dependencies
- Python 3.11+
- FastAPI / Uvicorn
- httpx (für osTicket API Calls)
- Docker (optional, aber empfohlen)

### Netzwerk
- Zabbix kann Webhook-Host erreichen (HTTP/HTTPS)
- Webhook-Host kann osTicket API erreichen
- Firewall-Regeln entsprechend konfiguriert

### API Keys
- Zabbix Webhook API Key (generiert)
- osTicket API Key (in osTicket erstellen)

---

## Implementierungs-Phasen

### Phase 1: Design & Planning ✓
- [x] LLD erstellen
- [x] Datenfluss definieren
- [x] API-Spezifikationen festlegen

### Phase 2: Backend-Entwicklung
- [ ] Webhook-Service implementieren (FastAPI)
- [ ] Daten-Validierung
- [ ] Transformations-Logik
- [ ] osTicket API Integration

### Phase 3: Zabbix-Konfiguration
- [ ] Media Type erstellen
- [ ] Action konfigurieren
- [ ] Test-Trigger definieren

### Phase 4: Testing
- [ ] Unit Tests
- [ ] Integration Tests
- [ ] End-to-End Tests
- [ ] Load Testing

### Phase 5: Deployment
- [ ] Docker Image bauen
- [ ] Produktions-Umgebung aufsetzen
- [ ] Monitoring konfigurieren
- [ ] Dokumentation finalisieren

### Phase 6: Monitoring & Support
- [ ] Metriken überwachen
- [ ] Alerts konfigurieren
- [ ] Runbooks erstellen
- [ ] Incident Response etablieren

---

## Erfolgs-Kriterien

✅ Zabbix-Alarm wird innerhalb von 5 Sekunden in osTicket-Ticket konvertiert
✅ Alle 4 Attribute (WER, WANN, WAS, Eventnummer) sind im Ticket vorhanden
✅ Success Rate > 99%
✅ Error Handling & Retry-Logik funktionieren
✅ Audit Trail für alle Transaktionen
✅ Monitoring & Alerting aktiv

---

## Häufige Fragen (FAQ)

**F: Was ist, wenn osTicket nicht erreichbar ist?**
A: Der Webhook hat eine Retry-Logik mit 3 Versuchen und Exponential Backoff. Nach Fehlschlag wird ein Error-Log erstellt.

**F: Kann man bestimmte Alarm-Typen filtern?**
A: Ja, in der Zabbix Action können Bedingungen definiert werden (z.B. nur bestimmte Trigger/Hosts).

**F: Wie wird die Authentifizierung gesichert?**
A: Über API Keys (Header: X-API-Key). Optional kann IP-Whitelist konfiguriert werden.

**F: Kann man Ticket-Updates bei Recovery senden?**
A: Ja, durch separate Action für Recovery-Events (optional, im Design offen).

**F: Welche Daten werden geloggt?**
A: Transaction ID, Zabbix Event ID, osTicket Ticket ID, Status, Dauer, Fehler.

---

## Dateien im Projekt

```
n8n-workflows/
├── docs/
│   ├── LLD-Zabbix-osTicket-Integration.md          (Detailliertes Design)
│   ├── QUICK_REFERENCE-Zabbix-osTicket.md         (Schnelle Referenz)
│   ├── IMPLEMENTATION_GUIDE-Zabbix-osTicket.md    (Code & Implementierung)
│   ├── README-Integration.md                       (Diese Datei)
│   └── ...
├── workflows/
│   ├── rBbxkgNzArvmkpBE-zabbix-alert-to-osticket.json
│   └── ...
├── scripts/
│   ├── webhook.py                                  (FastAPI Implementierung)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── ...
└── ...
```

---

## Kontakt & Support

**Projekt Lead:** [DevOps Team]
**Tech Lead:** [Backend Team]
**Questions?** Siehe Dokumentation oder Team Slack

---

## Changelog

### Version 1.0 (2025-10-26)
- ✨ Initiales Design abgeschlossen
- 📋 LLD Dokumentation fertig
- ⚡ Quick Reference erstellt
- 🔧 Implementation Guide mit Code-Beispielen

---

**Status:** 🟡 In Entwicklung (Design Phase ✓)
**Nächster Schritt:** Backend-Implementierung starten

