# HLD — Egon2: Persönlicher KI-Assistent

**Version:** 1.8
**Stand:** 2026-05-02
**Autor:** Marco Doehler / Claude

> **Hinweis zu Audit-Dokumenten:** Stand der Audit-Dokumente: v1.5 — Findings aus Runde 2 und 3 sind in v1.7/v1.8 eingearbeitet; ältere Audits können teilweise obsolete Befunde enthalten.

---

## 1. Zielbeschreibung

**"Egon der 2."** (kurz: **Egon**) ist ein persönlicher KI-Assistent mit Handlungskompetenzen.

Er kommuniziert über **Matrix** und **Telegram**, nimmt Aufgaben entgegen und setzt sie um —
indem er **spezialisierte Agenten (Spezialisten)** beauftragt, die jeweilige Arbeit auszuführen.
Egon selbst ist der **Verwalter**: er versteht, delegiert, koordiniert und berichtet.

Die Spezialisten sind Sub-Agents mit eigenen System-Prompts und klar definierten Fähigkeiten.
Egon führt Buch über jeden Einsatz. Er berichtet dem User nur das, was der User wissen möchte.

---

## 2. Persönlichkeit

**Name:** Egon der 2. — kurz: Egon
**Charakter:** Britisch-satirisches Understatement, denkt an Douglas Adams / Blackadder.
Kompetent. Direkt. Nie servil. Kommentiert gelegentlich — präzise, nicht ausschweifend.

**Kommunikationsprinzipien:**
- Deutsch, mit gelegentlichen englischen Einwürfen wenn es passt
- Sagt unangenehme Dinge, aber mit Stil
- Keine Berichte, keine Analysen, keine `.md`-Dokumente über die eigene Arbeit — außer der User fordert explizit etwas an
- Knappe Antworten bevorzugt, ausführliche wenn nötig

---

## 3. Infrastruktur-Rollen

| LXC | Name | IP | Rolle für Egon2 |
|---|---|---|---|
| **128** | Egon2 | 10.1.1.202 | Produktiv-LXC — nur Egon2-App, keine Fremddateien (6C/6GB/20GB) |
| 105 | claude | 10.1.1.105:3001 | LLM-Backend (Claude Code API, OpenAI-kompatibel) |
| 107 | mcp-sequential | 10.1.1.107:8080 | Knowledge Store (MCP-Server, SQLite) |
| 126 | egon-werkstatt | 10.1.1.203 | **Entwicklung & Werkstatt** — Quellcode-Repo + Spezialist-Ausführung |
| 125 | SearXNG | 10.1.1.204:80 | News-Quelle für den täglichen Report |

**Trennung Produktiv / Entwicklung:**
Der Egon2-LXC (128) enthält ausschließlich die deployete Egon2-Applikation unter `/opt/egon2/`.
Quellcode-Entwicklung und Spezialisten-Ausführung finden auf **LXC 126** statt:

| Verzeichnis auf LXC 126 | Zweck |
|---|---|
| `/opt/Projekte/Egon2/` | Quellcode (Monorepo, git-verwaltet) |
| `/opt/Projekte/Egon2/werkstatt/<task-id>/` | Isolierte Arbeitsverzeichnisse der Spezialisten |

Deploy-Weg: LXC 126 Monorepo → `deploy.sh` → rsync → LXC 128 `/opt/egon2/`

---

## 4. Systemarchitektur

```
                    MATRIX                    TELEGRAM
                      │                          │
                      ▼                          ▼
           ┌──────────────────────────────────────────────┐
           │              INTERFACE LAYER                  │
           │         matrix-nio      python-telegram-bot   │
           │                 Message-Router                │
           │         (eingehende Msgs in async Queue)      │
           └────────────────────┬─────────────────────────┘
                                │
           ┌────────────────────▼─────────────────────────┐
           │           EGON — CORE ENGINE (Verwalter)      │
           │                                               │
           │  ┌─────────────┐  ┌────────────────────────┐ │
           │  │  Kontext-   │  │    Task-Manager         │ │
           │  │  Manager    │  │  pending→running→done   │ │
           │  └──────┬──────┘  └──────────┬─────────────┘ │
           │         │                    │               │
           │  ┌──────▼────────────────────▼─────────────┐ │
           │  │        Agent-Dispatcher (Verwalter)      │ │
           │  │   Analyse → Spezialist wählen → Brief    │ │
           │  │         → Ergebnis empfangen             │ │
           │  └──────────────────┬──────────────────────┘ │
           │                     │                        │
           │  ┌──────────────────▼──────────────────────┐ │
           │  │  AsyncIOScheduler (Europe/Berlin TZ)     │ │
           │  │  Persistent SQLite JobStore              │ │
           │  │  News-Report 07:30 | Health 03:00        │ │
           │  └──────────────────┬──────────────────────┘ │
           └─────────────────────┼────────────────────────┘
                                 │
           ┌─────────────────────▼────────────────────────┐
           │           SPEZIALISTEN-SCHICHT (10 Agenten)   │
           │  LLM-Client → http://10.1.1.105:3001          │
           └────────────────────┬─────────────────────────┘
                                │
           ┌────────────────────▼─────────────────────────┐
           │               EXECUTOR LAYER                  │
           │  SSH → LXC 126 (Werkstatt)   SSH → LXCs      │
           └────────────────────┬─────────────────────────┘
                                │
           ┌────────────────────▼─────────────────────────┐
           │               PERSISTENZ                      │
           │  Lokal SQLite (egon2.db)                      │
           │  LXC 107 Knowledge MCP (10.1.1.107:8080)      │
           │  BookStack | GitHub (egon2-knowledge)         │
           └──────────────────────────────────────────────┘
```

---

## 5. Interaktion & Eingabe

### 5.1 Eingabe-Syntax

Egon versteht **natürliche Sprache** — kein starres Befehlsformat nötig. Zur Orientierung gibt
es optionale Slash-Kommandos für häufige Aktionen:

| Kommando | Bedeutung |
|---|---|
| `/task <Beschreibung>` | Aufgabe explizit anlegen |
| `/note <Text>` | Notiz speichern |
| `/wissen <Text>` | Eintrag in Knowledge Store |
| `/status` | Aktive und zuletzt abgeschlossene Tasks anzeigen |
| `/stats` | Spezialist-Statistiken und Kosten |
| `/suche <Begriff>` | Knowledge Store durchsuchen |
| `/agenten` | Alle Spezialisten (builtin + dynamisch erzeugte) auflisten |
| `/hilfe` | Übersicht der Fähigkeiten |

Ohne Präfix analysiert Egon den Intent und klassifiziert automatisch:
- Ist es eine Aufgabe? → Task-Manager
- Ist es eine Notiz / Gedanke? → Secretary + Notes-Tabelle
- Ist es eine Frage? → Direkte Antwort oder Researcher
- Ist es mehrdeutig? → Egon fragt kurz nach

