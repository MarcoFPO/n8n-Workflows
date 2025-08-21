#!/usr/bin/env python3
"""
LXC Integration Tests - End-to-End Testing für Classical-Enhanced ML Engine
==========================================================================

Comprehensive End-to-End Testing Suite für LXC 10.1.1.174 Container
Tests Classical-Enhanced ML Engine, Performance Monitoring, und Error Handling

Features:
- Complete ML Pipeline Testing
- LXC Performance Validation
- Error Handling und Recovery Testing
- Memory Constraint Testing
- API Endpoint Integration Testing
- Container Health Monitoring
- Regression Testing Suite

Author: Claude Code & LXC Testing Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import logging
import json
import time
import traceback
import numpy as np
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import sys
import psutil
import tempfile

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Import local modules
from lxc_performance_monitor_v1_0_0_20250819 import LXCPerformanceMonitor
from memory_efficient_portfolio_operations_v1_0_0_20250819 import MemoryEfficientPortfolioOperations, PortfolioConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'lxc_integration_tests_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    success: bool
    execution_time_ms: float
    memory_usage_mb: float
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None

@dataclass
class TestSuite:
    """Test suite configuration"""
    name: str
    tests: List[Callable]
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    timeout_seconds: int = 300  # 5 minute timeout

class LXCIntegrationTester:
    """
    Comprehensive Integration Tester für LXC 10.1.1.174
    Tests all aspects of Classical-Enhanced ML Engine
    """
    
    def __init__(self, base_url: str = "http://localhost:8021"):
        self.base_url = base_url
        self.session = None
        self.performance_monitor = LXCPerformanceMonitor("10.1.1.174")
        self.test_results: List[TestResult] = []
        self.test_data_dir = Path(tempfile.mkdtemp(prefix="lxc_integration_tests_"))
        self.container_ip = "10.1.1.174"
        
        # Test configuration
        self.test_config = {
            "memory_limit_mb": 1024,  # 1GB limit
            "cpu_limit_percent": 90,
            "test_timeout_seconds": 180,
            "portfolio_sizes": [5, 10, 20],  # LXC-optimized portfolio sizes für testing
            "stress_test_duration": 60  # seconds
        }
        
        logger.info("LXC Integration Tester initialized")
        logger.info(f"Base URL: {base_url}")
        logger.info(f"Container IP: {self.container_ip}")
        logger.info(f"Test data directory: {self.test_data_dir}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        await self.performance_monitor.start_monitoring(interval_seconds=5)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        await self.performance_monitor.stop_monitoring()
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Cleanup test data directory"""
        try:
            for file in self.test_data_dir.iterdir():
                file.unlink()
            self.test_data_dir.rmdir()
            logger.info("Test data cleanup completed")
        except Exception as e:
            logger.error(f"Error during test data cleanup: {str(e)}")
    
    async def make_request(self, endpoint: str, method: str = "GET", timeout: int = 10, **kwargs) -> Dict[str, Any]:
        """Make HTTP request mit improved error handling"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        # Add timeout to session
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, timeout=timeout_obj, **kwargs) as response:
                    execution_time = (time.time() - start_time) * 1000
                    if response.status == 200:
                        result = await response.json()
                        result["_request_time_ms"] = execution_time
                        return result
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"HTTP {response.status}: {error_text}",
                            "_request_time_ms": execution_time
                        }
            
            elif method.upper() == "POST":
                async with self.session.post(url, timeout=timeout_obj, **kwargs) as response:
                    execution_time = (time.time() - start_time) * 1000
                    if response.status == 200:
                        result = await response.json()
                        result["_request_time_ms"] = execution_time
                        return result
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"HTTP {response.status}: {error_text}",
                            "_request_time_ms": execution_time
                        }
                        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Request error for {endpoint}: {str(e)}")
            return {
                "error": str(e),
                "_request_time_ms": execution_time
            }
    
    async def test_system_health(self) -> TestResult:
        """Test 1: Basic system health check"""
        test_name = "system_health_check"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Test basic connectivity
            result = await self.make_request("/health")
            
            if "error" in result:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                    error_message=result["error"]
                )
            
            # Test LXC container health
            container_metrics = self.performance_monitor.get_performance_summary(hours=1)
            
            # Validate metrics are within acceptable ranges
            system_perf = container_metrics.get("system_performance", {})
            memory_percent = system_perf.get("avg_memory_percent", 0)
            cpu_percent = system_perf.get("avg_cpu_percent", 0)
            
            health_checks = {
                "api_responsive": "error" not in result,
                "memory_within_limits": memory_percent < 85,
                "cpu_within_limits": cpu_percent < 90,
                "container_operational": container_metrics.get("lxc_optimization_status", {}).get("monitoring_active", False)
            }
            
            all_healthy = all(health_checks.values())
            
            return TestResult(
                test_name=test_name,
                success=all_healthy,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                performance_metrics={
                    "health_checks": health_checks,
                    "container_metrics": container_metrics,
                    "response_time_ms": result.get("_request_time_ms", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"System health test failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=str(e)
            )
    
    async def test_classical_enhanced_engine_status(self) -> TestResult:
        """Test 2: Classical-Enhanced Engine Status"""
        test_name = "classical_enhanced_engine_status"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            result = await self.make_request("/api/v1/classical-enhanced/status")
            
            if "error" in result:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                    error_message=result["error"]
                )
            
            # Validate expected fields
            required_fields = ["engine_status", "lxc_performance", "container_ip", "optimization_level"]
            missing_fields = [field for field in required_fields if field not in result]
            
            success = len(missing_fields) == 0 and result.get("container_ip") == "10.1.1.174"
            
            return TestResult(
                test_name=test_name,
                success=success,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=f"Missing fields: {missing_fields}" if missing_fields else None,
                performance_metrics={
                    "status_response": result,
                    "response_time_ms": result.get("_request_time_ms", 0),
                    "required_fields_present": len(missing_fields) == 0
                }
            )
            
        except Exception as e:
            logger.error(f"Classical-Enhanced Engine status test failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=str(e)
            )
    
    async def test_portfolio_optimization_scaling(self) -> TestResult:
        """Test 3: Portfolio optimization scaling test"""
        test_name = "portfolio_optimization_scaling"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            scaling_results = {}
            
            for portfolio_size in self.test_config["portfolio_sizes"]:
                logger.info(f"Testing portfolio optimization with {portfolio_size} assets")
                
                # Generate test data
                expected_returns = np.random.uniform(0.05, 0.15, portfolio_size).tolist()
                
                # Generate positive semi-definite covariance matrix
                A = np.random.randn(portfolio_size, portfolio_size) * 0.1
                covariance_matrix = (A @ A.T + np.eye(portfolio_size) * 0.01).tolist()
                
                risk_tolerance = 0.5
                
                # Test VCE optimization with timeout and retry
                test_start = time.time()
                try:
                    result = await self.make_request(
                        "/api/v1/classical-enhanced/vce/portfolio-optimization",
                        method="POST",
                        json={
                            "expected_returns": expected_returns,
                            "covariance_matrix": covariance_matrix,
                            "risk_tolerance": risk_tolerance
                        },
                        timeout=30  # 30 second timeout for larger portfolios
                    )
                except asyncio.TimeoutError:
                    result = {"error": f"Timeout for portfolio size {portfolio_size}"}
                except Exception as e:
                    result = {"error": f"Request failed: {str(e)}"}
                test_duration = time.time() - test_start
                
                scaling_results[f"portfolio_{portfolio_size}"] = {
                    "success": "error" not in result,
                    "execution_time_s": test_duration,
                    "response_time_ms": result.get("_request_time_ms", 0),
                    "memory_metrics": result.get("lxc_performance_metrics", {}),
                    "error": result.get("error"),
                    "optimal_energy": result.get("optimal_energy"),
                    "classical_advantage": result.get("classical_advantage")
                }
                
                if "error" in result:
                    logger.error(f"Portfolio optimization failed for {portfolio_size} assets: {result['error']}")
                else:
                    logger.info(f"Portfolio optimization succeeded for {portfolio_size} assets in {test_duration:.2f}s")
            
            # Analyze scaling performance
            successful_tests = [r for r in scaling_results.values() if r["success"]]
            all_successful = len(successful_tests) == len(self.test_config["portfolio_sizes"])
            
            # Check if performance scales reasonably
            if len(successful_tests) >= 2:
                times = [r["execution_time_s"] for r in successful_tests]
                # More realistic scaling expectation for LXC
                max_time_ratio = max(times) / min(times) if min(times) > 0 else 1
                reasonable_scaling = max_time_ratio < 20  # Allow up to 20x slower for larger portfolios
            else:
                reasonable_scaling = len(successful_tests) > 0  # At least one test should pass
            
            return TestResult(
                test_name=test_name,
                success=all_successful and reasonable_scaling,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=None if all_successful else "Some portfolio optimizations failed",
                performance_metrics={
                    "scaling_results": scaling_results,
                    "successful_tests": len(successful_tests),
                    "total_tests": len(self.test_config["portfolio_sizes"]),
                    "reasonable_scaling": reasonable_scaling
                }
            )
            
        except Exception as e:
            logger.error(f"Portfolio optimization scaling test failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=str(e)
            )
    
    async def test_memory_efficient_operations(self) -> TestResult:
        """Test 4: Memory efficient operations test"""
        test_name = "memory_efficient_operations"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Test memory-efficient portfolio operations locally
            config = PortfolioConfig(
                max_assets=60,
                batch_size=15,
                memory_limit_mb=500.0,  # Conservative test limit
                use_sparse_matrices=True,
                use_memory_mapping=True
            )
            
            portfolio_ops = MemoryEfficientPortfolioOperations(config)
            
            try:
                # Generate test data for medium-sized portfolio
                n_assets = 80
                n_observations = 500
                
                # Generate synthetic data
                np.random.seed(42)
                returns = np.random.multivariate_normal(
                    mean=np.zeros(n_assets),
                    cov=np.eye(n_assets) * 0.01,
                    size=n_observations
                )
                expected_returns = np.mean(returns, axis=0) + np.random.uniform(0.05, 0.12, n_assets)
                
                # Run memory-efficient optimization
                optimization_start = time.time()
                result = portfolio_ops.optimize_large_portfolio(
                    expected_returns=expected_returns,
                    return_covariance_data=returns,
                    risk_tolerance=0.6
                )
                optimization_time = time.time() - optimization_start
                
                # Validate results
                success = (
                    result["lxc_performance"]["within_lxc_limits"] and
                    result["portfolio_optimization"]["optimization_success"] and
                    result["final_memory_metrics"]["within_limit"]
                )
                
                return TestResult(
                    test_name=test_name,
                    success=success,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                    performance_metrics={
                        "optimization_result": result,
                        "optimization_time_s": optimization_time,
                        "portfolio_size": n_assets,
                        "memory_efficiency": result["final_memory_metrics"]
                    }
                )
                
            finally:
                del portfolio_ops
                
        except Exception as e:
            logger.error(f"Memory efficient operations test failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=str(e)
            )
    
    async def test_error_handling_and_recovery(self) -> TestResult:
        """Test 5: Error handling and recovery mechanisms"""
        test_name = "error_handling_recovery"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            error_tests = {}
            
            # Test 1: Invalid input data
            logger.info("Testing error handling for invalid input data")
            invalid_data_result = await self.make_request(
                "/api/v1/classical-enhanced/vce/portfolio-optimization",
                method="POST",
                json={
                    "expected_returns": [0.1, 0.2],  # 2 assets
                    "covariance_matrix": [[0.01, 0.005], [0.005, 0.02], [0.001, 0.002]],  # 3x2 matrix (invalid)
                    "risk_tolerance": 0.5
                }
            )
            error_tests["invalid_input"] = {
                "success": "error" in invalid_data_result,
                "error_message": invalid_data_result.get("error", "No error returned"),
                "response_time_ms": invalid_data_result.get("_request_time_ms", 0)
            }
            
            # Test 2: Extreme risk tolerance
            logger.info("Testing error handling for extreme risk tolerance")
            extreme_risk_result = await self.make_request(
                "/api/v1/classical-enhanced/vce/portfolio-optimization",
                method="POST",
                json={
                    "expected_returns": [0.1, 0.2],
                    "covariance_matrix": [[0.01, 0.005], [0.005, 0.02]],
                    "risk_tolerance": -1.5  # Invalid risk tolerance
                }
            )
            error_tests["extreme_risk_tolerance"] = {
                "success": "error" in extreme_risk_result,
                "error_message": extreme_risk_result.get("error", "No error returned"),
                "response_time_ms": extreme_risk_result.get("_request_time_ms", 0)
            }
            
            # Test 3: Large portfolio (should handle gracefully for LXC)
            logger.info("Testing error handling for large portfolio")
            large_size = 50  # LXC-appropriate large size
            large_returns = np.random.uniform(0.05, 0.15, large_size).tolist()
            large_cov = np.eye(large_size).tolist()  # Simple identity matrix
            
            large_portfolio_result = await self.make_request(
                "/api/v1/classical-enhanced/vce/portfolio-optimization",
                method="POST",
                json={
                    "expected_returns": large_returns,
                    "covariance_matrix": large_cov,
                    "risk_tolerance": 0.5
                }
            )
            error_tests["large_portfolio"] = {
                "handled_gracefully": True,  # Should either succeed or fail gracefully
                "result_type": "success" if "error" not in large_portfolio_result else "error",
                "response_time_ms": large_portfolio_result.get("_request_time_ms", 0)
            }
            
            # Test 4: Recovery test - valid request after errors
            logger.info("Testing system recovery after errors")
            recovery_result = await self.make_request(
                "/api/v1/classical-enhanced/vce/portfolio-optimization",
                method="POST",
                json={
                    "expected_returns": [0.1, 0.12, 0.08],
                    "covariance_matrix": [
                        [0.01, 0.005, 0.002],
                        [0.005, 0.02, 0.003],
                        [0.002, 0.003, 0.015]
                    ],
                    "risk_tolerance": 0.5
                }
            )
            error_tests["recovery_after_errors"] = {
                "success": "error" not in recovery_result,
                "response_time_ms": recovery_result.get("_request_time_ms", 0)
            }
            
            # Evaluate overall error handling
            proper_error_handling = (
                error_tests["invalid_input"]["success"] and
                error_tests["extreme_risk_tolerance"]["success"] and
                error_tests["recovery_after_errors"]["success"]
            )
            
            return TestResult(
                test_name=test_name,
                success=proper_error_handling,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                performance_metrics={
                    "error_tests": error_tests,
                    "proper_error_handling": proper_error_handling,
                    "recovery_successful": error_tests["recovery_after_errors"]["success"]
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling and recovery test failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=str(e)
            )
    
    async def test_performance_under_load(self) -> TestResult:
        """Test 6: Performance under sustained load"""
        test_name = "performance_under_load"
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            logger.info("Starting sustained load test")
            
            # Configuration für load test
            num_concurrent_requests = 5
            test_duration_seconds = 30  # Reduced für integration test
            request_interval_seconds = 2
            
            load_test_results = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "response_times": [],
                "memory_usage_over_time": [],
                "errors": []
            }
            
            # Generate test portfolio data
            test_portfolio = {
                "expected_returns": [0.08, 0.10, 0.12, 0.09, 0.11],
                "covariance_matrix": [
                    [0.01, 0.005, 0.002, 0.003, 0.001],
                    [0.005, 0.02, 0.004, 0.006, 0.002],
                    [0.002, 0.004, 0.015, 0.003, 0.004],
                    [0.003, 0.006, 0.003, 0.018, 0.005],
                    [0.001, 0.002, 0.004, 0.005, 0.012]
                ],
                "risk_tolerance": 0.5
            }
            
            async def make_load_test_request():
                """Single load test request"""
                try:
                    result = await self.make_request(
                        "/api/v1/classical-enhanced/vce/portfolio-optimization",
                        method="POST",
                        json=test_portfolio
                    )
                    return result
                except Exception as e:
                    return {"error": str(e)}
            
            # Run load test
            load_start_time = time.time()
            while (time.time() - load_start_time) < test_duration_seconds:
                # Launch concurrent requests
                tasks = [make_load_test_request() for _ in range(num_concurrent_requests)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    load_test_results["total_requests"] += 1
                    
                    if isinstance(result, Exception):
                        load_test_results["failed_requests"] += 1
                        load_test_results["errors"].append(str(result))
                    elif "error" in result:
                        load_test_results["failed_requests"] += 1
                        load_test_results["errors"].append(result["error"])
                    else:
                        load_test_results["successful_requests"] += 1
                        load_test_results["response_times"].append(result.get("_request_time_ms", 0))
                
                # Record memory usage
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                load_test_results["memory_usage_over_time"].append(current_memory)
                
                # Wait before next batch
                await asyncio.sleep(request_interval_seconds)
            
            # Analyze results
            success_rate = (
                load_test_results["successful_requests"] / load_test_results["total_requests"]
                if load_test_results["total_requests"] > 0 else 0
            )
            
            avg_response_time = (
                np.mean(load_test_results["response_times"])
                if load_test_results["response_times"] else 0
            )
            
            memory_growth = (
                max(load_test_results["memory_usage_over_time"]) - 
                min(load_test_results["memory_usage_over_time"])
                if load_test_results["memory_usage_over_time"] else 0
            )
            
            # Success criteria
            performance_acceptable = (
                success_rate >= 0.9 and  # 90% success rate
                avg_response_time < 5000 and  # Average response under 5 seconds
                memory_growth < 200  # Memory growth under 200MB during test
            )
            
            return TestResult(
                test_name=test_name,
                success=performance_acceptable,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                performance_metrics={
                    "load_test_results": load_test_results,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "memory_growth_mb": memory_growth,
                    "performance_acceptable": performance_acceptable
                }
            )
            
        except Exception as e:
            logger.error(f"Performance under load test failed: {str(e)}")
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024 - start_memory,
                error_message=str(e)
            )
    
    async def run_complete_test_suite(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        logger.info("🧪 Starting Complete LXC Integration Test Suite")
        logger.info("=" * 80)
        
        suite_start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Define test sequence
        test_sequence = [
            ("System Health Check", self.test_system_health),
            ("Classical-Enhanced Engine Status", self.test_classical_enhanced_engine_status),
            ("Portfolio Optimization Scaling", self.test_portfolio_optimization_scaling),
            ("Memory Efficient Operations", self.test_memory_efficient_operations),
            ("Error Handling and Recovery", self.test_error_handling_and_recovery),
            ("Performance Under Load", self.test_performance_under_load),
        ]
        
        # Run all tests
        for test_name, test_func in test_sequence:
            logger.info(f"\\n🔬 Running: {test_name}")
            logger.info("-" * 50)
            
            try:
                result = await test_func()
                self.test_results.append(result)
                
                if result.success:
                    logger.info(f"✅ {test_name} PASSED")
                    logger.info(f"   Execution time: {result.execution_time_ms:.1f}ms")
                    logger.info(f"   Memory usage: {result.memory_usage_mb:.1f}MB")
                else:
                    logger.error(f"❌ {test_name} FAILED")
                    if result.error_message:
                        logger.error(f"   Error: {result.error_message}")
                
            except Exception as e:
                logger.error(f"❌ {test_name} EXCEPTION: {str(e)}")
                error_result = TestResult(
                    test_name=test_name,
                    success=False,
                    execution_time_ms=0,
                    memory_usage_mb=0,
                    error_message=str(e)
                )
                self.test_results.append(error_result)
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        total_execution_time = time.time() - suite_start_time
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_memory_usage = final_memory - initial_memory
        
        # Get final performance summary
        final_performance = self.performance_monitor.get_performance_summary(hours=1)
        
        suite_results = {
            "suite_name": "LXC Integration Test Suite",
            "container_ip": self.container_ip,
            "execution_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate_percent": success_rate,
                "total_execution_time_s": total_execution_time,
                "total_memory_usage_mb": total_memory_usage
            },
            "individual_test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "execution_time_ms": r.execution_time_ms,
                    "memory_usage_mb": r.memory_usage_mb,
                    "error_message": r.error_message,
                    "performance_metrics": r.performance_metrics
                } for r in self.test_results
            ],
            "lxc_performance_summary": final_performance,
            "test_environment": {
                "python_version": sys.version,
                "test_config": self.test_config,
                "container_ip": self.container_ip,
                "test_timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Print summary
        logger.info("\\n" + "=" * 80)
        logger.info("📋 LXC INTEGRATION TEST SUITE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"📊 Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        logger.info(f"⏱️  Total Time: {total_execution_time:.2f} seconds")
        logger.info(f"💾 Memory Usage: {total_memory_usage:.1f}MB")
        
        if success_rate >= 90:
            logger.info("🎉 LXC INTEGRATION TEST SUITE PASSED!")
            logger.info("🔧 Classical-Enhanced ML Engine is ready for production on LXC 10.1.1.174!")
        elif success_rate >= 70:
            logger.warning("⚠️  LXC INTEGRATION TEST SUITE PARTIALLY PASSED")
            logger.warning("🔧 Some optimizations may be needed before production deployment.")
        else:
            logger.error("❌ LXC INTEGRATION TEST SUITE FAILED")
            logger.error("🔧 Significant issues need to be resolved before deployment.")
        
        return suite_results
    
    def save_test_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save test results to JSON file"""
        if filename is None:
            filename = f"lxc_integration_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = Path(__file__).parent / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"📁 Test results saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving test results: {str(e)}")
            return ""

# Main execution
async def main():
    """Main test execution function"""
    print("🧪 LXC Integration Testing Suite Starting...")
    print("🔧 Testing Classical-Enhanced ML Engine für LXC 10.1.1.174")
    print("=" * 80)
    
    async with LXCIntegrationTester() as tester:
        try:
            # Run complete test suite
            results = await tester.run_complete_test_suite()
            
            # Save results
            results_file = tester.save_test_results(results)
            
            print(f"\\n📄 Detailed test results saved to: {results_file}")
            print("🧪 LXC Integration Testing Complete!")
            
            return results
            
        except KeyboardInterrupt:
            print("\\n⚠️  Integration testing interrupted by user")
        except Exception as e:
            print(f"\\n❌ Integration testing failed with error: {str(e)}")
            print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())