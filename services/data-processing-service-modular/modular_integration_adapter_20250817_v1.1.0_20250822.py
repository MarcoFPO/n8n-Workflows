#!/usr/bin/env python3
"""
Modular Integration Adapter
Integriert die neue modulare Datenquellen-Architektur in bestehende Services
Stellt Kompatibilität zwischen alter und neuer Architektur sicher
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import json

# Add paths for imports

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared') -> Import Manager

from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType
from logging_config import setup_logging
import structlog

logger = setup_logging("modular-integration-adapter")


class ModularIntegrationAdapter(BackendBaseModule):
    """
    Adapter für Integration der neuen modularen Architektur
    Übersetzt zwischen alten direkten Aufrufen und neuen Event-Bus-basierten Modulen
    """
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("modular_integration_adapter", event_bus)
        
        # Response tracking für synchrone API-Kompatibilität
        self.pending_requests = {}
        self.request_timeout = 30.0
        
        # Legacy compatibility mapping
        self.legacy_mapping = {
            'companies_marketcap_connector': 'marketcap_data_source',
            'profit_calculation': 'profit_calculation_engine'
        }
        
        # Performance Metriken
        self.metrics = {
            'requests_translated': 0,
            'successful_translations': 0,
            'legacy_api_calls': 0,
            'modular_api_calls': 0,
            'average_response_time': 0.0
        }
        
    async def _initialize_module(self) -> bool:
        """Initialize integration adapter"""
        try:
            logger.info("Initializing Modular Integration Adapter")
            
            # Test connectivity to new modular services
            await self._test_modular_services()
            
            logger.info("Modular Integration Adapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Modular Integration Adapter", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to integration events"""
        # Subscribe to responses from new modular services
        await self.subscribe_to_event(
            'data_source.marketcap.response',
            self._handle_marketcap_response
        )
        
        await self.subscribe_to_event(
            'profit_calculation.response',
            self._handle_calculation_response
        )
        
        # Subscribe to legacy integration requests
        await self.subscribe_to_event(
            'legacy.integration.request',
            self._handle_legacy_request
        )
    
    async def _test_modular_services(self):
        """Test connectivity to new modular services"""
        try:
            # Test MarketCap Data Source
            test_request_id = str(uuid.uuid4())
            await self.publish_module_event(
                'data_source.health_check',
                {
                    'request_id': test_request_id,
                    'source_name': 'marketcap_data_source'
                }
            )
            
            # Test Profit Calculation Engine
            await self.publish_module_event(
                'profit_calculation.status',
                {
                    'request_id': str(uuid.uuid4())
                }
            )
            
            logger.info("Modular services connectivity test completed")
            
        except Exception as e:
            logger.warning("Modular services connectivity test failed", error=str(e))
    
    async def get_companies_marketcap_legacy_compatible(self, country: str = "usa", limit: int = 100) -> List[Dict[str, Any]]:
        """
        Legacy-kompatible Methode für MarketCap-Daten
        Übersetzt alte API-Aufrufe in neue Event-Bus-basierte Aufrufe
        """
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        try:
            logger.info("Processing legacy MarketCap request", 
                       request_id=request_id, country=country, limit=limit)
            
            # Initialize response tracking
            self.pending_requests[request_id] = {
                'type': 'marketcap_batch',
                'start_time': start_time,
                'resolved': False,
                'result': None
            }
            
            # Send request to new modular data source
            await self.publish_module_event(
                'data_source.marketcap.batch_request',
                {
                    'request_id': request_id,
                    'country': country,
                    'limit': limit,
                    'requested_by': 'modular_integration_adapter'
                }
            )
            
            # Wait for response
            result = await self._wait_for_response(request_id, 'marketcap_batch')
            
            if result and result.get('success'):
                companies_data = result.get('data', [])
                
                # Convert to legacy format
                legacy_companies = []
                for company_data in companies_data:
                    legacy_company = self._convert_to_legacy_marketcap_format(company_data)
                    legacy_companies.append(legacy_company)
                
                self.metrics['successful_translations'] += 1
                logger.info("Legacy MarketCap request completed successfully", 
                           request_id=request_id, count=len(legacy_companies))
                
                return legacy_companies
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No response received'
                logger.error("Legacy MarketCap request failed", 
                           request_id=request_id, error=error_msg)
                return []
                
        except Exception as e:
            logger.error("Error in legacy MarketCap request", 
                        request_id=request_id, error=str(e))
            return []
        
        finally:
            self.metrics['requests_translated'] += 1
            self.metrics['legacy_api_calls'] += 1
            self._update_response_time_metric(start_time)
            
            # Cleanup
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    async def search_company_legacy_compatible(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Legacy-kompatible Methode für Unternehmenssuche
        """
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        try:
            logger.info("Processing legacy company search", 
                       request_id=request_id, query=query)
            
            # Initialize response tracking
            self.pending_requests[request_id] = {
                'type': 'company_search',
                'start_time': start_time,
                'resolved': False,
                'result': None
            }
            
            # Send request to new modular data source
            await self.publish_module_event(
                'data_source.marketcap.request',
                {
                    'request_id': request_id,
                    'symbol': query,  # Try as symbol first
                    'company_name': query,  # Also try as company name
                    'requested_by': 'modular_integration_adapter'
                }
            )
            
            # Wait for response
            result = await self._wait_for_response(request_id, 'company_search')
            
            if result and result.get('success'):
                company_data = result.get('data', {})
                legacy_company = self._convert_to_legacy_marketcap_format(company_data)
                
                self.metrics['successful_translations'] += 1
                logger.info("Legacy company search completed successfully", 
                           request_id=request_id, company=legacy_company.get('name', query))
                
                return legacy_company
            else:
                logger.info("Company not found in legacy search", 
                           request_id=request_id, query=query)
                return None
                
        except Exception as e:
            logger.error("Error in legacy company search", 
                        request_id=request_id, error=str(e))
            return None
        
        finally:
            self.metrics['requests_translated'] += 1
            self.metrics['legacy_api_calls'] += 1
            self._update_response_time_metric(start_time)
            
            # Cleanup
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    async def calculate_profit_prediction_legacy_compatible(self, symbol: str, company_name: str = None, 
                                                          forecast_days: int = 30) -> Dict[str, Any]:
        """
        Legacy-kompatible Methode für Gewinnvorhersage-Berechnung
        """
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        try:
            logger.info("Processing legacy profit calculation", 
                       request_id=request_id, symbol=symbol, forecast_days=forecast_days)
            
            # Initialize response tracking
            self.pending_requests[request_id] = {
                'type': 'profit_calculation',
                'start_time': start_time,
                'resolved': False,
                'result': None
            }
            
            # Send request to new calculation engine
            await self.publish_module_event(
                'profit_calculation.request',
                {
                    'request_id': request_id,
                    'symbol': symbol,
                    'company_name': company_name,
                    'forecast_days': forecast_days,
                    'data_sources': ['marketcap'],
                    'requested_by': 'modular_integration_adapter'
                }
            )
            
            # Wait for response
            result = await self._wait_for_response(request_id, 'profit_calculation')
            
            if result and result.get('success'):
                prediction_data = result.get('prediction', {})
                legacy_prediction = self._convert_to_legacy_prediction_format(prediction_data)
                
                self.metrics['successful_translations'] += 1
                logger.info("Legacy profit calculation completed successfully", 
                           request_id=request_id, symbol=symbol,
                           recommendation=legacy_prediction.get('recommendation'))
                
                return legacy_prediction
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No response received'
                logger.error("Legacy profit calculation failed", 
                           request_id=request_id, error=error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'symbol': symbol
                }
                
        except Exception as e:
            logger.error("Error in legacy profit calculation", 
                        request_id=request_id, error=str(e))
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol
            }
        
        finally:
            self.metrics['requests_translated'] += 1
            self.metrics['legacy_api_calls'] += 1
            self._update_response_time_metric(start_time)
            
            # Cleanup
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    def _convert_to_legacy_marketcap_format(self, modular_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert new modular format to legacy MarketCap format"""
        try:
            company_info = modular_data.get('company_info', {})
            financial_metrics = modular_data.get('financial_metrics', {})
            analysis_metrics = modular_data.get('analysis_metrics', {})
            
            # Legacy format compatible with existing code
            legacy_format = {
                'rank': company_info.get('rank', 0),
                'name': company_info.get('name', ''),
                'ticker': company_info.get('symbol', ''),
                'market_cap': financial_metrics.get('market_cap', 0),
                'stock_price': financial_metrics.get('stock_price', 0),
                'daily_change_percent': financial_metrics.get('daily_change_percent', 0),
                'country': company_info.get('country', ''),
                'currency': company_info.get('currency', 'USD'),
                'last_updated': modular_data.get('timestamp', datetime.now().isoformat()),
                
                # Additional fields for enhanced compatibility
                'analysis_score': analysis_metrics.get('analysis_score', 0),
                'market_cap_category': analysis_metrics.get('market_cap_category', ''),
                'risk_level': analysis_metrics.get('risk_level', 'medium')
            }
            
            return legacy_format
            
        except Exception as e:
            logger.error("Error converting to legacy MarketCap format", error=str(e))
            return {}
    
    def _convert_to_legacy_prediction_format(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert new prediction format to legacy format"""
        try:
            # Legacy format compatible with existing database and API
            legacy_format = {
                'success': True,
                'symbol': prediction_data.get('symbol', ''),
                'company_name': prediction_data.get('company_name', ''),
                'score': prediction_data.get('score', 0),
                'profit_forecast': prediction_data.get('profit_forecast', 0),
                'forecast_period_days': prediction_data.get('forecast_period_days', 30),
                'recommendation': prediction_data.get('recommendation', 'HOLD'),
                'confidence_level': prediction_data.get('confidence_level', 0.5),
                'trend': prediction_data.get('trend', 'neutral'),
                'target_date': prediction_data.get('target_date', ''),
                'created_at': prediction_data.get('created_at', datetime.now().isoformat()),
                
                # Enhanced fields from new architecture
                'source_count': prediction_data.get('source_count', 1),
                'source_reliability': prediction_data.get('source_reliability', 0.5),
                'calculation_method': prediction_data.get('calculation_method', 'single_source'),
                'risk_assessment': prediction_data.get('risk_assessment', 'medium'),
                
                # Metadata
                'base_metrics': prediction_data.get('base_metrics', {}),
                'modular_architecture': True,
                'adapter_version': '1.0.0'
            }
            
            return legacy_format
            
        except Exception as e:
            logger.error("Error converting to legacy prediction format", error=str(e))
            return {'success': False, 'error': str(e)}
    
    async def _handle_marketcap_response(self, event):
        """Handle MarketCap data source responses"""
        try:
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id')
            if request_id and request_id in self.pending_requests:
                self.pending_requests[request_id]['result'] = data
                self.pending_requests[request_id]['resolved'] = True
                
                logger.debug("Received MarketCap response", request_id=request_id)
                
        except Exception as e:
            logger.error("Error handling MarketCap response", error=str(e))
    
    async def _handle_calculation_response(self, event):
        """Handle profit calculation responses"""
        try:
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id')
            if request_id and request_id in self.pending_requests:
                self.pending_requests[request_id]['result'] = data
                self.pending_requests[request_id]['resolved'] = True
                
                logger.debug("Received calculation response", request_id=request_id)
                
        except Exception as e:
            logger.error("Error handling calculation response", error=str(e))
    
    async def _handle_legacy_request(self, event):
        """Handle legacy integration requests"""
        try:
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_type = data.get('type')
            request_id = data.get('request_id', str(uuid.uuid4()))
            
            if request_type == 'marketcap_companies':
                country = data.get('country', 'usa')
                limit = data.get('limit', 100)
                
                companies = await self.get_companies_marketcap_legacy_compatible(country, limit)
                
                await self.publish_module_event(
                    'legacy.integration.response',
                    {
                        'request_id': request_id,
                        'success': True,
                        'data': companies,
                        'type': 'marketcap_companies'
                    }
                )
            
            elif request_type == 'company_search':
                query = data.get('query', '')
                
                company = await self.search_company_legacy_compatible(query)
                
                await self.publish_module_event(
                    'legacy.integration.response',
                    {
                        'request_id': request_id,
                        'success': company is not None,
                        'data': company,
                        'type': 'company_search'
                    }
                )
            
            elif request_type == 'profit_calculation':
                symbol = data.get('symbol', '')
                company_name = data.get('company_name')
                forecast_days = data.get('forecast_days', 30)
                
                prediction = await self.calculate_profit_prediction_legacy_compatible(
                    symbol, company_name, forecast_days
                )
                
                await self.publish_module_event(
                    'legacy.integration.response',
                    {
                        'request_id': request_id,
                        'success': prediction.get('success', False),
                        'data': prediction,
                        'type': 'profit_calculation'
                    }
                )
            
        except Exception as e:
            logger.error("Error handling legacy request", error=str(e))
    
    async def _wait_for_response(self, request_id: str, request_type: str, timeout: float = None) -> Optional[Dict[str, Any]]:
        """Wait for response from modular services"""
        timeout = timeout or self.request_timeout
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if (request_id in self.pending_requests and 
                self.pending_requests[request_id]['resolved']):
                
                return self.pending_requests[request_id]['result']
            
            await asyncio.sleep(0.1)  # Check every 100ms
        
        logger.error(f"Timeout waiting for {request_type} response", 
                    request_id=request_id, timeout=timeout)
        return None
    
    def _update_response_time_metric(self, start_time: datetime):
        """Update average response time metric"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            # Moving average
            self.metrics['average_response_time'] = (
                self.metrics['average_response_time'] * 0.9 + response_time * 0.1
            )
    
    async def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration adapter metrics"""
        return {
            'metrics': self.metrics,
            'pending_requests': len(self.pending_requests),
            'legacy_mapping': self.legacy_mapping,
            'adapter_status': 'active',
            'timestamp': datetime.now().isoformat()
        }
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main business logic processing"""
        try:
            operation = data.get('operation', 'legacy_translation')
            
            if operation == 'get_marketcap_companies':
                country = data.get('country', 'usa')
                limit = data.get('limit', 100)
                
                companies = await self.get_companies_marketcap_legacy_compatible(country, limit)
                return {
                    'success': True,
                    'companies': companies,
                    'count': len(companies)
                }
            
            elif operation == 'search_company':
                query = data.get('query', '')
                company = await self.search_company_legacy_compatible(query)
                
                return {
                    'success': company is not None,
                    'company': company
                }
            
            elif operation == 'calculate_profit':
                symbol = data.get('symbol', '')
                company_name = data.get('company_name')
                forecast_days = data.get('forecast_days', 30)
                
                prediction = await self.calculate_profit_prediction_legacy_compatible(
                    symbol, company_name, forecast_days
                )
                
                return prediction
            
            elif operation == 'get_metrics':
                return await self.get_integration_metrics()
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
                
        except Exception as e:
            logger.error("Error in business logic processing", error=str(e))
            return {'success': False, 'error': str(e)}
    
    async def _cleanup_module(self):
        """Cleanup resources"""
        try:
            # Clear pending requests
            self.pending_requests.clear()
            
            await super()._cleanup_module()
            
        except Exception as e:
            logger.warning("Error during cleanup", error=str(e))


# Singleton instance for easy import in existing services
_adapter_instance = None
_event_bus_instance = None

async def get_modular_integration_adapter():
    """Get singleton instance of modular integration adapter"""
    global _adapter_instance, _event_bus_instance
    
    if _adapter_instance is None:
        _event_bus_instance = EventBusConnector("modular-integration-adapter-singleton")
        await _event_bus_instance.connect()
        
        _adapter_instance = ModularIntegrationAdapter(_event_bus_instance)
        await _adapter_instance.initialize()
    
    return _adapter_instance

async def cleanup_modular_integration_adapter():
    """Cleanup singleton instance"""
    global _adapter_instance, _event_bus_instance
    
    if _adapter_instance:
        await _adapter_instance.shutdown()
        _adapter_instance = None
    
    if _event_bus_instance:
        await _event_bus_instance.disconnect()
        _event_bus_instance = None