**Beispiel-Gespräch:**
```
Marco:  Recherchiere was sich bei Python 3.14 getan hat.
Egon:   Erledigt. Ich habe den Researcher beauftragt — dauert einen Moment.

[2 Minuten später]
Egon:   Python 3.14 bringt vor allem freie Threading-Verbesserungen (No-GIL-Experiment
        wird stabiler), t-strings als neue String-Typ-Klasse, und kleinere Optimierungen
        im Interpreter. Nichts Weltbewegendes. Der Researcher war enttäuscht.
```

### 5.2 Status-Feedback bei laufenden Tasks

```
Eingabe → Egon bestätigt sofort (< 2s):
  "Verstanden. [Spezialist] kümmert sich darum."

Bei Tasks > 30s → Zwischen-Update:
  "Noch in Bearbeitung — [Spezialist] ist dabei, [kurze Beschreibung]."

Bei Abschluss → Ergebnis-Nachricht

Bei Fehler → Egon meldet kurz was schiefgelaufen ist
  (nicht den Stack-Trace, aber den Grund)
```

Läuft eine Aufgabe noch wenn der User offline geht, wird das Ergebnis beim nächsten
Verbindungsaufbau über den Kanal zugestellt, auf dem die Anfrage eintraf.

### 5.3 Mehrdeutigkeit und Intent-Klassifikation

Egon entscheidet per LLM-Call ob eine Eingabe eine Aufgabe, Notiz, Wissensfrage oder
Konversation ist. Kriterien (im System-Prompt verankert):

- Enthält Verb + Ziel → Aufgabe (`task`)
- Beginnt mit "Merke", "Notiere", Gedanke ohne Ziel → Note
- Ist eine Frage → Direkte Antwort oder Researcher
- Unklar → kurze Rückfrage, max. eine

### 5.4 Onboarding (erster Start)

Beim ersten Kontakt sendet Egon eine knappe Begrüßung:

```
Egon:  "Egon der 2., zu Ihren Diensten. Oder kürzer: Egon. Ich nehme Aufgaben entgegen,
        recherchiere, entwickle, archiviere — und berichte nur wenn nötig.
        /hilfe zeigt was ich kann. Oder einfach anfangen."
```

`/hilfe` listet die wichtigsten Fähigkeiten und Kommandos in kompakter Form.

**Onboarding-Erkennung (DB-basiert, restart-fest):**
Bei jedem ankommenden User-Event prüft Egon vor der Verarbeitung:
```sql
SELECT COUNT(*) FROM conversations WHERE role='assistant'
```
Ergibt die Abfrage `0`, sendet Egon die Onboarding-Nachricht voraus. Es wird **kein**
AppState-Flag verwendet — der DB-Check ist autoritativ und überlebt Restarts/Crashes.

---

## 6. Spezialisten-System

### 6.1 Konzept

Egon ist der Verwalter. Er bewertet eingehende Aufgaben, wählt den passenden Spezialisten
aus der Registry und beauftragt ihn mit einem präzisen **Auftrag (Brief)**.
Der Spezialist führt aus — via eigenem System-Prompt und Claude Code API.
Egon empfängt das Ergebnis, bewertet es und antwortet dem User.

```
User-Anfrage
     │
     ▼
Egon klassifiziert Intent (task / note / question / conversation)
     │
     ▼ (bei task)
Agent-Registry: LLM-Klassifikation → Spezialist auswählen (siehe §6.2)
     │
     ▼
Brief erstellen (strukturiertes Format)
     │
     ▼
LLM-Call mit Spezialist-System-Prompt + Brief
     │
     ▼
Spezialist führt aus (ggf. SSH → LXC 126)
     │
     ▼
Ergebnis → Egon → User (kompakte Zusammenfassung)
     │
     ▼
Buchhaltungs-Eintrag: Spezialist, Brief, Ergebnis, Token, Kosten
```

### 6.2 Spezialist-Auswahl

Egon wählt Spezialisten **per LLM-Klassifikation** — kein Keyword- oder Capabilities-Score.
Der Intent-Klassifikations-Call (siehe §7.2 Schritt 1) liefert in einem einzigen Aufruf
sowohl den Intent als auch den passenden Spezialisten zurück.

**Klassifikations-Output:**
```json
{
  "intent": "task | note | question | conversation | cancel",
  "specialist": "researcher | journalist | it_admin | developer | analyst | controller | archivist | designer | secretary | inspector | dynamic"
}
```

**Matching-Ablauf:**

1. LLM-Call klassifiziert Intent + Spezialist (ein Call, zwei Outputs).
2. Bei `specialist ∈ {builtin-IDs}` → Spezialist direkt aus Registry laden.
3. Bei `specialist == "dynamic"`:
   a) Alle aktiven `dynamic_*`-Agenten dem LLM zur Auswahl vorlegen (mit `description`).
      LLM antwortet mit Agent-ID oder `"none"`.
   b) Bei `"none"` → Agenten-Erzeugungsfluss (→ Abschnitt 6.7).
4. Bei mehreren passenden dynamischen Kandidaten entscheidet das LLM; bei Gleichwertigkeit
   wird der mit niedrigerem `use_count` gewählt.

Das Capabilities-Feld in der Registry bleibt erhalten (für `/agenten` Anzeige, Audits, Statistik),
spielt aber im Matching keine Rolle mehr — die fachliche Zuordnung leistet das LLM.

### 6.3 Brief-Format

Jeder Auftrag an einen Spezialisten hat folgende Struktur:

```json
{
  "task_id": "uuid",
  "specialist": "researcher",
  "objective": "Was soll erreicht werden (1-2 Sätze)",
  "context": "Relevanter Kontext aus Knowledge Store und Gespräch",
  "constraints": ["Nur Quellen aus den letzten 7 Tagen", "Max. 3 Ergebnisse"],
  "expected_output": "Format und Inhalt des erwarteten Ergebnisses",
  "work_location": "local | lxc126 | lxc_any",
  "predecessor_confidence": null,
  "predecessor_note": null
}
```

**Predecessor-Felder (für mehrstufige Pipelines):**

In Pipelines, in denen mehrere Spezialisten nacheinander an derselben Aufgabe arbeiten
(z.B. Researcher → Journalist), reicht der vorherige Spezialist im Brief seines Nachfolgers
ein Qualitäts-Feedback weiter:

| Feld | Werte | Beschreibung |
|---|---|---|
| `predecessor_confidence` | `null` \| `"low"` \| `"medium"` \| `"high"` | Selbsteinschätzung des Vorgängers zur Qualität seines Outputs |
| `predecessor_note` | `null` \| Freitext | Optionaler Hinweis zur Datenlage / zu Einschränkungen |

