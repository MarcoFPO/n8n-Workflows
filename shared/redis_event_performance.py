"""
Redis Event Bus Performance Optimization & Load Testing
Comprehensive performance testing and optimization tools for the event bus
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

import asyncio
import time
import statistics
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import concurrent.futures
import threading
import queue
import psutil
import gc

from shared.redis_event_bus import RedisEventBus, Event, EventMetadata, EventPriority
from shared.redis_event_bus_factory import get_event_bus, ServiceEventBusRegistry
from shared.redis_event_publishers import PublisherFactory
from shared.redis_event_subscribers import SubscriberFactory

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


class LoadTestType(Enum):
    """Types of load tests"""
    PUBLISHER_ONLY = "publisher_only"
    SUBSCRIBER_ONLY = "subscriber_only"
    FULL_ROUNDTRIP = "full_roundtrip"
    BURST_LOAD = "burst_load"
    SUSTAINED_LOAD = "sustained_load"
    STRESS_TEST = "stress_test"


class PerformanceMetricType(Enum):
    """Performance metric types"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    NETWORK_IO = "network_io"


@dataclass
class LoadTestConfig:
    """Configuration for load tests"""
    test_type: LoadTestType
    test_name: str
    duration_seconds: int = 60
    event_rate_per_second: int = 100
    concurrent_publishers: int = 1
    concurrent_subscribers: int = 1
    event_payload_size: int = 1024
    event_types: List[str] = None
    priority_distribution: Dict[str, float] = None
    
    # Advanced settings
    ramp_up_seconds: int = 10
    ramp_down_seconds: int = 10
    burst_size: int = 1000
    burst_interval: int = 30
    
    # Performance targets
    target_latency_p99: float = 100.0  # ms
    target_throughput: int = 1000      # events/sec
    max_error_rate: float = 0.01       # 1%
    max_memory_mb: int = 512


@dataclass
class PerformanceResult:
    """Result of a performance test"""
    test_name: str
    test_type: LoadTestType
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Core metrics
    events_sent: int
    events_received: int
    events_failed: int
    
    # Latency metrics (milliseconds)
    latency_min: float
    latency_max: float
    latency_mean: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    
    # Throughput metrics
    throughput_events_per_second: float
    peak_throughput: float
    
    # Error metrics
    error_rate: float
    error_types: Dict[str, int]
    
    # System metrics
    peak_memory_mb: float
    peak_cpu_percent: float
    network_bytes_sent: int
    network_bytes_received: int
    
    # Performance targets compliance
    targets_met: bool
    target_violations: List[str]


class PerformanceMonitor:
    """Monitors system performance during tests"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics_history: List[Dict[str, Any]] = []
        self.sample_interval = 1.0  # seconds
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Process monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.initial_cpu_time = self.process.cpu_times()
        self.initial_network = psutil.net_io_counters()
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.metrics_history.clear()
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        summary = self._calculate_summary()
        logger.info("Performance monitoring stopped", summary=summary)
        return summary
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                await asyncio.sleep(self.sample_interval)
        except asyncio.CancelledError:
            pass
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            # Memory metrics
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # CPU metrics
            cpu_percent = self.process.cpu_percent()
            
            # Network metrics
            network = psutil.net_io_counters()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'memory_mb': memory_mb,
                'cpu_percent': cpu_percent,
                'network_bytes_sent': network.bytes_sent - self.initial_network.bytes_sent,
                'network_bytes_recv': network.bytes_recv - self.initial_network.bytes_recv,
                'gc_count': len(gc.get_objects())
            }
        except Exception as e:
            logger.warning("Failed to collect metrics", error=str(e))
            return {'error': str(e)}
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary from collected metrics"""
        if not self.metrics_history:
            return {}
        
        # Extract values for calculations
        memory_values = [m.get('memory_mb', 0) for m in self.metrics_history if 'memory_mb' in m]
        cpu_values = [m.get('cpu_percent', 0) for m in self.metrics_history if 'cpu_percent' in m]
        
        if not memory_values or not cpu_values:
            return {'error': 'No valid metrics collected'}
        
        return {
            'peak_memory_mb': max(memory_values),
            'avg_memory_mb': statistics.mean(memory_values),
            'peak_cpu_percent': max(cpu_values),
            'avg_cpu_percent': statistics.mean(cpu_values),
            'network_bytes_sent': self.metrics_history[-1].get('network_bytes_sent', 0),
            'network_bytes_recv': self.metrics_history[-1].get('network_bytes_recv', 0),
            'samples_collected': len(self.metrics_history)
        }


