#!/usr/bin/env python3
"""
LXC ML Analytics Service - Lightweight Service für LXC 10.1.1.174
===================================================================

Vereinfachte Version des ML Analytics Service optimiert für LXC Container
Fokus auf Classical-Enhanced ML ohne TensorFlow Dependencies

Features:
- Classical-Enhanced ML Engine (VCE, QIAOA, CENN)
- Memory-Efficient Portfolio Operations
- Real-time Market Intelligence
- LXC Performance Monitoring
- FastAPI REST Endpoints
- PostgreSQL/TimescaleDB Integration

Author: Claude Code & LXC Deployment Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import psutil

# FastAPI Dependencies
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Database Dependencies  
import asyncpg
from redis import Redis

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Local ML Modules (LXC-optimized)
from quantum_ml_engine_v1_0_0_20250819 import ClassicalEnhancedMLEngine
from market_intelligence_engine_v1_0_0_20250819 import MarketIntelligenceEngine
from lxc_performance_monitor_v1_0_0_20250819 import LXCPerformanceMonitor
from memory_efficient_portfolio_operations_v1_0_0_20250819 import MemoryEfficientPortfolioOperations, PortfolioConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic Models für API
class PortfolioOptimizationRequest(BaseModel):
    expected_returns: List[float]
    covariance_matrix: List[List[float]]
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)

class QIAOAOptimizationRequest(BaseModel):
    cost_matrix: List[List[float]]
    num_layers: int = Field(default=3, ge=1, le=10)

class NeuralNetworkTrainingRequest(BaseModel):
    model_name: str
    training_data: List[List[float]]
    training_labels: List[List[float]]
    num_epochs: int = Field(default=50, ge=1, le=200)
    learning_rate: float = Field(default=0.01, gt=0.0, le=1.0)

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    container_ip: str
    uptime_seconds: float

class LXCMLAnalyticsService:
    """
    LXC-optimized ML Analytics Service für Container 10.1.1.174
    Lightweight version ohne TensorFlow dependencies
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="LXC ML Analytics Service",
            description="Classical-Enhanced ML Service für LXC 10.1.1.174",
            version="1.0.0"
        )
        
        # LXC Configuration
        self.container_ip = "10.1.1.174"
        self.start_time = datetime.utcnow()
        
        # Database connections
        self.database_pool = None
        self.redis_client = None
        
        # ML Engines
        self.classical_enhanced_engine = None
        self.market_intelligence_engine = None
        self.performance_monitor = None
        self.portfolio_operations = None
        
        # Setup CORS für LXC
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Relaxed für private LXC
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"LXC ML Analytics Service initialized für {self.container_ip}")
    
    def _setup_routes(self):
        """Setup FastAPI routes optimiert für LXC"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Initialize services on startup"""
            await self._initialize_services()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Cleanup on shutdown"""
            await self._cleanup_services()
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint für LXC monitoring"""
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            return HealthResponse(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                container_ip=self.container_ip,
                uptime_seconds=uptime
            )
        
        @self.app.get("/api/v1/classical-enhanced/status")
        async def get_classical_enhanced_status():
            """Get Classical-Enhanced Engine status für LXC"""
            try:
                if not self.classical_enhanced_engine:
                    raise HTTPException(status_code=503, detail="Classical-Enhanced Engine not available")
                
                # Get performance summary
                perf_summary = self.performance_monitor.get_performance_summary(hours=1)
                
                return {
                    "engine_status": {
                        "status": "operational",
                        "container_optimization": "lxc-optimized",
                        "num_enhanced_models": 3,  # VCE, QIAOA, CENN
                        "num_enhanced_transformers": 1,
                        "num_algorithm_templates": 5
                    },
                    "lxc_performance": perf_summary,
                    "container_ip": self.container_ip,
                    "optimization_level": "LXC-Enhanced"
                }
            except Exception as e:
                logger.error(f"Error getting classical-enhanced status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/classical-enhanced/vce/portfolio-optimization")
        async def vce_portfolio_optimization(request: PortfolioOptimizationRequest):
            """VCE Portfolio Optimization für LXC"""
            try:
                if not self.classical_enhanced_engine:
                    raise HTTPException(status_code=503, detail="Classical-Enhanced Engine not available")
                
                # Use memory-efficient portfolio operations for large portfolios
                if len(request.expected_returns) > 20:
                    logger.info("Using memory-efficient operations for large portfolio")
                    
                    import numpy as np
                    expected_returns = np.array(request.expected_returns)
                    
                    # Generate synthetic return data für covariance calculation
                    n_assets = len(expected_returns)
                    returns_data = np.random.multivariate_normal(
                        mean=expected_returns * 0.01,  # Daily returns
                        cov=np.array(request.covariance_matrix) * 0.01,
                        size=252  # One year of trading days
                    )
                    
                    result = self.portfolio_operations.optimize_large_portfolio(
                        expected_returns=expected_returns,
                        return_covariance_data=returns_data,
                        risk_tolerance=request.risk_tolerance
                    )
                    
                    opt_result = result['portfolio_optimization']
                    lxc_perf = result['lxc_performance']
                    
                    return {
                        "optimal_energy": -opt_result['portfolio_return'],  # VCE minimizes
                        "portfolio_weights": opt_result['optimal_weights'].tolist(),
                        "classical_advantage": opt_result['sharpe_ratio'] / 2.0,  # Normalized
                        "num_iterations": opt_result['num_iterations'],
                        "risk_metrics": {
                            "portfolio_return": opt_result['portfolio_return'],
                            "portfolio_risk": opt_result['portfolio_risk'],
                            "sharpe_ratio": opt_result['sharpe_ratio']
                        },
                        "lxc_performance_metrics": {
                            "memory_usage_mb": opt_result['memory_usage_mb'],
                            "lxc_optimized": lxc_perf['within_lxc_limits'],
                            "computation_time_ms": 0  # Calculated in memory ops
                        }
                    }
                else:
                    # Use classical-enhanced engine for smaller portfolios
                    result = await self.classical_enhanced_engine.vce_portfolio_optimization(
                        expected_returns=request.expected_returns,
                        covariance_matrix=request.covariance_matrix,
                        risk_tolerance=request.risk_tolerance
                    )
                    return result
                    
            except Exception as e:
                logger.error(f"VCE Portfolio optimization error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/classical-enhanced/qiaoa/optimization")  
        async def qiaoa_optimization(request: QIAOAOptimizationRequest):
            """QIAOA Optimization für LXC"""
            try:
                if not self.classical_enhanced_engine:
                    raise HTTPException(status_code=503, detail="Classical-Enhanced Engine not available")
                
                result = await self.classical_enhanced_engine.qiaoa_optimization(
                    cost_matrix=request.cost_matrix,
                    num_layers=request.num_layers
                )
                return result
                
            except Exception as e:
                logger.error(f"QIAOA optimization error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/classical-enhanced/neural-network/train")
        async def neural_network_training(request: NeuralNetworkTrainingRequest):
            """Classical-Enhanced Neural Network Training für LXC"""
            try:
                if not self.classical_enhanced_engine:
                    raise HTTPException(status_code=503, detail="Classical-Enhanced Engine not available")
                
                result = await self.classical_enhanced_engine.train_classical_enhanced_neural_network(
                    model_name=request.model_name,
                    training_data=request.training_data,
                    training_labels=request.training_labels,
                    num_epochs=request.num_epochs,
                    learning_rate=request.learning_rate
                )
                return result
                
            except Exception as e:
                logger.error(f"Neural network training error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/lxc/performance/summary")
        async def get_lxc_performance_summary():
            """Get LXC performance summary"""
            try:
                if not self.performance_monitor:
                    raise HTTPException(status_code=503, detail="Performance Monitor not available")
                
                summary = self.performance_monitor.get_performance_summary(hours=2)
                return summary
                
            except Exception as e:
                logger.error(f"Performance summary error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _initialize_services(self):
        """Initialize all ML services für LXC"""
        try:
            logger.info("Initializing LXC ML Analytics Services...")
            
            # Initialize performance monitor
            self.performance_monitor = LXCPerformanceMonitor(self.container_ip)
            await self.performance_monitor.start_monitoring(interval_seconds=10)
            logger.info("✅ LXC Performance Monitor started")
            
            # Initialize memory-efficient portfolio operations
            config = PortfolioConfig(
                max_assets=100,
                batch_size=25,
                memory_limit_mb=800.0,  # Conservative for LXC
                use_sparse_matrices=True,
                use_memory_mapping=True
            )
            self.portfolio_operations = MemoryEfficientPortfolioOperations(config)
            logger.info("✅ Memory-Efficient Portfolio Operations initialized")
            
            # Try to initialize database connections (optional für LXC)
            try:
                # PostgreSQL connection
                DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/aktienanalyse')
                self.database_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
                logger.info("✅ Database pool created")
                
                # Redis connection
                REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
                self.redis_client = Redis.from_url(REDIS_URL)
                logger.info("✅ Redis connection established")
                
            except Exception as db_error:
                logger.warning(f"Database connections failed (running in standalone mode): {str(db_error)}")
            
            # Initialize Classical-Enhanced ML Engine
            self.classical_enhanced_engine = ClassicalEnhancedMLEngine(self.database_pool)
            await self.classical_enhanced_engine.initialize()
            logger.info("✅ Classical-Enhanced ML Engine initialized")
            
            # Initialize Market Intelligence Engine (if database available)
            if self.database_pool:
                self.market_intelligence_engine = MarketIntelligenceEngine(
                    self.database_pool, self.redis_client
                )
                await self.market_intelligence_engine.initialize()
                logger.info("✅ Market Intelligence Engine initialized")
            
            logger.info("🚀 LXC ML Analytics Service fully initialized!")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise
    
    async def _cleanup_services(self):
        """Cleanup services on shutdown"""
        logger.info("Shutting down LXC ML Analytics Service...")
        
        try:
            if self.performance_monitor:
                await self.performance_monitor.stop_monitoring()
            
            if self.portfolio_operations:
                del self.portfolio_operations
            
            if self.database_pool:
                await self.database_pool.close()
            
            if self.redis_client:
                self.redis_client.close()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8021):
        """Run the LXC ML Analytics Service"""
        logger.info(f"🚀 Starting LXC ML Analytics Service on {host}:{port}")
        logger.info(f"🔧 Optimized for LXC Container {self.container_ip}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            loop="asyncio"
        )

def main():
    """Main function für LXC deployment"""
    print("🔧 LXC ML Analytics Service Starting...")
    print(f"🔧 Optimized for Container 10.1.1.174")
    print("=" * 60)
    
    service = LXCMLAnalyticsService()
    service.run(host="0.0.0.0", port=8021)

if __name__ == "__main__":
    main()