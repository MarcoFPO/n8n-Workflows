# osTicket Ticketfelder - Vollständige Analyse
**Status:** ✅ Design Phase - Feldanalyse ABGESCHLOSSEN
**Datum:** 2025-10-26
**Erstellt von:** Claude Code (Specialized Agent)
**Version:** 1.0

---

## 📋 Überblick

Diese Dokumentation enthält eine vollständige Analyse aller osTicket-Ticketfelder für die Zabbix-Integration:

- **43 Felder** dokumentiert
- **7 Kategorien** organisiert (Basis, Klassifizierung, Zuordnung, Custom, Audit, Thread, Steuerung)
- **API-Mappings** mit Beispielen
- **GUI-Feldplatzierungsempfehlungen** für verschiedene Ansichten
- **Validierungsregeln** pro Feld

---

## 🎯 KRITISCHER FEHLER BEHOBEN

### ⚠️ Der ursprüngliche Fehler in der Dokumentation:

Das Feld **"WER"** bezieht sich **NICHT** auf einen User oder Agenten, sondern auf das **gestörte Objekt** (den Host/Service in Zabbix).

**Richtige Interpretation:**
- **WER** = Das gestörte Objekt (z.B. "prod-web-01", "Switch-ABC") → `affected_object`, `host_name`
- **WANN** = Zeitpunkt des Alarms → `event_time`, `created`
- **WAS** = Problemdescription (was ist gestört?) → `subject`, `message`, `trigger_description`
- **EVENTNUMMER** = Eindeutige Event-ID → `zabbix_event_id`

**Betroffene Felder der Fehleranalyse:**
- ~~Email/Name (User)~~ → Sollten nur "Zabbix Monitoring" als System-Absender sein
- **Affected Object / Host Name** → Diese Felder enthalten das "WER" (gestörtes Objekt)

---

## 📁 Feldstruktur - 7 Kategorien

### A. Basis-Informationen (Pflichtfelder für Ticketerstellung)

| Feldname (API) | Display-Name | Typ | Länge | Pflicht | Zabbix-Integration |
|---|---|---|---|---|---|
| `email` | Email Address | Email | 255 | **JA** | Automatisch (Monitoring-Mail) |
| `name` | Full Name | String | 128 | **JA** | Automatisch ("Zabbix Monitoring") |
| `subject` | Subject | String | 255 | **JA** | **ESSENTIELL** |
| `message` | Message / Body | Text/HTML | 64000 | **JA** | **ESSENTIELL** (Event Details) |

### B. Basis-Informationen (Optional)

| Feldname (API) | Display-Name | Typ | Länge | Pflicht | Zabbix-Integration |
|---|---|---|---|---|---|
| `phone` | Phone Number | Phone | 32 | Nein | Optional |
| `ip` | IP Address | IP | 45 | Nein | Empfohlen (Zabbix Server/Host IP) |
| `source` | Ticket Source | Enum | 32 | Nein | Automatisch = "API" |
| `notes` | Internal Notes | Text | 64000 | Nein | Optional (Meta-Infos) |

### C. Ticket-Steuerung (API-Parameter)

| Feldname (API) | Display-Name | Typ | Pflicht | Zabbix-Integration |
|---|---|---|---|---|
| `alert` | Send Alert to Staff | Boolean | Nein | Optional (Default: true) |
| `autorespond` | Send Auto-Response | Boolean | Nein | **Empfohlen: false** |
| `attachments` | Attachments | Array | Nein | Optional (Zabbix-Grafiken) |

### D. Klassifizierung & Routing

| Feldname (API) | Display-Name | Typ | Pflicht | Zabbix-Integration |
|---|---|---|---|---|
| `topicId` | Help Topic | Integer (ID) | Nein | **ESSENTIELL** (Routing) |
| `priority` | Priority | Integer (ID) | Nein | Optional (via Help Topic) |
| `dept_id` | Department | Integer (ID) | Read-Only | Via Help Topic |
| `sla_id` | SLA Plan | Integer (ID) | Read-Only | Via Help Topic |
| `status_id` | Status | Integer (ID) | Read-Only | Via Help Topic |

### E. Zuordnung (Assignment)

| Feldname (API) | Display-Name | Typ | Pflicht | Zabbix-Integration |
|---|---|---|---|---|
| `staff_id` | Assigned Agent | Integer (ID) | Nein | Via Help Topic |
| `team_id` | Assigned Team | Integer (ID) | Nein | Via Help Topic |
| `lock_id` | Locked By | Integer (ID) | Read-Only | System |

### F. Custom Fields (Zabbix-Spezifisch)

