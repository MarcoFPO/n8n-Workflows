# 🌐 ML Analytics Ökosystem v4.0 - API Documentation
## Complete OpenAPI/Swagger Specification - Production Ready

**Version:** 4.0 Clean Architecture  
**Service:** ML Analytics LXC Service  
**Container:** 10.1.1.174:8021  
**Documentation Date:** 21.08.2025

---

## 📋 API OVERVIEW

Das ML Analytics Ökosystem bietet eine umfassende REST API für **Quantum-inspired Classical Algorithms**, **Advanced AI & Deep Learning** und **Production AutoML** auf LXC Container 10.1.1.174.

### 🔧 **Base Configuration:**
- **Base URL:** `http://10.1.1.174:8021` (Production) / `http://localhost:8021` (Development)
- **Protocol:** HTTP/1.1
- **Content-Type:** `application/json`
- **Authentication:** None (Private LXC Environment)
- **Rate Limiting:** None (Internal Use)

---

## 🚀 QUICK START

### **Health Check:**
```bash
curl http://localhost:8021/api/v1/classical-enhanced/status
```

### **Portfolio Optimization:**
```bash
curl -X POST http://localhost:8021/api/v1/classical-enhanced/vce/portfolio-optimization \
  -H "Content-Type: application/json" \
  -d '{
    "expected_returns": [0.10, 0.12, 0.08],
    "covariance_matrix": [
      [0.01, 0.005, 0.002],
      [0.005, 0.02, 0.003],
      [0.002, 0.003, 0.015]
    ],
    "risk_tolerance": 0.5
  }'
```

---

## 🔬 CLASSICAL-ENHANCED ML ENGINE

### **GET /api/v1/classical-enhanced/status**
Engine Status und Performance Metrics

#### **Request:**
```http
GET /api/v1/classical-enhanced/status HTTP/1.1
Host: localhost:8021
```

#### **Response:**
```json
{
  "engine_status": {
    "status": "operational",
    "container_optimization": "lxc-optimized",
    "num_enhanced_models": 3,
    "num_enhanced_transformers": 1,
    "num_algorithm_templates": 5
  },
  "lxc_performance": {
    "container_ip": "10.1.1.174",
    "system_performance": {
      "avg_memory_percent": 54.47,
      "avg_cpu_percent": 37.93
    },
    "lxc_optimization_status": {
      "monitoring_active": true,
      "memory_optimization": "Active"
    }
  },
  "container_ip": "10.1.1.174",
  "optimization_level": "LXC-Enhanced",
  "_request_time_ms": 0.90
}
```

#### **Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `engine_status.status` | string | Engine operational status |
| `engine_status.num_enhanced_models` | integer | Active enhanced models count |
| `lxc_performance.container_ip` | string | LXC container IP address |
| `lxc_performance.system_performance` | object | System performance metrics |
| `optimization_level` | string | Current optimization level |
| `_request_time_ms` | float | Request processing time |

---

### **POST /api/v1/classical-enhanced/vce/portfolio-optimization**
VCE (Variational Classical Eigensolver) Portfolio Optimization

#### **Request:**
```http
POST /api/v1/classical-enhanced/vce/portfolio-optimization HTTP/1.1
Host: localhost:8021
Content-Type: application/json

{
  "expected_returns": [0.10, 0.12, 0.08],
  "covariance_matrix": [
    [0.01, 0.005, 0.002],
    [0.005, 0.02, 0.003],
    [0.002, 0.003, 0.015]
  ],
  "risk_tolerance": 0.5
}
```

#### **Request Parameters:**
| Parameter | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `expected_returns` | array[float] | ✅ Yes | Expected asset returns | Length: 2-100 |
| `covariance_matrix` | array[array[float]] | ✅ Yes | Asset covariance matrix | Square matrix, same size as expected_returns |
| `risk_tolerance` | float | ✅ Yes | Risk tolerance parameter | Range: 0.0-2.0 |

#### **Response:**
```json
{
  "optimal_energy": -0.15833333333333335,
  "portfolio_weights": [
    0.4166666666666667,
    0.5833333333333334,
    0.0
  ],
  "classical_advantage": 0.7557794199669436,
  "num_iterations": 43,
  "risk_metrics": {
    "portfolio_return": 0.15833333333333335,
    "portfolio_risk": 0.10474837574980446,
    "sharpe_ratio": 1.5115588399338873
  },
  "lxc_performance_metrics": {
    "memory_usage_mb": 57.59615120096561,
    "lxc_optimized": true,
    "computation_time_ms": 0.012159347534179688
  }
}
```

