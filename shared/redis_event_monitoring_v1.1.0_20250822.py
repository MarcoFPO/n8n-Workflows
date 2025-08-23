"""
Redis Event Bus Monitoring & Reporting System
Real-time monitoring, alerting and reporting for the event bus performance
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import deque, defaultdict

from shared.redis_event_bus import RedisEventBus, Event, EventPriority
from shared.redis_event_bus_factory import RedisEventBusFactory
from shared.redis_event_performance import PerformanceResult, LoadTestConfig

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


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to monitor"""
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    QUEUE_DEPTH = "queue_depth"
    CONNECTION_COUNT = "connection_count"


@dataclass
class MetricThreshold:
    """Threshold configuration for alerts"""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    time_window_minutes: int = 5
    min_samples: int = 3


@dataclass
class Alert:
    """Alert notification"""
    alert_id: str
    level: AlertLevel
    metric_type: MetricType
    service_name: str
    message: str
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    service_name: str
    throughput_eps: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    queue_depth: int
    events_processed_total: int
    events_failed_total: int


class RealTimeMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self, sample_interval: float = 5.0):
        self.sample_interval = sample_interval
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Metrics storage (ring buffers for efficiency)
        self.metrics_buffer_size = 1000  # ~1.4 hours at 5s interval
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.metrics_buffer_size))
        
        # Alert management
        self.alert_thresholds: List[MetricThreshold] = self._get_default_thresholds()
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        
        # Performance tracking
        self.last_sample_time = time.time()
        self.samples_collected = 0
        
        self.logger = logger.bind(component="realtime_monitor")
    
    def _get_default_thresholds(self) -> List[MetricThreshold]:
        """Get default alert thresholds"""
        return [
            MetricThreshold(MetricType.THROUGHPUT, 100, 50, 5, 3),
            MetricThreshold(MetricType.LATENCY, 100, 500, 3, 5),
            MetricThreshold(MetricType.ERROR_RATE, 0.05, 0.1, 2, 3),
            MetricThreshold(MetricType.MEMORY_USAGE, 512, 1024, 5, 3),
            MetricThreshold(MetricType.CPU_USAGE, 70, 90, 3, 5),
            MetricThreshold(MetricType.QUEUE_DEPTH, 1000, 5000, 2, 3)
        ]
    
    async def start_monitoring(self, service_names: List[str]):
        """Start real-time monitoring for specified services"""
        if self.running:
            self.logger.warning("Monitor already running")
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(service_names))
        
        self.logger.info("Real-time monitoring started", 
                       services=service_names,
                       interval=self.sample_interval)
    
    async def stop_monitoring(self):
        """Stop real-time monitoring"""
        if not self.running:
            return
        
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Real-time monitoring stopped", 
                       samples_collected=self.samples_collected)
    
    async def _monitoring_loop(self, service_names: List[str]):
        """Main monitoring loop"""
        try:
            while self.running:
                loop_start = time.time()
                
                # Collect metrics for all services
                for service_name in service_names:
                    try:
                        metrics = await self._collect_service_metrics(service_name)
                        if metrics:
                            self.metrics_history[service_name].append(metrics)
                            await self._check_alerts(metrics)
                    except Exception as e:
                        self.logger.warning("Failed to collect metrics", 
                                         service=service_name, error=str(e))
                
                self.samples_collected += 1
                self.last_sample_time = loop_start
                
                # Sleep until next sample
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.sample_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error("Monitoring loop error", error=str(e))
    
    async def _collect_service_metrics(self, service_name: str) -> Optional[PerformanceMetrics]:
        """Collect metrics for a specific service"""
        try:
            # Get event bus instance
            event_bus = await RedisEventBusFactory.get_event_bus(service_name)
            if not event_bus:
                return None
            
            # Get bus metrics
            bus_metrics = event_bus.get_metrics()
            
            # Calculate derived metrics
            current_time = datetime.now()
            
            # Get recent latency measurements for percentile calculation
            latencies = getattr(event_bus, 'recent_latencies', [])
            latency_p95 = self._percentile(latencies, 0.95) if latencies else 0.0
            latency_p99 = self._percentile(latencies, 0.99) if latencies else 0.0
            
            # Calculate throughput from recent samples
            throughput = self._calculate_throughput(service_name, bus_metrics)
            
            # Calculate error rate
            events_processed = bus_metrics.get('events_processed', 0)
            events_failed = bus_metrics.get('events_failed', 0)
            total_events = events_processed + events_failed
            error_rate = events_failed / total_events if total_events > 0 else 0.0
            
            return PerformanceMetrics(
                timestamp=current_time,
                service_name=service_name,
                throughput_eps=throughput,
                latency_p95_ms=latency_p95,
                latency_p99_ms=latency_p99,
                error_rate=error_rate,
                memory_usage_mb=bus_metrics.get('memory_usage_mb', 0),
                cpu_usage_percent=bus_metrics.get('cpu_usage_percent', 0),
                active_connections=bus_metrics.get('active_connections', 0),
                queue_depth=bus_metrics.get('queue_depth', 0),
                events_processed_total=events_processed,
                events_failed_total=events_failed
            )
            
        except Exception as e:
            self.logger.warning("Metrics collection failed", service=service_name, error=str(e))
            return None
    
    def _calculate_throughput(self, service_name: str, current_metrics: Dict[str, Any]) -> float:
        """Calculate throughput from recent metrics"""
        history = self.metrics_history.get(service_name)
        if not history or len(history) < 2:
            return 0.0
        
        # Get last two samples
        current_events = current_metrics.get('events_processed', 0)
        previous_metrics = history[-1]
        previous_events = previous_metrics.events_processed_total
        
        # Calculate time difference
        time_diff = (datetime.now() - previous_metrics.timestamp).total_seconds()
        if time_diff <= 0:
            return 0.0
        
        # Calculate events per second
        event_diff = current_events - previous_events
        return max(0.0, event_diff / time_diff)
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """Check metrics against thresholds and trigger alerts"""
        for threshold in self.alert_thresholds:
            metric_value = self._get_metric_value(metrics, threshold.metric_type)
            if metric_value is None:
                continue
            
            alert_key = f"{metrics.service_name}_{threshold.metric_type.value}"
            
            # Check critical threshold
            if metric_value >= threshold.critical_threshold:
                await self._trigger_alert(
                    alert_key, AlertLevel.CRITICAL, threshold,
                    metrics.service_name, metric_value
                )
            
            # Check warning threshold
            elif metric_value >= threshold.warning_threshold:
                await self._trigger_alert(
                    alert_key, AlertLevel.WARNING, threshold,
                    metrics.service_name, metric_value
                )
            
            # Resolve alert if value is below warning threshold
            elif alert_key in self.active_alerts:
                await self._resolve_alert(alert_key)
    
    def _get_metric_value(self, metrics: PerformanceMetrics, metric_type: MetricType) -> Optional[float]:
        """Extract specific metric value"""
        if metric_type == MetricType.THROUGHPUT:
            return metrics.throughput_eps
        elif metric_type == MetricType.LATENCY:
            return metrics.latency_p99_ms
        elif metric_type == MetricType.ERROR_RATE:
            return metrics.error_rate
        elif metric_type == MetricType.MEMORY_USAGE:
            return metrics.memory_usage_mb
        elif metric_type == MetricType.CPU_USAGE:
            return metrics.cpu_usage_percent
        elif metric_type == MetricType.QUEUE_DEPTH:
            return metrics.queue_depth
        return None
    
    async def _trigger_alert(self, alert_key: str, level: AlertLevel, 
                           threshold: MetricThreshold, service_name: str, value: float):
        """Trigger a new alert or update existing one"""
        
        # Check if alert already exists
        if alert_key in self.active_alerts:
            existing_alert = self.active_alerts[alert_key]
            if existing_alert.level == level:
                # Update existing alert
                existing_alert.value = value
                existing_alert.timestamp = datetime.now()
                return
        
        # Create new alert
        alert = Alert(
            alert_id=alert_key,
            level=level,
            metric_type=threshold.metric_type,
            service_name=service_name,
            message=f"{threshold.metric_type.value} {level.value}: {value:.2f} exceeds {threshold.critical_threshold if level == AlertLevel.CRITICAL else threshold.warning_threshold}",
            value=value,
            threshold=threshold.critical_threshold if level == AlertLevel.CRITICAL else threshold.warning_threshold,
            timestamp=datetime.now()
        )
        
        self.active_alerts[alert_key] = alert
        
        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error("Alert handler failed", error=str(e))
        
        self.logger.warning("Alert triggered", 
                          alert_id=alert_key,
                          level=level.value,
                          service=service_name,
                          metric=threshold.metric_type.value,
                          value=value)
    
    async def _resolve_alert(self, alert_key: str):
        """Resolve an active alert"""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.timestamp = datetime.now()
            
            # Notify handlers about resolution
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    self.logger.error("Alert resolution handler failed", error=str(e))
            
            del self.active_alerts[alert_key]
            
            self.logger.info("Alert resolved", alert_id=alert_key)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add alert notification handler"""
        self.alert_handlers.append(handler)
    
    def get_current_metrics(self, service_name: str) -> Optional[PerformanceMetrics]:
        """Get latest metrics for service"""
        history = self.metrics_history.get(service_name)
        return history[-1] if history else None
    
    def get_metrics_history(self, service_name: str, 
                          duration_minutes: int = 60) -> List[PerformanceMetrics]:
        """Get metrics history for specified duration"""
        history = self.metrics_history.get(service_name, deque())
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        return [m for m in history if m.timestamp >= cutoff_time]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())


class PerformanceReporter:
    """Generates performance reports and dashboards"""
    
    def __init__(self, monitor: RealTimeMonitor):
        self.monitor = monitor
        self.logger = logger.bind(component="performance_reporter")
    
    def generate_service_report(self, service_name: str, 
                              duration_hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report for a service"""
        duration_minutes = duration_hours * 60
        metrics_history = self.monitor.get_metrics_history(service_name, duration_minutes)
        
        if not metrics_history:
            return {'error': f'No metrics available for service {service_name}'}
        
        # Calculate statistics
        throughput_values = [m.throughput_eps for m in metrics_history]
        latency_values = [m.latency_p99_ms for m in metrics_history]
        error_rate_values = [m.error_rate for m in metrics_history]
        memory_values = [m.memory_usage_mb for m in metrics_history]
        
        report = {
            'service_name': service_name,
            'report_period': {
                'start': metrics_history[0].timestamp.isoformat(),
                'end': metrics_history[-1].timestamp.isoformat(),
                'duration_hours': duration_hours,
                'samples_count': len(metrics_history)
            },
            
            'throughput': {
                'avg_eps': statistics.mean(throughput_values),
                'max_eps': max(throughput_values),
                'min_eps': min(throughput_values),
                'p95_eps': self._percentile(throughput_values, 0.95)
            },
            
            'latency': {
                'avg_p99_ms': statistics.mean(latency_values),
                'max_p99_ms': max(latency_values),
                'min_p99_ms': min(latency_values),
                'p95_p99_ms': self._percentile(latency_values, 0.95)
            },
            
            'reliability': {
                'avg_error_rate': statistics.mean(error_rate_values),
                'max_error_rate': max(error_rate_values),
                'total_events': metrics_history[-1].events_processed_total,
                'total_failures': metrics_history[-1].events_failed_total,
                'uptime_percent': self._calculate_uptime(metrics_history)
            },
            
            'resources': {
                'avg_memory_mb': statistics.mean(memory_values),
                'peak_memory_mb': max(memory_values),
                'memory_trend': self._calculate_trend(memory_values)
            },
            
            'alerts_summary': self._get_alerts_summary(service_name),
            'performance_grade': self._calculate_performance_grade(metrics_history)
        }
        
        return report
    
    def generate_system_overview(self) -> Dict[str, Any]:
        """Generate system-wide performance overview"""
        all_services = list(self.monitor.metrics_history.keys())
        
        system_overview = {
            'timestamp': datetime.now().isoformat(),
            'total_services': len(all_services),
            'services': {},
            'system_health': 'healthy',
            'active_alerts': len(self.monitor.get_active_alerts()),
            'system_metrics': {
                'total_throughput_eps': 0,
                'avg_latency_ms': 0,
                'total_error_rate': 0,
                'total_memory_mb': 0
            }
        }
        
        total_throughput = 0
        latencies = []
        error_rates = []
        memory_usage = []
        
        # Collect current metrics for each service
        for service_name in all_services:
            current_metrics = self.monitor.get_current_metrics(service_name)
            if current_metrics:
                service_summary = {
                    'status': 'healthy',
                    'throughput_eps': current_metrics.throughput_eps,
                    'latency_p99_ms': current_metrics.latency_p99_ms,
                    'error_rate': current_metrics.error_rate,
                    'memory_mb': current_metrics.memory_usage_mb
                }
                
                total_throughput += current_metrics.throughput_eps
                latencies.append(current_metrics.latency_p99_ms)
                error_rates.append(current_metrics.error_rate)
                memory_usage.append(current_metrics.memory_usage_mb)
                
                # Determine service health
                service_alerts = [a for a in self.monitor.get_active_alerts() 
                                if a.service_name == service_name]
                if any(a.level == AlertLevel.CRITICAL for a in service_alerts):
                    service_summary['status'] = 'critical'
                elif any(a.level == AlertLevel.ERROR for a in service_alerts):
                    service_summary['status'] = 'error'
                elif any(a.level == AlertLevel.WARNING for a in service_alerts):
                    service_summary['status'] = 'warning'
                
                system_overview['services'][service_name] = service_summary
        
        # Calculate system-wide metrics
        if latencies:
            system_overview['system_metrics']['total_throughput_eps'] = total_throughput
            system_overview['system_metrics']['avg_latency_ms'] = statistics.mean(latencies)
            system_overview['system_metrics']['total_error_rate'] = statistics.mean(error_rates)
            system_overview['system_metrics']['total_memory_mb'] = sum(memory_usage)
        
        # Determine overall system health
        critical_alerts = [a for a in self.monitor.get_active_alerts() 
                          if a.level == AlertLevel.CRITICAL]
        if critical_alerts:
            system_overview['system_health'] = 'critical'
        elif self.monitor.get_active_alerts():
            system_overview['system_health'] = 'degraded'
        
        return system_overview
    
    def generate_performance_trends(self, duration_hours: int = 24) -> Dict[str, Any]:
        """Generate performance trends analysis"""
        all_services = list(self.monitor.metrics_history.keys())
        trends = {}
        
        for service_name in all_services:
            metrics_history = self.monitor.get_metrics_history(service_name, duration_hours * 60)
            if not metrics_history:
                continue
            
            # Calculate hourly aggregates
            hourly_aggregates = self._aggregate_metrics_hourly(metrics_history)
            
            # Calculate trends
            throughput_trend = self._calculate_trend([h['avg_throughput'] for h in hourly_aggregates])
            latency_trend = self._calculate_trend([h['avg_latency'] for h in hourly_aggregates])
            error_trend = self._calculate_trend([h['avg_error_rate'] for h in hourly_aggregates])
            
            trends[service_name] = {
                'throughput_trend': throughput_trend,
                'latency_trend': latency_trend,
                'error_rate_trend': error_trend,
                'hourly_data': hourly_aggregates,
                'trend_summary': self._summarize_trends(throughput_trend, latency_trend, error_trend)
            }
        
        return trends
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _calculate_uptime(self, metrics_history: List[PerformanceMetrics]) -> float:
        """Calculate uptime percentage"""
        if not metrics_history:
            return 0.0
        
        # Consider service up if it has metrics
        total_samples = len(metrics_history)
        up_samples = len([m for m in metrics_history if m.throughput_eps > 0 or m.events_processed_total > 0])
        
        return (up_samples / total_samples) * 100 if total_samples > 0 else 0.0
    
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
        max_val = max(abs(v) for v in values) if values else 1
        return max(-1.0, min(1.0, slope / max_val if max_val > 0 else 0))
    
    def _calculate_performance_grade(self, metrics_history: List[PerformanceMetrics]) -> str:
        """Calculate overall performance grade"""
        if not metrics_history:
            return 'Unknown'
        
        # Calculate average metrics
        avg_throughput = statistics.mean([m.throughput_eps for m in metrics_history])
        avg_latency = statistics.mean([m.latency_p99_ms for m in metrics_history])
        avg_error_rate = statistics.mean([m.error_rate for m in metrics_history])
        
        # Score based on performance criteria
        score = 0
        
        # Throughput scoring (0-40 points)
        if avg_throughput >= 1000:
            score += 40
        elif avg_throughput >= 500:
            score += 30
        elif avg_throughput >= 100:
            score += 20
        else:
            score += 10
        
        # Latency scoring (0-30 points)
        if avg_latency <= 50:
            score += 30
        elif avg_latency <= 100:
            score += 25
        elif avg_latency <= 200:
            score += 15
        else:
            score += 5
        
        # Error rate scoring (0-30 points)
        if avg_error_rate <= 0.001:
            score += 30
        elif avg_error_rate <= 0.01:
            score += 25
        elif avg_error_rate <= 0.05:
            score += 15
        else:
            score += 5
        
        # Grade assignment
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'
    
    def _get_alerts_summary(self, service_name: str) -> Dict[str, Any]:
        """Get alerts summary for service"""
        service_alerts = [a for a in self.monitor.get_active_alerts() 
                         if a.service_name == service_name]
        
        return {
            'total_active': len(service_alerts),
            'critical': len([a for a in service_alerts if a.level == AlertLevel.CRITICAL]),
            'error': len([a for a in service_alerts if a.level == AlertLevel.ERROR]),
            'warning': len([a for a in service_alerts if a.level == AlertLevel.WARNING]),
            'recent_alerts': [
                {
                    'level': a.level.value,
                    'message': a.message,
                    'timestamp': a.timestamp.isoformat()
                } for a in sorted(service_alerts, key=lambda x: x.timestamp, reverse=True)[:5]
            ]
        }
    
    def _aggregate_metrics_hourly(self, metrics_history: List[PerformanceMetrics]) -> List[Dict[str, Any]]:
        """Aggregate metrics by hour"""
        hourly_data = defaultdict(list)
        
        for metrics in metrics_history:
            hour_key = metrics.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_data[hour_key].append(metrics)
        
        aggregates = []
        for hour, hour_metrics in sorted(hourly_data.items()):
            aggregates.append({
                'hour': hour.isoformat(),
                'avg_throughput': statistics.mean([m.throughput_eps for m in hour_metrics]),
                'avg_latency': statistics.mean([m.latency_p99_ms for m in hour_metrics]),
                'avg_error_rate': statistics.mean([m.error_rate for m in hour_metrics]),
                'max_memory': max([m.memory_usage_mb for m in hour_metrics]),
                'sample_count': len(hour_metrics)
            })
        
        return aggregates
    
    def _summarize_trends(self, throughput_trend: float, 
                         latency_trend: float, error_trend: float) -> str:
        """Summarize trends into readable format"""
        if throughput_trend > 0.1 and latency_trend < -0.1 and error_trend < -0.1:
            return "Improving - throughput up, latency down, errors down"
        elif throughput_trend < -0.1 or latency_trend > 0.1 or error_trend > 0.1:
            return "Degrading - performance declining"
        elif abs(throughput_trend) < 0.1 and abs(latency_trend) < 0.1 and abs(error_trend) < 0.1:
            return "Stable - consistent performance"
        else:
            return "Mixed - some metrics improving, others degrading"


