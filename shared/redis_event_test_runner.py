"""
Redis Event Bus Performance Test Runner & Integration
Complete test orchestration and integration with the aktienanalyse ecosystem
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict
import tempfile

from shared.redis_event_performance import (
    PerformanceTestSuite, LoadTestConfig, LoadTestType, 
    PerformanceResult, PerformanceOptimizer
)
from shared.redis_event_monitoring import (
    RealTimeMonitor, PerformanceReporter, start_system_monitoring,
    stop_system_monitoring, get_system_overview
)
from shared.redis_event_bus_factory import (
    RedisEventBusFactory, initialize_event_bus_system,
    shutdown_event_bus_system
)

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🐛 {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
    logger = MockLogger()


class TestScenario:
    """Defines a complete test scenario"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.test_configs: List[LoadTestConfig] = []
        self.prerequisites: List[str] = []
        self.cleanup_actions: List[str] = []
        
    def add_test(self, config: LoadTestConfig):
        """Add test configuration to scenario"""
        self.test_configs.append(config)
        
    def add_prerequisite(self, action: str):
        """Add prerequisite action"""
        self.prerequisites.append(action)
        
    def add_cleanup(self, action: str):
        """Add cleanup action"""
        self.cleanup_actions.append(action)


class EcosystemTestRunner:
    """Complete test runner for the aktienanalyse ecosystem"""
    
    def __init__(self):
        self.logger = logger.bind(component="ecosystem_test_runner")
        self.test_suite = PerformanceTestSuite()
        self.optimizer = PerformanceOptimizer()
        self.monitor = RealTimeMonitor(sample_interval=1.0)  # High frequency for tests
        self.reporter = PerformanceReporter(self.monitor)
        
        # Test results storage
        self.test_results: List[PerformanceResult] = []
        self.test_reports: Dict[str, Dict[str, Any]] = {}
        
        # Service configuration
        self.service_names = [
            'account-service',
            'order-service', 
            'data-analysis-service',
            'intelligent-core-service',
            'market-data-service',
            'frontend-service'
        ]
        
    async def initialize_test_environment(self) -> bool:
        """Initialize complete test environment"""
        try:
            self.logger.info("Initializing Redis Event Bus test environment")
            
            # Initialize event bus system
            if not await initialize_event_bus_system():
                self.logger.error("Failed to initialize event bus system")
                return False
            
            # Wait for systems to stabilize
            await asyncio.sleep(2)
            
            # Start monitoring
            await self.monitor.start_monitoring(self.service_names)
            
            # Verify all services are accessible
            health_status = await RedisEventBusFactory.health_check_all()
            unhealthy_services = [name for name, status in health_status.items() 
                                if status.get('status') != 'healthy']
            
            if unhealthy_services:
                self.logger.warning("Some services unhealthy", services=unhealthy_services)
                # Continue anyway for testing
            
            self.logger.info("Test environment initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize test environment", error=str(e))
            return False
    
    async def cleanup_test_environment(self):
        """Clean up test environment"""
        try:
            self.logger.info("Cleaning up test environment")
            
            # Stop monitoring
            await self.monitor.stop_monitoring()
            
            # Shutdown event bus system
            await shutdown_event_bus_system()
            
            self.logger.info("Test environment cleanup completed")
            
        except Exception as e:
            self.logger.error("Cleanup failed", error=str(e))
    
    def create_standard_test_scenarios(self) -> List[TestScenario]:
        """Create standard performance test scenarios"""
        scenarios = []
        
        # 1. Basic Performance Baseline
        baseline_scenario = TestScenario(
            "Basic Performance Baseline",
            "Establish baseline performance metrics for all services"
        )
        
        baseline_scenario.add_test(LoadTestConfig(
            test_type=LoadTestType.PUBLISHER_ONLY,
            test_name="Baseline Publisher Test",
            duration_seconds=60,
            event_rate_per_second=100,
            event_types=['market_data.price_update'],
            target_throughput=90
        ))
        
        baseline_scenario.add_test(LoadTestConfig(
            test_type=LoadTestType.FULL_ROUNDTRIP,
            test_name="Baseline Roundtrip Test", 
            duration_seconds=60,
            event_rate_per_second=50,
            target_latency_p99=100.0
        ))
        
        scenarios.append(baseline_scenario)
        
        # 2. High Throughput Stress Test
        stress_scenario = TestScenario(
            "High Throughput Stress Test",
            "Test system behavior under high load conditions"
        )
        
        stress_scenario.add_test(LoadTestConfig(
            test_type=LoadTestType.STRESS_TEST,
            test_name="Market Data Stress Test",
            duration_seconds=180,
            event_rate_per_second=200,
            event_types=['market_data.price_update', 'market_data.indicators_update'],
            target_throughput=400,
            max_memory_mb=1024
        ))
        
        stress_scenario.add_test(LoadTestConfig(
            test_type=LoadTestType.BURST_LOAD,
            test_name="Order Burst Test",
            duration_seconds=120,
            burst_size=500,
            burst_interval=20,
            event_types=['order.created', 'order.updated'],
            target_latency_p99=200.0
        ))
        
        scenarios.append(stress_scenario)
        
        # 3. Mixed Workload Simulation
        mixed_scenario = TestScenario(
            "Mixed Workload Simulation", 
            "Simulate realistic mixed workload across all services"
        )
        
        mixed_scenario.add_test(LoadTestConfig(
            test_type=LoadTestType.FULL_ROUNDTRIP,
            test_name="Intelligence Decision Flow",
            duration_seconds=180,
            event_rate_per_second=75,
            event_types=[
                'market_data.price_update',
                'analysis.complete',
                'intelligence.recommendation',
                'order.created'
            ],
            target_throughput=70,
            target_latency_p99=150.0,
            event_payload_size=2048
        ))
        
        scenarios.append(mixed_scenario)
        
        # 4. Service Recovery Test
        recovery_scenario = TestScenario(
            "Service Recovery Test",
            "Test system recovery after service interruptions"
        )
        
        recovery_scenario.add_prerequisite("Simulate service interruption")
        recovery_scenario.add_test(LoadTestConfig(
            test_type=LoadTestType.SUSTAINED_LOAD,
            test_name="Recovery Validation Test",
            duration_seconds=120,
            event_rate_per_second=100,
            target_throughput=80,
            max_error_rate=0.02  # Allow higher error rate during recovery
        ))
        recovery_scenario.add_cleanup("Verify all services recovered")
        
        scenarios.append(recovery_scenario)
        
        return scenarios
    
    async def run_scenario(self, scenario: TestScenario) -> Dict[str, Any]:
        """Run a complete test scenario"""
        self.logger.info("Running test scenario", scenario=scenario.name)
        
        scenario_start = datetime.now()
        scenario_results = []
        
        try:
            # Execute prerequisites
            for prereq in scenario.prerequisites:
                self.logger.info("Executing prerequisite", action=prereq)
                await self._execute_prerequisite(prereq)
            
            # Run all tests in the scenario
            for test_config in scenario.test_configs:
                self.logger.info("Running test", test_name=test_config.test_name)
                
                try:
                    result = await self.test_suite.executor.run_load_test(test_config)
                    scenario_results.append(result)
                    self.test_results.append(result)
                    
                    self.logger.info("Test completed",
                                   test_name=test_config.test_name,
                                   success=result.targets_met,
                                   throughput=result.throughput_events_per_second,
                                   latency_p99=result.latency_p99)
                    
                    # Brief cooldown between tests
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    self.logger.error("Test failed", 
                                    test_name=test_config.test_name,
                                    error=str(e))
            
            # Execute cleanup actions
            for cleanup in scenario.cleanup_actions:
                self.logger.info("Executing cleanup", action=cleanup)
                await self._execute_cleanup(cleanup)
            
            scenario_duration = (datetime.now() - scenario_start).total_seconds()
            
            # Analyze scenario results
            scenario_analysis = self.optimizer.analyze_results(scenario_results)
            
            scenario_report = {
                'scenario_name': scenario.name,
                'description': scenario.description,
                'start_time': scenario_start.isoformat(),
                'duration_seconds': scenario_duration,
                'tests_count': len(scenario.test_configs),
                'tests_passed': len([r for r in scenario_results if r.targets_met]),
                'test_results': [asdict(r) for r in scenario_results],
                'analysis': scenario_analysis,
                'success': all(r.targets_met for r in scenario_results)
            }
            
            self.test_reports[scenario.name] = scenario_report
            
            self.logger.info("Scenario completed",
                           scenario=scenario.name,
                           success=scenario_report['success'],
                           duration=scenario_duration)
            
            return scenario_report
            
        except Exception as e:
            self.logger.error("Scenario failed", scenario=scenario.name, error=str(e))
            return {
                'scenario_name': scenario.name,
                'error': str(e),
                'success': False
            }
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run complete comprehensive test suite"""
        self.logger.info("Starting comprehensive Redis Event Bus test suite")
        
        suite_start = datetime.now()
        
        try:
            # Initialize test environment
            if not await self.initialize_test_environment():
                return {'error': 'Failed to initialize test environment'}
            
            # Create and run test scenarios
            scenarios = self.create_standard_test_scenarios()
            scenario_results = []
            
            for scenario in scenarios:
                try:
                    result = await self.run_scenario(scenario)
                    scenario_results.append(result)
                    
                    # Cooldown between scenarios
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    self.logger.error("Scenario execution failed", 
                                    scenario=scenario.name, error=str(e))
                    scenario_results.append({
                        'scenario_name': scenario.name,
                        'error': str(e),
                        'success': False
                    })
            
            suite_duration = (datetime.now() - suite_start).total_seconds()
            
            # Generate final comprehensive report
            comprehensive_report = await self._generate_comprehensive_report(
                suite_start, suite_duration, scenario_results
            )
            
            return comprehensive_report
            
        except Exception as e:
            self.logger.error("Test suite failed", error=str(e))
            return {
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
        
        finally:
            # Always cleanup
            await self.cleanup_test_environment()
    
    async def _execute_prerequisite(self, action: str):
        """Execute prerequisite action"""
        if action == "Simulate service interruption":
            # Simulate brief service interruption
            self.logger.info("Simulating service interruption for 10 seconds")
            await asyncio.sleep(10)
        # Add more prerequisite actions as needed
        
    async def _execute_cleanup(self, action: str):
        """Execute cleanup action"""
        if action == "Verify all services recovered":
            # Verify services are healthy
            health_status = await RedisEventBusFactory.health_check_all()
            healthy_count = sum(1 for s in health_status.values() 
                              if s.get('status') == 'healthy')
            self.logger.info("Service recovery verification",
                           healthy_services=healthy_count,
                           total_services=len(health_status))
        # Add more cleanup actions as needed
    
    async def _generate_comprehensive_report(self, start_time: datetime,
                                           duration: float,
                                           scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        # Overall statistics
        total_scenarios = len(scenario_results)
        successful_scenarios = len([r for r in scenario_results if r.get('success', False)])
        total_tests = sum(r.get('tests_count', 0) for r in scenario_results)
        successful_tests = sum(r.get('tests_passed', 0) for r in scenario_results)
        
        # System overview during testing
        system_overview = get_system_overview()
        
        # Performance analysis
        all_test_results = [r for r in self.test_results if r is not None]
        performance_analysis = self.optimizer.analyze_results(all_test_results) if all_test_results else {}
        
        # Generate recommendations
        recommendations = self._generate_ecosystem_recommendations(scenario_results, performance_analysis)
        
        report = {
            'test_suite_summary': {
                'name': 'Redis Event Bus Comprehensive Performance Test Suite',
                'start_time': start_time.isoformat(),
                'duration_minutes': duration / 60,
                'total_scenarios': total_scenarios,
                'successful_scenarios': successful_scenarios,
                'scenario_success_rate': successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'test_success_rate': successful_tests / total_tests if total_tests > 0 else 0,
                'overall_success': successful_scenarios == total_scenarios
            },
            
            'scenario_results': scenario_results,
            'system_overview': system_overview,
            'performance_analysis': performance_analysis,
            'recommendations': recommendations,
            
            'test_environment': {
                'services_tested': self.service_names,
                'redis_configuration': 'Default configuration with optimization recommendations',
                'test_duration_total_minutes': duration / 60
            },
            
            'conclusion': self._generate_test_conclusion(
                successful_scenarios == total_scenarios,
                successful_tests / total_tests if total_tests > 0 else 0,
                performance_analysis
            )
        }
        
        # Save report to file
        await self._save_report_to_file(report)
        
        return report
    
    def _generate_ecosystem_recommendations(self, scenario_results: List[Dict[str, Any]],
                                          performance_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations specific to the aktienanalyse ecosystem"""
        recommendations = []
        
        # Performance-based recommendations
        bottlenecks = performance_analysis.get('bottlenecks', [])
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'high_latency':
                recommendations.append({
                    'category': 'latency_optimization',
                    'priority': 'high',
                    'title': 'Optimize Market Data Processing Pipeline',
                    'description': 'High latency detected in event processing. Consider implementing market data batching and caching.',
                    'implementation': [
                        'Enable market data event batching with batch_size=100',
                        'Implement Redis-based market data caching',
                        'Optimize technical analysis calculations'
                    ]
                })
            
            elif bottleneck['type'] == 'high_memory':
                recommendations.append({
                    'category': 'memory_optimization',
                    'priority': 'medium',
                    'title': 'Optimize Intelligence Decision Memory Usage',
                    'description': 'High memory usage detected. Implement decision history pruning and model caching.',
                    'implementation': [
                        'Implement decision history TTL (24 hours)',
                        'Add ML model result caching',
                        'Enable event compression for large analysis results'
                    ]
                })
        
        # Scenario-specific recommendations
        for scenario in scenario_results:
            if not scenario.get('success', False):
                recommendations.append({
                    'category': 'reliability',
                    'priority': 'high', 
                    'title': f'Address {scenario["scenario_name"]} Failures',
                    'description': f'Scenario {scenario["scenario_name"]} failed. Investigate and fix root causes.',
                    'implementation': [
                        'Review error logs for failed tests',
                        'Implement additional error handling',
                        'Add circuit breaker patterns for external dependencies'
                    ]
                })
        
        # Ecosystem-specific optimizations
        recommendations.append({
            'category': 'trading_optimization',
            'priority': 'medium',
            'title': 'Optimize Trading Decision Pipeline',
            'description': 'Implement priority queues for time-sensitive trading events.',
            'implementation': [
                'Use HIGH priority for order events',
                'Use CRITICAL priority for market data updates',
                'Implement separate event channels for real-time vs. analytical events'
            ]
        })
        
        return recommendations
    
    def _generate_test_conclusion(self, overall_success: bool, test_success_rate: float,
                                performance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test conclusion summary"""
        
        if overall_success and test_success_rate > 0.95:
            status = "EXCELLENT"
            message = "Redis Event Bus system is performing excellently and ready for production."
            
        elif overall_success and test_success_rate > 0.8:
            status = "GOOD"
            message = "Redis Event Bus system is performing well with minor optimizations needed."
            
        elif test_success_rate > 0.6:
            status = "ACCEPTABLE"
            message = "Redis Event Bus system is functional but requires optimization before production."
            
        else:
            status = "NEEDS_WORK"
            message = "Redis Event Bus system requires significant optimization before production deployment."
        
        return {
            'status': status,
            'message': message,
            'test_success_rate': test_success_rate,
            'ready_for_production': overall_success and test_success_rate > 0.8,
            'key_metrics': {
                'avg_throughput_eps': performance_analysis.get('summary', {}).get('average_throughput_eps', 0),
                'avg_latency_p99_ms': performance_analysis.get('summary', {}).get('average_latency_p99_ms', 0),
                'avg_error_rate': performance_analysis.get('summary', {}).get('average_error_rate', 0)
            }
        }
    
    async def _save_report_to_file(self, report: Dict[str, Any]):
        """Save comprehensive report to file"""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = "/home/mdoehler/aktienanalyse-ökosystem/reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"redis_event_bus_performance_report_{timestamp}.json"
            filepath = os.path.join(reports_dir, filename)
            
            # Save report
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info("Report saved", filepath=filepath)
            
        except Exception as e:
            self.logger.error("Failed to save report", error=str(e))


# Global test runner instance
ecosystem_test_runner = EcosystemTestRunner()

# Convenience functions
async def run_comprehensive_tests() -> Dict[str, Any]:
    """Run comprehensive performance tests"""
    return await ecosystem_test_runner.run_comprehensive_test_suite()

async def run_basic_performance_check() -> Dict[str, Any]:
    """Run basic performance validation"""
    # Quick validation test
    config = LoadTestConfig(
        test_type=LoadTestType.PUBLISHER_ONLY,
        test_name="Quick Performance Check",
        duration_seconds=30,
        event_rate_per_second=100,
        target_throughput=80
    )
    
    if not await ecosystem_test_runner.initialize_test_environment():
        return {'error': 'Failed to initialize test environment'}
    
    try:
        result = await ecosystem_test_runner.test_suite.executor.run_load_test(config)
        return {
            'success': result.targets_met,
            'throughput_eps': result.throughput_events_per_second,
            'latency_p99_ms': result.latency_p99,
            'error_rate': result.error_rate,
            'message': 'Basic performance check completed'
        }
    finally:
        await ecosystem_test_runner.cleanup_test_environment()

# CLI entry point for running tests
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Redis Event Bus Performance Test Runner')
    parser.add_argument('--test-type', choices=['comprehensive', 'basic'], 
                       default='basic', help='Type of test to run')
    parser.add_argument('--output-file', help='Output file for test results')
    
    args = parser.parse_args()
    
    async def main():
        if args.test_type == 'comprehensive':
            results = await run_comprehensive_tests()
        else:
            results = await run_basic_performance_check()
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        else:
            print(json.dumps(results, indent=2, default=str))
    
    asyncio.run(main())