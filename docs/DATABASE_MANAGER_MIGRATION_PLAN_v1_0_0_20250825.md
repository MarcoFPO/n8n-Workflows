# Database Manager Migration Plan v1.0.0

**Datum**: 25. August 2025  
**Autor**: Claude Code - Architecture Modernization Specialist  
**Status**: 🚀 IN PROGRESS  
**Phase**: 3.3 - Database Centralization  

## 🎯 MIGRATION ZIEL
Alle 28 Services auf den zentralen PostgreSQL Database Connection Manager migrieren

## 📊 AKTUELLE ANALYSE

### ✅ Services mit Centralized Database Manager (3)
- `broker-gateway-service`: Bereits migriert - nutzt database_connection_manager_v1_0_0
- `event-bus-service`: Bereits migriert - nutzt database_connection_manager_v1_0_0  
- `unified-profit-engine-enhanced`: Bereits migriert - nutzt database_connection_manager_v1_0_0

### 🔄 Clean Architecture Services - SQLite zu PostgreSQL (5)
1. `prediction-tracking-service` - Clean Architecture v6.0.0 mit SQLite
2. `diagnostic-service` - Clean Architecture v6.0.0 mit SQLite
3. `data-processing-service` - Clean Architecture v6.0.0 mit SQLite
4. `ml-analytics-service` - Clean Architecture v6.0.0 mit Multi-SQLite
5. `marketcap-service` - Clean Architecture v6.0.0 mit Memory Repository

### 📦 Monolithic v6.0.0 Services - Refactoring benötigt (4)
6. `intelligent-core-service` - Monolithic v6.0.0
7. `market-data-service` - Monolithic v6.0.0  
8. `ml-pipeline-service` - Monolithic v6.0.0
9. `portfolio-management-service` - Monolithic v6.0.0

### 🏗️ Services für Complete Clean Architecture Migration (16)
10. `frontend-service` - Legacy
11. `monitoring-service` - Legacy
12. `trade-execution-service` - Empty/Placeholder
13. **Event Bus Service** - Hat bereits Clean Architecture Directory Structure
14. **Weitere Services** aus dem gesamten Ökosystem (12+)

## 🚀 MIGRATIONS-REIHENFOLGE - HÖCHSTE PRIORITÄT

### Phase 3.3.1: Clean Architecture Services Database Migration (SOFORT)
**Ziel**: 5 Clean Architecture Services von SQLite zu PostgreSQL migrieren

1. **prediction-tracking-service** ⭐ PRIORITY 1
   - Repository Pattern bereits vorhanden
   - Nur Persistence Layer ändern
   - Estimated: 30 min

2. **diagnostic-service** ⭐ PRIORITY 2  
   - Minimale Business Logic
   - Einfache Migration
   - Estimated: 20 min

3. **data-processing-service** ⭐ PRIORITY 3
   - Multi-Repository Architecture
   - Estimated: 45 min

4. **marketcap-service** ⭐ PRIORITY 4
   - Memory Repository zu PostgreSQL
   - Estimated: 30 min

5. **ml-analytics-service** ⭐ PRIORITY 5
   - Multi-Database zu PostgreSQL
   - Komplexeste Migration
   - Estimated: 60 min

### Phase 3.3.2: Monolithic Services Refactoring (NACH PHASE 3.3.1)
**Ziel**: 4 Monolithic Services zu Clean Architecture + PostgreSQL

6-9. **Monolithic Services** - Complete Refactoring erforderlich

### Phase 3.3.3: Legacy Services Complete Migration (FINAL)
**Ziel**: Alle verbleibenden Legacy Services

10-28. **Legacy Services** - Complete Clean Architecture + PostgreSQL

## 🔧 TECHNISCHE MIGRATIONS-PATTERN

### Database Repository Migration Pattern
```python
# VORHER: SQLite Repository
class SQLitePredictionRepository(IPredictionRepository):
    def __init__(self, database_path: str):
        self.database_path = database_path
    
    async def save(self, prediction: Prediction) -> bool:
        async with aiosqlite.connect(self.database_path) as db:
            # SQLite specific code

# NACHHER: PostgreSQL Repository  
class PostgreSQLPredictionRepository(IPredictionRepository):
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
    
    async def save(self, prediction: Prediction) -> bool:
        async with self.db_manager.get_connection() as connection:
            # PostgreSQL specific code
```

### Container Dependency Injection Update
```python
# VORHER: SQLite Injection
async def configure(self, config: Dict[str, Any]):
    self._prediction_repository = SQLitePredictionRepository(
        database_path=config.get('database_path', './predictions.db')
    )

# NACHHER: PostgreSQL Manager Injection
async def configure(self, config: Dict[str, Any]):
    self._db_manager = DatabaseConnectionManager(
        DatabaseConfiguration()
    )
    await self._db_manager.initialize()
    
    self._prediction_repository = PostgreSQLPredictionRepository(
        db_manager=self._db_manager
    )
```

## 📋 MIGRATION CHECKLISTE - PRO SERVICE

### ✅ Pre-Migration Validation
- [ ] Service hat Repository Pattern implementiert
- [ ] Interface Abstractions sind vorhanden
- [ ] Container.py existiert für Dependency Injection
- [ ] Database Schema kompatibel oder migrierbar

### ✅ Migration Steps
- [ ] PostgreSQL Repository Implementation erstellen
- [ ] Database Schema SQL erstellen/anpassen
- [ ] Container.py aktualisieren für Database Manager
- [ ] Integration Tests erstellen
- [ ] Health Checks anpassen
- [ ] Requirements.txt aktualisieren (asyncpg statt aiosqlite)

### ✅ Post-Migration Validation  
- [ ] Service startet erfolgreich
- [ ] Health Check ist grün
- [ ] Database Connections im Pool verfügbar
- [ ] Basic CRUD Operations funktional
- [ ] Performance acceptable (Baseline etablieren)

## 🎯 SUCCESS METRICS

### Quantitative Metriken
- **Services migriert**: 0/28 → 28/28
- **Database Connections zentralisiert**: 3/28 → 28/28  
- **SQLite Dependencies eliminiert**: 29 Files → 0 Files
- **PostgreSQL Connection Pool Utilization**: < 80%

### Qualitative Metriken  
- **Code-Qualität**: Consistent Repository Pattern
- **Maintainability**: Single Database Configuration
- **Performance**: Connection Pool Efficiency
- **Reliability**: Centralized Connection Health Monitoring

## 🚨 RISK MITIGATION

### Technical Risks
- **Schema Compatibility**: Pre-validate PostgreSQL schema compatibility
- **Connection Pool Exhaustion**: Monitor connection usage during migration
- **Data Loss**: Backup critical SQLite data before migration
- **Performance Regression**: Establish performance baselines

### Migration Risks
- **Service Downtime**: Minimal downtime durch Service Restart
- **Rollback Strategy**: Keep SQLite Repositories as backup branches
- **Dependencies**: Update all asyncpg/aiosqlite dependencies

## 📅 TIMELINE

**Phase 3.3.1**: 2-3 Stunden (5 Clean Architecture Services)
**Phase 3.3.2**: 4-6 Stunden (4 Monolithic Services Refactoring)  
**Phase 3.3.3**: 8-12 Stunden (16+ Legacy Services Complete Migration)

**Total Estimated**: 14-21 Stunden für complete Database Manager Migration

---

**NÄCHSTER SCHRITT**: Phase 3.3.1 - prediction-tracking-service Database Manager Migration