# Primitive: KI-Executer - Praktische Anwendungsbeispiele

---

## 1️⃣ LOG-ANALYSER WORKFLOW

### Aufbau:
```
Logs einlesen → Prompt vorbereiten → KI-Executer → Ergebnis speichern
```

### Code (Prompt-Preparation Node):

```javascript
const logs = $('Read File').json.content;
const prompt = `Du bist ein IT-Support Spezialist. Analysiere diese Error-Logs:

${logs}

Gib aus:
1. Häufigste Fehler
2. Root Causes
3. Betroffene Services
4. Empfehlung`;

return {
  json: {
    prompt: prompt,
    model: "sonnet",
    temperature: 0.1
  }
};
```

### Output verarbeiten:

```javascript
const result = $('KI-Executer').json;
const analysis = result.choices[0].message.content;

return {
  json: {
    analysis: analysis,
    tokens_used: result.usage.total_tokens,
    timestamp: new Date().toISOString()
  }
};
```

---

## 2️⃣ CODE-REVIEW WORKFLOW

### Aufbau:
```
Code laden → Security Review Prompt → KI-Executer → Bericht generieren
```

### Code (Prompt-Preparation):

```javascript
const code = $('Get Code File').json.content;
const framework = $('Get Framework').json.framework; // "django", "fastapi", etc.

const prompt = `Du bist ein Senior Security Engineer. Führe einen Security-Code-Review durch.

Framework: ${framework}
Umgebung: Production

Code:
\`\`\`
${code}
\`\`\`

Analyse-Punkte:
1. Security Vulnerabilities (OWASP Top 10)
2. Code Quality Issues
3. Performance Problems
4. Compliance Issues
5. Fixes & Recommendations

Format: Strukturiert mit Severity-Level (CRITICAL, HIGH, MEDIUM, LOW)`;

return {
  json: {
    prompt: prompt,
    model: "opus",      // Beste Qualität für Security
    temperature: 0.0    // Deterministisch
  }
};
```

---

## 3️⃣ HEALTH-CHECK GENERATOR

### Aufbau:
```
VM-Daten laden → Health-Check Prompt → KI-Executer → Shell-Script exportieren
```

### Code (Prompt-Preparation):

```javascript
const vm = $('Get VM Config').json;

const prompt = `Du bist ein DevOps-Experte. Generiere einen umfassenden Health-Check für diese VM.

OS: ${vm.os}
Services: ${vm.services.join(', ')}
Monitoring-Tool: ${vm.monitoring}

Health-Check soll prüfen:
1. CPU Load & Memory Usage
2. Disk Space
3. Service Status (${vm.services.join(', ')})
4. Network Connectivity
5. SSL Certificates
6. Log Errors (last 100 lines)

Format: SHELL SCRIPT (ausführbar mit bash)
Präfix: #!/bin/bash
Keine Erklärungen, nur Code!`;

return {
  json: {
    prompt: prompt,
    model: "haiku",      // Schnell & einfach
    temperature: 0.1
  }
};
```

### Output (Shell-Script extrahieren):

```javascript
const result = $('KI-Executer').json;
let script = result.choices[0].message.content;

// Cleanup: Entferne Markdown-Backticks wenn vorhanden
script = script.replace(/```bash\n?/g, '').replace(/```\n?/g, '');

return {
  json: {
    health_check_script: script,
    vm_id: $('Get VM Config').json.id,
    generated_at: new Date().toISOString()
  }
};
```

---

## 4️⃣ RCA (ROOT CAUSE ANALYSIS) WORKFLOW

### Aufbau:
```
Incident-Daten → RCA Prompt → KI-Executer → Executive Summary
```

### Code (Prompt-Preparation):

```javascript
const incident = $('Get Incident').json;

const prompt = `Du bist ein erfahrener Incident Commander. Führe eine Root Cause Analysis durch.

INCIDENT DETAILS:
═══════════════════════════════════════════════════════════
Service: ${incident.service}
Severity: ${incident.severity}
Status: ${incident.status}
Duration: ${incident.duration_minutes} minutes
Impact: ${incident.impact_description}

ERROR MESSAGE:
${incident.error_message}

TIMELINE:
${incident.timeline.map((e, i) => `${i + 1}. ${e.time} - ${e.event}`).join('\n')}

ATTEMPTED FIXES:
${incident.attempted_fixes.join('\n')}

═══════════════════════════════════════════════════════════

RCA OUTPUT erforderlich:
1. 🎯 ROOT CAUSE (Hauptursache)
2. 📌 CONTRIBUTING FACTORS (Beitragende Faktoren)
3. 🔧 IMMEDIATE ACTIONS (Sofort-Maßnahmen)
4. 🛡️ PREVENTION (Langfristige Prävention)
5. 📊 ESTIMATED TTR (Time To Recovery)

Format: Executive Summary + Technical Details`;

