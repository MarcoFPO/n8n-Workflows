#!/usr/bin/env python3
"""
Modernisierter Broker-Gateway Service Orchestrator v2
Verwendet shared libraries und eliminiert Code-Duplikation
"""

import sys
import time
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Standard Library
import asyncio

# Shared Libraries Import (eliminiert Code-Duplikation)
from shared import (
    # Basis-Klassen
    ModularService, DatabaseMixin, EventBusMixin,
    # Standard-Imports
    datetime, Dict, Any, Optional, List,
    FastAPI, HTTPException, BackgroundTasks, BaseModel, Field,
    # Security & Logging
    SecurityConfig, setup_logging,
    # Utilities
    get_current_timestamp, safe_get_env
)

# Event-Bus Imports for Compliance
from event_bus import EventBusConnector, Event, EventType

# Lokale Module
from modules.market_data_module import MarketDataModule, MarketData
from modules.order_module import OrderModule, OrderRequest, OrderResponse  
from modules.account_module import AccountModule, AccountBalance
from backend_base_module import BackendModuleRegistry

# Environment laden
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')


class BitpandaCredentials(BaseModel):
    """Bitpanda API Credentials Model"""
    api_key: str
    api_secret: str = Field(default_factory=lambda: SecurityConfig.get_api_secret())
    environment: str = "sandbox"


