# API Migration Guide v1.0.0 - Service API Standardization

## Übersicht

Dieses Dokument beschreibt die Migration bestehender Services zu den standardisierten API Patterns des Aktienanalyse-Ökosystems.

**Ziel:** Einheitliche API-Struktur für alle Services mit konsistenten Patterns, Fehlerbehandlung und Dokumentation.

---

## API Standards Framework

### Kernkomponenten

1. **API Standards Framework v1.0.0**
   - Lokation: `/shared/api_standards_framework_v1_0_0_20250825.py`
   - Zweck: Basis-Standards für alle APIs

2. **Service API Patterns v1.0.0**
   - Lokation: `/shared/service_api_patterns_v1_0_0_20250825.py`
   - Zweck: Domain-spezifische API-Patterns

3. **Error Handling Framework v1.0.0**
   - Lokation: `/shared/error_handling_framework_v1_0_0_20250825.py`
   - Zweck: Einheitliche Fehlerbehandlung

---

## Standardisierte API Struktur

### URL Schema
```
Basis-Pattern: /api/{version}/{resource}

Beispiele:
✅ /api/v1/models              (List models)
✅ /api/v1/models/{id}         (Get specific model)  
✅ /api/v1/predictions/generate (Generate prediction)
✅ /health                     (Health check)
✅ /api/v1/status             (Service status)

❌ /models                     (Inkonsistente Base)
❌ /v1/api/models             (Falsche Reihenfolge)
❌ /models-list               (Non-REST Pattern)
```

### HTTP Methoden Standards
```python
# CRUD Operations
GET    /api/v1/models         # List resources
POST   /api/v1/models         # Create resource
GET    /api/v1/models/{id}    # Get single resource
PUT    /api/v1/models/{id}    # Update resource (full)
PATCH  /api/v1/models/{id}    # Update resource (partial)
DELETE /api/v1/models/{id}    # Delete resource

# Spezifische Actions
POST   /api/v1/models/train                # Train models
POST   /api/v1/predictions/generate        # Generate prediction
GET    /api/v1/predictions/{symbol}/history # Get history
```

### Standard Response Format
```json
{
  "data": {
    // Actual response data
  },
  "metadata": {
    "timestamp": "2025-08-25T10:00:00Z",
    "service": "ml-analytics-service", 
    "version": "6.1.1",
    "request_id": "uuid",
    "processing_time_ms": 156.7
  },
  "pagination": {  // Nur bei Listen
    "page": 1,
    "size": 20,
    "total_pages": 5,
    "total_items": 100,
    "has_next": true,
    "has_previous": false
  }
}
```

---

## Migration Schritte

### Phase 1: Framework Integration

#### 1.1 Shared Module Import
```python
# main.py - Add to imports
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

from api_standards_framework_v1_0_0_20250825 import (
    APIStandards,
    APIDocumentationStandards, 
    apply_api_standards_to_app,
    StandardItemResponse,
    StandardListResponse,
    StandardMetadata,
    StandardHealthResponse
)

from service_api_patterns_v1_0_0_20250825 import (
    ServiceAPIPatternFactory,
    # Spezifische Pattern für Service-Typ
)
```

#### 1.2 FastAPI App Konfiguration
```python
# API Standards Configuration  
api_standards = APIStandards(
    version_strategy="url_path",
    current_version="v1",
    base_path="/api",
    default_page_size=20,
    max_page_size=100
)

# Apply standards to app
apply_api_standards_to_app(
    app,
    service_name="your-service-name",
    version="6.1.1",
    description="Service description"
)
```

### Phase 2: Endpoint Migration

#### 2.1 Health & Status Endpoints
```python
# Standard Health Endpoint
@app.get("/health", response_model=StandardHealthResponse, tags=["Health"])
async def health_check():
    return StandardHealthResponse(
        status="healthy",
        version="6.1.1",
        database=await get_db_health(),
        dependencies=await get_dependencies_health()
    )

# Standard Status Endpoint  
@app.get("/api/v1/status", response_model=StandardItemResponse, tags=["Status"])
async def service_status():
    start_time = time.time()
    stats = await get_service_stats()
    
    return StandardItemResponse(
        data=stats,
        metadata=StandardMetadata(
            service="your-service",
            version="6.1.1", 
            processing_time_ms=get_processing_time(start_time)
        )
    )
```

#### 2.2 CRUD Endpoints Migration
```python
# BEFORE: Alte API Structure
@app.get("/models")
async def list_models():
    models = await get_models()
    return {"models": models}

# AFTER: Standardized API Structure  
@app.get("/api/v1/models", response_model=StandardListResponse, tags=["Models"])
async def list_models(pagination: PaginationRequest = Depends()):
    start_time = time.time()
    result = await get_models_paginated(pagination.page, pagination.size)
    
    return StandardListResponse(
        data=result.get("items", []),
        metadata=StandardMetadata(
            service="your-service",
            version="6.1.1",
            processing_time_ms=get_processing_time(start_time)
        ),
        pagination=result.get("pagination")
    )
```

#### 2.3 Domain-spezifische Endpoints
```python
# ML Analytics Pattern
ml_pattern = ServiceAPIPatternFactory.create_ml_analytics_pattern(
    "ml-analytics-service", api_standards
)

# Data Processing Pattern
data_pattern = ServiceAPIPatternFactory.create_data_processing_pattern(
    "data-processing-service", api_standards  
)

# Tracking Pattern
tracking_pattern = ServiceAPIPatternFactory.create_tracking_pattern(
    "tracking-service", api_standards
)
```