return {
  json: {
    prompt: prompt,
    model: "opus",       // Komplexe Analyse
    temperature: 0.2
  }
};
```

---

## 5️⃣ PARALLEL BATCH PROCESSING

### Aufbau (Mehrere Prompts parallel):
```
┌─→ Prompt 1 → KI-Executer → Result 1 ─┐
├─→ Prompt 2 → KI-Executer → Result 2 ─┤ Merge Results
└─→ Prompt 3 → KI-Executer → Result 3 ─┘
```

### Orchestration-Code:

```javascript
// Vorbereitung: 3 verschiedene Prompts
const tasks = [
  {
    name: "log_analysis",
    prompt: "Analysiere diese Logs: " + logs1,
    model: "sonnet",
    temperature: 0.1
  },
  {
    name: "code_review",
    prompt: "Review dieser Code: " + code1,
    model: "opus",
    temperature: 0.0
  },
  {
    name: "suggestions",
    prompt: "Schlage Verbesserungen vor für: " + system1,
    model: "haiku",
    temperature: 0.3
  }
];

// Wird dann von 3 parallelen KI-Executer Nodes aufgerufen
return {
  json: {
    tasks: tasks
  }
};
```

### Merge Results:

```javascript
const results = $('KI-Executer 1').json;
const results2 = $('KI-Executer 2').json;
const results3 = $('KI-Executer 3').json;

return {
  json: {
    analysis: {
      logs: results.choices[0].message.content,
      code_review: results2.choices[0].message.content,
      suggestions: results3.choices[0].message.content
    },
    total_tokens:
      results.usage.total_tokens +
      results2.usage.total_tokens +
      results3.usage.total_tokens
  }
};
```

---

## 6️⃣ CONDITIONAL LOGIC (IF-ELSE mit Temperature)

### Aufbau:
```
Prüfe Fehlertyp → Wähle Model + Temperature → KI-Executer → Spezifische Antwort
```

### Code:

```javascript
const error = $('Get Error').json;

let model = "haiku";
let temperature = 0.1;
let prompt = "";

if (error.type === "security") {
  // Security-Issue: Maximum Quality
  model = "opus";
  temperature = 0.0;
  prompt = `SECURITY ISSUE ANALYSIS:\n\n${error.details}`;

} else if (error.type === "performance") {
  // Performance: Balanced
  model = "sonnet";
  temperature = 0.2;
  prompt = `PERFORMANCE OPTIMIZATION:\n\n${error.details}`;

} else if (error.type === "architecture") {
  // Architektur: Kreativ, aber strukturiert
  model = "sonnet";
  temperature = 0.4;
  prompt = `ARCHITECTURE IMPROVEMENT:\n\n${error.details}`;
}

return {
  json: {
    prompt: prompt,
    model: model,
    temperature: temperature
  }
};
```

---

## 🎯 BEST PRACTICES

### 1. Prompt-Engineering
```javascript
// ❌ SCHLECHT: Vage Anfrage
prompt = "Was ist falsch?"

// ✅ GUT: Klare, strukturierte Anfrage
prompt = `Analysiere folgendes:
- System: ${system}
- Fehler: ${error}
- Kontext: ${context}

Gib aus:
1. Ursache
2. Lösung
3. Prävention`
```

### 2. Error Handling
```javascript
const response = $('KI-Executer').json;

if (response.error) {
  console.error("API Error:", response.error.message);
  // Fallback-Logik
  return { json: { result: "Default response" } };
}

const answer = response.choices[0]?.message?.content;
if (!answer) {
  console.error("No content in response");
  return { json: { result: "Empty response" } };
}
```

### 3. Token-Budgeting
```javascript
const input_tokens = response.usage.prompt_tokens;
const output_tokens = response.usage.completion_tokens;
const total = response.usage.total_tokens;

// Warnung bei hohem Token-Verbrauch
if (total > 1500) {
  console.warn(`⚠️ High token usage: ${total}`);
}

// Cost tracking
const cost_usd = response.claude_metadata.total_cost_usd;
```

### 4. Session Tracking
```javascript
const session_id = response.claude_metadata.session_id;
const duration_ms = response.claude_metadata.duration_ms;

// Für Audit-Trail speichern
db.log({
  session_id: session_id,
  prompt_length: prompt.length,
  model: model,
  duration_ms: duration_ms,
  tokens_used: response.usage.total_tokens,
  cost_usd: response.claude_metadata.total_cost_usd
});
```

---

## 📞 Troubleshooting

### Problem: Timeout (>10 Sekunden)
**Lösung:** Kleinere max_tokens verwenden oder prompt vereinfachen

### Problem: "Connection refused" auf 10.1.1.105:3001
**Lösung:** Claude Code API-Server prüfen: `curl http://10.1.1.105:3001/health`

### Problem: Inkonsistente Antworten
**Lösung:** Temperature auf 0.0-0.1 senken für deterministisches Output

### Problem: Zu kurze Antworten
**Lösung:** Prompt mit "Sei detailliert" / "Gib lange Erklärung" starten

---

**Letzte Aktualisierung:** 2026-01-24