class EventGenerator:
    """Generates test events for load testing"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.event_templates = self._create_event_templates()
        
        # Priority distribution (default: 70% Normal, 20% High, 10% Critical)
        self.priority_dist = config.priority_distribution or {
            'NORMAL': 0.7,
            'HIGH': 0.2,
            'CRITICAL': 0.1
        }
    
    def _create_event_templates(self) -> Dict[str, Dict[str, Any]]:
        """Create event templates for different event types"""
        base_payload = 'x' * max(1, self.config.event_payload_size - 200)  # Reserve space for metadata
        
        templates = {
            'market_data.price_update': {
                'symbol': 'TEST_SYMBOL',
                'price': 100.50,
                'volume': 1000,
                'indicators': {'rsi': 65.5, 'macd': 1.2},
                'payload': base_payload
            },
            'order.created': {
                'order_id': 'TEST_ORDER_123',
                'symbol': 'TEST_SYMBOL',
                'quantity': 100,
                'price': 100.00,
                'status': 'pending',
                'payload': base_payload
            },
            'intelligence.recommendation': {
                'symbol': 'TEST_SYMBOL',
                'recommendation': 'BUY',
                'confidence': 0.85,
                'reasoning': ['Technical analysis positive', 'Market sentiment bullish'],
                'payload': base_payload
            },
            'analysis.complete': {
                'symbol': 'TEST_SYMBOL',
                'analysis_type': 'technical',
                'results': {'score': 8.5, 'trend': 'bullish'},
                'payload': base_payload
            }
        }
        
        return templates
    
    def generate_event(self, event_type: str = None, event_id: str = None) -> Event:
        """Generate a test event"""
        import random
        
        # Select event type
        if not event_type:
            event_types = self.config.event_types or list(self.event_templates.keys())
            event_type = random.choice(event_types)
        
        # Get template data
        event_data = self.event_templates.get(event_type, {}).copy()
        event_data['test_timestamp'] = datetime.now().isoformat()
        event_data['test_id'] = event_id or f"test_{int(time.time() * 1000000)}"
        
        # Select priority based on distribution
        priority_choice = random.random()
        cumulative = 0
        priority = EventPriority.NORMAL
        
        for prio_name, prob in self.priority_dist.items():
            cumulative += prob
            if priority_choice <= cumulative:
                priority = getattr(EventPriority, prio_name)
                break
        
        # Create event metadata
        metadata = EventMetadata(
            event_id=event_data['test_id'],
            timestamp=event_data['test_timestamp'],
            source_service="load_test",
            priority=priority
        )
        
        return Event(
            event_type=event_type,
            data=event_data,
            metadata=metadata
        )


class LoadTestExecutor:
    """Executes different types of load tests"""
    
    def __init__(self):
        self.logger = logger.bind(component="load_test_executor")
        self.performance_monitor = PerformanceMonitor()
        
        # Test state
        self.test_running = False
        self.results_queue = queue.Queue()
        self.latency_measurements: List[float] = []
        
    async def run_load_test(self, config: LoadTestConfig) -> PerformanceResult:
        """Run a load test with the given configuration"""
        self.logger.info("Starting load test", test_name=config.test_name, test_type=config.test_type.value)
        
        start_time = datetime.now()
        self.test_running = True
        self.results_queue = queue.Queue()
        self.latency_measurements.clear()
        
        # Start performance monitoring
        await self.performance_monitor.start_monitoring()
        
        try:
            # Execute test based on type
            if config.test_type == LoadTestType.PUBLISHER_ONLY:
                results = await self._run_publisher_test(config)
            elif config.test_type == LoadTestType.SUBSCRIBER_ONLY:
                results = await self._run_subscriber_test(config)
            elif config.test_type == LoadTestType.FULL_ROUNDTRIP:
                results = await self._run_roundtrip_test(config)
            elif config.test_type == LoadTestType.BURST_LOAD:
                results = await self._run_burst_test(config)
            elif config.test_type == LoadTestType.SUSTAINED_LOAD:
                results = await self._run_sustained_test(config)
            elif config.test_type == LoadTestType.STRESS_TEST:
                results = await self._run_stress_test(config)
            else:
                raise ValueError(f"Unknown test type: {config.test_type}")
            
        except Exception as e:
            self.logger.error("Load test failed", error=str(e))
            raise
        finally:
            self.test_running = False
            
        # Stop monitoring and get system metrics
        system_metrics = await self.performance_monitor.stop_monitoring()
        
        # Build final result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        performance_result = self._build_performance_result(
            config, start_time, end_time, duration, results, system_metrics
        )
        
        self.logger.info("Load test completed", 
                       test_name=config.test_name,
                       duration=duration,
                       events_sent=performance_result.events_sent,
                       throughput=performance_result.throughput_events_per_second,
                       targets_met=performance_result.targets_met)
        
        return performance_result
    
    async def _run_publisher_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Run publisher-only load test"""
        event_generator = EventGenerator(config)
        event_bus = await get_event_bus("load_test_publisher")
        
        events_sent = 0
        events_failed = 0
        
        # Calculate timing
        events_per_interval = max(1, config.event_rate_per_second // 10)  # 100ms intervals
        interval_delay = 0.1
        
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        while time.time() < end_time and self.test_running:
            interval_start = time.time()
            
            # Send batch of events
            for _ in range(events_per_interval):
                try:
                    event = event_generator.generate_event()
                    publish_start = time.time()
                    
                    success = await event_bus.publish(event)
                    
                    publish_end = time.time()
                    latency_ms = (publish_end - publish_start) * 1000
                    self.latency_measurements.append(latency_ms)
                    
                    if success:
                        events_sent += 1
                    else:
                        events_failed += 1
                        
                except Exception as e:
                    events_failed += 1
                    self.logger.debug("Event publish failed", error=str(e))
            
            # Wait for next interval
            interval_duration = time.time() - interval_start
            if interval_duration < interval_delay:
                await asyncio.sleep(interval_delay - interval_duration)
        
        return {
            'events_sent': events_sent,
            'events_received': events_sent,  # Same for publisher test
            'events_failed': events_failed
        }
    
    async def _run_subscriber_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Run subscriber-only load test"""
        # This would test subscription performance with pre-existing events
        # For now, simulate subscriber processing
        events_processed = 0
        events_failed = 0
        
        processing_time_per_event = 1.0 / config.event_rate_per_second
        
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        while time.time() < end_time and self.test_running:
            try:
                # Simulate event processing
                process_start = time.time()
                await asyncio.sleep(processing_time_per_event)
                process_end = time.time()
                
                latency_ms = (process_end - process_start) * 1000
                self.latency_measurements.append(latency_ms)
                
                events_processed += 1
                
            except Exception as e:
                events_failed += 1
                self.logger.debug("Event processing failed", error=str(e))
        
        return {
            'events_sent': events_processed,
            'events_received': events_processed,
            'events_failed': events_failed
        }
    
    async def _run_roundtrip_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Run full roundtrip test (publish -> subscribe -> process)"""
        event_generator = EventGenerator(config)
        publisher_bus = await get_event_bus("load_test_publisher")
        subscriber_bus = await get_event_bus("load_test_subscriber")
        
        events_sent = 0
        events_received = 0
        events_failed = 0
        
        received_events = {}
        
        async def event_handler(event_data: Dict[str, Any]):
            nonlocal events_received
            event_id = event_data.get('test_id')
            if event_id and event_id in received_events:
                receive_time = time.time()
                send_time = received_events[event_id]
                latency_ms = (receive_time - send_time) * 1000
                self.latency_measurements.append(latency_ms)
                events_received += 1
        
        # Subscribe to test events
        for event_type in config.event_types or ['market_data.price_update']:
            await subscriber_bus.subscribe(event_type, event_handler)
        
        # Send events
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        events_per_interval = max(1, config.event_rate_per_second // 10)
        interval_delay = 0.1
        
        while time.time() < end_time and self.test_running:
            interval_start = time.time()
            
            for _ in range(events_per_interval):
                try:
                    event = event_generator.generate_event()
                    event_id = event.data.get('test_id')
                    
                    send_time = time.time()
                    received_events[event_id] = send_time
                    
                    success = await publisher_bus.publish(event)
                    if success:
                        events_sent += 1
                    else:
                        events_failed += 1
                        
                except Exception as e:
                    events_failed += 1
                    self.logger.debug("Roundtrip event failed", error=str(e))
            
            # Wait for next interval
            interval_duration = time.time() - interval_start
            if interval_duration < interval_delay:
                await asyncio.sleep(interval_delay - interval_duration)
        
        # Wait a bit for remaining events to be processed
        await asyncio.sleep(2.0)
        
        return {
            'events_sent': events_sent,
            'events_received': events_received,
            'events_failed': events_failed
        }
    
    async def _run_burst_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Run burst load test"""
        event_generator = EventGenerator(config)
        event_bus = await get_event_bus("load_test_burst")
        
        events_sent = 0
        events_failed = 0
        
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        while time.time() < end_time and self.test_running:
            # Send burst of events
            burst_start = time.time()
            
            for _ in range(config.burst_size):
                try:
                    event = event_generator.generate_event()
                    publish_start = time.time()
                    
                    success = await event_bus.publish(event)
                    
                    publish_end = time.time()
                    latency_ms = (publish_end - publish_start) * 1000
                    self.latency_measurements.append(latency_ms)
                    
                    if success:
                        events_sent += 1
                    else:
                        events_failed += 1
                        
                except Exception as e:
                    events_failed += 1
            
            burst_duration = time.time() - burst_start
            self.logger.debug("Burst completed", 
                           burst_size=config.burst_size,
                           duration_ms=burst_duration * 1000)
            
            # Wait until next burst
            if time.time() + config.burst_interval < end_time:
                await asyncio.sleep(config.burst_interval)
        
        return {
            'events_sent': events_sent,
            'events_received': events_sent,
            'events_failed': events_failed
        }
    
    async def _run_sustained_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Run sustained load test with consistent rate"""
        return await self._run_publisher_test(config)  # Same as publisher test
    
    async def _run_stress_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Run stress test with increasing load"""
        event_generator = EventGenerator(config)
        event_bus = await get_event_bus("load_test_stress")
        
        events_sent = 0
        events_failed = 0
        
        start_time = time.time()
        duration_per_phase = config.duration_seconds // 5  # 5 phases
        
        for phase in range(5):
            phase_rate = config.event_rate_per_second * (phase + 1)  # Increasing load
            phase_start = time.time()
            phase_end = phase_start + duration_per_phase
            
            self.logger.info(f"Stress test phase {phase + 1}", target_rate=phase_rate)
            
            events_per_interval = max(1, phase_rate // 10)
            interval_delay = 0.1
            
            while time.time() < phase_end and self.test_running:
                interval_start = time.time()
                
                for _ in range(events_per_interval):
                    try:
                        event = event_generator.generate_event()
                        publish_start = time.time()
                        
                        success = await event_bus.publish(event)
                        
                        publish_end = time.time()
                        latency_ms = (publish_end - publish_start) * 1000
                        self.latency_measurements.append(latency_ms)
                        
                        if success:
                            events_sent += 1
                        else:
                            events_failed += 1
                            
                    except Exception as e:
                        events_failed += 1
                
                # Wait for next interval
                interval_duration = time.time() - interval_start
                if interval_duration < interval_delay:
                    await asyncio.sleep(interval_delay - interval_duration)
        
        return {
            'events_sent': events_sent,
            'events_received': events_sent,
            'events_failed': events_failed
        }
    
    def _build_performance_result(self, config: LoadTestConfig, 
                                start_time: datetime, end_time: datetime,
                                duration: float, test_results: Dict[str, Any],
                                system_metrics: Dict[str, Any]) -> PerformanceResult:
        """Build comprehensive performance result"""
        
        # Calculate latency statistics
        latencies = self.latency_measurements
        if latencies:
            latency_min = min(latencies)
            latency_max = max(latencies)
            latency_mean = statistics.mean(latencies)
            latency_p50 = statistics.median(latencies)
            latency_p95 = self._percentile(latencies, 0.95)
            latency_p99 = self._percentile(latencies, 0.99)
        else:
            latency_min = latency_max = latency_mean = latency_p50 = latency_p95 = latency_p99 = 0.0
        
        # Calculate throughput
        events_sent = test_results.get('events_sent', 0)
        throughput = events_sent / duration if duration > 0 else 0
        
        # Calculate error rate
        events_failed = test_results.get('events_failed', 0)
        total_events = events_sent + events_failed
        error_rate = events_failed / total_events if total_events > 0 else 0
        
        # Check performance targets
        targets_met = True
        violations = []
        
        if latency_p99 > config.target_latency_p99:
            targets_met = False
            violations.append(f"P99 latency {latency_p99:.2f}ms exceeds target {config.target_latency_p99}ms")
        
        if throughput < config.target_throughput:
            targets_met = False
            violations.append(f"Throughput {throughput:.1f} eps below target {config.target_throughput} eps")
        
        if error_rate > config.max_error_rate:
            targets_met = False
            violations.append(f"Error rate {error_rate:.3f} exceeds target {config.max_error_rate}")
        
        peak_memory = system_metrics.get('peak_memory_mb', 0)
        if peak_memory > config.max_memory_mb:
            targets_met = False
            violations.append(f"Peak memory {peak_memory:.1f}MB exceeds target {config.max_memory_mb}MB")
        
        return PerformanceResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            
            events_sent=events_sent,
            events_received=test_results.get('events_received', events_sent),
            events_failed=events_failed,
            
            latency_min=latency_min,
            latency_max=latency_max,
            latency_mean=latency_mean,
            latency_p50=latency_p50,
            latency_p95=latency_p95,
            latency_p99=latency_p99,
            
            throughput_events_per_second=throughput,
            peak_throughput=throughput,  # Could be enhanced with sliding window
            
            error_rate=error_rate,
            error_types={'general_error': events_failed},
            
            peak_memory_mb=peak_memory,
            peak_cpu_percent=system_metrics.get('peak_cpu_percent', 0),
            network_bytes_sent=system_metrics.get('network_bytes_sent', 0),
            network_bytes_received=system_metrics.get('network_bytes_recv', 0),
            
            targets_met=targets_met,
            target_violations=violations
        )
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]


class PerformanceOptimizer:
    """Provides performance optimization recommendations"""
    
    def __init__(self):
        self.logger = logger.bind(component="performance_optimizer")
    
    def analyze_results(self, results: List[PerformanceResult]) -> Dict[str, Any]:
        """Analyze performance results and provide recommendations"""
        if not results:
            return {'error': 'No results to analyze'}
        
        analysis = {
            'summary': self._create_summary(results),
            'bottlenecks': self._identify_bottlenecks(results),
            'recommendations': self._generate_recommendations(results),
            'trends': self._analyze_trends(results)
        }
        
        return analysis
    
    def _create_summary(self, results: List[PerformanceResult]) -> Dict[str, Any]:
        """Create summary of all test results"""
        total_events = sum(r.events_sent for r in results)
        avg_throughput = statistics.mean([r.throughput_events_per_second for r in results])
        avg_latency_p99 = statistics.mean([r.latency_p99 for r in results])
        avg_error_rate = statistics.mean([r.error_rate for r in results])
        
        targets_met_count = sum(1 for r in results if r.targets_met)
        
        return {
            'total_tests': len(results),
            'total_events_processed': total_events,
            'average_throughput_eps': avg_throughput,
            'average_latency_p99_ms': avg_latency_p99,
            'average_error_rate': avg_error_rate,
            'tests_meeting_targets': targets_met_count,
            'success_rate': targets_met_count / len(results)
        }
    
    def _identify_bottlenecks(self, results: List[PerformanceResult]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # High latency bottleneck
        high_latency_results = [r for r in results if r.latency_p99 > 100]
        if high_latency_results:
            avg_high_latency = statistics.mean([r.latency_p99 for r in high_latency_results])
            bottlenecks.append({
                'type': 'high_latency',
                'severity': 'high' if avg_high_latency > 500 else 'medium',
                'description': f'High P99 latency detected: avg {avg_high_latency:.2f}ms',
                'affected_tests': len(high_latency_results)
            })
        
        # Memory bottleneck
        high_memory_results = [r for r in results if r.peak_memory_mb > 256]
        if high_memory_results:
            avg_memory = statistics.mean([r.peak_memory_mb for r in high_memory_results])
            bottlenecks.append({
                'type': 'high_memory',
                'severity': 'high' if avg_memory > 512 else 'medium',
                'description': f'High memory usage detected: avg {avg_memory:.1f}MB',
                'affected_tests': len(high_memory_results)
            })
        
        # Error rate bottleneck
        high_error_results = [r for r in results if r.error_rate > 0.05]
        if high_error_results:
            avg_error_rate = statistics.mean([r.error_rate for r in high_error_results])
            bottlenecks.append({
                'type': 'high_error_rate',
                'severity': 'critical',
                'description': f'High error rate detected: avg {avg_error_rate:.3f}',
                'affected_tests': len(high_error_results)
            })
        
        return bottlenecks
    
    def _generate_recommendations(self, results: List[PerformanceResult]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Analyze patterns
        avg_throughput = statistics.mean([r.throughput_events_per_second for r in results])
        avg_latency = statistics.mean([r.latency_p99 for r in results])
        avg_memory = statistics.mean([r.peak_memory_mb for r in results])
        
        # Throughput recommendations
        if avg_throughput < 500:
            recommendations.append({
                'category': 'throughput',
                'priority': 'high',
                'title': 'Increase Redis Connection Pool Size',
                'description': 'Current throughput is low. Consider increasing Redis connection pool size.',
                'config_change': 'REDIS_POOL_SIZE=20, REDIS_POOL_MAX=50'
            })
        
        # Latency recommendations
        if avg_latency > 50:
            recommendations.append({
                'category': 'latency',
                'priority': 'medium',
                'title': 'Enable Event Compression',
                'description': 'High latency detected. Enable compression for large events.',
                'config_change': 'EVENT_ENABLE_COMPRESSION=true, EVENT_COMPRESSION_THRESHOLD=512'
            })
        
        # Memory recommendations
        if avg_memory > 256:
            recommendations.append({
                'category': 'memory',
                'priority': 'medium',
                'title': 'Optimize Event TTL',
                'description': 'High memory usage. Reduce event persistence TTL.',
                'config_change': 'EVENT_PERSISTENCE_TTL=3600, EVENT_DEAD_LETTER_TTL=7200'
            })
        
        # Performance tuning recommendations
        recommendations.append({
            'category': 'general',
            'priority': 'low',
            'title': 'Batch Processing Optimization',
            'description': 'Enable batch processing for high-volume event types.',
            'config_change': 'EVENT_BATCH_SIZE=250, SUBSCRIBER_BUFFER_SIZE=2000'
        })
        
        return recommendations
    
    def _analyze_trends(self, results: List[PerformanceResult]) -> Dict[str, Any]:
        """Analyze performance trends across tests"""
        if len(results) < 2:
            return {'message': 'Need at least 2 test results for trend analysis'}
        
        # Sort by start time
        sorted_results = sorted(results, key=lambda r: r.start_time)
        
        # Calculate trends
        throughputs = [r.throughput_events_per_second for r in sorted_results]
        latencies = [r.latency_p99 for r in sorted_results]
        memories = [r.peak_memory_mb for r in sorted_results]
        
        return {
            'throughput_trend': self._calculate_trend(throughputs),
            'latency_trend': self._calculate_trend(latencies),
            'memory_trend': self._calculate_trend(memories),
            'overall_performance_trend': 'improving' if self._calculate_trend(throughputs) > 0 and self._calculate_trend(latencies) < 0 else 'degrading'
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        return max(-1.0, min(1.0, slope / max(abs(v) for v in values) if max(abs(v) for v in values) > 0 else 0))


# Performance test suite
class PerformanceTestSuite:
    """Comprehensive performance test suite"""
    
    def __init__(self):
        self.executor = LoadTestExecutor()
        self.optimizer = PerformanceOptimizer()
        self.logger = logger.bind(component="performance_test_suite")
        
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite"""
        self.logger.info("Starting comprehensive performance test suite")
        
        test_configs = [
            # Basic throughput test
            LoadTestConfig(
                test_type=LoadTestType.PUBLISHER_ONLY,
                test_name="Basic Throughput Test",
                duration_seconds=30,
                event_rate_per_second=100,
                event_types=['market_data.price_update']
            ),
            
            # High throughput test
            LoadTestConfig(
                test_type=LoadTestType.PUBLISHER_ONLY,
                test_name="High Throughput Test",
                duration_seconds=30,
                event_rate_per_second=500,
                target_throughput=400
            ),
            
            # Roundtrip latency test
            LoadTestConfig(
                test_type=LoadTestType.FULL_ROUNDTRIP,
                test_name="Roundtrip Latency Test",
                duration_seconds=30,
                event_rate_per_second=50,
                target_latency_p99=50.0
            ),
            
            # Burst load test
            LoadTestConfig(
                test_type=LoadTestType.BURST_LOAD,
                test_name="Burst Load Test",
                duration_seconds=60,
                burst_size=1000,
                burst_interval=15
            ),
            
            # Stress test
            LoadTestConfig(
                test_type=LoadTestType.STRESS_TEST,
                test_name="Stress Test",
                duration_seconds=60,
                event_rate_per_second=100,
                target_throughput=400
            )
        ]
        
        results = []
        for config in test_configs:
            try:
                result = await self.executor.run_load_test(config)
                results.append(result)
                
                # Brief cooldown between tests
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error("Test failed", test_name=config.test_name, error=str(e))
        
        # Analyze results
        analysis = self.optimizer.analyze_results(results)
        
        return {
            'test_results': [asdict(r) for r in results],
            'analysis': analysis,
            'summary': {
                'total_tests': len(results),
                'successful_tests': len(results),
                'overall_success': all(r.targets_met for r in results)
            }
        }


# Global performance test instance
performance_tester = PerformanceTestSuite()

async def run_performance_tests() -> Dict[str, Any]:
    """Run comprehensive performance tests"""
    return await performance_tester.run_comprehensive_test()

async def run_single_load_test(config: LoadTestConfig) -> PerformanceResult:
    """Run single load test"""
    executor = LoadTestExecutor()
    return await executor.run_load_test(config)