**Heuristiken:**
- Researcher setzt `predecessor_confidence = "low"`, wenn er weniger als 2 brauchbare Quellen findet.
- Journalist (oder anderer Folge-Spezialist) muss bei `"low"` explizit auf die Datenlage hinweisen ("Quellenlage dünn — …").
- Bei `null` (kein Vorgänger oder nicht angegeben) wird das Feld ignoriert.

### 6.4 Spezialist-Registry (10 initiale Agenten)

| Spezialist | Kürzel | Capabilities | Arbeitsort |
|---|---|---|---|
| **Researcher** | `researcher` | `web_search`, `fact_check`, `summarize` | Egon2-LXC |
| **Journalist** | `journalist` | `write`, `report`, `news_format` | Egon2-LXC |
| **IT-Administrator** | `it_admin` | `ssh`, `systemctl`, `apt`, `monitoring` | LXCs via SSH |
| **Developer** | `developer` | `code`, `script`, `debug`, `shell` | LXC 126 |
| **Analyst** | `analyst` | `data_analysis`, `pattern`, `statistics` | Egon2-LXC |
| **Controller** | `controller` | `cost_tracking`, `agent_stats`, `budget` | Egon2-LXC |
| **Archivist** | `archivist` | `knowledge_write`, `knowledge_structure`, `tagging` | LXC 107 |
| **Designer** | `designer` | `ui_concept`, `layout`, `visual_structure` | Egon2-LXC |
| **Secretary** | `secretary` | `note_taking`, `structuring`, `prioritizing` | Egon2-LXC |
| **Inspector** | `inspector` | `health_check`, `agent_review`, `data_audit` | Egon2-LXC |

Die Registry ist **dynamisch erweiterbar** — Egon erzeugt bei Bedarf neue Spezialisten (→ Abschnitt 6.7).
Builtin-Agenten sind durch `created_by = 'seed'` von dynamisch erzeugten (`created_by = 'egon'`) unterscheidbar.

### 6.5 Spezialist-Datenmodell

```sql
agents (
    id                  TEXT PRIMARY KEY,   -- 'researcher' | 'dynamic_legal_analyst'
    name                TEXT NOT NULL,
    description         TEXT,
    system_prompt       TEXT NOT NULL,
    capabilities        TEXT,               -- JSON-Array
    work_location       TEXT,               -- 'local' | 'lxc126' | 'lxc_any'
    prompt_version      INTEGER DEFAULT 1,  -- erhöht bei jeder Prompt-Änderung
    status              TEXT DEFAULT 'active',
                            -- 'pending_approval' → neu erzeugt, einsatzfähig, vom Matcher berücksichtigt,
                            --                       wartet auf User-Aktivierung (`/agenten aktiviere`)
                            -- 'active'           → regulär nutzbar
                            -- 'inactive'         → nicht mehr für Matching herangezogen (Audit-Trail bleibt)
    created_by          TEXT DEFAULT 'seed', -- 'seed' | 'egon' | 'user'
    last_used_at        TIMESTAMP,          -- NULL bei nie genutzten Agenten
    use_count           INTEGER DEFAULT 0,  -- Anzahl abgeschlossener Assignments
    deactivated_reason  TEXT,               -- 'inactive_14d'|'3_failed_assignments'|'user_request'|'limit_reached'
    promoted_to_builtin BOOLEAN DEFAULT 0,  -- nach /agenten promote: created_by='user'
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
)

agent_assignments (
    id                  TEXT PRIMARY KEY,
    agent_id            TEXT REFERENCES agents(id),
    task_id             TEXT REFERENCES tasks(id),
    brief               TEXT,              -- JSON-Dokument (s. Brief-Format)
    result              TEXT,
    status              TEXT,              -- 'running'|'done'|'failed'|'cancelled'
    tokens_input        INTEGER,
    tokens_output       INTEGER,
    cost_estimate       REAL,
    duration_ms         INTEGER,
    quality_score       INTEGER,           -- 1–5
    prompt_version_used INTEGER,           -- Snapshot von agents.prompt_version zur Laufzeit
    assigned_at         TIMESTAMP,
    completed_at        TIMESTAMP
)

agent_prompt_history (
    id             TEXT PRIMARY KEY,
    agent_id       TEXT REFERENCES agents(id),
    prompt_version INTEGER,
    system_prompt  TEXT NOT NULL,
    changed_by     TEXT,               -- 'inspector' | 'user' | 'system'
    change_reason  TEXT,               -- z.B. 'test_failed: researcher_smoke'
    created_at     TIMESTAMP
)
```

### 6.7 Dynamische Agenten-Erzeugung

Liefert die LLM-Klassifikation `specialist == "dynamic"` und die Auswahl unter
bestehenden dynamischen Agenten ergibt `"none"` (siehe §6.2), erzeugt Egon
eigenständig einen neuen Spezialisten — ohne User-Interaktion, außer beim ersten
Einsatz des neuen Agenten.

#### Ablauf

```
LLM-Klassifikation: specialist="dynamic", Auswahl unter dynamic_* = "none"
          │
          ▼
Egon informiert User: "Kein passender Spezialist vorhanden. Ich richte einen ein — einen Moment."
          │
          ▼
LLM erzeugt vollständigen System-Prompt für den neuen Spezialisten
→ Pflicht-Bestandteile: Rollenidentität, Output-Format, Anti-Injection-Direktive, Brief-Format-Referenz
          │
          ▼
Validierung: Smoke-Test (vordefinierter Test-Corpus, nicht LLM-generiert)
  → 3 Meta-Fragen aus Domain-Question-Pool
  → Bewertung durch Egon-Verwalter (nicht durch neuen Agenten selbst)
          │
     ┌────┴────┐
   ≥2/3 ok   <2/3 ok
     │            │
     ▼            ▼
Agent in DB              Kein DB-Eintrag
speichern                → Fallback auf besten vorhandenen Spezialisten
(status='pending_approval') → User: "Einrichtung fehlgeschlagen. [X] übernimmt stattdessen."
     │
     ▼
User: "Neuer Spezialist einsatzbereit: [Name] ([Fachgebiet])."
     │
     ▼
Aufgabe ausführen — Spezialist bleibt 'pending_approval' bis Marco ihn über
`/agenten aktiviere <id>` freigibt. Der Matcher berücksichtigt sowohl 'active'
als auch 'pending_approval' (kein Deadlock bei Folge-Aufgaben).
```

**Hinweis (Drei-Wege-Status):** Neue dynamische Agenten starten mit `status='pending_approval'`.
In diesem Zustand sind sie regulär matching-fähig — der Matcher in §6.2 schließt sowohl
`'active'` als auch `'pending_approval'` ein. `'inactive'` wird vom Matcher ignoriert.
Eine Aktivierung über `/agenten aktiviere <id>` setzt den Status auf `'active'`
(rein kosmetisch / Vertrauensmarker — pragmatisch im Heimnetz-Betrieb).