### Phase 3: Response Standardization

#### 3.1 Processing Time Integration
```python
def get_processing_time(start_time: float) -> float:
    """Calculate processing time in milliseconds"""
    return round((time.time() - start_time) * 1000, 2)

# In endpoints:
start_time = time.time()
# ... processing ...
processing_time_ms=get_processing_time(start_time)
```

#### 3.2 Error Handling Integration
```python
# Already handled by Error Framework
# No changes needed if Error Framework is integrated
```

---

## Service-spezifische Migration

### ML Analytics Services
```python
# Use ML Analytics API Pattern
from service_api_patterns_v1_0_0_20250825 import (
    MLTrainingRequest,
    MLPredictionRequest,
    MLBatchPredictionRequest,
    MLEvaluationRequest
)

# Standardized training endpoint
@app.post("/api/v1/models/train", response_model=StandardItemResponse)
async def train_model(request: MLTrainingRequest):
    # Implementation
```

### Data Processing Services  
```python
# Use Data Processing API Pattern
from service_api_patterns_v1_0_0_20250825 import (
    DataProcessingJobRequest,
    DataTransformRequest
)

# Standardized job endpoint
@app.post("/api/v1/jobs/start", response_model=StandardItemResponse)
async def start_job(request: DataProcessingJobRequest):
    # Implementation
```

### Tracking/Monitoring Services
```python
# Use Tracking API Pattern
from service_api_patterns_v1_0_0_20250825 import (
    TrackingEventRequest,
    MetricsQuery
)

# Standardized tracking endpoint
@app.post("/api/v1/events/track", response_model=StandardItemResponse)
async def track_event(request: TrackingEventRequest):
    # Implementation
```

---

## Migration Checkliste

### ✅ Framework Integration
- [ ] Shared modules importiert
- [ ] API Standards konfiguriert
- [ ] FastAPI App mit Standards aktualisiert
- [ ] Error Handling Framework integriert

### ✅ Endpoint Migration
- [ ] Health endpoint standardisiert (`/health`)
- [ ] Status endpoint migriert (`/api/v1/status`) 
- [ ] CRUD endpoints zu `/api/v1/resource` Pattern migriert
- [ ] Processing time tracking implementiert
- [ ] Pagination support hinzugefügt

### ✅ Response Standardization
- [ ] StandardItemResponse für Einzelobjekte
- [ ] StandardListResponse für Listen
- [ ] StandardMetadata in allen Responses
- [ ] Pagination metadata bei Listen
- [ ] Processing time in metadata

### ✅ Documentation
- [ ] OpenAPI tags aktualisiert
- [ ] Endpoint descriptions standardisiert
- [ ] Request/Response models dokumentiert
- [ ] API version in documentation

### ✅ Testing
- [ ] Health endpoint funktional
- [ ] Status endpoint funktional  
- [ ] Standard response format validiert
- [ ] Error handling funktional
- [ ] Pagination funktional

---

## Migrierte Services Status

### ✅ Vollständig migriert (v6.1.1)
- **ML Analytics Service** - Alle Patterns implementiert
- **Prediction Tracking Service** - Basis-Standards integriert

### 🔄 In Migration
- **Diagnostic Service** - Framework integriert
- **Data Processing Service** - Framework integriert  
- **Marketcap Service** - Framework integriert

### ⏳ Ausstehend
- Broker Gateway Service
- Frontend Service
- Weitere Legacy Services

---

## Best Practices

### URL Design
- Verwende Plural-Nomen für Ressourcen (`/models`, nicht `/model`)
- Konsistente Hierarchie (`/api/v1/resource/id/subresource`)
- Keine Verben in URLs (`/api/v1/models/train` ist OK als Action)

### HTTP Status Codes
- `200 OK` - Erfolgreiche GET/PUT Requests
- `201 Created` - Erfolgreiche POST Requests
- `204 No Content` - Erfolgreiche DELETE Requests  
- `400 Bad Request` - Client-Fehler
- `404 Not Found` - Ressource nicht gefunden
- `500 Internal Server Error` - Server-Fehler

### Response Design
- Immer Standard-Format verwenden
- Processing time für Performance-Monitoring
- Pagination bei Listen implementieren
- Konsistente Fehler-Responses

### Versioning
- URL-basiertes Versioning (`/api/v1/`)
- Backwards Compatibility für mindestens eine Version
- Clear deprecation strategy

---

## Troubleshooting

### Häufige Probleme

#### Import Errors
```bash
# Lösung: Prüfe sys.path setup
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
```

#### Pydantic V2 Kompatibilität
```python
# FALSCH (Pydantic V1)
Field(regex="^pattern$")

# RICHTIG (Pydantic V2) 
Field(pattern="^pattern$")
```

#### Response Format Inkonsistenz
```python
# Verwende immer Standard Response Models
return StandardItemResponse(data=result, metadata=metadata)
# Nicht: return {"result": result}
```

---

## Support und Ressourcen

- **Framework Location**: `/shared/`
- **Documentation**: `/docs/`  
- **Examples**: Siehe migrierte Services
- **Error Handling**: Error Framework v1.0.0
- **API Standards**: API Standards Framework v1.0.0

**Migration Support**: Bei Problemen, siehe migrierte Services als Referenz oder Error Framework Documentation.