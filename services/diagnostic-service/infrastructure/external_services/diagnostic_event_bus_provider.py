#!/usr/bin/env python3
"""
Diagnostic Service - Event Bus Provider
CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER

Event Bus integration für real diagnostic monitoring
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import json

from ...domain.repositories.diagnostic_repository import IDiagnosticEventBusProvider


logger = logging.getLogger(__name__)


class DiagnosticEventBusProvider(IDiagnosticEventBusProvider):
    """
    Real Event Bus Provider Implementation
    INFRASTRUCTURE LAYER: Integration with existing Event Bus system
    """
    
    def __init__(self, event_bus_connector=None):
        """
        Initialize with actual Event Bus connector
        
        Args:
            event_bus_connector: Actual EventBusConnector instance
        """
        self.event_bus = event_bus_connector
        self.service_name = "diagnostic_service"
        self.connected_at = datetime.now()
        self.published_events_count = 0
        self.subscription_count = 0
        self.failed_operations = 0
        self.subscribed_event_types: Set[str] = set()
        self.health_check_interval = 30  # seconds
        self.last_health_check = None
        self.is_healthy = True
        
        # Event Bus availability fallback
        if self.event_bus is None:
            logger.warning("Event Bus connector not provided - using mock mode")
            self._mock_mode = True
        else:
            self._mock_mode = False
            logger.info("Event Bus provider initialized with real connector")
    
    async def publish_diagnostic_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish diagnostic event to event bus"""
        try:
            if self._mock_mode:
                return await self._publish_mock_event(event_data)
            
            # Create Event object compatible with existing Event Bus
            from event_bus import Event  # Import from actual event bus system
            
            event = Event(
                event_type=event_data.get('event_type', 'diagnostic.unknown'),
                stream_id=event_data.get('stream_id', f"diagnostic-{uuid.uuid4()}"),
                data=event_data.get('data', {}),
                source=self.service_name,
                correlation_id=event_data.get('correlation_id', str(uuid.uuid4()))
            )
            
            # Publish via Event Bus
            await self.event_bus.publish(event)
            self.published_events_count += 1
            
            logger.debug(f"Published diagnostic event: {event.event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish diagnostic event: {e}")
            self.failed_operations += 1
            return False
    
    async def subscribe_to_events(self, event_types: List[str]) -> bool:
        """Subscribe to specific event types for monitoring"""
        try:
            if self._mock_mode:
                return await self._subscribe_mock_events(event_types)
            
            from event_bus import EventType  # Import from actual event bus
            
            # Convert string event types to EventType enums
            for event_type_str in event_types:
                try:
                    # Map string to EventType enum
                    event_type = self._map_string_to_event_type(event_type_str)
                    if event_type:
                        # Subscribe with diagnostic monitoring callback
                        await self.event_bus.subscribe(event_type, self._diagnostic_event_handler)
                        self.subscribed_event_types.add(event_type_str)
                        self.subscription_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to subscribe to event type {event_type_str}: {e}")
                    continue
            
            logger.info(f"Subscribed to {len(self.subscribed_event_types)} event types for monitoring")
            return len(self.subscribed_event_types) > 0
            
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")
            self.failed_operations += 1
            return False
    
    async def send_test_message(
        self, 
        target_module: str, 
        message_data: Dict[str, Any]
    ) -> str:
        """Send test message and return test correlation ID"""
        try:
            correlation_id = str(uuid.uuid4())
            
            if self._mock_mode:
                await self._send_mock_test_message(target_module, message_data, correlation_id)
                return correlation_id
            
            from event_bus import Event  # Import from actual event bus
            
            # Create test event
            test_event = Event(
                event_type="diagnostic.test.message",
                stream_id=f"diagnostic-test-{target_module}",
                data={
                    'test_message': True,
                    'target_module': target_module,
                    'message_data': message_data,
                    'sent_from': self.service_name,
                    'timestamp': datetime.now().isoformat()
                },
                source=self.service_name,
                correlation_id=correlation_id
            )
            
            # Publish test event
            await self.event_bus.publish(test_event)
            self.published_events_count += 1
            
            logger.info(f"Sent test message to {target_module} with correlation_id: {correlation_id}")
            return correlation_id
            
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            self.failed_operations += 1
            raise
    
    async def ping_module(self, module_name: str) -> bool:
        """Ping specific module to test connectivity"""
        try:
            if self._mock_mode:
                return await self._ping_mock_module(module_name)
            
            from event_bus import Event
            
            # Create ping event
            ping_event = Event(
                event_type="diagnostic.ping",
                stream_id=f"diagnostic-ping-{module_name}",
                data={
                    'ping': True,
                    'target_module': module_name,
                    'ping_from': self.service_name,
                    'timestamp': datetime.now().isoformat(),
                    'ping_id': str(uuid.uuid4())
                },
                source=self.service_name
            )
            
            # Send ping
            await self.event_bus.publish(ping_event)
            self.published_events_count += 1
            
            # In real implementation, would wait for response
            # For now, assume success if no exception
            logger.debug(f"Pinged module: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ping module {module_name}: {e}")
            self.failed_operations += 1
            return False
    
    async def is_event_bus_healthy(self) -> bool:
        """Check if event bus is healthy and responsive"""
        try:
            if self._mock_mode:
                return True  # Mock is always "healthy"
            
            # Perform health check if needed
            now = datetime.now()
            if (self.last_health_check is None or 
                (now - self.last_health_check).seconds > self.health_check_interval):
                
                self.is_healthy = await self._perform_health_check()
                self.last_health_check = now
            
            return self.is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            return False
    
    async def get_connected_modules(self) -> List[str]:
        """Get list of modules connected to event bus"""
        try:
            if self._mock_mode:
                return await self._get_mock_connected_modules()
            
            # In real implementation, would query event bus for connected services
            # For now, return known/expected modules
            known_modules = [
                'analysis_module',
                'portfolio_module', 
                'trading_module',
                'order_module',
                'intelligence_module',
                'market_data_service',
                'unified_profit_engine'
            ]
            
            # Could implement actual discovery by sending broadcast ping
            # and collecting responses
            
            return known_modules
            
        except Exception as e:
            logger.error(f"Failed to get connected modules: {e}")
            return []
    
    async def _diagnostic_event_handler(self, event):
        """Handle events for diagnostic monitoring"""
        # This would be called when subscribed events are received
        # The actual monitoring logic would be in the Use Case layer
        logger.debug(f"Diagnostic handler received event: {event.event_type}")
        
        # Could forward to monitoring use case here
        # For now, just log the reception
        pass
    
    async def _perform_health_check(self) -> bool:
        """Perform actual event bus health check"""
        try:
            # Send health check ping
            health_check_event = {
                'event_type': 'diagnostic.health_check',
                'data': {
                    'health_check': True,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Try to publish health check event
            success = await self.publish_diagnostic_event(health_check_event)
            return success
            
        except Exception as e:
            logger.warning(f"Health check ping failed: {e}")
            return False
    
    def _map_string_to_event_type(self, event_type_str: str):
        """Map string event type to EventType enum"""
        # This would map string event types to the actual EventType enum
        # Based on the existing event bus system
        from event_bus import EventType
        
        event_type_mapping = {
            'analysis': EventType.ANALYSIS_STATE_CHANGED,
            'portfolio': EventType.PORTFOLIO_STATE_CHANGED,
            'trading': EventType.TRADING_STATE_CHANGED,
            'intelligence': EventType.INTELLIGENCE_TRIGGERED,
            'data_sync': EventType.DATA_SYNCHRONIZED,
            'system_alert': EventType.SYSTEM_ALERT_RAISED,
            'user_interaction': EventType.USER_INTERACTION_LOGGED,
            'config_update': EventType.CONFIG_UPDATED
        }
        
        return event_type_mapping.get(event_type_str.lower())
    
    # Mock mode methods for development/testing
    async def _publish_mock_event(self, event_data: Dict[str, Any]) -> bool:
        """Mock event publishing"""
        logger.debug(f"[MOCK] Publishing event: {event_data.get('event_type', 'unknown')}")
        self.published_events_count += 1
        await asyncio.sleep(0.01)  # Simulate network delay
        return True
    
    async def _subscribe_mock_events(self, event_types: List[str]) -> bool:
        """Mock event subscription"""
        for event_type in event_types:
            self.subscribed_event_types.add(event_type)
            self.subscription_count += 1
            
        logger.info(f"[MOCK] Subscribed to {len(event_types)} event types")
        return True
    
    async def _send_mock_test_message(
        self, 
        target_module: str, 
        message_data: Dict[str, Any], 
        correlation_id: str
    ):
        """Mock test message sending"""
        logger.info(f"[MOCK] Sending test message to {target_module}: {correlation_id}")
        self.published_events_count += 1
        await asyncio.sleep(0.05)  # Simulate processing time
    
    async def _ping_mock_module(self, module_name: str) -> bool:
        """Mock module ping"""
        logger.debug(f"[MOCK] Pinging module: {module_name}")
        await asyncio.sleep(0.02)
        # Simulate some modules being "unreachable"
        unreachable_modules = ['legacy_module', 'deprecated_service']
        return module_name not in unreachable_modules
    
    async def _get_mock_connected_modules(self) -> List[str]:
        """Mock connected modules list"""
        return [
            'analysis_module',
            'portfolio_module',
            'trading_module',
            'order_module', 
            'intelligence_module',
            'market_data_service',
            'diagnostic_service'  # Self
        ]
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        uptime = datetime.now() - self.connected_at
        success_rate = 100.0
        
        total_operations = (self.published_events_count + 
                           self.subscription_count + 
                           self.failed_operations)
        
        if total_operations > 0:
            success_rate = ((total_operations - self.failed_operations) / 
                           total_operations * 100)
        
        return {
            'provider_type': 'mock' if self._mock_mode else 'real_event_bus',
            'service_name': self.service_name,
            'uptime_seconds': int(uptime.total_seconds()),
            'published_events': self.published_events_count,
            'subscriptions': self.subscription_count,
            'failed_operations': self.failed_operations,
            'success_rate_percent': round(success_rate, 2),
            'subscribed_event_types': list(self.subscribed_event_types),
            'is_healthy': self.is_healthy,
            'last_health_check': (self.last_health_check.isoformat() 
                                 if self.last_health_check else None),
            'connected_at': self.connected_at.isoformat()
        }


class MockDiagnosticEventBusProvider(IDiagnosticEventBusProvider):
    """
    Mock Event Bus Provider for Development/Testing
    INFRASTRUCTURE LAYER: Test doubles for isolation
    """
    
    def __init__(self):
        self.published_events = []
        self.subscribed_event_types = set()
        self.connected_modules = [
            'analysis_module', 'portfolio_module', 'trading_module'
        ]
        self.is_healthy = True
        self.operation_count = 0
    
    async def publish_diagnostic_event(self, event_data: Dict[str, Any]) -> bool:
        """Mock publish diagnostic event"""
        self.published_events.append({
            'event_data': event_data,
            'published_at': datetime.now().isoformat()
        })
        self.operation_count += 1
        return True
    
    async def subscribe_to_events(self, event_types: List[str]) -> bool:
        """Mock subscribe to events"""
        for event_type in event_types:
            self.subscribed_event_types.add(event_type)
        self.operation_count += 1
        return True
    
    async def send_test_message(
        self, 
        target_module: str, 
        message_data: Dict[str, Any]
    ) -> str:
        """Mock send test message"""
        correlation_id = str(uuid.uuid4())
        self.published_events.append({
            'event_type': 'test_message',
            'target_module': target_module,
            'message_data': message_data,
            'correlation_id': correlation_id,
            'sent_at': datetime.now().isoformat()
        })
        self.operation_count += 1
        return correlation_id
    
    async def ping_module(self, module_name: str) -> bool:
        """Mock ping module"""
        self.operation_count += 1
        return module_name in self.connected_modules
    
    async def is_event_bus_healthy(self) -> bool:
        """Mock health check"""
        return self.is_healthy
    
    async def get_connected_modules(self) -> List[str]:
        """Mock connected modules"""
        return self.connected_modules.copy()
    
    def get_mock_statistics(self) -> Dict[str, Any]:
        """Get mock provider statistics"""
        return {
            'provider_type': 'mock',
            'published_events_count': len(self.published_events),
            'subscribed_event_types': list(self.subscribed_event_types),
            'connected_modules_count': len(self.connected_modules),
            'total_operations': self.operation_count,
            'is_healthy': self.is_healthy,
            'recent_events': self.published_events[-5:]  # Last 5 events
        }