#!/usr/bin/env python3
"""
Vereinfachter GUI-Test für aktienanalyse-ökosystem
"""

import sys
import asyncio
import aiohttp
from datetime import datetime

# GUI Testing Module direkt importieren
sys.path.append('services/diagnostic-service-modular')
from modules.gui_testing_module import WebGUIQualityChecker

async def run_simple_gui_test():
    """Einfacher GUI-Test"""
    print("🚀 Starting Simple GUI Quality Test")
    print("=" * 50)
    
    # URL des Frontend Services (läuft auf Port 8005)
    frontend_url = "http://localhost:8005"
    
    print(f"🎯 Target: {frontend_url}")
    
    # GUI-Quality-Checker initialisieren
    async with WebGUIQualityChecker(frontend_url) as checker:
        try:
            # Umfassenden GUI-Test durchführen
            result = await checker.run_comprehensive_gui_test()
            
            print(f"\n✅ GUI Quality Test Completed!")
            print(f"   Success Rate: {result.success_rate:.1f}%")
            print(f"   Total Tests: {result.total_tests}")
            print(f"   ✅ Passed: {result.passed_tests}")
            print(f"   ❌ Failed: {result.failed_tests}")  
            print(f"   ⚠️  Warnings: {result.warning_tests}")
            print(f"   ⏱️  Duration: {result.total_duration_ms:.0f}ms")
            
            print(f"\n📋 Individual Test Results:")
            print("-" * 40)
            
            for test in result.tests:
                if test.status == "success":
                    status_emoji = "✅"
                elif test.status == "warning":
                    status_emoji = "⚠️"
                else:
                    status_emoji = "❌"
                
                print(f"{status_emoji} {test.test_name:20} | {test.status:8} | {test.duration_ms:6.0f}ms")
                
                if test.error_message:
                    print(f"   └─ Error: {test.error_message}")
                
                # Wichtige Details anzeigen
                if test.test_name == "performance" and test.details:
                    metrics = test.details.get("metrics", {})
                    if metrics:
                        print(f"   └─ Page Load: {metrics.get('page_load_ms', 0):.0f}ms, "
                              f"API Response: {metrics.get('api_response_ms', 0):.0f}ms")
                
                elif test.test_name == "api_endpoints" and test.details:
                    successful = test.details.get("successful_endpoints", 0)
                    total = test.details.get("tested_endpoints", 0)
                    print(f"   └─ API Endpoints: {successful}/{total} working")
                
                elif test.test_name == "html_structure" and test.details:
                    passed = test.details.get("passed_checks", 0) 
                    total = test.details.get("total_checks", 0)
                    print(f"   └─ HTML Checks: {passed}/{total} passed")
            
            print(f"\n📊 Quality Assessment:")
            print("-" * 40)
            
            if result.success_rate >= 90:
                print("🟢 EXCELLENT - GUI quality is outstanding")
            elif result.success_rate >= 75:
                print("🟡 GOOD - GUI quality is acceptable with minor issues")
            elif result.success_rate >= 50:
                print("🟠 NEEDS IMPROVEMENT - Several GUI issues detected")
            else:
                print("🔴 CRITICAL - Major GUI problems require immediate attention")
            
            # Empfehlungen basierend auf Testergebnissen
            failed_tests = [t for t in result.tests if t.status == "failed"]
            if failed_tests:
                print(f"\n💡 Recommendations:")
                for test in failed_tests:
                    if test.test_name == "frontend_availability":
                        print("   • Check if Frontend Service is running on port 8005")
                    elif test.test_name == "api_endpoints":
                        print("   • Verify API endpoints are properly implemented")
                    elif test.test_name == "performance":
                        print("   • Optimize page load times and API response times")
                    elif test.test_name == "html_structure":
                        print("   • Improve HTML structure and add missing elements")
            
            return result
            
        except Exception as e:
            print(f"❌ GUI Test Error: {e}")
            print("   • Make sure Frontend Service is running")
            print("   • Check network connectivity")
            print("   • Verify all dependencies are installed")
            return None

if __name__ == "__main__":
    print("🔧 Simple GUI Quality Checker for aktienanalyse-ökosystem")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = asyncio.run(run_simple_gui_test())
    
    if result:
        print(f"\n🎯 Final Result: {result.success_rate:.1f}% success rate")
    else:
        print(f"\n❌ Test could not be completed")
    
    print(f"🕒 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")