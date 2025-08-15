#!/usr/bin/env python3
"""
Debug Test Environment - Simuliere exakte Test-Bedingungen
"""

import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, List

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from event_orchestrator import EventOrchestrator, EventRoute
from cross_service_integration_tests import MockEventBus


async def simulate_exact_test_conditions():
    """Simuliere die exakten Test-Bedingungen"""
    print("🧪 SIMULATE: Exact Test Conditions")
    print("=" * 50)
    
    # Exakte Test-Setup wie in cross_service_integration_tests.py
    mock_event_bus = MockEventBus()
    orchestrator = EventOrchestrator(event_bus=mock_event_bus)
    
    # Register test services - exakt wie im Test
    orchestrator.register_service('account_service', {
        'type': 'account_management',
        'version': '1.0.0',
        'capabilities': ['balance_management', 'portfolio_summary']
    })
    
    orchestrator.register_service('order_service', {
        'type': 'order_management', 
        'version': '1.0.0',
        'capabilities': ['order_placement', 'order_execution']
    })
    
    orchestrator.register_service('frontend_service', {
        'type': 'user_interface',
        'version': '1.0.0',
        'capabilities': ['dashboard', 'trading_interface']
    })
    
    # Clear any previous events - exakt wie im Test
    mock_event_bus.clear_published_events()
    
    # Create market data update event - exakt wie im Test
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
    
    print("📨 Processing Market Event (Exact Test Conditions)")
    
    # Process event - exakt wie im Test
    result = await orchestrator.process_event(market_event)
    
    print(f"🎯 Result Analysis:")
    print(f"   routed: {result['routed']}")
    print(f"   successful_routes: {result.get('successful_routes', 'MISSING')}")
    print(f"   routes_processed: {result.get('routes_processed', 'MISSING')}")
    
    # Test Assertion 1: routed should be True
    assert result['routed'] == True, f"Expected routed=True, got {result['routed']}"
    print("✅ Assertion 1 PASSED: routed == True")
    
    # Test Assertion 2: successful_routes should be 3
    try:
        assert result['successful_routes'] == 3, f"Expected successful_routes=3, got {result.get('successful_routes')}"
        print("✅ Assertion 2 PASSED: successful_routes == 3")
    except AssertionError as e:
        print(f"❌ Assertion 2 FAILED: {e}")
        return False
    
    # Get all published events after processing - exakt wie im Test
    all_published = mock_event_bus.published_events
    print(f"\n📋 Published Events Analysis:")
    print(f"   Total: {len(all_published)}")
    
    # Verify each service received the event - exakt wie im Test
    target_services = ['account_service', 'order_service', 'frontend_service']
    received_services = set()
    
    for published_event in all_published:
        stream_id = published_event.get('stream_id', '')
        print(f"   Event: stream_id={stream_id}")
        for service in target_services:
            if stream_id == f'{service}-orchestrated':
                received_services.add(service)
                print(f"     → Matched service: {service}")
    
    print(f"\n🎯 Service Coverage:")
    print(f"   Expected: {target_services}")
    print(f"   Received: {list(received_services)}")
    
    # Test Assertion 3: len(received_services) should be 3
    try:
        assert len(received_services) == 3, f"Expected all 3 services to receive market data, got {len(received_services)}: {received_services}"
        print("✅ Assertion 3 PASSED: len(received_services) == 3")
    except AssertionError as e:
        print(f"❌ Assertion 3 FAILED: {e}")
        return False
    
    return True


async def debug_result_structure():
    """Debug die Struktur des result dictionary"""
    print("\n🔍 DEBUG: Result Structure Analysis")
    print("=" * 40)
    
    mock_event_bus = MockEventBus()
    orchestrator = EventOrchestrator(event_bus=mock_event_bus)
    
    test_event = {
        'event_type': 'market.prices.updated',
        'source': 'market_data_service',
        'data': {'test': True}
    }
    
    result = await orchestrator.process_event(test_event)
    
    print("📊 Complete Result Dictionary:")
    for key, value in result.items():
        print(f"   {key}: {value} (type: {type(value).__name__})")
    
    # Check if the issue is in successful_routes calculation
    if 'routes_processed' in result and 'successful_routes' in result:
        routes_processed = result['routes_processed']
        successful_routes = result['successful_routes']
        
        print(f"\n🧮 Route Success Analysis:")
        print(f"   Routes Processed: {routes_processed}")
        print(f"   Successful Routes: {successful_routes}")
        print(f"   Success Rate: {successful_routes/routes_processed*100 if routes_processed > 0 else 0:.1f}%")


if __name__ == "__main__":
    async def main():
        success = await simulate_exact_test_conditions()
        await debug_result_structure()
        
        print(f"\n🏁 FINAL TEST SIMULATION RESULT:")
        if success:
            print("✅ All test assertions would PASS")
        else:
            print("❌ Test assertions would FAIL")
        
        return success
    
    result = asyncio.run(main())
    exit(0 if result else 1)