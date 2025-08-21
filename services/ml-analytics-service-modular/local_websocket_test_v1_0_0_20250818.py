#!/usr/bin/env python3
"""
Local WebSocket Test Client für Streaming Demo
===============================================

Testet die lokale Streaming Demo WebSocket-Verbindung.

Author: Claude Code & AI Development Team  
Version: 1.0.0
Date: 2025-08-18
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalWebSocketClient:
    """Local WebSocket Test Client"""
    
    def __init__(self):
        self.websocket_url = "ws://localhost:8022"
        self.websocket = None
        self.is_connected = False
        
    async def connect(self):
        """Connect to local WebSocket server"""
        try:
            logger.info(f"Connecting to {self.websocket_url}")
            self.websocket = await websockets.connect(self.websocket_url)
            self.is_connected = True
            logger.info("Successfully connected to streaming demo server!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            return False
    
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        if not self.is_connected:
            logger.error("Not connected to server")
            return
        
        try:
            logger.info("Listening for real-time trading signals and price updates...")
            logger.info("=" * 60)
            
            signal_count = 0
            price_update_count = 0
            alert_count = 0
            
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    if message_type == "welcome":
                        logger.info(f"📡 Welcome: {data.get('message')}")
                        logger.info(f"   Tracked Symbols: {', '.join(data.get('tracked_symbols', []))}")
                        
                    elif message_type == "price_update":
                        price_update_count += 1
                        prices = data.get("prices", {})
                        timestamp = data.get("timestamp", "")
                        
                        if price_update_count % 3 == 0:  # Show every 3rd update to reduce spam
                            logger.info(f"💹 Price Update #{price_update_count} at {timestamp[:19]}")
                            for symbol, price in prices.items():
                                logger.info(f"   {symbol}: ${price}")
                        
                    elif message_type == "trading_signal":
                        signal_count += 1
                        signal = data.get("signal", {})
                        
                        signal_type = signal.get("signal_type", "")
                        symbol = signal.get("symbol", "")
                        confidence = signal.get("confidence", 0)
                        price = signal.get("price", 0)
                        target = signal.get("target_price", 0)
                        horizon = signal.get("horizon_days", 0)
                        model_source = signal.get("model_source", "")
                        
                        # Color coding for signal types
                        signal_emoji = {
                            "STRONG_BUY": "🚀",
                            "BUY": "📈", 
                            "HOLD": "🔄",
                            "SELL": "📉",
                            "STRONG_SELL": "🔻"
                        }.get(signal_type, "❓")
                        
                        logger.info(f"{signal_emoji} TRADING SIGNAL #{signal_count}")
                        logger.info(f"   Symbol: {symbol} | Signal: {signal_type}")
                        logger.info(f"   Confidence: {confidence:.1%} | Horizon: {horizon} days")
                        logger.info(f"   Current: ${price} | Target: ${target}")
                        logger.info(f"   Model: {model_source}")
                        
                    elif message_type == "risk_alert":
                        alert_count += 1
                        alert = data.get("alert", {})
                        
                        risk_level = alert.get("risk_level", "")
                        symbol = alert.get("symbol", "")
                        message_text = alert.get("message", "")
                        current_price = alert.get("current_price", 0)
                        
                        risk_emoji = {
                            "LOW": "🟢",
                            "MEDIUM": "🟡", 
                            "HIGH": "🟠",
                            "CRITICAL": "🔴"
                        }.get(risk_level, "⚪")
                        
                        logger.info(f"{risk_emoji} RISK ALERT #{alert_count}")
                        logger.info(f"   {symbol}: {message_text}")
                        logger.info(f"   Current Price: ${current_price}")
                        logger.info(f"   Risk Level: {risk_level}")
                        
                    else:
                        logger.info(f"📨 Unknown message type: {message_type}")
                        
                    # Add separator for readability
                    if message_type in ["trading_signal", "risk_alert"]:
                        logger.info("-" * 40)
                        
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON message")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening for messages: {str(e)}")
        finally:
            self.is_connected = False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from server")


async def main():
    """Main test function"""
    client = LocalWebSocketClient()
    
    try:
        logger.info("=" * 60)
        logger.info("LOCAL WEBSOCKET TEST CLIENT - Phase 7 Demo")
        logger.info("=" * 60)
        
        # Connect to server
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to streaming demo server")
            logger.info("Make sure the streaming demo is running!")
            return
        
        # Listen for messages
        await client.listen_for_messages()
        
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Client error: {str(e)}")
    finally:
        await client.disconnect()
        logger.info("Local WebSocket test completed")


if __name__ == "__main__":
    asyncio.run(main())