#### Agenten-Spezifikation (LLM-generiert)

Egon generiert beim Anlegen eines neuen Spezialisten alle Felder eigenständig per LLM-Call:

| Feld | Beschreibung |
|---|---|
| `id` | Slug-Format: `dynamic_<fachgebiet>`, z.B. `dynamic_legal_analyst` |
| `name` | Lesbare Bezeichnung, z.B. "Rechtsanalyst" |
| `description` | Ein Satz: Was kann dieser Spezialist? |
| `capabilities` | JSON-Array abgeleiteter Fähigkeiten, z.B. `["legal_analysis", "contract_review"]` |
| `system_prompt` | Vollständig LLM-generierter System-Prompt — Egon entscheidet selbstständig über Inhalt und Struktur |
| `work_location` | fest: `local` — kein SSH für dynamische Agenten |
| `created_by` | `'egon'` |

Pflicht-Bestandteile im generierten System-Prompt (im Egon-Verwalter-System-Prompt verankert):
- Rollenidentität + Fachgebiet
- Erwartetes Output-Format
- Anti-Injection-Direktive (User-Input in `<external>`-Tags)
- Verweis auf Brief-Format

#### Grenzen und Schutzmechanismen

| Grenze | Wert | Begründung |
|---|---|---|
| Max. aktive dynamische Agenten | 20 | Verhindert unkontrolliertes Wachstum der Registry (`status` ∈ {`active`, `pending_approval`}) |
| Auslöser für Neuerzeugung | LLM-Auswahl liefert `"none"` | Kein Duplikat wenn ein vorhandener dynamischer Spezialist passt |
| Naming-Convention | `dynamic_*` | Klar von Builtin-IDs (`researcher`, `it_admin` etc.) unterscheidbar |
| System-Prompt-Länge | max. 2000 Token | Verhindert aufgeblähte, unzuverlässige Prompts |
| work_location bei dynamischen Agenten | nur `local` (Standard) | SSH-Zugriff auf LXCs nur für builtin-Agenten mit definiertem Scope |

Ist das Limit von 20 dynamischen Agenten erreicht, informiert Egon den User:
> *"Das Spezialistenlimit ist erreicht. Ich beauftrage stattdessen [bester Match]. Mit /agenten können Sie inaktive Spezialisten entfernen."*

#### Lebenszyklus dynamischer Agenten

```
Erzeugung (created_by='egon', status='pending_approval')
     │  (matching-fähig, wartet auf User-Freigabe — kein Deadlock)
     ▼
Nutzung: last_used_at + use_count werden aktualisiert
     │
     ▼  /agenten aktiviere <id>
status='active'
     │
     ▼
Inspector-Wochens-Audit (Mo 04:00):
  → use_count = 0 nach 14 Tagen → User-Hinweis + status='inactive'
  → use_count > 0, last_used_at > 30 Tage → Warnung an User
  → Spezialist fehlgeschlagen (3 aufeinanderfolgende failed assignments) → status='inactive' + User-Meldung
     │
     ▼
status='inactive': bleibt in DB (Audit-Trail), wird nicht mehr für Matching herangezogen
```

User kann über `/agenten` jederzeit:
- Alle Spezialisten (builtin + dynamisch, aktiv + inaktiv) sehen
- Dynamische Spezialisten aktivieren / deaktivieren
- Bewährte dynamische Spezialisten promoten (`/agenten promote <id>`)
- System-Prompt auf Vorgänger-Version rollbacken (`/agenten rollback <id>`)
- Statistiken (use_count, letzte Nutzung, Kosten) einsehen

#### Transparenz

Egon meldet bei jeder Neuerzeugung eines Spezialisten — knapp, einmalig:

```
Egon: "Ich habe einen neuen Spezialisten eingesetzt: Rechtsanalyst (rechtliche Analyse,
       Vertragsüberprüfung). Er wird diese Aufgabe bearbeiten."
```

Bei Folgeaufgaben desselben Typs wird der bestehende dynamische Spezialist genutzt —
ohne erneuten Hinweis.

---

### 6.6 Werkstatt — LXC 126

Wenn Developer oder IT-Admin auf Fremdsystemen arbeiten:

- SSH via User `egon` auf LXC 126 (`10.1.1.203`)
- Arbeitsverzeichnis: `/opt/Projekte/Egon2/werkstatt/<task-id>/`
- Nach Abschluss: Verzeichnis wird bereinigt (Retention: 24h nach Task-Abschluss)
- LXC 126: 36 GB freier Disk, 4 GB RAM

---

## 7. Komponenten

### 7.1 Interface Layer

**Matrix-Bot:** `matrix-nio` (async), Homeserver `matrix.doehlercomputing.de`,
Account `@egon2:doehlercomputing.de`, privater 1:1-Raum.

**Telegram-Bot:** `python-telegram-bot` v21, Token via Vaultwarden, Whitelist autorisierter User-IDs.

**Message-Router:** Gemeinsame async Queue zwischen Interface Layer und Core Engine.
Jede eingehende Nachricht erhält eine `request_id` (8-Zeichen-Hex) für durchgängiges Log-Tracing.
Consumer dispatcht jeden Auftrag als `asyncio.create_task()` mit `Semaphore(3)` — maximal 3
parallele LLM-Calls, Queue bleibt responsiv. Antwort geht auf den Eingangskanal zurück.

**Sub-Tasks und Semaphore-Verhalten:** Sub-Tasks des Developer-Spezialisten (oder anderer
Spezialisten, die intern weitere Spezialisten beauftragen) laufen **außerhalb** des
`Semaphore(3)` der Message-Consumer-Queue — sie erhalten einen eigenen internen Slot.
Der Parent-Task gibt seinen Consumer-Slot frei, **bevor** er auf Sub-Task-Ergebnisse
wartet (sonst Deadlock-Gefahr bei ≥3 parallelen Parent-Tasks mit Sub-Tasks).

**Eingabe-Sicherheit:** Alle externen Texte (Matrix, Telegram, SearXNG-Snippets, Knowledge-Store-Treffer)
werden vor Übergabe an den Kontext-Manager mit `safe_wrap(source, content)` in
`<external source="…">…</external>` gekapselt — verhindert Prompt Injection über alle Kanäle.

### 7.2 Agent-Dispatcher

