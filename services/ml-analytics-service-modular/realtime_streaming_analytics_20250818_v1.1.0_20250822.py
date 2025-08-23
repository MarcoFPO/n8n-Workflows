"""
Real-time Streaming Analytics v1.0.0
Live-Streaming ML Analytics für Real-time Trading Signals

Features:
- WebSocket Server für Live-Daten Streaming
- Real-time Model Predictions
- Event-driven Live Signal Generation  
- Portfolio Risk Monitoring
- Multi-Asset Correlation Analysis
- Automated Trading Alerts

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg

# WebSocket Dependencies
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# NumPy für Berechnungen
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading Signal Types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"

class AlertPriority(Enum):
    """Alert Priority Levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class LiveSignal:
    """Real-time Trading Signal"""
    symbol: str
    signal_type: SignalType
    confidence: float
    price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    horizon_days: int
    model_source: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class RiskAlert:
    """Risk Management Alert"""
    alert_id: str
    symbol: str
    alert_type: str
    priority: AlertPriority
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    action_required: bool

@dataclass
class StreamingMetrics:
    """Real-time Streaming Metrics"""
    connected_clients: int
    signals_sent_per_minute: int
    predictions_generated: int
    average_latency_ms: float
    error_rate: float
    uptime_seconds: float

class RealTimeStreamingAnalytics:
    """
    Real-time Streaming Analytics System
    
    Verwaltet:
    - WebSocket Verbindungen für Live-Daten
    - Real-time Model Predictions
    - Live Trading Signal Generation
    - Portfolio Risk Monitoring
    - Multi-Asset Correlation Analysis
    """
    
    def __init__(self, database_pool: asyncpg.Pool, ml_service_instance):
        self.database_pool = database_pool
        self.ml_service = ml_service_instance
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # WebSocket Server State
        self.websocket_server = None
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.is_streaming = False
        
        # Streaming Configuration
        self.streaming_config = {
            "websocket_host": "0.0.0.0",
            "websocket_port": 8022,
            "prediction_interval_seconds": 30,  # Predictions alle 30 Sekunden
            "signal_threshold": 0.7,  # Minimum confidence für Signals
            "risk_check_interval_seconds": 60,  # Risk checks jede Minute
            "max_clients": 100,  # Maximum WebSocket connections
            "heartbeat_interval_seconds": 30
        }
        
        # Tracked Symbols für Live-Analysis
        self.tracked_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        
        # Streaming State
        self.streaming_metrics = StreamingMetrics(
            connected_clients=0,
            signals_sent_per_minute=0,
            predictions_generated=0,
            average_latency_ms=0.0,
            error_rate=0.0,
            uptime_seconds=0.0
        )
        self.start_time = None
        
        # Signal History für Analytics
        self.recent_signals: List[LiveSignal] = []
        self.recent_alerts: List[RiskAlert] = []
        
        if not WEBSOCKETS_AVAILABLE:
            self.logger.warning("WebSockets not available - streaming will be limited")
        
        if not NUMPY_AVAILABLE:
            self.logger.warning("NumPy not available - some calculations will be limited")
    
    async def initialize(self):
        """Initialisiert Real-time Streaming System"""
        try:
            self.logger.info("Initializing Real-time Streaming Analytics")
            
            # Database Tables für Streaming erstellen
            await self._create_streaming_tables()
            
            # Load streaming configuration
            await self._load_streaming_config()
            
            self.start_time = datetime.utcnow()
            self.logger.info("Real-time Streaming Analytics initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize streaming analytics: {str(e)}")
            raise
    
    async def start_websocket_server(self):
        """Startet WebSocket Server für Live-Streaming"""
        try:
            if not WEBSOCKETS_AVAILABLE:
                self.logger.error("WebSockets not available - cannot start streaming server")
                return
            
            self.logger.info(f"Starting WebSocket server on {self.streaming_config['websocket_host']}:{self.streaming_config['websocket_port']}")
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self.handle_websocket_connection,
                self.streaming_config["websocket_host"],
                self.streaming_config["websocket_port"],
                ping_interval=self.streaming_config["heartbeat_interval_seconds"],
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_streaming = True
            
            # Start background tasks
            asyncio.create_task(self._prediction_loop())
            asyncio.create_task(self._risk_monitoring_loop())
            asyncio.create_task(self._metrics_update_loop())
            
            self.logger.info("WebSocket server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {str(e)}")
            raise
    
    async def stop_websocket_server(self):
        """Stoppt WebSocket Server gracefully"""
        try:
            if self.websocket_server:
                self.logger.info("Stopping WebSocket server...")
                
                self.is_streaming = False
                
                # Close all client connections
                if self.connected_clients:
                    await asyncio.gather(
                        *[client.close() for client in self.connected_clients.copy()],
                        return_exceptions=True
                    )
                
                # Stop server
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
                
                self.logger.info("WebSocket server stopped")
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket server: {str(e)}")
    
    async def handle_websocket_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Behandelt eingehende WebSocket Verbindungen"""
        try:
            # Check connection limit
            if len(self.connected_clients) >= self.streaming_config["max_clients"]:
                await websocket.close(code=1013, reason="Server at capacity")
                return
            
            # Add client
            self.connected_clients.add(websocket)
            client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
            self.logger.info(f"New WebSocket client connected from {client_ip}. Total clients: {len(self.connected_clients)}")
            
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "message": "Connected to ML Analytics Real-time Stream",
                "server_time": datetime.utcnow().isoformat(),
                "tracked_symbols": self.tracked_symbols,
                "update_intervals": {
                    "predictions": self.streaming_config["prediction_interval_seconds"],
                    "risk_checks": self.streaming_config["risk_check_interval_seconds"]
                }
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Handle messages from client
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    self.logger.error(f"Error handling client message: {str(e)}")
                    await self._send_error(websocket, "Message processing error")
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {client_ip} disconnected")
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {str(e)}")
        finally:
            # Remove client
            self.connected_clients.discard(websocket)
            self.logger.info(f"Client removed. Total clients: {len(self.connected_clients)}")
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Behandelt Nachrichten von Clients"""
        try:
            message_type = data.get("type")
            
            if message_type == "subscribe_symbol":
                symbol = data.get("symbol", "").upper()
                if symbol and symbol not in self.tracked_symbols:
                    self.tracked_symbols.append(symbol)
                    response = {
                        "type": "subscription_confirmed",
                        "symbol": symbol,
                        "message": f"Subscribed to {symbol} updates"
                    }
                    await websocket.send(json.dumps(response))
            
            elif message_type == "unsubscribe_symbol":
                symbol = data.get("symbol", "").upper()
                if symbol in self.tracked_symbols:
                    self.tracked_symbols.remove(symbol)
                    response = {
                        "type": "subscription_cancelled",
                        "symbol": symbol,
                        "message": f"Unsubscribed from {symbol} updates"
                    }
                    await websocket.send(json.dumps(response))
            
            elif message_type == "get_current_signals":
                # Send recent signals to client
                recent_signals = [asdict(signal) for signal in self.recent_signals[-10:]]
                response = {
                    "type": "current_signals",
                    "signals": recent_signals,
                    "count": len(recent_signals)
                }
                await websocket.send(json.dumps(response))
            
            elif message_type == "get_metrics":
                # Send streaming metrics
                metrics = asdict(self.streaming_metrics)
                metrics["uptime_seconds"] = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
                response = {
                    "type": "streaming_metrics",
                    "metrics": metrics
                }
                await websocket.send(json.dumps(response))
            
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling client message: {str(e)}")
            await self._send_error(websocket, "Internal server error")
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """Sendet Fehlernachricht an Client"""
        try:
            error_response = {
                "type": "error",
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(error_response))
        except Exception as e:
            self.logger.debug(f"Error sending error message to client: {e}")
    
    async def broadcast_signal(self, signal: LiveSignal):
        """Broadcastet Trading Signal an alle verbundenen Clients"""
        if not self.connected_clients:
            return
        
        try:
            # Prepare signal message
            signal_data = asdict(signal)
            signal_data["timestamp"] = signal.timestamp.isoformat()
            signal_data["signal_type"] = signal.signal_type.value
            
            message = {
                "type": "trading_signal",
                "signal": signal_data
            }
            
            message_json = json.dumps(message)
            
            # Broadcast to all clients
            disconnected_clients = []
            
            for client in self.connected_clients.copy():
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client)
                except Exception as e:
                    self.logger.error(f"Error sending signal to client: {str(e)}")
                    disconnected_clients.append(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.connected_clients.discard(client)
            
            # Add to recent signals
            self.recent_signals.append(signal)
            if len(self.recent_signals) > 100:  # Keep last 100 signals
                self.recent_signals = self.recent_signals[-100:]
                
            self.logger.info(f"Broadcast signal {signal.signal_type.value} for {signal.symbol} to {len(self.connected_clients)} clients")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting signal: {str(e)}")
    
    async def broadcast_risk_alert(self, alert: RiskAlert):
        """Broadcastet Risk Alert an alle verbundenen Clients"""
        if not self.connected_clients:
            return
        
        try:
            # Prepare alert message
            alert_data = asdict(alert)
            alert_data["timestamp"] = alert.timestamp.isoformat()
            alert_data["priority"] = alert.priority.value
            
            message = {
                "type": "risk_alert",
                "alert": alert_data
            }
            
            message_json = json.dumps(message)
            
            # Broadcast to all clients
            disconnected_clients = []
            
            for client in self.connected_clients.copy():
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client)
                except Exception as e:
                    self.logger.error(f"Error sending alert to client: {str(e)}")
                    disconnected_clients.append(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.connected_clients.discard(client)
            
            # Add to recent alerts
            self.recent_alerts.append(alert)
            if len(self.recent_alerts) > 50:  # Keep last 50 alerts
                self.recent_alerts = self.recent_alerts[-50:]
                
            self.logger.info(f"Broadcast {alert.priority.value} risk alert for {alert.symbol} to {len(self.connected_clients)} clients")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting risk alert: {str(e)}")
    
    async def _prediction_loop(self):
        """Background Loop für regelmäßige Predictions"""
        while self.is_streaming:
            try:
                prediction_start = time.time()
                
                for symbol in self.tracked_symbols:
                    try:
                        # Generate predictions for all models
                        signal = await self._generate_live_signal(symbol)
                        
                        if signal and signal.confidence >= self.streaming_config["signal_threshold"]:
                            await self.broadcast_signal(signal)
                            
                            # Update metrics
                            self.streaming_metrics.predictions_generated += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error generating prediction for {symbol}: {str(e)}")
                
                # Calculate and update latency
                prediction_time = (time.time() - prediction_start) * 1000  # ms
                self.streaming_metrics.average_latency_ms = (
                    self.streaming_metrics.average_latency_ms * 0.9 + prediction_time * 0.1
                )
                
                # Update connected clients count
                self.streaming_metrics.connected_clients = len(self.connected_clients)
                
                # Wait for next interval
                await asyncio.sleep(self.streaming_config["prediction_interval_seconds"])
                
            except Exception as e:
                self.logger.error(f"Error in prediction loop: {str(e)}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def _risk_monitoring_loop(self):
        """Background Loop für Risk Monitoring"""
        while self.is_streaming:
            try:
                for symbol in self.tracked_symbols:
                    try:
                        # Perform risk analysis
                        risk_alerts = await self._analyze_symbol_risk(symbol)
                        
                        for alert in risk_alerts:
                            await self.broadcast_risk_alert(alert)
                        
                    except Exception as e:
                        self.logger.error(f"Error in risk analysis for {symbol}: {str(e)}")
                
                # Wait for next interval
                await asyncio.sleep(self.streaming_config["risk_check_interval_seconds"])
                
            except Exception as e:
                self.logger.error(f"Error in risk monitoring loop: {str(e)}")
                await asyncio.sleep(10)  # Wait before retry
    
    async def _metrics_update_loop(self):
        """Background Loop für Metrics Updates"""
        while self.is_streaming:
            try:
                # Update uptime
                if self.start_time:
                    self.streaming_metrics.uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
                
                # Calculate signals per minute (simple approximation)
                if len(self.recent_signals) > 0:
                    recent_time = datetime.utcnow() - timedelta(minutes=1)
                    recent_signals_count = len([s for s in self.recent_signals if s.timestamp > recent_time])
                    self.streaming_metrics.signals_sent_per_minute = recent_signals_count
                
                # Persist metrics to database
                await self._persist_streaming_metrics()
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error updating metrics: {str(e)}")
                await asyncio.sleep(30)
    
    async def _generate_live_signal(self, symbol: str) -> Optional[LiveSignal]:
        """Generiert Live Trading Signal für Symbol"""
        try:
            # Get predictions from multiple models
            predictions = {}
            
            # LSTM prediction
            try:
                lstm_pred = await self.ml_service.lstm_model.predict(symbol)
                predictions["lstm"] = lstm_pred
            except Exception as e:
                self.logger.debug(f"LSTM prediction failed: {e}")
            
            # Multi-horizon predictions (use 7-day for live signals)
            try:
                if 7 in self.ml_service.multi_horizon_models:
                    mh_pred = await self.ml_service.multi_horizon_models[7].predict(symbol)
                    predictions["multi_horizon_7d"] = mh_pred
            except Exception as e:
                self.logger.debug(f"LSTM prediction failed: {e}")
            
            # Ensemble prediction
            try:
                # Get base predictions for meta model
                lstm_pred = await self.ml_service.lstm_model.predict(symbol)
                sentiment_pred = await self.ml_service.sentiment_model.predict(symbol)
                fundamental_pred = await self.ml_service.fundamental_model.predict(symbol)
                
                base_predictions = {
                    'technical': lstm_pred,
                    'sentiment': sentiment_pred,
                    'fundamental': fundamental_pred
                }
                
                ensemble_pred = await self.ml_service.meta_model.predict_ensemble(base_predictions)
                predictions["ensemble"] = ensemble_pred
            except Exception as e:
                self.logger.debug(f"LSTM prediction failed: {e}")
            
            if not predictions:
                return None
            
            # Analyze predictions and generate signal
            signal = self._analyze_predictions_for_signal(symbol, predictions)
            return signal
            
        except Exception as e:
            self.logger.error(f"Error generating live signal for {symbol}: {str(e)}")
            return None
    
    def _analyze_predictions_for_signal(self, symbol: str, predictions: Dict[str, Any]) -> Optional[LiveSignal]:
        """Analysiert Predictions und generiert Trading Signal"""
        try:
            if not predictions:
                return None
            
            # Collect price predictions and confidences
            price_predictions = []
            confidences = []
            
            for model_name, pred_data in predictions.items():
                if isinstance(pred_data, dict):
                    price = pred_data.get("predicted_price")
                    conf = pred_data.get("confidence_score")
                    
                    if price is not None and conf is not None:
                        price_predictions.append(price)
                        confidences.append(conf)
            
            if not price_predictions:
                return None
            
            # Calculate ensemble metrics
            if NUMPY_AVAILABLE:
                avg_price = float(np.mean(price_predictions))
                avg_confidence = float(np.mean(confidences))
                price_std = float(np.std(price_predictions))
            else:
                avg_price = sum(price_predictions) / len(price_predictions)
                avg_confidence = sum(confidences) / len(confidences)
                price_std = 0.0
            
            # Assume current price (mock for demonstration)
            current_price = 150.0  # Would be from real-time data feed
            
            # Calculate return expectation
            expected_return = (avg_price - current_price) / current_price
            
            # Generate signal based on expected return and confidence
            if expected_return > 0.02 and avg_confidence > 0.7:  # >2% gain with high confidence
                signal_type = SignalType.STRONG_BUY
                target_price = avg_price
                stop_loss = current_price * 0.95  # 5% stop loss
            elif expected_return > 0.005 and avg_confidence > 0.6:  # >0.5% gain with good confidence
                signal_type = SignalType.BUY
                target_price = avg_price
                stop_loss = current_price * 0.98  # 2% stop loss
            elif expected_return < -0.02 and avg_confidence > 0.7:  # <-2% loss with high confidence
                signal_type = SignalType.STRONG_SELL
                target_price = avg_price
                stop_loss = current_price * 1.05  # 5% stop loss for short
            elif expected_return < -0.005 and avg_confidence > 0.6:  # <-0.5% loss with good confidence
                signal_type = SignalType.SELL
                target_price = avg_price
                stop_loss = current_price * 1.02  # 2% stop loss for short
            else:
                signal_type = SignalType.HOLD
                target_price = None
                stop_loss = None
            
            # Create signal
            signal = LiveSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=avg_confidence,
                price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                horizon_days=7,
                model_source="ensemble_live",
                timestamp=datetime.utcnow(),
                metadata={
                    "expected_return": expected_return,
                    "price_std": price_std,
                    "models_used": list(predictions.keys()),
                    "prediction_count": len(price_predictions)
                }
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error analyzing predictions for signal: {str(e)}")
            return None
    
    async def _analyze_symbol_risk(self, symbol: str) -> List[RiskAlert]:
        """Analysiert Risiken für Symbol"""
        alerts = []
        
        try:
            # Mock risk analysis - in real system would use market data
            current_price = 150.0  # From real-time data
            volatility = 0.25  # Historical volatility
            
            # Check volatility risk
            if volatility > 0.4:  # >40% volatility
                alert = RiskAlert(
                    alert_id=f"{symbol}_volatility_{int(time.time())}",
                    symbol=symbol,
                    alert_type="high_volatility",
                    priority=AlertPriority.HIGH,
                    message=f"{symbol} showing high volatility ({volatility:.1%})",
                    current_value=volatility,
                    threshold_value=0.4,
                    timestamp=datetime.utcnow(),
                    action_required=True
                )
                alerts.append(alert)
            
            # Check price movement risk (mock)
            price_change_5min = 0.03  # 3% price change in 5 minutes
            if abs(price_change_5min) > 0.02:  # >2% move in 5 minutes
                priority = AlertPriority.CRITICAL if abs(price_change_5min) > 0.05 else AlertPriority.HIGH
                alert = RiskAlert(
                    alert_id=f"{symbol}_price_move_{int(time.time())}",
                    symbol=symbol,
                    alert_type="rapid_price_movement",
                    priority=priority,
                    message=f"{symbol} rapid price movement: {price_change_5min:+.1%} in 5 minutes",
                    current_value=abs(price_change_5min),
                    threshold_value=0.02,
                    timestamp=datetime.utcnow(),
                    action_required=True
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error analyzing risk for {symbol}: {str(e)}")
            return []
    
    async def get_streaming_status(self) -> Dict[str, Any]:
        """Returns Streaming System Status"""
        try:
            if self.start_time:
                uptime = (datetime.utcnow() - self.start_time).total_seconds()
            else:
                uptime = 0
            
            return {
                "streaming_active": self.is_streaming,
                "websocket_server_running": self.websocket_server is not None,
                "connected_clients": len(self.connected_clients),
                "tracked_symbols": self.tracked_symbols,
                "metrics": {
                    "uptime_seconds": uptime,
                    "predictions_generated": self.streaming_metrics.predictions_generated,
                    "signals_sent_per_minute": self.streaming_metrics.signals_sent_per_minute,
                    "average_latency_ms": self.streaming_metrics.average_latency_ms,
                    "recent_signals_count": len(self.recent_signals),
                    "recent_alerts_count": len(self.recent_alerts)
                },
                "configuration": self.streaming_config
            }
            
        except Exception as e:
            self.logger.error(f"Error getting streaming status: {str(e)}")
            return {"error": str(e)}
    
    # Database Helper Methods
    
    async def _create_streaming_tables(self):
        """Erstellt Streaming-spezifische Database Tables"""
        try:
            async with self.database_pool.acquire() as conn:
                # Streaming Metrics Table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS streaming_metrics (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        connected_clients INTEGER,
                        signals_per_minute FLOAT,
                        predictions_generated INTEGER,
                        average_latency_ms FLOAT,
                        error_rate FLOAT,
                        uptime_seconds FLOAT
                    )
                """)
                
                # Live Signals Table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS live_signals (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(10) NOT NULL,
                        signal_type VARCHAR(20) NOT NULL,
                        confidence FLOAT NOT NULL,
                        price FLOAT NOT NULL,
                        target_price FLOAT,
                        stop_loss FLOAT,
                        horizon_days INTEGER,
                        model_source VARCHAR(50),
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        metadata JSONB
                    )
                """)
                
                # Risk Alerts Table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS risk_alerts (
                        id SERIAL PRIMARY KEY,
                        alert_id VARCHAR(100) UNIQUE,
                        symbol VARCHAR(10) NOT NULL,
                        alert_type VARCHAR(50) NOT NULL,
                        priority VARCHAR(20) NOT NULL,
                        message TEXT,
                        current_value FLOAT,
                        threshold_value FLOAT,
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        action_required BOOLEAN DEFAULT FALSE,
                        resolved BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Create indexes
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_live_signals_symbol_timestamp ON live_signals(symbol, timestamp)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_alerts_symbol_timestamp ON risk_alerts(symbol, timestamp)")
                
        except Exception as e:
            self.logger.error(f"Failed to create streaming tables: {str(e)}")
            raise
    
    async def _load_streaming_config(self):
        """Lädt Streaming Configuration"""
        # Placeholder - könnte aus Database oder Config-File geladen werden
        pass
    
    async def _persist_streaming_metrics(self):
        """Persistiert Streaming Metrics in Database"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO streaming_metrics 
                    (connected_clients, signals_per_minute, predictions_generated, 
                     average_latency_ms, error_rate, uptime_seconds)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                self.streaming_metrics.connected_clients,
                self.streaming_metrics.signals_sent_per_minute,
                self.streaming_metrics.predictions_generated,
                self.streaming_metrics.average_latency_ms,
                self.streaming_metrics.error_rate,
                self.streaming_metrics.uptime_seconds)
        except Exception as e:
            self.logger.error(f"Failed to persist streaming metrics: {str(e)}")

# Export
__all__ = ['RealTimeStreamingAnalytics', 'LiveSignal', 'RiskAlert', 'SignalType', 'AlertPriority']