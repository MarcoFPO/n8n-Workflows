#!/usr/bin/env python3
"""
EVENT-BUS-FIRST Broker-Gateway Service Orchestrator
Clean Architecture: ALLE Kommunikation nur über Event-Bus
Ersetzt direkte Module-Importe mit Event-basierter Koordination
"""

import sys
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Shared Libraries Import (NUR Event-Bus, KEINE direkten Module-Importe)
from shared import (
    # Basis-Klassen
    ModularService, 
    # Standard-Imports
    datetime, Dict, Any, Optional, List,
    FastAPI, HTTPException, BackgroundTasks, BaseModel, Field,
    # Security & Logging
    SecurityConfig, setup_logging,
    # Utilities
    get_current_timestamp, safe_get_env
)

# Event-Bus EINZIGE externe Abhängigkeit
from shared.event_bus import EventBusConnector, Event, EventType

# Environment laden
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Logging setup
logger = setup_logging("broker-gateway-orchestrator-eventbus-first")

# Pydantic Models für API
class OrderRequest(BaseModel):
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None

class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    status: str
    message: str
    timestamp: str

class AccountBalance(BaseModel):
    balance: float
    currency: str
    last_updated: str

class MarketData(BaseModel):
    symbol: str
    price: float
    volume: int
    timestamp: str

