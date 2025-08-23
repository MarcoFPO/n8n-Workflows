#!/usr/bin/env python3
"""
Unit Tests für Consolidated Module v1.0.0
Clean Architecture - Testing für alle konsolidierten Module

Test Coverage:
- ConsolidatedTechnicalAnalysis
- ConsolidatedIntelligenceManager  
- ConsolidatedOrderManager (bereits erstellt)
- ConsolidatedAccountManager (bereits erstellt)
- Import Manager
- Service Registry

Code-Qualität: HÖCHSTE PRIORITÄT
- Comprehensive Test Coverage
- Clean Test Architecture
- Fast Execution
- Reliable Test Results
"""

import unittest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import pandas as pd
import numpy as np

# Import Manager Setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test Imports
try:
    from shared.import_manager import ImportManager, setup_imports
    from shared.service_registry import ServiceRegistry, ServiceInfo, ServiceStatus
    from services.intelligent_core_service_modular.consolidated_technical_analysis_v1_0_0_20250821 import (
        ConsolidatedTechnicalAnalysis, TechnicalIndicators, TrendDirection
    )
    from services.intelligent_core_service_modular.consolidated_intelligence_manager_v1_0_0_20250821 import (
        ConsolidatedIntelligenceManager, IntelligenceRecommendation, ActionType, RiskLevel, MarketSentiment
    )
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback für Test-Umgebung ohne alle Dependencies


class TestImportManager(unittest.TestCase):
    """Test Import Manager Functionality"""
    
    def setUp(self):
        self.import_manager = ImportManager()
    
    def test_project_root_detection(self):
        """Test automatic project root detection"""
        project_root = self.import_manager.get_project_root()
        self.assertIsInstance(project_root, str)
        self.assertTrue(len(project_root) > 0)
        self.assertTrue(project_root.endswith('aktienanalyse-ökosystem'))
    
    def test_environment_detection(self):
        """Test environment detection (dev vs production)"""
        is_production = self.import_manager.is_production()
        self.assertIsInstance(is_production, bool)
    
    def test_path_setup(self):
        """Test path configuration"""
        original_path_length = len(sys.path)
        self.import_manager.setup_paths()
        
        # Should add paths to sys.path
        self.assertGreaterEqual(len(sys.path), original_path_length)
    
    def test_get_service_path(self):
        """Test service path retrieval"""
        # Test with known service (may not exist in test env)
        service_path = self.import_manager.get_service_path("frontend-service-modular")
        if service_path:
            self.assertIsInstance(service_path, str)


class TestServiceRegistry(unittest.TestCase):
    """Test Service Registry Functionality"""
    
    def setUp(self):
        self.registry = ServiceRegistry()
    
    def test_service_registration(self):
        """Test service registration"""
        service_info = ServiceInfo(
            name="test_service",
            host="localhost",
            port=8999,
            health_endpoint="/health",
            description="Test service"
        )
        
        result = self.registry.register_service(service_info)
        self.assertTrue(result)
        
        # Verify service is registered
        retrieved_service = self.registry.get_service("test_service")
        self.assertIsNotNone(retrieved_service)
        self.assertEqual(retrieved_service.name, "test_service")
        self.assertEqual(retrieved_service.port, 8999)
    
    def test_service_unregistration(self):
        """Test service unregistration"""
        # Register service first
        service_info = ServiceInfo(
            name="temp_service",
            host="localhost", 
            port=8998,
            health_endpoint="/health"
        )
        self.registry.register_service(service_info)
        
        # Unregister service
        result = self.registry.unregister_service("temp_service")
        self.assertTrue(result)
        
        # Verify service is gone
        retrieved_service = self.registry.get_service("temp_service")
        self.assertIsNone(retrieved_service)
    
    def test_service_filtering(self):
        """Test service filtering methods"""
        # Initially may have some services from config
        initial_count = len(self.registry.list_all_services())
        
        # Test list all services
        all_services = self.registry.list_all_services()
        self.assertIsInstance(all_services, dict)
        self.assertGreaterEqual(len(all_services), 0)
        
        # Test healthy services (none should be healthy without health checks)
        healthy_services = self.registry.get_healthy_services()
        self.assertIsInstance(healthy_services, list)
    
    def test_service_summary(self):
        """Test service summary generation"""
        summary = self.registry.get_service_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertIn("total_services", summary)
        self.assertIn("healthy_services", summary)
        self.assertIn("available_services", summary)
        self.assertIn("discovery_running", summary)
        self.assertIsInstance(summary["total_services"], int)


