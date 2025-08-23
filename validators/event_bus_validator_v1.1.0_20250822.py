#!/usr/bin/env python3
"""
Event-Bus Validator für Single Function Modules
Validiert Event-Bus Integration und Kommunikation NACH dem Single Function Module Pattern
"""

import sys
import os
import importlib
import inspect
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

# Minimal imports to avoid dependency issues during validation
from datetime import datetime

# Simple logger replacement for validation
class SimpleLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg} {kwargs}")
    def debug(self, msg, **kwargs): print(f"DEBUG: {msg} {kwargs}")
    def warning(self, msg, **kwargs): print(f"WARNING: {msg} {kwargs}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg} {kwargs}")

logger = SimpleLogger()

# Mock Event and EventType for validation (to avoid heavy imports)
class MockEvent:
    def __init__(self, event_type, stream_id, data, source):
        self.event_type = event_type
        self.stream_id = stream_id
        self.data = data
        self.source = source

class MockEventType:
    DASHBOARD_REQUEST = "dashboard.request"
    MARKET_DATA_REQUEST = "market.data.request"
    TRADING_REQUEST = "trading.request"
    SYSTEM_HEALTH_REQUEST = "system.health.request"


class EventBusValidationResult:
    """Result of Event-Bus validation"""
    
    def __init__(self):
        self.total_modules = 0
        self.compliant_modules = 0
        self.non_compliant_modules = 0
        self.validation_details = {}
        self.compliance_issues = []
        self.recommendations = []
        self.overall_compliance_score = 0.0