#### **Error Responses:**
```json
// Invalid Matrix Dimension
{
  "error": "Dimension mismatch: expected_returns has 2 assets but covariance_matrix has 3 rows"
}

// Invalid Risk Tolerance
{
  "error": "Invalid risk_tolerance: -1.5. Must be between 0 and 2"
}

// Portfolio Too Large
{
  "error": "Portfolio too large: 150 assets. Maximum 100 assets allowed on LXC container"
}
```

---

### **POST /api/v1/classical-enhanced/qiaoa/optimization**
QIAOA (Quantum-Inspired Approximate Optimization Algorithm) für Kombinatorische Optimierung

#### **Request:**
```http
POST /api/v1/classical-enhanced/qiaoa/optimization HTTP/1.1
Host: localhost:8021
Content-Type: application/json

{
  "cost_matrix": [
    [0, 5, 3, 7],
    [5, 0, 8, 2],
    [3, 8, 0, 4],
    [7, 2, 4, 0]
  ],
  "num_layers": 3
}
```

#### **Request Parameters:**
| Parameter | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `cost_matrix` | array[array[float]] | ✅ Yes | Cost matrix for optimization | Square matrix, max 50x50 |
| `num_layers` | integer | No | QAOA layers (default: 3) | Range: 1-10 |

#### **Response:**
```json
{
  "optimal_solution": [0, 1, 0, 1],
  "optimal_cost": 12.5,
  "convergence_iterations": 28,
  "quantum_advantage": 0.23,
  "lxc_performance_metrics": {
    "memory_usage_mb": 45.2,
    "lxc_optimized": true,
    "computation_time_ms": 15.7
  }
}
```

#### **Error Responses:**
```json
// Invalid Cost Matrix
{
  "error": "cost_matrix must be a non-empty list"
}

// Matrix Too Large
{
  "error": "Cost matrix too large: 60x60. Maximum 50x50 matrix allowed on LXC container"
}

// Invalid Layers
{
  "error": "Invalid num_layers: 15. Must be an integer between 1 and 10"
}
```

---

## 🧠 ADVANCED AI & DEEP LEARNING

### **POST /api/v1/ai/multimodal/transform**
Multi-Modal Transformer Networks für Cross-Modal Feature Fusion

#### **Request:**
```json
{
  "text_input": "Analyze market sentiment for AAPL",
  "numerical_features": [0.15, 0.23, -0.08, 0.45],
  "categorical_features": ["tech", "large_cap", "growth"],
  "fusion_strategy": "attention"
}
```

#### **Response:**
```json
{
  "transformed_features": [0.234, -0.123, 0.567, 0.891],
  "attention_weights": {
    "text_weight": 0.45,
    "numerical_weight": 0.35,
    "categorical_weight": 0.20
  },
  "confidence_score": 0.87,
  "processing_time_ms": 23.4
}
```

---

### **POST /api/v1/ai/rl/trading-decision**
Reinforcement Learning Trading Agent für Marktentscheidungen

#### **Request:**
```json
{
  "market_state": {
    "price": 150.25,
    "volume": 1250000,
    "volatility": 0.23,
    "rsi": 65.4,
    "macd": 0.15
  },
  "portfolio_state": {
    "cash": 10000,
    "positions": {"AAPL": 50}
  },
  "agent_type": "q_learning"
}
```

#### **Response:**
```json
{
  "recommended_action": "buy",
  "action_confidence": 0.78,
  "quantity": 25,
  "expected_reward": 0.034,
  "risk_assessment": "moderate",
  "agent_state_updated": true
}
```

---

### **POST /api/v1/ai/cv/chart-analysis**
Computer Vision Chart Analysis für technische Analyse

#### **Request:**
```json
{
  "chart_image_base64": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "analysis_type": "pattern_recognition",
  "timeframe": "1d",
  "indicators": ["support", "resistance", "trend_lines"]
}
```

#### **Response:**
```json
{
  "detected_patterns": [
    {
      "pattern_type": "ascending_triangle",
      "confidence": 0.82,
      "coordinates": {"x1": 120, "y1": 45, "x2": 200, "y2": 78}
    }
  ],
  "support_resistance": {
    "support_levels": [148.50, 145.20],
    "resistance_levels": [152.80, 155.10]
  },
  "trend_analysis": {
    "direction": "bullish",
    "strength": 0.76
  }
}
```

---

### **POST /api/v1/ai/nlp/sentiment**
Advanced NLP Sentiment Engine für News und Text Analysis

#### **Request:**
```json
{
  "text": "Apple reports strong quarterly earnings with revenue growth",
  "language": "en",
  "analysis_depth": "detailed",
  "include_entities": true
}
```

