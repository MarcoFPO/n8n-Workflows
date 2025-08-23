#!/usr/bin/env python3
"""
Redis Event-Bus CLI Test Tool für aktienanalyse-ökosystem
Benutzerfreundliches CLI für Performance Tests, Monitoring und System Validation
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
import argparse
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from shared.redis_event_test_runner import run_comprehensive_tests, run_basic_performance_check
from shared.redis_event_monitoring import (
    start_system_monitoring, stop_system_monitoring, get_system_overview,
    get_service_report, realtime_monitor
)
from shared.redis_event_system_integration import (
    initialize_aktienanalyse_event_system, shutdown_aktienanalyse_event_system,
    get_current_system_status, run_performance_validation
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


class EventBusCLI:
    """Command-line interface for Event-Bus testing and monitoring"""
    
    def __init__(self):
        self.logger = logger.bind(component="event_bus_cli")
        self.reports_dir = Path("/home/mdoehler/aktienanalyse-ökosystem/reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Service configuration for aktienanalyse-ökosystem
        self.ecosystem_services = [
            'account-service',
            'order-service', 
            'data-analysis-service',
            'intelligent-core-service',
            'market-data-service',
            'frontend-service'
        ]
    
    async def initialize_system(self) -> bool:
        """Initialize the Event-Bus system"""
        print("🚀 Initialisiere Redis Event-Bus System...")
        
        try:
            success = await initialize_aktienanalyse_event_system()
            if success:
                print("✅ Event-Bus System erfolgreich initialisiert")
                return True
            else:
                print("❌ Event-Bus System Initialisierung fehlgeschlagen")
                return False
        except Exception as e:
            print(f"❌ Initialisierung fehlgeschlagen: {str(e)}")
            return False
    
    async def shutdown_system(self):
        """Shutdown the Event-Bus system"""
        print("🛑 Event-Bus System herunterfahren...")
        try:
            await shutdown_aktienanalyse_event_system()
            print("✅ System erfolgreich heruntergefahren")
        except Exception as e:
            print(f"⚠️ Shutdown-Warnung: {str(e)}")
    
    async def run_quick_health_check(self) -> Dict[str, Any]:
        """Run quick system health check"""
        print("🏥 Führe schnellen System Health Check durch...")
        
        try:
            result = await run_performance_validation()
            
            if result.get('success', False):
                print("✅ System Health Check: ERFOLGREICH")
                print(f"   Durchsatz: {result.get('throughput_eps', 0):.1f} events/sec")
                print(f"   Latenz P99: {result.get('latency_p99_ms', 0):.1f}ms")
                print(f"   Fehlerrate: {result.get('error_rate', 0):.3f}")
            else:
                print("❌ System Health Check: FEHLGESCHLAGEN")
                if 'error' in result:
                    print(f"   Fehler: {result['error']}")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Health Check Fehler: {str(e)}")
            return error_result
    
    async def run_performance_tests(self, test_type: str = 'basic') -> Dict[str, Any]:
        """Run performance tests"""
        if test_type == 'comprehensive':
            print("🚀 Starte umfassende Performance Tests...")
            print("⏱️ Dies kann mehrere Minuten dauern...")
            result = await run_comprehensive_tests()
        else:
            print("⚡ Starte Basic Performance Test...")
            result = await run_basic_performance_check()
        
        # Display results
        self._display_test_results(result, test_type)
        return result
    
    async def start_live_monitoring(self, duration_minutes: int = 60):
        """Start live monitoring for specified duration"""
        print(f"📊 Starte Live-Monitoring für {duration_minutes} Minuten...")
        print("📈 Drücke Ctrl+C zum Stoppen")
        
        # Start monitoring
        await start_system_monitoring(self.ecosystem_services)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        try:
            while time.time() < end_time:
                # Show current status every 30 seconds
                await asyncio.sleep(30)
                overview = get_system_overview()
                self._display_monitoring_update(overview)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring durch Benutzer gestoppt")
        finally:
            await stop_system_monitoring()
            print("✅ Monitoring beendet")
    
    async def generate_system_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive system report"""
        print(f"📋 Generiere System Report für die letzten {hours} Stunden...")
        
        # Get system overview
        overview = get_system_overview()
        
        # Get individual service reports
        service_reports = {}
        for service_name in self.ecosystem_services:
            try:
                report = get_service_report(service_name, hours)
                if 'error' not in report:
                    service_reports[service_name] = report
            except Exception as e:
                self.logger.warning(f"Could not generate report for {service_name}", error=str(e))
        
        # Compile comprehensive report
        comprehensive_report = {
            'report_timestamp': datetime.now().isoformat(),
            'report_period_hours': hours,
            'system_overview': overview,
            'service_reports': service_reports,
            'ecosystem_summary': self._generate_ecosystem_summary(overview, service_reports)
        }
        
        # Save report
        await self._save_report(comprehensive_report, f"system_report_{hours}h")
        
        # Display summary
        self._display_system_report_summary(comprehensive_report)
        
        return comprehensive_report
    
    def _display_test_results(self, results: Dict[str, Any], test_type: str):
        """Display test results in a readable format"""
        print("\n" + "="*60)
        print(f"📊 {test_type.upper()} PERFORMANCE TEST RESULTS")
        print("="*60)
        
        if results.get('success', False):
            print("✅ TEST STATUS: ERFOLGREICH")
            
            if 'throughput_eps' in results:
                print(f"📈 Durchsatz: {results['throughput_eps']:.1f} events/sec")
            if 'latency_p99_ms' in results:
                print(f"⏱️ Latenz P99: {results['latency_p99_ms']:.1f}ms")
            if 'error_rate' in results:
                print(f"❌ Fehlerrate: {results['error_rate']:.3f}")
            
        else:
            print("❌ TEST STATUS: FEHLGESCHLAGEN")
            if 'error' in results:
                print(f"🔍 Fehler: {results['error']}")
        
        # Comprehensive test specific results
        if test_type == 'comprehensive' and 'test_suite_summary' in results:
            summary = results['test_suite_summary']
            print(f"\n📋 Test Suite Zusammenfassung:")
            print(f"   Szenarien: {summary.get('successful_scenarios', 0)}/{summary.get('total_scenarios', 0)}")
            print(f"   Tests: {summary.get('successful_tests', 0)}/{summary.get('total_tests', 0)}")
            print(f"   Erfolgsrate: {summary.get('test_success_rate', 0)*100:.1f}%")
            print(f"   Dauer: {summary.get('duration_minutes', 0):.1f} Minuten")
            
            if 'conclusion' in results:
                conclusion = results['conclusion']
                print(f"\n🎯 Fazit: {conclusion.get('status', 'Unknown')}")
                print(f"   {conclusion.get('message', 'Keine Nachricht verfügbar')}")
                print(f"   Production Ready: {'✅ Ja' if conclusion.get('ready_for_production', False) else '❌ Nein'}")
        
        print("="*60 + "\n")
    
    def _display_monitoring_update(self, overview: Dict[str, Any]):
        """Display live monitoring update"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        system_health = overview.get('system_health', 'unknown')
        active_alerts = overview.get('active_alerts', 0)
        
        health_emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🚨"}.get(system_health, "❓")
        
        print(f"[{timestamp}] {health_emoji} System: {system_health} | Alerts: {active_alerts}")
        
        # Show key metrics
        metrics = overview.get('system_metrics', {})
        if metrics:
            print(f"           📈 Durchsatz: {metrics.get('total_throughput_eps', 0):.1f} eps")
            print(f"           ⏱️ Latenz: {metrics.get('avg_latency_ms', 0):.1f}ms")
            print(f"           💾 Memory: {metrics.get('total_memory_mb', 0):.0f}MB")
    
    def _display_system_report_summary(self, report: Dict[str, Any]):
        """Display system report summary"""
        print("\n" + "="*70)
        print("📋 SYSTEM REPORT ZUSAMMENFASSUNG")
        print("="*70)
        
        overview = report.get('system_overview', {})
        ecosystem_summary = report.get('ecosystem_summary', {})
        
        # System health
        system_health = overview.get('system_health', 'unknown')
        health_emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🚨"}.get(system_health, "❓")
        print(f"{health_emoji} System Health: {system_health}")
        
        # Service count
        total_services = overview.get('total_services', 0)
        healthy_services = ecosystem_summary.get('healthy_services', 0)
        print(f"🔧 Services: {healthy_services}/{total_services} gesund")
        
        # System metrics
        metrics = overview.get('system_metrics', {})
        if metrics:
            print(f"📈 Gesamtdurchsatz: {metrics.get('total_throughput_eps', 0):.1f} events/sec")
            print(f"⏱️ Durchschnittliche Latenz: {metrics.get('avg_latency_ms', 0):.1f}ms")
            print(f"💾 Gesamter Memory: {metrics.get('total_memory_mb', 0):.0f}MB")
        
        # Alerts
        active_alerts = overview.get('active_alerts', 0)
        if active_alerts > 0:
            print(f"🚨 Aktive Alerts: {active_alerts}")
        else:
            print("✅ Keine aktiven Alerts")
        
        # Top performing services
        top_services = ecosystem_summary.get('top_performing_services', [])
        if top_services:
            print(f"\n🏆 Top Services:")
            for i, service in enumerate(top_services[:3], 1):
                print(f"   {i}. {service['name']} - {service['performance_grade']}")
        
        print("="*70)
        print(f"📁 Report gespeichert in: {self.reports_dir}")
        print("="*70 + "\n")
    
    def _generate_ecosystem_summary(self, overview: Dict[str, Any], 
                                   service_reports: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate ecosystem-specific summary"""
        
        # Count healthy services
        services = overview.get('services', {})
        healthy_services = len([s for s in services.values() if s.get('status') == 'healthy'])
        
        # Get top performing services
        top_services = []
        for service_name, report in service_reports.items():
            grade = report.get('performance_grade', 'D')
            top_services.append({
                'name': service_name,
                'performance_grade': grade,
                'throughput': report.get('throughput', {}).get('avg_eps', 0)
            })
        
        # Sort by grade and throughput
        grade_order = {'A+': 9, 'A': 8, 'B': 7, 'C': 6, 'D': 5}
        top_services.sort(key=lambda x: (grade_order.get(x['performance_grade'], 0), x['throughput']), reverse=True)
        
        # Calculate ecosystem health score
        total_services = len(services)
        health_score = (healthy_services / total_services * 100) if total_services > 0 else 0
        
        return {
            'healthy_services': healthy_services,
            'total_services': total_services,
            'ecosystem_health_score': health_score,
            'top_performing_services': top_services,
            'recommendations': self._generate_ecosystem_recommendations(overview, service_reports)
        }
    
    def _generate_ecosystem_recommendations(self, overview: Dict[str, Any], 
                                          service_reports: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate ecosystem-specific recommendations"""
        recommendations = []
        
        # Check system health
        if overview.get('system_health') != 'healthy':
            recommendations.append("🚨 System Health kritisch - sofortige Untersuchung erforderlich")
        
        # Check active alerts
        active_alerts = overview.get('active_alerts', 0)
        if active_alerts > 5:
            recommendations.append(f"⚠️ {active_alerts} aktive Alerts - Alert-Management optimieren")
        
        # Check service performance
        poor_services = []
        for service_name, report in service_reports.items():
            grade = report.get('performance_grade', 'D')
            if grade in ['D', 'C']:
                poor_services.append(service_name)
        
        if poor_services:
            recommendations.append(f"📈 Performance optimieren für: {', '.join(poor_services)}")
        
        # Check memory usage
        total_memory = overview.get('system_metrics', {}).get('total_memory_mb', 0)
        if total_memory > 4096:  # > 4GB
            recommendations.append("💾 Memory Usage hoch - Memory-Optimierung erwägen")
        
        # Trading-specific recommendations
        if 'intelligent-core-service' in service_reports:
            intel_report = service_reports['intelligent-core-service']
            avg_latency = intel_report.get('latency', {}).get('avg_p99_ms', 0)
            if avg_latency > 200:
                recommendations.append("🧠 Intelligence Service Latenz optimieren für Trading-Performance")
        
        if not recommendations:
            recommendations.append("✅ System läuft optimal - keine sofortigen Maßnahmen erforderlich")
        
        return recommendations
    
    async def _save_report(self, report: Dict[str, Any], filename_prefix: str):
        """Save report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = self.reports_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info("Report saved", filepath=str(filepath))
        except Exception as e:
            print(f"⚠️ Report konnte nicht gespeichert werden: {str(e)}")


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Redis Event-Bus CLI Test Tool für aktienanalyse-ökosystem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s health                    # Quick Health Check
  %(prog)s test basic               # Basic Performance Test
  %(prog)s test comprehensive       # Umfassende Performance Tests
  %(prog)s monitor --duration 30    # 30 Minuten Live-Monitoring
  %(prog)s report --hours 24        # 24h System Report generieren
  %(prog)s status                   # Aktueller System Status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Befehle')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Quick System Health Check')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Performance Tests ausführen')
    test_parser.add_argument('type', choices=['basic', 'comprehensive'], 
                           default='basic', nargs='?',
                           help='Test-Typ (default: basic)')
    test_parser.add_argument('--output', help='Output-Datei für Testergebnisse')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Live-Monitoring starten')
    monitor_parser.add_argument('--duration', type=int, default=60,
                              help='Monitoring-Dauer in Minuten (default: 60)')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='System Report generieren')
    report_parser.add_argument('--hours', type=int, default=24,
                             help='Report-Zeitraum in Stunden (default: 24)')
    report_parser.add_argument('--output', help='Output-Datei für Report')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Aktueller System Status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = EventBusCLI()
    
    try:
        if args.command == 'health':
            await cli.initialize_system()
            try:
                result = await cli.run_quick_health_check()
                if args.output if hasattr(args, 'output') and args.output else False:
                    with open(args.output, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
            finally:
                await cli.shutdown_system()
        
        elif args.command == 'test':
            await cli.initialize_system()
            try:
                result = await cli.run_performance_tests(args.type)
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
            finally:
                await cli.shutdown_system()
        
        elif args.command == 'monitor':
            await cli.initialize_system()
            try:
                await cli.start_live_monitoring(args.duration)
            finally:
                await cli.shutdown_system()
        
        elif args.command == 'report':
            await cli.initialize_system()
            try:
                result = await cli.generate_system_report(args.hours)
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
            finally:
                await cli.shutdown_system()
        
        elif args.command == 'status':
            # Status can work without full initialization
            try:
                status = get_current_system_status()
                print("\n" + "="*50)
                print("📊 AKTUELLER SYSTEM STATUS")
                print("="*50)
                
                if status.get('status') == 'not_initialized':
                    print("⚠️ Event-Bus System nicht initialisiert")
                    print("💡 Tipp: Verwende 'health' für vollständigen Check")
                else:
                    print(f"✅ System Status: {status.get('status', 'Unknown')}")
                    if 'message' in status:
                        print(f"📝 Details: {status['message']}")
                
                print("="*50 + "\n")
                
            except Exception as e:
                print(f"❌ Status-Abfrage fehlgeschlagen: {str(e)}")
        
    except KeyboardInterrupt:
        print("\n🛑 Vorgang durch Benutzer abgebrochen")
    except Exception as e:
        print(f"❌ CLI Fehler: {str(e)}")
        logger.error("CLI execution failed", error=str(e))
    
    print("👋 Event-Bus CLI Tool beendet")


if __name__ == "__main__":
    asyncio.run(main())