```
1. Intent + Spezialist klassifizieren (ein LLM-Call, Output: {intent, specialist})
   → intent ∈ {task, note, question, conversation, cancel}
   → specialist ∈ {builtin-ID | "dynamic"}
2. Bei task:
   ├── specialist ∈ builtin-IDs → Spezialist aus Registry laden (status ∈ {active, pending_approval})
   └── specialist == "dynamic" → LLM wählt unter dynamic_*-Agenten
       ├── Auswahl != "none" → diesen verwenden
       └── Auswahl == "none" → Dynamischen Spezialisten erzeugen (→ 6.7)
                                ├── Smoke-Test bestanden → neuen Spezialisten verwenden
                                └── Smoke-Test fehlgeschlagen → besten vorhandenen Spezialisten verwenden
3. Kontext zusammenstellen (Knowledge Store + Rolling Window + Aufgabe)
4. Brief als JSON erstellen
5. Task-Status auf 'running' setzen (vor LLM-Call)
6. LLM-Call mit Spezialist-System-Prompt + Brief
7. Ergebnis bewerten
8. Task-Status auf 'done' / 'failed' setzen
9. use_count und last_used_at des Spezialisten aktualisieren
10. User-Antwort formulieren
11. agent_assignment Eintrag schreiben (in einer Transaktion mit Task-Update + Agent-Update)
```

Schritt 8, 9 und 11 laufen in einer SQLite-Transaktion — kein Teilergebnis ohne Buchhaltung.

### 7.3 Kontext-Manager

```
System-Prompt (Egon's Persönlichkeit + Fähigkeiten + aktuelles Datum/Uhrzeit)
+ Relevantes Wissen (LXC 107 Knowledge Store, Top-5 nach Keyword-Relevanz)
+ Rolling Window (letzte 20 Nachrichten aus conversations, kanalunabhängig)
+ Intent + Aufgaben-Brief
```

### 7.4 Scheduler

**Timezone: Europe/Berlin** (explizit in AsyncIOScheduler konfiguriert)

**Persistent JobStore:** APScheduler mit SQLite-basiertem JobStore (`/opt/egon2/data/scheduler.db`).
Jobs überleben Neustarts. Bei verpasstem Job-Zeitfenster (LXC war offline): einmaliger
Nachhol-Run beim nächsten Start (APScheduler `misfire_grace_time = 3600`).

| Job | Zeit | Ablauf |
|---|---|---|
| **News-Report** | täglich 07:30 | Researcher + Journalist → SearXNG → Matrix → Archivist |
| **System-Health-Check** | täglich 03:00 | Inspector → Komponenten, Daten, Spezialisten |
| **Wissens-Audit** | Mo 04:00 | Inspector + Archivist: Bereinigung + Struktur-Prüfung |
| **Wochenzusammenfassung** | Sa 20:00 | Analyst → Tasks + Knowledge der Woche → BookStack |
| **DB-Backup** | täglich 02:00 | `egon2.db` → `/opt/egon2/backup/` (7 Tage Rolling) |
| **Werkstatt-Cleanup** | täglich 01:00 | SSH → LXC 126: löscht `/opt/Projekte/Egon2/werkstatt/<task-id>/` für alle Tasks mit `status='done' AND completed_at < now() - 24h` |

**Ablauf News-Report:**
```
Scheduler → Researcher (SearXNG http://10.1.1.204 — Tech, KI, Allgemein)
          → Journalist (formuliert in Egon-Tonalität)
          → Matrix-Versand
          → Archivist (Knowledge Store, channel='news', expires_at=+30 Tage)
```

**Ablauf Wochenzusammenfassung (Sa 20:00):**
```
Analyst → liest tasks (letzte 7 Tage, status='done')
        → liest agent_assignments (Kosten, häufigste Spezialisten)
        → liest notes (letzte 7 Tage)
        → erstellt kompakte Wochenzusammenfassung
        → BookStack-Sync (Buch "Egon2 — Wochenzusammenfassungen")
```

### 7.5 Executor Layer

**SSH-Executor:** User `egon`, Ed25519-Key `/opt/egon2/.ssh/id_ed25519`.
Timeout: 120s pro Kommando. Bei Timeout: Status `failed`, Egon informiert User.

Befehle werden als **Argv-Liste** ausgeführt (kein Shell-String) — verhindert Shell-Injection via
Heredocs, Backtick-Substitution, Pipes und Argument-Chaining.
Jedes Binary hat eine eigene Argument-Allowlist (erlaubte Flags + Pfad-Patterns).
Beispiele: `systemctl` nur `status/is-active/is-enabled`; `apt` nur `list --installed / apt-cache show`;
`curl` nur GET ohne pipe-to-sh; `find` kein `-exec` / `-delete`.

**`pct`-Operationen:** Vollständig erlaubt — lesen und schreiben. Egon hat bewusst Vollzugriff auf
die LXC-Infrastruktur, das ist Teil seines autonomen Handlungsmandats. Akzeptiertes Risiko im Heimnetz.

**Shell-Executor:** Lokale Kommandos auf Egon2-LXC, gleiche Argv-Allowlist-Logik.
Destruktive Ops (`rm`, `mv`, `systemctl stop`) nur nach expliziter User-Bestätigung im Chat.

---

## 8. Persistenz

### 8.1 Lokales SQLite — `egon2.db` (Egon2-LXC)

SQLite wird mit **WAL-Modus** betrieben (`PRAGMA journal_mode=WAL`) —
ermöglicht gleichzeitige Lesezugriffe neben Schreiboperationen.

```sql
conversations (
    id          TEXT PRIMARY KEY,
    channel     TEXT,               -- 'matrix' | 'telegram'
    role        TEXT,               -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    source_channel  TEXT,
    status          TEXT DEFAULT 'pending',  -- pending|running|done|failed|cancelled|waiting_approval
    assigned_agent  TEXT REFERENCES agents(id),
    result          TEXT,
    parent_task_id  TEXT REFERENCES tasks(id),  -- für Sub-Tasks (max. Tiefe 2)
    request_id      TEXT,                        -- 8-Hex Correlation-ID aus IncomingMessage
    cancelled_reason TEXT,                       -- 'user_correction'|'user_request'|'system_timeout'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

notes (
    id               TEXT PRIMARY KEY,
    title            TEXT,
    content          TEXT NOT NULL,
    tags             TEXT,            -- JSON-Array
    source_channel   TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_knowledge INTEGER DEFAULT 0,  -- 0=pending | 1=synced | 2=error
    synced_bookstack INTEGER DEFAULT 0,  -- 0=pending | 1=synced | 2=error
    synced_github    INTEGER DEFAULT 0,  -- 0=pending | 1=synced | 2=error
    bookstack_page_id INTEGER DEFAULT NULL  -- für Update statt Create (Duplikat-Schutz)
)

agents (...)              -- s. Abschnitt 6.5
agent_assignments (...)   -- s. Abschnitt 6.5

health_checks (
    id           TEXT PRIMARY KEY,
    check_type   TEXT,   -- 'system' | 'data' | 'agent'
    target       TEXT,   -- Komponente, Domain oder Agent-ID
    status       TEXT,   -- 'ok' | 'repaired' | 'warning' | 'degraded'
    findings     TEXT,   -- JSON-Array der Befunde
    action_taken TEXT,
    checked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

scheduler_log (
    id           TEXT PRIMARY KEY,
    job_name     TEXT,
    started_at   TIMESTAMP,
    finished_at  TIMESTAMP,
    status       TEXT,   -- 'ok' | 'failed' | 'skipped'
    output       TEXT
)
```