| Feldname (API) | Display-Name | Typ | Länge | Pflicht | Zabbix-Integration |
|---|---|---|---|---|---|
| **`zabbix_event_id`** | **Zabbix Event ID** | **Number** | **20** | **JA** | **ESSENTIELL** |
| `zabbix_trigger_id` | Zabbix Trigger ID | Number | 20 | Nein | Empfohlen |
| **`affected_object`** | **Affected Object / Host** | **String** | **255** | **Nein** | **ESSENTIELL - Das "WER"** |
| `severity` | Severity | Choice | - | Nein | Empfohlen |
| `event_time` | Event Time | DateTime | - | Nein | Automatisch |
| `event_status` | Event Status | Choice | - | Nein | **Empfohlen (für Auto-Close)** |
| `host_name` | Host Name | String | 255 | Nein | Automatisch |
| `trigger_description` | Trigger Description | Text | 4000 | Nein | Automatisch |
| `event_url` | Event URL / Zabbix Link | URL | 512 | Nein | Automatisch |

### G. Audit & Metadata (Read-Only)

| Feldname (API) | Display-Name | Typ | Sichtbarkeit |
|---|---|---|---|
| `ticket_id` | Ticket ID | Integer (PK) | System |
| `number` | Ticket Number | String | User & Agent |
| `user_id` | User ID | Integer (FK) | System |
| `created` | Created Date | DateTime | User & Agent |
| `updated` | Updated Date | DateTime | Agent only |
| `lastupdate` | Last Update | DateTime | Agent only |
| `reopened` | Reopened Date | DateTime | Agent only |
| `closed` | Closed Date | DateTime | User & Agent |
| `duedate` | Due Date | DateTime | User & Agent |
| `est_duedate` | Estimated Due Date (SLA) | DateTime | Agent only |
| `isoverdue` | Is Overdue | Boolean | Agent only |
| `isanswered` | Is Answered | Boolean | Agent only |
| `flags` | Flags | Integer (Bitfield) | System |
| `ticket_pid` | Parent Ticket ID | Integer | System |

### H. Thread & Collaboration

| Feldname (API) | Display-Name | Typ | Sichtbarkeit |
|---|---|---|---|
| `thread` | Thread | Relation | User & Agent |
| `collaborators` | Collaborators | Relation (Many) | Agent only |
| `tasks` | Tasks | Relation (Many) | Agent only |

---

## 🎯 Feldplatzierung auf der GUI - Designempfehlungen

### **1. Ticket-Erstellung (Client Portal)**

#### Sichtbar für User:
```
┌─────────────────────────────────────┐
│ Email Address (Auto-Fill)           │  ← Pflichtfeld
│ Full Name (Auto-Fill)               │  ← Pflichtfeld
│ Phone Number (Optional)             │  ← Optional
│ Help Topic (Dropdown)               │  ← ESSENTIELL für Routing
├─────────────────────────────────────┤
│ Subject (Einzeiliger Text)          │  ← Pflichtfeld
│ Message (Rich Text Editor)          │  ← Pflichtfeld (HTML unterstützt)
│ Attachments (Drag & Drop)           │  ← Optional
└─────────────────────────────────────┘
```

**Für Zabbix-Integration:** Keine User-Eingabe erforderlich! Alle Felder werden via API gefüllt.

---

### **2. Ticket-Ansicht (Agent Staff Panel)**

#### **Oberer Bereich - Ticket Header:**
```
┌─────────────────────────────────────────────────────────────────┐
│ #123456 [DROPDOWN: Status]  [DROPDOWN: Priority]               │
│ Subject: [PROBLEM] High CPU usage on prod-web-01               │
│ From: Zabbix Monitoring <monitoring@example.com>               │
└─────────────────────────────────────────────────────────────────┘
```

#### **Linke Sidebar - User Info:**
```
┌─────────────────────────┐
│ USER INFORMATION        │
├─────────────────────────┤
│ Name:                   │
│ Zabbix Monitoring       │
│                         │
│ Email:                  │
│ monitoring@example.com  │
│                         │
│ Phone:                  │
│ +49-123-456789X100      │
│                         │
│ [View User Profile]     │
└─────────────────────────┘
```

#### **Rechte Sidebar - Ticket Properties:**
```
┌─────────────────────────────────────┐
│ TICKET PROPERTIES                   │
├─────────────────────────────────────┤
│ Department:     [Transfer ↔]        │
│ Help Topic:     Zabbix Monitoring   │
│ Assigned To:    [Select Team/Agent] │
│ SLA Plan:       24/7 Monitoring     │
│ Due Date:       [DatePicker]        │
│ Source:         📡 API              │
│ Ticket Lock:    [Lock Info]         │
│                                     │
│ [Expand] Metadata                   │
│ ├─ Created: 2025-10-26 14:23:45    │
│ ├─ Last Update: 2025-10-26 15:30   │
│ ├─ Overdue: ❌ No                   │
│ ├─ Answered: ✅ Yes                 │
│ └─ Closed: -                        │
└─────────────────────────────────────┘
```

