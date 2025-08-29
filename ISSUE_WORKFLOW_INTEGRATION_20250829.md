# 🔄 Issue Workflow Integration - Code Quality Verbesserungen

**Erstellt**: 29. August 2025  
**Repository**: https://github.com/MarcoFPO/aktienanalyse--kosystem  
**Issues**: #61-#66

## 📋 Erstellte GitHub Issues

| Issue # | Titel | Priorität | Aufwand | Status |
|---------|-------|-----------|---------|--------|
| [#61](https://github.com/MarcoFPO/aktienanalyse--kosystem/issues/61) | Code-Duplikation in Service-Initialisierung (30%) | 🔴 HOCH | 8-10h | Open |
| [#62](https://github.com/MarcoFPO/aktienanalyse--kosystem/issues/62) | SOLID-Prinzip Verletzungen | 🔴 HOCH | 15-20h | Open |
| [#63](https://github.com/MarcoFPO/aktienanalyse--kosystem/issues/63) | Performance: Synchrone DB-Zugriffe | 🟡 MITTEL | 10-12h | Open |
| [#64](https://github.com/MarcoFPO/aktienanalyse--kosystem/issues/64) | Clean Architecture Layer-Verletzungen | 🟠 MITTEL-HOCH | 20-25h | Open |
| [#65](https://github.com/MarcoFPO/aktienanalyse--kosystem/issues/65) | Toter Code und Archive-Cleanup | 🟢 NIEDRIG | 2-3h | Open |
| [#66](https://github.com/MarcoFPO/aktienanalyse--kosystem/issues/66) | Generische Exception-Catches | 🟡 MITTEL | 8-10h | Open |

**Gesamt-Aufwand**: 63-80 Stunden

---

## 🎯 Sprint-Planung

### Sprint 1: Foundation (Woche 1-2) - 15-20h
**Ziel**: Basis für weitere Refactorings schaffen

#### Ticket-Reihenfolge:
1. **Issue #65** - Toter Code Cleanup (2-3h)
   - Einfacher Einstieg, schnelle Erfolge
   - Repository sauber für weitere Arbeiten

2. **Issue #61** - Service Base-Klasse (8-10h) 
   - Fundamentale Verbesserung
   - Reduziert sofort 30% Code-Duplikation
   - Basis für alle weiteren Service-Refactorings

3. **Issue #66** - Exception Framework (5-7h)
   - Besseres Debugging für Sprint 2+
   - Stabilere Entwicklungsumgebung

### Sprint 2: Architecture (Woche 3-4) - 25-32h
**Ziel**: Architektur-Qualität verbessern

1. **Issue #62** - SOLID-Prinzipien (15-20h)
   - Nutzt Base-Klasse aus Sprint 1
   - Fundamentale Architektur-Verbesserung

2. **Issue #63** - Performance-Optimierung (10-12h)
   - Async/Await für alle DB-Operationen
   - Connection-Pool-Management

### Sprint 3: Clean Architecture (Woche 5-6) - 20-25h
**Ziel**: Clean Architecture konsequent umsetzen

1. **Issue #64** - Layer-Trennung (20-25h)
   - Nutzt Erkenntnisse aus Sprint 1+2
   - Finale Architektur-Migration

---

## 🔄 Workflow-Integration

### Development Workflow

#### 1. Issue Assignment
```bash
# Issue zuweisen
gh issue edit <issue_number> --add-assignee @MarcoFPO

# Branch erstellen
git checkout -b issue-<issue_number>-<kurze-beschreibung>
# Beispiel: git checkout -b issue-61-service-base-class
```

#### 2. Development Process
```bash
# Feature Branch entwickeln
git add .
git commit -m "feat: implement BaseServiceOrchestrator class

- Create shared/base_service.py
- Migrate event-bus-service to use base class
- Reduce code duplication by 30%

Fixes #61"

git push -u origin issue-61-service-base-class
```

#### 3. Pull Request Creation
```bash
# PR mit Issue-Referenz erstellen
gh pr create --title "Implement BaseServiceOrchestrator to reduce code duplication" \
             --body "Fixes #61

## Changes
- [x] Create BaseServiceOrchestrator class
- [x] Migrate event-bus-service
- [x] Update tests
- [x] Documentation

## Impact
- Reduces code duplication from 30% to <5%
- Easier maintenance of all services
- Consistent service structure"
```

#### 4. Code Review & Merge
```bash
# Nach Approval mergen
gh pr merge --squash --delete-branch
```

---

## 📊 Progress Tracking

### Issue Labels für Filtering
- `code-quality` - Code-Qualitäts-Verbesserungen
- `refactoring` - Strukturelle Änderungen
- `performance` - Performance-Optimierungen
- `architecture` - Architektur-Änderungen
- `technical-debt` - Technische Schulden

### Milestone-Struktur
```bash
# Milestones erstellen
gh api repos/MarcoFPO/aktienanalyse--kosystem/milestones \
  --method POST \
  --field title="Code Quality Sprint 1" \
  --field description="Foundation improvements" \
  --field due_on="2025-09-12T23:59:59Z"

gh api repos/MarcoFPO/aktienanalyse--kosystem/milestones \
  --method POST \
  --field title="Code Quality Sprint 2" \
  --field description="Architecture improvements" \
  --field due_on="2025-09-26T23:59:59Z"

gh api repos/MarcoFPO/aktienanalyse--kosystem/milestones \
  --method POST \
  --field title="Code Quality Sprint 3" \
  --field description="Clean Architecture migration" \
  --field due_on="2025-10-10T23:59:59Z"
```

---

## 🎯 Success Metrics

### Sprint 1 Erfolg
- [ ] Code-Duplikation < 10% (aktuell 30%)
- [ ] Repository-Größe -20% (Archive entfernt)
- [ ] Alle Services nutzen BaseServiceOrchestrator
- [ ] Exception-Framework implementiert

### Sprint 2 Erfolg  
- [ ] Keine direkten Infrastructure-Abhängigkeiten in Domain
- [ ] Response Time <100ms für Standard-Queries
- [ ] Connection-Pool-Management aktiv
- [ ] SRP/DIP-Verletzungen < 5 (aktuell 15+)

### Sprint 3 Erfolg
- [ ] Clean Architecture Score >8/10 (aktuell 3/10)
- [ ] Alle Services folgen Layer-Struktur
- [ ] Dependency Injection implementiert
- [ ] Code-Qualitäts-Score >7/10 (aktuell 3.5/10)

---

## 🔧 Entwickler-Commands

### Issue-Management
```bash
# Alle offenen Code-Quality Issues anzeigen
gh issue list --label "code-quality" --state open

# Issue Status updaten
gh issue edit <issue_number> --add-label "in-progress"

# Issue schließen mit Commit-Referenz
gh issue close <issue_number> --comment "Fixed in commit abc1234"
```

### Branch-Management
```bash
# Alle Feature-Branches anzeigen
git branch --list "issue-*"

# Branch mit Issue verknüpfen
git checkout -b issue-61-service-base-class
git push -u origin issue-61-service-base-class
```

### PR-Templates
Erstelle `.github/pull_request_template.md`:
```markdown
## Issue Reference
Fixes #

## Changes
- [ ] Implementation completed
- [ ] Tests added/updated  
- [ ] Documentation updated
- [ ] Code quality checks passed

## Impact
- Code duplication: Before X% → After Y%
- Performance: Before Xms → After Yms
- Architecture: [Beschreibung der Verbesserung]

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
```

---

## 📈 Monitoring & Reporting

### Wöchentliche Reports
```bash
# Issues-Status für Sprint
gh issue list --milestone "Code Quality Sprint 1" --json number,title,state,assignees

# PR-Activity  
gh pr list --state all --created ">=2025-08-29"

# Code-Änderungen
git diff --stat origin/main..HEAD
```

### Automatisierte Checks
Erstelle `.github/workflows/code-quality.yml`:
```yaml
name: Code Quality Checks
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check code duplication
        run: |
          # Duplikation-Check mit Tool
          echo "Code duplication check"
      - name: SOLID principles check  
        run: |
          # Architecture-Validation
          echo "SOLID principles validation"
```

---

*Workflow Integration für Code Quality Improvement Initiative*  
*Nächste Review: 5. September 2025*