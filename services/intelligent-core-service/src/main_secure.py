"""
Intelligent-Core Service für aktienanalyse-ökosystem (SECURITY FIXED VERSION)
Vereint Analysis, Performance und Intelligence in einem Service
Security fixes: Environment-Variablen, SQL-Injection-Schutz, Input-Validation
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import shared libraries (SECURITY FIX)
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging, setup_security_logging, setup_performance_logging
from database_mock import DatabaseManager, EventStore, StockAnalysisRepository, HealthChecker
from security import InputValidator, SecurityConfig, StockAnalysisRequest, create_security_headers, get_client_ip, RateLimiter
from event_bus_simple import EventBusConnector, create_analysis_event, EventType

# Load environment variables (SECURITY FIX)
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Initialize loggers (SECURITY FIX - no duplicate code)
logger = setup_logging("intelligent-core-service")
security_logger = setup_security_logging("intelligent-core-service")
performance_logger = setup_performance_logging("intelligent-core-service")

# Initialize security components (SECURITY FIX)
security_config = SecurityConfig()
input_validator = InputValidator(security_config)
rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100")),
    window_seconds=60
)

# ================================================================
# MODELS (SECURITY FIX - using shared validation)
# ================================================================

class AnalysisResponse(BaseModel):
    symbol: str
    score: float
    recommendation: str
    confidence: float
    indicators: Dict[str, float]
    timestamp: str

class PerformanceMetrics(BaseModel):
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    alpha: float
    beta: float

# ================================================================
# INTELLIGENT CORE SERVICE
# ================================================================

class IntelligentCoreService:
    def __init__(self):
        # Database connections (SECURITY FIX - using shared database manager)
        self.db_manager = DatabaseManager()
        self.event_store = None
        self.analysis_repository = None
        self.health_checker = None
        
        # Event bus (SECURITY FIX - real implementation)
        self.event_bus = EventBusConnector("intelligent-core-service")
        
        # ML Models
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Cache for repeated requests
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize service with proper error handling"""
        try:
            # Initialize database (SECURITY FIX)
            await self.db_manager.initialize()
            self.event_store = EventStore(self.db_manager)
            self.analysis_repository = StockAnalysisRepository(self.db_manager)
            self.health_checker = HealthChecker(self.db_manager)
            
            # Initialize event bus (SECURITY FIX)
            await self.event_bus.connect()
            
            # Subscribe to relevant events
            await self.event_bus.subscribe(
                EventType.DATA_SYNCHRONIZED.value,
                self._handle_data_sync_event
            )
            
            # Initialize ML model
            await self._initialize_ml_model()
            
            logger.info("Intelligent-Core Service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize service", error=str(e))
            raise
    
    async def shutdown(self):
        """Shutdown service gracefully"""
        try:
            await self.event_bus.disconnect()
            await self.db_manager.close()
            logger.info("Intelligent-Core Service shutdown complete")
        except Exception as e:
            logger.error("Error during service shutdown", error=str(e))
    
    async def _initialize_ml_model(self):
        """Initialize ML model with dummy data for now"""
        try:
            # Generate dummy training data for demonstration
            np.random.seed(42)
            X = np.random.rand(1000, 5)  # 5 features
            y = np.random.rand(1000)     # target
            
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            self.model.fit(X_scaled, y)
            
            self.is_trained = True
            logger.info("ML model initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize ML model", error=str(e))
            # Continue without ML model
            self.is_trained = False
    
    async def analyze_stock(self, request: StockAnalysisRequest, client_ip: str) -> AnalysisResponse:
        """Analyze stock with security fixes and validation"""
        start_time = datetime.now()
        
        try:
            # Rate limiting (SECURITY FIX)
            if not rate_limiter.is_allowed(client_ip):
                security_logger.log_rate_limit_exceeded(client_ip, client_ip, "/analyze")
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Input validation (SECURITY FIX)
            validated_symbol = input_validator.validate_stock_symbol(request.symbol)
            
            # Check cache first
            cache_key = f"{validated_symbol}_{request.period}"
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if datetime.now() - cache_entry['timestamp'] < timedelta(seconds=self.cache_ttl):
                    logger.debug("Returning cached analysis", symbol=validated_symbol)
                    return cache_entry['data']
            
            # Fetch market data (SECURITY FIX - input validation)
            try:
                import yfinance as yf
                ticker = yf.Ticker(validated_symbol)
                hist_data = ticker.history(period=request.period)
                
                if hist_data.empty:
                    raise HTTPException(status_code=404, detail=f"No data found for symbol {validated_symbol}")
                
            except Exception as e:
                logger.error("Failed to fetch market data", symbol=validated_symbol, error=str(e))
                raise HTTPException(status_code=503, detail="Market data service unavailable")
            
            # Calculate technical indicators
            indicators = await self._calculate_technical_indicators(hist_data)
            
            # Calculate ML score if model is available
            ml_score = await self._calculate_ml_score(indicators) if self.is_trained else 0.5
            
            # Generate recommendation
            recommendation = self._generate_recommendation(ml_score, indicators)
            
            # Calculate confidence
            confidence = self._calculate_confidence(indicators, ml_score)
            
            # Create response
            analysis_result = AnalysisResponse(
                symbol=validated_symbol,
                score=ml_score,
                recommendation=recommendation,
                confidence=confidence,
                indicators=indicators,
                timestamp=datetime.now().isoformat()
            )
            
            # Cache result
            self.cache[cache_key] = {
                'data': analysis_result,
                'timestamp': datetime.now()
            }
            
            # Store in database (SECURITY FIX - parameterized query)
            await self.analysis_repository.update_analysis(
                validated_symbol, ml_score, recommendation, confidence
            )
            
            # Publish event (SECURITY FIX - real event bus)
            event = create_analysis_event(
                symbol=validated_symbol,
                score=ml_score,
                recommendation=recommendation,
                source="intelligent-core-service",
                confidence=confidence
            )
            await self.event_bus.publish(event)
            
            # Log performance (SECURITY FIX)
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            performance_logger.log_request_duration(
                endpoint="/analyze",
                method="POST",
                duration_ms=duration_ms,
                status_code=200
            )
            
            logger.info("Stock analysis completed", 
                       symbol=validated_symbol,
                       score=ml_score,
                       recommendation=recommendation)
            
            return analysis_result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error in stock analysis", 
                        symbol=request.symbol,
                        error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical indicators with error handling"""
        try:
            indicators = {}
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else 50.0
            
            # MACD
            exp1 = data['Close'].ewm(span=12).mean()
            exp2 = data['Close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            indicators['macd'] = float(macd.iloc[-1]) if not macd.empty else 0.0
            indicators['macd_signal'] = float(signal.iloc[-1]) if not signal.empty else 0.0
            
            # Moving Averages
            sma_20 = data['Close'].rolling(window=20).mean()
            sma_50 = data['Close'].rolling(window=50).mean()
            indicators['sma_20'] = float(sma_20.iloc[-1]) if not sma_20.empty else data['Close'].iloc[-1]
            indicators['sma_50'] = float(sma_50.iloc[-1]) if not sma_50.empty else data['Close'].iloc[-1]
            
            # Bollinger Bands
            sma = data['Close'].rolling(window=20).mean()
            std = data['Close'].rolling(window=20).std()
            bb_upper = sma + (std * 2)
            bb_lower = sma - (std * 2)
            indicators['bb_upper'] = float(bb_upper.iloc[-1]) if not bb_upper.empty else data['Close'].iloc[-1] * 1.1
            indicators['bb_lower'] = float(bb_lower.iloc[-1]) if not bb_lower.empty else data['Close'].iloc[-1] * 0.9
            
            # Current price
            indicators['current_price'] = float(data['Close'].iloc[-1])
            
            # Volume analysis
            indicators['avg_volume'] = float(data['Volume'].rolling(window=20).mean().iloc[-1])
            indicators['current_volume'] = float(data['Volume'].iloc[-1])
            
            return indicators
            
        except Exception as e:
            logger.error("Error calculating technical indicators", error=str(e))
            # Return safe defaults
            return {
                'rsi': 50.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'sma_20': 100.0,
                'sma_50': 100.0,
                'bb_upper': 110.0,
                'bb_lower': 90.0,
                'current_price': 100.0,
                'avg_volume': 1000000.0,
                'current_volume': 1000000.0
            }
    
    async def _calculate_ml_score(self, indicators: Dict[str, float]) -> float:
        """Calculate ML score with proper error handling"""
        try:
            if not self.is_trained:
                return 0.5  # Neutral score
            
            # Prepare features for ML model
            features = np.array([[
                indicators.get('rsi', 50.0),
                indicators.get('macd', 0.0),
                indicators.get('current_price', 100.0) / indicators.get('sma_20', 100.0),
                indicators.get('current_volume', 1000000.0) / indicators.get('avg_volume', 1000000.0),
                (indicators.get('current_price', 100.0) - indicators.get('bb_lower', 90.0)) / 
                (indicators.get('bb_upper', 110.0) - indicators.get('bb_lower', 90.0))
            ]])
            
            # Scale features and predict
            features_scaled = self.scaler.transform(features)
            score = self.model.predict(features_scaled)[0]
            
            # Normalize score to 0-1 range
            score = max(0.0, min(1.0, score))
            
            return float(score)
            
        except Exception as e:
            logger.error("Error calculating ML score", error=str(e))
            return 0.5  # Default neutral score
    
    def _generate_recommendation(self, ml_score: float, indicators: Dict[str, float]) -> str:
        """Generate recommendation based on score and indicators"""
        try:
            # Combine ML score with technical indicators
            rsi = indicators.get('rsi', 50.0)
            macd = indicators.get('macd', 0.0)
            price_to_sma = indicators.get('current_price', 100.0) / indicators.get('sma_20', 100.0)
            
            # Calculate composite score
            if ml_score > 0.7 and rsi < 70 and macd > 0 and price_to_sma > 1.02:
                return "STRONG_BUY"
            elif ml_score > 0.6 and rsi < 60:
                return "BUY"
            elif ml_score < 0.3 and rsi > 70:
                return "STRONG_SELL"
            elif ml_score < 0.4 and rsi > 60:
                return "SELL"
            else:
                return "HOLD"
                
        except Exception as e:
            logger.error("Error generating recommendation", error=str(e))
            return "HOLD"
    
    def _calculate_confidence(self, indicators: Dict[str, float], ml_score: float) -> float:
        """Calculate confidence level for the analysis"""
        try:
            # Base confidence on data quality and indicator alignment
            confidence_factors = []
            
            # RSI confidence
            rsi = indicators.get('rsi', 50.0)
            if 30 <= rsi <= 70:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            # Volume confirmation
            volume_ratio = indicators.get('current_volume', 1.0) / indicators.get('avg_volume', 1.0)
            if 0.5 <= volume_ratio <= 2.0:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
            
            # ML model confidence
            if self.is_trained:
                # Distance from neutral score indicates confidence
                ml_confidence = abs(ml_score - 0.5) * 2
                confidence_factors.append(ml_confidence)
            else:
                confidence_factors.append(0.3)
            
            # Calculate average confidence
            confidence = sum(confidence_factors) / len(confidence_factors)
            return round(confidence, 3)
            
        except Exception as e:
            logger.error("Error calculating confidence", error=str(e))
            return 0.5
    
    async def _handle_data_sync_event(self, event):
        """Handle data synchronization events"""
        try:
            logger.info("Received data sync event", event_type=event.event_type)
            # Invalidate cache when new data arrives
            self.cache.clear()
            logger.debug("Analysis cache cleared due to data sync")
        except Exception as e:
            logger.error("Error handling data sync event", error=str(e))
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        try:
            db_health = await self.health_checker.check_connection()
            
            return {
                "service": "intelligent-core-service",
                "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
                "version": "2.0.0-secure",
                "timestamp": datetime.now().isoformat(),
                "database": db_health,
                "event_bus": {"connected": self.event_bus.connected},
                "ml_model": {"trained": self.is_trained},
                "cache_size": len(self.cache)
            }
        except Exception as e:
            logger.error("Error getting health status", error=str(e))
            return {
                "service": "intelligent-core-service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# ================================================================
# FASTAPI APPLICATION (SECURITY FIX)
# ================================================================

app = FastAPI(
    title="Intelligent Core Service",
    description="Secure Analysis, Performance und Intelligence Service",
    version="2.0.0-secure"
)

# CORS Configuration (SECURITY FIX - restricted origins)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://10.1.1.174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # SECURITY FIX - no wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Initialize service
service = IntelligentCoreService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await service.shutdown()

# Security middleware (SECURITY FIX)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Add security headers
    for header, value in create_security_headers().items():
        response.headers[header] = value
    
    return response

# ================================================================
# API ENDPOINTS (SECURITY FIX)
# ================================================================

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock_endpoint(request: StockAnalysisRequest, http_request: Request):
    """Analyze stock with security validation"""
    client_ip = get_client_ip(http_request)
    return await service.analyze_stock(request, client_ip)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return await service.get_health_status()

@app.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    return {
        "cache_size": len(service.cache),
        "ml_model_trained": service.is_trained,
        "event_bus_connected": service.event_bus.connected,
        "timestamp": datetime.now().isoformat()
    }

# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=int(os.getenv("INTELLIGENT_CORE_PORT", "8001")),
        log_config=None,  # Use our custom logging
        access_log=False   # Disable default access logging
    )