# Phase 2: Code-Bereinigung Plan
**Datum**: 26. August 2025
**Status**: In Bearbeitung

## Konsolidierungs-Mapping für shared/ Module

### Zu konsolidierende Dateien:
1. `shared/database_connection_manager_v1_0_0_20250825.py` → `shared/database_connection_manager.py`
2. `shared/http_client_pool_v1.0.0_20250824.py` → `shared/http_client_pool.py`
3. `shared/performance_config_v1.0.0_20250824.py` → `shared/performance_config.py`
4. `shared/standard_import_manager_v1.0.0_20250824.py` → `shared/import_manager.py`
5. `shared/base_health_checker_v1.0.0_20250824.py` → `shared/health_checker.py`
6. `shared/performance_monitor_v1.0.0_20250824.py` → `shared/performance_monitor.py`
7. `shared/rate_limiter_service_v1.0.0_20250824.py` → `shared/rate_limiter.py`

### Framework-Dateien (behalten mit cleanen Namen):
- `shared/error_handling_framework_v1_0_0_20250825.py` → `shared/error_handling.py`
- `shared/service_validation_framework_v1_0_0_20250825.py` → `shared/validation.py`
- `shared/api_standards_framework_v1_0_0_20250825.py` → `shared/api_standards.py`
- `shared/service_api_patterns_v1_0_0_20250825.py` → `shared/api_patterns.py`

### Event-Schema (wichtig, behalten):
- `shared/prediction_events_schema_v1_0_0.py` → BEHALTEN (aktiv genutzt)
- `shared/ml_prediction_event_types_v1.0.0_20250823.py` → Prüfen ob redundant

### Utility/Tools (evaluieren):
- `shared/openapi_documentation_generator_v1_0_0.py` → `shared/api_docs_generator.py`
- `shared/simple_api_docs_generator_v1_0_0_20250825.py` → Merge mit obigem
- `shared/business_logic_test_framework_v1_0_0.py` → `tests/test_framework.py`
- `shared/service_error_template_v1_0_0_20250825.py` → Merge in error_handling.py

## Services zu bereinigen:
- `services/diagnostic-service/main_v6_0_0.py` → Check aktuelle main.py
- Weitere service Versionen identifizieren und konsolidieren