# Tier 3: Functional Modules

Business-Logik — verbinden Plattform-Operationen mit Claude-Analyse.

| Modul | Funktion |
|-------|----------|
| `unified-log-analyser.json` | Logs via SSH sammeln + Claude-Analyse |
| `unified-health-checker.json` | System-Metriken prüfen + Health-Score via Claude |
| `unified-system-updater.json` | Updates prüfen + Claude-Risikobewertung + apt upgrade |
| `issue-aggregator.json` | Issues aus mehreren Systemen aggregieren und priorisieren |

## Abhängigkeiten

- Tier 1: `ssh-command-executor.json`
- SUB-Workflows: `SUB: Claude AI Executor`, `SUB: SSH Command Executor`
