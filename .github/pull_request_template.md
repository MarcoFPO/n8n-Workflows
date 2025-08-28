# Pull Request Template - Aktienanalyse Ökosystem

## 📋 PR Übersicht
**Issue-Referenz:** Closes #[issue-nummer]
**Branch:** `feature/issue-[nummer]-[kurzbeschreibung]`
**Art der Änderung:** [Feature/Bugfix/Refactoring/Documentation/Other]

## 🎯 Was wurde implementiert?
<!-- Prägnante Beschreibung der Änderungen -->

### Hauptänderungen:
- [ ] 
- [ ] 
- [ ] 

## 🔍 Code Review Checklist

### 📖 Code-Qualität (HÖCHSTE PRIORITÄT)
- [ ] **Clean Code:** Code ist lesbar, verständlich und selbst-dokumentierend
- [ ] **SOLID Principles:** Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion befolgt
- [ ] **DRY:** Keine Code-Duplikation vorhanden
- [ ] **Maintainability:** Code ist modular, wartbar und erweiterbar
- [ ] **Error Handling:** Comprehensive und defensive Fehlerbehandlung implementiert
- [ ] **Performance:** Effiziente Algorithmen und Datenstrukturen verwendet

### 🧪 Testing & Qualitätssicherung
- [ ] **Unit Tests:** Neue Funktionalität ist durch Tests abgedeckt
- [ ] **Integration Tests:** API-Endpunkte und Service-Integration getestet
- [ ] **Test Coverage:** Mindestens 80% Code-Coverage für neue Änderungen
- [ ] **Linting:** Code entspricht Formatierungs-Standards
- [ ] **Type Safety:** TypeScript/Python Type Hints korrekt implementiert

### 🏗️ Architektur & Design
- [ ] **Clean Architecture:** Layered Architecture befolgt
- [ ] **Dependency Injection:** Services sind ordnungsgemäß injiziert
- [ ] **Interface Segregation:** Abstractions sind korrekt definiert
- [ ] **Single Responsibility:** Jede Klasse/Funktion hat eine klare Verantwortung

### 📚 Dokumentation & Wartbarkeit
- [ ] **Code-Kommentare:** Komplexe Logik ist dokumentiert
- [ ] **API-Dokumentation:** Neue Endpoints sind dokumentiert
- [ ] **README Updates:** Relevante Dokumentation wurde aktualisiert
- [ ] **Migration Guide:** Breaking Changes sind dokumentiert

### 🔒 Security & Best Practices (Privater Gebrauch - Nachrangig)
- [ ] **Input Validation:** Eingaben werden validiert (Nice-to-have)
- [ ] **Error Messages:** Keine sensiblen Informationen in Fehlermeldungen
- [ ] **Secrets Management:** Keine Credentials im Code

## 🚀 Deployment & Infrastructure
- [ ] **Native Services:** Keine Container-Dependencies eingeführt
- [ ] **systemd Integration:** Service-Management ordnungsgemäß konfiguriert
- [ ] **Environment Config:** Konfiguration über Umgebungsvariablen
- [ ] **Health Checks:** Monitoring und Logging implementiert

## 🔧 Breaking Changes Assessment
<!-- Falls Breaking Changes vorliegen -->
- [ ] **Backward Compatibility:** Änderungen sind rückwärts-kompatibel
- [ ] **Migration Required:** Migration-Schritte dokumentiert
- [ ] **API Versioning:** API-Versionierung berücksichtigt

## 📊 Performance Impact
- [ ] **Memory Usage:** Keine signifikanten Memory-Leaks
- [ ] **CPU Performance:** Keine Performance-Degradation
- [ ] **Database Queries:** Optimierte Datenbankabfragen
- [ ] **API Response Times:** Acceptable Response-Zeiten

## ✅ Pre-Merge Requirements
- [ ] **CI/CD Pipeline:** Alle Tests sind grün ✅
- [ ] **Code Review:** Mindestens 1 Reviewer hat approved
- [ ] **Conflicts Resolved:** Merge-Konflikte sind gelöst
- [ ] **Branch Updated:** Branch ist aktuell mit main/develop

## 📝 Testing Instructions
<!-- Schritte zum Testen der Änderungen -->

### Lokal testen:
1. `git checkout feature/issue-[nummer]-[beschreibung]`
2. `pip install -r requirements.txt`
3. `python -m pytest tests/`
4. [Spezifische Test-Schritte]

### Integration testen:
1. [API-Endpunkt Tests]
2. [Service-Integration Tests]
3. [End-to-End Scenarios]

## 🎯 Definition of Done
- [ ] Feature/Fix ist vollständig implementiert
- [ ] Tests sind geschrieben und bestehen
- [ ] Code Review ist durchgeführt
- [ ] Dokumentation ist aktualisiert
- [ ] CI/CD Pipeline ist erfolgreich
- [ ] Breaking Changes sind kommuniziert

---

**🤖 Generated with Claude Code - Branch Management System v1.0**

<!-- 
Template basiert auf 4-Augen-Prinzip für MarcoFPO/aktienanalyse--kosystem
Code-Qualität hat HÖCHSTE PRIORITÄT gemäß CLAUDE.md
-->