#!/usr/bin/env python3
"""
Production Service Health Check Script
Testet alle Services auf 10.1.1.174 und generiert einen umfassenden Bericht
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import argparse
import sys

@dataclass
class ServiceHealthResult:
    """Gesundheitsstatus eines einzelnen Service"""
    name: str
    url: str
    status: str  # healthy, unhealthy, unreachable
    response_time_ms: int
    version: Optional[str] = None
    architecture: Optional[str] = None
    features: Optional[List[str]] = None
    error_message: Optional[str] = None
    additional_info: Optional[Dict] = None

class ProductionHealthChecker:
    """Health Check für alle Production Services"""
    
    # Service-Definition: Name -> (Host, Port, Endpoint)
    SERVICES = {
        "frontend": ("10.1.1.174", 8080, "/health"),
        "data-processing": ("10.1.1.174", 8017, "/health"),
        "prediction-tracking": ("10.1.1.174", 8018, "/health"),
        "event-bus": ("10.1.1.174", 8014, "/health"),
        "ml-analytics": ("10.1.1.174", 8021, "/health"),
        "broker-gateway": ("10.1.1.174", 8012, "/health"),
        "intelligent-core": ("10.1.1.174", 8001, "/health"),
        "monitoring": ("10.1.1.174", 8015, "/health"),
        "diagnostic": ("10.1.1.174", 8013, "/health"),
        "marketcap": ("10.1.1.174", 8011, "/health"),
    }
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.results: List[ServiceHealthResult] = []
    
    async def check_service(self, name: str, host: str, port: int, endpoint: str) -> ServiceHealthResult:
        """Testet einen einzelnen Service"""
        url = f"http://{host}:{port}{endpoint}"
        start_time = datetime.now()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    end_time = datetime.now()
                    response_time = int((end_time - start_time).total_seconds() * 1000)
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return ServiceHealthResult(
                                name=name,
                                url=url,
                                status="healthy",
                                response_time_ms=response_time,
                                version=data.get("version"),
                                architecture=data.get("architecture"),
                                features=data.get("features"),
                                additional_info={k: v for k, v in data.items() if k not in ["version", "architecture", "features"]}
                            )
                        except json.JSONDecodeError:
                            # Service antwortet, aber nicht mit JSON
                            return ServiceHealthResult(
                                name=name,
                                url=url,
                                status="unhealthy",
                                response_time_ms=response_time,
                                error_message="Invalid JSON response"
                            )
                    else:
                        return ServiceHealthResult(
                            name=name,
                            url=url,
                            status="unhealthy", 
                            response_time_ms=response_time,
                            error_message=f"HTTP {response.status}"
                        )
                        
        except asyncio.TimeoutError:
            return ServiceHealthResult(
                name=name,
                url=url,
                status="unreachable",
                response_time_ms=self.timeout * 1000,
                error_message="Timeout"
            )
        except Exception as e:
            return ServiceHealthResult(
                name=name,
                url=url,
                status="unreachable",
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def check_all_services(self) -> List[ServiceHealthResult]:
        """Testet alle Services parallel"""
        tasks = []
        for name, (host, port, endpoint) in self.SERVICES.items():
            task = self.check_service(name, host, port, endpoint)
            tasks.append(task)
        
        self.results = await asyncio.gather(*tasks)
        return self.results
    
    def generate_report(self) -> Dict:
        """Generiert einen detaillierten Bericht"""
        if not self.results:
            return {"error": "No health checks performed"}
        
        healthy_count = sum(1 for r in self.results if r.status == "healthy")
        unhealthy_count = sum(1 for r in self.results if r.status == "unhealthy")
        unreachable_count = sum(1 for r in self.results if r.status == "unreachable")
        
        # Performance-Statistiken (nur für erreichbare Services)
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Service-Details
        services_by_status = {
            "healthy": [r for r in self.results if r.status == "healthy"],
            "unhealthy": [r for r in self.results if r.status == "unhealthy"],
            "unreachable": [r for r in self.results if r.status == "unreachable"]
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_services": len(self.results),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "unreachable": unreachable_count,
            "health_percentage": round((healthy_count / len(self.results)) * 100, 1),
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 1),
                "max_response_time_ms": max_response_time,
                "timeout_threshold_ms": self.timeout * 1000
            },
            "services_by_status": {
                status: [asdict(service) for service in services]
                for status, services in services_by_status.items()
            }
        }
    
    def print_summary(self, report: Dict):
        """Druckt eine übersichtliche Zusammenfassung"""
        print("=" * 80)
        print("PRODUCTION SERVICE HEALTH CHECK REPORT")
        print("=" * 80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Server: 10.1.1.174 (LXC Container)")
        print()
        
        # Status-Übersicht
        print("SERVICE STATUS OVERVIEW")
        print("-" * 40)
        print(f"✅ Healthy:     {report['healthy']:2d}/{report['total_services']} services")
        print(f"⚠️  Unhealthy:   {report['unhealthy']:2d}/{report['total_services']} services")
        print(f"❌ Unreachable: {report['unreachable']:2d}/{report['total_services']} services")
        print(f"🎯 Health Rate: {report['health_percentage']}%")
        print()
        
        # Performance
        perf = report['performance']
        print("PERFORMANCE METRICS")
        print("-" * 40)
        print(f"Average Response Time: {perf['avg_response_time_ms']:.1f}ms")
        print(f"Slowest Response:     {perf['max_response_time_ms']}ms")
        print(f"Timeout Threshold:    {perf['timeout_threshold_ms']}ms")
        print()
        
        # Service-Details
        for status in ["healthy", "unhealthy", "unreachable"]:
            services = report['services_by_status'][status]
            if services:
                status_icons = {"healthy": "✅", "unhealthy": "⚠️", "unreachable": "❌"}
                print(f"{status_icons[status]} {status.upper()} SERVICES")
                print("-" * 40)
                
                for service in services:
                    name = service['name'].ljust(18)
                    response_time = f"{service['response_time_ms']}ms".rjust(6)
                    version = service.get('version', 'N/A')
                    
                    if service['error_message']:
                        print(f"{name} | {response_time} | {version} | ❌ {service['error_message']}")
                    else:
                        features = service.get('features', [])
                        feature_str = f"({len(features)} features)" if features else ""
                        print(f"{name} | {response_time} | {version} | ✅ {feature_str}")
                
                print()


async def main():
    parser = argparse.ArgumentParser(description='Production service health check')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--continuous', type=int, help='Run continuously every N seconds')
    
    args = parser.parse_args()
    
    checker = ProductionHealthChecker(timeout=args.timeout)
    
    if args.continuous:
        print(f"Running continuous health check every {args.continuous} seconds...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                await checker.check_all_services()
                report = checker.generate_report()
                
                if args.json:
                    print(json.dumps(report, indent=2))
                else:
                    checker.print_summary(report)
                
                await asyncio.sleep(args.continuous)
        except KeyboardInterrupt:
            print("\nHealth check stopped by user")
    else:
        await checker.check_all_services()
        report = checker.generate_report()
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            checker.print_summary(report)
        
        # Exit code basierend auf Gesundheitsstatus
        if report['health_percentage'] < 80:
            sys.exit(1)  # Unhealthy system
        elif report['health_percentage'] < 100:
            sys.exit(2)  # Partially healthy


if __name__ == "__main__":
    asyncio.run(main())