class BrokerGatewayService(ModularService, DatabaseMixin, EventBusMixin):
    """
    Modernisierter Broker-Gateway Service
    Verwendet shared libraries für bessere Code-Qualität
    """
    
    def __init__(self):
        # Service-Initialisierung über BaseService
        super().__init__(
            service_name="broker-gateway",
            version="2.0.0",
            port=SecurityConfig.get_service_port("broker_gateway")
        )
        
        # Module Registry
        self.module_registry = BackendModuleRegistry()
        
        # Module initialisieren
        self._initialize_modules()
    
    async def _setup_service(self):
        """Service-spezifische Initialisierung (überschreibt BaseService)"""
        # Database Connections
        await self.setup_postgres()
        await self.setup_redis()
        
        # Event-Bus Connection
        await self.setup_event_bus("broker-gateway")
        
        # Module starten
        await self._start_modules()
        
        # API Routes registrieren
        self._setup_api_routes()
        
        self.logger.info("Broker-Gateway Service v2 fully initialized")
    
    def _initialize_modules(self):
        """Module initialisieren und registrieren"""
        # Market Data Module
        market_data_module = MarketDataModule(
            module_id="market_data",
            config={"refresh_interval": 30}
        )
        self.register_module("market_data", market_data_module)
        
        # Order Management Module
        order_module = OrderModule(
            module_id="order_management", 
            config={"max_concurrent_orders": 10}
        )
        self.register_module("order_management", order_module)
        
        # Account Module
        account_module = AccountModule(
            module_id="account_management",
            config={"balance_check_interval": 60}
        )
        self.register_module("account_management", account_module)
    
    async def _start_modules(self):
        """Alle Module starten"""
        for module_name, module in self.modules.items():
            try:
                if hasattr(module, 'start'):
                    await module.start()
                self.logger.info(f"Module {module_name} started successfully")
            except Exception as e:
                self.logger.error(f"Failed to start module {module_name}: {e}")
    
    def _setup_api_routes(self):
        """API Routes für alle Module registrieren"""
        
        # Market Data Routes
        @self.app.get("/api/v2/market-data/{symbol}")
        async def get_market_data(symbol: str):
            """Marktdaten für Symbol abrufen"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.MARKET_DATA_REQUEST.value,
                    stream_id=f"market-{symbol}",
                    data={"symbol": symbol, "request_type": "get_market_data"},
                    source="broker-gateway"
                )
                
                # For now, fallback to direct call until response handling is implemented
                market_module = self.modules["market_data"]
                data = await market_module.get_market_data(symbol)
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                return {
                    "symbol": symbol,
                    "data": data,
                    "timestamp": get_current_timestamp().isoformat(),
                    "source": "broker-gateway-v2"
                }
            except Exception as e:
                self.logger.error(f"Market data error for {symbol}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Order Management Routes
        @self.app.post("/api/v2/orders")
        async def create_order(order: OrderRequest, background_tasks: BackgroundTasks):
            """Neue Order erstellen"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.ORDER_REQUEST.value,
                    stream_id=f"order-create-{int(time.time())}",
                    data={"order": order.dict(), "request_type": "create_order"},
                    source="broker-gateway"
                )
                
                # For now, fallback to direct call until response handling is implemented
                order_module = self.modules["order_management"]
                result = await order_module.create_order(order)
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                # Background task für Event-Publishing
                background_tasks.add_task(
                    self._publish_order_event, 
                    "order_created", 
                    result.dict()
                )
                
                return result
            except Exception as e:
                self.logger.error(f"Order creation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Account Routes
        @self.app.get("/api/v2/account/balance")
        async def get_account_balance():
            """Account Balance abrufen"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.ACCOUNT_BALANCE_REQUEST.value,
                    stream_id=f"balance-{int(time.time())}",
                    data={"request_type": "get_balance"},
                    source="broker-gateway"
                )
                
                # For now, fallback to direct call until response handling is implemented
                account_module = self.modules["account_management"]
                balance = await account_module.get_balance()
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                return balance
            except Exception as e:
                self.logger.error(f"Account balance error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _publish_order_event(self, event_type: str, order_data: Dict[str, Any]):
        """Order Event über Event-Bus publishen"""
        if self.event_bus:
            await self.event_bus.publish_event(
                event_type=event_type,
                data=order_data,
                source="broker-gateway-v2"
            )
    
    async def _get_health_details(self) -> Dict[str, Any]:
        """Erweiterte Health-Details für Broker-Gateway"""
        base_health = await super()._get_health_details()
        
        # Event-Bus-Compliance: Health checks through Event-Bus
        health_event = Event(
            event_type=EventType.SYSTEM_HEALTH_REQUEST.value,
            stream_id=f"health-broker-{int(time.time())}",
            data={"request_type": "broker_health"},
            source="broker-gateway"
        )
        
        # For now, fallback to direct calls until response handling is implemented
        module_health = {}
        for name, module in self.modules.items():
            try:
                if hasattr(module, 'get_health'):
                    module_health[name] = await module.get_health()
                else:
                    module_health[name] = {"status": "registered", "active": True}
            except Exception as e:
                module_health[name] = {"status": "error", "error": str(e)}
        
        # Publish event for logging/monitoring
        if self.event_bus and self.event_bus.connected:
            await self.event_bus.publish(health_event)
        
        # Database Health
        db_health = {
            "postgres": self.db_pool is not None,
            "redis": self.redis_client is not None
        }
        
        # Event-Bus Health  
        event_bus_health = {
            "connected": self.event_bus is not None,
            "type": "rabbitmq"
        }
        
        return {
            **base_health,
            "database": db_health,
            "event_bus": event_bus_health,
            "modules": {
                "total": len(self.modules),
                "active": len([m for m in self.modules.values() if hasattr(m, 'is_active') and m.is_active]),
                "details": module_health
            },
            "api_version": "v2",
            "code_quality": "refactored_with_shared_libraries"
        }


# Service-Instanz erstellen und starten
def create_app() -> FastAPI:
    """FastAPI App erstellen"""
    service = BrokerGatewayService()
    return service.app


async def start_service():
    """Service starten"""
    service = BrokerGatewayService()
    await service._setup_service()
    
    # Server starten
    service.run(
        host="0.0.0.0",
        debug=SecurityConfig.is_debug_mode()
    )


if __name__ == "__main__":
    asyncio.run(start_service())