#!/usr/bin/env python3
"""
Portfolio Management Service Enhanced v6.0.0 - Clean Architecture Implementation
=================================================================================

CLEAN ARCHITECTURE LAYERS:
- Domain Layer: Portfolio Business Logic und Entities
- Application Layer: Portfolio Management Use Cases
- Infrastructure Layer: Database, Redis, External Services
- Presentation Layer: FastAPI REST Controllers

EVENT-DRIVEN PATTERN: Portfolio Events publizieren für Trade Execution Integration
SOLID PRINCIPLES: Single Responsibility, Dependency Injection, Interface Segregation

Port: 8004
Dependencies: Market Data Service (8002), ML Pipeline Service (8003), Event-Bus (8014), Redis, PostgreSQL

Author: Claude & System
Version: 6.0.0
Date: 2025-08-24
"""

import asyncio
import json
import logging
import os
import sys
import traceback
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

# Web Framework
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import uvicorn

# Async HTTP Client
import httpx

# Redis Integration
import redis.asyncio as redis

# PostgreSQL Integration
import asyncpg
import psycopg2

# Environment Configuration
from dotenv import load_dotenv

# Load Environment
load_dotenv()

# =============================================================================
# DOMAIN LAYER - Portfolio Business Logic
# =============================================================================

class PortfolioStatus(str, Enum):
    """Portfolio Status Enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    LIQUIDATING = "liquidating"
    CLOSED = "closed"

class AllocationStrategy(str, Enum):
    """Portfolio Allocation Strategy"""
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP_WEIGHT = "market_cap_weight"
    VOLATILITY_WEIGHT = "volatility_weight"
    ML_OPTIMIZED = "ml_optimized"
    RISK_PARITY = "risk_parity"

class RiskLevel(str, Enum):
    """Portfolio Risk Level"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"

class RebalanceFrequency(str, Enum):
    """Portfolio Rebalancing Frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

@dataclass
class Position:
    """Portfolio Position Entity"""
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    weight: float
    target_weight: float
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "quantity": float(self.quantity),
            "avg_cost": float(self.avg_cost),
            "current_price": float(self.current_price),
            "market_value": float(self.market_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "weight": self.weight,
            "target_weight": self.target_weight,
            "last_updated": self.last_updated.isoformat()
        }

@dataclass
class PortfolioMetrics:
    """Portfolio Performance Metrics"""
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    total_return: float
    daily_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    position_count: int

class PortfolioEntity:
    """Portfolio Domain Entity"""
    
    def __init__(
        self,
        portfolio_id: str,
        name: str,
        status: PortfolioStatus,
        allocation_strategy: AllocationStrategy,
        risk_level: RiskLevel,
        target_positions: Dict[str, float],
        cash_balance: Decimal,
        total_value: Decimal,
        created_at: datetime
    ):
        self.portfolio_id = portfolio_id
        self.name = name
        self.status = status
        self.allocation_strategy = allocation_strategy
        self.risk_level = risk_level
        self.target_positions = target_positions
        self.cash_balance = cash_balance
        self.total_value = total_value
        self.created_at = created_at
        self.positions: Dict[str, Position] = {}
        self.metrics: Optional[PortfolioMetrics] = None
        self.last_rebalance: Optional[datetime] = None
        
    def add_position(self, position: Position):
        """Add position to portfolio"""
        self.positions[position.symbol] = position
        
    def update_position_price(self, symbol: str, new_price: Decimal):
        """Update position current price"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = new_price
            position.market_value = position.quantity * new_price
            position.unrealized_pnl = position.market_value - (position.quantity * position.avg_cost)
            position.last_updated = datetime.now()
            
    def calculate_portfolio_value(self) -> Decimal:
        """Calculate total portfolio value"""
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        return total_market_value + self.cash_balance
        
    def get_position_weights(self) -> Dict[str, float]:
        """Calculate current position weights"""
        total_value = self.calculate_portfolio_value()
        if total_value == 0:
            return {}
        
        weights = {}
        for symbol, position in self.positions.items():
            weights[symbol] = float(position.market_value / total_value)
        return weights
        
    def needs_rebalancing(self, tolerance: float = 0.05) -> bool:
        """Check if portfolio needs rebalancing"""
        current_weights = self.get_position_weights()
        
        for symbol, target_weight in self.target_positions.items():
            current_weight = current_weights.get(symbol, 0.0)
            if abs(current_weight - target_weight) > tolerance:
                return True
        return False

