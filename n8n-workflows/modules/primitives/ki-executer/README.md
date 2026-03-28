# Primitive: KI-Executer

**Status:** Production Ready
**Version:** 2.0 (Umbenannt von HTTP Request Wrapper)
**Tier:** 1 (Primitive Module)
**Workflow ID:** `yt2okRvNmGItRjCI`

---

## 📋 Übersicht

Spezialisierter HTTP-Wrapper für alle KI/Claude-API Aufrufe über den Claude Code API Server (10.1.1.105:3001). Wird verwendet für alle LLM-basierten Workflows und KI-gestützten Automatisierungen.

**Basis-Architektur:**
```
Input (Prompt + Parameter)
  → HTTP POST Call
  → API Response passthrough
```

---

## 🔌 INPUT PARAMETER

### Erforderlich:

| Parameter | Typ | Beschreibung | Beispiel |
|-----------|-----|-------------|----------|
| `prompt` | string | Der Prompt/die Anfrage für die API | `"Analysiere diese Logs"` |

### Optional:

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|-------------|
| `model` | string | `haiku` | Modell: `haiku`, `sonnet`, `opus` |
| `temperature` | number | `0.1` | Kreativität (0.0 = deterministisch, 1.0 = kreativ) |

---

## 📤 OUTPUT PARAMETER

Die komplette API-Response wird durchgeleitet:

```json
{
  "id": "chatcmpl-<uuid>",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "haiku",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Die Antwort von Claude..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 250,
    "total_tokens": 400,
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0
  },
  "claude_metadata": {
    "session_id": "uuid",
    "duration_ms": 2000,
    "total_cost_usd": 0.015
  }
}
```

### Hauptfelder:
- **`choices[0].message.content`** → Claude's Antwort (string)
- **`usage.total_tokens`** → Gesamte Token (number)
- **`claude_metadata.cost_usd`** → Geschätzte Kosten (number)

---

## 🔧 VERWENDUNGSBEISPIELE

### Beispiel 1: Log-Analyse mit Defaults

```javascript
// Input
{
  "prompt": "Analysiere diese Error-Logs und finde Muster:\n\nERROR [2026-01-24 13:45:23] Connection timeout\nERROR [2026-01-24 13:45:45] Connection timeout"
}

// Output (choices[0].message.content)
"Basierend auf den Logs erkenne ich folgende Muster:
1. Zeitraum: 22 Sekunden zwischen den Fehlern
2. Fehlertyp: Connection Timeout
3. Ursache: Mögliche Netzwerküberlastung oder Service-Ausfall
4. Empfehlung: Prüfe Netzwerk-Konnektivität und Service-Status"
```

---

### Beispiel 2: Code Review mit Sonnet

```javascript
// Input
{
  "prompt": "Review diesen Python-Code auf Security Issues:\n\nimport subprocess\nresult = subprocess.run(user_input, shell=True)",
  "model": "sonnet",
  "temperature": 0.0
}

// Output
"🚨 KRITISCHE SICHERHEITSLÜCKE - Command Injection!\n\nProblem:\n- shell=True mit user_input erlaubt Shell-Injection\n\nFix:\nsubprocess.run(user_input.split(), shell=False)"
```

---

### Beispiel 3: Health-Check mit Haiku

```javascript
// Input
{
  "prompt": "Generiere einen Health-Check für Ubuntu 22.04 mit nginx",
  "model": "haiku",
  "temperature": 0.1
}

// Output
"#!/bin/bash\necho 'CPU:'\ntop -bn1 | grep 'Cpu(s)'\necho 'Memory:'\nfree -h\necho 'Nginx:'\nsudo systemctl status nginx"
```

---

## 📊 NODE-STRUKTUR

Der Workflow besteht aus 3 Knoten:

### 1️⃣ Input Node (Trigger)
- **Typ:** executeWorkflowTrigger
- **Funktion:** Akzeptiert Eingabeparameter
- **Output:** `$json` mit {prompt, model, temperature}