class EventBusFirstBrokerGateway:
    """
    EVENT-BUS-FIRST Broker-Gateway
    Clean Architecture Compliance: KEINE direkten Module-Importe
    """
    
    def __init__(self, port: int = 8012):
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
            title="Broker-Gateway Orchestrator (Event-Bus-First)",
            description="Clean Architecture: Nur Event-Bus Kommunikation",
            version="1.0.0"
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
                "service": "broker-gateway-orchestrator-eventbus-first",
                "initialized": self.is_initialized,
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "event_bus_connected": self.event_bus.is_connected() if self.event_bus else False
            }
            
        @self.app.post("/order/place")
        async def place_order(order: OrderRequest):
            result = await self.place_order_eventbus_first(order)
            return result
            
        @self.app.get("/account/balance")
        async def get_balance():
            result = await self.get_account_balance_eventbus_first()
            return result
            
        @self.app.get("/market/{symbol}")
        async def get_market_data(symbol: str):
            result = await self.get_market_data_eventbus_first(symbol)
            return result
            
    async def initialize(self) -> bool:
        """Initialize orchestrator with Event-Bus-First approach"""
        try:
            logger.info("Initializing Event-Bus-First Broker-Gateway")
            
            # 1. Initialisiere Event-Bus (EINZIGE externe Abhängigkeit)
            self.event_bus = EventBusConnector("broker-gateway-orchestrator-eventbus-first")
            await self.event_bus.connect()
            
            # 2. Event-Handler für Response-Tracking setup
            await self._setup_response_handlers()
            
            # 3. Sende "orchestrator.ready" Event
            await self.event_bus.publish({
                'event_type': 'orchestrator.ready',
                'data': {
                    'orchestrator': 'broker-gateway-eventbus-first',
                    'capabilities': ['order_management', 'account_balance', 'market_data'],
                    'startup_time': datetime.now().isoformat()
                },
                'source': 'broker-gateway-orchestrator-eventbus-first'
            })
            
            self.is_initialized = True
            self.startup_time = datetime.now()
            
            logger.info("Event-Bus-First Broker-Gateway initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Event-Bus-First broker-gateway", error=str(e))
            return False
            
    async def _setup_response_handlers(self):
        """Setup handlers for module responses"""
        
        async def handle_order_response(event):
            await self._handle_module_response('order_placement', event)
            
        async def handle_balance_response(event):
            await self._handle_module_response('account_balance', event)
            
        async def handle_market_response(event):
            await self._handle_module_response('market_data', event)
        
        # Subscribe to events
        await self.event_bus.subscribe('order.placed', handle_order_response)
        await self.event_bus.subscribe('account.balance.retrieved', handle_balance_response)
        await self.event_bus.subscribe('market.data.retrieved', handle_market_response)
            
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
            
    async def place_order_eventbus_first(self, order: OrderRequest) -> OrderResponse:
        """
        EVENT-BUS-FIRST Order Placement
        Clean Architecture: Koordination nur über Events
        """
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
                
            logger.info("Starting Event-Bus-First order placement", symbol=order.symbol)
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Initialize response tracking
            self.pending_responses[request_id] = {}
            
            # Sende Order-Placement-Event
            await self.event_bus.publish({
                'event_type': 'order.placement.requested',
                'data': {
                    'request_id': request_id,
                    'symbol': order.symbol,
                    'side': order.side,
                    'quantity': order.quantity,
                    'order_type': order.order_type,
                    'price': order.price,
                    'requested_by': 'broker-gateway-orchestrator-eventbus-first'
                },
                'source': 'broker-gateway-orchestrator-eventbus-first'
            })
            
            # Warte auf Order Response
            order_result = await self._wait_for_module_response(request_id, 'order_placement')
            if not order_result or not order_result.get('success'):
                raise HTTPException(status_code=500, detail="Order placement failed")
                
            # Build response
            order_data = order_result['data']
            response = OrderResponse(
                order_id=order_data.get('order_id', request_id),
                symbol=order.symbol,
                status=order_data.get('status', 'placed'),
                message=order_data.get('message', 'Order placed successfully'),
                timestamp=datetime.now().isoformat()
            )
            
            # Cleanup
            del self.pending_responses[request_id]
            
            logger.info("Event-Bus-First order placement completed", 
                       symbol=order.symbol, 
                       order_id=response.order_id)
            
            return response
            
        except Exception as e:
            # Cleanup in case of error
            if request_id in self.pending_responses:
                del self.pending_responses[request_id]
                
            logger.error("Event-Bus-First order placement failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Order failed: {str(e)}")
            
    async def get_account_balance_eventbus_first(self) -> AccountBalance:
        """
        EVENT-BUS-FIRST Account Balance Retrieval
        """
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
                
            logger.info("Starting Event-Bus-First balance retrieval")
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Initialize response tracking
            self.pending_responses[request_id] = {}
            
            # Sende Balance-Request-Event
            await self.event_bus.publish({
                'event_type': 'account.balance.requested',
                'data': {
                    'request_id': request_id,
                    'requested_by': 'broker-gateway-orchestrator-eventbus-first'
                },
                'source': 'broker-gateway-orchestrator-eventbus-first'
            })
            
            # Warte auf Balance Response
            balance_result = await self._wait_for_module_response(request_id, 'account_balance')
            if not balance_result or not balance_result.get('success'):
                raise HTTPException(status_code=500, detail="Balance retrieval failed")
                
            # Build response
            balance_data = balance_result['data']
            response = AccountBalance(
                balance=balance_data.get('balance', 0.0),
                currency=balance_data.get('currency', 'EUR'),
                last_updated=datetime.now().isoformat()
            )
            
            # Cleanup
            del self.pending_responses[request_id]
            
            logger.info("Event-Bus-First balance retrieval completed", balance=response.balance)
            
            return response
            
        except Exception as e:
            # Cleanup in case of error
            if request_id in self.pending_responses:
                del self.pending_responses[request_id]
                
            logger.error("Event-Bus-First balance retrieval failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Balance failed: {str(e)}")
            
    async def get_market_data_eventbus_first(self, symbol: str) -> MarketData:
        """
        EVENT-BUS-FIRST Market Data Retrieval
        """
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
                
            logger.info("Starting Event-Bus-First market data retrieval", symbol=symbol)
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Initialize response tracking
            self.pending_responses[request_id] = {}
            
            # Sende Market-Data-Request-Event
            await self.event_bus.publish({
                'event_type': 'market.data.requested',
                'data': {
                    'request_id': request_id,
                    'symbol': symbol,
                    'requested_by': 'broker-gateway-orchestrator-eventbus-first'
                },
                'source': 'broker-gateway-orchestrator-eventbus-first'
            })
            
            # Warte auf Market Data Response
            market_result = await self._wait_for_module_response(request_id, 'market_data')
            if not market_result or not market_result.get('success'):
                raise HTTPException(status_code=500, detail="Market data retrieval failed")
                
            # Build response
            market_data = market_result['data']
            response = MarketData(
                symbol=symbol,
                price=market_data.get('price', 0.0),
                volume=market_data.get('volume', 0),
                timestamp=datetime.now().isoformat()
            )
            
            # Cleanup
            del self.pending_responses[request_id]
            
            logger.info("Event-Bus-First market data retrieval completed", 
                       symbol=symbol, price=response.price)
            
            return response
            
        except Exception as e:
            # Cleanup in case of error
            if request_id in self.pending_responses:
                del self.pending_responses[request_id]
                
            logger.error("Event-Bus-First market data retrieval failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Market data failed: {str(e)}")
            
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
        
    async def shutdown(self):
        """Shutdown orchestrator"""
        try:
            logger.info("Shutting down Event-Bus-First Broker-Gateway")
            
            if self.event_bus:
                await self.event_bus.disconnect()
                
            self.is_initialized = False
            logger.info("Event-Bus-First Broker-Gateway shutdown complete")
            
        except Exception as e:
            logger.error("Error during Event-Bus-First broker-gateway shutdown", error=str(e))

# Main execution
if __name__ == "__main__":
    import uvicorn
    
    orchestrator = EventBusFirstBrokerGateway(port=8012)
    
    try:
        logger.info("Starting Event-Bus-First Broker-Gateway Orchestrator on port 8012")
        uvicorn.run(
            orchestrator.app,
            host="0.0.0.0",
            port=8012,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Event-Bus-First Broker-Gateway stopped by user")
    except Exception as e:
        logger.error("Failed to start Event-Bus-First broker-gateway", error=str(e))
        sys.exit(1)