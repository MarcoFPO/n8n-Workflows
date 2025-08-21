#!/usr/bin/env python3
"""
Streaming Analytics Demo - Phase 7 Demonstration
===================================================

Lokale Demo der Real-time Streaming Analytics Funktionalität ohne vollständige Infrastruktur.
Simuliert Live-Trading Signals und WebSocket-Broadcasting für AAPL.

Author: Claude Code & AI Development Team
Version: 1.0.0
Date: 2025-08-18
"""

import asyncio
import websockets
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Set, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import numpy as np

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading Signal Types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"

class RiskLevel(Enum):
    """Risk Alert Levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class LiveSignal:
    """Live Trading Signal"""
    symbol: str
    signal_type: SignalType
    confidence: float
    price: float
    target_price: float
    stop_loss: float
    horizon_days: int
    model_source: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class RiskAlert:
    """Risk Management Alert"""
    symbol: str
    risk_level: RiskLevel
    message: str
    current_price: float
    risk_metrics: Dict[str, float]
    timestamp: datetime

class StreamingDemo:
    """Demo-Version der Real-time Streaming Analytics"""
    
    def __init__(self):
        self.websocket_port = 8022
        self.connected_clients: Set = set()
        self.is_running = False
        self.recent_signals: List[LiveSignal] = []
        self.recent_alerts: List[RiskAlert] = []
        
        # Simulated market data
        self.current_prices = {
            "AAPL": 175.50,
            "MSFT": 335.20,
            "GOOGL": 138.40,
            "TSLA": 245.80
        }
        
        # Demo configuration
        self.symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
        self.signal_interval = 15  # seconds
        self.price_update_interval = 5  # seconds
        
    async def start_demo_server(self):
        """Start WebSocket Demo Server"""
        logger.info(f"Starting streaming demo server on port {self.websocket_port}")
        
        async def handle_client(websocket, path):
            """Handle new WebSocket client connection"""
            self.connected_clients.add(websocket)
            client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
            logger.info(f"New client connected from {client_ip} (Total: {len(self.connected_clients)})")
            
            try:
                # Send welcome message
                welcome_msg = {
                    "type": "welcome",
                    "message": "Connected to ML Analytics Streaming Demo",
                    "timestamp": datetime.utcnow().isoformat(),
                    "tracked_symbols": self.symbols
                }
                await websocket.send(json.dumps(welcome_msg))
                
                # Keep connection alive
                await websocket.wait_closed()
                
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client {client_ip} disconnected")
            except Exception as e:
                logger.error(f"Client handling error: {str(e)}")
            finally:
                self.connected_clients.discard(websocket)
                logger.info(f"Client removed (Remaining: {len(self.connected_clients)})")
        
        # Start WebSocket server
        server = await websockets.serve(handle_client, "0.0.0.0", self.websocket_port)
        self.is_running = True
        logger.info(f"WebSocket server started on ws://0.0.0.0:{self.websocket_port}")
        
        # Start background tasks
        asyncio.create_task(self.price_update_loop())
        asyncio.create_task(self.signal_generation_loop())
        asyncio.create_task(self.risk_monitoring_loop())
        
        # Keep server running
        await server.wait_closed()
    
    async def price_update_loop(self):
        """Simulate real-time price updates"""
        while self.is_running:
            try:
                for symbol in self.symbols:
                    # Simulate price movement
                    change_percent = random.uniform(-2.0, 2.0)  # ±2% movement
                    self.current_prices[symbol] *= (1 + change_percent / 100)
                    self.current_prices[symbol] = round(self.current_prices[symbol], 2)
                
                # Broadcast price updates
                price_update = {
                    "type": "price_update",
                    "prices": self.current_prices,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await self.broadcast_message(price_update)
                await asyncio.sleep(self.price_update_interval)
                
            except Exception as e:
                logger.error(f"Price update loop error: {str(e)}")
                await asyncio.sleep(5)
    
    async def signal_generation_loop(self):
        """Generate synthetic trading signals"""
        while self.is_running:
            try:
                # Generate random signal
                symbol = random.choice(self.symbols)
                signal = await self.generate_synthetic_signal(symbol)
                
                # Store and broadcast
                self.recent_signals.append(signal)
                if len(self.recent_signals) > 50:  # Keep last 50 signals
                    self.recent_signals.pop(0)
                
                await self.broadcast_signal(signal)
                await asyncio.sleep(self.signal_interval)
                
            except Exception as e:
                logger.error(f"Signal generation loop error: {str(e)}")
                await asyncio.sleep(10)
    
    async def risk_monitoring_loop(self):
        """Monitor risk levels and generate alerts"""
        while self.is_running:
            try:
                # Check for high volatility or unusual price movements
                for symbol in self.symbols:
                    if random.random() < 0.1:  # 10% chance of risk alert
                        alert = await self.generate_risk_alert(symbol)
                        
                        self.recent_alerts.append(alert)
                        if len(self.recent_alerts) > 20:  # Keep last 20 alerts
                            self.recent_alerts.pop(0)
                        
                        await self.broadcast_risk_alert(alert)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Risk monitoring loop error: {str(e)}")
                await asyncio.sleep(30)
    
    async def generate_synthetic_signal(self, symbol: str) -> LiveSignal:
        """Generate realistic trading signal"""
        current_price = self.current_prices[symbol]
        
        # Generate signal type based on simulated ML prediction
        confidence = random.uniform(0.6, 0.95)
        
        if confidence > 0.85:
            signal_type = random.choice([SignalType.STRONG_BUY, SignalType.STRONG_SELL])
        elif confidence > 0.75:
            signal_type = random.choice([SignalType.BUY, SignalType.SELL])
        else:
            signal_type = SignalType.HOLD
        
        # Calculate target and stop loss
        if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            target_multiplier = random.uniform(1.02, 1.08)  # 2-8% upside
            stop_multiplier = random.uniform(0.95, 0.98)   # 2-5% downside
        elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            target_multiplier = random.uniform(0.92, 0.98)  # 2-8% downside
            stop_multiplier = random.uniform(1.02, 1.05)   # 2-5% upside
        else:  # HOLD
            target_multiplier = random.uniform(0.99, 1.01)
            stop_multiplier = random.uniform(0.97, 1.03)
        
        horizon_days = random.choice([7, 30, 150, 365])
        model_source = f"ensemble_horizon_{horizon_days}d"
        
        return LiveSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            target_price=round(current_price * target_multiplier, 2),
            stop_loss=round(current_price * stop_multiplier, 2),
            horizon_days=horizon_days,
            model_source=model_source,
            timestamp=datetime.utcnow(),
            metadata={
                "volatility": random.uniform(0.15, 0.45),
                "volume_spike": random.uniform(0.8, 2.5),
                "technical_score": random.uniform(-1.0, 1.0),
                "sentiment_score": random.uniform(-1.0, 1.0),
                "demo_mode": True
            }
        )
    
    async def generate_risk_alert(self, symbol: str) -> RiskAlert:
        """Generate risk management alert"""
        current_price = self.current_prices[symbol]
        risk_level = random.choice(list(RiskLevel))
        
        risk_messages = {
            RiskLevel.LOW: f"Minor volatility detected in {symbol}",
            RiskLevel.MEDIUM: f"Elevated risk levels for {symbol} - monitor position sizing",
            RiskLevel.HIGH: f"High volatility warning for {symbol} - consider defensive positions",
            RiskLevel.CRITICAL: f"CRITICAL: Extreme price movement in {symbol} - immediate attention required"
        }
        
        return RiskAlert(
            symbol=symbol,
            risk_level=risk_level,
            message=risk_messages[risk_level],
            current_price=current_price,
            risk_metrics={
                "var_95": random.uniform(0.02, 0.15),
                "sharpe_ratio": random.uniform(-0.5, 2.0),
                "max_drawdown": random.uniform(0.05, 0.25),
                "volatility": random.uniform(0.15, 0.60)
            },
            timestamp=datetime.utcnow()
        )
    
    async def broadcast_signal(self, signal: LiveSignal):
        """Broadcast trading signal to all connected clients"""
        if not self.connected_clients:
            return
        
        try:
            signal_data = asdict(signal)
            signal_data["timestamp"] = signal.timestamp.isoformat()
            signal_data["signal_type"] = signal.signal_type.value
            
            message = {
                "type": "trading_signal",
                "signal": signal_data
            }
            
            # Send to all connected clients
            disconnected_clients = set()
            for client in self.connected_clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"Error sending signal to client: {str(e)}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.connected_clients.discard(client)
            
            if disconnected_clients:
                logger.info(f"Removed {len(disconnected_clients)} disconnected clients")
            
            logger.info(f"Broadcasted {signal.signal_type.value} signal for {signal.symbol} "
                       f"to {len(self.connected_clients)} clients")
            
        except Exception as e:
            logger.error(f"Signal broadcast error: {str(e)}")
    
    async def broadcast_risk_alert(self, alert: RiskAlert):
        """Broadcast risk alert to all connected clients"""
        if not self.connected_clients:
            return
        
        try:
            alert_data = asdict(alert)
            alert_data["timestamp"] = alert.timestamp.isoformat()
            alert_data["risk_level"] = alert.risk_level.value
            
            message = {
                "type": "risk_alert",
                "alert": alert_data
            }
            
            # Send to all connected clients
            disconnected_clients = set()
            for client in self.connected_clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"Error sending alert to client: {str(e)}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.connected_clients.discard(client)
            
            logger.info(f"Broadcasted {alert.risk_level.value} risk alert for {alert.symbol} "
                       f"to {len(self.connected_clients)} clients")
            
        except Exception as e:
            logger.error(f"Risk alert broadcast error: {str(e)}")
    
    async def broadcast_message(self, message: dict):
        """Broadcast generic message to all clients"""
        if not self.connected_clients:
            return
        
        try:
            disconnected_clients = set()
            for client in self.connected_clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
                except Exception as e:
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.connected_clients.discard(client)
            
        except Exception as e:
            logger.error(f"Message broadcast error: {str(e)}")
    
    def get_status(self) -> dict:
        """Get demo streaming status"""
        return {
            "demo_mode": True,
            "websocket_server_running": self.is_running,
            "websocket_port": self.websocket_port,
            "connected_clients": len(self.connected_clients),
            "tracked_symbols": self.symbols,
            "recent_signals_count": len(self.recent_signals),
            "recent_alerts_count": len(self.recent_alerts),
            "current_prices": self.current_prices,
            "signal_interval_seconds": self.signal_interval,
            "price_update_interval_seconds": self.price_update_interval
        }


async def main():
    """Start Streaming Demo"""
    demo = StreamingDemo()
    
    try:
        logger.info("=" * 60)
        logger.info("ML Analytics - Phase 7 Streaming Demo")
        logger.info("=" * 60)
        logger.info("Starting real-time trading signals simulation...")
        logger.info(f"WebSocket Server: ws://localhost:{demo.websocket_port}")
        logger.info("Tracked Symbols: " + ", ".join(demo.symbols))
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        await demo.start_demo_server()
        
    except KeyboardInterrupt:
        logger.info("Demo stopped by user")
        demo.is_running = False
    except Exception as e:
        logger.error(f"Demo error: {str(e)}")
    finally:
        logger.info("Streaming demo terminated")


if __name__ == "__main__":
    asyncio.run(main())