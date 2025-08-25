#!/usr/bin/env python3
"""
ML Analytics Service Orchestrator v1.0.0
Hauptorchestrator für alle ML-Operationen im aktienanalyse-ökosystem

NEUE FEATURES v1.0.0 - 18. August 2025:
- Model Version Manager mit Semantic Versioning
- Automated Retraining Scheduler mit Performance Monitoring
- Multi-Horizon Training mit Synthetic Data
- Investment-Strategy Ensemble Analysis
- Vollständige Phase 6 Implementierung

Integration: Event-Driven Architecture (Port 8021)
Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import logging
import signal
import sys
import traceback
import numpy as np
import asyncpg
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Import configuration
from config.ml_service_config import ML_SERVICE_CONFIG

# Import ML modules
from basic_features_v1_0_0_20250818 import BasicFeatureEngine
from simple_lstm_model_v1_0_0_20250818 import SimpleLSTMModel
from multi_horizon_lstm_model_v1_0_0_20250818 import MultiHorizonLSTMModel
from multi_horizon_ensemble_v1_0_0_20250818 import MultiHorizonEnsembleManager
from synthetic_multi_horizon_trainer_v1_0_0_20250818 import SyntheticMultiHorizonTrainer
from sentiment_features_v1_0_0_20250818 import SentimentFeatureEngine
from sentiment_xgboost_model_v1_0_0_20250818 import SentimentXGBoostModel
from fundamental_features_v1_0_0_20250818 import FundamentalFeatureEngine
from fundamental_xgboost_model_v1_0_0_20250818 import FundamentalXGBoostModel

# Phase 13 Import - Advanced Risk Management Engine
from risk_management_engine_v1_0_0_20250819 import AdvancedRiskEngine, RiskMeasure, VaRMethod, StressTestType

# Phase 14 Import - ESG Analytics und Sustainable Finance Engine
from esg_analytics_engine_v1_0_0_20250819 import ESGAnalyticsEngine, ESGCategory, ESGRatingAgency, SustainabilityMetric, ClimateRiskType

# Phase 15 Import - Real-Time Market Intelligence und Event-Driven Analytics Engine
from market_intelligence_engine_v1_0_0_20250819 import MarketIntelligenceEngine, EventType, EventPriority, MarketRegime

# Phase 16 Import - Classical-Enhanced ML Models für LXC 10.1.1.174
from quantum_ml_engine_v1_0_0_20250819 import ClassicalEnhancedMLEngine, ClassicalAlgorithmType, ModelArchitectureType, VCEResult, QIAOAResult
from lxc_performance_monitor_v1_0_0_20250819 import LXCPerformanceMonitor
from meta_lightgbm_model_v1_0_0_20250818 import MetaLightGBMModel
from model_version_manager_v1_0_0_20250818 import ModelVersionManager
from automated_retraining_scheduler_v1_0_0_20250818 import AutomatedRetrainingScheduler
from realtime_streaming_analytics_v1_0_0_20250818 import RealTimeStreamingAnalytics
from portfolio_risk_manager_v1_0_0_20250818 import PortfolioRiskManager
from advanced_portfolio_optimizer_v1_0_0_20250818 import AdvancedPortfolioOptimizer, OptimizationMethod, InvestorView, ViewConfidence
from multi_asset_correlation_engine_v1_0_0_20250818 import MultiAssetCorrelationEngine, AssetClass, Sector, MarketRegime
from global_portfolio_optimizer_v1_0_0_20250818 import GlobalPortfolioOptimizer, AllocationStrategy, CurrencyHedgeStrategy, RiskBudget
from market_microstructure_engine_v1_0_0_20250818 import MarketMicrostructureEngine
from ai_options_pricing_engine_v1_0_0_20250818 import AIOptionsOraclingEngine, OptionType, VolatilityModel, PricingMethod
from exotic_derivatives_engine_v1_0_0_20250819 import ExoticDerivativesEngine, ExoticType, BarrierType, AsianType, LookbackType, SimulationMethod
from ml_event_publisher_v1_0_0_20250818 import ml_event_publisher

# Setup simple logging
logging.basicConfig(
    level=logging.INFO,
    format='{"service": "ml-analytics", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
)
logger = logging.getLogger("ml-analytics")


class MLAnalyticsService:
    """
    ML Analytics Service Orchestrator v1.0.0 - Phase 6 Enhanced
    Verwaltet alle ML-Operationen mit automatischem Retraining und Versioning
    """
    
    def __init__(self):
        self.service_name = "ml-analytics"
        self.service_port = ML_SERVICE_CONFIG['service']['port']
        
        # Infrastructure
        self.database_pool = None
        self.feature_engine = None
        self.sentiment_engine = None
        self.fundamental_engine = None
        self.lstm_model = None
        self.sentiment_model = None
        self.fundamental_model = None
        self.meta_model = None
        self.multi_horizon_models = {}  # Dict für verschiedene Horizonte
        
        # Phase 6: Version Management und Automated Retraining
        self.version_manager = None
        self.retraining_scheduler = None
        self.multi_horizon_ensemble = None
        self.synthetic_trainer = None
        
        # Phase 7: Real-time Streaming Analytics
        self.streaming_analytics = None
        
        # Phase 8: Advanced Portfolio Risk Management
        self.portfolio_risk_manager = None
        self.portfolio_optimizer = None
        
        # Phase 9: Multi-Asset Cross-Correlation and Global Portfolio Optimization
        self.multi_asset_correlation_engine = None
        self.global_portfolio_optimizer = None
        
        # Phase 10: Advanced Market Microstructure and High-Frequency Trading Analytics
        self.market_microstructure_engine = None
        
        # Phase 11: AI-Enhanced Options Pricing and Volatility Surface Modeling
        self.ai_options_pricing_engine = None
        
        # Phase 12: Advanced Derivatives Pricing and Exotic Options Engine
        self.exotic_derivatives_engine = None
        
        # Phase 13: Advanced Risk Management und Real-Time Portfolio Analytics
        self.advanced_risk_engine = None
        
        # Phase 14: ESG Analytics und Sustainable Finance Integration
        self.esg_analytics_engine = None
        
        # Phase 15: Real-Time Market Intelligence und Event-Driven Analytics
        self.market_intelligence_engine = None
        
        # Phase 16: Quantum Computing ML Models und Advanced Neural Networks
        self.quantum_ml_engine = None
        
        self.app = None
        
        # Service State
        self.is_healthy = False
        self.startup_time = None
        self.shutdown_requested = False
        
    async def initialize_components(self):
        """Initialisiert alle Service-Komponenten inklusive Phase 6 Features"""
        try:
            logger.info("Initializing ML Analytics Service v1.0.0 with Phase 6 features...")
            
            # Database Connection Pool
            await self._initialize_database()
            
            # Initialize Feature Engines
            self.feature_engine = BasicFeatureEngine(self.database_pool)
            logger.info("Technical Feature Engine initialized")
            
            self.sentiment_engine = SentimentFeatureEngine(self.database_pool)
            logger.info("Sentiment Feature Engine initialized")
            
            self.fundamental_engine = FundamentalFeatureEngine(self.database_pool)
            logger.info("Fundamental Feature Engine initialized")
            
            # Initialize ML Models
            model_storage_path = ML_SERVICE_CONFIG['storage']['model_storage_path']
            
            self.lstm_model = SimpleLSTMModel(self.database_pool, model_storage_path)
            logger.info("LSTM Model initialized")
            
            self.sentiment_model = SentimentXGBoostModel(self.database_pool, model_storage_path)
            logger.info("Sentiment XGBoost Model initialized")
            
            self.fundamental_model = FundamentalXGBoostModel(self.database_pool, model_storage_path)
            logger.info("Fundamental XGBoost Model initialized")
            
            self.meta_model = MetaLightGBMModel(self.database_pool, model_storage_path)
            logger.info("Meta LightGBM Model initialized")
            
            # Initialize Multi-Horizon LSTM Models
            supported_horizons = [7, 30, 150, 365]
            for horizon in supported_horizons:
                self.multi_horizon_models[horizon] = MultiHorizonLSTMModel(
                    self.database_pool, model_storage_path, horizon
                )
            logger.info(f"Multi-Horizon LSTM Models initialized for horizons: {supported_horizons}")
            
            # Initialize Multi-Horizon Ensemble Manager
            self.multi_horizon_ensemble = MultiHorizonEnsembleManager(self.database_pool)
            logger.info("Multi-Horizon Ensemble Manager initialized")
            
            # Initialize Synthetic Multi-Horizon Trainer
            self.synthetic_trainer = SyntheticMultiHorizonTrainer(self.database_pool, model_storage_path)
            logger.info("Synthetic Multi-Horizon Trainer initialized")
            
            # Phase 6: Initialize Model Version Manager
            self.version_manager = ModelVersionManager(self.database_pool, model_storage_path)
            await self.version_manager.initialize()
            logger.info("Model Version Manager initialized with semantic versioning")
            
            # Phase 6: Initialize Automated Retraining Scheduler
            self.retraining_scheduler = AutomatedRetrainingScheduler(self.database_pool, self)
            await self.retraining_scheduler.initialize()
            logger.info("Automated Retraining Scheduler initialized")
            
            # Phase 7: Initialize Real-time Streaming Analytics
            self.streaming_analytics = RealTimeStreamingAnalytics(self.database_pool, self)
            await self.streaming_analytics.initialize()
            logger.info("Real-time Streaming Analytics initialized")
            
            # Phase 8: Initialize Portfolio Risk Management
            self.portfolio_risk_manager = PortfolioRiskManager(self.database_pool)
            await self.portfolio_risk_manager.initialize()
            logger.info("Portfolio Risk Manager initialized")
            
            # Phase 9: Initialize Multi-Asset Cross-Correlation Engine
            self.multi_asset_correlation_engine = MultiAssetCorrelationEngine(self.database_pool)
            await self.multi_asset_correlation_engine.initialize()
            logger.info("Multi-Asset Cross-Correlation Engine initialized")
            
            # Phase 9: Initialize Global Portfolio Optimizer
            self.global_portfolio_optimizer = GlobalPortfolioOptimizer(self.multi_asset_correlation_engine)
            logger.info("Global Portfolio Optimizer initialized")
            
            # Phase 10: Initialize Market Microstructure Engine
            self.market_microstructure_engine = MarketMicrostructureEngine(self.database_pool)
            await self.market_microstructure_engine.initialize()
            logger.info("Market Microstructure Engine initialized")
            
            # Phase 11: Initialize AI Options Pricing Engine
            self.ai_options_pricing_engine = AIOptionsOraclingEngine(self.database_pool)
            await self.ai_options_pricing_engine.initialize()
            logger.info("AI Options Pricing Engine initialized")
            
            # Phase 12: Initialize Exotic Derivatives Engine
            self.exotic_derivatives_engine = ExoticDerivativesEngine(self.database_pool)
            await self.exotic_derivatives_engine.initialize()
            logger.info("Exotic Derivatives Engine initialized")
            
            # Phase 13: Initialize Advanced Risk Management Engine
            self.advanced_risk_engine = AdvancedRiskEngine(self.database_pool)
            await self.advanced_risk_engine.initialize()
            logger.info("Advanced Risk Management Engine initialized")
            
            # Phase 14: Initialize ESG Analytics Engine
            self.esg_analytics_engine = ESGAnalyticsEngine(self.database_pool)
            await self.esg_analytics_engine.initialize()
            logger.info("ESG Analytics Engine initialized")
            
            # Phase 15: Initialize Market Intelligence Engine
            self.market_intelligence_engine = MarketIntelligenceEngine(self.database_pool)
            await self.market_intelligence_engine.initialize()
            logger.info("Market Intelligence Engine initialized")
            
            # Phase 16: Initialize Quantum ML Engine
            self.classical_enhanced_engine = ClassicalEnhancedMLEngine(self.database_pool)
            self.lxc_performance_monitor = LXCPerformanceMonitor("10.1.1.174")
            await self.classical_enhanced_engine.initialize()
            await self.lxc_performance_monitor.start_monitoring(interval_seconds=30)
            logger.info("Classical-Enhanced ML Engine und LXC Performance Monitor initialized")
            
            # Initialize ML Event Publisher
            await ml_event_publisher.initialize()
            logger.info("ML Event Publisher initialized")
            
            logger.info("ML Analytics Service v1.0.0 components initialized successfully - Phase 16 Active!")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def start_automated_retraining(self):
        """Startet den automatischen Retraining Scheduler"""
        try:
            if self.retraining_scheduler:
                await self.retraining_scheduler.start_scheduler()
                logger.info("Automated retraining scheduler started successfully")
            else:
                logger.warning("Retraining scheduler not initialized")
        except Exception as e:
            logger.error(f"Failed to start automated retraining: {str(e)}")
    
    async def stop_automated_retraining(self):
        """Stoppt den automatischen Retraining Scheduler"""
        try:
            if self.retraining_scheduler:
                await self.retraining_scheduler.stop_scheduler()
                logger.info("Automated retraining scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop automated retraining: {str(e)}")
    
    async def start_streaming_analytics(self):
        """Startet Real-time Streaming Analytics"""
        try:
            if self.streaming_analytics:
                await self.streaming_analytics.start_websocket_server()
                logger.info("Real-time streaming analytics started successfully")
            else:
                logger.warning("Streaming analytics not initialized")
        except Exception as e:
            logger.error(f"Failed to start streaming analytics: {str(e)}")
    
    async def stop_streaming_analytics(self):
        """Stoppt Real-time Streaming Analytics"""
        try:
            if self.streaming_analytics:
                await self.streaming_analytics.stop_websocket_server()
                logger.info("Real-time streaming analytics stopped")
        except Exception as e:
            logger.error(f"Failed to stop streaming analytics: {str(e)}")
    
    async def get_ml_predictions_for_optimization(self) -> Dict[str, float]:
        """Get ML model predictions for portfolio optimization"""
        try:
            predictions = {}
            
            # Get predictions from multi-horizon ensemble
            if self.multi_horizon_ensemble:
                for symbol in ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN', 'META', 'NVDA', 'NFLX']:
                    try:
                        # Get 30-day prediction
                        prediction = await self.multi_horizon_ensemble.generate_ensemble_prediction(
                            symbol, 30, use_meta_model=True
                        )
                        predictions[symbol] = prediction.get('final_prediction', 0.1)
                    except:
                        predictions[symbol] = 0.1  # Default 10% return
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to get ML predictions: {str(e)}")
            return {'AAPL': 0.1, 'MSFT': 0.08, 'GOOGL': 0.12}  # Default predictions
    
    async def _initialize_database(self):
        """Initialisiert PostgreSQL Database Pool"""
        try:
            db_config = ML_SERVICE_CONFIG['database']
            # SECURITY FIX: Use asyncpg.create_pool with separate parameters to avoid password logging
            connection_params = {
                "host": db_config['host'],
                "port": db_config['port'],
                "database": db_config['name'],
                "user": db_config['user'],
                "password": db_config['password']
            }
            
            self.database_pool = await asyncpg.create_pool(
                **connection_params,
                min_size=db_config.get('min_connections', 5),
                max_size=db_config.get('max_connections', 20),
                command_timeout=60,
                server_settings={
                    'application_name': 'ml-analytics-v1.0.0',
                    'jit': 'off'
                }
            )
            
            # Test connection and check ML schema
            async with self.database_pool.acquire() as conn:
                await conn.execute('SELECT 1')
                
                # Check ML tables
                ml_tables = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'ml_%'"
                )
                
                logger.info(f"Database connection established - {ml_tables} ML tables found")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def setup_event_handlers(self):
        """Konfiguriert Event-Handler für ML-Events"""
        try:
            # For now, just log that event handlers would be set up
            logger.info("Event handlers setup (placeholder)")
            
        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            raise
    
    def _calculate_recommendation_strength(self, predictions: Dict[str, Any]) -> str:
        """Berechnet Empfehlungsstärke basierend auf ML-Predictions (placeholder)"""
        return "NEUTRAL"
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive Health Check mit Phase 6 Status"""
        try:
            # Component Status
            component_status = {
                'database': bool(self.database_pool),
                'feature_engine': bool(self.feature_engine),
                'lstm_model': bool(self.lstm_model),
                'sentiment_model': bool(self.sentiment_model),
                'fundamental_model': bool(self.fundamental_model),
                'meta_model': bool(self.meta_model),
                'multi_horizon_models': len(self.multi_horizon_models),
                'multi_horizon_ensemble': bool(self.multi_horizon_ensemble),
                'synthetic_trainer': bool(self.synthetic_trainer),
                'version_manager': bool(self.version_manager),
                'retraining_scheduler': bool(self.retraining_scheduler),
                'streaming_analytics': bool(self.streaming_analytics),
                'multi_asset_correlation_engine': bool(self.multi_asset_correlation_engine),
                'global_portfolio_optimizer': bool(self.global_portfolio_optimizer),
                'market_microstructure_engine': bool(self.market_microstructure_engine),
                'ai_options_pricing_engine': bool(self.ai_options_pricing_engine),
                'exotic_derivatives_engine': bool(self.exotic_derivatives_engine),
                'advanced_risk_engine': bool(self.advanced_risk_engine),
                'esg_analytics_engine': bool(self.esg_analytics_engine)
            }
            
            # Version Manager Status
            versioning_status = {}
            if self.version_manager:
                versioning_status = await self.version_manager.get_versioning_status()
            
            # Retraining Scheduler Status
            scheduler_status = {}
            if self.retraining_scheduler:
                scheduler_status = await self.retraining_scheduler.get_scheduler_status()
            
            # Streaming Analytics Status
            streaming_status = {}
            if self.streaming_analytics:
                streaming_status = await self.streaming_analytics.get_streaming_status()
            
            # Portfolio Risk Management Status
            portfolio_risk_status = {}
            if self.portfolio_risk_manager:
                portfolio_risk_status = await self.portfolio_risk_manager.get_risk_manager_status()
            
            # Multi-Asset Engine Status
            multi_asset_status = {}
            if self.multi_asset_correlation_engine:
                multi_asset_status = await self.multi_asset_correlation_engine.get_multi_asset_status()
            
            # Market Microstructure Engine Status
            microstructure_status = {}
            if self.market_microstructure_engine:
                microstructure_status = await self.market_microstructure_engine.get_microstructure_status()
            
            # AI Options Pricing Engine Status
            options_pricing_status = {}
            if self.ai_options_pricing_engine:
                options_pricing_status = {
                    'initialized': True,
                    'supported_models': ['black_scholes', 'heston', 'sabr', 'neural_network'],
                    'pricing_methods': ['analytical', 'monte_carlo', 'ai_enhanced'],
                    'options_chains_loaded': len(self.ai_options_pricing_engine.options_chains),
                    'volatility_surfaces': len(self.ai_options_pricing_engine.volatility_surfaces)
                }
            
            # Exotic Derivatives Engine Status
            exotic_derivatives_status = {}
            if self.exotic_derivatives_engine:
                exotic_derivatives_status = await self.exotic_derivatives_engine.get_pricing_engine_status()
            
            health_status = {
                'service': 'ml-analytics',
                'version': '1.0.0',
                'phase': 'Phase 12 - Advanced Derivatives Pricing and Exotic Options Engine',
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds() if self.startup_time else 0,
                'components': component_status,
                'versioning_system': versioning_status,
                'retraining_scheduler': scheduler_status,
                'streaming_analytics': streaming_status,
                'portfolio_risk_management': portfolio_risk_status,
                'multi_asset_engine': multi_asset_status,
                'market_microstructure_engine': microstructure_status,
                'ai_options_pricing_engine': options_pricing_status,
                'exotic_derivatives_engine': exotic_derivatives_status,
                'advanced_risk_engine': await self.advanced_risk_engine.get_risk_engine_status() if self.advanced_risk_engine else {},
                'esg_analytics_engine': await self.esg_analytics_engine.get_esg_engine_status() if self.esg_analytics_engine else {}
            }
            
            # Database connectivity test
            if self.database_pool:
                try:
                    async with self.database_pool.acquire() as conn:
                        await conn.execute('SELECT 1')
                        health_status['database_connected'] = True
                except Exception as e:
                    health_status['database_connected'] = False
                    health_status['database_error'] = str(e)
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'service': 'ml-analytics',
                'version': '1.0.0',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def shutdown(self):
        """Graceful Shutdown mit Phase 6 Cleanup"""
        try:
            logger.info("ML Analytics Service shutdown initiated...")
            self.shutdown_requested = True
            
            # Stop automated retraining
            await self.stop_automated_retraining()
            
            # Close ML Event Publisher
            if ml_event_publisher.redis_client:
                await ml_event_publisher.shutdown()
                logger.info("ML Event Publisher shut down")
            
            # Close database pool
            if self.database_pool:
                await self.database_pool.close()
                logger.info("Database pool closed")
            
            logger.info("ML Analytics Service shut down completed")
            
        except Exception as e:
            logger.error(f"Shutdown error: {str(e)}")