# Global monitoring instances
realtime_monitor = RealTimeMonitor()
performance_reporter = PerformanceReporter(realtime_monitor)

# Convenience functions
async def start_system_monitoring(service_names: List[str] = None):
    """Start monitoring for all or specific services"""
    if not service_names:
        # Get all active services
        instances = RedisEventBusFactory.list_instances()
        service_names = list(instances.keys())
    
    await realtime_monitor.start_monitoring(service_names)

async def stop_system_monitoring():
    """Stop system monitoring"""
    await realtime_monitor.stop_monitoring()

def get_system_overview() -> Dict[str, Any]:
    """Get current system overview"""
    return performance_reporter.generate_system_overview()

def get_service_report(service_name: str, hours: int = 24) -> Dict[str, Any]:
    """Get service performance report"""
    return performance_reporter.generate_service_report(service_name, hours)

def add_alert_handler(handler: Callable[[Alert], None]):
    """Add custom alert handler"""
    realtime_monitor.add_alert_handler(handler)

# Default alert handlers
def console_alert_handler(alert: Alert):
    """Print alert to console"""
    if alert.resolved:
        print(f"✅ RESOLVED: {alert.service_name} - {alert.message}")
    else:
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
        print(f"{emoji.get(alert.level.value, '?')} ALERT: {alert.service_name} - {alert.message}")

# Register default handler
add_alert_handler(console_alert_handler)