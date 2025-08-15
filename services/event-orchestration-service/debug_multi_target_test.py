#!/usr/bin/env python3
"""
Debug Multi-Target Event Broadcasting
Analysiert warum Market Data Broadcasting nur 1 statt 3 Services erreicht
"""

import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, List

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from event_orchestrator import EventOrchestrator, EventRoute
from cross_service_integration_tests import MockEventBus


async def debug_multi_target_broadcasting():
    """Debug Multi-Target Event Broadcasting Issues"""
    print("🔍 DEBUG: Multi-Target Event Broadcasting Analysis")
    print("=" * 60)
    
    # Setup
    mock_event_bus = MockEventBus()
    orchestrator = EventOrchestrator(event_bus=mock_event_bus)
    
    # Register services
    services = ['account_service', 'order_service', 'frontend_service']
    for service in services:
        orchestrator.register_service(service, {
            'type': f'{service}_type',
            'version': '1.0.0'
        })
    
    print(f"✅ Registered {len(services)} services")
    print(f"📊 Active Routes: {orchestrator.metrics.active_routes}")
    
    # Clear events and create market data event
    mock_event_bus.clear_published_events()
    
    market_event = {
        'event_type': 'market.prices.updated',
        'source': 'market_data_service',
        'stream_id': 'market-prices',
        'data': {
            'updated_prices': {'BTC': 45500.0, 'ETH': 2850.0},
            'currencies_updated': ['BTC', 'ETH'],
            'updated_at': datetime.now().isoformat()
        }
    }
    
    print(f"📨 Processing Market Data Event...")
    print(f"   Event Type: {market_event['event_type']}")
    print(f"   Source: {market_event['source']}")
    
    # Process event
    result = await orchestrator.process_event(market_event)
    
    print(f"\n🎯 Orchestration Result:")
    print(f"   Routed: {result['routed']}")
    print(f"   Routes Processed: {result.get('routes_processed', 0)}")
    print(f"   Successful Routes: {result.get('successful_routes', 0)}")
    print(f"   Processing Time: {result.get('processing_time_ms', 0):.2f}ms")
    
    # Analyze published events
    all_published = mock_event_bus.published_events
    print(f"\n📋 Published Events Analysis:")
    print(f"   Total Published Events: {len(all_published)}")
    
    # Check each event
    target_streams = set()
    for i, published_event in enumerate(all_published):
        stream_id = published_event.get('stream_id', 'unknown')
        event_data = published_event.get('event', {})
        target_service = event_data.get('target_service', 'unknown')
        
        print(f"   Event {i+1}:")
        print(f"     Stream ID: {stream_id}")
        print(f"     Target Service: {target_service}")
        print(f"     Event Type: {event_data.get('event_type', 'unknown')}")
        
        target_streams.add(stream_id)
    
    # Check target services coverage
    expected_streams = set(f'{service}-orchestrated' for service in services)
    print(f"\n🎯 Target Coverage Analysis:")
    print(f"   Expected Streams: {expected_streams}")
    print(f"   Actual Streams: {target_streams}")
    print(f"   Missing Streams: {expected_streams - target_streams}")
    
    # Check orchestration routes
    print(f"\n🛤️ Route Configuration Analysis:")
    route_key = "market_data_service:market.prices.updated"
    if route_key in orchestrator.event_routes:
        route = orchestrator.event_routes[route_key]
        print(f"   Route Found: {route_key}")
        print(f"   Target Services: {route.target_services}")
        print(f"   Priority: {route.priority}")
        print(f"   Transformation Rules: {route.transformation_rules}")
    else:
        print(f"   ❌ Route NOT Found: {route_key}")
        print(f"   Available Routes: {list(orchestrator.event_routes.keys())}")
    
    return {
        'expected_targets': len(services),
        'actual_targets': len(target_streams),
        'success_rate': len(target_streams) / len(services) * 100,
        'missing_targets': expected_streams - target_streams
    }


async def debug_specific_route_execution():
    """Debug specific route execution logic"""
    print("\n🔧 DEBUG: Route Execution Logic")
    print("=" * 40)
    
    mock_event_bus = MockEventBus()
    orchestrator = EventOrchestrator(event_bus=mock_event_bus)
    
    # Get the market data route
    route_key = "market_data_service:market.prices.updated"
    if route_key in orchestrator.event_routes:
        route = orchestrator.event_routes[route_key]
        
        # Manually test _execute_event_route
        test_event = {
            'event_type': 'market.prices.updated',
            'source': 'market_data_service',
            'data': {'test': 'debug'}
        }
        
        print(f"🧪 Testing Route Execution:")
        print(f"   Route: {route_key}")
        print(f"   Target Services: {route.target_services}")
        
        # Execute the route manually
        result = await orchestrator._execute_event_route(test_event, route, "debug-123")
        
        print(f"\n📊 Route Execution Result:")
        print(f"   Success: {result['success']}")
        print(f"   Target Results Count: {len(result.get('target_results', []))}")
        
        if 'target_results' in result:
            for i, target_result in enumerate(result['target_results']):
                print(f"   Target {i+1}:")
                print(f"     Service: {target_result['target_service']}")
                print(f"     Success: {target_result['success']}")
                if not target_result['success']:
                    print(f"     Error: {target_result.get('error', 'unknown')}")
        
        # Check mock event bus
        published_after_manual = mock_event_bus.published_events
        print(f"\n📨 Events Published After Manual Route:")
        print(f"   Count: {len(published_after_manual)}")
        
        for event in published_after_manual:
            print(f"   Stream: {event['stream_id']}")


if __name__ == "__main__":
    async def main():
        result1 = await debug_multi_target_broadcasting()
        await debug_specific_route_execution()
        
        print(f"\n🏁 FINAL DEBUG RESULTS:")
        print(f"   Expected Targets: {result1['expected_targets']}")
        print(f"   Actual Targets: {result1['actual_targets']}")
        print(f"   Success Rate: {result1['success_rate']:.1f}%")
        
        if result1['missing_targets']:
            print(f"   ❌ Missing Targets: {result1['missing_targets']}")
        else:
            print(f"   ✅ All Targets Reached")
    
    asyncio.run(main())