# Global service instance
ml_service = MLAnalyticsService()


# FastAPI Lifecycle Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application Lifecycle Manager"""
    try:
        # Startup
        logger.info("Starting ML Analytics Service v1.0.0...")
        ml_service.startup_time = datetime.utcnow()
        
        await ml_service.initialize_components()
        await ml_service.setup_event_handlers()
        
        # Start automated retraining
        await ml_service.start_automated_retraining()
        
        ml_service.is_healthy = True
        logger.info("ML Analytics Service v1.0.0 started successfully - Phase 10 Active")
        
        yield
        
        # Shutdown
        logger.info("Shutting down ML Analytics Service...")
        ml_service.is_healthy = False
        await ml_service.shutdown()
        
    except Exception as e:
        logger.error(f"Lifecycle management error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


# Initialize FastAPI app
app = FastAPI(
    title="ML Analytics Service",
    version="1.0.0",
    description="Phase 10: Advanced Market Microstructure and High-Frequency Trading Analytics",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ml_service.app = app


# ===================== HEALTH & STATUS ENDPOINTS =====================

@app.get("/health")
async def health_check():
    """Service Health Check"""
    return await ml_service.health_check()

@app.get("/api/v1/schema/info")
async def get_ml_schema_info():
    """Get ML database schema information"""
    try:
        if not ml_service.database_pool:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        async with ml_service.database_pool.acquire() as conn:
            # Get ML tables
            ml_tables = await conn.fetch("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_name LIKE 'ml_%' OR table_name LIKE '%model%' OR table_name LIKE '%version%' OR table_name LIKE '%retrain%'
                ORDER BY table_name
            """)
            
            # Get schema version
            try:
                schema_version = await conn.fetchrow(
                    "SELECT version, deployed_at FROM ml_schema_version ORDER BY deployed_at DESC LIMIT 1"
                )
            except:
                schema_version = None
            
            return {
                "ml_tables": [dict(row) for row in ml_tables],
                "tables_count": len(ml_tables),
                "schema_version": dict(schema_version) if schema_version else None,
                "database_connected": True
            }
            
    except Exception as e:
        logger.error(f"Failed to get ML schema info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/models/status")
async def get_models_status():
    """Get ML models status"""
    try:
        if not ml_service.database_pool:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        async with ml_service.database_pool.acquire() as conn:
            # Get model registry info
            models = await conn.fetch("""
                SELECT model_id, model_type, model_version, horizon_days, status, 
                       file_path, performance_metrics, created_at
                FROM ml_model_metadata
                WHERE status = 'active'
                ORDER BY model_type, horizon_days
            """)
            
            return {
                "active_models": [dict(row) for row in models],
                "models_count": len(models),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get models status: {str(e)}")
        # Return empty result if table doesn't exist yet
        return {
            "active_models": [],
            "models_count": 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# ===================== PHASE 6: VERSION MANAGEMENT ENDPOINTS =====================

@app.get("/api/v1/versions/status")
async def get_versioning_status():
    """Get version management system status"""
    try:
        if not ml_service.version_manager:
            raise HTTPException(status_code=503, detail="Version manager not initialized")
        
        return await ml_service.version_manager.get_versioning_status()
        
    except Exception as e:
        logger.error(f"Failed to get versioning status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/versions/history/{model_type}")
async def get_version_history(model_type: str, limit: int = 20):
    """Get version history for a model type"""
    try:
        if not ml_service.version_manager:
            raise HTTPException(status_code=503, detail="Version manager not initialized")
        
        history = await ml_service.version_manager.get_version_history(model_type, limit)
        return {
            "model_type": model_type,
            "versions": history,
            "count": len(history),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get version history for {model_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/versions/rollback/{model_type}/{version}")
async def rollback_model_version(model_type: str, version: str):
    """Rollback a model to specific version"""
    try:
        if not ml_service.version_manager:
            raise HTTPException(status_code=503, detail="Version manager not initialized")
        
        rollback_plan = await ml_service.version_manager.rollback_to_version(model_type, version)
        return {
            "model_type": model_type,
            "target_version": version,
            "rollback_plan": rollback_plan.__dict__,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to rollback {model_type} to {version}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/versions/compare/{model_type}/{version1}/{version2}")
async def compare_model_versions(model_type: str, version1: str, version2: str):
    """Compare performance between two model versions"""
    try:
        if not ml_service.version_manager:
            raise HTTPException(status_code=503, detail="Version manager not initialized")
        
        comparison = await ml_service.version_manager.get_performance_comparison(model_type, version1, version2)
        return comparison
        
    except Exception as e:
        logger.error(f"Failed to compare versions {version1} vs {version2} for {model_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 6: AUTOMATED RETRAINING ENDPOINTS =====================

@app.get("/api/v1/retraining/status")
async def get_retraining_status():
    """Get automated retraining scheduler status"""
    try:
        if not ml_service.retraining_scheduler:
            raise HTTPException(status_code=503, detail="Retraining scheduler not initialized")
        
        return await ml_service.retraining_scheduler.get_scheduler_status()
        
    except Exception as e:
        logger.error(f"Failed to get retraining status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/retraining/schedule/{model_type}")
async def schedule_manual_retraining(model_type: str, symbol: str = "AAPL", priority: int = 1):
    """Schedule manual retraining job"""
    try:
        if not ml_service.retraining_scheduler:
            raise HTTPException(status_code=503, detail="Retraining scheduler not initialized")
        
        from automated_retraining_scheduler_v1_0_0_20250818 import RetrainingTrigger
        
        job_id = await ml_service.retraining_scheduler.schedule_retraining_job(
            model_type, RetrainingTrigger.MANUAL, symbol, priority
        )
        
        return {
            "job_id": job_id,
            "model_type": model_type,
            "symbol": symbol,
            "trigger": "manual",
            "priority": priority,
            "scheduled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule retraining for {model_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/retraining/history")
async def get_retraining_history(limit: int = 50):
    """Get retraining job history"""
    try:
        if not ml_service.retraining_scheduler:
            raise HTTPException(status_code=503, detail="Retraining scheduler not initialized")
        
        history = await ml_service.retraining_scheduler.get_retraining_history(limit)
        return {
            "retraining_jobs": history,
            "count": len(history),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get retraining history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/retraining/start")
async def start_retraining_scheduler():
    """Start automated retraining scheduler"""
    try:
        await ml_service.start_automated_retraining()
        return {"message": "Automated retraining scheduler started", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to start retraining scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/retraining/stop")
async def stop_retraining_scheduler():
    """Stop automated retraining scheduler"""
    try:
        await ml_service.stop_automated_retraining()
        return {"message": "Automated retraining scheduler stopped", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to stop retraining scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 7: STREAMING ANALYTICS ENDPOINTS =====================

@app.get("/api/v1/streaming/status")
async def get_streaming_status():
    """Get real-time streaming analytics status"""
    try:
        if not ml_service.streaming_analytics:
            raise HTTPException(status_code=503, detail="Streaming analytics not initialized")
        
        return await ml_service.streaming_analytics.get_streaming_status()
        
    except Exception as e:
        logger.error(f"Failed to get streaming status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/streaming/start")
async def start_streaming_server():
    """Start WebSocket streaming server"""
    try:
        await ml_service.start_streaming_analytics()
        return {"message": "Streaming analytics started", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to start streaming server: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/streaming/stop")
async def stop_streaming_server():
    """Stop WebSocket streaming server"""
    try:
        await ml_service.stop_streaming_analytics()
        return {"message": "Streaming analytics stopped", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to stop streaming server: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/streaming/clients")
async def get_connected_clients():
    """Get connected WebSocket clients info"""
    try:
        if not ml_service.streaming_analytics:
            raise HTTPException(status_code=503, detail="Streaming analytics not initialized")
        
        return {
            "connected_clients": len(ml_service.streaming_analytics.connected_clients),
            "websocket_port": ml_service.streaming_analytics.streaming_config.get("websocket_port", 8022),
            "tracked_symbols": ml_service.streaming_analytics.tracked_symbols,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get client info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/streaming/signals/recent")
async def get_recent_signals(limit: int = 20):
    """Get recent trading signals"""
    try:
        if not ml_service.streaming_analytics:
            raise HTTPException(status_code=503, detail="Streaming analytics not initialized")
        
        recent_signals = ml_service.streaming_analytics.recent_signals[-limit:]
        
        # Convert signals to serializable format
        signals_data = []
        for signal in recent_signals:
            signal_dict = {
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "confidence": signal.confidence,
                "price": signal.price,
                "target_price": signal.target_price,
                "stop_loss": signal.stop_loss,
                "horizon_days": signal.horizon_days,
                "model_source": signal.model_source,
                "timestamp": signal.timestamp.isoformat(),
                "metadata": signal.metadata
            }
            signals_data.append(signal_dict)
        
        return {
            "recent_signals": signals_data,
            "count": len(signals_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 8: PORTFOLIO RISK MANAGEMENT ENDPOINTS =====================

@app.get("/api/v1/portfolio/risk-metrics")
async def get_portfolio_risk_metrics():
    """Get comprehensive portfolio risk metrics"""
    try:
        if not ml_service.portfolio_risk_manager:
            raise HTTPException(status_code=503, detail="Portfolio Risk Manager not initialized")
        
        # Get current portfolio weights
        current_weights = {k: v['weight'] for k, v in ml_service.portfolio_risk_manager.current_portfolio.items()}
        
        risk_metrics = await ml_service.portfolio_risk_manager.calculate_risk_metrics(current_weights)
        
        return {
            "portfolio_weights": current_weights,
            "risk_metrics": {
                "var_95": risk_metrics.var_95,
                "var_99": risk_metrics.var_99,
                "expected_shortfall_95": risk_metrics.expected_shortfall_95,
                "expected_shortfall_99": risk_metrics.expected_shortfall_99,
                "sharpe_ratio": risk_metrics.sharpe_ratio,
                "sortino_ratio": risk_metrics.sortino_ratio,
                "max_drawdown": risk_metrics.max_drawdown,
                "volatility": risk_metrics.volatility,
                "beta": risk_metrics.beta,
                "tracking_error": risk_metrics.tracking_error,
                "information_ratio": risk_metrics.information_ratio,
                "calmar_ratio": risk_metrics.calmar_ratio
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get portfolio risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portfolio/optimize/{method}")
async def optimize_portfolio(method: str, custom_weights: Optional[Dict[str, float]] = None):
    """Optimize portfolio using specified method"""
    try:
        if not ml_service.portfolio_risk_manager:
            raise HTTPException(status_code=503, detail="Portfolio Risk Manager not initialized")
        
        # Initialize portfolio optimizer if needed
        if not ml_service.portfolio_optimizer:
            ml_service.portfolio_optimizer = AdvancedPortfolioOptimizer(
                ml_service.portfolio_risk_manager.returns_data
            )
        
        optimization_method = OptimizationMethod(method.lower())
        
        if optimization_method == OptimizationMethod.BLACK_LITTERMAN:
            # Get ML predictions for views
            ml_predictions = await ml_service.get_ml_predictions_for_optimization()
            ml_views = await ml_service.portfolio_optimizer.create_ml_investor_views(ml_predictions)
            result = await ml_service.portfolio_optimizer.optimize_black_litterman(ml_views)
            
            return {
                "optimization_method": method,
                "optimal_weights": result.optimal_weights,
                "expected_return": result.expected_return,
                "expected_volatility": result.expected_volatility,
                "sharpe_ratio": result.sharpe_ratio,
                "views_incorporated": result.views_incorporated,
                "optimization_success": result.optimization_success,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        elif optimization_method == OptimizationMethod.RISK_PARITY:
            result = await ml_service.portfolio_optimizer.optimize_risk_parity()
            
            return {
                "optimization_method": method,
                "optimal_weights": result.optimal_weights,
                "risk_contributions": result.risk_contributions,
                "risk_concentration": result.risk_concentration,
                "expected_return": result.expected_return,
                "volatility": result.volatility,
                "diversification_ratio": result.diversification_ratio,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        elif optimization_method == OptimizationMethod.MAX_DIVERSIFICATION:
            optimal_weights = await ml_service.portfolio_optimizer.optimize_maximum_diversification()
            
            return {
                "optimization_method": method,
                "optimal_weights": optimal_weights,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        elif optimization_method == OptimizationMethod.HIERARCHICAL_RISK_PARITY:
            result = await ml_service.portfolio_optimizer.optimize_hierarchical_risk_parity()
            
            return {
                "optimization_method": method,
                "optimal_weights": result.optimal_weights,
                "expected_return": result.expected_return,
                "expected_volatility": result.expected_volatility,
                "clustering_info": result.clustering_tree,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported optimization method: {method}")
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Portfolio optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portfolio/stress-test")
async def perform_stress_testing():
    """Perform comprehensive stress testing on current portfolio"""
    try:
        if not ml_service.portfolio_risk_manager:
            raise HTTPException(status_code=503, detail="Portfolio Risk Manager not initialized")
        
        # Get current portfolio weights
        current_weights = {k: v['weight'] for k, v in ml_service.portfolio_risk_manager.current_portfolio.items()}
        
        stress_results = await ml_service.portfolio_risk_manager.perform_stress_testing(current_weights)
        
        stress_data = []
        for result in stress_results:
            stress_data.append({
                "scenario_name": result.scenario_name,
                "portfolio_loss": result.portfolio_loss,
                "worst_case_var": result.worst_case_var,
                "probability": result.probability,
                "affected_positions": result.affected_positions,
                "risk_contribution": result.risk_contribution
            })
        
        return {
            "portfolio_weights": current_weights,
            "stress_scenarios": stress_data,
            "total_scenarios": len(stress_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stress testing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/portfolio/correlation-analysis")
async def get_correlation_analysis():
    """Get asset correlation analysis and market dependency"""
    try:
        if not ml_service.portfolio_risk_manager:
            raise HTTPException(status_code=503, detail="Portfolio Risk Manager not initialized")
        
        correlation_matrix = ml_service.portfolio_risk_manager.correlation_matrix
        if correlation_matrix is None:
            raise HTTPException(status_code=503, detail="Correlation matrix not available")
        
        # Convert to serializable format
        correlation_data = correlation_matrix.to_dict()
        
        # Calculate portfolio diversification metrics
        current_weights = {k: v['weight'] for k, v in ml_service.portfolio_risk_manager.current_portfolio.items()}
        
        return {
            "correlation_matrix": correlation_data,
            "portfolio_weights": current_weights,
            "average_correlation": correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean(),
            "max_correlation": correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].max(),
            "min_correlation": correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].min(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Correlation analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 9: MULTI-ASSET CROSS-CORRELATION ENDPOINTS =====================

@app.get("/api/v1/multi-asset/status")
async def get_multi_asset_status():
    """Get Multi-Asset Cross-Correlation Engine status"""
    try:
        if not ml_service.multi_asset_correlation_engine:
            raise HTTPException(status_code=503, detail="Multi-Asset Engine not initialized")
        
        return await ml_service.multi_asset_correlation_engine.get_multi_asset_status()
        
    except Exception as e:
        logger.error(f"Failed to get multi-asset status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/multi-asset/correlations")
async def get_cross_asset_correlations():
    """Get cross-asset correlation analysis"""
    try:
        if not ml_service.multi_asset_correlation_engine:
            raise HTTPException(status_code=503, detail="Multi-Asset Engine not initialized")
        
        correlations = await ml_service.multi_asset_correlation_engine.analyze_cross_asset_correlations()
        
        # Convert to serializable format
        correlation_data = []
        for corr in correlations:
            correlation_data.append({
                "asset_pair": corr.asset_pair,
                "correlation": corr.correlation,
                "correlation_stability": corr.correlation_stability,
                "statistical_significance": corr.statistical_significance,
                "time_period": corr.time_period,
                "regime_dependent_correlations": corr.regime_dependent_correlations
            })
        
        return {
            "cross_asset_correlations": correlation_data,
            "total_pairs": len(correlation_data),
            "current_market_regime": ml_service.multi_asset_correlation_engine.current_regime.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cross-asset correlations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/multi-asset/sectors")
async def get_sector_analysis():
    """Get sector-based asset correlation analysis"""
    try:
        if not ml_service.multi_asset_correlation_engine:
            raise HTTPException(status_code=503, detail="Multi-Asset Engine not initialized")
        
        sector_analysis = await ml_service.multi_asset_correlation_engine.analyze_sector_correlations()
        
        # Convert to serializable format
        sectors_data = {}
        for sector, analysis in sector_analysis.items():
            sectors_data[sector.value] = {
                "assets": analysis.assets,
                "asset_count": len(analysis.assets),
                "sector_correlation": analysis.sector_correlation,
                "intra_sector_correlation": analysis.intra_sector_correlation,
                "sector_volatility": analysis.sector_volatility,
                "sector_momentum": analysis.sector_momentum,
                "sector_relative_strength": analysis.sector_relative_strength
            }
        
        return {
            "sector_analysis": sectors_data,
            "sectors_analyzed": len(sectors_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get sector analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/multi-asset/signals")
async def get_cross_asset_signals():
    """Get cross-asset trading signals"""
    try:
        if not ml_service.multi_asset_correlation_engine:
            raise HTTPException(status_code=503, detail="Multi-Asset Engine not initialized")
        
        signals = await ml_service.multi_asset_correlation_engine.generate_cross_asset_signals()
        
        # Convert to serializable format
        signals_data = []
        for signal in signals:
            signals_data.append({
                "primary_asset": signal.primary_asset,
                "signal_type": signal.signal_type,
                "signal_strength": signal.signal_strength,
                "supporting_assets": signal.supporting_assets,
                "cross_asset_confirmation": signal.cross_asset_confirmation,
                "regime_context": signal.regime_context.value,
                "confidence_level": signal.confidence_level,
                "timestamp": signal.timestamp.isoformat()
            })
        
        return {
            "cross_asset_signals": signals_data,
            "signals_count": len(signals_data),
            "market_regime": ml_service.multi_asset_correlation_engine.current_regime.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cross-asset signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/multi-asset/risk-contagion")
async def get_risk_contagion_analysis():
    """Get risk contagion analysis across assets"""
    try:
        if not ml_service.multi_asset_correlation_engine:
            raise HTTPException(status_code=503, detail="Multi-Asset Engine not initialized")
        
        contagion_analysis = await ml_service.multi_asset_correlation_engine.analyze_risk_contagion()
        
        # Convert to serializable format
        contagion_data = []
        for contagion in contagion_analysis:
            contagion_data.append({
                "source_asset": contagion.source_asset,
                "affected_assets": contagion.affected_assets,
                "affected_count": len(contagion.affected_assets),
                "contagion_coefficient": contagion.contagion_coefficient,
                "time_to_contagion": contagion.time_to_contagion,
                "probability": contagion.probability,
                "historical_occurrences": contagion.historical_occurrences
            })
        
        return {
            "risk_contagion_patterns": contagion_data,
            "patterns_detected": len(contagion_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get risk contagion analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 9: GLOBAL PORTFOLIO OPTIMIZATION ENDPOINTS =====================

@app.post("/api/v1/global-portfolio/optimize")
async def optimize_global_portfolio(
    strategy: str = "strategic",
    risk_budget: str = "moderate", 
    currency_hedge: str = "selective_hedge",
    esg_weight: float = 0.0
):
    """Optimize global multi-asset portfolio"""
    try:
        if not ml_service.global_portfolio_optimizer:
            raise HTTPException(status_code=503, detail="Global Portfolio Optimizer not initialized")
        
        # Convert string parameters to enums
        allocation_strategy = AllocationStrategy(strategy.lower())
        risk_budget_enum = RiskBudget(risk_budget.lower())
        currency_hedge_enum = CurrencyHedgeStrategy(currency_hedge.lower())
        
        # Optimize portfolio
        allocation = await ml_service.global_portfolio_optimizer.optimize_global_portfolio(
            allocation_strategy, risk_budget_enum, currency_hedge_enum, esg_weight
        )
        
        return {
            "optimization_strategy": strategy,
            "risk_budget": risk_budget,
            "currency_hedge_strategy": currency_hedge,
            "esg_weight": esg_weight,
            "allocation": {
                "asset_weights": allocation.asset_weights,
                "asset_class_weights": {k.value: v for k, v in allocation.asset_class_weights.items()},
                "sector_weights": {k.value: v for k, v in allocation.sector_weights.items()},
                "geographic_weights": allocation.geographic_weights,
                "currency_exposure": allocation.currency_exposure,
                "expected_return": allocation.expected_return,
                "expected_volatility": allocation.expected_volatility,
                "sharpe_ratio": allocation.sharpe_ratio,
                "max_drawdown_estimate": allocation.max_drawdown_estimate,
                "var_95": allocation.var_95
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Global portfolio optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/global-portfolio/asset-universe")
async def get_asset_universe():
    """Get available asset universe for global optimization"""
    try:
        if not ml_service.multi_asset_correlation_engine:
            raise HTTPException(status_code=503, detail="Multi-Asset Engine not initialized")
        
        asset_universe = ml_service.multi_asset_correlation_engine.asset_universe
        
        # Convert to serializable format
        assets_data = {}
        for symbol, asset in asset_universe.items():
            assets_data[symbol] = {
                "name": asset.name,
                "asset_class": asset.asset_class.value,
                "sector": asset.sector.value if asset.sector else None,
                "currency": asset.currency,
                "exchange": asset.exchange,
                "market_cap": asset.market_cap,
                "country": asset.country,
                "is_active": asset.is_active
            }
        
        # Group by asset class
        asset_classes = {}
        for symbol, asset in asset_universe.items():
            asset_class = asset.asset_class.value
            if asset_class not in asset_classes:
                asset_classes[asset_class] = []
            asset_classes[asset_class].append(symbol)
        
        return {
            "asset_universe": assets_data,
            "total_assets": len(assets_data),
            "asset_classes": asset_classes,
            "supported_strategies": [strategy.value for strategy in AllocationStrategy],
            "supported_risk_budgets": [budget.value for budget in RiskBudget],
            "supported_currency_hedges": [hedge.value for hedge in CurrencyHedgeStrategy],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get asset universe: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 10: MARKET MICROSTRUCTURE ANALYTICS ENDPOINTS =====================

@app.get("/api/v1/microstructure/status")
async def get_microstructure_status():
    """Get Market Microstructure Engine status"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        return await ml_service.market_microstructure_engine.get_microstructure_status()
        
    except Exception as e:
        logger.error(f"Failed to get microstructure status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/microstructure/metrics/{symbol}")
async def get_microstructure_metrics(symbol: str):
    """Get comprehensive microstructure metrics for a symbol"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        metrics = await ml_service.market_microstructure_engine.calculate_microstructure_metrics(symbol)
        
        return {
            "symbol": symbol,
            "microstructure_metrics": {
                "bid_ask_spread": metrics.bid_ask_spread,
                "effective_spread": metrics.effective_spread,
                "realized_spread": metrics.realized_spread,
                "price_impact": metrics.price_impact,
                "adverse_selection_cost": metrics.adverse_selection_cost,
                "order_flow_imbalance": metrics.order_flow_imbalance,
                "trade_intensity": metrics.trade_intensity,
                "volatility_signature": metrics.volatility_signature,
                "roll_variance": metrics.roll_variance,
                "market_depth": metrics.market_depth,
                "resilience_metric": metrics.resilience_metric,
                "information_share": metrics.information_share
            },
            "timestamp": metrics.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get microstructure metrics for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/microstructure/liquidity/{symbol}")
async def get_liquidity_metrics(symbol: str):
    """Get liquidity metrics for a symbol"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        liquidity = await ml_service.market_microstructure_engine.calculate_liquidity_metrics(symbol)
        
        return {
            "symbol": symbol,
            "liquidity_metrics": {
                "bid_ask_spread_bps": liquidity.bid_ask_spread_bps,
                "quoted_spread_bps": liquidity.quoted_spread_bps,
                "effective_spread_bps": liquidity.effective_spread_bps,
                "market_depth_usd": liquidity.market_depth_usd,
                "turnover_ratio": liquidity.turnover_ratio,
                "price_impact_bps": liquidity.price_impact_bps,
                "amihud_illiquidity": liquidity.amihud_illiquidity,
                "kyle_lambda": liquidity.kyle_lambda,
                "roll_impact": liquidity.roll_impact,
                "hasbrouck_info_share": liquidity.hasbrouck_info_share
            },
            "timestamp": liquidity.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get liquidity metrics for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/microstructure/hft-patterns/{symbol}")
async def get_hft_patterns(symbol: str):
    """Detect high-frequency trading patterns for a symbol"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        patterns = await ml_service.market_microstructure_engine.detect_hft_patterns(symbol)
        
        # Convert to serializable format
        patterns_data = []
        for pattern in patterns:
            patterns_data.append({
                "pattern_type": pattern.pattern_type,
                "detection_timestamp": pattern.detection_timestamp.isoformat(),
                "duration_ms": pattern.duration_ms,
                "frequency": pattern.frequency,
                "amplitude": pattern.amplitude,
                "confidence_score": pattern.confidence_score,
                "affected_symbols": pattern.affected_symbols,
                "pattern_description": pattern.pattern_description
            })
        
        return {
            "symbol": symbol,
            "hft_patterns": patterns_data,
            "patterns_detected": len(patterns_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to detect HFT patterns for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/microstructure/transaction-costs/{symbol}")
async def get_transaction_costs(symbol: str):
    """Get transaction cost analysis for a symbol"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        tx_costs = await ml_service.market_microstructure_engine.analyze_transaction_costs(symbol)
        
        return {
            "symbol": symbol,
            "transaction_cost_analysis": tx_costs,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get transaction cost analysis for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/microstructure/order-book/{symbol}")
async def get_order_book(symbol: str):
    """Get current order book snapshot for a symbol"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        order_book = await ml_service.market_microstructure_engine.get_real_time_order_book(symbol)
        
        if not order_book:
            raise HTTPException(status_code=404, detail=f"No order book data available for {symbol}")
        
        # Convert OrderBookLevel objects to serializable format
        bids_data = []
        for bid in order_book.bids:
            bids_data.append({
                "price": bid.price,
                "quantity": bid.quantity,
                "orders_count": bid.orders_count,
                "timestamp": bid.timestamp.isoformat()
            })
        
        asks_data = []
        for ask in order_book.asks:
            asks_data.append({
                "price": ask.price,
                "quantity": ask.quantity,
                "orders_count": ask.orders_count,
                "timestamp": ask.timestamp.isoformat()
            })
        
        return {
            "symbol": symbol,
            "order_book": {
                "timestamp": order_book.timestamp.isoformat(),
                "bids": bids_data,
                "asks": asks_data,
                "spread": order_book.spread,
                "mid_price": order_book.mid_price,
                "total_bid_volume": order_book.total_bid_volume,
                "total_ask_volume": order_book.total_ask_volume,
                "imbalance_ratio": order_book.imbalance_ratio
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get order book for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/microstructure/symbols")
async def get_microstructure_symbols():
    """Get list of symbols with microstructure data"""
    try:
        if not ml_service.market_microstructure_engine:
            raise HTTPException(status_code=503, detail="Market Microstructure Engine not initialized")
        
        return {
            "tracked_symbols": list(ml_service.market_microstructure_engine.active_symbols),
            "symbols_count": len(ml_service.market_microstructure_engine.active_symbols),
            "max_history_length": ml_service.market_microstructure_engine.max_history_length,
            "microstructure_window": ml_service.market_microstructure_engine.microstructure_window,
            "hft_detection_window": ml_service.market_microstructure_engine.hft_detection_window,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get microstructure symbols: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 11: AI OPTIONS PRICING ANALYTICS ENDPOINTS =====================

@app.get("/api/v1/options/status")
async def get_options_pricing_status():
    """Get AI Options Pricing Engine status"""
    try:
        if not ml_service.ai_options_pricing_engine:
            raise HTTPException(status_code=503, detail="AI Options Pricing Engine not initialized")
        
        return {
            "initialized": True,
            "supported_volatility_models": ["black_scholes", "heston", "sabr", "neural_network", "stochastic_local_vol"],
            "pricing_methods": ["analytical", "monte_carlo", "binomial_tree", "finite_difference", "ai_enhanced"],
            "options_chains_loaded": len(ml_service.ai_options_pricing_engine.options_chains),
            "volatility_surfaces": len(ml_service.ai_options_pricing_engine.volatility_surfaces),
            "supported_strategies": ml_service.ai_options_pricing_engine.supported_strategies,
            "risk_free_rate": ml_service.ai_options_pricing_engine.risk_free_rate,
            "monte_carlo_paths": ml_service.ai_options_pricing_engine.monte_carlo_paths,
            "confidence_level": ml_service.ai_options_pricing_engine.confidence_level,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get options pricing status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/options/price/{symbol}")
async def calculate_option_price(
    symbol: str,
    option_type: str,
    strike: float,
    time_to_expiration: float,
    volatility_model: str = "neural_network",
    pricing_method: str = "ai_enhanced"
):
    """Calculate theoretical option price using AI-enhanced models"""
    try:
        if not ml_service.ai_options_pricing_engine:
            raise HTTPException(status_code=503, detail="AI Options Pricing Engine not initialized")
        
        # Convert string enums
        try:
            option_type_enum = OptionType(option_type.lower())
            volatility_model_enum = VolatilityModel(volatility_model.lower())
            pricing_method_enum = PricingMethod(pricing_method.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
        
        # Calculate option price
        pricing_result = await ml_service.ai_options_pricing_engine.calculate_option_price(
            underlying_symbol=symbol,
            option_type=option_type_enum,
            strike=strike,
            time_to_expiration=time_to_expiration,
            volatility_model=volatility_model_enum,
            pricing_method=pricing_method_enum
        )
        
        return {
            "symbol": symbol,
            "option_type": option_type,
            "strike": strike,
            "time_to_expiration": time_to_expiration,
            "pricing_result": {
                "theoretical_price": pricing_result.theoretical_price,
                "implied_volatility": pricing_result.implied_volatility,
                "greeks": {
                    "delta": pricing_result.delta,
                    "gamma": pricing_result.gamma,
                    "theta": pricing_result.theta,
                    "vega": pricing_result.vega,
                    "rho": pricing_result.rho
                },
                "pricing_method": pricing_result.pricing_method.value,
                "volatility_model": pricing_result.volatility_model.value,
                "confidence_interval": pricing_result.confidence_interval,
                "model_accuracy": pricing_result.model_accuracy,
                "last_updated": pricing_result.last_updated.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate option price for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/options/volatility-surface/{symbol}")
async def get_volatility_surface(symbol: str):
    """Get complete volatility surface for an underlying"""
    try:
        if not ml_service.ai_options_pricing_engine:
            raise HTTPException(status_code=503, detail="AI Options Pricing Engine not initialized")
        
        vol_surface = await ml_service.ai_options_pricing_engine.get_volatility_surface(symbol)
        
        # Convert surface points to serializable format
        surface_points = []
        for point in vol_surface.surface_points:
            surface_points.append({
                "strike": point.strike,
                "time_to_expiration": point.time_to_expiration,
                "implied_volatility": point.implied_volatility,
                "option_type": point.option_type.value,
                "confidence": point.confidence,
                "model_source": point.model_source
            })
        
        return {
            "underlying": symbol,
            "volatility_surface": {
                "surface_points": surface_points,
                "atm_volatility": vol_surface.atm_volatility,
                "volatility_skew": vol_surface.volatility_skew,
                "term_structure": vol_surface.term_structure,
                "surface_quality": vol_surface.surface_quality,
                "interpolation_method": vol_surface.interpolation_method,
                "last_updated": vol_surface.last_updated.isoformat()
            },
            "surface_statistics": {
                "total_points": len(surface_points),
                "time_ranges": {
                    "min_expiration": min(p["time_to_expiration"] for p in surface_points) if surface_points else 0,
                    "max_expiration": max(p["time_to_expiration"] for p in surface_points) if surface_points else 0
                },
                "strike_ranges": {
                    "min_strike": min(p["strike"] for p in surface_points) if surface_points else 0,
                    "max_strike": max(p["strike"] for p in surface_points) if surface_points else 0
                },
                "avg_implied_vol": sum(p["implied_volatility"] for p in surface_points) / len(surface_points) if surface_points else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get volatility surface for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/options/chain/{symbol}")
async def get_options_chain(symbol: str):
    """Get complete options chain for an underlying"""
    try:
        if not ml_service.ai_options_pricing_engine:
            raise HTTPException(status_code=503, detail="AI Options Pricing Engine not initialized")
        
        options_chain = await ml_service.ai_options_pricing_engine.get_options_chain(symbol)
        
        # Convert options contracts to serializable format
        options_data = []
        for contract in options_chain:
            options_data.append({
                "symbol": contract.symbol,
                "underlying": contract.underlying,
                "option_type": contract.option_type.value,
                "strike": contract.strike,
                "expiration": contract.expiration.isoformat(),
                "market_price": contract.market_price,
                "bid": contract.bid,
                "ask": contract.ask,
                "volume": contract.volume,
                "open_interest": contract.open_interest,
                "implied_volatility": contract.implied_volatility,
                "greeks": {
                    "delta": contract.delta,
                    "gamma": contract.gamma,
                    "theta": contract.theta,
                    "vega": contract.vega,
                    "rho": contract.rho
                }
            })
        
        # Group by expiration and option type
        chain_by_expiration = {}
        for option in options_data:
            exp_date = option["expiration"]
            if exp_date not in chain_by_expiration:
                chain_by_expiration[exp_date] = {"calls": [], "puts": []}
            
            if option["option_type"] == "call":
                chain_by_expiration[exp_date]["calls"].append(option)
            else:
                chain_by_expiration[exp_date]["puts"].append(option)
        
        return {
            "underlying": symbol,
            "options_chain": chain_by_expiration,
            "chain_statistics": {
                "total_contracts": len(options_data),
                "expiration_dates": list(chain_by_expiration.keys()),
                "calls_count": len([o for o in options_data if o["option_type"] == "call"]),
                "puts_count": len([o for o in options_data if o["option_type"] == "put"]),
                "total_volume": sum(o["volume"] for o in options_data),
                "total_open_interest": sum(o["open_interest"] for o in options_data),
                "avg_implied_vol": sum(o["implied_volatility"] for o in options_data) / len(options_data) if options_data else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get options chain for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/options/strategy/analyze")
async def analyze_options_strategy(strategy_data: dict):
    """Analyze options trading strategy performance and risk metrics"""
    try:
        if not ml_service.ai_options_pricing_engine:
            raise HTTPException(status_code=503, detail="AI Options Pricing Engine not initialized")
        
        # Validate strategy data structure
        required_fields = ["strategy_name", "legs"]
        for field in required_fields:
            if field not in strategy_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Analyze the strategy
        strategy_analysis = await ml_service.ai_options_pricing_engine.analyze_options_strategy(strategy_data)
        
        return {
            "strategy_analysis": {
                "strategy_name": strategy_analysis.strategy_name,
                "legs": strategy_analysis.legs,
                "net_premium": strategy_analysis.net_premium,
                "max_profit": strategy_analysis.max_profit,
                "max_loss": strategy_analysis.max_loss,
                "breakeven_points": strategy_analysis.breakeven_points,
                "probability_of_profit": strategy_analysis.probability_of_profit,
                "expected_return": strategy_analysis.expected_return,
                "strategy_greeks": strategy_analysis.strategy_greeks,
                "risk_reward_ratio": strategy_analysis.risk_reward_ratio
            },
            "risk_metrics": {
                "var_95": strategy_analysis.max_loss * 0.95,  # Simplified VaR
                "maximum_drawdown": abs(strategy_analysis.max_loss),
                "profit_probability": strategy_analysis.probability_of_profit,
                "time_decay_risk": strategy_analysis.strategy_greeks.get("theta", 0),
                "volatility_exposure": strategy_analysis.strategy_greeks.get("vega", 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze options strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/options/strategies/templates")
async def get_strategy_templates():
    """Get predefined options strategy templates"""
    try:
        return {
            "strategy_templates": [
                {
                    "name": "long_call",
                    "description": "Simple long call position",
                    "risk_profile": "Limited risk, unlimited profit potential",
                    "market_outlook": "Bullish"
                },
                {
                    "name": "long_put", 
                    "description": "Simple long put position",
                    "risk_profile": "Limited risk, high profit potential",
                    "market_outlook": "Bearish"
                },
                {
                    "name": "covered_call",
                    "description": "Long stock + short call",
                    "risk_profile": "Moderate risk, limited profit",
                    "market_outlook": "Neutral to slightly bullish"
                },
                {
                    "name": "protective_put",
                    "description": "Long stock + long put",
                    "risk_profile": "Limited downside risk",
                    "market_outlook": "Bullish with downside protection"
                },
                {
                    "name": "bull_call_spread",
                    "description": "Long call + short call (higher strike)",
                    "risk_profile": "Limited risk, limited profit",
                    "market_outlook": "Moderately bullish"
                },
                {
                    "name": "bear_put_spread",
                    "description": "Long put + short put (lower strike)",
                    "risk_profile": "Limited risk, limited profit",
                    "market_outlook": "Moderately bearish"
                },
                {
                    "name": "iron_condor",
                    "description": "Bull put spread + bear call spread",
                    "risk_profile": "Limited risk, limited profit",
                    "market_outlook": "Neutral (range-bound)"
                },
                {
                    "name": "straddle",
                    "description": "Long call + long put (same strike)",
                    "risk_profile": "Limited risk, unlimited profit potential",
                    "market_outlook": "High volatility expected"
                },
                {
                    "name": "strangle",
                    "description": "Long call + long put (different strikes)",
                    "risk_profile": "Limited risk, unlimited profit potential",
                    "market_outlook": "High volatility expected"
                },
                {
                    "name": "butterfly",
                    "description": "Complex spread with 3 strikes",
                    "risk_profile": "Limited risk, limited profit",
                    "market_outlook": "Low volatility expected"
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategy templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 12: EXOTIC DERIVATIVES PRICING ENDPOINTS =====================

@app.get("/api/v1/exotic/status")
async def get_exotic_derivatives_status():
    """Get Exotic Derivatives Engine status"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        return await ml_service.exotic_derivatives_engine.get_pricing_engine_status()
        
    except Exception as e:
        logger.error(f"Failed to get exotic derivatives status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/exotic/types")
async def get_supported_exotic_types():
    """Get list of supported exotic derivative types"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        return await ml_service.exotic_derivatives_engine.get_supported_exotic_types()
        
    except Exception as e:
        logger.error(f"Failed to get exotic types: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/exotic/price")
async def price_exotic_derivative(contract_data: dict):
    """Price exotic derivative using Monte Carlo simulation"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        # Validate required fields
        required_fields = ["contract_id", "exotic_type", "underlying_assets", "expiration_date"]
        for field in required_fields:
            if field not in contract_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Parse contract specification
        from exotic_derivatives_engine_v1_0_0_20250819 import ExoticContractSpec, UnderlyingAsset, ExoticType
        from datetime import datetime
        
        # Parse underlying assets
        underlying_assets = []
        for asset_data in contract_data["underlying_assets"]:
            asset = UnderlyingAsset(
                symbol=asset_data["symbol"],
                current_price=asset_data["current_price"],
                volatility=asset_data["volatility"],
                dividend_yield=asset_data.get("dividend_yield", 0.0),
                currency=asset_data.get("currency", "USD")
            )
            underlying_assets.append(asset)
        
        # Parse expiration date
        if isinstance(contract_data["expiration_date"], str):
            expiration_date = datetime.fromisoformat(contract_data["expiration_date"].replace('Z', '+00:00'))
        else:
            expiration_date = contract_data["expiration_date"]
        
        # Create contract specification
        contract = ExoticContractSpec(
            contract_id=contract_data["contract_id"],
            exotic_type=ExoticType(contract_data["exotic_type"]),
            underlying_assets=underlying_assets,
            expiration_date=expiration_date,
            strike=contract_data.get("strike"),
            barrier_level=contract_data.get("barrier_level"),
            payoff_currency=contract_data.get("payoff_currency", "USD"),
            notional=contract_data.get("notional", 1000000.0),
            digital_payout=contract_data.get("digital_payout"),
            basket_weights=contract_data.get("basket_weights")
        )
        
        # Parse simulation parameters if provided
        simulation_params = None
        if "simulation_parameters" in contract_data:
            from exotic_derivatives_engine_v1_0_0_20250819 import SimulationParameters, SimulationMethod
            sim_data = contract_data["simulation_parameters"]
            
            simulation_params = SimulationParameters(
                num_paths=sim_data.get("num_paths", 100000),
                num_time_steps=sim_data.get("num_time_steps", 252),
                simulation_method=SimulationMethod(sim_data.get("simulation_method", "standard_mc")),
                random_seed=sim_data.get("random_seed"),
                variance_reduction=sim_data.get("variance_reduction", True)
            )
        
        # Price the exotic derivative
        pricing_result = await ml_service.exotic_derivatives_engine.price_exotic_derivative(
            contract=contract,
            simulation_params=simulation_params,
            calculate_greeks=contract_data.get("calculate_greeks", True)
        )
        
        # Convert result to serializable format
        result_dict = {
            "contract_id": pricing_result.contract_id,
            "theoretical_price": pricing_result.theoretical_price,
            "price_currency": pricing_result.price_currency,
            "greeks": {
                "delta": pricing_result.delta,
                "gamma": pricing_result.gamma,
                "vega": pricing_result.vega,
                "theta": pricing_result.theta,
                "rho": pricing_result.rho
            },
            "confidence_interval": {
                "lower_bound": pricing_result.confidence_interval[0],
                "upper_bound": pricing_result.confidence_interval[1]
            },
            "standard_error": pricing_result.standard_error,
            "convergence_diagnostics": pricing_result.convergence_diagnostics,
            "pricing_method": pricing_result.pricing_method,
            "computation_time": pricing_result.computation_time,
            "last_updated": pricing_result.last_updated.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Failed to price exotic derivative: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/exotic/barrier")
async def price_barrier_option(barrier_data: dict):
    """Price barrier option with specific barrier parameters"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        # Validate barrier-specific fields
        required_fields = ["symbol", "current_price", "volatility", "strike", "barrier_level", "barrier_type", "expiration_date"]
        for field in required_fields:
            if field not in barrier_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        from exotic_derivatives_engine_v1_0_0_20250819 import ExoticContractSpec, UnderlyingAsset, ExoticType, BarrierType
        from datetime import datetime
        
        # Create underlying asset
        underlying = UnderlyingAsset(
            symbol=barrier_data["symbol"],
            current_price=barrier_data["current_price"],
            volatility=barrier_data["volatility"],
            dividend_yield=barrier_data.get("dividend_yield", 0.0),
            currency=barrier_data.get("currency", "USD")
        )
        
        # Parse expiration date
        if isinstance(barrier_data["expiration_date"], str):
            expiration_date = datetime.fromisoformat(barrier_data["expiration_date"].replace('Z', '+00:00'))
        else:
            expiration_date = barrier_data["expiration_date"]
        
        # Create barrier option contract
        contract = ExoticContractSpec(
            contract_id=f"BARRIER_{barrier_data['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            exotic_type=ExoticType.BARRIER_OPTION,
            underlying_assets=[underlying],
            expiration_date=expiration_date,
            strike=barrier_data["strike"],
            barrier_level=barrier_data["barrier_level"],
            barrier_type=BarrierType(barrier_data["barrier_type"]),
            payoff_currency=barrier_data.get("payoff_currency", "USD"),
            notional=barrier_data.get("notional", 1000000.0)
        )
        
        # Price the barrier option
        pricing_result = await ml_service.exotic_derivatives_engine.price_exotic_derivative(contract)
        
        return {
            "contract_id": pricing_result.contract_id,
            "barrier_type": barrier_data["barrier_type"],
            "barrier_level": barrier_data["barrier_level"],
            "theoretical_price": pricing_result.theoretical_price,
            "confidence_interval": pricing_result.confidence_interval,
            "computation_time": pricing_result.computation_time,
            "convergence_diagnostics": pricing_result.convergence_diagnostics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to price barrier option: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/exotic/asian")
async def price_asian_option(asian_data: dict):
    """Price Asian option with average price or strike"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        # Validate Asian-specific fields
        required_fields = ["symbol", "current_price", "volatility", "strike", "asian_type", "expiration_date"]
        for field in required_fields:
            if field not in asian_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        from exotic_derivatives_engine_v1_0_0_20250819 import ExoticContractSpec, UnderlyingAsset, ExoticType, AsianType
        from datetime import datetime
        
        # Create underlying asset
        underlying = UnderlyingAsset(
            symbol=asian_data["symbol"],
            current_price=asian_data["current_price"],
            volatility=asian_data["volatility"],
            dividend_yield=asian_data.get("dividend_yield", 0.0),
            currency=asian_data.get("currency", "USD")
        )
        
        # Parse expiration date
        if isinstance(asian_data["expiration_date"], str):
            expiration_date = datetime.fromisoformat(asian_data["expiration_date"].replace('Z', '+00:00'))
        else:
            expiration_date = asian_data["expiration_date"]
        
        # Create Asian option contract
        contract = ExoticContractSpec(
            contract_id=f"ASIAN_{asian_data['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            exotic_type=ExoticType.ASIAN_OPTION,
            underlying_assets=[underlying],
            expiration_date=expiration_date,
            strike=asian_data["strike"],
            asian_type=AsianType(asian_data["asian_type"]),
            payoff_currency=asian_data.get("payoff_currency", "USD"),
            notional=asian_data.get("notional", 1000000.0)
        )
        
        # Price the Asian option
        pricing_result = await ml_service.exotic_derivatives_engine.price_exotic_derivative(contract)
        
        return {
            "contract_id": pricing_result.contract_id,
            "asian_type": asian_data["asian_type"],
            "theoretical_price": pricing_result.theoretical_price,
            "confidence_interval": pricing_result.confidence_interval,
            "computation_time": pricing_result.computation_time,
            "convergence_diagnostics": pricing_result.convergence_diagnostics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to price Asian option: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/exotic/basket")
async def price_basket_option(basket_data: dict):
    """Price basket option on multiple underlying assets"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        # Validate basket-specific fields
        required_fields = ["underlying_assets", "strike", "expiration_date"]
        for field in required_fields:
            if field not in basket_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        if len(basket_data["underlying_assets"]) < 2:
            raise HTTPException(status_code=400, detail="Basket options require at least 2 underlying assets")
        
        from exotic_derivatives_engine_v1_0_0_20250819 import ExoticContractSpec, UnderlyingAsset, ExoticType
        from datetime import datetime
        
        # Create underlying assets
        underlying_assets = []
        for asset_data in basket_data["underlying_assets"]:
            asset = UnderlyingAsset(
                symbol=asset_data["symbol"],
                current_price=asset_data["current_price"],
                volatility=asset_data["volatility"],
                dividend_yield=asset_data.get("dividend_yield", 0.0),
                currency=asset_data.get("currency", "USD")
            )
            underlying_assets.append(asset)
        
        # Parse expiration date
        if isinstance(basket_data["expiration_date"], str):
            expiration_date = datetime.fromisoformat(basket_data["expiration_date"].replace('Z', '+00:00'))
        else:
            expiration_date = basket_data["expiration_date"]
        
        # Create basket option contract
        contract = ExoticContractSpec(
            contract_id=f"BASKET_{len(underlying_assets)}ASSETS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            exotic_type=ExoticType.BASKET_OPTION,
            underlying_assets=underlying_assets,
            expiration_date=expiration_date,
            strike=basket_data["strike"],
            basket_weights=basket_data.get("basket_weights"),
            payoff_currency=basket_data.get("payoff_currency", "USD"),
            notional=basket_data.get("notional", 1000000.0)
        )
        
        # Price the basket option
        pricing_result = await ml_service.exotic_derivatives_engine.price_exotic_derivative(contract)
        
        return {
            "contract_id": pricing_result.contract_id,
            "num_assets": len(underlying_assets),
            "basket_weights": basket_data.get("basket_weights", "equal_weighted"),
            "theoretical_price": pricing_result.theoretical_price,
            "confidence_interval": pricing_result.confidence_interval,
            "greeks": pricing_result.delta,  # Delta per asset
            "computation_time": pricing_result.computation_time,
            "convergence_diagnostics": pricing_result.convergence_diagnostics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to price basket option: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/exotic/lookback")
async def price_lookback_option(lookback_data: dict):
    """Price lookback option with best historical price"""
    try:
        if not ml_service.exotic_derivatives_engine:
            raise HTTPException(status_code=503, detail="Exotic Derivatives Engine not initialized")
        
        # Validate lookback-specific fields
        required_fields = ["symbol", "current_price", "volatility", "lookback_type", "expiration_date"]
        for field in required_fields:
            if field not in lookback_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        from exotic_derivatives_engine_v1_0_0_20250819 import ExoticContractSpec, UnderlyingAsset, ExoticType, LookbackType
        from datetime import datetime
        
        # Create underlying asset
        underlying = UnderlyingAsset(
            symbol=lookback_data["symbol"],
            current_price=lookback_data["current_price"],
            volatility=lookback_data["volatility"],
            dividend_yield=lookback_data.get("dividend_yield", 0.0),
            currency=lookback_data.get("currency", "USD")
        )
        
        # Parse expiration date
        if isinstance(lookback_data["expiration_date"], str):
            expiration_date = datetime.fromisoformat(lookback_data["expiration_date"].replace('Z', '+00:00'))
        else:
            expiration_date = lookback_data["expiration_date"]
        
        # Create lookback option contract
        contract = ExoticContractSpec(
            contract_id=f"LOOKBACK_{lookback_data['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            exotic_type=ExoticType.LOOKBACK_OPTION,
            underlying_assets=[underlying],
            expiration_date=expiration_date,
            strike=lookback_data.get("strike"),  # May be None for floating strike
            lookback_type=LookbackType(lookback_data["lookback_type"]),
            payoff_currency=lookback_data.get("payoff_currency", "USD"),
            notional=lookback_data.get("notional", 1000000.0)
        )
        
        # Price the lookback option
        pricing_result = await ml_service.exotic_derivatives_engine.price_exotic_derivative(contract)
        
        return {
            "contract_id": pricing_result.contract_id,
            "lookback_type": lookback_data["lookback_type"],
            "theoretical_price": pricing_result.theoretical_price,
            "confidence_interval": pricing_result.confidence_interval,
            "computation_time": pricing_result.computation_time,
            "convergence_diagnostics": pricing_result.convergence_diagnostics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to price lookback option: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/exotic/simulation-methods")
async def get_simulation_methods():
    """Get available Monte Carlo simulation methods"""
    try:
        return {
            "simulation_methods": [
                {
                    "method": "standard_mc",
                    "name": "Standard Monte Carlo",
                    "description": "Pseudo-random number generation",
                    "advantages": ["Simple implementation", "Fast for low dimensions"],
                    "suitable_for": ["Most exotic options", "Quick estimates"]
                },
                {
                    "method": "quasi_mc_sobol",
                    "name": "Quasi-Monte Carlo (Sobol)",
                    "description": "Low-discrepancy Sobol sequence",
                    "advantages": ["Better convergence", "Deterministic"],
                    "suitable_for": ["High-dimensional problems", "Basket options"]
                },
                {
                    "method": "quasi_mc_halton",
                    "name": "Quasi-Monte Carlo (Halton)",
                    "description": "Low-discrepancy Halton sequence",
                    "advantages": ["Good for moderate dimensions", "Fast generation"],
                    "suitable_for": ["Multi-asset derivatives", "Asian options"]
                },
                {
                    "method": "antithetic_variates",
                    "name": "Antithetic Variates",
                    "description": "Variance reduction technique",
                    "advantages": ["Reduced variance", "Simple to implement"],
                    "suitable_for": ["Symmetric payoffs", "European-style options"]
                },
                {
                    "method": "control_variates",
                    "name": "Control Variates",
                    "description": "Correlation-based variance reduction",
                    "advantages": ["Significant variance reduction", "Uses known solutions"],
                    "suitable_for": ["Complex exotics", "Path-dependent options"]
                },
                {
                    "method": "importance_sampling",
                    "name": "Importance Sampling",
                    "description": "Weighted sampling technique",
                    "advantages": ["Efficient for rare events", "Reduced tail estimation error"],
                    "suitable_for": ["Deep OTM options", "Risk management"]
                }
            ],
            "default_parameters": {
                "num_paths": 100000,
                "num_time_steps": 252,
                "variance_reduction": True,
                "confidence_level": 0.95
            },
            "performance_guidelines": {
                "quick_estimate": {"num_paths": 10000, "num_time_steps": 100},
                "standard_pricing": {"num_paths": 100000, "num_time_steps": 252},
                "high_precision": {"num_paths": 1000000, "num_time_steps": 500}
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get simulation methods: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 13: ADVANCED RISK MANAGEMENT ENDPOINTS =====================

@app.get("/api/v1/risk/status")
async def get_risk_engine_status():
    """Get Advanced Risk Management Engine status and capabilities"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        status = await ml_service.advanced_risk_engine.get_risk_engine_status()
        
        return {
            "risk_engine_status": status,
            "phase": "Phase 13 - Advanced Risk Management und Real-Time Portfolio Analytics",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get risk engine status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk/var/{symbol}")
async def calculate_value_at_risk(
    symbol: str,
    confidence_level: float = 0.95,
    holding_period: int = 1,
    method: str = "historical_simulation",
    lookback_days: int = 252
):
    """Calculate Value at Risk for a specific asset"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        # Convert method string to enum
        try:
            var_method = VaRMethod(method.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid VaR method: {method}")
        
        # Validate parameters
        if not 0.5 <= confidence_level <= 0.999:
            raise HTTPException(status_code=400, detail="Confidence level must be between 0.5 and 0.999")
        
        if holding_period < 1 or holding_period > 250:
            raise HTTPException(status_code=400, detail="Holding period must be between 1 and 250 days")
        
        # Calculate VaR
        var_result = await ml_service.advanced_risk_engine.calculate_var(
            symbol=symbol,
            confidence_level=confidence_level,
            holding_period=holding_period,
            method=var_method,
            lookback_days=lookback_days
        )
        
        return {
            "symbol": symbol,
            "var_calculation": var_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate VaR for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/risk/portfolio")
async def calculate_portfolio_risk(portfolio_data: dict):
    """Calculate comprehensive portfolio risk metrics"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        # Validate portfolio data
        if "portfolio_weights" not in portfolio_data:
            raise HTTPException(status_code=400, detail="Missing portfolio_weights in request body")
        
        portfolio_weights = portfolio_data["portfolio_weights"]
        lookback_days = portfolio_data.get("lookback_days", 252)
        confidence_level = portfolio_data.get("confidence_level", 0.95)
        
        # Validate weights sum to 1
        total_weight = sum(portfolio_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise HTTPException(status_code=400, detail=f"Portfolio weights sum to {total_weight:.3f}, must sum to 1.0")
        
        # Calculate portfolio risk
        portfolio_risk = await ml_service.advanced_risk_engine.calculate_portfolio_risk(
            portfolio_weights=portfolio_weights,
            lookback_days=lookback_days,
            confidence_level=confidence_level
        )
        
        return {
            "portfolio_id": portfolio_risk.portfolio_id,
            "risk_metrics": {
                "total_var": portfolio_risk.total_var,
                "component_var": portfolio_risk.component_var,
                "marginal_var": portfolio_risk.marginal_var,
                "incremental_var": portfolio_risk.incremental_var,
                "diversification_ratio": portfolio_risk.diversification_ratio,
                "risk_concentration": portfolio_risk.risk_concentration,
                "volatility_contribution": portfolio_risk.volatility_contribution
            },
            "calculation_parameters": {
                "confidence_level": confidence_level,
                "lookback_days": lookback_days,
                "portfolio_weights": portfolio_weights
            },
            "timestamp": portfolio_risk.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate portfolio risk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/risk/stress-test")
async def perform_stress_test(stress_data: dict):
    """Perform stress testing on portfolio"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        # Validate stress test data
        required_fields = ["portfolio_weights", "scenario_name"]
        for field in required_fields:
            if field not in stress_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        portfolio_weights = stress_data["portfolio_weights"]
        scenario_name = stress_data["scenario_name"]
        custom_scenario = stress_data.get("custom_scenario")
        
        # Perform stress test
        stress_result = await ml_service.advanced_risk_engine.perform_stress_test(
            portfolio_weights=portfolio_weights,
            scenario_name=scenario_name,
            custom_scenario=custom_scenario
        )
        
        return {
            "stress_test_results": {
                "scenario_name": stress_result.scenario_name,
                "scenario_type": stress_result.scenario_type.value,
                "portfolio_pnl": stress_result.portfolio_pnl,
                "individual_pnl": stress_result.individual_pnl,
                "worst_performers": stress_result.worst_performers,
                "best_performers": stress_result.best_performers,
                "risk_factors_impact": stress_result.risk_factors_impact,
                "scenario_description": stress_result.scenario_description
            },
            "timestamp": stress_result.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to perform stress test: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk/liquidity/{symbol}")
async def assess_liquidity_risk(symbol: str):
    """Assess liquidity risk for individual asset"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        # Assess liquidity risk
        liquidity_risk = await ml_service.advanced_risk_engine.assess_liquidity_risk(symbol)
        
        return {
            "symbol": symbol,
            "liquidity_assessment": {
                "bid_ask_spread": liquidity_risk.bid_ask_spread,
                "average_daily_volume": liquidity_risk.average_daily_volume,
                "market_impact_cost": liquidity_risk.market_impact_cost,
                "liquidity_score": liquidity_risk.liquidity_score,
                "days_to_liquidate": liquidity_risk.days_to_liquidate,
                "liquidity_tier": liquidity_risk.liquidity_tier,
                "emergency_liquidation_cost": liquidity_risk.emergency_liquidation_cost
            },
            "timestamp": liquidity_risk.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to assess liquidity risk for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk/comprehensive/{symbol}")
async def get_comprehensive_risk_metrics(
    symbol: str,
    benchmark_symbol: Optional[str] = None,
    lookback_days: int = 252
):
    """Calculate comprehensive risk metrics for a single asset"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        # Calculate comprehensive risk metrics
        risk_metrics = await ml_service.advanced_risk_engine.calculate_comprehensive_risk_metrics(
            symbol=symbol,
            benchmark_symbol=benchmark_symbol,
            lookback_days=lookback_days
        )
        
        return {
            "symbol": symbol,
            "benchmark_symbol": benchmark_symbol,
            "risk_metrics": {
                "var_95": risk_metrics.var_95,
                "var_99": risk_metrics.var_99,
                "expected_shortfall_95": risk_metrics.expected_shortfall_95,
                "expected_shortfall_99": risk_metrics.expected_shortfall_99,
                "volatility": risk_metrics.volatility,
                "maximum_drawdown": risk_metrics.maximum_drawdown,
                "beta": risk_metrics.beta,
                "tracking_error": risk_metrics.tracking_error,
                "sharpe_ratio": risk_metrics.sharpe_ratio,
                "information_ratio": risk_metrics.information_ratio,
                "method_used": risk_metrics.method_used
            },
            "calculation_parameters": {
                "lookback_days": lookback_days,
                "benchmark_used": benchmark_symbol is not None
            },
            "timestamp": risk_metrics.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate comprehensive risk metrics for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk/scenarios")
async def get_available_stress_scenarios():
    """Get all available stress test scenarios"""
    try:
        if not ml_service.advanced_risk_engine:
            raise HTTPException(status_code=503, detail="Advanced Risk Management Engine not initialized")
        
        scenarios = ml_service.advanced_risk_engine.stress_scenarios
        
        return {
            "available_scenarios": scenarios,
            "scenario_count": len(scenarios),
            "custom_scenarios_supported": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get stress scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 14: ESG ANALYTICS & SUSTAINABLE FINANCE ENDPOINTS =====================

@app.get("/api/v1/esg/status")
async def get_esg_engine_status():
    """Get ESG Analytics Engine status"""
    try:
        if not ml_service.esg_analytics_engine:
            raise HTTPException(status_code=503, detail="ESG Analytics Engine not initialized")
        
        return await ml_service.esg_analytics_engine.get_esg_engine_status()
        
    except Exception as e:
        logger.error(f"Failed to get ESG engine status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/esg/score/{symbol}")
async def get_esg_score(symbol: str, rating_agency: str = "composite", include_sector_adjustment: bool = True):
    """Calculate comprehensive ESG score for a symbol"""
    try:
        if not ml_service.esg_analytics_engine:
            raise HTTPException(status_code=503, detail="ESG Analytics Engine not initialized")
        
        from esg_analytics_engine_v1_0_0_20250819 import ESGRatingAgency
        
        # Convert string to enum
        try:
            agency_enum = ESGRatingAgency(rating_agency.lower())
        except ValueError:
            agency_enum = ESGRatingAgency.COMPOSITE
        
        esg_score = await ml_service.esg_analytics_engine.calculate_esg_score(
            symbol=symbol,
            rating_agency=agency_enum,
            include_sector_adjustment=include_sector_adjustment
        )
        
        return {
            "symbol": symbol,
            "overall_score": esg_score.overall_score,
            "environmental_score": esg_score.environmental_score,
            "social_score": esg_score.social_score,
            "governance_score": esg_score.governance_score,
            "rating_agency": esg_score.rating_agency.value,
            "percentile_rank": esg_score.percentile_rank,
            "sector_comparison": esg_score.sector_comparison,
            "improvement_trend": esg_score.improvement_trend,
            "data_quality": esg_score.data_quality,
            "controversy_level": esg_score.controversy_level,
            "score_date": esg_score.score_date.isoformat(),
            "last_updated": esg_score.last_updated.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate ESG score for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/esg/carbon-footprint/{symbol}")
async def get_carbon_footprint(symbol: str):
    """Analyze company's carbon footprint"""
    try:
        if not ml_service.esg_analytics_engine:
            raise HTTPException(status_code=503, detail="ESG Analytics Engine not initialized")
        
        carbon_footprint = await ml_service.esg_analytics_engine.analyze_carbon_footprint(symbol)
        
        return {
            "symbol": symbol,
            "scope1_emissions": carbon_footprint.scope1_emissions,
            "scope2_emissions": carbon_footprint.scope2_emissions,
            "scope3_emissions": carbon_footprint.scope3_emissions,
            "total_emissions": carbon_footprint.total_emissions,
            "carbon_intensity": carbon_footprint.carbon_intensity,
            "emissions_trend": carbon_footprint.emissions_trend,
            "reduction_targets": carbon_footprint.reduction_targets,
            "net_zero_commitment": carbon_footprint.net_zero_commitment.isoformat() if carbon_footprint.net_zero_commitment else None,
            "carbon_offset_program": carbon_footprint.carbon_offset_program,
            "verification_status": carbon_footprint.verification_status,
            "reporting_standard": carbon_footprint.reporting_standard,
            "timestamp": carbon_footprint.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze carbon footprint for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/esg/sustainable-finance/{symbol}")
async def get_sustainable_finance_metrics(symbol: str):
    """Assess sustainable finance metrics"""
    try:
        if not ml_service.esg_analytics_engine:
            raise HTTPException(status_code=503, detail="ESG Analytics Engine not initialized")
        
        sf_metrics = await ml_service.esg_analytics_engine.assess_sustainable_finance_metrics(symbol)
        
        return {
            "symbol": symbol,
            "green_revenue_percentage": sf_metrics.green_revenue_percentage,
            "sustainable_capex_percentage": sf_metrics.sustainable_capex_percentage,
            "taxonomy_alignment_percentage": sf_metrics.taxonomy_alignment_percentage,
            "transition_finance_percentage": sf_metrics.transition_finance_percentage,
            "sustainable_debt_ratio": sf_metrics.sustainable_debt_ratio,
            "green_bond_issuance": sf_metrics.green_bond_issuance,
            "esg_linked_financing": sf_metrics.esg_linked_financing,
            "sustainability_targets": sf_metrics.sustainability_targets,
            "impact_measurement": sf_metrics.impact_measurement,
            "sdg_alignment": sf_metrics.sdg_alignment,
            "timestamp": sf_metrics.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to assess sustainable finance metrics for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/esg/climate-risk/{symbol}")
async def assess_climate_risk(symbol: str, time_horizon: str = "2030", scenario: str = "rcp45"):
    """Assess climate-related risks"""
    try:
        if not ml_service.esg_analytics_engine:
            raise HTTPException(status_code=503, detail="ESG Analytics Engine not initialized")
        
        climate_risk = await ml_service.esg_analytics_engine.assess_climate_risk(
            symbol=symbol,
            time_horizon=time_horizon,
            scenario=scenario
        )
        
        return {
            "symbol": symbol,
            "physical_risk_score": climate_risk.physical_risk_score,
            "transition_risk_score": climate_risk.transition_risk_score,
            "overall_climate_risk": climate_risk.overall_climate_risk,
            "time_horizon": climate_risk.time_horizon,
            "scenario_analysis": climate_risk.scenario_analysis,
            "adaptation_measures": climate_risk.adaptation_measures,
            "resilience_score": climate_risk.resilience_score,
            "stranded_assets_risk": climate_risk.stranded_assets_risk,
            "carbon_pricing_exposure": climate_risk.carbon_pricing_exposure,
            "regulatory_risk_score": climate_risk.regulatory_risk_score,
            "reputational_risk_score": climate_risk.reputational_risk_score,
            "timestamp": climate_risk.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to assess climate risk for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/esg/portfolio-metrics")
async def calculate_portfolio_esg_metrics(portfolio_data: dict):
    """Calculate portfolio-level ESG metrics"""
    try:
        if not ml_service.esg_analytics_engine:
            raise HTTPException(status_code=503, detail="ESG Analytics Engine not initialized")
        
        # Validate portfolio data
        if "portfolio_weights" not in portfolio_data:
            raise HTTPException(status_code=400, detail="Missing portfolio_weights in request body")
        
        portfolio_weights = portfolio_data["portfolio_weights"]
        
        # Validate weights sum to 1.0 (or close to it)
        total_weight = sum(portfolio_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise HTTPException(status_code=400, detail=f"Portfolio weights must sum to 1.0, got {total_weight}")
        
        portfolio_esg = await ml_service.esg_analytics_engine.calculate_portfolio_esg_metrics(portfolio_weights)
        
        return {
            "portfolio_id": portfolio_esg.portfolio_id,
            "weighted_esg_score": portfolio_esg.weighted_esg_score,
            "esg_score_distribution": portfolio_esg.esg_score_distribution,
            "carbon_footprint": portfolio_esg.carbon_footprint,
            "water_footprint": portfolio_esg.water_footprint,
            "waste_footprint": portfolio_esg.waste_footprint,
            "controversy_exposure": portfolio_esg.controversy_exposure,
            "sector_allocation": portfolio_esg.sector_allocation,
            "regional_allocation": portfolio_esg.regional_allocation,
            "sdg_alignment": portfolio_esg.sdg_alignment,
            "eu_taxonomy_alignment": portfolio_esg.eu_taxonomy_alignment,
            "green_revenue_exposure": portfolio_esg.green_revenue_exposure,
            "fossil_fuel_exposure": portfolio_esg.fossil_fuel_exposure,
            "timestamp": portfolio_esg.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate portfolio ESG metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/esg/categories")
async def get_esg_categories():
    """Get supported ESG categories and metrics"""
    try:
        from esg_analytics_engine_v1_0_0_20250819 import ESGCategory, ESGRatingAgency, SustainabilityMetric, ClimateRiskType
        
        return {
            "esg_categories": [cat.value for cat in ESGCategory],
            "rating_agencies": [agency.value for agency in ESGRatingAgency],
            "sustainability_metrics": [metric.value for metric in SustainabilityMetric],
            "climate_risk_types": [risk.value for risk in ClimateRiskType],
            "supported_scenarios": ["rcp26", "rcp45", "rcp85"],
            "time_horizons": ["2025", "2030", "2040", "2050"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get ESG categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== MULTI-HORIZON TRAINING & ENSEMBLE ENDPOINTS =====================

@app.post("/api/v1/models/train/multi-horizon/{symbol}")
async def train_multi_horizon_models(symbol: str):
    """Train all multi-horizon models with synthetic data"""
    try:
        if not ml_service.synthetic_trainer:
            raise HTTPException(status_code=503, detail="Synthetic trainer not initialized")
        
        logger.info(f"Starting multi-horizon training for {symbol}")
        result = await ml_service.synthetic_trainer.train_all_horizons(symbol)
        
        # Publish ML event
        await ml_event_publisher.publish_event({
            "event_type": "multi_horizon_training_completed",
            "symbol": symbol,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed multi-horizon training for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/multi-horizon/{symbol}")
async def get_multi_horizon_predictions(symbol: str, horizon: int):
    """Get predictions for specific horizon"""
    try:
        if horizon not in ml_service.multi_horizon_models:
            raise HTTPException(status_code=400, detail=f"Horizon {horizon} not supported")
        
        model = ml_service.multi_horizon_models[horizon]
        prediction = await model.predict(symbol)
        
        return {
            "symbol": symbol,
            "horizon_days": horizon,
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get {horizon}-day prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/all-horizons/{symbol}")
async def get_all_horizons_predictions(symbol: str):
    """Get predictions for all supported horizons"""
    try:
        predictions = {}
        
        for horizon, model in ml_service.multi_horizon_models.items():
            try:
                prediction = await model.predict(symbol)
                predictions[f"{horizon}d"] = prediction
            except Exception as e:
                predictions[f"{horizon}d"] = {"error": str(e)}
        
        return {
            "symbol": symbol,
            "predictions": predictions,
            "supported_horizons": list(ml_service.multi_horizon_models.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get all-horizon predictions for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ensemble/analysis/{symbol}")
async def get_multi_horizon_ensemble_analysis(symbol: str):
    """Get comprehensive multi-horizon ensemble analysis with investment strategies"""
    try:
        if not ml_service.multi_horizon_ensemble:
            raise HTTPException(status_code=503, detail="Multi-horizon ensemble manager not initialized")
        
        # Get predictions for all horizons
        predictions = {}
        for horizon, model in ml_service.multi_horizon_models.items():
            try:
                prediction = await model.predict(symbol)
                predictions[f"{horizon}d"] = prediction
            except Exception as e:
                logger.warning(f"Failed to get {horizon}d prediction: {str(e)}")
                predictions[f"{horizon}d"] = {
                    "predicted_price": 150.0,  # Fallback
                    "confidence_score": 0.3,   # Low confidence
                    "error": str(e)
                }
        
        # Get comprehensive ensemble analysis
        analysis = await ml_service.multi_horizon_ensemble.get_multi_horizon_analysis(symbol, predictions)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to get ensemble analysis for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== LEGACY TRAINING ENDPOINTS =====================

@app.post("/api/v1/models/train/lstm/{symbol}")
async def train_lstm_model(symbol: str):
    """Train LSTM model for specific symbol"""
    try:
        result = await ml_service.lstm_model.train_model(symbol)
        
        # Publish ML event
        await ml_event_publisher.publish_event({
            "event_type": "lstm_model_trained",
            "symbol": symbol,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to train LSTM model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train/sentiment/{symbol}")
async def train_sentiment_model(symbol: str):
    """Train Sentiment XGBoost model for specific symbol"""
    try:
        result = await ml_service.sentiment_model.train_model(symbol)
        
        # Publish ML event
        await ml_event_publisher.publish_event({
            "event_type": "sentiment_model_trained",
            "symbol": symbol,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to train Sentiment model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train/fundamental/{symbol}")
async def train_fundamental_model(symbol: str):
    """Train Fundamental XGBoost model for specific symbol"""
    try:
        result = await ml_service.fundamental_model.train_model(symbol)
        
        # Publish ML event
        await ml_event_publisher.publish_event({
            "event_type": "fundamental_model_trained",
            "symbol": symbol,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to train Fundamental model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train/meta/{symbol}")
async def train_meta_ensemble_model(symbol: str):
    """Train Meta LightGBM ensemble model"""
    try:
        result = await ml_service.meta_model.train_ensemble_model(symbol)
        
        # Publish ML event
        await ml_event_publisher.publish_event({
            "event_type": "meta_ensemble_trained",
            "symbol": symbol,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to train Meta ensemble for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PREDICTION ENDPOINTS =====================

@app.get("/api/v1/predictions/lstm/{symbol}")
async def get_lstm_prediction(symbol: str):
    """Get LSTM prediction for symbol"""
    try:
        prediction = await ml_service.lstm_model.predict(symbol)
        return {
            "symbol": symbol,
            "model_type": "lstm",
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get LSTM prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/sentiment/{symbol}")
async def get_sentiment_prediction(symbol: str):
    """Get Sentiment prediction for symbol"""
    try:
        prediction = await ml_service.sentiment_model.predict(symbol)
        return {
            "symbol": symbol,
            "model_type": "sentiment",
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get Sentiment prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/fundamental/{symbol}")
async def get_fundamental_prediction(symbol: str):
    """Get Fundamental prediction for symbol"""
    try:
        prediction = await ml_service.fundamental_model.predict(symbol)
        return {
            "symbol": symbol,
            "model_type": "fundamental",
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get Fundamental prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/ensemble/{symbol}")
async def get_ensemble_prediction(symbol: str):
    """Get Meta ensemble prediction combining all models"""
    try:
        # Get base predictions
        lstm_pred = await ml_service.lstm_model.predict(symbol)
        sentiment_pred = await ml_service.sentiment_model.predict(symbol)
        fundamental_pred = await ml_service.fundamental_model.predict(symbol)
        
        # Combine via meta model
        base_predictions = {
            'technical': lstm_pred,
            'sentiment': sentiment_pred,
            'fundamental': fundamental_pred
        }
        
        ensemble_prediction = await ml_service.meta_model.predict_ensemble(base_predictions)
        
        return {
            "symbol": symbol,
            "model_type": "ensemble",
            "base_predictions": base_predictions,
            "ensemble_prediction": ensemble_prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get ensemble prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 15: MARKET INTELLIGENCE & EVENT-DRIVEN ANALYTICS ENDPOINTS =====================

@app.get("/api/v1/market-intelligence/status")
async def get_market_intelligence_status():
    """Get Market Intelligence Engine status"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        return await ml_service.market_intelligence_engine.get_engine_status()
        
    except Exception as e:
        logger.error(f"Failed to get market intelligence status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/events")
async def get_recent_events(limit: int = 50, event_type: Optional[str] = None):
    """Get recent market events"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        # Convert string to EventType enum if provided
        event_type_filter = None
        if event_type:
            try:
                from market_intelligence_engine_v1_0_0_20250819 import EventType
                event_type_filter = EventType(event_type.lower())
            except ValueError:
                pass
        
        events = await ml_service.market_intelligence_engine.get_recent_events(
            limit=limit,
            event_type_filter=event_type_filter
        )
        
        return {
            "events": events,
            "count": len(events),
            "event_type_filter": event_type,
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/sentiment/{symbol}")
async def get_realtime_sentiment(symbol: str, timeframe_hours: int = 24):
    """Get real-time sentiment analysis for symbol"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        sentiment_analysis = await ml_service.market_intelligence_engine.analyze_realtime_sentiment(
            symbol=symbol,
            timeframe_hours=timeframe_hours
        )
        
        return {
            "symbol": symbol,
            "timeframe_hours": timeframe_hours,
            "sentiment_analysis": sentiment_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get sentiment for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/volatility-alerts")
async def get_volatility_alerts(limit: int = 20):
    """Get recent volatility spike alerts"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        alerts = await ml_service.market_intelligence_engine.detect_volatility_spikes(limit=limit)
        
        return {
            "volatility_alerts": alerts,
            "count": len(alerts),
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get volatility alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/regime-analysis")
async def get_market_regime_analysis():
    """Get current market regime analysis"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        regime_analysis = await ml_service.market_intelligence_engine.detect_market_regime_changes()
        
        return {
            "market_regime_analysis": regime_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get market regime analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/economic-indicators")
async def get_economic_indicators():
    """Get recent economic indicator updates"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        indicators = await ml_service.market_intelligence_engine.monitor_economic_indicators()
        
        return {
            "economic_indicators": indicators,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get economic indicators: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/correlation-breaks")
async def get_correlation_break_analysis(limit: int = 10):
    """Get recent correlation break events"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        correlation_breaks = await ml_service.market_intelligence_engine.analyze_correlation_breaks(limit=limit)
        
        return {
            "correlation_breaks": correlation_breaks,
            "count": len(correlation_breaks),
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get correlation breaks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-intelligence/comprehensive-report")
async def get_comprehensive_market_intelligence():
    """Get comprehensive market intelligence report"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        report = await ml_service.market_intelligence_engine.generate_comprehensive_intelligence_report()
        
        return {
            "comprehensive_report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to generate comprehensive market intelligence report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/market-intelligence/start-streaming")
async def start_market_intelligence_streaming():
    """Start market intelligence real-time streaming"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        await ml_service.market_intelligence_engine.start_event_processing()
        
        return {
            "status": "started",
            "message": "Market intelligence streaming started successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start market intelligence streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/market-intelligence/stop-streaming")
async def stop_market_intelligence_streaming():
    """Stop market intelligence real-time streaming"""
    try:
        if not ml_service.market_intelligence_engine:
            raise HTTPException(status_code=503, detail="Market Intelligence Engine not initialized")
        
        await ml_service.market_intelligence_engine.stop_event_processing()
        
        return {
            "status": "stopped",
            "message": "Market intelligence streaming stopped successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop market intelligence streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== PHASE 16: QUANTUM COMPUTING ML MODELS & ADVANCED NEURAL NETWORKS ENDPOINTS =====================

@app.get("/api/v1/quantum/status")
async def get_quantum_ml_status():
    """Get Quantum ML Engine status"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        return await ml_service.classical_enhanced_engine.get_quantum_engine_status()
        
    except Exception as e:
        logger.error(f"Failed to get quantum ML status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/quantum/vqe/portfolio-optimization")
async def run_vqe_portfolio_optimization(
    expected_returns: List[float], 
    covariance_matrix: List[List[float]], 
    risk_tolerance: float = 0.5
):
    """Run VQE Portfolio Optimization"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        expected_returns_array = np.array(expected_returns)
        covariance_matrix_array = np.array(covariance_matrix)
        
        vqe_result = await ml_service.classical_enhanced_engine.run_vqe_portfolio_optimization(
            expected_returns=expected_returns_array,
            covariance_matrix=covariance_matrix_array,
            risk_tolerance=risk_tolerance
        )
        
        return {
            "optimal_energy": vqe_result.optimal_energy,
            "optimal_parameters": vqe_result.optimal_parameters.tolist(),
            "portfolio_weights": vqe_result.portfolio_weights.tolist(),
            "quantum_advantage": vqe_result.quantum_advantage,
            "num_iterations": vqe_result.num_iterations,
            "risk_metrics": vqe_result.risk_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to run VQE portfolio optimization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/quantum/qaoa/optimization")
async def run_qaoa_optimization(cost_matrix: List[List[float]], num_layers: int = 3):
    """Run QAOA Optimization"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        cost_matrix_array = np.array(cost_matrix)
        
        qaoa_result = await ml_service.classical_enhanced_engine.run_qaoa_optimization(
            cost_matrix=cost_matrix_array,
            num_layers=num_layers
        )
        
        return {
            "optimal_value": qaoa_result.optimal_value,
            "optimal_bitstring": qaoa_result.optimal_bitstring,
            "probability_distribution": qaoa_result.probability_distribution,
            "beta_parameters": qaoa_result.beta_parameters.tolist(),
            "gamma_parameters": qaoa_result.gamma_parameters.tolist(),
            "quantum_speedup": qaoa_result.quantum_speedup,
            "convergence_achieved": qaoa_result.convergence_achieved,
            "num_layers": qaoa_result.num_layers,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to run QAOA optimization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/quantum/neural-network/train")
async def train_quantum_neural_network(
    model_name: str,
    training_data: List[List[float]],
    training_labels: List[List[float]],
    num_epochs: int = 100,
    learning_rate: float = 0.01
):
    """Train Quantum Neural Network"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        training_data_array = np.array(training_data)
        training_labels_array = np.array(training_labels)
        
        training_result = await ml_service.classical_enhanced_engine.train_quantum_neural_network(
            model_name=model_name,
            training_data=training_data_array,
            training_labels=training_labels_array,
            num_epochs=num_epochs,
            learning_rate=learning_rate
        )
        
        return training_result
        
    except Exception as e:
        logger.error(f"Failed to train quantum neural network: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/quantum/attention/apply")
async def apply_quantum_attention(
    sequence_data: List[List[List[float]]],
    model_name: str = "quantum_attention"
):
    """Apply Quantum-Enhanced Attention"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        sequence_data_array = np.array(sequence_data)
        
        attention_result = await ml_service.classical_enhanced_engine.apply_quantum_attention(
            sequence_data=sequence_data_array,
            model_name=model_name
        )
        
        return {
            "model_name": attention_result["model_name"],
            "quantum_entropy": attention_result["quantum_entropy"],
            "classical_entropy": attention_result["classical_entropy"],
            "entropy_advantage": attention_result["entropy_advantage"],
            "output_shape": attention_result["output_shape"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to apply quantum attention: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/quantum/monte-carlo")
async def run_quantum_monte_carlo(
    num_samples: int = 10000,
    num_qubits: int = 8,
    spot_price: float = 100.0,
    strike_price: float = 105.0,
    risk_free_rate: float = 0.05,
    volatility: float = 0.2,
    time_to_maturity: float = 0.25
):
    """Run Quantum Monte Carlo Simulation"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        option_params = {
            "spot_price": spot_price,
            "strike_price": strike_price,
            "risk_free_rate": risk_free_rate,
            "volatility": volatility,
            "time_to_maturity": time_to_maturity
        }
        
        monte_carlo_result = await ml_service.classical_enhanced_engine.run_quantum_monte_carlo(
            num_samples=num_samples,
            num_qubits=num_qubits,
            option_params=option_params
        )
        
        return monte_carlo_result
        
    except Exception as e:
        logger.error(f"Failed to run quantum Monte Carlo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/quantum/models/list")
async def list_quantum_models():
    """List all available quantum models"""
    try:
        if not ml_service.classical_enhanced_engine:
            raise HTTPException(status_code=503, detail="Classical-Enhanced ML Engine not initialized")
        
        status = await ml_service.classical_enhanced_engine.get_quantum_engine_status()
        
        return {
            "quantum_neural_networks": list(ml_service.classical_enhanced_engine.quantum_neural_networks.keys()),
            "quantum_transformers": list(ml_service.classical_enhanced_engine.quantum_transformers.keys()),
            "circuit_templates": list(ml_service.classical_enhanced_engine.circuit_templates.keys()),
            "quantum_advantage_scores": status["quantum_advantage_scores"],
            "training_models": status["training_models"],
            "quantum_available": status["quantum_available"],
            "torch_available": status["torch_available"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list quantum models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/quantum/algorithms/supported")
async def get_supported_quantum_algorithms():
    """Get list of supported quantum algorithms"""
    try:
        algorithms = {
            "optimization": [
                {
                    "name": "VQE",
                    "description": "Variational Quantum Eigensolver for portfolio optimization",
                    "use_case": "Portfolio risk-return optimization with quantum advantage"
                },
                {
                    "name": "QAOA", 
                    "description": "Quantum Approximate Optimization Algorithm",
                    "use_case": "Combinatorial optimization problems in finance"
                }
            ],
            "machine_learning": [
                {
                    "name": "QNN",
                    "description": "Quantum Neural Networks",
                    "use_case": "Financial time series prediction with quantum features"
                },
                {
                    "name": "Quantum Attention",
                    "description": "Quantum-enhanced attention mechanisms",
                    "use_case": "Advanced financial text analysis and market sentiment"
                }
            ],
            "simulation": [
                {
                    "name": "Quantum Monte Carlo",
                    "description": "Quantum-enhanced Monte Carlo simulations",
                    "use_case": "Option pricing with quantum random number generation"
                }
            ]
        }
        
        return {
            "supported_algorithms": algorithms,
            "total_algorithms": sum(len(category) for category in algorithms.values()),
            "quantum_advantage_areas": [
                "Portfolio Optimization",
                "Risk Analysis", 
                "Monte Carlo Simulations",
                "Feature Extraction",
                "Pattern Recognition"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get supported quantum algorithms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== SIGNAL HANDLING =====================

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    ml_service.shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# ===================== MAIN ENTRY POINT =====================

if __name__ == "__main__":
    logger.info("Starting ML Analytics Service v1.0.0 - Phase 10: Advanced Market Microstructure & HFT Analytics")
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=ML_SERVICE_CONFIG['service']['port'],
        log_level="info",
        access_log=False  # Disable access logs to reduce noise
    )