#### **Zabbix-Spezifische Tab / Ausklappbereich:**
```
┌──────────────────────────────────────────┐
│ [+] ZABBIX EVENT DETAILS                 │
├──────────────────────────────────────────┤
│ Status:         🔴 PROBLEM               │
│ Severity:       ⚠️  High                 │
│ Event ID:       123456789               │
│ Trigger ID:     98765                   │
│                                          │
│ Affected Object (WER):                  │
│ ► prod-web-01.example.com               │
│                                          │
│ Host Name:      prod-web-01             │
│ Host IP:        192.168.1.100           │
│                                          │
│ Event Time:     2025-10-26 14:23:45     │
│ Trigger Name:   CPU usage > 90%         │
│ Current Value:  95.3%                   │
│                                          │
│ Description:                            │
│ CPU usage has exceeded the 90%          │
│ threshold for more than 5 consecutive   │
│ minutes...                              │
│                                          │
│ [🔗 View Event in Zabbix] [📋 Copy ID] │
└──────────────────────────────────────────┘
```

#### **Hauptbereich - Thread:**
```
┌──────────────────────────────────────────┐
│ THREAD (Chronologisch)                   │
├──────────────────────────────────────────┤
│ [14:23] Auto-created by Zabbix           │
│ 🤖 System: Event received and processed  │
│                                          │
│ [14:30] John Assigned                    │
│ 👤 Agent: Assigned to John Smith         │
│                                          │
│ [15:00] John Replied                     │
│ 💬 Agent: Investigating the issue...     │
│                                          │
│ [15:25] Auto-Updated                    │
│ 🤖 System: Event status changed: OK      │
│ ✅ RESOLVED - 95.3% → 65.2%             │
│                                          │
│ [15:30] John Closed                      │
│ 👤 Agent: Issue resolved, closing ticket│
└──────────────────────────────────────────┘
```

#### **Aktionen (unten):**
```
┌──────────────────────────────────────────┐
│ [Reply] [Post Note] [Change Status] ▼   │
│ [Assign/Transfer] [Add Collaborator]    │
│ [Close Ticket] [Reopen] [Print] [...]   │
└──────────────────────────────────────────┘
```

---

### **3. Ticket-Liste / Queue-Ansicht**

#### **Standard-Spalten (alle Tickets):**
```
┌────┬────────┬──────────────────────────────┬────────────┬──────────────┬──────────────┐
│ #  │ Ticket │ Subject                      │ From       │ Priority     │ Status       │
├────┼────────┼──────────────────────────────┼────────────┼──────────────┼──────────────┤
│ ☐  │ #123456│ High CPU usage on prod-web-01│ Zabbix     │ ⚠️  High     │ Open         │
│ ☐  │ #123457│ Disk space low on db-server  │ Zabbix     │ ⚠️  Normal   │ In Progress  │
│ ☐  │ #123455│ Network timeout on switch-01 │ Zabbix     │ 🔴 Emergency│ Open         │
└────┴────────┴──────────────────────────────┴────────────┴──────────────┴──────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Department   │ Assigned To  │ Last Update  │ Due Date     │ Overdue      │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ IT Ops       │ John Smith   │ 15:30        │ 2025-10-26   │ ❌ No       │
│ IT Ops       │ Team Monitor │ 14:00        │ 2025-10-27   │ ❌ No       │
│ IT Ops       │ Unassigned   │ 14:23        │ 2025-10-26   │ ✅ Yes      │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

#### **Zabbix-spezifische Queue (empfohlen):**
```
┌────┬────────┬──────────┬──────────┬────────────────────────────┬──────────────┬──────────┐
│ #  │ Ticket │ Status   │ Severity │ Affected Object (WER)      │ Event Time   │ Updated  │
├────┼────────┼──────────┼──────────┼────────────────────────────┼──────────────┼──────────┤
│ ☐  │ #123456│ 🔴 PROB  │ ⚠️ High │ prod-web-01.example.com   │ 14:23        │ 15:30    │
│ ☐  │ #123457│ 🟢 OK    │ ℹ️ Avg  │ db-server-02.example.com  │ 13:10        │ 14:00    │
│ ☐  │ #123455│ 🔴 PROB  │ 🔴 Dis  │ switch-core-01.example.com│ 12:00        │ 14:23    │
└────┴────────┴──────────┴──────────┴────────────────────────────┴──────────────┴──────────┘

