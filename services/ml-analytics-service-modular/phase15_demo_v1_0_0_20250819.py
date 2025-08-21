#!/usr/bin/env python3
"""
Phase 15 Demonstration Script - Real-Time Market Intelligence und Event-Driven Analytics Engine
===============================================================================================

Umfassende Demonstration der Phase 15 Capabilities:
- Real-Time Market Intelligence Engine Status
- Event-Driven Market Analysis
- Sentiment Analysis Real-Time Processing
- Economic Indicator Monitoring
- Volatility Spike Detection
- Market Regime Change Analysis
- Correlation Break Detection
- Comprehensive Market Intelligence Reporting
- Real-Time Streaming Management

Author: Claude Code & AI Development Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
import asyncpg
from pathlib import Path
import sys

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Phase15DemonstrationRunner:
    """
    Phase 15 Demonstration Runner - Real-Time Market Intelligence Analytics
    Demonstrates all capabilities of the Market Intelligence Engine
    """
    
    def __init__(self, base_url: str = "http://localhost:8021"):
        self.base_url = base_url
        self.session = None
        self.test_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        self.results = {}
        self.start_time = datetime.utcnow()
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make HTTP request to ML Analytics Service"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Request failed: {response.status} - {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
            
            elif method.upper() == "POST":
                async with self.session.post(url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Request failed: {response.status} - {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            logger.error(f"Request error for {endpoint}: {str(e)}")
            return {"error": str(e)}
    
    async def test_market_intelligence_status(self) -> Dict[str, Any]:
        """Test 1: Market Intelligence Engine Status"""
        logger.info("🔍 Testing Market Intelligence Engine Status...")
        
        result = await self.make_request("/api/v1/market-intelligence/status")
        
        if "error" not in result:
            logger.info(f"✅ Market Intelligence Engine Status: {result.get('status', 'Unknown')}")
            logger.info(f"   - Components Initialized: {result.get('components_initialized', 0)}")
            logger.info(f"   - Event Processing Active: {result.get('event_processing_active', False)}")
            logger.info(f"   - Total Events Processed: {result.get('total_events_processed', 0)}")
        else:
            logger.error(f"❌ Market Intelligence Status Test Failed: {result['error']}")
        
        return result
    
    async def test_recent_events(self) -> Dict[str, Any]:
        """Test 2: Recent Market Events Analysis"""
        logger.info("📊 Testing Recent Market Events Retrieval...")
        
        result = await self.make_request("/api/v1/market-intelligence/events", params={"limit": 25})
        
        if "error" not in result and "events" in result:
            events_count = result.get("count", 0)
            logger.info(f"✅ Retrieved {events_count} Recent Market Events")
            
            if events_count > 0:
                # Show sample events
                events = result["events"][:5]  # Show first 5 events
                for i, event in enumerate(events, 1):
                    logger.info(f"   Event {i}: {event.get('event_type', 'Unknown')} - {event.get('description', 'No description')[:100]}...")
                    
        else:
            logger.error(f"❌ Recent Events Test Failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    async def test_realtime_sentiment_analysis(self) -> Dict[str, Any]:
        """Test 3: Real-Time Sentiment Analysis"""
        logger.info("💭 Testing Real-Time Sentiment Analysis...")
        
        sentiment_results = {}
        
        for symbol in self.test_symbols[:3]:  # Test first 3 symbols
            logger.info(f"   Analyzing sentiment for {symbol}...")
            result = await self.make_request(f"/api/v1/market-intelligence/sentiment/{symbol}", 
                                           params={"timeframe_hours": 24})
            
            if "error" not in result and "sentiment_analysis" in result:
                sentiment = result["sentiment_analysis"]
                logger.info(f"   ✅ {symbol} Sentiment Score: {sentiment.get('overall_sentiment', 0):.3f}")
                logger.info(f"      - Positive Sources: {sentiment.get('positive_sources', 0)}")
                logger.info(f"      - Negative Sources: {sentiment.get('negative_sources', 0)}")
                logger.info(f"      - Confidence: {sentiment.get('confidence', 0):.3f}")
                sentiment_results[symbol] = sentiment
            else:
                logger.error(f"   ❌ Sentiment analysis failed for {symbol}: {result.get('error', 'Unknown')}")
                sentiment_results[symbol] = {"error": result.get('error', 'Unknown')}
        
        return {"sentiment_results": sentiment_results}
    
    async def test_volatility_alerts(self) -> Dict[str, Any]:
        """Test 4: Volatility Spike Detection"""
        logger.info("⚡ Testing Volatility Spike Detection...")
        
        result = await self.make_request("/api/v1/market-intelligence/volatility-alerts", params={"limit": 15})
        
        if "error" not in result and "volatility_alerts" in result:
            alerts_count = result.get("count", 0)
            logger.info(f"✅ Detected {alerts_count} Volatility Alerts")
            
            if alerts_count > 0:
                alerts = result["volatility_alerts"][:5]  # Show first 5 alerts
                for i, alert in enumerate(alerts, 1):
                    logger.info(f"   Alert {i}: {alert.get('symbol', 'Unknown')} - Volatility: {alert.get('volatility_spike', 0):.2f}%")
                    logger.info(f"            Trigger: {alert.get('trigger_reason', 'Unknown')}")
        else:
            logger.error(f"❌ Volatility Alerts Test Failed: {result.get('error', 'Unknown')}")
        
        return result
    
    async def test_market_regime_analysis(self) -> Dict[str, Any]:
        """Test 5: Market Regime Change Detection"""
        logger.info("📈 Testing Market Regime Change Analysis...")
        
        result = await self.make_request("/api/v1/market-intelligence/regime-analysis")
        
        if "error" not in result and "market_regime_analysis" in result:
            analysis = result["market_regime_analysis"]
            logger.info(f"✅ Current Market Regime: {analysis.get('current_regime', 'Unknown')}")
            logger.info(f"   - Regime Confidence: {analysis.get('regime_confidence', 0):.3f}")
            logger.info(f"   - Regime Duration: {analysis.get('regime_duration_days', 0)} days")
            logger.info(f"   - Transition Probability: {analysis.get('transition_probability', 0):.3f}")
            
            if "regime_indicators" in analysis:
                indicators = analysis["regime_indicators"]
                logger.info(f"   - VIX Level: {indicators.get('vix_level', 0):.2f}")
                logger.info(f"   - Market Volatility: {indicators.get('market_volatility', 0):.3f}")
                logger.info(f"   - Trend Strength: {indicators.get('trend_strength', 0):.3f}")
        else:
            logger.error(f"❌ Market Regime Analysis Failed: {result.get('error', 'Unknown')}")
        
        return result
    
    async def test_economic_indicators(self) -> Dict[str, Any]:
        """Test 6: Economic Indicators Monitoring"""
        logger.info("📊 Testing Economic Indicators Monitoring...")
        
        result = await self.make_request("/api/v1/market-intelligence/economic-indicators")
        
        if "error" not in result and "economic_indicators" in result:
            indicators = result["economic_indicators"]
            logger.info(f"✅ Retrieved {len(indicators)} Economic Indicators")
            
            # Show key indicators
            key_indicators = ["GDP_GROWTH", "UNEMPLOYMENT_RATE", "INFLATION_RATE", "INTEREST_RATES", "PMI"]
            for indicator in key_indicators:
                if indicator in indicators:
                    value = indicators[indicator]
                    logger.info(f"   - {indicator}: {value.get('current_value', 'N/A')} (Change: {value.get('change', 0):.2f}%)")
        else:
            logger.error(f"❌ Economic Indicators Test Failed: {result.get('error', 'Unknown')}")
        
        return result
    
    async def test_correlation_breaks(self) -> Dict[str, Any]:
        """Test 7: Correlation Break Detection"""
        logger.info("🔗 Testing Correlation Break Analysis...")
        
        result = await self.make_request("/api/v1/market-intelligence/correlation-breaks", params={"limit": 10})
        
        if "error" not in result and "correlation_breaks" in result:
            breaks_count = result.get("count", 0)
            logger.info(f"✅ Detected {breaks_count} Correlation Breaks")
            
            if breaks_count > 0:
                breaks = result["correlation_breaks"][:3]  # Show first 3 breaks
                for i, break_event in enumerate(breaks, 1):
                    logger.info(f"   Break {i}: {break_event.get('asset_pair', 'Unknown Pair')}")
                    logger.info(f"            Previous Correlation: {break_event.get('previous_correlation', 0):.3f}")
                    logger.info(f"            Current Correlation: {break_event.get('current_correlation', 0):.3f}")
                    logger.info(f"            Break Magnitude: {break_event.get('break_magnitude', 0):.3f}")
        else:
            logger.error(f"❌ Correlation Breaks Test Failed: {result.get('error', 'Unknown')}")
        
        return result
    
    async def test_streaming_management(self) -> Dict[str, Any]:
        """Test 8: Streaming Intelligence Management"""
        logger.info("🔄 Testing Market Intelligence Streaming Management...")
        
        # Test starting streaming
        start_result = await self.make_request("/api/v1/market-intelligence/start-streaming", method="POST")
        
        if "error" not in start_result:
            logger.info(f"✅ Streaming Started: {start_result.get('status', 'Unknown')}")
            logger.info(f"   Message: {start_result.get('message', 'No message')}")
            
            # Wait a moment for streaming to initialize
            await asyncio.sleep(2)
            
            # Test stopping streaming
            stop_result = await self.make_request("/api/v1/market-intelligence/stop-streaming", method="POST")
            
            if "error" not in stop_result:
                logger.info(f"✅ Streaming Stopped: {stop_result.get('status', 'Unknown')}")
                return {"start_result": start_result, "stop_result": stop_result}
            else:
                logger.error(f"❌ Failed to stop streaming: {stop_result.get('error', 'Unknown')}")
                return {"start_result": start_result, "stop_error": stop_result["error"]}
        else:
            logger.error(f"❌ Failed to start streaming: {start_result.get('error', 'Unknown')}")
            return {"start_error": start_result["error"]}
    
    async def test_comprehensive_intelligence_report(self) -> Dict[str, Any]:
        """Test 9: Comprehensive Market Intelligence Report"""
        logger.info("📋 Testing Comprehensive Market Intelligence Report...")
        
        result = await self.make_request("/api/v1/market-intelligence/comprehensive-report")
        
        if "error" not in result and "comprehensive_report" in result:
            report = result["comprehensive_report"]
            logger.info(f"✅ Generated Comprehensive Market Intelligence Report")
            logger.info(f"   - Report Sections: {len(report.get('sections', []))}")
            logger.info(f"   - Total Events Analyzed: {report.get('total_events_analyzed', 0)}")
            logger.info(f"   - Market Sentiment Score: {report.get('overall_market_sentiment', 0):.3f}")
            logger.info(f"   - Risk Level: {report.get('overall_risk_level', 'Unknown')}")
            
            if "key_insights" in report:
                insights = report["key_insights"][:3]  # Show first 3 insights
                logger.info("   Key Insights:")
                for i, insight in enumerate(insights, 1):
                    logger.info(f"     {i}. {insight}")
                    
        else:
            logger.error(f"❌ Comprehensive Report Failed: {result.get('error', 'Unknown')}")
        
        return result
    
    async def run_comprehensive_demo(self) -> Dict[str, Any]:
        """Run comprehensive Phase 15 demonstration"""
        logger.info("🚀 Starting Phase 15 Comprehensive Demonstration...")
        logger.info("=" * 80)
        
        demo_results = {
            "phase": 15,
            "demo_name": "Real-Time Market Intelligence und Event-Driven Analytics",
            "start_time": self.start_time.isoformat(),
            "tests": {}
        }
        
        # Test sequence
        test_sequence = [
            ("market_intelligence_status", self.test_market_intelligence_status),
            ("recent_events", self.test_recent_events),
            ("realtime_sentiment", self.test_realtime_sentiment_analysis),
            ("volatility_alerts", self.test_volatility_alerts),
            ("market_regime_analysis", self.test_market_regime_analysis),
            ("economic_indicators", self.test_economic_indicators),
            ("correlation_breaks", self.test_correlation_breaks),
            ("streaming_management", self.test_streaming_management),
            ("comprehensive_report", self.test_comprehensive_intelligence_report),
        ]
        
        success_count = 0
        total_tests = len(test_sequence)
        
        for test_name, test_func in test_sequence:
            try:
                logger.info(f"\n{'='*20} {test_name.upper()} {'='*20}")
                result = await test_func()
                demo_results["tests"][test_name] = result
                
                if "error" not in result or not any("error" in v for v in result.values() if isinstance(v, dict)):
                    success_count += 1
                    logger.info(f"✅ Test {test_name} PASSED")
                else:
                    logger.error(f"❌ Test {test_name} FAILED")
                
                # Small delay between tests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Test {test_name} EXCEPTION: {str(e)}")
                demo_results["tests"][test_name] = {"error": str(e)}
        
        # Final summary
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        demo_results.update({
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_tests": total_tests,
            "successful_tests": success_count,
            "failed_tests": total_tests - success_count,
            "success_rate": (success_count / total_tests) * 100
        })
        
        logger.info("\n" + "="*80)
        logger.info("🎯 PHASE 15 DEMONSTRATION SUMMARY")
        logger.info("="*80)
        logger.info(f"📊 Total Tests: {total_tests}")
        logger.info(f"✅ Successful Tests: {success_count}")
        logger.info(f"❌ Failed Tests: {total_tests - success_count}")
        logger.info(f"📈 Success Rate: {(success_count/total_tests)*100:.1f}%")
        logger.info(f"⏱️  Total Duration: {duration:.2f} seconds")
        logger.info("="*80)
        
        if success_count == total_tests:
            logger.info("🎉 ALL PHASE 15 TESTS PASSED! Market Intelligence Engine is fully operational!")
        elif success_count >= total_tests * 0.8:
            logger.info("✅ PHASE 15 MOSTLY SUCCESSFUL! Most market intelligence features are working!")
        else:
            logger.error("❌ PHASE 15 NEEDS ATTENTION! Multiple market intelligence features failed!")
        
        return demo_results
    
    async def save_results(self, results: Dict[str, Any]) -> str:
        """Save demonstration results to file"""
        filename = f"phase15_demo_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(__file__).parent / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📁 Results saved to: {filepath}")
        return str(filepath)


async def main():
    """Main demonstration function"""
    print("🚀 Phase 15 Market Intelligence Demonstration Starting...")
    print("Real-Time Market Intelligence und Event-Driven Analytics Engine")
    print("=" * 80)
    
    async with Phase15DemonstrationRunner() as demo:
        try:
            # Run comprehensive demonstration
            results = await demo.run_comprehensive_demo()
            
            # Save results
            results_file = await demo.save_results(results)
            
            print(f"\n📄 Detailed results saved to: {results_file}")
            print("🎯 Phase 15 Market Intelligence Demonstration Complete!")
            
        except KeyboardInterrupt:
            print("\n⚠️  Demonstration interrupted by user")
        except Exception as e:
            print(f"\n❌ Demonstration failed with error: {str(e)}")
            import traceback
            print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())