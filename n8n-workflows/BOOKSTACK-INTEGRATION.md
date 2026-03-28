# Shared Services – Integration & Zugriff

> Dieses Dokument beschreibt alle gemeinsam genutzten Dienste der Infrastruktur.
> Jedes Projekt hat Zugriff auf BookStack, GitHub und Vaultwarden.

---

# 1. BookStack – Wissensdatenbank & Protokolle

## Ziel

Alle Dienste und Projekte dokumentieren ihre Arbeit, Entscheidungen und Erkenntnisse in BookStack. Das schafft eine nachvollziehbare Betriebshistorie und macht das System für Marco transparent.

## BookStack API

| Parameter | Wert |
|-----------|------|
| Base-URL | `https://bookstack.doehlercomputing.de/api` |
| Auth-Header | `Authorization: Token <token_id>:<token_secret>` |
| Content-Type | `application/json` |
| Format | Markdown (`markdown`-Feld) |

**API-Token** (shared, aus Vaultwarden: Org "Bots" → "BookStack API"):
```
a5FgBtyb3qJCZZRM2zgpvMn0eIMVIkcJ:fRt0WwEHGwRvZh5YzC8djKZ6rM0rJrin
```

## Buch-Struktur

| Buch | ID | Kapitel | Kapitel-ID | Nutzer |
|------|----|---------|-----------|--------|
| Betriebsprotokolle – Automatisierte Dienste | 90 | Egon | 91 | Egon |
| | | SuperOrchestrator | 92 | SuperOrchestrator |
| | | Orchestrator | 93 | Orchestrator |

## Seite erstellen (POST)

```bash
curl -s -X POST https://bookstack.doehlercomputing.de/api/pages \
  -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "chapter_id": <KAPITEL_ID>,
    "name": "Seitentitel",
    "markdown": "## Inhalt\n\nMarkdown-Text hier"
  }'
```

## Seite aktualisieren (PUT)

```bash
curl -s -X PUT https://bookstack.doehlercomputing.de/api/pages/<PAGE_ID> \
  -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Seitentitel",
    "markdown": "## Inhalt\n\nAktualisierter Inhalt"
  }'
```

## Python-Hilfsfunktion

```python
import urllib.request, json
from datetime import datetime

BS_TOKEN = "a5FgBtyb3qJCZZRM2zgpvMn0eIMVIkcJ:fRt0WwEHGwRvZh5YzC8djKZ6rM0rJrin"
BS_URL = "https://bookstack.doehlercomputing.de/api"

def bookstack_create_page(chapter_id: int, title: str, markdown: str) -> dict:
    data = {"chapter_id": chapter_id, "name": title, "markdown": markdown}
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BS_URL}/pages", data=body, method="POST",
        headers={"Authorization": f"Token {BS_TOKEN}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def bookstack_update_page(page_id: int, title: str, markdown: str) -> dict:
    data = {"name": title, "markdown": markdown}
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BS_URL}/pages/{page_id}", data=body, method="PUT",
        headers={"Authorization": f"Token {BS_TOKEN}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)
```

---

## Egon – Dokumentationsrichtlinie

**Kapitel-ID:** 91 | **Wann:** Nach jeder abgeschlossenen Interaktion mit Marco

### Was dokumentieren

| Ereignis | Seitenformat | Inhalt |
|----------|-------------|--------|
| Aufgaben-Delegation | `YYYY-MM-DD – <Aufgabe>` | Aufgabe, Klassifikation, an wen delegiert, Ergebnis |
| Infrastruktur-Aktion | `YYYY-MM-DD – Infrastruktur: <Aktion>` | Was geändert, warum, Auswirkung |
| Erkenntnis / Lernen | `Erkenntnis: <Thema>` | Was gelernt, wie für Zukunft relevant |

### Seitenvorlage

```markdown
## Kontext
- **Datum:** YYYY-MM-DD HH:MM
- **Kanal:** Matrix / Telegram / TUI
- **Marco-Anfrage:** <kurze Zusammenfassung>

## Klassifikation
- **Typ:** Infrastruktur-Aufgabe / Software-Entwicklung / Auskunft / Wartung
- **Komplexität:** einfach (selbst ausgeführt) / komplex (an SuperOrchestrator delegiert)

## Aktion
<Was wurde getan oder delegiert>

## Ergebnis
<Ergebnis / Status / Offene Punkte>
```

---

## SuperOrchestrator – Dokumentationsrichtlinie

**Kapitel-ID:** 92 | **Wann:** Nach Abschluss jedes koordinierten Workflows

### Was dokumentieren

| Ereignis | Seitenformat | Inhalt |
|----------|-------------|--------|
| Workflow abgeschlossen | `YYYY-MM-DD – Workflow: <Name>` | Aufgabe, Routing-Entscheidung, Ergebnis |
| Routing-Entscheidung | Teil des Workflow-Protokolls | Warum welcher Dienst gewählt |
| Fehlgeschlagener Workflow | `YYYY-MM-DD – Fehler: <Workflow>` | Fehler, Root Cause, Maßnahme |

