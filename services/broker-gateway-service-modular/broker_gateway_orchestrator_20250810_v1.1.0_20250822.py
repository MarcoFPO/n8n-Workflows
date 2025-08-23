#!/usr/bin/env python3
"""
Modularer Broker-Gateway Service Orchestrator
Koordiniert Market Data, Order Management und Account Module
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add paths for imports

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared') -> Import Manager

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import structlog
import asyncpg

# Shared imports
from backend_base_module import BackendModuleRegistry
from event_bus import EventBusConnector, EventType
from logging_config import setup_logging

# Module imports
from modules.market_data_module_v1_2_0_20250810 import MarketDataModule, MarketData
from modules.order_module_v1_1_0_20250809 import OrderModule, OrderRequest, OrderResponse
from modules.account_module_v1_1_0_20250809 import AccountModule, AccountBalance

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Logging setup
logger = setup_logging("broker-gateway-modular")

# Pydantic Models
class BitpandaCredentials(BaseModel):
    api_key: str
    api_secret: str = "dummy_secret"
    environment: str = "sandbox"


class BrokerGatewayOrchestrator:
    """Orchestrator für alle Broker-Gateway Module"""
    
    def __init__(self):
        self.event_bus = EventBusConnector("broker-gateway-modular")
        self.module_registry = BackendModuleRegistry("broker-gateway-modular", self.event_bus)
        
        # Initialize modules
        self.market_data_module = MarketDataModule(self.event_bus)
        self.order_module = OrderModule(self.event_bus)
        self.account_module = AccountModule(self.event_bus)
        
        # Database connection
        self.db_pool: Optional[asyncpg.Pool] = None
        
        # Service state
        self.is_initialized = False
        self.startup_time = None
        
    async def initialize(self) -> bool:
        """Initialize orchestrator and all modules"""
        try:
            logger.info("Initializing Broker-Gateway Orchestrator")
            
            # Initialize database connection
            await self._initialize_database()
            
            # Connect to event bus
            event_bus_connected = await self.event_bus.connect()
            if not event_bus_connected:
                logger.error("Failed to connect to event bus")
                return False
            
            # Register all modules
            self.module_registry.register_module(self.market_data_module)
            self.module_registry.register_module(self.order_module)
            self.module_registry.register_module(self.account_module)
            
            # Initialize all modules
            initialization_results = await self.module_registry.initialize_all_modules()
            
            # Check if all modules initialized successfully
            failed_modules = [name for name, success in initialization_results.items() if not success]
            if failed_modules:
                logger.error("Some modules failed to initialize", failed_modules=failed_modules)
                # Continue with partial initialization
            
            self.is_initialized = True
            self.startup_time = datetime.now()
            
            logger.info("Broker-Gateway Orchestrator initialized successfully",
                       modules_initialized=len(initialization_results),
                       failed_modules=len(failed_modules))
            
            return True
            
        except Exception as e:
            logger.error("Failed to initialize orchestrator", error=str(e))
            return False
    
    async def _initialize_database(self):
        """Initialize database connection"""
        try:
            postgres_url = os.getenv(
                "POSTGRES_URL", 
                "postgresql://aktienanalyse:secure_password@localhost:5432/aktienanalyse_events?sslmode=disable"
            )
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=2, max_size=10)
            logger.info("Database connection established")
        except Exception as e:
            logger.warning("Database connection failed", error=str(e))
            # Continue without database (using in-memory storage)
    
    async def shutdown(self):
        """Shutdown orchestrator and all modules"""
        try:
            logger.info("Shutting down Broker-Gateway Orchestrator")
            
            await self.module_registry.shutdown_all_modules()
            await self.event_bus.disconnect()
            
            if self.db_pool:
                await self.db_pool.close()
            
            self.is_initialized = False
            logger.info("Orchestrator shutdown complete")
            
        except Exception as e:
            logger.error("Error during orchestrator shutdown", error=str(e))
    
    async def get_account_balances(self, credentials: BitpandaCredentials) -> List[AccountBalance]:
        """Get account balances through account module"""
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            result = await self.account_module.process_business_logic({
                'type': 'get_balances',
                'credentials': credentials.dict()
            })
            
            if not result.get('success', False):
                raise HTTPException(status_code=500, detail=result.get('error', 'Failed to get balances'))
            
            # Convert to AccountBalance objects
            balances = []
            for currency, balance_data in result['balances'].items():
                balances.append(AccountBalance(**balance_data))
            
            # Publish account event
            await self.event_bus.publish_event(
                "account.balances.retrieved",
                "account_balances",
                {
                    "balances_count": len(balances),
                    "currencies": [b.currency_code for b in balances]
                }
            )
            
            return balances
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting account balances", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get balances: {str(e)}")
    
    async def get_market_data(self, instrument_code: str) -> MarketData:
        """Get market data through market data module"""
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            result = await self.market_data_module.process_business_logic({
                'type': 'get_market_data',
                'instrument_code': instrument_code
            })
            
            if not result.get('success', False):
                raise HTTPException(status_code=500, detail=result.get('error', 'Failed to get market data'))
            
            market_data = MarketData(**result['data'])
            
            # Store in database if available
            if self.db_pool:
                await self._store_market_data_in_db(market_data)
            
            return market_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting market data", 
                        instrument=instrument_code, 
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")
    
    async def place_order(self, order_request: OrderRequest, credentials: BitpandaCredentials) -> OrderResponse:
        """Place order through order module"""
        try:
            if not self.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            # Check account capacity first
            capacity_check = await self.account_module.process_business_logic({
                'type': 'check_trading_capacity',
                'currency_code': 'EUR',  # Simplified for demo
                'amount': order_request.amount
            })
            
            if not capacity_check.get('success', False) or not capacity_check.get('has_capacity', False):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient capacity: {capacity_check.get('reason', 'Unknown error')}"
                )
            
            # Place order
            result = await self.order_module.process_business_logic({
                'type': 'place_order',
                'order_request': order_request.dict(),
                'credentials': credentials.dict()
            })
            
            if not result.get('success', False):
                raise HTTPException(status_code=500, detail=result.get('error', 'Failed to place order'))
            
            order_response = OrderResponse(**result['order'])
            
            # Process account transaction if order is filled
            if order_response.status.value in ['FILLED', 'PARTIALLY_FILLED']:
                await self._process_order_fill(order_response)
            
            # Store in database if available
            if self.db_pool:
                await self._store_order_in_db(order_response)
            
            return order_response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error placing order", 
                        order=order_request.dict(), 
                        error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")
    
    async def _process_order_fill(self, order: OrderResponse):
        """Process account transactions for filled orders"""
        try:
            filled_amount = float(order.filled_amount)
            if filled_amount <= 0:
                return
            
            # Determine currencies involved
            if '_' in order.instrument_code:
                # Crypto pair (e.g., BTC_EUR)
                base_currency, quote_currency = order.instrument_code.split('_')
            else:
                # Stock (assume EUR)
                base_currency = order.instrument_code
                quote_currency = 'EUR'
            
            # Calculate transaction amounts
            if order.average_price:
                price = float(order.average_price)
                quote_amount = filled_amount * price
            else:
                # Fallback for market orders without average price
                quote_amount = filled_amount * 100  # Mock price
            
            # Process transactions based on order side
            if order.side.value == 'BUY':
                # Buying: decrease quote currency, increase base currency
                await self.account_module.process_business_logic({
                    'type': 'process_transaction',
                    'transaction_type': 'trade_buy',
                    'currency_code': quote_currency,
                    'amount': str(quote_amount),
                    'description': f'Buy {order.instrument_code}',
                    'order_id': order.order_id
                })
                
                await self.account_module.process_business_logic({
                    'type': 'process_transaction',
                    'transaction_type': 'trade_sell',
                    'currency_code': base_currency,
                    'amount': str(filled_amount),
                    'description': f'Received {order.instrument_code}',
                    'order_id': order.order_id
                })
                
            else:  # SELL
                # Selling: decrease base currency, increase quote currency
                await self.account_module.process_business_logic({
                    'type': 'process_transaction',
                    'transaction_type': 'trade_buy',
                    'currency_code': base_currency,
                    'amount': str(filled_amount),
                    'description': f'Sell {order.instrument_code}',
                    'order_id': order.order_id
                })
                
                await self.account_module.process_business_logic({
                    'type': 'process_transaction',
                    'transaction_type': 'trade_sell',
                    'currency_code': quote_currency,
                    'amount': str(quote_amount),
                    'description': f'Received from {order.instrument_code} sale',
                    'order_id': order.order_id
                })
            
            # Process trading fee (0.1% for demo)
            fee_amount = quote_amount * 0.001
            await self.account_module.process_business_logic({
                'type': 'process_transaction',
                'transaction_type': 'fee',
                'currency_code': quote_currency,
                'amount': str(fee_amount),
                'description': f'Trading fee for {order.order_id}',
                'order_id': order.order_id
            })
            
        except Exception as e:
            logger.error("Error processing order fill", 
                        order_id=order.order_id, 
                        error=str(e))
    
    async def _store_market_data_in_db(self, market_data: MarketData):
        """Store market data in database"""
        try:
            if not self.db_pool:
                return
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO market_data_events (
                        instrument_code, last_price, best_bid, best_ask,
                        price_change, price_change_percentage, volume_24h,
                        timestamp, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                market_data.instrument_code,
                market_data.last_price,
                market_data.best_bid,
                market_data.best_ask,
                market_data.price_change,
                market_data.price_change_percentage,
                market_data.volume_24h,
                market_data.timestamp,
                datetime.now()
                )
                
        except Exception as e:
            logger.warning("Failed to store market data in database", error=str(e))
    
    async def _store_order_in_db(self, order: OrderResponse):
        """Store order in database"""
        try:
            if not self.db_pool:
                return
            
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO order_events (
                        order_id, client_id, status, instrument_code, side, type,
                        amount, filled_amount, remaining_amount, price, average_price,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                order.order_id,
                order.client_id,
                order.status.value,
                order.instrument_code,
                order.side.value,
                order.type.value,
                order.amount,
                order.filled_amount,
                order.remaining_amount,
                order.price,
                order.average_price,
                order.created_at,
                order.updated_at
                )
                
        except Exception as e:
            logger.warning("Failed to store order in database", error=str(e))
    
    async def get_order_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get order history from order module"""
        try:
            result = await self.order_module.process_business_logic({
                'type': 'get_order_history',
                'limit': limit
            })
            
            return result
            
        except Exception as e:
            logger.error("Error getting order history", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get order history: {str(e)}")
    
    async def get_supported_brokers(self) -> Dict[str, Any]:
        """Get list of supported brokers"""
        return {
            "supported_brokers": [
                {
                    "name": "Bitpanda Pro",
                    "code": "bitpanda",
                    "features": ["spot_trading", "market_data", "account_info"],
                    "environments": ["sandbox", "production"],
                    "supported_instruments": await self._get_supported_instruments()
                }
            ],
            "total_count": 1
        }
    
    async def _get_supported_instruments(self) -> List[str]:
        """Get supported instruments from market data module"""
        try:
            result = await self.market_data_module.process_business_logic({
                'type': 'get_instruments'
            })
            
            if result.get('success'):
                return result.get('instruments', [])
            return []
            
        except Exception as e:
            logger.error("Error getting supported instruments", error=str(e))
            return []
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            # Get module status
            module_status = self.module_registry.get_all_module_status()
            
            # Calculate service health
            healthy_modules = sum(1 for module in module_status['modules'].values() 
                                if module.get('is_initialized', False))
            total_modules = len(module_status['modules'])
            
            # Test database connection
            db_healthy = False
            if self.db_pool:
                try:
                    async with self.db_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                    db_healthy = True
                except Exception as e:
                    self.logger.warning(f"Database health check failed: {e}")
                    db_healthy = False
            
            service_healthy = (
                self.is_initialized and 
                self.event_bus.connected and 
                healthy_modules >= total_modules * 0.75
            )
            
            return {
                'service': 'broker-gateway-modular',
                'status': 'healthy' if service_healthy else 'unhealthy',
                'version': '1.0.0-modular',
                'startup_time': self.startup_time.isoformat() if self.startup_time else None,
                'uptime_seconds': (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0,
                'database': {
                    'connected': db_healthy,
                    'pool_size': self.db_pool.get_size() if self.db_pool else 0
                },
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
                'service': 'broker-gateway-modular',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Global orchestrator instance
orchestrator = BrokerGatewayOrchestrator()

# FastAPI Application
app = FastAPI(
    title="Broker Gateway Service - Modular",
    description="Modularer Trading und Market Data Service",
    version="1.0.0-modular",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    logger.info("Starting Broker-Gateway Modular Service...")
    success = await orchestrator.initialize()
    if not success:
        logger.error("Failed to initialize service")
        raise RuntimeError("Service initialization failed")
    logger.info("Broker-Gateway Modular Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Broker-Gateway Modular Service...")
    await orchestrator.shutdown()
    logger.info("Service stopped")

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    return await orchestrator.get_service_health()

# Bitpanda Pro Endpoints
@app.get("/bitpanda/balances", response_model=List[AccountBalance])
async def get_bitpanda_balances(
    api_key: str,
    environment: str = "sandbox"
):
    """Get account balances from Bitpanda Pro"""
    credentials = BitpandaCredentials(
        api_key=api_key,
        api_secret="dummy_secret",
        environment=environment
    )
    return await orchestrator.get_account_balances(credentials)

@app.get("/bitpanda/market/{instrument_code}", response_model=MarketData)
async def get_bitpanda_market_data(instrument_code: str):
    """Get market data for trading pair"""
    return await orchestrator.get_market_data(instrument_code)

@app.post("/bitpanda/orders", response_model=OrderResponse)
async def place_bitpanda_order(
    order_request: OrderRequest,
    api_key: str,
    environment: str = "sandbox"
):
    """Place order via Bitpanda Pro"""
    credentials = BitpandaCredentials(
        api_key=api_key,
        api_secret="dummy_secret",
        environment=environment
    )
    return await orchestrator.place_order(order_request, credentials)

# Generic Broker Endpoints
@app.get("/brokers/supported")
async def get_supported_brokers():
    """Get list of supported brokers"""
    return await orchestrator.get_supported_brokers()

@app.get("/orders/history")
async def get_order_history(limit: int = 50):
    """Get order history"""
    return await orchestrator.get_order_history(limit)

# Module-specific endpoints
@app.get("/modules")
async def list_modules():
    """List all available modules"""
    module_status = orchestrator.module_registry.get_all_module_status()
    return {
        'service': 'broker-gateway-modular',
        'modules': list(module_status['modules'].keys()),
        'module_details': module_status['modules']
    }

@app.get("/market-data/instruments")
async def get_supported_instruments():
    """Get supported trading instruments"""
    result = await orchestrator.market_data_module.process_business_logic({
        'type': 'get_instruments'
    })
    return result

@app.get("/account/portfolio")
async def get_portfolio_summary():
    """Get portfolio summary"""
    result = await orchestrator.account_module.process_business_logic({
        'type': 'get_portfolio_summary'
    })
    return result

@app.get("/orders/active")
async def get_active_orders():
    """Get active orders"""
    result = await orchestrator.order_module.process_business_logic({
        'type': 'get_active_orders'
    })
    return result

if __name__ == "__main__":
    uvicorn.run(
        "broker_gateway_orchestrator:app",
        host="0.0.0.0",
        port=int(os.getenv("BROKER_GATEWAY_MODULAR_PORT", "8012")),
        log_config=None,  # Use our custom logging
        access_log=False   # Disable default access logging
    )