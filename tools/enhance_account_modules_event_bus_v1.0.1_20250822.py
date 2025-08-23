#!/usr/bin/env python3
"""
Account Modules Event-Bus Integration Enhancement Tool
Erweitert alle Account Modules um vollständige Event-Bus Integration
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add project path

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

print("🔧 Account Modules Event-Bus Enhancement Tool")
print("=" * 60)

ACCOUNT_MODULES_PATH = "/home/mdoehler/aktienanalyse-ökosystem/services/broker-gateway-service-modular/modules/account_modules"

# Event-Bus Integration Template
EVENT_BUS_INTEGRATION_TEMPLATE = '''
    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions"""
        try:
            # Subscribe to relevant events for this module
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            
            self.logger.info("Event subscriptions setup completed", 
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)
    
    async def process_event(self, event):
        """Process incoming events"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'execution_count': getattr(self, 'execution_history', []),
                        'average_execution_time_ms': self.average_execution_time,
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
            elif event_type == f'{self.module_name}.request':
                # Module-specific request
                event_data = event.get('data', {})
                result = await self.execute_function(event_data)
                
                response_event = {
                    'event_type': f'{self.module_name}.response',
                    'stream_id': event.get('stream_id', f'{self.module_name}-request'),
                    'data': result,
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(response_event)
            
            else:
                self.logger.debug("Unhandled event type", 
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)
'''

def get_account_modules() -> List[Path]:
    """Get all Python modules in account_modules directory"""
    modules_path = Path(ACCOUNT_MODULES_PATH)
    if not modules_path.exists():
        print(f"❌ Account modules path not found: {ACCOUNT_MODULES_PATH}")
        return []
    
    python_files = list(modules_path.glob("*.py"))
    # Filter out __init__ and base files
    python_files = [f for f in python_files if not f.name.startswith('__') and 'base' not in f.name.lower()]
    
    return python_files

def analyze_module_event_integration(module_path: Path) -> Dict[str, Any]:
    """Analyze current Event-Bus integration level of a module"""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Event-Bus indicators
        indicators = {
            'has_event_bus_param': 'event_bus=None' in content,
            'has_process_event': 'async def process_event' in content or 'def process_event' in content,
            'has_event_publishing': 'event_bus.publish' in content or 'await self.event_bus.publish' in content,
            'has_event_subscriptions': '_setup_event_subscriptions' in content,
            'has_health_response': 'system.health.response' in content,
            'imports_datetime': 'from datetime import' in content or 'import datetime' in content,
        }
        
        # Calculate integration score
        integration_score = sum(indicators.values()) / len(indicators) * 100
        
        return {
            'module_path': module_path,
            'module_name': module_path.stem,
            'integration_score': integration_score,
            'indicators': indicators,
            'needs_enhancement': integration_score < 80.0
        }
        
    except Exception as e:
        print(f"❌ Failed to analyze {module_path.name}: {e}")
        return {
            'module_path': module_path,
            'module_name': module_path.stem,
            'integration_score': 0,
            'indicators': {},
            'needs_enhancement': True,
            'error': str(e)
        }

def enhance_module_event_integration(analysis: Dict[str, Any]) -> bool:
    """Enhance a module with Event-Bus integration"""
    module_path = analysis['module_path']
    
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Modifications needed
        modified = False
        
        # 1. Add event subscriptions setup to __init__
        if not analysis['indicators']['has_event_subscriptions']:
            # Find __init__ method and add event setup
            if 'def __init__(self, event_bus=None):' in content and 'self._setup_event_subscriptions()' not in content:
                content = content.replace(
                    'def __init__(self, event_bus=None):\n        super().__init__',
                    'def __init__(self, event_bus=None):\n        super().__init__'
                )
                
                # Find the end of __init__ and add event setup
                init_lines = content.split('\n')
                for i, line in enumerate(init_lines):
                    if 'def __init__(self, event_bus=None):' in line:
                        # Find the end of __init__ (next method or class)
                        for j in range(i + 1, len(init_lines)):
                            if (init_lines[j].strip().startswith('def ') and 
                                not init_lines[j].strip().startswith('def __init__') and
                                not init_lines[j].strip().startswith('    ')):
                                
                                # Insert event setup before this line
                                event_setup_lines = [
                                    '',
                                    '        # Event-Bus Integration Setup',
                                    '        if self.event_bus:',
                                    '            asyncio.create_task(self._setup_event_subscriptions())',
                                    ''
                                ]
                                
                                for k, setup_line in enumerate(event_setup_lines):
                                    init_lines.insert(j + k, setup_line)
                                
                                modified = True
                                break
                        break
                
                if modified:
                    content = '\n'.join(init_lines)
        
        # 2. Add missing imports
        if 'import asyncio' not in content and modified:
            # Add asyncio import after existing imports
            import_lines = []
            other_lines = []
            in_imports = True
            
            for line in content.split('\n'):
                if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == ''):
                    import_lines.append(line)
                elif line.startswith('import ') or line.startswith('from '):
                    import_lines.append(line)
                else:
                    in_imports = False
                    other_lines.append(line)
            
            # Add asyncio import if not present
            if not any('import asyncio' in line for line in import_lines):
                import_lines.insert(-1, 'import asyncio')
                content = '\n'.join(import_lines + other_lines)
        
        # 3. Add Event-Bus integration methods at end of class
        if not analysis['indicators']['has_process_event'] or not analysis['indicators']['has_event_subscriptions']:
            # Find the end of the class (before the last closing brace/end)
            class_lines = content.split('\n')
            
            # Find the last method in the class
            last_method_end = -1
            in_class = False
            
            for i, line in enumerate(class_lines):
                if line.strip().startswith('class ') and 'SingleFunctionModule' in line:
                    in_class = True
                elif in_class and line.strip() and not line.startswith('    '):
                    # End of class
                    last_method_end = i
                    break
            
            if last_method_end == -1:
                last_method_end = len(class_lines)
            
            # Insert Event-Bus methods before class end
            integration_methods = EVENT_BUS_INTEGRATION_TEMPLATE.split('\n')
            
            for j, method_line in enumerate(integration_methods):
                class_lines.insert(last_method_end + j, method_line)
            
            content = '\n'.join(class_lines)
            modified = True
        
        # Write enhanced content back
        if modified:
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Enhanced {module_path.name} - Event-Bus integration added")
            return True
        else:
            print(f"ℹ️  {module_path.name} - Already has Event-Bus integration")
            return False
            
    except Exception as e:
        print(f"❌ Failed to enhance {module_path.name}: {e}")
        return False

def main():
    """Main enhancement process"""
    
    print("📊 Scanning Account Modules...")
    account_modules = get_account_modules()
    
    if not account_modules:
        print("❌ No account modules found!")
        return
    
    print(f"📁 Found {len(account_modules)} account modules")
    print()
    
    # Analyze current integration status
    analyses = []
    for module_path in account_modules:
        analysis = analyze_module_event_integration(module_path)
        analyses.append(analysis)
        
        status = "✅" if analysis['integration_score'] >= 80 else "⚠️" if analysis['integration_score'] >= 50 else "❌"
        print(f"{status} {analysis['module_name']}: {analysis['integration_score']:.1f}% Event-Bus integration")
    
    print()
    
    # Enhancement phase
    modules_needing_enhancement = [a for a in analyses if a['needs_enhancement']]
    
    if modules_needing_enhancement:
        print(f"🔧 Enhancing {len(modules_needing_enhancement)} modules...")
        
        enhanced_count = 0
        for analysis in modules_needing_enhancement:
            if enhance_module_event_integration(analysis):
                enhanced_count += 1
        
        print(f"✅ Enhanced {enhanced_count} modules with Event-Bus integration")
    else:
        print("✅ All modules already have adequate Event-Bus integration")
    
    print()
    print("📊 ENHANCEMENT SUMMARY")
    print("-" * 40)
    print(f"Total Modules: {len(account_modules)}")
    print(f"Already Integrated: {len([a for a in analyses if not a['needs_enhancement']])}")
    print(f"Enhanced: {len(modules_needing_enhancement)}")
    print()
    
    # Final integration scores
    print("🎯 Final Integration Scores:")
    for analysis in analyses:
        status_emoji = "✅" if analysis['integration_score'] >= 80 else "⚠️" if analysis['integration_score'] >= 50 else "❌"
        print(f"{status_emoji} {analysis['module_name']}: {analysis['integration_score']:.1f}%")

if __name__ == "__main__":
    main()