#### **Response:**
```json
{
  "sentiment": {
    "polarity": 0.75,
    "label": "positive",
    "confidence": 0.89
  },
  "entities": [
    {"text": "Apple", "type": "company", "confidence": 0.95},
    {"text": "quarterly earnings", "type": "financial_event", "confidence": 0.88}
  ],
  "emotions": {
    "optimism": 0.65,
    "confidence": 0.23,
    "neutral": 0.12
  },
  "market_relevance": 0.84
}
```

---

## 🤖 PRODUCTION AUTOML PIPELINE

### **POST /api/v1/automl/train**
Automated ML Model Training mit Hyperparameter Optimization

#### **Request:**
```json
{
  "dataset": {
    "features": [[1.2, 3.4, 5.6], [2.1, 4.3, 6.5], [3.0, 5.2, 7.4]],
    "target": [0, 1, 0],
    "feature_names": ["price_ratio", "volume_ratio", "volatility"]
  },
  "task_type": "classification",
  "algorithms": ["random_forest", "gradient_boosting", "neural_network"],
  "optimization_metric": "f1_score",
  "max_training_time_minutes": 30
}
```

#### **Response:**
```json
{
  "training_id": "automl_20250821_050234",
  "best_model": {
    "algorithm": "gradient_boosting",
    "hyperparameters": {
      "n_estimators": 200,
      "learning_rate": 0.1,
      "max_depth": 6
    },
    "performance": {
      "f1_score": 0.898,
      "accuracy": 0.891,
      "precision": 0.885,
      "recall": 0.912
    }
  },
  "ensemble_performance": {
    "f1_score": 0.915,
    "accuracy": 0.908
  },
  "training_time_seconds": 847.3,
  "model_saved": true
}
```

---

### **POST /api/v1/automl/predict**
Prediction mit trainiertem AutoML Model

#### **Request:**
```json
{
  "model_id": "automl_20250821_050234",
  "features": [[1.5, 3.8, 5.9], [2.3, 4.1, 6.2]],
  "return_probabilities": true
}
```

#### **Response:**
```json
{
  "predictions": [1, 0],
  "probabilities": [
    [0.23, 0.77],
    [0.89, 0.11]
  ],
  "confidence_scores": [0.77, 0.89],
  "model_version": "v1.0.0",
  "prediction_time_ms": 2.3
}
```

---

### **GET /api/v1/automl/models**
Liste verfügbarer AutoML Modelle

#### **Response:**
```json
{
  "models": [
    {
      "model_id": "automl_20250821_050234",
      "algorithm": "gradient_boosting",
      "task_type": "classification",
      "performance": {"f1_score": 0.898},
      "created_at": "2025-08-21T05:02:34Z",
      "status": "ready"
    }
  ],
  "total_models": 1,
  "active_models": 1
}
```

---

## 🔍 SYSTEM HEALTH & MONITORING

### **GET /api/v1/health**
System Health Check

#### **Response:**
```json
{
  "status": "healthy",
  "checks": {
    "api_responsive": true,
    "memory_within_limits": true,
    "cpu_within_limits": true,
    "container_operational": true
  },
  "system_metrics": {
    "memory_usage_percent": 49.6,
    "cpu_usage_percent": 2.0,
    "available_memory_mb": 2064.58,
    "load_average": [1.84, 1.32, 1.21]
  },
  "container_ip": "10.1.1.174",
  "uptime_seconds": 3847.2
}
```

---

### **GET /api/v1/system/metrics**
Detailed System Performance Metrics

#### **Response:**
```json
{
  "container_metrics": {
    "ip": "10.1.1.174",
    "memory_utilization_percent": 15.3,
    "cpu_utilization_percent": 3.6,
    "disk_usage_percent": 42.1
  },
  "service_metrics": {
    "requests_processed": 1247,
    "average_response_time_ms": 3.13,
    "error_rate_percent": 0.0,
    "uptime_hours": 1.07
  },
  "ml_engine_metrics": {
    "models_loaded": 3,
    "algorithms_active": 5,
    "total_optimizations": 89,
    "cache_hit_rate_percent": 78.4
  }
}
```

---

## ⚠️ ERROR HANDLING

### **HTTP Status Codes:**
| Code | Status | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `400` | Bad Request | Invalid request parameters |
| `500` | Internal Server Error | Server processing error |
| `503` | Service Unavailable | Service temporarily unavailable |

### **Error Response Format:**
```json
{
  "error": "Error description message",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "risk_tolerance",
    "constraint": "Must be between 0 and 2"
  },
  "timestamp": "2025-08-21T05:00:00Z"
}
```

