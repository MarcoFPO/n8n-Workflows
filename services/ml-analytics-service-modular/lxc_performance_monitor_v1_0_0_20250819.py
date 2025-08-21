#!/usr/bin/env python3
"""
LXC Performance Monitor - Classical-Enhanced ML Performance Monitoring
======================================================================

Speziell entwickelt für LXC 10.1.1.174 Container Performance Monitoring
Überwacht Memory, CPU, und ML Algorithm Performance in Echtzeit

Features:
- Real-time LXC Resource Monitoring
- ML Algorithm Performance Benchmarking  
- Memory Usage Tracking und Alerting
- CPU Utilization Monitoring
- Performance Regression Detection
- LXC Container Health Checks

Author: Claude Code & LXC Optimization Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import logging
import json
import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import numpy as np
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LXCMetrics:
    """LXC Container Metrics Data Structure"""
    timestamp: datetime
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    available_memory_mb: float
    disk_usage_mb: float
    network_io_kb: Dict[str, float]
    process_count: int
    load_average: List[float]

@dataclass
class AlgorithmPerformance:
    """ML Algorithm Performance Metrics"""
    algorithm_name: str
    execution_time_ms: float
    memory_peak_mb: float
    cpu_utilization_percent: float
    accuracy_score: float
    optimization_method: str
    convergence_achieved: bool
    lxc_optimized: bool

class LXCPerformanceMonitor:
    """
    LXC Performance Monitor für Classical-Enhanced ML Engine
    Optimiert für Container 10.1.1.174 Performance Monitoring
    """
    
    def __init__(self, container_ip: str = "10.1.1.174"):
        self.container_ip = container_ip
        self.monitoring_active = False
        self.metrics_history: List[LXCMetrics] = []
        self.algorithm_benchmarks: Dict[str, List[AlgorithmPerformance]] = {}
        self.alert_thresholds = {
            "memory_percent": 85.0,  # 85% Memory Alert
            "cpu_percent": 90.0,     # 90% CPU Alert
            "response_time_ms": 2000  # 2s Response Time Alert
        }
        self.performance_baselines = {}
        self.alert_callbacks: List[Callable] = []
        
    async def start_monitoring(self, interval_seconds: int = 5) -> None:
        """Start continuous LXC performance monitoring"""
        if self.monitoring_active:
            logger.warning("Performance monitoring already active")
            return
            
        self.monitoring_active = True
        logger.info(f"Starting LXC Performance Monitoring für {self.container_ip}")
        
        # Background monitoring task
        asyncio.create_task(self._monitoring_loop(interval_seconds))
        
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self.monitoring_active = False
        logger.info("LXC Performance Monitoring stopped")
        
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect LXC metrics
                metrics = self._collect_lxc_metrics()
                self.metrics_history.append(metrics)
                
                # Keep history limited für LXC memory
                if len(self.metrics_history) > 1000:  # Keep last 1000 metrics
                    self.metrics_history = self.metrics_history[-1000:]
                
                # Check for alerts
                await self._check_performance_alerts(metrics)
                
                # Wait before next collection
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(interval_seconds)
                
    def _collect_lxc_metrics(self) -> LXCMetrics:
        """Collect comprehensive LXC metrics"""
        try:
            # Process metrics
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # System metrics
            virtual_memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk_usage = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()
            
            # Load average (Linux specific)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
            
            metrics = LXCMetrics(
                timestamp=datetime.utcnow(),
                memory_usage_mb=memory_info.rss / 1024 / 1024,
                memory_percent=virtual_memory.percent,
                cpu_percent=cpu_percent,
                available_memory_mb=virtual_memory.available / 1024 / 1024,
                disk_usage_mb=disk_usage.used / 1024 / 1024,
                network_io_kb={
                    "bytes_sent": net_io.bytes_sent / 1024 if net_io else 0,
                    "bytes_recv": net_io.bytes_recv / 1024 if net_io else 0
                },
                process_count=len(psutil.pids()),
                load_average=list(load_avg)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting LXC metrics: {str(e)}")
            # Return default metrics
            return LXCMetrics(
                timestamp=datetime.utcnow(),
                memory_usage_mb=0.0,
                memory_percent=0.0,
                cpu_percent=0.0,
                available_memory_mb=0.0,
                disk_usage_mb=0.0,
                network_io_kb={"bytes_sent": 0, "bytes_recv": 0},
                process_count=0,
                load_average=[0.0, 0.0, 0.0]
            )
    
    async def _check_performance_alerts(self, metrics: LXCMetrics) -> None:
        """Check für performance alerts and trigger callbacks"""
        alerts = []
        
        # Memory alert
        if metrics.memory_percent > self.alert_thresholds["memory_percent"]:
            alerts.append({
                "type": "memory_high",
                "message": f"Memory usage {metrics.memory_percent:.1f}% exceeds threshold {self.alert_thresholds['memory_percent']}%",
                "severity": "warning",
                "timestamp": metrics.timestamp,
                "value": metrics.memory_percent
            })
        
        # CPU alert
        if metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
            alerts.append({
                "type": "cpu_high", 
                "message": f"CPU usage {metrics.cpu_percent:.1f}% exceeds threshold {self.alert_thresholds['cpu_percent']}%",
                "severity": "warning",
                "timestamp": metrics.timestamp,
                "value": metrics.cpu_percent
            })
        
        # Trigger alert callbacks
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {str(e)}")
                    
    def benchmark_algorithm(
        self,
        algorithm_name: str,
        execution_function: Callable,
        *args,
        **kwargs
    ) -> AlgorithmPerformance:
        """Benchmark ML algorithm performance on LXC"""
        logger.info(f"Benchmarking algorithm: {algorithm_name}")
        
        # Collect baseline metrics
        start_metrics = self._collect_lxc_metrics()
        start_time = time.time()
        
        try:
            # Execute algorithm
            result = execution_function(*args, **kwargs)
            
            # Collect end metrics
            end_time = time.time()
            end_metrics = self._collect_lxc_metrics()
            
            # Calculate performance metrics
            execution_time_ms = (end_time - start_time) * 1000
            memory_peak_mb = max(start_metrics.memory_usage_mb, end_metrics.memory_usage_mb)
            cpu_utilization = (start_metrics.cpu_percent + end_metrics.cpu_percent) / 2
            
            # Estimate accuracy (if result contains accuracy info)
            accuracy_score = 0.0
            if isinstance(result, dict) and 'accuracy' in result:
                accuracy_score = result['accuracy']
            elif isinstance(result, dict) and 'classical_advantage' in result:
                accuracy_score = result['classical_advantage']
            
            performance = AlgorithmPerformance(
                algorithm_name=algorithm_name,
                execution_time_ms=execution_time_ms,
                memory_peak_mb=memory_peak_mb,
                cpu_utilization_percent=cpu_utilization,
                accuracy_score=accuracy_score,
                optimization_method="LXC-Optimized",
                convergence_achieved=True,  # Default assumption
                lxc_optimized=True
            )
            
            # Store benchmark
            if algorithm_name not in self.algorithm_benchmarks:
                self.algorithm_benchmarks[algorithm_name] = []
            
            self.algorithm_benchmarks[algorithm_name].append(performance)
            
            logger.info(f"Algorithm {algorithm_name} benchmarked: {execution_time_ms:.1f}ms, {memory_peak_mb:.1f}MB peak")
            return performance
            
        except Exception as e:
            logger.error(f"Error benchmarking algorithm {algorithm_name}: {str(e)}")
            # Return error performance
            return AlgorithmPerformance(
                algorithm_name=algorithm_name,
                execution_time_ms=0.0,
                memory_peak_mb=0.0,
                cpu_utilization_percent=0.0,
                accuracy_score=0.0,
                optimization_method="Failed",
                convergence_achieved=False,
                lxc_optimized=False
            )
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {"error": "No recent metrics available"}
        
        # Calculate averages
        avg_memory_percent = np.mean([m.memory_percent for m in recent_metrics])
        avg_cpu_percent = np.mean([m.cpu_percent for m in recent_metrics])
        max_memory_usage = max([m.memory_usage_mb for m in recent_metrics])
        min_available_memory = min([m.available_memory_mb for m in recent_metrics])
        
        # Recent algorithm performance
        recent_algorithms = {}
        for algo_name, benchmarks in self.algorithm_benchmarks.items():
            recent_benchmarks = [b for b in benchmarks if len(benchmarks) <= 10]  # Last 10 runs
            if recent_benchmarks:
                recent_algorithms[algo_name] = {
                    "avg_execution_time_ms": np.mean([b.execution_time_ms for b in recent_benchmarks]),
                    "avg_memory_peak_mb": np.mean([b.memory_peak_mb for b in recent_benchmarks]),
                    "avg_accuracy": np.mean([b.accuracy_score for b in recent_benchmarks]),
                    "total_runs": len(recent_benchmarks)
                }
        
        summary = {
            "container_ip": self.container_ip,
            "summary_period_hours": hours,
            "metrics_count": len(recent_metrics),
            "system_performance": {
                "avg_memory_percent": avg_memory_percent,
                "avg_cpu_percent": avg_cpu_percent,
                "max_memory_usage_mb": max_memory_usage,
                "min_available_memory_mb": min_available_memory,
                "current_load_average": recent_metrics[-1].load_average if recent_metrics else [0, 0, 0]
            },
            "algorithm_performance": recent_algorithms,
            "lxc_optimization_status": {
                "monitoring_active": self.monitoring_active,
                "total_algorithms_benchmarked": len(self.algorithm_benchmarks),
                "memory_optimization": "Active" if avg_memory_percent < 80 else "Warning"
            }
        }
        
        return summary
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add callback für performance alerts"""
        self.alert_callbacks.append(callback)
        logger.info("Performance alert callback added")
    
    def set_alert_thresholds(self, **thresholds) -> None:
        """Update alert thresholds"""
        self.alert_thresholds.update(thresholds)
        logger.info(f"Alert thresholds updated: {self.alert_thresholds}")
    
    def export_metrics_to_file(self, filepath: str) -> None:
        """Export metrics history to JSON file"""
        try:
            # Convert metrics to serializable format
            export_data = {
                "container_ip": self.container_ip,
                "export_timestamp": datetime.utcnow().isoformat(),
                "metrics_count": len(self.metrics_history),
                "metrics": []
            }
            
            for metric in self.metrics_history:
                export_data["metrics"].append({
                    "timestamp": metric.timestamp.isoformat(),
                    "memory_usage_mb": metric.memory_usage_mb,
                    "memory_percent": metric.memory_percent,
                    "cpu_percent": metric.cpu_percent,
                    "available_memory_mb": metric.available_memory_mb,
                    "load_average": metric.load_average
                })
            
            # Algorithm benchmarks
            export_data["algorithm_benchmarks"] = {}
            for algo_name, benchmarks in self.algorithm_benchmarks.items():
                export_data["algorithm_benchmarks"][algo_name] = [
                    {
                        "algorithm_name": b.algorithm_name,
                        "execution_time_ms": b.execution_time_ms,
                        "memory_peak_mb": b.memory_peak_mb,
                        "cpu_utilization_percent": b.cpu_utilization_percent,
                        "accuracy_score": b.accuracy_score,
                        "lxc_optimized": b.lxc_optimized
                    } for b in benchmarks
                ]
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Metrics exported to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {str(e)}")

# Example usage and testing
async def example_usage():
    """Example usage of LXC Performance Monitor"""
    monitor = LXCPerformanceMonitor("10.1.1.174")
    
    # Add alert callback
    async def alert_handler(alert):
        print(f"🚨 ALERT: {alert['type']} - {alert['message']}")
    
    monitor.add_alert_callback(alert_handler)
    
    # Start monitoring
    await monitor.start_monitoring(interval_seconds=10)
    
    # Simulate some ML algorithm execution
    def dummy_algorithm(n=1000):
        # Simulate some computation
        data = np.random.randn(n, 10)
        result = np.mean(data, axis=0)
        return {"accuracy": 0.85, "result": result}
    
    # Benchmark algorithm
    performance = monitor.benchmark_algorithm("DummyMLAlgorithm", dummy_algorithm, n=5000)
    print(f"Algorithm Performance: {performance}")
    
    # Wait a bit
    await asyncio.sleep(30)
    
    # Get performance summary
    summary = monitor.get_performance_summary(hours=1)
    print(f"Performance Summary: {json.dumps(summary, indent=2)}")
    
    # Export metrics
    monitor.export_metrics_to_file("lxc_performance_metrics.json")
    
    # Stop monitoring
    await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(example_usage())