class TestConsolidatedTechnicalAnalysis(unittest.TestCase):
    """Test Consolidated Technical Analysis"""
    
    def setUp(self):
        self.analyzer = ConsolidatedTechnicalAnalysis()
    
    def test_moving_averages_calculation(self):
        """Test moving averages calculation"""
        # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = [100 + i*0.5 + np.random.normal(0, 1) for i in range(100)]
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'volume': [100000] * 100
        })
        
        ma_results = self.analyzer.calculate_moving_averages(df)
        
        self.assertIn('sma_20', ma_results)
        self.assertIn('sma_50', ma_results)
        self.assertIn('ema_12', ma_results)
        self.assertIn('ema_26', ma_results)
        
        # Values should be reasonable
        for key, value in ma_results.items():
            if value is not None:
                self.assertGreater(value, 0)
                self.assertLess(value, 1000)  # Reasonable range
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        # Create sample data with known pattern
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        prices = [100 + i*2 for i in range(50)]  # Uptrending
        
        df = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': [100000] * 50
        })
        
        rsi = self.analyzer.calculate_rsi(df)
        
        self.assertIsNotNone(rsi)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
        # For uptrending data, RSI should be > 50
        self.assertGreater(rsi, 50)
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        prices = [100 + np.random.normal(0, 2) for _ in range(50)]
        
        df = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': [100000] * 50
        })
        
        bb_results = self.analyzer.calculate_bollinger_bands(df)
        
        self.assertIn('bb_upper', bb_results)
        self.assertIn('bb_middle', bb_results)
        self.assertIn('bb_lower', bb_results)
        self.assertIn('bb_width', bb_results)
        
        # Upper should be > Middle > Lower
        if all(v is not None for v in bb_results.values()):
            self.assertGreater(bb_results['bb_upper'], bb_results['bb_middle'])
            self.assertGreater(bb_results['bb_middle'], bb_results['bb_lower'])
    
    def test_trend_analysis(self):
        """Test trend analysis"""
        # Bullish trend data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = [100 + i*0.5 for i in range(100)]  # Clear uptrend
        
        df = pd.DataFrame({
            'close': prices,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': [100000] * 100
        })
        
        trend_results = self.analyzer.analyze_trend(df)
        
        self.assertIn('trend_direction', trend_results)
        self.assertIn('trend_strength', trend_results)
        
        trend_direction = trend_results['trend_direction']
        self.assertIsInstance(trend_direction, TrendDirection)
        
        # For clear uptrend, should be bullish
        self.assertEqual(trend_direction, TrendDirection.BULLISH)


class TestConsolidatedIntelligenceManager(unittest.TestCase):
    """Test Consolidated Intelligence Manager"""
    
    def setUp(self):
        self.manager = ConsolidatedIntelligenceManager()
    
    def test_risk_assessment(self):
        """Test risk assessment functionality"""
        # Low risk scenario
        low_risk_data = {
            'rsi': 50,
            'atr': 1.0,
            'bb_width': 2.0,
            'volume_ratio': 1.0,
            'current_price': 100,
            'resistance_level': 110,
            'support_level': 90
        }
        
        risk_level, risk_score = self.manager.assess_risk("TEST", low_risk_data)
        
        self.assertIsInstance(risk_level, RiskLevel)
        self.assertIsInstance(risk_score, float)
        self.assertGreaterEqual(risk_score, 0)
        self.assertLessEqual(risk_score, 100)
        
        # High risk scenario
        high_risk_data = {
            'rsi': 85,  # Overbought
            'atr': 5.0,  # High volatility
            'bb_width': 8.0,  # High width
            'volume_ratio': 0.3,  # Low volume
            'current_price': 109,  # Near resistance
            'resistance_level': 110,
            'support_level': 90
        }
        
        high_risk_level, high_risk_score = self.manager.assess_risk("TEST", high_risk_data)
        
        # High risk scenario should have higher risk score
        self.assertGreater(high_risk_score, risk_score)
    
    def test_market_sentiment_analysis(self):
        """Test market sentiment analysis"""
        # Bullish scenario
        bullish_data = {
            'rsi': 45,  # Neutral RSI
            'macd_histogram': 1.5,  # Bullish MACD
            'current_price': 105,
            'sma_20': 102,
            'sma_50': 100,  # Price > SMA20 > SMA50
            'volume_ratio': 1.8  # High volume
        }
        
        sentiment, sentiment_score = self.manager.analyze_market_sentiment("TEST", bullish_data)
        
        self.assertIsInstance(sentiment, MarketSentiment)
        self.assertIsInstance(sentiment_score, float)
        self.assertGreaterEqual(sentiment_score, -100)
        self.assertLessEqual(sentiment_score, 100)
        
        # Should be bullish sentiment
        self.assertIn(sentiment, [MarketSentiment.BULLISH, MarketSentiment.VERY_BULLISH])
        self.assertLess(sentiment_score, 0)  # Negative score = bullish
    
    def test_action_priority_calculation(self):
        """Test action priority calculation"""
        # Buy scenario
        buy_data = {
            'rsi': 25,  # Oversold
            'macd_histogram': 0.5,  # Bullish MACD
            'current_price': 100,
            'sma_20': 102,
            'sma_50': 105,
            'volume_ratio': 1.6
        }
        
        action, priority = self.manager.calculate_action_priority(
            "TEST", buy_data, RiskLevel.LOW, MarketSentiment.BULLISH
        )
        
        self.assertIsInstance(action, ActionType)
        self.assertIsInstance(priority, float)
        self.assertGreaterEqual(priority, 0)
        self.assertLessEqual(priority, 100)
    
    def test_reasoning_generation(self):
        """Test reasoning generation"""
        sample_data = {
            'current_price': 150.0,
            'rsi': 65.0,
            'sma_20': 148.0,
            'sma_50': 145.0
        }
        
        reasoning, key_factors = self.manager.generate_reasoning(
            "TEST", sample_data, ActionType.BUY, RiskLevel.MODERATE, MarketSentiment.BULLISH
        )
        
        self.assertIsInstance(reasoning, str)
        self.assertIsInstance(key_factors, list)
        self.assertGreater(len(reasoning), 10)  # Should have substantial reasoning
        self.assertGreater(len(key_factors), 0)  # Should have key factors
    
    def test_confidence_score_adjustment(self):
        """Test confidence score adjustment"""
        base_score = 70.0
        
        # Test with different risk levels
        low_risk_score = self.manager.adjust_confidence_score(
            base_score, RiskLevel.LOW, 1.0, 50.0
        )
        high_risk_score = self.manager.adjust_confidence_score(
            base_score, RiskLevel.HIGH, 1.0, 50.0
        )
        
        # Low risk should increase confidence, high risk should decrease
        self.assertGreater(low_risk_score, base_score)
        self.assertLess(high_risk_score, base_score)
        
        # Both should be in valid range
        self.assertGreaterEqual(low_risk_score, 0)
        self.assertLessEqual(low_risk_score, 100)
        self.assertGreaterEqual(high_risk_score, 0)
        self.assertLessEqual(high_risk_score, 100)
    
    def test_decision_storage(self):
        """Test decision history storage"""
        sample_recommendation = IntelligenceRecommendation(
            symbol="TEST",
            timestamp="2024-01-01T12:00:00",
            action=ActionType.BUY,
            confidence_score=80.0,
            priority_score=75.0,
            risk_level=RiskLevel.LOW,
            risk_score=25.0,
            market_sentiment=MarketSentiment.BULLISH,
            sentiment_score=-30.0,
            reasoning="Test reasoning",
            key_factors=["Test factor"]
        )
        
        initial_count = len(self.manager.decision_history)
        decision_id = self.manager.store_decision(sample_recommendation)
        
        self.assertIsInstance(decision_id, str)
        self.assertGreater(len(decision_id), 0)
        self.assertEqual(len(self.manager.decision_history), initial_count + 1)
        
        # Test retrieval
        history = self.manager.get_decision_history("TEST")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1].symbol, "TEST")


class TestConsolidatedModulesIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for consolidated modules"""
    
    async def test_technical_analysis_full_workflow(self):
        """Test complete technical analysis workflow"""
        analyzer = ConsolidatedTechnicalAnalysis()
        
        # Mock market data to avoid external dependencies
        with patch.object(analyzer, 'get_market_data') as mock_get_data:
            # Create realistic mock data
            dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
            prices = [100 + i*0.5 + np.random.normal(0, 1) for i in range(100)]
            
            mock_df = pd.DataFrame({
                'date': dates,
                'open': [p * 0.99 for p in prices],
                'high': [p * 1.02 for p in prices],
                'low': [p * 0.98 for p in prices],
                'close': prices,
                'volume': [np.random.randint(100000, 1000000) for _ in range(100)]
            })
            
            mock_get_data.return_value = mock_df
            
            # Test full analysis
            result = await analyzer.analyze_symbol("TEST")
            
            self.assertIsInstance(result, TechnicalIndicators)
            self.assertEqual(result.symbol, "TEST")
            self.assertIsNotNone(result.current_price)
            self.assertIsNotNone(result.rsi)
            self.assertIsNotNone(result.trend_direction)
    
    async def test_intelligence_manager_full_workflow(self):
        """Test complete intelligence manager workflow"""
        manager = ConsolidatedIntelligenceManager()
        
        # Sample comprehensive technical data
        technical_data = {
            'current_price': 150.0,
            'rsi': 45.0,
            'macd_histogram': 0.5,
            'sma_20': 148.0,
            'sma_50': 145.0,
            'atr': 2.5,
            'bb_width': 4.0,
            'volume_ratio': 1.3,
            'resistance_level': 155.0,
            'support_level': 142.0,
            'trend_strength': 65.0
        }
        
        # Test full recommendation generation
        recommendation = await manager.generate_recommendation("TEST", technical_data)
        
        self.assertIsInstance(recommendation, IntelligenceRecommendation)
        self.assertEqual(recommendation.symbol, "TEST")
        self.assertIsInstance(recommendation.action, ActionType)
        self.assertIsInstance(recommendation.risk_level, RiskLevel)
        self.assertIsInstance(recommendation.market_sentiment, MarketSentiment)
        self.assertGreater(len(recommendation.reasoning), 10)
        self.assertGreater(len(recommendation.key_factors), 0)
        self.assertGreater(len(recommendation.decision_id), 0)


if __name__ == '__main__':
    # Setup test environment
    print("=== Running Consolidated Module Tests ===")
    
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise in tests
    
    # Run tests
    unittest.main(verbosity=2)