# 📋 Versioning Requirements - Aktienanalyse-Ökosystem

## 🎯 **VERPFLICHTENDE Versioning-Compliance**

**Alle Entwickler müssen diese Anforderungen bei jeder Modul-Änderung befolgen!**

---

## 📖 **Namenskonvention (VERPFLICHTEND)**

### **Format für alle Module:**
```
{modul_name}_v{major}.{minor}.{patch}_{YYYYMMDD}.py
```

### **Beispiele:**
```bash
✅ KORREKT:
- order_execution_module_v1.3.2_20250815.py
- data_processing_service_v2.0.0_20250815.py
- market_data_fetcher_module_v1.5.0_20250814.py

❌ FALSCH:
- order_execution_module.py
- data_processing_service_v2.py
- market_data_fetcher_module_latest.py
```

---

## 🔢 **Semantic Versioning (VERPFLICHTEND)**

### **Major Version (X.0.0):**
- **Breaking Changes**: API-Inkompatibilitäten
- **Architektur-Änderungen**: Grundlegende Strukturänderungen
- **Dependency-Updates**: Neue Framework-Versionen
- **Database Schema Changes**: Strukturelle DB-Änderungen

### **Minor Version (0.X.0):**
- **Neue Features**: Zusätzliche Funktionalität
- **API-Erweiterungen**: Neue Endpoints/Methoden
- **Performance-Verbesserungen**: Signifikante Optimierungen
- **Neue Dependencies**: Zusätzliche Libraries

### **Patch Version (0.0.X):**
- **Bugfixes**: Fehlerkorrekturen ohne API-Änderungen
- **Performance-Tweaks**: Kleine Optimierungen
- **Code-Cleanup**: Refactoring ohne Funktionsänderungen
- **Documentation-Updates**: Nur Dokumentation

---

## 📋 **WORKFLOW bei Modul-Änderungen (VERPFLICHTEND)**

### **Schritt 1: Version bestimmen**
```bash
# Prüfe Art der Änderung:
# - Breaking Change → Major++
# - Neue Features → Minor++  
# - Bugfixes → Patch++
```

### **Schritt 2: Datei umbenennen**
```bash
# ALT: order_execution_module_v1.3.1_20250810.py
# NEU: order_execution_module_v1.3.2_20250815.py

mv order_execution_module_v1.3.1_20250810.py order_execution_module_v1.3.2_20250815.py
```

### **Schritt 3: Release Register aktualisieren**
```bash
# MODUL_RELEASE_REGISTER.md aktualisieren:
vim MODUL_RELEASE_REGISTER.md

# Neue Zeile hinzufügen:
| **order_execution_module** | v1.3.2 | 2025-08-15 | Performance Optimization | ✅ AKTIV |
```

### **Schritt 4: Imports aktualisieren**
```python
# Alle Imports in anderen Dateien aktualisieren:
# ALT: from modules.order_execution_module_v1.3.1_20250810 import execute_order
# NEU: from modules.order_execution_module_v1.3.2_20250815 import execute_order
```

### **Schritt 5: Git Commit**
```bash
git add .
git commit -m "feat: order_execution_module v1.3.2 - Performance Optimization

- Improved execution speed by 15%
- Fixed memory leak in order processing
- Updated error handling

Module: order_execution_module_v1.3.2_20250815.py
Previous: v1.3.1
Changes: Performance + Bugfixes"
```

---

## ⚠️ **AUTOMATISCHE VALIDIERUNG**

### **Pre-commit Hook (VERPFLICHTEND):**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Prüfe Dateinamen-Convention
for file in $(git diff --cached --name-only | grep '\.py$'); do
    if [[ $file == *"_module.py" ]] || [[ $file == *"_service.py" ]] || [[ $file == *"_orchestrator.py" ]]; then
        if [[ ! $file =~ _v[0-9]+\.[0-9]+\.[0-9]+_[0-9]{8}\.py$ ]]; then
            echo "❌ FEHLER: $file entspricht nicht der Versioning-Convention!"
            echo "Format: {name}_v{major}.{minor}.{patch}_{YYYYMMDD}.py"
            exit 1
        fi
    fi
done

# Prüfe Release Register Update
if ! git diff --cached --name-only | grep -q "MODUL_RELEASE_REGISTER.md"; then
    if git diff --cached --name-only | grep -q "_v[0-9]"; then
        echo "❌ FEHLER: Modul-Änderung ohne Release Register Update!"
        echo "Bitte MODUL_RELEASE_REGISTER.md aktualisieren."
        exit 1
    fi
fi

echo "✅ Versioning-Compliance OK"
```

### **CI Pipeline Checks:**
```yaml
# .github/workflows/versioning-check.yml
name: Versioning Compliance Check

on: [push, pull_request]