### **Common Error Types:**
1. **Input Validation Errors:**
   - Invalid matrix dimensions
   - Out-of-range parameters
   - Missing required fields

2. **Resource Limit Errors:**
   - Portfolio size too large
   - Matrix size exceeds limits
   - Memory constraints

3. **Processing Errors:**
   - Algorithm convergence failures
   - Computation timeouts
   - Model loading errors

---

## 🎯 USAGE EXAMPLES

### **Complete Portfolio Optimization Workflow:**
```bash
# 1. Check service status
curl http://localhost:8021/api/v1/classical-enhanced/status

# 2. Optimize portfolio
curl -X POST http://localhost:8021/api/v1/classical-enhanced/vce/portfolio-optimization \
  -H "Content-Type: application/json" \
  -d '{
    "expected_returns": [0.10, 0.12, 0.08, 0.15],
    "covariance_matrix": [
      [0.01, 0.005, 0.002, 0.001],
      [0.005, 0.02, 0.003, 0.002],
      [0.002, 0.003, 0.015, 0.001],
      [0.001, 0.002, 0.001, 0.025]
    ],
    "risk_tolerance": 0.6
  }'

# 3. Monitor system health
curl http://localhost:8021/api/v1/health
```

### **Python Client Example:**
```python
import requests
import json

# ML Analytics API Client
class MLAnalyticsClient:
    def __init__(self, base_url="http://localhost:8021"):
        self.base_url = base_url
    
    def optimize_portfolio(self, returns, covariance, risk_tolerance):
        response = requests.post(
            f"{self.base_url}/api/v1/classical-enhanced/vce/portfolio-optimization",
            json={
                "expected_returns": returns,
                "covariance_matrix": covariance,
                "risk_tolerance": risk_tolerance
            }
        )
        return response.json()
    
    def get_health_status(self):
        response = requests.get(f"{self.base_url}/api/v1/health")
        return response.json()

# Usage
client = MLAnalyticsClient()
result = client.optimize_portfolio(
    returns=[0.10, 0.12, 0.08],
    covariance=[[0.01, 0.005, 0.002], [0.005, 0.02, 0.003], [0.002, 0.003, 0.015]],
    risk_tolerance=0.5
)
print(f"Optimal weights: {result['portfolio_weights']}")
```

---

## 📈 PERFORMANCE SPECIFICATIONS

### **Response Time SLAs:**
| Endpoint Category | Expected Response Time | Max Response Time |
|-------------------|------------------------|-------------------|
| Health Checks | < 5ms | 50ms |
| Portfolio Optimization (≤20 assets) | < 10ms | 100ms |
| Portfolio Optimization (≤100 assets) | < 50ms | 500ms |
| AI/ML Predictions | < 100ms | 1000ms |
| AutoML Training | Variable | 30 minutes |

### **Throughput Specifications:**
- **Concurrent Requests:** Up to 50 concurrent connections
- **Request Rate:** 1000 requests/minute sustained
- **Memory Usage:** ≤ 1GB RAM (LXC optimized)
- **CPU Usage:** ≤ 200% (2 cores)

---

## 🔒 SECURITY & COMPLIANCE

### **Security Headers:**
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

### **Input Validation:**
- All numeric inputs validated for type and range
- Matrix dimensions verified for consistency
- Array sizes checked against LXC limits
- String inputs sanitized for length and content

### **Private Environment:**
- No authentication required (LXC internal network)
- No HTTPS enforcement (private container)
- No rate limiting (trusted internal use)
- CORS disabled for security

---

## 📝 CHANGELOG

### **Version 4.0 (2025-08-21)**
- ✅ Production-ready deployment on LXC 10.1.1.174
- ✅ 100% Integration test success rate
- ✅ Comprehensive error handling and input validation
- ✅ Advanced AI & Deep Learning endpoints added
- ✅ Production AutoML pipeline integration
- ✅ LXC-optimized performance monitoring
- ✅ Complete OpenAPI specification

### **Version 3.0 (2025-08-20)**
- Enterprise integration features
- WebSocket streaming capabilities
- Multi-tenant architecture support

### **Version 2.0 (2025-08-19)**
- Quantum-inspired classical algorithms
- Real-time market intelligence
- Memory-efficient operations

### **Version 1.0 (2025-08-17)**
- Basic ML analytics functionality
- Core portfolio optimization
- Initial LXC deployment

---

**🎯 API Documentation Complete - Production Ready für LXC Container 10.1.1.174**

*Generated by ML Analytics Team*  
*Documentation Version: v1.0.0_20250821*