### 8.2 Backup-Strategie (egon2.db)

Täglicher Backup-Job um 02:00 (vor dem Health-Check):

```
cp /opt/egon2/data/egon2.db   /opt/egon2/backup/egon2-$(date +%Y%m%d).db
cp /opt/egon2/data/scheduler.db /opt/egon2/backup/scheduler-$(date +%Y%m%d).db
→ Rotation: nur die letzten 7 Tage behalten
→ Backup-Verzeichnis: /opt/egon2/backup/ (auf gleichem LXC)
```

Für Disaster Recovery gilt: GitHub-Sync (`egon2-knowledge`) sichert den Knowledge Store.
Die `egon2.db` ist über den Rolling-Backup wiederherstellbar.
LXC-Sicherung erfolgt bei Bedarf auf Hypervisor-Ebene (Proxmox) — kein separates Anwendungs-Backup nötig.

### 8.3 Knowledge Store — LXC 107 (10.1.1.107:8080)

Vorhandene DB `mcp_knowledge_v5.db` wird per Migration erweitert.

**Migration-Sequenz (einmalig, vor erstem Deployment):**

```
1. MCP-Server auf LXC 107 stoppen:  systemctl stop mcp-sequential
2. Migration ausführen:              python3 /opt/Projekte/Egon2/egon2/knowledge/migration.py
3. MCP-Server starten:              systemctl start mcp-sequential
```

Die Migration ist idempotent (prüft via `migration_v6_applied`-Flag ob Schema bereits aktuell).
Egon2-Startup prüft in Stufe 3 (Knowledge Client init) ob Migration nötig ist —
bei fehlender FTS5-Tabelle warnt Startup (non-fatal), Volltextsuche fällt auf LIKE-Fallback zurück.

**Erweitertes Schema (neue Spalten in `knowledge_entries`):**

```sql
knowledge_type  TEXT DEFAULT 'general'
    -- 'general'   → langfristiges Wissen, Fakten, Präferenzen
    -- 'reference' → Zeiger auf Spezialwissen (BookStack, Docs, Pfade)
    -- 'news'      → News-Report-Einträge
    -- 'note'      → User-Notizen

domain  TEXT DEFAULT 'general'
    -- 'general' | 'it' | 'network' | 'project' | 'personal' | 'news'

importance  INTEGER DEFAULT 5   -- 1 (niedrig) bis 10 (kritisch)
source      TEXT                -- z.B. 'egon2/news-report', 'user/matrix'
references  TEXT                -- JSON: [{"type":"bookstack","url":"..."}]
expires_at  TIMESTAMP           -- NULL = permanent; news = +30 Tage
```

**Channels = Domains** (unified, kein separates Mapping nötig):

| Channel/Domain | Inhalt |
|---|---|
| `general` | Allgemeines Wissen, Fakten, User-Präferenzen |
| `it` | Infrastruktur, Konfigurationen, Lösungen |
| `network` | Netzwerk-spezifisches Wissen |
| `project` | Projektspezifisches Wissen |
| `personal` | Persönliche Informationen, Gewohnheiten |
| `news` | Tägliche News-Reports (30 Tage TTL) |
| `reference` | Zeiger auf externes Spezialwissen |

### 8.4 Synchronisation

| Ziel | Was | Wann |
|---|---|---|
| BookStack | Notizen, News-Reports | täglich 23:00 |
| BookStack | Wochenzusammenfassung | Sa 20:05 (nach Analyst-Job) |
| GitHub `egon2-knowledge` | Notizen als Markdown, Knowledge-Snapshots | täglich 23:30 |

---

## 9. Tech-Stack

| Schicht | Technologie | Detail |
|---|---|---|
| Sprache | Python 3.12+ | |
| Framework | FastAPI + uvicorn | |
| Scheduler | APScheduler **3.10+** — `AsyncIOScheduler` | Läuft im FastAPI-Lifespan-Kontext, gleicher Event-Loop. APScheduler 4.x NICHT verwenden (noch Beta, andere API). |
| Scheduler Persistence | APScheduler SQLiteJobStore | `/opt/egon2/data/scheduler.db` — Jobs überleben Neustarts |
| Matrix | `matrix-nio` (async) | |
| Telegram | `python-telegram-bot` v21 (async) | |
| Datenbank | SQLite via `aiosqlite`, WAL-Modus | |
| Knowledge Store | `httpx` async → LXC 107:8080 | Connection Pool (max 5) |
| SSH | `asyncssh` | Timeout 120s, kein Blocking des Event-Loops |
| News-Quelle | SearXNG `http://10.1.1.204` (Port 80, via Nginx) | |
| Paketmanager | `uv` | |

**APScheduler + FastAPI Integration (9-stufiger Startup, 7-stufiger Shutdown):**

```python
# main.py — Lifespan-Kontext
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup (Reihenfolge zwingend einhalten)
    await db.init()                          # 1. DB + WAL + Migrationen
    await task_repo.recover_orphaned()       # 2. running→pending Recovery
    await knowledge_client.connect()         # 3. Knowledge Store (soft-fail)
    await llm_client.ping()                  # 4. LLM + Verbindungstest
    consumer = MessageConsumer(Semaphore(3)) # 5. Queue + Dispatcher + Consumer
    await consumer.start()
    await matrix_bot.start()                 # 6. Matrix Bot
    await telegram_bot.initialize()          # 7. Telegram Bot
    await telegram_bot.start()
    telegram_bot.updater.start_polling(stop_signals=None)  # PTB: kein SIGTERM-Handler!
    scheduler.add_job(..., replace_existing=True)
    scheduler.start()                        # 8. Scheduler — NACH den Interfaces!
                                             #    (verhindert misfire-Runs ohne Bot)
    yield

    # Shutdown (spiegelverkehrt, mit Queue-Drain)
    scheduler.shutdown(wait=False)           # 1. Keine neuen Jobs
    await matrix_bot.stop()                  # 2. Kein neuer Input
    await telegram_bot.updater.stop()        # 3. Kein neuer Input
    await telegram_bot.stop()
    await message_queue.join(timeout=30)     # 4. Queue drainen (max 30s)
    await consumer.stop()                    # 5. Consumer + Tasks awaiten
    await ssh_executor.aclose()             # 6. SSH-Verbindungen schließen
    await db.checkpoint_and_close()         # 7. WAL-Checkpoint + DB close
```

---

## 10. Verzeichnisstruktur