### Seitenvorlage

```markdown
## Workflow-Details
- **Datum:** YYYY-MM-DD HH:MM
- **Quelle:** Egon / direkt
- **Aufgabe:** <Aufgabenbeschreibung>

## Routing-Entscheidung
- **Ziel-Dienst:** Orchestrator / agent-pipeline / n8n
- **Begründung:** <Warum dieser Dienst>

## Ausführung
- **Status:** Erfolgreich / Fehlgeschlagen / Teilweise
- **Dauer:** <Zeit>

## Ergebnis & Erkenntnisse
<Ergebnis, Besonderheiten, was für zukünftige Aufgaben relevant ist>
```

---

## Orchestrator – Dokumentationsrichtlinie

**Kapitel-ID:** 93 | **Wann:** Nach Abschluss jedes Produktions-Workflows

### Was dokumentieren

| Ereignis | Seitenformat | Inhalt |
|----------|-------------|--------|
| Software-Workflow | `YYYY-MM-DD – <Projektname>: <Feature>` | Schritte, Agenten-Jobs, Ergebnis |
| Deployment | `YYYY-MM-DD – Deploy: <Service>` | Was deployt, Version, Ziel-LXC |
| Code-Qualität / Review | Teil des Workflow-Protokolls | Erkenntnisse aus Code-Reviews |
| Fehler im Workflow | `YYYY-MM-DD – Fehler: <Workflow>` | Schritt, Fehler, Lösung |

### Seitenvorlage

```markdown
## Workflow-Details
- **Datum:** YYYY-MM-DD HH:MM
- **Aufgabe:** <Aufgabe vom SuperOrchestrator>
- **Projekt:** <Projektname / Repository>

## Workflow-Schritte
| Schritt | Agent-Job | Status | Ergebnis |
|---------|-----------|--------|---------|
| 1 | <Beschreibung> | ✓/✗ | <Kurzfassung> |
| 2 | ... | | |

## Code & Deployment
- **Geänderte Dateien:** <Liste>
- **Deployt auf:** LXC <ID> / keines
- **Tests:** bestanden / fehlgeschlagen

## Erkenntnisse
<Was hat gut funktioniert, was sollte beim nächsten Mal anders gemacht werden>
```

---

## Abgrenzung: Was wird NICHT dokumentiert

| Dienst | Nicht dokumentieren |
|--------|-------------------|
| Egon | Reine Auskunftsfragen ohne Aktion (z.B. "Wie spät ist es?") |
| SuperOrchestrator | Interne Routing-Logik ohne Ergebnis (nur bei Abschluss) |
| Orchestrator | Einzelne Agent-Prompts (zu granular) – nur Gesamt-Workflow |

---

# 2. GitHub – Code & Änderungshistorie

## Organisation

| Parameter | Wert |
|-----------|------|
| GitHub Org/User | https://github.com/marcoFPO |
| Zweck | Code-Repositories, Dokumentation, Änderungsverfolgung |
| Scope | Alle Projekte dokumentieren Änderungen via Commits/PRs/Issues |

**GitHub Token** (aus Vaultwarden, Org "Bots" → "Standardsammlung" → "GitHub API Token")

## Konventionen

### Commits
```bash
# Aussagekräftige Commit-Messages mit Kontext
git commit -m "feat(modul): kurze Beschreibung was und warum"
git commit -m "fix(service): Fehlerbeschreibung und Lösung"
git commit -m "docs: Dokumentation aktualisiert"
```

### Issues – Aufgaben dokumentieren
```bash
# Issue erstellen via GitHub CLI
gh issue create \
  --title "Kurze Aufgabenbeschreibung" \
  --body "## Kontext\n...\n## Ziel\n..." \
  --label "task"
```

### Pull Requests – Änderungen nachhalten
```bash
# PR erstellen
gh pr create \
  --title "Beschreibung der Änderung" \
  --body "## Was wurde geändert\n...\n## Warum\n..."
```

### Python – GitHub API

```python
import urllib.request, json

GH_TOKEN = "<token-aus-vaultwarden>"
GH_ORG   = "marcoFPO"

def gh_create_issue(repo: str, title: str, body: str, labels: list = None) -> dict:
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_ORG}/{repo}/issues",
        data=json.dumps(data).encode(), method="POST",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)
```

## Was wird wo dokumentiert

| Ereignis | GitHub-Aktion |
|----------|--------------|
| Neue Funktionalität | Feature-Branch + PR |
| Bugfix | Issue + Fix-Commit + PR |
| Deployment | Commit mit Deploy-Tag |
| Konfigurationsänderung | Commit in entsprechendem Repo |
| Erkannte Probleme | Issue erstellen |

---

# 3. Vaultwarden – Credentials & Secrets

## Zugang

| Parameter | Wert |
|-----------|------|
| URL | `http://10.1.1.110` (LXC 127) |
| Organisation | **Bots** |
| Sammlung | **Standardsammlung** |
| CLI | `bw` (Bitwarden CLI, installiert) |
| Login | `doehlerm@arcor.de` |