class EventBusValidator:
    """
    Event-Bus Validator für Single Function Modules
    Validiert Compliance mit der Regel: "Kommunikation immer über den Bus"
    """
    
    def __init__(self):
        self.logger = logger
        self.discovered_modules = {}
        self.validation_results = {}
        self.event_bus = None
        
        # Validation Criteria
        self.validation_criteria = {
            'event_bus_parameter': {'weight': 0.15, 'name': 'Event-Bus Parameter in __init__'},
            'event_publishing': {'weight': 0.25, 'name': 'Event Publishing Implementation'},
            'event_handling': {'weight': 0.20, 'name': 'Event Handling Capability'},
            'single_function_pattern': {'weight': 0.20, 'name': 'Single Function Module Pattern Compliance'},
            'module_communication': {'weight': 0.20, 'name': 'Inter-Module Communication via Event-Bus'}
        }
        
        # Module Paths for discovery
        self.module_search_paths = [
            '/home/mdoehler/aktienanalyse-ökosystem/modules/account_management',
            '/home/mdoehler/aktienanalyse-ökosystem/modules/order_management',
            '/home/mdoehler/aktienanalyse-ökosystem/services/frontend-service-modular'
        ]
    
    async def validate_all_modules(self) -> EventBusValidationResult:
        """
        Validiert alle Single Function Modules auf Event-Bus Compliance
        """
        self.logger.info("Starting comprehensive Event-Bus validation")
        
        result = EventBusValidationResult()
        
        # 1. Discover all Single Function Modules
        await self._discover_modules()
        
        # 2. Initialize Event-Bus for testing
        await self._initialize_event_bus()
        
        # 3. Validate each module
        for module_path, module_info in self.discovered_modules.items():
            validation_result = await self._validate_single_module(module_info)
            self.validation_results[module_path] = validation_result
            result.total_modules += 1
            
            if validation_result['overall_compliance'] >= 0.8:
                result.compliant_modules += 1
            else:
                result.non_compliant_modules += 1
        
        # 4. Generate comprehensive results
        await self._generate_validation_report(result)
        
        # 5. Cleanup
        await self._cleanup_event_bus()
        
        self.logger.info("Event-Bus validation completed",
                        total_modules=result.total_modules,
                        compliant_modules=result.compliant_modules,
                        compliance_score=result.overall_compliance_score)
        
        return result
    
    async def _discover_modules(self):
        """
        Entdeckt alle Single Function Modules in den definierten Pfaden
        """
        self.logger.info("Discovering Single Function Modules")
        
        for search_path in self.module_search_paths:
            if not os.path.exists(search_path):
                self.logger.warning(f"Search path not found: {search_path}")
                continue
            
            # Suche nach Python-Dateien
            for py_file in Path(search_path).rglob("*.py"):
                if py_file.name.startswith('__'):
                    continue
                
                try:
                    module_info = await self._analyze_python_file(py_file)
                    if module_info and module_info.get('is_single_function_module'):
                        self.discovered_modules[str(py_file)] = module_info
                        self.logger.debug(f"Discovered module: {module_info['module_name']}")
                
                except Exception as e:
                    self.logger.error(f"Failed to analyze {py_file}: {e}")
        
        self.logger.info(f"Discovered {len(self.discovered_modules)} Single Function Modules")
    
    async def _analyze_python_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analysiert eine Python-Datei auf Single Function Module Pattern
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for Single Function Module indicators
            if 'SingleFunctionModule' not in content:
                return None
            
            # Extract module name from file
            relative_path = str(file_path).replace('/home/mdoehler/aktienanalyse-ökosystem/', '')
            module_name = file_path.stem
            
            # Try to identify the main class
            main_class = None
            if 'class ' in content:
                lines = content.split('\n')
                for line in lines:
                    if line.strip().startswith('class ') and 'SingleFunctionModule' in line:
                        main_class = line.split('class ')[1].split('(')[0].strip()
                        break
            
            return {
                'file_path': str(file_path),
                'relative_path': relative_path,
                'module_name': module_name,
                'main_class': main_class,
                'content': content,
                'is_single_function_module': True,
                'file_size': len(content),
                'line_count': len(content.split('\n'))
            }
        
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {e}")
            return None
    
    async def _initialize_event_bus(self):
        """
        Initialisiert Event-Bus für Validierungstests (Mock for validation)
        """
        try:
            # For validation, we use a mock to avoid dependency issues
            self.event_bus = None  # Will be mocked during actual testing
            self.logger.info("Event-Bus validation mode initialized (mock)")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Event-Bus: {e}")
            self.event_bus = None
    
    async def _validate_single_module(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validiert ein einzelnes Single Function Module
        """
        validation_result = {
            'module_name': module_info['module_name'],
            'file_path': module_info['file_path'],
            'validations': {},
            'overall_compliance': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        # 1. Event-Bus Parameter Check
        validation_result['validations']['event_bus_parameter'] = await self._check_event_bus_parameter(module_info)
        
        # 2. Event Publishing Check
        validation_result['validations']['event_publishing'] = await self._check_event_publishing(module_info)
        
        # 3. Event Handling Check
        validation_result['validations']['event_handling'] = await self._check_event_handling(module_info)
        
        # 4. Single Function Pattern Check
        validation_result['validations']['single_function_pattern'] = await self._check_single_function_pattern(module_info)
        
        # 5. Module Communication Check
        validation_result['validations']['module_communication'] = await self._check_module_communication(module_info)
        
        # Calculate overall compliance
        validation_result['overall_compliance'] = self._calculate_compliance_score(validation_result['validations'])
        
        # Generate issues and recommendations
        await self._generate_module_issues_and_recommendations(validation_result)
        
        return validation_result
    
    async def _check_event_bus_parameter(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prüft ob Event-Bus Parameter im __init__ vorhanden ist
        """
        content = module_info['content']
        
        result = {
            'score': 0.0,
            'passed': False,
            'details': {}
        }
        
        # Check for event_bus parameter in __init__
        if 'def __init__(self' in content:
            init_lines = []
            in_init = False
            
            for line in content.split('\n'):
                if 'def __init__(self' in line:
                    in_init = True
                    init_lines.append(line)
                elif in_init:
                    if line.strip().startswith('def ') and '__init__' not in line:
                        break
                    init_lines.append(line)
            
            init_content = '\n'.join(init_lines)
            
            if 'event_bus' in init_content:
                result['score'] = 1.0
                result['passed'] = True
                result['details']['has_event_bus_param'] = True
                
                # Check for proper initialization
                if 'self.event_bus = event_bus' in init_content:
                    result['details']['proper_initialization'] = True
                else:
                    result['score'] = 0.8
                    result['details']['proper_initialization'] = False
            else:
                result['details']['has_event_bus_param'] = False
        
        return result
    
    async def _check_event_publishing(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prüft Event Publishing Implementation
        """
        content = module_info['content']
        
        result = {
            'score': 0.0,
            'passed': False,
            'details': {}
        }
        
        # Check for event publishing patterns
        publishing_indicators = [
            'await self.event_bus.publish',
            'self.event_bus.publish',
            'Event(',
            'event_bus.publish'
        ]
        
        found_indicators = []
        for indicator in publishing_indicators:
            if indicator in content:
                found_indicators.append(indicator)
        
        if found_indicators:
            result['score'] = min(len(found_indicators) / len(publishing_indicators), 1.0)
            result['passed'] = result['score'] >= 0.5
            result['details']['publishing_patterns'] = found_indicators
            
            # Check for proper event creation
            if 'Event(' in content:
                result['details']['proper_event_creation'] = True
                result['score'] = min(result['score'] + 0.2, 1.0)
        
        return result
    
    async def _check_event_handling(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prüft Event Handling Capability
        """
        content = module_info['content']
        
        result = {
            'score': 0.0,
            'passed': False,
            'details': {}
        }
        
        # Check for event handling patterns
        handling_indicators = [
            'async def process_event',
            'async def handle_event',
            'def event_handler',
            'await self.event_bus.subscribe',
            'event_bus.subscribe'
        ]
        
        found_handlers = []
        for indicator in handling_indicators:
            if indicator in content:
                found_handlers.append(indicator)
        
        if found_handlers:
            result['score'] = min(len(found_handlers) / 2, 1.0)  # 2 or more = full score
            result['passed'] = len(found_handlers) > 0
            result['details']['handling_patterns'] = found_handlers
        
        return result
    
    async def _check_single_function_pattern(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prüft Single Function Pattern Compliance
        """
        content = module_info['content']
        
        result = {
            'score': 0.0,
            'passed': False,
            'details': {}
        }
        
        score_components = []
        
        # Check inheritance from SingleFunctionModule
        if 'SingleFunctionModule' in content:
            score_components.append(0.3)
            result['details']['inherits_from_base'] = True
        
        # Check for execute_function method
        if 'async def execute_function' in content:
            score_components.append(0.4)
            result['details']['has_execute_function'] = True
        
        # Check for single responsibility (fewer public methods)
        public_methods = content.count('def ') - content.count('def _')
        if public_methods <= 3:  # execute_function + maybe 1-2 utility methods
            score_components.append(0.3)
            result['details']['single_responsibility'] = True
        else:
            result['details']['single_responsibility'] = False
            result['details']['public_methods_count'] = public_methods
        
        result['score'] = sum(score_components)
        result['passed'] = result['score'] >= 0.7
        
        return result
    
    async def _check_module_communication(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prüft Inter-Module Communication via Event-Bus
        """
        content = module_info['content']
        
        result = {
            'score': 0.0,
            'passed': False,
            'details': {}
        }
        
        # Check for direct module imports (should be avoided)
        direct_import_indicators = [
            'from modules.',
            'import modules.',
            'from services.',
            'import services.'
        ]
        
        direct_imports_found = []
        for indicator in direct_import_indicators:
            if indicator in content:
                direct_imports_found.append(indicator)
        
        # Check for event-based communication patterns
        event_communication_indicators = [
            'EventType.',
            'event_type=',
            'publish(',
            'subscribe('
        ]
        
        event_patterns_found = []
        for indicator in event_communication_indicators:
            if indicator in content:
                event_patterns_found.append(indicator)
        
        # Calculate score
        if event_patterns_found:
            base_score = min(len(event_patterns_found) / len(event_communication_indicators), 1.0)
        else:
            base_score = 0.0
        
        # Penalty for direct imports
        penalty = min(len(direct_imports_found) * 0.2, 0.5)
        
        result['score'] = max(base_score - penalty, 0.0)
        result['passed'] = result['score'] >= 0.6
        result['details']['event_patterns'] = event_patterns_found
        result['details']['direct_imports'] = direct_imports_found
        
        return result
    
    def _calculate_compliance_score(self, validations: Dict[str, Dict[str, Any]]) -> float:
        """
        Berechnet Overall Compliance Score basierend auf gewichteten Kriterien
        """
        total_score = 0.0
        
        for criterion, weight_info in self.validation_criteria.items():
            if criterion in validations:
                validation = validations[criterion]
                weighted_score = validation['score'] * weight_info['weight']
                total_score += weighted_score
        
        return total_score
    
    async def _generate_module_issues_and_recommendations(self, validation_result: Dict[str, Any]):
        """
        Generiert Issues und Recommendations für ein Modul
        """
        validations = validation_result['validations']
        
        # Event-Bus Parameter Issues
        if not validations.get('event_bus_parameter', {}).get('passed', False):
            validation_result['issues'].append("Missing event_bus parameter in __init__ method")
            validation_result['recommendations'].append("Add event_bus=None parameter to __init__ method")
        
        # Event Publishing Issues
        if not validations.get('event_publishing', {}).get('passed', False):
            validation_result['issues'].append("Missing or incomplete event publishing implementation")
            validation_result['recommendations'].append("Implement event publishing using await self.event_bus.publish(event)")
        
        # Event Handling Issues
        if not validations.get('event_handling', {}).get('passed', False):
            validation_result['issues'].append("Missing event handling capability")
            validation_result['recommendations'].append("Add async def process_event or subscribe to relevant events")
        
        # Single Function Pattern Issues
        if not validations.get('single_function_pattern', {}).get('passed', False):
            validation_result['issues'].append("Single Function Pattern not properly implemented")
            validation_result['recommendations'].append("Ensure module inherits from SingleFunctionModule and has execute_function method")
        
        # Module Communication Issues
        communication_validation = validations.get('module_communication', {})
        if not communication_validation.get('passed', False):
            validation_result['issues'].append("Direct module imports detected - should use Event-Bus")
            validation_result['recommendations'].append("Replace direct module imports with Event-Bus communication")
    
    async def _generate_validation_report(self, result: EventBusValidationResult):
        """
        Generiert comprehensive validation report
        """
        result.validation_details = self.validation_results.copy()
        
        # Calculate overall compliance score
        if result.total_modules > 0:
            result.overall_compliance_score = result.compliant_modules / result.total_modules
        
        # Collect all issues and recommendations
        for module_result in self.validation_results.values():
            result.compliance_issues.extend(module_result['issues'])
            result.recommendations.extend(module_result['recommendations'])
        
        # Remove duplicates
        result.compliance_issues = list(set(result.compliance_issues))
        result.recommendations = list(set(result.recommendations))
    
    async def _cleanup_event_bus(self):
        """
        Cleanup Event-Bus connection
        """
        if self.event_bus:
            try:
                await self.event_bus.disconnect()
            except Exception as e:
                self.logger.error(f"Failed to disconnect Event-Bus: {e}")
    
    def generate_compliance_report(self, result: EventBusValidationResult) -> str:
        """
        Generiert human-readable compliance report
        """
        report = []
        report.append("=" * 80)
        report.append("EVENT-BUS COMPLIANCE VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Validation Date: {datetime.now().isoformat()}")
        report.append(f"Architecture Rule: 'Kommunikation immer über den Bus'")
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Modules Analyzed: {result.total_modules}")
        report.append(f"Compliant Modules: {result.compliant_modules}")
        report.append(f"Non-Compliant Modules: {result.non_compliant_modules}")
        report.append(f"Overall Compliance Score: {result.overall_compliance_score:.1%}")
        report.append("")
        
        # Detailed Results
        report.append("DETAILED VALIDATION RESULTS")
        report.append("-" * 40)
        
        for module_path, validation in result.validation_details.items():
            module_name = validation['module_name']
            compliance = validation['overall_compliance']
            status = "✅ COMPLIANT" if compliance >= 0.8 else "❌ NON-COMPLIANT"
            
            report.append(f"Module: {module_name} ({compliance:.1%}) {status}")
            
            # Validation Details
            for criterion, validation_detail in validation['validations'].items():
                score = validation_detail['score']
                passed = "✅" if validation_detail['passed'] else "❌"
                criterion_name = self.validation_criteria[criterion]['name']
                report.append(f"  {passed} {criterion_name}: {score:.1%}")
            
            # Issues
            if validation['issues']:
                report.append("  Issues:")
                for issue in validation['issues']:
                    report.append(f"    - {issue}")
            
            report.append("")
        
        # Recommendations
        if result.recommendations:
            report.append("RECOMMENDATIONS")
            report.append("-" * 40)
            for i, recommendation in enumerate(result.recommendations, 1):
                report.append(f"{i}. {recommendation}")
            report.append("")
        
        # Compliance Issues Summary
        if result.compliance_issues:
            report.append("COMPLIANCE ISSUES SUMMARY")
            report.append("-" * 40)
            for i, issue in enumerate(result.compliance_issues, 1):
                report.append(f"{i}. {issue}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


async def main():
    """
    Hauptfunktion für Event-Bus Validation
    """
    print("🔍 Starting Event-Bus Compliance Validation...")
    
    validator = EventBusValidator()
    result = await validator.validate_all_modules()
    
    # Generate and save report
    report = validator.generate_compliance_report(result)
    
    # Save report to file
    report_path = "/home/mdoehler/aktienanalyse-ökosystem/EVENT_BUS_COMPLIANCE_VALIDATION_2025_08_09.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📊 Validation completed!")
    print(f"📁 Report saved to: {report_path}")
    print("")
    print("SUMMARY:")
    print(f"  Total Modules: {result.total_modules}")
    print(f"  Compliant: {result.compliant_modules}")
    print(f"  Non-Compliant: {result.non_compliant_modules}")
    print(f"  Overall Compliance: {result.overall_compliance_score:.1%}")
    
    # Print critical issues
    if result.compliance_issues:
        print("")
        print("CRITICAL ISSUES:")
        for issue in result.compliance_issues[:5]:  # Top 5
            print(f"  - {issue}")


if __name__ == "__main__":
    asyncio.run(main())