```
/opt/Projekte/Egon2/              ← Quellcode auf LXC 126 (git-verwaltet)
├── pyproject.toml                ← Abhängigkeiten mit gepinnten Versionen (uv)
├── egon2/
│   ├── main.py                   ← FastAPI-App, 9-stufiger Lifespan
│   ├── settings.py               ← pydantic-settings BaseSettings, typisiert
│   ├── dependencies.py           ← FastAPI Depends-Provider (DB, LLMClient, State)
│   ├── state.py                  ← AppState-Dataclass (in app.state)
│   ├── exceptions.py             ← Domänenspezifische Exception-Hierarchie
│   ├── database.py               ← SQLite-Setup, WAL-Pragma, Migrations
│   ├── personality.py            ← Egon's System-Prompt + Charakter
│   ├── llm_client.py             ← Claude Code API Client (httpx async, retry)
│   ├── interfaces/
│   │   ├── matrix_bot.py
│   │   └── telegram_bot.py       ← stop_signals=None zwingend!
│   ├── core/
│   │   ├── message_queue.py      ← Async Queue + MessageConsumer (Semaphore 3)
│   │   ├── context_manager.py    ← safe_wrap() für alle externen Quellen
│   │   ├── task_manager.py       ← State-Machine inkl. cancelled
│   │   ├── agent_dispatcher.py   ← create_task Dispatching
│   │   └── scheduler.py
│   ├── agents/
│   │   ├── registry.py           ← Seed-Daten + LLM-basiertes Matching (§6.2)
│   │   ├── dynamic_factory.py    ← LLM-gestützte Agenten-Erzeugung
│   │   ├── smoke_test.py         ← Vordefinierter Test-Corpus
│   │   ├── researcher.py
│   │   ├── journalist.py
│   │   ├── it_admin.py
│   │   ├── developer.py
│   │   ├── analyst.py
│   │   ├── controller.py
│   │   ├── archivist.py
│   │   ├── designer.py
│   │   ├── secretary.py
│   │   └── inspector.py
│   ├── executors/
│   │   ├── ssh_executor.py       ← asyncssh, Argv-Liste (kein Shell), Allowlist
│   │   └── shell_executor.py     ← Argv-Allowlist, kein Shell-String
│   ├── knowledge/
│   │   ├── mcp_client.py         ← httpx Pool → LXC 107:8080, retry
│   │   └── migration.py          ← Schema-Erweiterung auf LXC 107
│   └── sync/
│       ├── bookstack_sync.py
│       └── github_sync.py
├── deploy/
│   └── deploy.sh                 ← rsync LXC 126 → LXC 128
├── docs/
│   └── HLD-Egon2.md
└── systemd/
    └── egon2.service

/opt/egon2/                       ← Deploy-Ziel auf LXC 128 (nur App-Code)
├── egon2/
├── data/
│   ├── egon2.db
│   └── scheduler.db              ← APScheduler Persistent JobStore
├── backup/
│   ├── egon2-YYYYMMDD.db        ← Rolling 7-Tage-Backup
│   └── scheduler-YYYYMMDD.db
└── .ssh/
    ├── id_ed25519                ← chmod 600, chown egon2:egon2
    └── id_ed25519.pub

/opt/Projekte/Egon2/werkstatt/    ← Auf LXC 126, Spezialist-Arbeitsverzeichnis
└── <task-id>/                    ← Cleanup: 24h nach Task-Abschluss
```

---

## 11. Deployment

- **Egon2-LXC:** LXC 128, IP `10.1.1.202`, 6 Cores, 6 GB RAM, 20 GB Disk
- **Werkstatt:** LXC 126 (10.1.1.203) — Quellcode + Spezialist-Ausführung
- **Deploy:** `deploy.sh` → rsync von LXC 126 → LXC 128 → systemd restart
- **Service:** `egon2.service` (system-level, `Restart=on-failure`, `After=network-online.target`)

---

## 12. Self-Monitoring

### 12.1 System-Check (täglich 03:00)

| Komponente | Prüfung | Erwartetes Ergebnis |
|---|---|---|
| LLM-API (10.1.1.105:3001) | HTTP-Request Mini-Prompt | Antwort < 30s |
| Knowledge MCP (10.1.1.107:8080) | Lese-Query | HTTP 200 |
| SQLite lokal | Lese-/Schreibtest `egon2.db` | Kein Fehler |
| SSH-Executor | `echo ok` via SSH auf LXC 126 | Exit-Code 0 |
| SearXNG (10.1.1.204:80) | Suchanfrage | ≥ 1 Ergebnis |

### 12.2 Daten-Aktualitätsprüfung

**Täglich (im Health-Check):**
- `expires_at < now()` → `is_active = 0`
- Verwaiste `reference`-Einträge ohne erreichbare URL → markieren

**Wöchentlich Mo 04:00 (Archivist + Inspector):**
- Inhaltlich ähnliche Einträge zusammenführen
- Einträge älter 90 Tage ohne Update → zur Überprüfung markieren (`importance -= 1`)
- Einträge ohne `domain`/`tags` → Inspector vervollständigt per LLM

### 12.3 Spezialisten-Review (täglich im Health-Check)

**Builtin-Spezialisten** bekommen eine fest definierte Test-Aufgabe.
**Dynamisch erzeugte Spezialisten** (`created_by='egon'`) erhalten eine generische Test-Aufgabe,
die Inspector per LLM aus dem `description`-Feld des Agenten ableitet — kein festes Test-Skript nötig.

Jeder Spezialist bekommt eine Test-Aufgabe:

| Spezialist | Test-Aufgabe |
|---|---|
| `researcher` | SearXNG-Suche "Python asyncio", 2 Ergebnisse zurückgeben |
| `journalist` | Einen Satz über Wiesbaden im Egon-Stil formulieren |
| `it_admin` | Uptime von LXC 126 via SSH zurückgeben |
| `developer` | Python-Funktion schreiben: zwei Zahlen addieren |
| `analyst` | Unterschied mean / median in 2 Sätzen erklären |
| `controller` | Summe der letzten 7 `agent_assignments.cost_estimate` berechnen |
| `archivist` | 3 zuletzt aktualisierte Knowledge-Einträge zurückgeben |
| `designer` | Minimales Chat-UI-Layout in 3 Punkten beschreiben |
| `secretary` | Notiz strukturieren: "morgen einkaufen, Milch, Brot, Kaffee" |
| *dynamisch* | Inspector leitet Test aus `description` ab — z.B. bei `dynamic_legal_analyst`: "Erkläre den Unterschied zwischen AGB und Individualvertrag in 2 Sätzen" |

**Reparatur-Ablauf bei Testversagen:**

```
Test fehlgeschlagen
     │
     ▼
Inspector analysiert Fehlerursache
     │
     ▼
Automatische Reparatur (System-Prompt korrigieren, Capabilities anpassen)
     │
     ├── Test erneut bestanden → Status: 'repaired' → kein User-Bericht
     │
     └── Reparatur erfolglos → Status: 'degraded'
                              → is_active = 0
                              → User-Meldung via Matrix (+ Telegram)
```

