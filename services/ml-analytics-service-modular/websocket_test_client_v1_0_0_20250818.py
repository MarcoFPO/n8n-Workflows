#!/usr/bin/env python3
"""
WebSocket Test Client v1.0.0
Test Client für Real-time Streaming Analytics

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketTestClient:
    """Test Client für ML Analytics WebSocket Stream"""
    
    def __init__(self, server_url: str = "ws://10.1.1.174:8022"):
        self.server_url = server_url
        self.websocket = None
        self.is_running = False
    
    async def connect(self):
        """Verbindet zum WebSocket Server"""
        try:
            if not WEBSOCKETS_AVAILABLE:
                logger.error("WebSockets not available - please install websockets package")
                return
            
            logger.info(f"Connecting to {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.is_running = True
            logger.info("Connected to WebSocket server")
            
            # Start listening task
            asyncio.create_task(self.listen_for_messages())
            
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
    
    async def disconnect(self):
        """Trennt WebSocket Verbindung"""
        try:
            if self.websocket:
                self.is_running = False
                await self.websocket.close()
                logger.info("Disconnected from WebSocket server")
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
    
    async def listen_for_messages(self):
        """Hört auf eingehende WebSocket Messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {str(e)}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening for messages: {str(e)}")
    
    async def handle_message(self, data: Dict[str, Any]):
        """Behandelt eingehende Messages"""
        message_type = data.get("type", "unknown")
        
        if message_type == "welcome":
            logger.info("Received welcome message")
            logger.info(f"Server time: {data.get('server_time')}")
            logger.info(f"Tracked symbols: {data.get('tracked_symbols')}")
            
        elif message_type == "trading_signal":
            signal = data.get("signal", {})
            logger.info(f"🚨 TRADING SIGNAL: {signal.get('symbol')} - {signal.get('signal_type')} (confidence: {signal.get('confidence', 0):.2f})")
            logger.info(f"   Price: ${signal.get('price', 0):.2f}, Target: ${signal.get('target_price', 0):.2f}")
            
        elif message_type == "risk_alert":
            alert = data.get("alert", {})
            priority = alert.get("priority", "unknown").upper()
            logger.warning(f"⚠️  RISK ALERT [{priority}]: {alert.get('symbol')} - {alert.get('message')}")
            
        elif message_type == "error":
            logger.error(f"Server error: {data.get('message')}")
            
        else:
            logger.info(f"Received {message_type}: {data}")
    
    async def send_message(self, message: Dict[str, Any]):
        """Sendet Message an Server"""
        try:
            if self.websocket:
                await self.websocket.send(json.dumps(message))
                logger.info(f"Sent: {message}")
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
    
    async def subscribe_symbol(self, symbol: str):
        """Abonniert Symbol für Updates"""
        message = {
            "type": "subscribe_symbol",
            "symbol": symbol
        }
        await self.send_message(message)
    
    async def unsubscribe_symbol(self, symbol: str):
        """Kündigt Symbol-Abo"""
        message = {
            "type": "unsubscribe_symbol",
            "symbol": symbol
        }
        await self.send_message(message)
    
    async def get_current_signals(self):
        """Holt aktuelle Signals"""
        message = {
            "type": "get_current_signals"
        }
        await self.send_message(message)
    
    async def get_metrics(self):
        """Holt Streaming Metrics"""
        message = {
            "type": "get_metrics"
        }
        await self.send_message(message)

async def main():
    """Test Client Main Function"""
    client = WebSocketTestClient()
    
    try:
        await client.connect()
        
        # Wait a bit for connection
        await asyncio.sleep(2)
        
        # Test verschiedene Commands
        logger.info("Testing WebSocket commands...")
        
        await client.get_metrics()
        await asyncio.sleep(1)
        
        await client.get_current_signals()
        await asyncio.sleep(1)
        
        await client.subscribe_symbol("NVDA")
        await asyncio.sleep(1)
        
        # Keep connection alive to receive real-time updates
        logger.info("Listening for real-time updates... Press Ctrl+C to exit")
        while client.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Test client error: {str(e)}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    if not WEBSOCKETS_AVAILABLE:
        print("WebSockets not available. Install with: pip install websockets")
    else:
        asyncio.run(main())