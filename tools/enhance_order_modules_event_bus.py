#!/usr/bin/env python3
"""
Order Modules Event-Bus Integration Enhancement Tool
Erweitert alle Order Modules um vollständige Event-Bus Integration
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add project path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

print("🔧 Order Modules Event-Bus Enhancement Tool")
print("=" * 60)

ORDER_MODULES_PATH = "/home/mdoehler/aktienanalyse-ökosystem/services/broker-gateway-service-modular/modules/order_modules"

def get_order_modules() -> List[Path]:
    """Get all Python modules in order_modules directory"""
    modules_path = Path(ORDER_MODULES_PATH)
    if not modules_path.exists():
        print(f"❌ Order modules path not found: {ORDER_MODULES_PATH}")
        return []
    
    python_files = list(modules_path.glob("*.py"))
    # Filter out __init__ and base files
    python_files = [f for f in python_files if not f.name.startswith('__') and 'base' not in f.name.lower()]
    
    return python_files

def enhance_order_module_with_event_bus(module_path: Path) -> bool:
    """Enhance an order module with comprehensive Event-Bus integration"""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has event integration
        if 'async def process_event' in content and 'await self.event_bus.publish' in content:
            print(f"ℹ️  {module_path.name} - Already has Event-Bus integration")
            return False
        
        # Add async import if not present
        if 'import asyncio' not in content:
            # Find the first import line and add asyncio
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    lines.insert(i, 'import asyncio')
                    break
            content = '\n'.join(lines)
        
        # Modify __init__ to setup event subscriptions
        if 'def __init__(self, event_bus=None):' in content:
            # Add event setup to __init__
            content = content.replace(
                'self.execution_history = []',
                '''self.execution_history = []
        
        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())'''
            )
        
        # Add Event-Bus integration methods at the end of the class
        # Find the end of the class
        lines = content.split('\n')
        class_end_index = len(lines)
        
        # Find last method in the class
        for i in range(len(lines)-1, -1, -1):
            line = lines[i].strip()
            if line and not line.startswith('#') and not line.startswith('"'):
                if not line.startswith(' ') and i > 0:
                    # This is likely the end of the class
                    class_end_index = i
                    break
        
        # Insert Event-Bus methods before the class end
        event_methods = [
            '',
            '    async def _setup_event_subscriptions(self):',
            '        """Setup Event-Bus Subscriptions for Order Module"""',
            '        try:',
            '            # Subscribe to system health requests',
            '            await self.event_bus.subscribe(\'system.health.request\', self.process_event)',
            '            ',
            '            # Subscribe to module-specific order events',
            '            await self.event_bus.subscribe(f\'{self.module_name}.request\', self.process_event)',
            '            await self.event_bus.subscribe(\'order.status.request\', self.process_event)',
            '            await self.event_bus.subscribe(\'order.update\', self.process_event)',
            '            ',
            '            self.logger.info("Event subscriptions setup completed",',
            '                           module=self.module_name)',
            '        except Exception as e:',
            '            self.logger.error("Failed to setup event subscriptions",',
            '                            error=str(e), module=self.module_name)',
            '',
            '    async def process_event(self, event):',
            '        """Process incoming events"""',
            '        try:',
            '            event_type = event.get(\'event_type\', \'\')',
            '            ',
            '            if event_type == \'system.health.request\':',
            '                # Health check response',
            '                health_response = {',
            '                    \'event_type\': \'system.health.response\',',
            '                    \'stream_id\': \'health-check\',',
            '                    \'data\': {',
            '                        \'module_name\': self.module_name,',
            '                        \'status\': \'healthy\',',
            '                        \'execution_count\': len(self.execution_history),',
            '                        \'average_execution_time_ms\': self.average_execution_time,',
            '                        \'orders_processed\': getattr(self, \'orders_processed\', 0),',
            '                        \'health_check_timestamp\': datetime.now().isoformat()',
            '                    },',
            '                    \'source\': self.module_name,',
            '                    \'correlation_id\': event.get(\'correlation_id\')',
            '                }',
            '                await self.event_bus.publish(health_response)',
            '                ',
            '            elif event_type == f\'{self.module_name}.request\':',
            '                # Module-specific request',
            '                event_data = event.get(\'data\', {})',
            '                result = await self.execute_function(event_data)',
            '                ',
            '                response_event = {',
            '                    \'event_type\': f\'{self.module_name}.response\',',
            '                    \'stream_id\': event.get(\'stream_id\', f\'{self.module_name}-request\'),',
            '                    \'data\': result,',
            '                    \'source\': self.module_name,',
            '                    \'correlation_id\': event.get(\'correlation_id\')',
            '                }',
            '                await self.event_bus.publish(response_event)',
            '            ',
            '            elif event_type == \'order.status.request\':',
            '                # Order status request',
            '                order_id = event.get(\'data\', {}).get(\'order_id\')',
            '                if order_id and hasattr(self, \'get_order_status\'):',
            '                    status = self.get_order_status(order_id)',
            '                    status_response = {',
            '                        \'event_type\': \'order.status.response\',',
            '                        \'stream_id\': event.get(\'stream_id\', \'order-status\'),',
            '                        \'data\': {',
            '                            \'order_id\': order_id,',
            '                            \'status\': status,',
            '                            \'module\': self.module_name',
            '                        },',
            '                        \'source\': self.module_name,',
            '                        \'correlation_id\': event.get(\'correlation_id\')',
            '                    }',
            '                    await self.event_bus.publish(status_response)',
            '            ',
            '            else:',
            '                self.logger.debug("Unhandled event type",',
            '                                event_type=event_type, module=self.module_name)',
            '                ',
            '        except Exception as e:',
            '            self.logger.error("Failed to process event",',
            '                            error=str(e), event=str(event), module=self.module_name)',
            '',
            '    async def publish_order_event(self, event_type: str, order_data: dict):',
            '        """Publish order-related events"""',
            '        if not self.event_bus:',
            '            return',
            '            ',
            '        try:',
            '            order_event = {',
            '                \'event_type\': event_type,',
            '                \'stream_id\': f\'order-{order_data.get("order_id", "unknown")}\',',
            '                \'data\': {',
            '                    **order_data,',
            '                    \'timestamp\': datetime.now().isoformat(),',
            '                    \'processing_module\': self.module_name',
            '                },',
            '                \'source\': self.module_name',
            '            }',
            '            await self.event_bus.publish(order_event)',
            '            ',
            '        except Exception as e:',
            '            self.logger.error("Failed to publish order event",',
            '                            error=str(e), event_type=event_type)'
        ]
        
        # Insert the methods
        for i, method_line in enumerate(event_methods):
            lines.insert(class_end_index + i, method_line)
        
        content = '\n'.join(lines)
        
        # Write enhanced content back
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Enhanced {module_path.name} - Event-Bus integration added")
        return True
        
    except Exception as e:
        print(f"❌ Failed to enhance {module_path.name}: {e}")
        return False

def main():
    """Main enhancement process"""
    
    print("📊 Scanning Order Modules...")
    order_modules = get_order_modules()
    
    if not order_modules:
        print("❌ No order modules found!")
        return
    
    print(f"📁 Found {len(order_modules)} order modules")
    print()
    
    # Enhancement phase
    enhanced_count = 0
    for module_path in order_modules:
        if enhance_order_module_with_event_bus(module_path):
            enhanced_count += 1
    
    print(f"\n✅ Enhanced {enhanced_count} order modules with Event-Bus integration")
    
    print()
    print("📊 ORDER MODULE ENHANCEMENT SUMMARY")
    print("-" * 40)
    print(f"Total Modules: {len(order_modules)}")
    print(f"Enhanced: {enhanced_count}")
    print(f"Already Integrated: {len(order_modules) - enhanced_count}")

if __name__ == "__main__":
    main()