### 12.4 Benachrichtigungs-Logik

```
Alle ok / repaired       → kein Bericht, nur health_checks DB-Eintrag
System-/Daten-warning    → kurze Zusammenfassung via Matrix
degraded / critical      → sofortige Meldung via Matrix + Telegram
```

---

## 13. Implementierungs-Phasen

### Phase 1 — Grundgerüst
- [ ] `pyproject.toml` mit gepinnten Versionen (`apscheduler>=3.10,<4`, `httpx`, `aiosqlite`, `matrix-nio`, `python-telegram-bot==21.*`)
- [ ] FastAPI-Skeleton: `main.py`, `settings.py`, `dependencies.py`, `state.py`, `exceptions.py`
- [ ] SQLite-Schema (alle Tabellen inkl. `request_id`, `cancelled_reason`, `agent_prompt_history`)
- [ ] Egon's Persönlichkeit (`personality.py`)
- [ ] LLM-Client (`httpx` async, 3-Retry mit Backoff `[1,2,4]s` bei ConnectError/Timeout)
- [ ] Agent-Registry mit **10 Builtin-Spezialisten** (Seed-Daten); Matching per LLM-Klassifikation (§6.2)
- [ ] MessageConsumer (async Queue + `create_task` + `Semaphore(3)`)
- [ ] Matrix-Bot (Empfangen + Antworten, `safe_wrap()` für alle Eingaben)
- [ ] Kontext-Manager (Rolling Window, `safe_wrap()` für Knowledge/SearXNG)
- [ ] Intent-Klassifikation (task / note / question / conversation / cancel)
- [ ] Task-State-Machine inkl. `cancelled`-Status
- [ ] 9-stufiger Lifespan (Scheduler als letzte Stufe) + 7-stufiger Shutdown mit Queue-Drain
- [ ] Deployment auf LXC 128

### Phase 2 — Spezialisten & Ausführung
- [ ] Agent-Dispatcher (LLM-Klassifikation Intent+Spezialist → Brief → `create_task` Dispatching)
- [ ] Buchhaltungs-Logik (Transaktion: Task + agent_assignment + `prompt_version_used` + Agent-Stats)
- [ ] SSH-Executor (asyncssh, Argv-Liste ohne Shell, Argument-Allowlist je Binary) + User `egon`
- [ ] Shell-Executor (gleiche Argv-Allowlist-Logik)
- [ ] `pct`-Vollzugriff in SSH-Allowlist (lesen + schreiben — autonomes Handlungsmandat)
- [ ] Developer-Spezialist → Werkstatt LXC 126
- [ ] Status-Feedback (sofortige Bestätigung + Zwischen-Updates)
- [ ] Cancel-Intent-Erkennung + Task-Stornierung
- [ ] Telegram-Bot (`stop_signals=None` zwingend)
- [ ] Dynamische Agenten-Erzeugung (→ Abschnitt 6.7)
  - [ ] LLM-Auswahl unter `dynamic_*`-Agenten (Duplikat-Check) vor Neuerzeugung
  - [ ] LLM-generierter System-Prompt (Pflicht-Bestandteile im Verwalter-Prompt verankert)
  - [ ] Smoke-Test mit vordefinierten Test-Corpus (nicht LLM-generiert)
  - [ ] `status='pending_approval'` bei Erzeugung (matching-fähig), Aktivierung via `/agenten aktiviere` setzt auf `'active'`
  - [ ] Limit-Prüfung (max. 20 dynamische Agenten)
  - [ ] `/agenten`-Kommando (Liste, aktiviere, deaktiviere, promote, rollback)
  - [ ] `agent_prompt_history` bei jeder Prompt-Änderung befüllen

### Phase 3 — Wissen & Notizen
- [ ] Knowledge-Client für LXC 107 (httpx Pool, retry)
- [ ] DB-Migration auf LXC 107 (Schema erweitern)
- [ ] Archivist-Spezialist
- [ ] Notizen-Erfassung (Secretary + `/note`)
- [ ] Knowledge-Abfrage (`/suche`)

### Phase 4 — Automatisierung & Sync
- [ ] Scheduler (nach Phase 1 Lifespan-Grundstruktur, Jobs in Phase 4 vervollständigen)
- [ ] News-Report-Job (Researcher + Journalist + SearXNG, `safe_wrap()` für Snippets)
- [ ] DB-Backup-Job (täglich 02:00, egon2.db + scheduler.db, Rolling 7 Tage)
- [ ] Werkstatt-Cleanup-Job (täglich 01:00, SSH → LXC 126: `werkstatt/<task-id>/` für `done`-Tasks > 24h löschen)
- [ ] Wochenzusammenfassung-Job (Analyst, Sa 20:00)
- [ ] BookStack-Sync (dreistufige Sync-Flags, `bookstack_page_id` für Dedup)
- [ ] GitHub-Sync (lokal als Master, Force-Push-Strategie dokumentiert)
- [ ] Onboarding-Nachricht (erster Kontakt — DB-Check `SELECT COUNT(*) FROM conversations WHERE role='assistant'`, kein AppState-Flag)

### Phase 5 — Self-Monitoring
- [ ] Inspector-Spezialist + fester Test-Corpus (builtin) / LLM-abgeleiteter Test (dynamisch)
- [ ] System-Health-Check (täglich 03:00) + einfacher Retry vor Alarm
- [ ] Daten-Aktualitätsprüfung + wöchentlicher Audit
- [ ] Spezialisten-Review mit `agent_prompt_history`-Rollback bei Reparatur
- [ ] `health_checks` Tabelle + Benachrichtigungs-Logik
- [ ] Lebenszyklus-Prüfung dynamischer Agenten (`inactive_14d`, `3_failed_assignments`)

---

## 14. Vorbereitungsaufgaben

- [x] LXC 128 → `Egon2` umbenannt, IP `10.1.1.202` (2026-05-02)
- [x] LXC 128 bereinigt (OpenClaw, Twitch-STT, PowerShell entfernt)
- [ ] Matrix-Account `@egon2:doehlercomputing.de` anlegen
- [ ] Telegram-Bot registrieren, Token in Vaultwarden
- [ ] GitHub-Repo `egon2-knowledge` anlegen (privat)
- [ ] User `egon` auf Proxmox + alle LXCs + LXC 126 anlegen, SSH-Key verteilen
      sudo-Scope: `NOPASSWD: /usr/bin/apt, /bin/systemctl, /usr/sbin/pct`
      **Hinweis:** `pct` erlaubt effektiv root-Zugriff auf alle LXCs — das ist so gewollt.
      Egon hat autonomes Handlungsmandat. Akzeptiertes Risiko im privaten Heimnetz.
      Vollständige Sudoers-Vorlage: LLD-Architektur.md § 2.7.
- [ ] Marco's Telegram-User-ID für Whitelist
