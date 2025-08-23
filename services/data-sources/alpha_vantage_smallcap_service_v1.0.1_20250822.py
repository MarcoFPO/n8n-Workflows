#!/usr/bin/env python3
"""
Alpha Vantage Small-Cap Data Source Service
Spezialisiert auf Nebenwerte und Small-Cap Aktien mit technischen Indikatoren
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Any, Optional

# Add path for logging

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/opt/aktienanalyse-ökosystem/shared') -> Import Manager
from logging_config import setup_logging

logger = setup_logging("alpha-vantage-smallcap")

class AlphaVantageSmallCapService:
    """Alpha Vantage Small-Cap Data Source Service"""
    
    def __init__(self):
        self.running = False
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')  # Demo key for testing
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
        
        # Small-Cap Focus: Symbols unter 2 Milliarden Marktkapitalisierung
        self.small_cap_symbols = [
            'PLUG', 'FCEL', 'SPWR', 'SEDG', 'ENPH',  # Clean Energy Small-Caps
            'CRSP', 'EDIT', 'NTLA', 'BEAM', 'VERV',  # Biotech Small-Caps
            'ROKU', 'PINS', 'SNAP', 'SPOT', 'ZM',    # Tech Small-Caps
            'ETSY', 'SHOP', 'SQ', 'PYPL', 'ADYEY',   # Fintech Small-Caps
            'TDOC', 'VEEV', 'ZS', 'OKTA', 'CRWD'     # Healthcare Tech Small-Caps
        ]
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing Alpha Vantage Small-Cap Service")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Aktienanalyse-System/1.0'}
        )
        self.running = True
        logger.info("Alpha Vantage Small-Cap Service initialized", 
                   symbols_tracked=len(self.small_cap_symbols))
        return True
        
    async def get_small_cap_overview(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive small-cap stock overview"""
        try:
            # Get basic quote
            quote_data = await self._get_global_quote(symbol)
            
            # Get technical indicators
            rsi_data = await self._get_rsi(symbol)
            macd_data = await self._get_macd(symbol)
            
            # Combine data
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'alpha_vantage_smallcap',
                'data_type': 'small_cap_overview',
                'quote': quote_data,
                'technical_indicators': {
                    'rsi': rsi_data,
                    'macd': macd_data
                },
                'small_cap_metrics': self._calculate_small_cap_metrics(quote_data),
                'success': True
            }
            
            logger.info("Small-cap overview retrieved", symbol=symbol)
            return result
            
        except Exception as e:
            logger.error("Error getting small-cap overview", symbol=symbol, error=str(e))
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'alpha_vantage_smallcap',
                'error': str(e),
                'success': False
            }
            
    async def _get_global_quote(self, symbol: str) -> Dict[str, Any]:
        """Get global quote data"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        async with self.session.get(self.base_url, params=params) as response:
            data = await response.json()
            
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'price': float(quote.get('05. price', 0)),
                    'change': float(quote.get('09. change', 0)),
                    'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                    'volume': int(quote.get('06. volume', 0)),
                    'previous_close': float(quote.get('08. previous close', 0)),
                    'open': float(quote.get('02. open', 0)),
                    'high': float(quote.get('03. high', 0)),
                    'low': float(quote.get('04. low', 0))
                }
            else:
                logger.warning("No quote data found", symbol=symbol, response=data)
                return {}
                
    async def _get_rsi(self, symbol: str, time_period: int = 14) -> Dict[str, Any]:
        """Get RSI technical indicator"""
        params = {
            'function': 'RSI',
            'symbol': symbol,
            'interval': 'daily',
            'time_period': time_period,
            'series_type': 'close',
            'apikey': self.api_key
        }
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                if 'Technical Analysis: RSI' in data:
                    rsi_data = data['Technical Analysis: RSI']
                    latest_date = max(rsi_data.keys())
                    latest_rsi = float(rsi_data[latest_date]['RSI'])
                    
                    return {
                        'value': latest_rsi,
                        'date': latest_date,
                        'signal': self._interpret_rsi(latest_rsi),
                        'time_period': time_period
                    }
                else:
                    return {'error': 'No RSI data available'}
                    
        except Exception as e:
            logger.error("Error getting RSI", symbol=symbol, error=str(e))
            return {'error': str(e)}
            
    async def _get_macd(self, symbol: str) -> Dict[str, Any]:
        """Get MACD technical indicator"""
        params = {
            'function': 'MACD',
            'symbol': symbol,
            'interval': 'daily',
            'series_type': 'close',
            'apikey': self.api_key
        }
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                if 'Technical Analysis: MACD' in data:
                    macd_data = data['Technical Analysis: MACD']
                    latest_date = max(macd_data.keys())
                    latest_macd = macd_data[latest_date]
                    
                    macd_line = float(latest_macd['MACD'])
                    signal_line = float(latest_macd['MACD_Signal'])
                    histogram = float(latest_macd['MACD_Hist'])
                    
                    return {
                        'macd_line': macd_line,
                        'signal_line': signal_line,
                        'histogram': histogram,
                        'date': latest_date,
                        'signal': self._interpret_macd(macd_line, signal_line, histogram)
                    }
                else:
                    return {'error': 'No MACD data available'}
                    
        except Exception as e:
            logger.error("Error getting MACD", symbol=symbol, error=str(e))
            return {'error': str(e)}
            
    def _interpret_rsi(self, rsi_value: float) -> str:
        """Interpret RSI signal"""
        if rsi_value > 70:
            return "OVERBOUGHT"
        elif rsi_value < 30:
            return "OVERSOLD"
        elif rsi_value > 50:
            return "BULLISH"
        else:
            return "BEARISH"
            
    def _interpret_macd(self, macd_line: float, signal_line: float, histogram: float) -> str:
        """Interpret MACD signal"""
        if macd_line > signal_line and histogram > 0:
            return "STRONG_BUY"
        elif macd_line > signal_line:
            return "BUY"
        elif macd_line < signal_line and histogram < 0:
            return "STRONG_SELL"
        else:
            return "SELL"
            
    def _calculate_small_cap_metrics(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate small-cap specific metrics"""
        if not quote_data:
            return {}
            
        price = quote_data.get('price', 0)
        volume = quote_data.get('volume', 0)
        change_percent = float(quote_data.get('change_percent', '0').replace('%', ''))
        
        # Small-cap volatility assessment
        volatility_score = abs(change_percent)
        
        # Volume analysis
        volume_category = "LOW" if volume < 100000 else "MEDIUM" if volume < 1000000 else "HIGH"
        
        # Risk assessment for small-caps
        risk_level = "HIGH" if volatility_score > 5 else "MEDIUM" if volatility_score > 2 else "LOW"
        
        return {
            'price_category': self._categorize_price(price),
            'volatility_score': round(volatility_score, 2),
            'volume_category': volume_category,
            'risk_level': risk_level,
            'small_cap_rating': self._get_small_cap_rating(price, volume, volatility_score)
        }
        
    def _categorize_price(self, price: float) -> str:
        """Categorize stock by price"""
        if price < 1:
            return "PENNY_STOCK"
        elif price < 5:
            return "MICRO_CAP"
        elif price < 20:
            return "SMALL_CAP"
        else:
            return "MID_CAP"
            
    def _get_small_cap_rating(self, price: float, volume: int, volatility: float) -> str:
        """Get overall small-cap investment rating"""
        score = 0
        
        # Price factor
        if price > 1:
            score += 1
        if price > 5:
            score += 1
            
        # Volume factor  
        if volume > 100000:
            score += 1
        if volume > 500000:
            score += 1
            
        # Volatility factor (inverse)
        if volatility < 3:
            score += 1
        if volatility < 1:
            score += 1
            
        if score >= 5:
            return "STRONG_BUY"
        elif score >= 4:
            return "BUY"
        elif score >= 3:
            return "HOLD"
        elif score >= 2:
            return "CAUTION"
        else:
            return "AVOID"
            
    async def get_small_cap_batch_data(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get batch data for multiple small-cap stocks"""
        results = []
        symbols_to_process = self.small_cap_symbols[:limit]
        
        logger.info("Processing small-cap batch", symbols=len(symbols_to_process))
        
        # Process in small batches to respect API limits
        batch_size = 3
        for i in range(0, len(symbols_to_process), batch_size):
            batch = symbols_to_process[i:i + batch_size]
            
            # Process batch
            batch_tasks = [self.get_small_cap_overview(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error("Batch processing error", error=str(result))
                else:
                    results.append(result)
                    
            # Rate limiting: Wait between batches
            if i + batch_size < len(symbols_to_process):
                await asyncio.sleep(12)  # Alpha Vantage rate limit compliance
                
        logger.info("Small-cap batch completed", results=len(results))
        return results
        
    async def run(self):
        """Main service loop"""
        logger.info("Alpha Vantage Small-Cap Service started successfully")
        
        while self.running:
            try:
                # Periodic batch update
                batch_data = await self.get_small_cap_batch_data(5)
                logger.info("Periodic batch update completed", 
                          results=len(batch_data),
                          timestamp=datetime.now().isoformat())
                          
                # Wait 1 hour between batch updates (API limit consideration)
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error("Error in service loop", error=str(e))
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Alpha Vantage Small-Cap Service stopped")

async def main():
    """Main entry point"""
    service = AlphaVantageSmallCapService()
    
    try:
        success = await service.initialize()
        if not success:
            logger.error("Failed to initialize service")
            return 1
        
        await service.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        await service.shutdown()
        return 0
    except Exception as e:
        logger.error("Service failed", error=str(e))
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical service error", error=str(e))
        sys.exit(1)