#!/usr/bin/env python3
"""
Modularer Intelligent-Core Service Orchestrator
Koordiniert Analysis, ML, Performance und Intelligence Module
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# Add paths for imports
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/services/intelligent-core-service/src')

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import structlog

# Shared imports
from backend_base_module import BackendModuleRegistry
from event_bus import EventBusConnector, EventType
from logging_config import setup_logging
from security import StockAnalysisRequest, get_client_ip, create_security_headers

# Module imports
from modules.analysis_module import AnalysisModule
from modules.ml_module import MLModule
from modules.performance_module import PerformanceModule
from modules.intelligence_module import IntelligenceModule

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Logging setup
logger = setup_logging("intelligent-core-modular")

# Pydantic Models
class AnalysisResponse(BaseModel):
    symbol: str
    score: float
    recommendation: str
    confidence: float
    indicators: Dict[str, float]
    timestamp: str

class ModuleStatusResponse(BaseModel):
    service: str
    status: str
    modules: Dict[str, Any]
    timestamp: str


class IntelligentCoreOrchestrator:
    """Orchestrator für alle Intelligent-Core Module"""
    
    def __init__(self):
        self.event_bus = EventBusConnector("intelligent-core-modular")
        self.module_registry = BackendModuleRegistry("intelligent-core-modular", self.event_bus)
        
        # Initialize modules
        self.analysis_module = AnalysisModule(self.event_bus)
        self.ml_module = MLModule(self.event_bus)
        self.performance_module = PerformanceModule(self.event_bus)
        self.intelligence_module = IntelligenceModule(self.event_bus)
        
        # Service state
        self.is_initialized = False
        self.startup_time = None
        
    async def initialize(self) -> bool:
        """Initialize orchestrator and all modules"""
        try:
            logger.info("Initializing Intelligent-Core Orchestrator")
            
            # Connect to event bus
            event_bus_connected = await self.event_bus.connect()
            if not event_bus_connected:
                logger.error("Failed to connect to event bus")
                return False
            
            # Register all modules
            self.module_registry.register_module(self.analysis_module)
            self.module_registry.register_module(self.ml_module)
            self.module_registry.register_module(self.performance_module)
            self.module_registry.register_module(self.intelligence_module)
            
            # Initialize all modules
            initialization_results = await self.module_registry.initialize_all_modules()
            
            # Check if all modules initialized successfully
            failed_modules = [name for name, success in initialization_results.items() if not success]
            if failed_modules:
                logger.error("Some modules failed to initialize", failed_modules=failed_modules)
                # Continue with partial initialization
            
            self.is_initialized = True
            self.startup_time = datetime.now()
            
            logger.info("Intelligent-Core Orchestrator initialized successfully",
                       modules_initialized=len(initialization_results),
                       failed_modules=len(failed_modules))
            
            return True
            
        except Exception as e:
            logger.error("Failed to initialize orchestrator", error=str(e))
            return False
    
    async def shutdown(self):
        """Shutdown orchestrator and all modules"""
        try:
            logger.info("Shutting down Intelligent-Core Orchestrator")
            
            await self.module_registry.shutdown_all_modules()
            await self.event_bus.disconnect()
            
            self.is_initialized = False
            logger.info("Orchestrator shutdown complete")
            
        except Exception as e:
            logger.error("Error during orchestrator shutdown", error=str(e))
    
    async def analyze_stock(self, request: StockAnalysisRequest, client_ip: str) -> AnalysisResponse:
        """Coordinate stock analysis across all modules"""
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            logger.info("Starting coordinated stock analysis", symbol=request.symbol)
            
            # Step 1: Technical Analysis
            analysis_result = await self.analysis_module.process_business_logic({
                'request': request,
                'client_ip': client_ip
            })
            
            if not analysis_result.get('success', False):
                raise HTTPException(status_code=500, detail=analysis_result.get('error', 'Analysis failed'))
            
            indicators = analysis_result['data']['indicators']
            
            # Step 2: ML Prediction
            ml_result = await self.ml_module.process_business_logic({
                'type': 'prediction',
                'indicators': indicators,
                'symbol': request.symbol
            })
            
            ml_scores = ml_result.get('ml_scores', {}) if ml_result.get('success') else {}
            ml_confidence = ml_result.get('confidence', 0.5) if ml_result.get('success') else 0.5
            
            # Step 3: Performance Analysis (if historical data available)
            performance_result = await self.performance_module.process_business_logic({
                'type': 'confidence_calculation',
                'indicators': indicators,
                'ml_scores': ml_scores,
                'symbol': request.symbol
            })
            
            confidence = performance_result.get('confidence', ml_confidence) if performance_result.get('success') else ml_confidence
            
            # Step 4: Intelligence Recommendation
            intelligence_result = await self.intelligence_module.process_business_logic({
                'type': 'recommendation',
                'symbol': request.symbol,
                'ml_scores': ml_scores,
                'indicators': indicators,
                'confidence': confidence
            })
            
            if not intelligence_result.get('success', False):
                raise HTTPException(status_code=500, detail="Intelligence processing failed")
            
            recommendation = intelligence_result['recommendation']
            final_confidence = intelligence_result['confidence']
            
            # Create comprehensive response
            response = AnalysisResponse(
                symbol=request.symbol,
                score=ml_scores.get('composite_score', 0.5),
                recommendation=recommendation,
                confidence=final_confidence,
                indicators=indicators,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info("Coordinated stock analysis completed",
                       symbol=request.symbol,
                       recommendation=recommendation,
                       confidence=final_confidence)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error in coordinated stock analysis", 
                        symbol=request.symbol, 
                        error=str(e))
            raise HTTPException(status_code=500, detail="Internal analysis error")
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get comprehensive health status of orchestrator and all modules"""
        try:
            # Get module status
            module_status = self.module_registry.get_all_module_status()
            
            # Calculate service health
            healthy_modules = sum(1 for module in module_status['modules'].values() 
                                if module.get('is_initialized', False))
            total_modules = len(module_status['modules'])
            
            service_healthy = (
                self.is_initialized and 
                self.event_bus.connected and 
                healthy_modules >= total_modules * 0.75  # At least 75% modules healthy
            )
            
            return {
                'service': 'intelligent-core-modular',
                'status': 'healthy' if service_healthy else 'unhealthy',
                'version': '1.0.0-modular',
                'startup_time': self.startup_time.isoformat() if self.startup_time else None,
                'uptime_seconds': (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0,
                'event_bus': {
                    'connected': self.event_bus.connected,
                    'service_name': self.event_bus.service_name
                },
                'modules': {
                    'total': total_modules,
                    'healthy': healthy_modules,
                    'details': module_status['modules']
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Error getting service health", error=str(e))
            return {
                'service': 'intelligent-core-modular',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific module"""
        try:
            module = self.module_registry.get_module(module_name)
            if not module:
                return {
                    'success': False,
                    'error': f'Module {module_name} not found'
                }
            
            return {
                'success': True,
                'module_info': module.get_module_status(),
                'cache_info': {
                    'cache_size': len(getattr(module, 'module_data_cache', {})),
                    'last_update': getattr(module, 'last_cache_update', None)
                }
            }
            
        except Exception as e:
            logger.error("Error getting module info", module=module_name, error=str(e))
            return {
                'success': False,
                'error': str(e)
            }


# Global orchestrator instance
orchestrator = IntelligentCoreOrchestrator()

# FastAPI Application
app = FastAPI(
    title="Intelligent Core Service - Modular",
    description="Modularer Analysis, ML, Performance und Intelligence Service",
    version="1.0.0-modular"
)

# CORS Configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://10.1.1.174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Add security headers
    for header, value in create_security_headers().items():
        response.headers[header] = value
    
    return response

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    logger.info("Starting Intelligent-Core Modular Service...")
    success = await orchestrator.initialize()
    if not success:
        logger.error("Failed to initialize service")
        raise RuntimeError("Service initialization failed")
    logger.info("Intelligent-Core Modular Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Intelligent-Core Modular Service...")
    await orchestrator.shutdown()
    logger.info("Service stopped")

# API Endpoints
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock_endpoint(request: StockAnalysisRequest, http_request: Request):
    """Analyze stock with modular architecture"""
    client_ip = get_client_ip(http_request)
    return await orchestrator.analyze_stock(request, client_ip)

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    return await orchestrator.get_service_health()

@app.get("/modules")
async def list_modules():
    """List all available modules"""
    module_status = orchestrator.module_registry.get_all_module_status()
    return {
        'service': 'intelligent-core-modular',
        'modules': list(module_status['modules'].keys()),
        'module_details': module_status['modules']
    }

@app.get("/modules/{module_name}")
async def get_module_info_endpoint(module_name: str):
    """Get detailed information about a specific module"""
    return await orchestrator.get_module_info(module_name)

@app.get("/metrics")
async def get_service_metrics():
    """Get service metrics and performance data"""
    health = await orchestrator.get_service_health()
    return {
        'service_metrics': {
            'uptime_seconds': health.get('uptime_seconds', 0),
            'modules_healthy': health.get('modules', {}).get('healthy', 0),
            'modules_total': health.get('modules', {}).get('total', 0),
            'event_bus_connected': health.get('event_bus', {}).get('connected', False)
        },
        'module_metrics': {
            name: {
                'initialized': details.get('is_initialized', False),
                'cache_size': details.get('cache_size', 0),
                'subscribed_events': details.get('subscribed_events_count', 0)
            }
            for name, details in health.get('modules', {}).get('details', {}).items()
        },
        'timestamp': datetime.now().isoformat()
    }

# Module-specific endpoints
@app.post("/analysis/technical")
async def technical_analysis_endpoint(request: StockAnalysisRequest):
    """Direct technical analysis endpoint"""
    try:
        result = await orchestrator.analysis_module.process_business_logic({
            'request': request,
            'client_ip': '127.0.0.1'  # Internal call
        })
        return result
    except Exception as e:
        logger.error("Error in technical analysis", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ml/predict")
async def ml_prediction_endpoint(indicators: Dict[str, float], symbol: str = "UNKNOWN"):
    """Direct ML prediction endpoint"""
    try:
        result = await orchestrator.ml_module.process_business_logic({
            'type': 'prediction',
            'indicators': indicators,
            'symbol': symbol
        })
        return result
    except Exception as e:
        logger.error("Error in ML prediction", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/intelligence/recommend")
async def intelligence_recommendation_endpoint(
    symbol: str,
    ml_scores: Dict[str, float],
    indicators: Dict[str, float],
    confidence: float
):
    """Direct intelligence recommendation endpoint"""
    try:
        result = await orchestrator.intelligence_module.process_business_logic({
            'type': 'recommendation',
            'symbol': symbol,
            'ml_scores': ml_scores,
            'indicators': indicators,
            'confidence': confidence
        })
        return result
    except Exception as e:
        logger.error("Error in intelligence recommendation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "intelligent_core_orchestrator:app",
        host="0.0.0.0",
        port=int(os.getenv("INTELLIGENT_CORE_MODULAR_PORT", "8011")),
        log_config=None,  # Use our custom logging
        access_log=False   # Disable default access logging
    )