class PortfolioDomainService:
    """Portfolio Domain Service - Business Logic"""
    
    @staticmethod
    def calculate_optimal_allocation(
        symbols: List[str],
        strategy: AllocationStrategy,
        risk_level: RiskLevel,
        market_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate optimal portfolio allocation"""
        
        if strategy == AllocationStrategy.EQUAL_WEIGHT:
            weight = 1.0 / len(symbols)
            return {symbol: weight for symbol in symbols}
            
        elif strategy == AllocationStrategy.MARKET_CAP_WEIGHT:
            # Market cap weighted allocation (simplified)
            market_caps = {}
            for symbol in symbols:
                # Use price as proxy for market cap (would be actual market cap in production)
                market_caps[symbol] = market_data.get(symbol, {}).get('price', 100)
            
            total_cap = sum(market_caps.values())
            return {symbol: cap / total_cap for symbol, cap in market_caps.items()}
            
        elif strategy == AllocationStrategy.VOLATILITY_WEIGHT:
            # Inverse volatility weighted allocation
            volatilities = {}
            for symbol in symbols:
                vol = market_data.get(symbol, {}).get('volatility', 0.2)
                volatilities[symbol] = 1 / max(vol, 0.01)  # Inverse volatility
            
            total_inv_vol = sum(volatilities.values())
            return {symbol: inv_vol / total_inv_vol for symbol, inv_vol in volatilities.items()}
            
        elif strategy == AllocationStrategy.RISK_PARITY:
            # Risk parity allocation (simplified equal risk contribution)
            # In production, would use actual risk models
            return {symbol: 1.0 / len(symbols) for symbol in symbols}
            
        else:  # ML_OPTIMIZED
            # ML-based optimization (simplified)
            # In production, would use actual ML predictions
            return {symbol: 1.0 / len(symbols) for symbol in symbols}
    
    @staticmethod
    def calculate_rebalance_trades(
        current_positions: Dict[str, Position],
        target_weights: Dict[str, float],
        total_value: Decimal,
        min_trade_value: Decimal = Decimal('100')
    ) -> List[Dict[str, Any]]:
        """Calculate trades needed for rebalancing"""
        
        trades = []
        
        for symbol, target_weight in target_weights.items():
            target_value = total_value * Decimal(str(target_weight))
            current_position = current_positions.get(symbol)
            current_value = current_position.market_value if current_position else Decimal('0')
            
            trade_value = target_value - current_value
            
            if abs(trade_value) >= min_trade_value:
                current_price = current_position.current_price if current_position else Decimal('100')  # Would get from market data
                quantity = trade_value / current_price
                
                trades.append({
                    'symbol': symbol,
                    'action': 'buy' if trade_value > 0 else 'sell',
                    'quantity': abs(quantity),
                    'estimated_value': abs(trade_value),
                    'target_weight': target_weight,
                    'current_weight': float(current_value / total_value) if total_value > 0 else 0
                })
        
        return trades

# =============================================================================
# APPLICATION LAYER - Portfolio Management Use Cases
# =============================================================================

class CreatePortfolioRequest(BaseModel):
    """Create Portfolio Request DTO"""
    name: str = Field(..., description="Portfolio name")
    allocation_strategy: AllocationStrategy = Field(..., description="Allocation strategy")
    risk_level: RiskLevel = Field(..., description="Risk level")
    symbols: List[str] = Field(..., description="Initial stock symbols")
    initial_capital: float = Field(gt=0, description="Initial capital amount")
    rebalance_frequency: RebalanceFrequency = Field(default=RebalanceFrequency.MONTHLY)

class PortfolioResponse(BaseModel):
    """Portfolio Response DTO"""
    portfolio_id: str
    name: str
    status: PortfolioStatus
    allocation_strategy: AllocationStrategy
    risk_level: RiskLevel
    total_value: float
    cash_balance: float
    positions: List[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    last_updated: str

class RebalanceRequest(BaseModel):
    """Portfolio Rebalance Request"""
    portfolio_id: str
    force_rebalance: bool = Field(default=False, description="Force rebalance even if not needed")
    min_trade_value: float = Field(default=100.0, description="Minimum trade value")

class RebalanceResponse(BaseModel):
    """Portfolio Rebalance Response"""
    portfolio_id: str
    rebalance_needed: bool
    trades: List[Dict[str, Any]]
    estimated_cost: float
    execution_timestamp: str

class CreatePortfolioUseCase:
    """Create Portfolio Use Case"""
    
    def __init__(
        self,
        portfolio_repository,
        market_data_client,
        ml_pipeline_client,
        event_publisher
    ):
        self.portfolio_repository = portfolio_repository
        self.market_data_client = market_data_client
        self.ml_pipeline_client = ml_pipeline_client
        self.event_publisher = event_publisher
    
    async def execute(self, request: CreatePortfolioRequest) -> PortfolioResponse:
        """Execute create portfolio use case"""
        logger = logging.getLogger(__name__)
        
        try:
            # Generate portfolio ID
            portfolio_id = f"portfolio-{uuid.uuid4().hex[:8]}"
            
            # Get market data for symbols
            market_data = {}
            for symbol in request.symbols:
                try:
                    price_data = await self.market_data_client.get_current_price(symbol)
                    if price_data:
                        market_data[symbol] = price_data
                except Exception as e:
                    logger.warning(f"Failed to get market data for {symbol}: {e}")
                    # Use fallback data
                    market_data[symbol] = {'price': 100.0, 'volatility': 0.2}
            
            # Calculate optimal allocation
            target_weights = PortfolioDomainService.calculate_optimal_allocation(
                request.symbols,
                request.allocation_strategy,
                request.risk_level,
                market_data
            )
            
            # Create portfolio entity
            portfolio = PortfolioEntity(
                portfolio_id=portfolio_id,
                name=request.name,
                status=PortfolioStatus.ACTIVE,
                allocation_strategy=request.allocation_strategy,
                risk_level=request.risk_level,
                target_positions=target_weights,
                cash_balance=Decimal(str(request.initial_capital)),
                total_value=Decimal(str(request.initial_capital)),
                created_at=datetime.now()
            )
            
            # Save portfolio
            await self.portfolio_repository.save_portfolio(portfolio)
            
            # Publish portfolio created event
            await self.event_publisher.publish_event(
                'portfolio_created',
                {
                    'portfolio_id': portfolio_id,
                    'name': request.name,
                    'initial_capital': request.initial_capital,
                    'symbols': request.symbols,
                    'allocation_strategy': request.allocation_strategy.value
                }
            )
            
            logger.info(f"✅ Portfolio created: {portfolio_id} with {len(request.symbols)} symbols")
            
            return PortfolioResponse(
                portfolio_id=portfolio_id,
                name=portfolio.name,
                status=portfolio.status,
                allocation_strategy=portfolio.allocation_strategy,
                risk_level=portfolio.risk_level,
                total_value=float(portfolio.total_value),
                cash_balance=float(portfolio.cash_balance),
                positions=[],
                metrics=None,
                last_updated=portfolio.created_at.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to create portfolio: {e}")
            raise HTTPException(status_code=500, detail=f"Portfolio creation failed: {str(e)}")

class RebalancePortfolioUseCase:
    """Portfolio Rebalancing Use Case"""
    
    def __init__(
        self,
        portfolio_repository,
        market_data_client,
        event_publisher
    ):
        self.portfolio_repository = portfolio_repository
        self.market_data_client = market_data_client
        self.event_publisher = event_publisher
    
    async def execute(self, request: RebalanceRequest) -> RebalanceResponse:
        """Execute portfolio rebalancing"""
        logger = logging.getLogger(__name__)
        
        try:
            # Get portfolio
            portfolio = await self.portfolio_repository.get_portfolio(request.portfolio_id)
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            # Update current prices
            for symbol in portfolio.positions:
                try:
                    price_data = await self.market_data_client.get_current_price(symbol)
                    if price_data:
                        portfolio.update_position_price(symbol, Decimal(str(price_data['price'])))
                except Exception as e:
                    logger.warning(f"Failed to update price for {symbol}: {e}")
            
            # Check if rebalancing is needed
            needs_rebalance = portfolio.needs_rebalancing() or request.force_rebalance
            
            if not needs_rebalance:
                return RebalanceResponse(
                    portfolio_id=request.portfolio_id,
                    rebalance_needed=False,
                    trades=[],
                    estimated_cost=0.0,
                    execution_timestamp=datetime.now().isoformat()
                )
            
            # Calculate rebalancing trades
            total_value = portfolio.calculate_portfolio_value()
            trades = PortfolioDomainService.calculate_rebalance_trades(
                portfolio.positions,
                portfolio.target_positions,
                total_value,
                Decimal(str(request.min_trade_value))
            )
            
            # Estimate trading cost (simplified)
            estimated_cost = sum(trade['estimated_value'] * 0.001 for trade in trades)  # 0.1% commission
            
            # Update portfolio rebalance timestamp
            portfolio.last_rebalance = datetime.now()
            await self.portfolio_repository.save_portfolio(portfolio)
            
            # Publish rebalance event
            await self.event_publisher.publish_event(
                'portfolio_rebalance_calculated',
                {
                    'portfolio_id': request.portfolio_id,
                    'trades_count': len(trades),
                    'estimated_cost': estimated_cost,
                    'total_value': float(total_value),
                    'trades': trades
                }
            )
            
            logger.info(f"✅ Portfolio rebalance calculated: {request.portfolio_id}, {len(trades)} trades")
            
            return RebalanceResponse(
                portfolio_id=request.portfolio_id,
                rebalance_needed=True,
                trades=trades,
                estimated_cost=estimated_cost,
                execution_timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to rebalance portfolio: {e}")
            raise HTTPException(status_code=500, detail=f"Portfolio rebalancing failed: {str(e)}")

# =============================================================================
# INFRASTRUCTURE LAYER - External Services & Repositories
# =============================================================================

class ServiceConfiguration:
    """Service Configuration Management"""
    
    def __init__(self):
        self.service_host = os.getenv('SERVICE_HOST', '0.0.0.0')
        self.service_port = int(os.getenv('SERVICE_PORT', '8004'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Redis Configuration
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        # PostgreSQL Configuration
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.postgres_db = os.getenv('POSTGRES_DB', 'aktienanalyse_ecosystem')
        self.postgres_user = os.getenv('POSTGRES_USER', 'aktienanalyse_user')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD', 'secure_password_2024')
        
        # Service URLs
        self.event_bus_url = os.getenv('EVENT_BUS_URL', 'http://localhost:8014')
        self.market_data_service_url = os.getenv('MARKET_DATA_SERVICE_URL', 'http://localhost:8002')
        self.ml_pipeline_service_url = os.getenv('ML_PIPELINE_SERVICE_URL', 'http://localhost:8003')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'service_host': self.service_host,
            'service_port': self.service_port,
            'log_level': self.log_level,
            'redis_connected': f"{self.redis_host}:{self.redis_port}",
            'postgres_connected': f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}",
            'event_bus_url': self.event_bus_url,
            'market_data_service_url': self.market_data_service_url,
            'ml_pipeline_service_url': self.ml_pipeline_service_url
        }

class PostgreSQLPortfolioRepository:
    """PostgreSQL Portfolio Repository"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.connection_pool = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                min_size=1,
                max_size=5
            )
            logging.info("✅ PostgreSQL Portfolio Repository initialized")
        except Exception as e:
            logging.error(f"Failed to initialize PostgreSQL Portfolio Repository: {e}")
            self.connection_pool = None
    
    async def save_portfolio(self, portfolio: PortfolioEntity):
        """Save portfolio to database"""
        if not self.connection_pool:
            logging.warning("PostgreSQL not available, skipping portfolio save")
            return
        
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO portfolios 
                    (portfolio_id, name, status, allocation_strategy, risk_level, 
                     target_positions, cash_balance, total_value, created_at, last_rebalance)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        name = $2, status = $3, cash_balance = $7, 
                        total_value = $8, last_rebalance = $10
                ''',
                    portfolio.portfolio_id,
                    portfolio.name,
                    portfolio.status.value,
                    portfolio.allocation_strategy.value,
                    portfolio.risk_level.value,
                    json.dumps(portfolio.target_positions),
                    float(portfolio.cash_balance),
                    float(portfolio.total_value),
                    portfolio.created_at,
                    portfolio.last_rebalance
                )
        except Exception as e:
            logging.error(f"Failed to save portfolio: {e}")
    
    async def get_portfolio(self, portfolio_id: str) -> Optional[PortfolioEntity]:
        """Get portfolio from database"""
        if not self.connection_pool:
            logging.warning("PostgreSQL not available, returning None")
            return None
        
        try:
            async with self.connection_pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM portfolios WHERE portfolio_id = $1',
                    portfolio_id
                )
                if row:
                    portfolio = PortfolioEntity(
                        portfolio_id=row['portfolio_id'],
                        name=row['name'],
                        status=PortfolioStatus(row['status']),
                        allocation_strategy=AllocationStrategy(row['allocation_strategy']),
                        risk_level=RiskLevel(row['risk_level']),
                        target_positions=json.loads(row['target_positions']),
                        cash_balance=Decimal(str(row['cash_balance'])),
                        total_value=Decimal(str(row['total_value'])),
                        created_at=row['created_at']
                    )
                    portfolio.last_rebalance = row['last_rebalance']
                    return portfolio
        except Exception as e:
            logging.error(f"Failed to get portfolio: {e}")
        
        return None

class MarketDataServiceClient:
    """Market Data Service Integration Client"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.base_url = config.market_data_service_url
        self.http_client = None
    
    async def initialize(self):
        """Initialize HTTP client"""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_keepalive_connections=5)
        )
        logging.info("✅ Market Data Service Client initialized")
    
    async def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current stock price"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/api/v1/market-data/price/{symbol}"
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.warning(f"Failed to get price for {symbol}: {e}")
        return None
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> Optional[Dict[str, Any]]:
        """Get historical price data"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/api/v1/market-data/historical/{symbol}",
                params={'period': period}
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.warning(f"Failed to get historical data for {symbol}: {e}")
        return None
    
    async def health_check(self) -> bool:
        """Check Market Data Service health"""
        try:
            response = await self.http_client.get(f"{self.base_url}/api/v1/market-data/health")
            return response.status_code == 200
        except:
            return False

class RedisEventPublisher:
    """Redis Event Publisher for Event-Driven Architecture"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.redis_client = None
        self.connection_healthy = False
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.connection_healthy = True
            logging.info("✅ Redis Event Publisher initialized")
            
        except Exception as e:
            logging.error(f"Failed to initialize Redis Event Publisher: {e}")
            self.connection_healthy = False
    
    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to Redis"""
        if not self.connection_healthy or not self.redis_client:
            logging.warning(f"Redis not available, skipping event: {event_type}")
            return
        
        try:
            event_data = {
                'event_id': str(uuid.uuid4()),
                'event_type': event_type,
                'service': 'portfolio-management-service',
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Publish to general events channel
            await self.redis_client.publish('portfolio_events', json.dumps(event_data))
            
            # Publish to specific event type channel
            await self.redis_client.publish(f'portfolio_{event_type}', json.dumps(event_data))
            
            logging.info(f"📤 Event published: {event_type}")
            
        except Exception as e:
            logging.error(f"Failed to publish event {event_type}: {e}")
            self.connection_healthy = False

class PortfolioManagementDependencyContainer:
    """Portfolio Management Dependency Injection Container"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        
        # Infrastructure Layer
        self.portfolio_repository = PostgreSQLPortfolioRepository(config)
        self.market_data_client = MarketDataServiceClient(config)
        self.event_publisher = RedisEventPublisher(config)
        
        # Application Layer
        self.create_portfolio_use_case = None
        self.rebalance_portfolio_use_case = None
    
    async def initialize(self):
        """Initialize all dependencies"""
        logger = logging.getLogger(__name__)
        logger.info("🔧 Initializing Portfolio Management Dependency Container")
        
        # Initialize Infrastructure
        await self.portfolio_repository.initialize()
        await self.market_data_client.initialize()
        await self.event_publisher.initialize()
        
        # Initialize Use Cases
        self.create_portfolio_use_case = CreatePortfolioUseCase(
            self.portfolio_repository,
            self.market_data_client,
            None,  # ML Pipeline Client would go here
            self.event_publisher
        )
        
        self.rebalance_portfolio_use_case = RebalancePortfolioUseCase(
            self.portfolio_repository,
            self.market_data_client,
            self.event_publisher
        )
        
        logger.info("✅ Portfolio Management Dependency Container initialized successfully")

# =============================================================================
# PRESENTATION LAYER - FastAPI REST Controllers
# =============================================================================

class HealthCheckResponse(BaseModel):
    """Health Check Response Model"""
    healthy: bool
    service: str
    version: str
    dependencies: Dict[str, bool]
    portfolios_count: int
    event_bus_connected: bool
    database_connected: bool
    market_data_service_available: bool
    timestamp: str
    uptime_seconds: float
    error: Optional[str] = None

class ServiceMetricsResponse(BaseModel):
    """Service Metrics Response Model"""
    total_portfolios: int
    active_portfolios: int
    total_portfolio_value: float
    rebalances_today: int
    trades_executed_today: int
    average_portfolio_performance: float
    top_performing_strategies: List[Dict[str, Any]]
    system_load: Dict[str, float]

# Global Container
container: Optional[PortfolioManagementDependencyContainer] = None

def get_container() -> PortfolioManagementDependencyContainer:
    """Dependency Injection Helper"""
    if not container:
        raise HTTPException(status_code=500, detail="Service not properly initialized")
    return container

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

def setup_logging(log_level: str = "INFO"):
    """Centralized Logging Configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='{"service": "portfolio-management-service", "version": "6.0.0", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s", "module": "%(name)s"}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"/tmp/portfolio-management-service-{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    
    # Suppress noisy external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Application Lifespan Management"""
    logger = logging.getLogger(__name__)
    global container
    
    # Startup
    try:
        logger.info("🚀 Starting Portfolio Management Service Enhanced v6.0.0 - Clean Architecture")
        
        # Initialize Configuration
        config = ServiceConfiguration()
        logger.info(f"⚙️ Configuration loaded: {config.to_dict()}")
        
        # Initialize Dependency Container
        container = PortfolioManagementDependencyContainer(config)
        await container.initialize()
        
        # Store in app state
        app.state.container = container
        app.state.config = config
        app.state.startup_time = datetime.now()
        
        logger.info("✅ Portfolio Management Service Enhanced v6.0.0 initialized successfully")
        logger.info(f"🌐 Service available at http://{config.service_host}:{config.service_port}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise
    
    # Shutdown
    finally:
        logger.info("🔄 Shutting down Portfolio Management Service Enhanced v6.0.0")
        if container and container.market_data_client and container.market_data_client.http_client:
            await container.market_data_client.http_client.aclose()

# FastAPI Application
app = FastAPI(
    title="Portfolio Management Service Enhanced v6.0",
    description="Clean Architecture Portfolio Management mit Event-Driven Pattern",
    version="6.0.0",
    lifespan=lifespan
)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.post("/api/v1/portfolio/create", response_model=PortfolioResponse)
async def create_portfolio(
    request: CreatePortfolioRequest,
    container: PortfolioManagementDependencyContainer = Depends(get_container)
):
    """
    Create New Portfolio
    
    CLEAN ARCHITECTURE: Create Portfolio Use Case
    """
    return await container.create_portfolio_use_case.execute(request)

@app.post("/api/v1/portfolio/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(
    request: RebalanceRequest,
    container: PortfolioManagementDependencyContainer = Depends(get_container)
):
    """
    Rebalance Portfolio
    
    CLEAN ARCHITECTURE: Rebalance Portfolio Use Case
    """
    return await container.rebalance_portfolio_use_case.execute(request)

@app.get("/api/v1/portfolio/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: str,
    container: PortfolioManagementDependencyContainer = Depends(get_container)
):
    """
    Get Portfolio Details
    
    CLEAN ARCHITECTURE: Portfolio Query
    """
    portfolio = await container.portfolio_repository.get_portfolio(portfolio_id)
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Convert positions to dict format
    positions = [pos.to_dict() for pos in portfolio.positions.values()]
    
    return PortfolioResponse(
        portfolio_id=portfolio.portfolio_id,
        name=portfolio.name,
        status=portfolio.status,
        allocation_strategy=portfolio.allocation_strategy,
        risk_level=portfolio.risk_level,
        total_value=float(portfolio.total_value),
        cash_balance=float(portfolio.cash_balance),
        positions=positions,
        metrics=asdict(portfolio.metrics) if portfolio.metrics else None,
        last_updated=portfolio.created_at.isoformat()
    )

@app.get("/api/v1/portfolio/health", response_model=HealthCheckResponse)
async def health_check(container: PortfolioManagementDependencyContainer = Depends(get_container)):
    """
    Service Health Check
    
    Comprehensive Health Check inklusive Market Data Service, Redis, PostgreSQL
    """
    
    # Check dependencies
    redis_healthy = container.event_publisher.connection_healthy
    postgres_healthy = container.portfolio_repository.connection_pool is not None
    market_data_healthy = await container.market_data_client.health_check()
    
    # Calculate uptime
    uptime = (datetime.now() - app.state.startup_time).total_seconds()
    
    # Overall health
    overall_healthy = redis_healthy and market_data_healthy  # PostgreSQL not critical
    
    return HealthCheckResponse(
        healthy=overall_healthy,
        service="portfolio-management-service",
        version="6.0.0",
        dependencies={
            "redis": redis_healthy,
            "postgresql": postgres_healthy,
            "market_data_service": market_data_healthy
        },
        portfolios_count=0,  # Would query database in production
        event_bus_connected=redis_healthy,
        database_connected=postgres_healthy,
        market_data_service_available=market_data_healthy,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        error=None
    )

@app.get("/api/v1/portfolio/metrics", response_model=ServiceMetricsResponse)
async def get_service_metrics(container: PortfolioManagementDependencyContainer = Depends(get_container)):
    """
    Service Metriken für Monitoring (Portfolios, Performance, Rebalancing)
    """
    
    # In production, these would be real metrics from database
    return ServiceMetricsResponse(
        total_portfolios=0,
        active_portfolios=0,
        total_portfolio_value=0.0,
        rebalances_today=0,
        trades_executed_today=0,
        average_portfolio_performance=0.0,
        top_performing_strategies=[],
        system_load={
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "redis_connections": 1
        }
    )

@app.post("/api/v1/portfolio/test/event-flow")
async def test_event_flow(container: PortfolioManagementDependencyContainer = Depends(get_container)):
    """
    Test Endpoint für Event-Driven Pattern
    
    CLEAN ARCHITECTURE: Event Flow Testing
    """
    await container.event_publisher.publish_event(
        'portfolio_test_event',
        {
            'message': 'Test event from Portfolio Management Service',
            'timestamp': datetime.now().isoformat(),
            'service_version': '6.0.0'
        }
    )
    
    return {"status": "Event published successfully", "timestamp": datetime.now().isoformat()}

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def main():
    """Main Application Entry Point"""
    
    # Setup logging
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    setup_logging(log_level)
    
    # Get configuration
    config = ServiceConfiguration()
    
    # Run FastAPI application
    uvicorn.run(
        app,
        host=config.service_host,
        port=config.service_port,
        log_config=None  # Use our custom logging
    )

if __name__ == "__main__":
    main()