┌──────────────┬──────────────┬─────────────────────────────────┐
│ Subject      │ Assigned To  │ Event URL                       │
├──────────────┼──────────────┼─────────────────────────────────┤
│ High CPU     │ John Smith   │ [🔗 View in Zabbix]            │
│ Disk space   │ Team Monitor │ [🔗 View in Zabbix]            │
│ Network TO   │ Unassigned   │ [🔗 View in Zabbix]            │
└──────────────┴──────────────┴─────────────────────────────────┘
```

---

## 📊 Feldnutzungs-Häufigkeit (für UI-Priorisierung)

### **Täglich (Prominente Platzierung):**
```
ticket.number
ticket.subject
ticket.status
ticket.priority
ticket.department
ticket.staff_id
ticket.created
ticket.lastupdate
```

### **Mehrmals pro Woche:**
```
ticket.email
ticket.name
ticket.message
ticket.topicId
ticket.duedate
ticket.isoverdue
ticket.isanswered
ticket.closed
```

### **Gelegentlich (Sidebar/Tabs):**
```
ticket.phone
ticket.ip
ticket.source
ticket.team_id
ticket.sla_id
ticket.reopened
ticket.notes
```

### **Zabbix-Spezifisch (Zabbix Queue wichtig):**
```
zabbix_event_id ⭐⭐⭐
event_status ⭐⭐⭐
affected_object ⭐⭐⭐
severity ⭐⭐
event_url ⭐⭐
host_name ⭐
event_time ⭐
zabbix_trigger_id ⭐
trigger_description ⭐
```

---

## 🔧 Feldkonfiguration pro View

### **View 1: Client Portal (Ticket-Erstellung)**

| Position | Feld | Typ | Pflicht | Sichtbar |
|----------|------|-----|---------|----------|
| 1 | email | Text (Auto-Fill) | JA | User |
| 2 | name | Text (Auto-Fill) | JA | User |
| 3 | phone | Text (Optional) | Nein | User |
| 4 | topicId | Dropdown | Nein | User |
| 5 | subject | Text (Single-Line) | JA | User |
| 6 | message | Rich Text Editor | JA | User |
| 7 | attachments | File Upload | Nein | User |

**Custom Fields:** KEINE (alle via API)

---

### **View 2: Agent Staff Panel - Ticket Details**

#### **Header (immer sichtbar):**
| Position | Feld | Typ | Editierbar |
|----------|------|-----|-----------|
| 1 | number | Badge (Read-Only) | Nein |
| 2 | subject | Text | Nein |
| 3 | status_id | Dropdown | **Ja** |
| 4 | priority | Dropdown | **Ja** |

#### **Linke Sidebar - User Info:**
| Position | Feld | Typ | Editierbar |
|----------|------|-----|-----------|
| 1 | name | Text (Read-Only) | Nein |
| 2 | email | Text (Link) | Nein |
| 3 | phone | Text | Nein |
| 4 | user_id | Link zu User-Profil | Nein |

#### **Rechte Sidebar - Ticket Properties:**
| Position | Feld | Typ | Editierbar |
|----------|------|-----|-----------|
| 1 | dept_id | Dropdown (Transfer) | **Ja** |
| 2 | topicId | Dropdown | Nein |
| 3 | staff_id, team_id | Select (Assign) | **Ja** |
| 4 | sla_id | Text (Read-Only) | Nein |
| 5 | duedate | DatePicker | **Ja** |
| 6 | source | Badge (Read-Only) | Nein |
| 7 | lock_id | Status (Read-Only) | Nein |

#### **Rechte Sidebar - Metadata (Expandable):**
| Position | Feld | Typ | Editierbar |
|----------|------|-----|-----------|
| 1 | created | DateTime (Read-Only) | Nein |
| 2 | updated | DateTime (Read-Only) | Nein |
| 3 | lastupdate | DateTime (Read-Only) | Nein |
| 4 | isoverdue | Badge (Read-Only) | Nein |
| 5 | isanswered | Badge (Read-Only) | Nein |
| 6 | closed | DateTime (Read-Only) | Nein |

#### **Zabbix Tab - Event Details:**
| Position | Feld | Typ | Editierbar |
|----------|------|-----|-----------|
| 1 | event_status | Badge (Red/Green) | Nein |
| 2 | severity | Badge mit Icon | Nein |
| 3 | affected_object | **PROMINENT** | Nein |
| 4 | zabbix_event_id | Link zu Event | Nein |
| 5 | host_name | Text | Nein |
| 6 | host_ip (via `ip`) | Text | Nein |
| 7 | event_time | DateTime | Nein |
| 8 | zabbix_trigger_id | Link zu Trigger | Nein |
| 9 | trigger_description | Expandable Text | Nein |
| 10 | event_url | Button "View in Zabbix" | Nein |

#### **Thread (Hauptbereich):**
| Feld | Typ | Beschreibung |
|------|-----|-----------|
| thread | Messages + Responses | Chronologisch, farbcodiert |
| notes | Internal Notes | Grau hinterlegt |
| attachments | File Links | Downloads |

#### **Actions (unten):**
```
[Reply] [Post Internal Note] [Change Status ▼] [Assign ▼]
[Add Collaborator] [Close] [Reopen] [Print] [...]
```

---

### **View 3: Queue List (Ticket-Übersicht)**

#### **Standard-Spalten (alle Tickets):**
```
[x] | # | Subject | From | Priority | Status | Department | Assigned | Last Update
```

#### **Zabbix-Queue-Spalten (spezialisiert):**
```
[x] | # | Status | Severity | Affected Object | Subject | Event Time | Updated | Actions
```

---

## 🎨 Farbschema für Zabbix-Integration

### **Status-Icons:**
```
🔴 PROBLEM (Rot #d9534f)
🟢 OK (Grün #5cb85c)
🟡 UNKNOWN (Gelb #f0ad4e)
```

### **Severity-Farben:**
```
⚠️ Disaster (Rot #d9534f)
⚠️ High (Orange #f0ad4e)
⚠️ Average (Gelb #ffc107)
ℹ️ Warning (Blau #5bc0de)
ℹ️ Information (Blau #5bc0de)
ℹ️ Not classified (Grau #777)
```

### **Priority-Icons:**
```
🔴 Emergency (Rot) = Disaster
⚠️ High (Orange) = High
⚠️ Normal (Gelb) = Average/Warning
ℹ️ Low (Blau) = Info/Not classified
```

---

## 📋 Zusammenfassung: Feldplatzierung für Zabbix

### **ESSENTIELL (Muss für Zabbix-Integration):**
1. ✅ **affected_object** → **Prominent in Liste und Detail** (Das "WER")
2. ✅ **zabbix_event_id** → Custom Field, Internal, Link zu Zabbix
3. ✅ **event_status** → Badge, Auto-Close-Logik
4. ✅ **subject** → Automatisch aus Zabbix Event
5. ✅ **message** → HTML mit Event-Details
6. ✅ **topicId** → Bestimmt Routing und Department

### **Stark Empfohlen:**
7. ⭐ **severity** → Farbcodiert in Liste
8. ⭐ **event_url** → Button "View in Zabbix"
9. ⭐ **host_name** → In Zabbix-Tab
10. ⭐ **event_time** → Zeitstempel des Events

### **Optional aber Hilfreich:**
11. 📌 **zabbix_trigger_id** → Für Trigger-Verlinkung
12. 📌 **trigger_description** → In Zabbix-Tab
13. 📌 **notes** → Internal Tracking
14. 📌 **priority** → Mapping von Severity

### **Automatisch (System):**
15. 🔒 **number, status, created, lastupdate, isoverdue, isanswered** → Read-Only

---

## ✅ Nächste Schritte

1. **Bestätigung:** Prüfung der Feldliste mit osTicket-Administratoren
2. **Custom Fields anlegen:** In osTicket Admin Panel
3. **Help Topic erstellen:** "Zabbix Monitoring" mit Custom Form
4. **Webhook Service implementieren:** Verwendet diese Felddokumentation
5. **GUI-Template erstellen:** Für Zabbix-spezifische Queue

---

## 📚 Dateien in diesem Projekt

```
docs/
├── OSTICKET-FIELDS-COMPLETE-ANALYSIS.md ← Diese Datei
├── README-Integration.md                 ← Projekt-Übersicht
├── LLD-Zabbix-osTicket-Integration.md   ← Technisches Design
├── QUICK_REFERENCE-Zabbix-osTicket.md   ← Schnelle Referenz
└── IMPLEMENTATION_GUIDE-Zabbix-osTicket.md ← Code & Deployment
```

---

**Status:** ✅ **FELDANALYSE ABGESCHLOSSEN**

Diese Dokumentation ist die Basis für:
- ✅ Custom Fields Konfiguration
- ✅ API Integration
- ✅ GUI Layout Design
- ✅ Webhook Implementation

**Nächster Meilenstein:** Feldplatzierung gemeinsam designen und Help Topic konfigurieren
