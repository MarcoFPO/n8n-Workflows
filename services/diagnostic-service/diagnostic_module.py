#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic Module für Event-Bus Monitoring und Testing
Kann alle Bus-Nachrichten mitlesen und Test-Nachrichten an Module senden
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
import structlog
import sys
import os
from collections import defaultdict, deque

# Event-Bus System importieren
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from event_bus import EventBusConnector, Event, EventType, EventBusConfig
from backend_base_module import BackendBaseModule

logger = structlog.get_logger(__name__)


class EventCapture:
    """Event capture and storage for diagnostics"""
    
    def __init__(self, max_events: int = 1000):
        self.max_events = max_events
        self.captured_events = deque(maxlen=max_events)
        self.event_counts = defaultdict(int)
        self.source_counts = defaultdict(int)
        self.error_events = deque(maxlen=100)
        
    def capture_event(self, event: Event, metadata: Dict[str, Any] = None):
        """Capture an event with metadata"""
        capture_data = {
            'event': event.to_dict(),
            'captured_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.captured_events.append(capture_data)
        self.event_counts[event.event_type] += 1
        self.source_counts[event.source] += 1
        
        # Check for potential error patterns
        if self._is_error_event(event):
            self.error_events.append(capture_data)
    
    def _is_error_event(self, event: Event) -> bool:
        """Detect if event indicates an error condition"""
        error_indicators = [
            'error', 'fail', 'exception', 'timeout', 'disconnect'
        ]
        event_data_str = json.dumps(event.data).lower()
        return any(indicator in event_data_str for indicator in error_indicators)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event capture statistics"""
        return {
            'total_events': len(self.captured_events),
            'event_type_counts': dict(self.event_counts),
            'source_counts': dict(self.source_counts),
            'error_count': len(self.error_events),
            'capture_window': f"{self.max_events} events"
        }


class MessageGenerator:
    """Generate test messages for modules"""
    
    def __init__(self):
        self.test_counter = 0
    
    def generate_test_event(self, event_type: str, target_module: str, 
                          custom_data: Dict[str, Any] = None) -> Event:
        """Generate a test event"""
        self.test_counter += 1
        
        base_data = {
            'test_id': f"diagnostic_test_{self.test_counter}",
            'generated_by': 'diagnostic_module',
            'target_module': target_module,
            'timestamp': datetime.now().isoformat()
        }
        
        if custom_data:
            base_data.update(custom_data)
        
        return Event(
            event_type=event_type,
            stream_id=f"diagnostic-test-{self.test_counter}",
            data=base_data,
            source="diagnostic_module",
            correlation_id=str(uuid.uuid4())
        )
    
    def generate_analysis_test(self, symbol: str = "AAPL") -> Event:
        """Generate test analysis event"""
        return self.generate_test_event(
            EventType.ANALYSIS_STATE_CHANGED.value,
            "analysis_module",
            {
                'symbol': symbol,
                'score': 15.5,
                'recommendation': 'TEST_BUY',
                'confidence': 0.85,
                'indicators': {
                    'rsi': 65.2,
                    'macd': 0.12,
                    'sma_20': 150.5
                }
            }
        )
    
    def generate_trading_test(self, order_type: str = "TEST_MARKET") -> Event:
        """Generate test trading event"""
        return self.generate_test_event(
            EventType.TRADING_STATE_CHANGED.value,
            "order_module",
            {
                'order_id': f"test_order_{self.test_counter}",
                'order_type': order_type,
                'symbol': 'AAPL',
                'quantity': 10,
                'price': 150.0,
                'status': 'TEST_PENDING'
            }
        )
    
    def generate_portfolio_test(self) -> Event:
        """Generate test portfolio event"""
        return self.generate_test_event(
            EventType.PORTFOLIO_STATE_CHANGED.value,
            "portfolio_module",
            {
                'portfolio_value': 10000.0,
                'daily_return': 2.5,
                'positions': [
                    {'symbol': 'AAPL', 'shares': 10, 'value': 1500.0},
                    {'symbol': 'GOOGL', 'shares': 5, 'value': 1250.0}
                ]
            }
        )


class DiagnosticModule(BackendBaseModule):
    """
    Diagnostic Module für Event-Bus Monitoring und Testing
    Kann alle Nachrichten mitlesen und Test-Nachrichten senden
    """
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("diagnostic", event_bus)
        self.event_capture = EventCapture(max_events=2000)
        self.message_generator = MessageGenerator()
        self.monitoring_active = False
        self.subscribed_events: Set[str] = set()
        self.test_results = {}
        
    async def _initialize_module(self) -> bool:
        """Initialize diagnostic module"""
        try:
            self.logger.info("🔧 Initializing Diagnostic Module...")
            
            # Test Event-Bus connectivity
            await self._test_event_bus_connectivity()
            
            # Subscribe to all known event types for monitoring
            await self._subscribe_to_all_events()
            
            self.monitoring_active = True
            self.logger.info("✅ Diagnostic module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Diagnostic initialization failed: {e}")
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to events for monitoring"""
        # This will be called by _subscribe_to_all_events
        pass
    
    async def _subscribe_to_all_events(self):
        """Subscribe to all known event types for comprehensive monitoring"""
        all_event_types = [
            EventType.ANALYSIS_STATE_CHANGED,
            EventType.PORTFOLIO_STATE_CHANGED,
            EventType.TRADING_STATE_CHANGED,
            EventType.INTELLIGENCE_TRIGGERED,
            EventType.DATA_SYNCHRONIZED,
            EventType.SYSTEM_ALERT_RAISED,
            EventType.USER_INTERACTION_LOGGED,
            EventType.CONFIG_UPDATED
        ]
        
        for event_type in all_event_types:
            await self.subscribe_to_event(event_type, self._monitor_event)
            self.subscribed_events.add(event_type.value)
            
        self.logger.info(f"📡 Subscribed to {len(all_event_types)} event types for monitoring")
    
    async def _monitor_event(self, event: Event):
        """Monitor and capture all events"""
        if not self.monitoring_active:
            return
            
        # Capture the event
        self.event_capture.capture_event(event, {
            'received_at': datetime.now().isoformat(),
            'diagnostic_module_active': True
        })
        
        self.logger.debug(
            "📨 Event captured",
            event_type=event.event_type,
            source=event.source,
            stream_id=event.stream_id
        )
    
    async def _test_event_bus_connectivity(self):
        """Test Event-Bus connectivity"""
        try:
            # Send a test event to ourselves
            test_event = Event(
                event_type="diagnostic.connectivity.test",
                stream_id="diagnostic-connectivity",
                data={'test': 'connectivity', 'timestamp': datetime.now().isoformat()},
                source="diagnostic_module"
            )
            
            await self.event_bus.publish(test_event)
            self.logger.info("🔌 Event-Bus connectivity test successful")
            
        except Exception as e:
            self.logger.error(f"🔌 Event-Bus connectivity test failed: {e}")
            raise
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process diagnostic commands and requests"""
        try:
            command = data.get('command')
            
            if command == 'get_statistics':
                return await self._get_monitoring_statistics()
            elif command == 'get_recent_events':
                return await self._get_recent_events(data.get('limit', 50))
            elif command == 'send_test_message':
                return await self._send_test_message(data)
            elif command == 'test_module_communication':
                return await self._test_module_communication(data.get('target_module'))
            elif command == 'get_system_health':
                return await self._get_system_health()
            else:
                return {
                    'success': False,
                    'error': f'Unknown command: {command}'
                }
                
        except Exception as e:
            self.logger.error(f"Diagnostic processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        stats = self.event_capture.get_statistics()
        stats.update({
            'monitoring_active': self.monitoring_active,
            'subscribed_events': list(self.subscribed_events),
            'diagnostic_uptime': (datetime.now() - datetime.now()).total_seconds()  # Placeholder
        })
        
        return {
            'success': True,
            'data': stats
        }
    
    async def _get_recent_events(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent captured events"""
        recent_events = list(self.event_capture.captured_events)[-limit:]
        
        return {
            'success': True,
            'data': {
                'events': recent_events,
                'count': len(recent_events),
                'total_captured': len(self.event_capture.captured_events)
            }
        }
    
    async def _send_test_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a test message to a specific module"""
        try:
            message_type = data.get('message_type', 'analysis')
            target_module = data.get('target_module')
            custom_data = data.get('custom_data', {})
            
            # Generate appropriate test event
            if message_type == 'analysis':
                test_event = self.message_generator.generate_analysis_test(
                    custom_data.get('symbol', 'AAPL')
                )
            elif message_type == 'trading':
                test_event = self.message_generator.generate_trading_test(
                    custom_data.get('order_type', 'TEST_MARKET')
                )
            elif message_type == 'portfolio':
                test_event = self.message_generator.generate_portfolio_test()
            else:
                # Custom event
                event_type = data.get('event_type', EventType.DATA_SYNCHRONIZED.value)
                test_event = self.message_generator.generate_test_event(
                    event_type, target_module or 'unknown', custom_data
                )
            
            # Send the test event
            await self.event_bus.publish(test_event)
            
            # Store test result for tracking
            test_id = test_event.data.get('test_id')
            self.test_results[test_id] = {
                'sent_at': datetime.now().isoformat(),
                'event': test_event.to_dict(),
                'status': 'sent'
            }
            
            self.logger.info(
                "🧪 Test message sent",
                test_id=test_id,
                event_type=test_event.event_type,
                target=target_module
            )
            
            return {
                'success': True,
                'data': {
                    'test_id': test_id,
                    'event_sent': test_event.to_dict(),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send test message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _test_module_communication(self, target_module: str) -> Dict[str, Any]:
        """Test communication with a specific module"""
        try:
            # Send ping-style test to target module
            ping_event = Event(
                event_type="diagnostic.ping",
                stream_id=f"diagnostic-ping-{target_module}",
                data={
                    'ping': True,
                    'target_module': target_module,
                    'timestamp': datetime.now().isoformat(),
                    'diagnostic_correlation_id': str(uuid.uuid4())
                },
                source="diagnostic_module"
            )
            
            await self.publish_event(ping_event)
            
            return {
                'success': True,
                'data': {
                    'ping_sent': True,
                    'target_module': target_module,
                    'ping_event': ping_event.to_dict()
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health based on captured events"""
        try:
            stats = self.event_capture.get_statistics()
            recent_errors = len(self.event_capture.error_events)
            
            # Simple health assessment
            health_score = 100
            if recent_errors > 10:
                health_score -= 30
            if stats['total_events'] == 0:
                health_score -= 50
            
            health_status = "healthy" if health_score > 80 else \
                           "degraded" if health_score > 50 else "unhealthy"
            
            return {
                'success': True,
                'data': {
                    'health_status': health_status,
                    'health_score': health_score,
                    'total_events': stats['total_events'],
                    'error_events': recent_errors,
                    'active_sources': len(stats['source_counts']),
                    'event_types_seen': len(stats['event_type_counts']),
                    'monitoring_active': self.monitoring_active
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def start_monitoring(self):
        """Start event monitoring"""
        self.monitoring_active = True
        self.logger.info("📡 Event monitoring started")
    
    async def stop_monitoring(self):
        """Stop event monitoring"""
        self.monitoring_active = False
        self.logger.info("📡 Event monitoring stopped")
    
    async def clear_captured_events(self):
        """Clear captured events buffer"""
        self.event_capture.captured_events.clear()
        self.event_capture.event_counts.clear()
        self.event_capture.source_counts.clear()
        self.event_capture.error_events.clear()
        self.logger.info("🗑️ Captured events buffer cleared")


if __name__ == "__main__":
    # Test initialization
    async def test_diagnostic():
        config = EventBusConfig()
        event_bus = EventBusConnector("diagnostic_test", config)
        
        diagnostic = DiagnosticModule(event_bus)
        success = await diagnostic._initialize_module()
        
        if success:
            print("✅ Diagnostic module test successful")
        else:
            print("❌ Diagnostic module test failed")
    
    asyncio.run(test_diagnostic())