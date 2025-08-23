#!/usr/bin/env python3
"""
System Health Checker für Aktienanalyse-Ökosystem
Validiert alle refactored Services und Module
"""

import sys
import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

# Simple logger for health checks
class HealthLogger:
    def info(self, msg, **kwargs): 
        print(f"ℹ️ {msg} {kwargs if kwargs else ''}")
    def success(self, msg, **kwargs): 
        print(f"✅ {msg} {kwargs if kwargs else ''}")
    def warning(self, msg, **kwargs): 
        print(f"⚠️ {msg} {kwargs if kwargs else ''}")
    def error(self, msg, **kwargs): 
        print(f"❌ {msg} {kwargs if kwargs else ''}")


class SystemHealthResult:
    """System Health Check Result"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.overall_status = "unknown"
        self.services_checked = 0
        self.services_healthy = 0
        self.services_warning = 0
        self.services_error = 0
        
        self.service_results = {}
        self.module_results = {}
        self.architecture_compliance = {}
        self.recommendations = []
        self.critical_issues = []


class SystemHealthChecker:
    """
    Comprehensive System Health Checker
    Validates architecture compliance, service health, and module functionality
    """
    
    def __init__(self):
        self.logger = HealthLogger()
        self.result = SystemHealthResult()
        
        # Paths to check
        self.service_paths = {
            'frontend_service': '/home/mdoehler/aktienanalyse-ökosystem/services/frontend-service-modular',
            'account_service': '/home/mdoehler/aktienanalyse-ökosystem/services/broker-gateway-service-modular/modules/account_modules', 
            'order_service': '/home/mdoehler/aktienanalyse-ökosystem/services/broker-gateway-service-modular/modules/order_modules'
        }
        
        # Expected modules per service
        self.expected_modules = {
            'frontend_service': [
                'dashboard_handler.py',
                'market_data_handler.py', 
                'trading_handler.py',
                'gui_testing_handler.py'
            ],
            'account_service': [
                'account_balance_module.py',
                'single_balance_module.py',
                'transaction_history_module.py',
                'transaction_processing_module.py',
                'account_limits_module.py',
                'portfolio_summary_module.py',
                'trading_capacity_module.py',
                'current_usage_calculation_module.py',
                'event_handling_module.py',
                'balance_update_module.py',
                'withdrawal_processing_module.py',
                'risk_assessment_module.py',
                'account_verification_module.py',
                'account_settings_module.py'
            ],
            'order_service': [
                'active_orders_module.py',
                'order_cancellation_module.py', 
                'order_config_handler_module.py',
                'order_daily_limit_module.py',
                'order_execution_module.py',
                'order_history_module.py',
                'order_intelligence_handler_module.py',
                'order_market_data_handler_module.py',
                'order_modification_module.py',
                'order_placement_module.py',
                'order_risk_assessment_module.py',
                'order_simulation_module.py',
                'order_status_module.py',
                'order_system_alert_handler_module.py',
                'order_validation_module.py'
            ]
        }
        
        # Health check criteria
        self.health_criteria = {
            'file_exists': {'weight': 0.3, 'name': 'File Existence'},
            'syntax_valid': {'weight': 0.2, 'name': 'Python Syntax Valid'},
            'imports_valid': {'weight': 0.2, 'name': 'Import Dependencies Valid'},
            'class_structure': {'weight': 0.1, 'name': 'Class Structure Correct'},
            'event_bus_integration': {'weight': 0.1, 'name': 'Event-Bus Integration'},
            'code_quality': {'weight': 0.1, 'name': 'Code Quality Indicators'}
        }
    
    async def run_comprehensive_health_check(self) -> SystemHealthResult:
        """Run comprehensive system health check"""
        
        self.logger.info("🏥 Starting Comprehensive System Health Check...")
        
        # 1. Check Service Health
        await self._check_service_health()
        
        # 2. Check Module Health  
        await self._check_module_health()
        
        # 3. Check Architecture Compliance
        await self._check_architecture_compliance()
        
        # 4. Check System Integration
        await self._check_system_integration()
        
        # 5. Generate Recommendations
        await self._generate_recommendations()
        
        # 6. Calculate Overall Status
        self._calculate_overall_status()
        
        self.logger.info("🏥 System Health Check Completed")
        
        return self.result
    
    async def _check_service_health(self):
        """Check health of all services"""
        
        self.logger.info("Checking Service Health...")
        
        for service_name, service_path in self.service_paths.items():
            try:
                service_health = await self._check_single_service_health(service_name, service_path)
                self.result.service_results[service_name] = service_health
                self.result.services_checked += 1
                
                if service_health['status'] == 'healthy':
                    self.result.services_healthy += 1
                    self.logger.success(f"Service {service_name}: HEALTHY")
                elif service_health['status'] == 'warning':
                    self.result.services_warning += 1
                    self.logger.warning(f"Service {service_name}: WARNING")
                else:
                    self.result.services_error += 1
                    self.logger.error(f"Service {service_name}: ERROR")
                    
            except Exception as e:
                self.logger.error(f"Failed to check service {service_name}: {e}")
                self.result.services_error += 1
    
    async def _check_single_service_health(self, service_name: str, service_path: str) -> Dict[str, Any]:
        """Check health of a single service"""
        
        health_result = {
            'service_name': service_name,
            'path': service_path,
            'status': 'healthy',
            'modules_found': 0,
            'modules_expected': 0,
            'modules_healthy': 0,
            'issues': [],
            'score': 0.0
        }
        
        # Check if service path exists
        if not os.path.exists(service_path):
            health_result['status'] = 'error'
            health_result['issues'].append(f'Service path does not exist: {service_path}')
            return health_result
        
        # Check expected modules
        expected_modules = self.expected_modules.get(service_name, [])
        health_result['modules_expected'] = len(expected_modules)
        
        modules_found = 0
        modules_healthy = 0
        
        for module_file in expected_modules:
            module_path = os.path.join(service_path, module_file)
            
            if os.path.exists(module_path):
                modules_found += 1
                
                # Basic health check for module
                module_health = await self._check_module_file_health(module_path)
                if module_health['healthy']:
                    modules_healthy += 1
                else:
                    health_result['issues'].extend(module_health['issues'])
            else:
                health_result['issues'].append(f'Module not found: {module_file}')
        
        health_result['modules_found'] = modules_found
        health_result['modules_healthy'] = modules_healthy
        
        # Calculate service health score
        if expected_modules:
            completion_rate = modules_found / len(expected_modules)
            health_rate = modules_healthy / max(modules_found, 1)
            health_result['score'] = (completion_rate * 0.6 + health_rate * 0.4)
            
            # Determine status
            if health_result['score'] >= 0.9:
                health_result['status'] = 'healthy'
            elif health_result['score'] >= 0.7:
                health_result['status'] = 'warning'
            else:
                health_result['status'] = 'error'
        
        return health_result
    
    async def _check_module_file_health(self, module_path: str) -> Dict[str, Any]:
        """Check health of a single module file"""
        
        health_result = {
            'path': module_path,
            'healthy': True,
            'issues': [],
            'scores': {}
        }
        
        try:
            # Read file content
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check file size (too small might indicate incomplete module)
            if len(content) < 500:
                health_result['issues'].append('Module file suspiciously small (< 500 chars)')
                health_result['healthy'] = False
            
            # Check for required patterns
            required_patterns = [
                'class ',
                'def __init__',
                'async def execute_function',
                'SingleFunctionModule'
            ]
            
            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                health_result['issues'].append(f'Missing required patterns: {missing_patterns}')
                health_result['healthy'] = False
            
            # Check for Event-Bus integration
            event_bus_indicators = [
                'event_bus',
                'Event(',
                'await self.event_bus.publish',
                'process_event'
            ]
            
            event_bus_score = sum(1 for indicator in event_bus_indicators if indicator in content)
            health_result['scores']['event_bus_integration'] = event_bus_score / len(event_bus_indicators)
            
            # Check for error handling
            error_handling_indicators = [
                'try:',
                'except',
                'self.logger.error',
                'raise'
            ]
            
            error_handling_score = sum(1 for indicator in error_handling_indicators if indicator in content)
            health_result['scores']['error_handling'] = min(error_handling_score / 2, 1.0)  # Max 1.0
            
        except Exception as e:
            health_result['healthy'] = False
            health_result['issues'].append(f'Failed to read module file: {str(e)}')
        
        return health_result
    
    async def _check_module_health(self):
        """Check health of individual modules"""
        
        self.logger.info("Checking Individual Module Health...")
        
        total_modules = 0
        healthy_modules = 0
        
        for service_name, service_path in self.service_paths.items():
            if not os.path.exists(service_path):
                continue
                
            # Find all Python modules
            for py_file in Path(service_path).rglob("*.py"):
                if py_file.name.startswith('__'):
                    continue
                
                total_modules += 1
                module_health = await self._check_module_file_health(str(py_file))
                
                module_key = f"{service_name}:{py_file.name}"
                self.result.module_results[module_key] = module_health
                
                if module_health['healthy']:
                    healthy_modules += 1
        
        self.logger.success(f"Module Health: {healthy_modules}/{total_modules} healthy")
    
    async def _check_architecture_compliance(self):
        """Check architecture compliance"""
        
        self.logger.info("Checking Architecture Compliance...")
        
        compliance_results = {
            'single_function_pattern': 0.0,
            'event_bus_integration': 0.0,
            'file_structure': 0.0,
            'code_quality': 0.0
        }
        
        # Calculate compliance scores based on module results
        if self.result.module_results:
            event_bus_scores = []
            error_handling_scores = []
            
            for module_key, module_result in self.result.module_results.items():
                if 'scores' in module_result:
                    scores = module_result['scores']
                    if 'event_bus_integration' in scores:
                        event_bus_scores.append(scores['event_bus_integration'])
                    if 'error_handling' in scores:
                        error_handling_scores.append(scores['error_handling'])
            
            if event_bus_scores:
                compliance_results['event_bus_integration'] = sum(event_bus_scores) / len(event_bus_scores)
            
            if error_handling_scores:
                compliance_results['code_quality'] = sum(error_handling_scores) / len(error_handling_scores)
        
        # File structure compliance
        expected_total_modules = sum(len(modules) for modules in self.expected_modules.values())
        found_modules = len([m for m in self.result.module_results.values() if m['healthy']])
        compliance_results['file_structure'] = min(found_modules / max(expected_total_modules, 1), 1.0)
        
        # Single function pattern (based on healthy modules with proper structure)
        properly_structured = len([
            m for m in self.result.module_results.values() 
            if m['healthy'] and not any('Missing required patterns' in issue for issue in m['issues'])
        ])
        compliance_results['single_function_pattern'] = properly_structured / max(len(self.result.module_results), 1)
        
        self.result.architecture_compliance = compliance_results
        
        # Log compliance results
        for criterion, score in compliance_results.items():
            if score >= 0.8:
                self.logger.success(f"Architecture {criterion}: {score:.1%} ✅")
            elif score >= 0.6:
                self.logger.warning(f"Architecture {criterion}: {score:.1%} ⚠️")
            else:
                self.logger.error(f"Architecture {criterion}: {score:.1%} ❌")
    
    async def _check_system_integration(self):
        """Check system-level integration health"""
        
        self.logger.info("Checking System Integration...")
        
        integration_checks = {
            'event_bus_config': self._check_event_bus_config(),
            'service_dependencies': self._check_service_dependencies(),
            'shared_libraries': self._check_shared_libraries()
        }
        
        integration_issues = []
        
        for check_name, check_result in integration_checks.items():
            if not check_result['healthy']:
                integration_issues.extend(check_result['issues'])
                self.logger.warning(f"Integration Issue in {check_name}")
        
        if integration_issues:
            self.result.critical_issues.extend(integration_issues)
    
    def _check_event_bus_config(self) -> Dict[str, Any]:
        """Check Event-Bus configuration"""
        
        event_bus_path = '/home/mdoehler/aktienanalyse-ökosystem/shared/event_bus.py'
        
        if os.path.exists(event_bus_path):
            return {'healthy': True, 'issues': []}
        else:
            return {'healthy': False, 'issues': ['Event-Bus configuration file missing']}
    
    def _check_service_dependencies(self) -> Dict[str, Any]:
        """Check service dependencies"""
        
        shared_path = '/home/mdoehler/aktienanalyse-ökosystem/shared'
        
        if os.path.exists(shared_path):
            return {'healthy': True, 'issues': []}
        else:
            return {'healthy': False, 'issues': ['Shared libraries directory missing']}
    
    def _check_shared_libraries(self) -> Dict[str, Any]:
        """Check shared libraries availability"""
        
        required_shared = [
            '/home/mdoehler/aktienanalyse-ökosystem/shared/common_imports.py',
            '/home/mdoehler/aktienanalyse-ökosystem/services/broker-gateway-service-modular/modules/single_function_module_base.py'
        ]
        
        missing_files = []
        for required_file in required_shared:
            if not os.path.exists(required_file):
                missing_files.append(required_file)
        
        if missing_files:
            return {'healthy': False, 'issues': [f'Missing shared libraries: {missing_files}']}
        else:
            return {'healthy': True, 'issues': []}
    
    async def _generate_recommendations(self):
        """Generate recommendations based on health check results"""
        
        self.logger.info("Generating Recommendations...")
        
        recommendations = []
        
        # Service health recommendations
        error_services = [
            name for name, result in self.result.service_results.items() 
            if result['status'] == 'error'
        ]
        
        if error_services:
            recommendations.append(f"🔥 CRITICAL: Fix error services: {error_services}")
        
        warning_services = [
            name for name, result in self.result.service_results.items() 
            if result['status'] == 'warning'
        ]
        
        if warning_services:
            recommendations.append(f"⚠️ WARNING: Address issues in services: {warning_services}")
        
        # Architecture compliance recommendations
        compliance = self.result.architecture_compliance
        
        if compliance.get('event_bus_integration', 0) < 0.8:
            recommendations.append("📡 Improve Event-Bus integration in modules")
        
        if compliance.get('single_function_pattern', 0) < 0.8:
            recommendations.append("🔧 Fix Single Function Module pattern compliance")
        
        if compliance.get('code_quality', 0) < 0.7:
            recommendations.append("✨ Improve error handling and code quality")
        
        # Integration recommendations
        if self.result.critical_issues:
            recommendations.append(f"🚨 URGENT: Resolve critical issues: {len(self.result.critical_issues)} issues found")
        
        self.result.recommendations = recommendations
        
        # Log recommendations
        for rec in recommendations:
            if "CRITICAL" in rec or "URGENT" in rec:
                self.logger.error(rec)
            elif "WARNING" in rec:
                self.logger.warning(rec)
            else:
                self.logger.info(rec)
    
    def _calculate_overall_status(self):
        """Calculate overall system status"""
        
        # Calculate weighted score
        service_health_score = self.result.services_healthy / max(self.result.services_checked, 1)
        
        architecture_scores = list(self.result.architecture_compliance.values())
        architecture_score = sum(architecture_scores) / max(len(architecture_scores), 1) if architecture_scores else 0
        
        critical_issues_penalty = min(len(self.result.critical_issues) * 0.1, 0.3)
        
        overall_score = (service_health_score * 0.6 + architecture_score * 0.4) - critical_issues_penalty
        
        # Determine overall status
        if overall_score >= 0.9 and len(self.result.critical_issues) == 0:
            self.result.overall_status = "healthy"
        elif overall_score >= 0.7:
            self.result.overall_status = "warning"
        else:
            self.result.overall_status = "error"
        
        self.logger.info(f"Overall System Score: {overall_score:.1%}")
    
    def generate_health_report(self) -> str:
        """Generate comprehensive health report"""
        
        report = []
        report.append("=" * 80)
        report.append("🏥 SYSTEM HEALTH CHECK REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {self.result.timestamp.isoformat()}")
        report.append(f"Overall Status: {self.result.overall_status.upper()}")
        report.append("")
        
        # Service Health Summary
        report.append("📊 SERVICE HEALTH SUMMARY")
        report.append("-" * 40)
        report.append(f"Services Checked: {self.result.services_checked}")
        report.append(f"Healthy Services: {self.result.services_healthy}")
        report.append(f"Warning Services: {self.result.services_warning}")
        report.append(f"Error Services: {self.result.services_error}")
        report.append("")
        
        # Service Details
        report.append("🔍 SERVICE DETAILS")
        report.append("-" * 40)
        for service_name, service_result in self.result.service_results.items():
            status_emoji = {"healthy": "✅", "warning": "⚠️", "error": "❌"}[service_result['status']]
            report.append(f"{status_emoji} {service_name}: {service_result['status'].upper()}")
            report.append(f"   Modules: {service_result['modules_healthy']}/{service_result['modules_found']} healthy")
            report.append(f"   Score: {service_result['score']:.1%}")
            if service_result['issues']:
                for issue in service_result['issues'][:3]:  # Show top 3 issues
                    report.append(f"   - {issue}")
        report.append("")
        
        # Architecture Compliance
        report.append("🏗️ ARCHITECTURE COMPLIANCE")
        report.append("-" * 40)
        for criterion, score in self.result.architecture_compliance.items():
            emoji = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❌"
            report.append(f"{emoji} {criterion}: {score:.1%}")
        report.append("")
        
        # Recommendations
        if self.result.recommendations:
            report.append("💡 RECOMMENDATIONS")
            report.append("-" * 40)
            for i, rec in enumerate(self.result.recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        # Critical Issues
        if self.result.critical_issues:
            report.append("🚨 CRITICAL ISSUES")
            report.append("-" * 40)
            for i, issue in enumerate(self.result.critical_issues, 1):
                report.append(f"{i}. {issue}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


async def main():
    """Main health check execution"""
    
    print("🏥 System Health Checker - Aktienanalyse-Ökosystem")
    print("=" * 60)
    
    checker = SystemHealthChecker()
    result = await checker.run_comprehensive_health_check()
    
    # Generate and save report
    report = checker.generate_health_report()
    
    # Save to file
    report_path = "/home/mdoehler/aktienanalyse-ökosystem/SYSTEM_HEALTH_REPORT_2025_08_09.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print("📋 HEALTH CHECK SUMMARY")
    print("=" * 60)
    print(f"Overall Status: {result.overall_status.upper()}")
    print(f"Services Healthy: {result.services_healthy}/{result.services_checked}")
    print(f"Architecture Compliance: {sum(result.architecture_compliance.values())/len(result.architecture_compliance):.1%}")
    print(f"Critical Issues: {len(result.critical_issues)}")
    print(f"📄 Report saved to: {report_path}")
    
    return result.overall_status == "healthy"


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)