### 2️⃣ HTTP Call Node
- **Typ:** httpRequest
- **Methode:** POST
- **URL:** `http://10.1.1.105:3001/v1/chat/completions`
- **Body:**
  ```json
  {
    "model": model || "haiku",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": temperature || 0.1,
    "max_tokens": 2000
  }
  ```

### 3️⃣ Return Output Node
- **Typ:** respondToWebhook
- **Funktion:** Gibt komplette API-Response zurück

---

## 🔗 INTEGRATION IN ANDERE WORKFLOWS

### Im Master-Workflow aufrufen:

```json
{
  "name": "Execute: Primitive: KI-Executer",
  "type": "executeWorkflow",
  "parameters": {
    "workflowId": "yt2okRvNmGItRjCI",
    "source": "database"
  }
}
```

### Input übergeben (Code-Node):

```javascript
return {
  json: {
    prompt: "Analysiere: " + $('Parse Logs').json.logs,
    model: "sonnet",
    temperature: 0.1
  }
};
```

### Output verarbeiten:

```javascript
const response = $('HTTP Wrapper').json;
const answer = response.choices[0].message.content;
const tokens = response.usage.total_tokens;
const cost = response.claude_metadata.total_cost_usd;

return {
  json: {
    result: answer,
    tokens_used: tokens,
    cost_usd: cost
  }
};
```

---

## ⚙️ KONFIGURATION

### API-Endpoint (hardcodiert)
- **URL:** `http://10.1.1.105:3001/v1/chat/completions`
- **Method:** POST
- **Content-Type:** application/json

### Parameter-Defaults
| Parameter | Default | Bereich |
|-----------|---------|---------|
| model | haiku | haiku, sonnet, opus |
| temperature | 0.1 | 0.0 - 1.0 |
| max_tokens | 2000 | (von API bestimmt) |

---

## 📈 EMPFEHLUNGEN

### Model-Wahl:
- **haiku**: Schnelle Tasks (Log-Parsing, Health-Checks) → ~1-2s
- **sonnet**: Balanced (Code-Review, RCA) → ~3-5s
- **opus**: Komplexe Aufgaben (Deep-Analysis) → ~5-10s

### Temperature-Einstellungen:
- **0.0-0.2**: Deterministic (Security Review, Log Analysis)
- **0.3-0.5**: Balanced (Health Checks, Standard Tasks)
- **0.6-1.0**: Creative (Brainstorming, Ideation)

### Token-Budgets (max_tokens: 2000):
- Log Analysis: ~300-500 tokens Input → ~500-800 tokens Output
- Code Review: ~800-1200 tokens Input → ~600-800 tokens Output
- Health Check: ~200-400 tokens Input → ~400-600 tokens Output

---

## 🚨 FEHLERBEHANDLUNG

### API-Fehler:
```json
{
  "error": {
    "message": "Invalid API key",
    "type": "authentication_error",
    "code": 401
  }
}
```

### Behandlung im Master-Workflow:
```javascript
if ($('HTTP Wrapper').json.error) {
  console.error("API Error:", $('HTTP Wrapper').json.error.message);
  // Fallback-Logik
}
```

---

## 📚 Verwandte Module

- **Sub_Claude_Task_Executor.json** - Erweiterte Version mit Session-Tracking
- **MODULE_SPECIFICATION.md** - Detaillierte Architektur-Spec
- **/opt/Projekte/API-DOKUMENTATION.md** - Komplette Claude Code API Dokumentation

---

## 🔄 VERSIONSVERLAUF

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-01-24 | Initial Release |
| | | - Default model: haiku |
| | | - Default temperature: 0.1 |
| | | - max_tokens: 2000 (von API-Doku) |

---

**Erstellt:** 2026-01-24
**Status:** Production Ready
**n8n Workflow ID:** `yt2okRvNmGItRjCI`
