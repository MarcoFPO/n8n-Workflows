#!/usr/bin/env python3
"""
EVENT-BUS-FIRST Intelligent-Core Service Orchestrator
Clean Architecture: ALLE Kommunikation nur über Event-Bus
Ersetzt direkte Module-Importe mit Event-basierter Koordination
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Add paths for imports
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import structlog

# Shared imports - NUR Event-Bus, KEINE direkten Module-Importe
from event_bus import EventBusConnector, EventType
from logging_config import setup_logging
from security import StockAnalysisRequest, get_client_ip, create_security_headers

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Logging setup
logger = setup_logging("intelligent-core-orchestrator-eventbus-first")

# Pydantic Models
class AnalysisResponse(BaseModel):
    symbol: str
    score: float
    recommendation: str
    confidence: float
    indicators: Dict[str, float]
    timestamp: str

class EventBusFirstOrchestrator:
    """
    EVENT-BUS-FIRST Orchestrator
    Clean Architecture Compliance: KEINE direkten Module-Importe
    """
    
    def __init__(self, port: int = 8011):
        self.port = port
        self.is_initialized = False
        self.startup_time = None
        
        # Event-Bus ist die EINZIGE Kommunikationsschnittstelle
        self.event_bus = None
        
        # Response tracking für async Event-koordination
        self.pending_responses = {}
        self.response_timeout = 30  # 30 Sekunden Timeout
        
        # FastAPI Setup
        self.app = FastAPI(
            title="Intelligent-Core Orchestrator (Event-Bus-First)",
            description="Clean Architecture: Nur Event-Bus Kommunikation",
            version="1.0.0"
        )
        
        # CORS Setup
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.on_event("startup")
        async def startup_event():
            await self.initialize()
        
        @self.app.on_event("shutdown") 
        async def shutdown_event():
            await self.shutdown()
            
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy" if self.is_initialized else "initializing",
                "service": "intelligent-core-orchestrator-eventbus-first",
                "initialized": self.is_initialized,
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "event_bus_connected": self.event_bus.is_connected() if self.event_bus else False
            }
            
        @self.app.post("/analyze")
        async def analyze_stock(request: StockAnalysisRequest, http_request: Request):
            client_ip = get_client_ip(http_request)
            result = await self.analyze_stock_eventbus_first(request, client_ip)
            return result
        
        @self.app.get("/marketcap/top/{country}")
        async def get_top_companies_by_marketcap(country: str, limit: int = 100):
            """Get top companies by market cap from CompaniesMarketCap.com"""
            result = await self.get_marketcap_data_eventbus_first(country, limit)
            return result
        
        @self.app.get("/marketcap/search/{query}")
        async def search_company_marketcap(query: str):
            """Search for specific company market cap data"""
            result = await self.search_company_eventbus_first(query)
            return result
            
    async def initialize(self) -> bool:
        """Initialize orchestrator with Event-Bus-First approach"""
        try:
            logger.info("Initializing Event-Bus-First Orchestrator")
            
            # 1. Initialisiere Event-Bus (EINZIGE externe Abhängigkeit)
            self.event_bus = EventBusConnector("intelligent-core-orchestrator-eventbus-first")
            await self.event_bus.connect()
            
            # 2. Event-Handler für Response-Tracking setup
            await self._setup_response_handlers()
            
            # 3. Sende "orchestrator.ready" Event
            await self.event_bus.publish({
                'event_type': 'orchestrator.ready',
                'data': {
                    'orchestrator': 'intelligent-core-eventbus-first',
                    'capabilities': ['stock_analysis', 'ml_prediction', 'performance_tracking'],
                    'startup_time': datetime.now().isoformat()
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            self.is_initialized = True
            self.startup_time = datetime.now()
            
            logger.info("Event-Bus-First Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Event-Bus-First orchestrator", error=str(e))
            return False
            
    async def _setup_response_handlers(self):
        """Setup handlers for module responses"""
        
        async def handle_analysis_response(event):
            await self._handle_module_response('analysis', event)
            
        async def handle_ml_response(event):
            await self._handle_module_response('ml_prediction', event)
            
        async def handle_performance_response(event):
            await self._handle_module_response('performance', event)
            
        async def handle_intelligence_response(event):
            await self._handle_module_response('intelligence', event)
        
        # Subscribe to events
        await self.event_bus.subscribe('analysis.completed', handle_analysis_response)
        await self.event_bus.subscribe('ml.prediction.completed', handle_ml_response)
        await self.event_bus.subscribe('performance.calculated', handle_performance_response)
        await self.event_bus.subscribe('intelligence.recommendation.generated', handle_intelligence_response)
        
        # CompaniesMarketCap event handlers
        async def handle_marketcap_response(event):
            await self._handle_module_response('marketcap', event)
        
        await self.event_bus.subscribe('marketcap.data.retrieved', handle_marketcap_response)
            
    async def _handle_module_response(self, module_type: str, event):
        """Handle responses from modules"""
        try:
            # Handle both Event objects and dict-based events
            if hasattr(event, 'data'):
                # Event object
                data = event.data
            else:
                # Dict-based event
                data = event.get('data', {})
            
            request_id = data.get('request_id')
            
            if not request_id or request_id not in self.pending_responses:
                logger.warning(f"Received {module_type} response without valid request_id", 
                             request_id=request_id)
                return
                
            # Store response
            self.pending_responses[request_id][module_type] = {
                'data': data,
                'timestamp': datetime.now(),
                'success': data.get('success', True)
            }
            
            logger.info(f"Received {module_type} response", request_id=request_id)
            
        except Exception as e:
            logger.error(f"Error handling {module_type} response", error=str(e))
            
    async def analyze_stock_eventbus_first(self, request: StockAnalysisRequest, client_ip: str) -> AnalysisResponse:
        """
        EVENT-BUS-FIRST Stock Analysis
        Clean Architecture: Koordination nur über Events
        """
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
                
            logger.info("Starting Event-Bus-First stock analysis", symbol=request.symbol)
            
            # Generate unique request ID für Response-Tracking
            request_id = str(uuid.uuid4())
            
            # Initialize response tracking
            self.pending_responses[request_id] = {}
            
            # SCHRITT 1: Technical Analysis über Event-Bus anfordern
            await self.event_bus.publish({
                'event_type': 'analysis.requested',
                'data': {
                    'request_id': request_id,
                    'symbol': request.symbol,
                    'client_ip': client_ip,
                    'requested_by': 'intelligent-core-orchestrator-eventbus-first'
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            # Warte auf Analysis Response
            analysis_result = await self._wait_for_module_response(request_id, 'analysis')
            if not analysis_result or not analysis_result.get('success'):
                raise HTTPException(status_code=500, detail="Technical analysis failed")
                
            indicators = analysis_result['data'].get('indicators', {})
            
            # SCHRITT 2: ML Prediction über Event-Bus anfordern  
            await self.event_bus.publish({
                'event_type': 'ml.prediction.requested',
                'data': {
                    'request_id': request_id,
                    'symbol': request.symbol,
                    'indicators': indicators,
                    'requested_by': 'intelligent-core-orchestrator-eventbus-first'
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            # Warte auf ML Response
            ml_result = await self._wait_for_module_response(request_id, 'ml_prediction')
            if not ml_result or not ml_result.get('success'):
                logger.warning("ML prediction failed, continuing with technical analysis only")
                ml_scores = {}
            else:
                ml_scores = ml_result['data'].get('ml_scores', {})
            
            # SCHRITT 3: Performance Calculation über Event-Bus anfordern
            await self.event_bus.publish({
                'event_type': 'performance.calculation.requested',
                'data': {
                    'request_id': request_id,
                    'symbol': request.symbol,
                    'indicators': indicators,
                    'ml_scores': ml_scores,
                    'requested_by': 'intelligent-core-orchestrator-eventbus-first'
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            # SCHRITT 4: Intelligence Recommendation über Event-Bus anfordern
            await self.event_bus.publish({
                'event_type': 'intelligence.recommendation.requested',
                'data': {
                    'request_id': request_id,
                    'symbol': request.symbol,
                    'indicators': indicators,
                    'ml_scores': ml_scores,
                    'requested_by': 'intelligent-core-orchestrator-eventbus-first'
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            # Warte auf Intelligence Response
            intelligence_result = await self._wait_for_module_response(request_id, 'intelligence')
            if not intelligence_result or not intelligence_result.get('success'):
                raise HTTPException(status_code=500, detail="Intelligence recommendation failed")
                
            # Combine results
            recommendation_data = intelligence_result['data']
            
            # Cleanup response tracking
            del self.pending_responses[request_id]
            
            # Build final response
            response = AnalysisResponse(
                symbol=request.symbol,
                score=recommendation_data.get('score', 0.5),
                recommendation=recommendation_data.get('recommendation', 'HOLD'),
                confidence=recommendation_data.get('confidence', 0.5),
                indicators=indicators,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info("Event-Bus-First analysis completed successfully", 
                       symbol=request.symbol, 
                       recommendation=response.recommendation)
            
            return response
            
        except Exception as e:
            # Cleanup in case of error
            if request_id in self.pending_responses:
                del self.pending_responses[request_id]
                
            logger.error("Event-Bus-First analysis failed", symbol=request.symbol, error=str(e))
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
            
    async def _wait_for_module_response(self, request_id: str, module_type: str, timeout: int = None) -> Optional[Dict[str, Any]]:
        """Wait for specific module response with timeout"""
        timeout = timeout or self.response_timeout
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if (request_id in self.pending_responses and 
                module_type in self.pending_responses[request_id]):
                
                return self.pending_responses[request_id][module_type]
                
            await asyncio.sleep(0.1)  # Check every 100ms
            
        logger.error(f"Timeout waiting for {module_type} response", 
                    request_id=request_id, timeout=timeout)
        return None
    
    async def get_marketcap_data_eventbus_first(self, country: str, limit: int = 100) -> Dict[str, Any]:
        """
        EVENT-BUS-FIRST MarketCap Data Retrieval
        Get top companies by market cap from CompaniesMarketCap.com
        """
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
                
            logger.info("Starting Event-Bus-First marketcap data retrieval", 
                       country=country, limit=limit)
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Initialize response tracking
            self.pending_responses[request_id] = {}
            
            # Send MarketCap-Request-Event
            await self.event_bus.publish({
                'event_type': 'marketcap.data.requested',
                'data': {
                    'request_id': request_id,
                    'country': country,
                    'limit': limit,
                    'requested_by': 'intelligent-core-orchestrator-eventbus-first'
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            # Wait for MarketCap Response
            marketcap_result = await self._wait_for_module_response(request_id, 'marketcap')
            if not marketcap_result or not marketcap_result.get('success'):
                raise HTTPException(status_code=500, detail="MarketCap data retrieval failed")
                
            # Build response
            marketcap_data = marketcap_result['data']
            response = {
                'success': True,
                'companies': marketcap_data.get('companies', []),
                'total_count': marketcap_data.get('total_count', 0),
                'country': country,
                'source': 'companiesmarketcap.com',
                'timestamp': datetime.now().isoformat()
            }
            
            # Cleanup
            del self.pending_responses[request_id]
            
            logger.info("Event-Bus-First marketcap data retrieval completed", 
                       country=country, count=response['total_count'])
            
            return response
            
        except Exception as e:
            # Cleanup in case of error
            if request_id in self.pending_responses:
                del self.pending_responses[request_id]
                
            logger.error("Event-Bus-First marketcap data retrieval failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"MarketCap failed: {str(e)}")
    
    async def search_company_eventbus_first(self, query: str) -> Dict[str, Any]:
        """
        EVENT-BUS-FIRST Company Search
        Search for specific company in MarketCap data
        """
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
                
            logger.info("Starting Event-Bus-First company search", query=query)
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Initialize response tracking
            self.pending_responses[request_id] = {}
            
            # Send Company-Lookup-Event
            await self.event_bus.publish({
                'event_type': 'company.lookup.requested',
                'data': {
                    'request_id': request_id,
                    'query': query,
                    'requested_by': 'intelligent-core-orchestrator-eventbus-first'
                },
                'source': 'intelligent-core-orchestrator-eventbus-first'
            })
            
            # Wait for Company Response
            company_result = await self._wait_for_module_response(request_id, 'marketcap')
            if not company_result or not company_result.get('success'):
                return {
                    'success': False,
                    'error': f'Company "{query}" not found',
                    'source': 'companiesmarketcap.com'
                }
                
            # Build response
            company_data = company_result['data']
            response = {
                'success': True,
                'company': company_data.get('company', {}),
                'source': 'companiesmarketcap.com',
                'timestamp': datetime.now().isoformat()
            }
            
            # Cleanup
            del self.pending_responses[request_id]
            
            logger.info("Event-Bus-First company search completed", 
                       query=query, found=response['success'])
            
            return response
            
        except Exception as e:
            # Cleanup in case of error
            if request_id in self.pending_responses:
                del self.pending_responses[request_id]
                
            logger.error("Event-Bus-First company search failed", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'source': 'companiesmarketcap.com'
            }
        
    async def shutdown(self):
        """Shutdown orchestrator"""
        try:
            logger.info("Shutting down Event-Bus-First Orchestrator")
            
            if self.event_bus:
                await self.event_bus.disconnect()
                
            self.is_initialized = False
            logger.info("Event-Bus-First Orchestrator shutdown complete")
            
        except Exception as e:
            logger.error("Error during Event-Bus-First orchestrator shutdown", error=str(e))

# Main execution
if __name__ == "__main__":
    orchestrator = EventBusFirstOrchestrator(port=8011)
    
    try:
        logger.info("Starting Event-Bus-First Intelligent-Core Orchestrator on port 8011")
        uvicorn.run(
            orchestrator.app,
            host="0.0.0.0",
            port=8011,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Event-Bus-First Orchestrator stopped by user")
    except Exception as e:
        logger.error("Failed to start Event-Bus-First orchestrator", error=str(e))
        sys.exit(1)