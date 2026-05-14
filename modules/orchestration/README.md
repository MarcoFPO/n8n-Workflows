# Tier 4: Orchestration Modules

Koordinations-Logik — orchestrieren Tier-3-Module für komplexe Workflows.

| Modul | Funktion |
|-------|----------|
| `master-orchestrator.json` | Routing von Tasks zu passenden Functional-Modulen |
| `master-incident-handler.json` | Incident-Bearbeitung: RCA → Analyse → Empfehlung |

## Abhängigkeiten

- Tier 3: Alle Functional-Module
- SUB-Workflows: `SUB: Claude AI Executor`, `SUB: Znuny Note Adder`, `SUB: Notification Dispatcher`

## Hinweis

Die MASTER-Workflows in `/master/` implementieren Tier 4 als vollständige n8n-Produktiv-Workflows.
Diese Module hier sind wiederverwendbare Bausteine für neue Master-Workflows.
