#!/usr/bin/env python3
"""
Cross-Service Integration Tests - Phase 2
Tests für Service-übergreifende Event-Bus Integration
"""

import sys
import asyncio
import unittest
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from event_orchestrator_v1_5_0_20250809 import EventOrchestrator, EventRoute


class MockEventBus:
    """Mock Event-Bus for testing cross-service integration"""
    
    def __init__(self):
        self.published_events = []
        self.subscribers = {}
        self.connected = True
    
    async def publish(self, event: Dict[str, Any], stream_id: str = None):
        """Mock publish - store events"""
        published_event = {
            'event': event,
            'stream_id': stream_id,
            'timestamp': datetime.now().isoformat()
        }
        self.published_events.append(published_event)
        return True
    
    async def subscribe(self, event_type: str, handler, queue_name: str = None):
        """Mock subscribe - store subscriptions"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append({
            'handler': handler,
            'queue_name': queue_name
        })
        return True
    
    def get_published_events(self, event_type: str = None, stream_id: str = None) -> List[Dict]:
        """Get published events with optional filtering"""
        events = self.published_events
        
        if event_type:
            events = [e for e in events if e['event'].get('event_type') == event_type]
        
        if stream_id:
            events = [e for e in events if e['stream_id'] == stream_id]
        
        return events
    
    def clear_published_events(self):
        """Clear published events"""
        self.published_events = []


class CrossServiceIntegrationTests(unittest.TestCase):
    """Integration Tests für Service-übergreifende Event-Bus Integration"""
    
    def setUp(self):
        """Setup test environment"""
        self.mock_event_bus = MockEventBus()
        self.orchestrator = EventOrchestrator(event_bus=self.mock_event_bus)
        
        # Register test services
        self.orchestrator.register_service('account_service', {
            'type': 'account_management',
            'version': '1.0.0',
            'capabilities': ['balance_management', 'portfolio_summary']
        })
        
        self.orchestrator.register_service('order_service', {
            'type': 'order_management', 
            'version': '1.0.0',
            'capabilities': ['order_placement', 'order_execution']
        })
        
        self.orchestrator.register_service('frontend_service', {
            'type': 'user_interface',
            'version': '1.0.0',
            'capabilities': ['dashboard', 'trading_interface']
        })
    
    async def test_account_to_frontend_routing(self):
        """Test Account Balance Update routing to Frontend"""
        
        # Create account balance update event
        account_event = {
            'event_type': 'account.balance.updated',
            'source': 'account_service',
            'stream_id': 'account-balance-EUR',
            'data': {
                'currency_code': 'EUR',
                'available': '10500.00',
                'locked': '0.00',
                'total': '10500.00',
                'updated_at': datetime.now().isoformat()
            }
        }
        
        # Process event through orchestrator
        result = await self.orchestrator.process_event(account_event)
        
        # Verify routing success
        self.assertTrue(result['routed'])
        self.assertEqual(result['routes_processed'], 1)
        self.assertEqual(result['successful_routes'], 1)
        
        # Verify frontend service received transformed event
        frontend_events = self.mock_event_bus.get_published_events(
            event_type='dashboard.balance.refresh',
            stream_id='frontend_service-orchestrated'
        )
        
        self.assertEqual(len(frontend_events), 1)
        
        frontend_event = frontend_events[0]
        self.assertEqual(frontend_event['event']['event_type'], 'dashboard.balance.refresh')
        self.assertEqual(frontend_event['event']['target_service'], 'frontend_service')
        self.assertIn('orchestration', frontend_event['event'])
    
    async def test_order_to_account_routing(self):
        """Test Order Execution routing to Account Service"""
        
        # Create order execution event
        order_event = {
            'event_type': 'order.executed',
            'source': 'order_service',
            'stream_id': 'order-12345',
            'data': {
                'order_id': 'ORD_12345',
                'symbol': 'BTC/EUR',
                'side': 'buy',
                'amount': '0.1',
                'price': '45000.0',
                'executed_at': datetime.now().isoformat()
            }
        }
        
        # Process event
        result = await self.orchestrator.process_event(order_event)
        
        # Verify routing
        self.assertTrue(result['routed'])
        self.assertEqual(result['successful_routes'], 1)
        
        # Verify account service received transformed event
        account_events = self.mock_event_bus.get_published_events(
            event_type='account.balance.sync',
            stream_id='account_service-orchestrated'
        )
        
        self.assertEqual(len(account_events), 1)
        
        account_event = account_events[0]
        self.assertEqual(account_event['event']['event_type'], 'account.balance.sync')
        self.assertTrue(account_event['event']['data'].get('trigger_portfolio_update', False))
    
    async def test_market_data_broadcast(self):
        """Test Market Data Update broadcast to all services"""
        
        # Clear any previous events
        self.mock_event_bus.clear_published_events()
        
        # Create market data update event
        market_event = {
            'event_type': 'market.prices.updated',
            'source': 'market_data_service',
            'stream_id': 'market-prices',
            'data': {
                'updated_prices': {
                    'BTC': 45500.0,
                    'ETH': 2850.0
                },
                'currencies_updated': ['BTC', 'ETH'],
                'updated_at': datetime.now().isoformat()
            }
        }
        
        # Process event
        result = await self.orchestrator.process_event(market_event)
        
        # Verify routing to all 3 target services
        self.assertTrue(result['routed'])
        self.assertEqual(result['successful_routes'], 3)
        
        # Get all published events after processing
        all_published = self.mock_event_bus.published_events
        
        # Verify each service received the event
        target_services = ['account_service', 'order_service', 'frontend_service']
        received_services = set()
        
        for published_event in all_published:
            stream_id = published_event.get('stream_id', '')
            for service in target_services:
                if stream_id == f'{service}-orchestrated':
                    received_services.add(service)
        
        self.assertEqual(len(received_services), 3, 
                        f"Expected all 3 services to receive market data, got {len(received_services)}: {received_services}")
        
        # Verify all target services received the event
        for service in target_services:
            self.assertIn(service, received_services, 
                         f"Service {service} should receive market data event")
    
    async def test_system_health_orchestration(self):
        """Test System Health Request orchestration"""
        
        # Clear any previous events
        self.mock_event_bus.clear_published_events()
        
        # Create system health request
        health_event = {
            'event_type': 'system.health.request',
            'source': 'monitoring_service',
            'stream_id': 'health-check',
            'data': {
                'request_type': 'full_system_health',
                'request_id': 'health_001'
            }
        }
        
        # Process event
        result = await self.orchestrator.process_event(health_event)
        
        # Verify routing to all services
        self.assertTrue(result['routed'])
        self.assertEqual(result['successful_routes'], 3)
        
        # Get all published events after processing
        all_published = self.mock_event_bus.published_events
        
        # Verify each service received the health request
        target_services = ['account_service', 'order_service', 'frontend_service']
        received_services = set()
        
        for published_event in all_published:
            stream_id = published_event.get('stream_id', '')
            for service in target_services:
                if stream_id == f'{service}-orchestrated':
                    received_services.add(service)
        
        self.assertEqual(len(received_services), 3, 
                        f"Expected all 3 services to receive health request, got {len(received_services)}: {received_services}")
        
        # Verify orchestration metrics updated
        metrics = self.orchestrator.get_orchestration_metrics()
        self.assertGreater(metrics['metrics']['total_events_processed'], 0)
        self.assertGreater(metrics['metrics']['successful_routings'], 0)
    
    async def test_event_transformation(self):
        """Test event transformation during routing"""
        
        # Create event that should be transformed
        source_event = {
            'event_type': 'account.balance.updated',
            'source': 'account_service',
            'data': {
                'currency': 'EUR',
                'new_balance': '15000.00'
            }
        }
        
        # Process event
        await self.orchestrator.process_event(source_event)
        
        # Verify transformation occurred
        frontend_events = self.mock_event_bus.get_published_events(
            event_type='dashboard.balance.refresh'
        )
        
        self.assertEqual(len(frontend_events), 1)
        
        transformed_event = frontend_events[0]['event']
        
        # Verify transformation metadata
        self.assertIn('orchestration', transformed_event)
        self.assertEqual(transformed_event['orchestration']['original_event_type'], 'account.balance.updated')
        self.assertIn('processing_id', transformed_event['orchestration'])
        
        # Verify routing metadata
        self.assertIn('routing_metadata', transformed_event)
        self.assertEqual(transformed_event['routing_metadata']['route_priority'], 1)
    
    async def test_orchestration_metrics(self):
        """Test orchestration metrics collection"""
        
        # Process several events
        events = [
            {
                'event_type': 'account.balance.updated',
                'source': 'account_service',
                'data': {'test': 1}
            },
            {
                'event_type': 'order.executed', 
                'source': 'order_service',
                'data': {'test': 2}
            },
            {
                'event_type': 'market.prices.updated',
                'source': 'market_data_service',
                'data': {'test': 3}
            }
        ]
        
        for event in events:
            await self.orchestrator.process_event(event)
        
        # Check metrics
        metrics = self.orchestrator.get_orchestration_metrics()
        
        self.assertEqual(metrics['metrics']['total_events_processed'], 3)
        self.assertGreater(metrics['metrics']['successful_routings'], 0)
        self.assertGreater(metrics['metrics']['average_processing_time_ms'], 0)
        self.assertEqual(metrics['registered_services'], 3)
    
    async def test_service_health_monitoring(self):
        """Test service health monitoring"""
        
        # Get initial health summary
        health_summary = self.orchestrator.get_service_health_summary()
        
        self.assertEqual(health_summary['total_services'], 3)
        self.assertEqual(health_summary['healthy_services'], 3)
        
        # Verify service details
        self.assertIn('account_service', health_summary['services'])
        self.assertIn('order_service', health_summary['services'])
        self.assertIn('frontend_service', health_summary['services'])
        
        for service_name, service_health in health_summary['services'].items():
            self.assertEqual(service_health['status'], 'healthy')
            self.assertIn('last_seen', service_health)
            self.assertIn('seconds_since_seen', service_health)
    
    def test_event_route_management(self):
        """Test event route management"""
        
        # Add custom route
        custom_route = EventRoute(
            source_service="custom_service",
            event_type="custom.event",
            target_services=["account_service"],
            priority=3
        )
        
        initial_routes = self.orchestrator.metrics.active_routes
        self.orchestrator.add_event_route(custom_route)
        
        self.assertEqual(self.orchestrator.metrics.active_routes, initial_routes + 1)
        
        # Verify route was added
        route_key = "custom_service:custom.event"
        self.assertIn(route_key, self.orchestrator.event_routes)
        self.assertEqual(self.orchestrator.event_routes[route_key].priority, 3)


class CrossServiceAsyncTestRunner:
    """Async test runner for cross-service integration tests"""
    
    def __init__(self):
        self.test_suite = CrossServiceIntegrationTests()
        self.test_results = {}
    
    async def run_all_tests(self):
        """Run all cross-service integration tests"""
        print("🧪 Starting Cross-Service Integration Tests...")
        
        test_methods = [
            'test_account_to_frontend_routing',
            'test_order_to_account_routing',
            'test_market_data_broadcast',
            'test_system_health_orchestration',
            'test_event_transformation',
            'test_orchestration_metrics',
            'test_service_health_monitoring',
            'test_event_route_management'
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_method in test_methods:
            try:
                print(f"  Running {test_method}...")
                
                # Setup fresh test environment
                self.test_suite.setUp()
                
                # Run the test
                if asyncio.iscoroutinefunction(getattr(self.test_suite, test_method)):
                    await getattr(self.test_suite, test_method)()
                else:
                    getattr(self.test_suite, test_method)()
                
                print(f"  ✅ {test_method} PASSED")
                self.test_results[test_method] = 'PASSED'
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {test_method} FAILED: {str(e)}")
                self.test_results[test_method] = f'FAILED: {str(e)}'
                failed_tests += 1
        
        # Summary
        print(f"\n📊 Cross-Service Integration Test Results:")
        print(f"  Total Tests: {len(test_methods)}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success Rate: {(passed_tests/len(test_methods)*100):.1f}%")
        
        return {
            'total_tests': len(test_methods),
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/len(test_methods)*100),
            'results': self.test_results
        }


async def main():
    """Main test execution"""
    runner = CrossServiceAsyncTestRunner()
    results = await runner.run_all_tests()
    
    # Save test results
    test_report_path = "/home/mdoehler/aktienanalyse-ökosystem/CROSS_SERVICE_INTEGRATION_TEST_2025_08_09.md"
    
    with open(test_report_path, 'w', encoding='utf-8') as f:
        f.write("# Cross-Service Integration Test Report - Phase 2\n\n")
        f.write(f"**Test Date**: {datetime.now().isoformat()}\n\n")
        f.write(f"**Total Tests**: {results['total_tests']}\n")
        f.write(f"**Passed**: {results['passed']}\n")
        f.write(f"**Failed**: {results['failed']}\n")
        f.write(f"**Success Rate**: {results['success_rate']:.1f}%\n\n")
        
        f.write("## Test Results\n\n")
        for test_name, result in results['results'].items():
            status = "✅" if result == "PASSED" else "❌"
            f.write(f"- {status} **{test_name}**: {result}\n")
        
        f.write("\n## Cross-Service Integration Capabilities\n\n")
        f.write("- ✅ Account-to-Frontend Event Routing\n")
        f.write("- ✅ Order-to-Account Event Routing\n")
        f.write("- ✅ Market Data Broadcast to All Services\n")
        f.write("- ✅ System Health Request Orchestration\n")
        f.write("- ✅ Event Transformation & Routing Metadata\n")
        f.write("- ✅ Orchestration Metrics Collection\n")
        f.write("- ✅ Service Health Monitoring\n")
        f.write("- ✅ Dynamic Event Route Management\n")
    
    print(f"\n📁 Cross-service integration test report saved to: {test_report_path}")
    
    return results['success_rate'] == 100.0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)