> Alle Projekte und Dienste lesen Credentials ausschließlich aus Vaultwarden.
> **Keine Secrets in Code, Config-Dateien oder Git-Repositories speichern.**

## Bitwarden CLI

```bash
# Einmalig einloggen (Session-Token speichern)
export BW_SESSION=$(bw login doehlerm@arcor.de --raw)
# oder bei bereits eingeloggtem Account:
export BW_SESSION=$(bw unlock --raw)

# Item aus "Bots"-Organisation abrufen
bw get item "Service-Name" --session "$BW_SESSION"

# Passwort direkt abrufen
bw get password "Service-Name" --session "$BW_SESSION"

# Notiz abrufen (z.B. für API-Tokens)
bw get notes "Service-Name" --session "$BW_SESSION"
```

## Python – Vaultwarden via CLI

```python
import subprocess, json

def vaultwarden_get(item_name: str, session: str, field: str = "password") -> str:
    result = subprocess.run(
        ["bw", "get", field, item_name, "--session", session],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

def vaultwarden_get_item(item_name: str, session: str) -> dict:
    result = subprocess.run(
        ["bw", "get", "item", item_name, "--session", session],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)
```

## Vorhandene Credentials (Org "Bots" → Standardsammlung)

| Name in Vaultwarden | Inhalt | Genutzt von |
|--------------------|--------|-------------|
| BookStack API | Token-ID:Token-Secret | Egon, SuperOrchestrator, Orchestrator |
| GitHub API Token | Personal Access Token | Alle Projekte |
| NetBox API Token | REST API Token | n8n, Egon |
| Claude API Key | Anthropic API Key | claude-code-api (LXC 105) |

## Neue Credentials hinzufügen

Neue Secrets immer in **Org "Bots" → Standardsammlung** anlegen – nie lokal speichern.

```bash
# Neues Item anlegen
bw create item "$(bw get template item | jq \
  '.name="Service-Name" | .login.password="secret" | .organizationId="<bots-org-id>"' \
)" --session "$BW_SESSION"
```

---

# Zusammenfassung: Shared Service Endpoints

| Dienst | URL / Endpoint | Auth-Quelle |
|--------|---------------|-------------|
| BookStack | `https://bookstack.doehlercomputing.de/api` | Vaultwarden: "BookStack API" |
| GitHub | `https://api.github.com` / `https://github.com/marcoFPO` | Vaultwarden: "GitHub API Token" |
| Vaultwarden | `http://10.1.1.110` | Login: `doehlerm@arcor.de` |

---

# 4. Projektstruktur – /opt/Projekte

## Ablageort

Alle Projekte werden zentral unter `/opt/Projekte/` verwaltet.

```
/opt/Projekte/
├── Overview/              ← Infrastruktur-Dokumentation (diese Datei)
├── Orchestrator/          ← Claude Orchestrator (LXC 131)
├── agent-pipeline/        ← Agent Pipeline (LXC 133)
├── claude-code-api-local/ ← Claude Code API (LXC 105)
├── Ernährung/             ← Ernährungs-App
├── egons-tagebuch/        ← Egon Hugo-Website (LXC 134)
├── n8n-workflows/         ← n8n Workflow-Definitionen (LXC 117)
├── Mailserver/            ← Mailserver-Konfiguration (LXC 121)
├── Orchestrator/          ← SuperOrchestrator / Orchestrator
├── <weiteres Projekt>/
└── BOOKSTACK-INTEGRATION.md  ← diese Datei (in jedem Projektordner)
```

## Verfügbarkeit

Die Struktur `/opt/Projekte/` ist auf **allen relevanten Systemen** verfügbar:

| System | Rolle | Zugriff auf /opt/Projekte |
|--------|-------|--------------------------|
| Entwicklungshost | Primäres Arbeits- und Claude-Code-System | lokal (primär) |
| LXC 105 (claude) | Claude Code API, GitHub Actions Runner | verfügbar |
| LXC 131 (Orchestrator) | Softwareproduktion | verfügbar |
| LXC 133 (agent-pipeline) | Agent-Ausführung | verfügbar |

## Konventionen

- Jedes Projekt hat einen **eigenen Unterordner** unter `/opt/Projekte/`
- Die Datei `BOOKSTACK-INTEGRATION.md` liegt in **jedem Projektordner** (diese Datei)
- Projekte werden via **GitHub** (`https://github.com/marcoFPO`) versioniert
- Deployment erfolgt per `rsync` oder `git push` auf das jeweilige Zielsystem

## Neues Projekt anlegen

```bash
# Verzeichnis erstellen
mkdir /opt/Projekte/<projektname>
cd /opt/Projekte/<projektname>

# Git initialisieren und mit GitHub verknüpfen
git init
gh repo create marcoFPO/<projektname> --private --source=. --remote=origin

# Shared-Services-Dokument hineinkopieren
cp /opt/Projekte/Overview/BOOKSTACK-INTEGRATION.md .

# Ersten Commit
git add .
git commit -m "feat: Projektstruktur initialisiert"
git push -u origin main
```