jobs:
  versioning-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Check Module Naming Convention
        run: |
          # Prüfe alle Python-Module auf korrekte Namenskonvention
          find . -name "*_module.py" -o -name "*_service.py" -o -name "*_orchestrator.py" | while read file; do
            if [[ ! $file =~ _v[0-9]+\.[0-9]+\.[0-9]+_[0-9]{8}\.py$ ]]; then
              echo "❌ $file: Falsche Namenskonvention"
              exit 1
            fi
          done
          
      - name: Validate Release Register
        run: |
          # Prüfe Release Register Konsistenz
          python scripts/validate_release_register.py
```

---

## 🚫 **VERBOTENE PRAKTIKEN**

### **❌ NIEMALS:**
```bash
# KEINE Versionslose Dateinamen
order_execution_module.py

# KEINE unspezifischen Versionen  
order_execution_module_v2.py
order_execution_module_latest.py

# KEINE inkonsistenten Datumsformate
order_execution_module_v1.2.0_15-08-2025.py
order_execution_module_v1.2.0_Aug15.py

# KEINE Breaking Changes ohne Major-Increment
order_execution_module_v1.2.0 → order_execution_module_v1.2.1 (aber API geändert)
```

### **✅ IMMER:**
```bash
# Korrekte Namenskonvention
order_execution_module_v1.3.2_20250815.py

# Korrekte Versionierung
v1.2.0 → v2.0.0 (Breaking Change)
v1.2.0 → v1.3.0 (Neue Features)
v1.2.0 → v1.2.1 (Bugfixes)

# Release Register Update
Nach jeder Änderung MODUL_RELEASE_REGISTER.md aktualisieren
```

---

## 📝 **TEMPLATE für Release Register Einträge**

```markdown
| **{modul_name}** | v{X.Y.Z} | {YYYY-MM-DD} | {Upgrade_Beschreibung} | ✅ AKTIV |
```

### **Beispiele:**
```markdown
| **order_execution_module** | v1.3.2 | 2025-08-15 | Performance Optimization + Memory Fix | ✅ AKTIV |
| **data_processing_service** | v2.0.0 | 2025-08-15 | Vollständige CSV-Integration | ✅ AKTIV |
| **market_data_fetcher_module** | v1.5.0 | 2025-08-14 | CompaniesMarketCap Integration | ✅ AKTIV |
```

---

## 🔄 **MIGRATION bestehender Module**

### **Phase 1: Service-Level (PRIORITÄT 1)**
```bash
# Hauptservices umbenennen
intelligent_core_orchestrator.py → intelligent_core_orchestrator_v2.1.0_20250815.py
broker_gateway_orchestrator.py → broker_gateway_orchestrator_v2.0.1_20250810.py
data_processing_service.py → data_processing_service_v2.0.0_20250815.py
```

### **Phase 2: Core Modules (PRIORITÄT 2)**
```bash
# Wichtigste Module umbenennen
order_execution_module.py → order_execution_module_v1.3.2_20250810.py
market_data_fetcher_module.py → market_data_fetcher_module_v1.5.0_20250814.py
companies_marketcap_connector.py → companies_marketcap_connector_v1.2.0_20250814.py
```

### **Phase 3: Alle verbleibenden Module (PRIORITÄT 3)**
```bash
# Systematische Umbenennung aller Module
# Pro Tag: 10-15 Module umbenennen
# Timeframe: 1 Woche
```

---

## 📊 **COMPLIANCE TRACKING**

### **Aktueller Status:**
```yaml
✅ Service-Level Module:     5/7 umbenannt (71%)
🔄 Core Modules:            8/15 umbenannt (53%)
❌ Alle Module:             15/87 umbenannt (17%)

Target: 100% bis 2025-08-22
```

### **Tägliche Checks:**
- **09:00**: Automated Compliance Report
- **17:00**: Manual Release Register Review
- **Weekly**: Full Module Audit

---

## 🎯 **ENFORCEMENT**

### **Entwickler-Verantwortung:**
- **Jeder Commit** muss Versioning-compliant sein
- **Pre-commit Hooks** verhindern Non-Compliance
- **Code Reviews** prüfen Versioning-Adherence

### **Team-Lead Verantwortung:**
- **Release Register** wöchentlich reviewen
- **Compliance Metrics** monatlich reportieren
- **Migration Progress** täglich tracken

### **Konsequenzen bei Non-Compliance:**
1. **Warnung**: Erste Verletzung
2. **Commit Rejection**: Zweite Verletzung  
3. **Mandatory Training**: Dritte Verletzung
4. **Code Review Required**: Alle weiteren Commits

---

**DIESE ANFORDERUNGEN SIND VERPFLICHTEND UND GELTEN AB SOFORT!**

**Letzte Aktualisierung**: 2025-08-15 08:30 CET  
**Gültig ab**: 2025-08-15 00:00 CET  
**Review Datum**: 2025-08-22