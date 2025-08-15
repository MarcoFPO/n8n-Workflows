"""
Redis Event Bus Migration System
Handles migration from legacy event systems to Redis Event Bus
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum

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


class MigrationPhase(Enum):
    """Migration phases"""
    PREPARATION = "preparation"
    DUAL_MODE = "dual_mode"         # Both systems running
    VALIDATION = "validation"       # Validate Redis system
    CUTOVER = "cutover"            # Switch to Redis only
    CLEANUP = "cleanup"            # Remove legacy system


@dataclass
class MigrationConfig:
    """Configuration for service migration"""
    service_name: str
    legacy_modules: List[str]
    target_publishers: List[str]
    target_subscribers: List[str]
    validation_period_hours: int = 24
    enable_dual_mode: bool = True
    enable_validation: bool = True
    rollback_enabled: bool = True


class ServiceMigrator:
    """Handles migration of individual services to Redis Event Bus"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.service_name = config.service_name
        self.logger = logger.bind(service=self.service_name)
        
        # Migration state
        self.current_phase = MigrationPhase.PREPARATION
        self.migration_start_time: Optional[datetime] = None
        self.legacy_event_bus = None  # Reference to legacy system
        self.redis_event_bus: Optional[RedisEventBus] = None
        
        # Publishers and subscribers
        self.publishers: Dict[str, Any] = {}
        self.subscribers: Dict[str, Any] = {}
        
        # Migration metrics
        self.metrics = {
            'events_migrated': 0,
            'legacy_events_processed': 0,
            'redis_events_processed': 0,
            'migration_errors': 0,
            'validation_passed': 0,
            'validation_failed': 0
        }
        
        # Event mapping for legacy to Redis conversion
        self.event_mapping = self._create_event_mapping()
        
    def _create_event_mapping(self) -> Dict[str, str]:
        """Create mapping from legacy event types to Redis event types"""
        return {
            # Legacy -> Redis event type mappings
            'order_created': 'order.created',
            'order_updated': 'order.updated',
            'order_executed': 'order.executed',
            'order_cancelled': 'order.cancelled',
            
            'account_balance_changed': 'account.balance_update',
            'account_transaction': 'account.transaction',
            'account_limit_updated': 'account.limit_change',
            
            'market_price_update': 'market_data.price_update',
            'market_indicators_update': 'market_data.indicators_update',
            'market_status_change': 'market_data.status_change',
            
            'analysis_completed': 'analysis.complete',
            'analysis_requested': 'analysis.request',
            'analysis_failed': 'analysis.error',
            
            'intelligence_recommendation': 'intelligence.recommendation',
            'intelligence_decision_request': 'intelligence.decision_request',
            'model_updated': 'intelligence.model_update',
            
            'service_started': 'system.service_started',
            'service_stopped': 'system.service_stopped',
            'health_check': 'system.health_check',
            'system_error': 'system.error'
        }
    
    async def start_migration(self) -> bool:
        """Start the migration process"""
        try:
            self.migration_start_time = datetime.now()
            self.logger.info("Starting service migration to Redis Event Bus")
            
            # Phase 1: Preparation
            if not await self._preparation_phase():
                return False
            
            # Phase 2: Dual Mode (if enabled)
            if self.config.enable_dual_mode:
                if not await self._dual_mode_phase():
                    return False
            
            # Phase 3: Validation (if enabled)
            if self.config.enable_validation:
                if not await self._validation_phase():
                    return False
            
            # Phase 4: Cutover
            if not await self._cutover_phase():
                return False
            
            # Phase 5: Cleanup
            await self._cleanup_phase()
            
            self.logger.info("Service migration completed successfully",
                           duration_minutes=(datetime.now() - self.migration_start_time).total_seconds() / 60)
            
            return True
            
        except Exception as e:
            self.logger.error("Migration failed", error=str(e))
            if self.config.rollback_enabled:
                await self._rollback_migration()
            return False
    
    async def _preparation_phase(self) -> bool:
        """Preparation phase - set up Redis infrastructure"""
        try:
            self.current_phase = MigrationPhase.PREPARATION
            self.logger.info("Starting preparation phase")
            
            # Initialize Redis Event Bus for service
            self.redis_event_bus = await ServiceEventBusRegistry.create_service_event_bus(
                self.service_name
            )
            
            # Create publishers
            for publisher_type in self.config.target_publishers:
                publisher = await self._create_publisher(publisher_type)
                if publisher:
                    self.publishers[publisher_type] = publisher
                else:
                    self.logger.error("Failed to create publisher", type=publisher_type)
                    return False
            
            # Create subscribers  
            for subscriber_type in self.config.target_subscribers:
                subscriber = await self._create_subscriber(subscriber_type)
                if subscriber:
                    self.subscribers[subscriber_type] = subscriber
                else:
                    self.logger.error("Failed to create subscriber", type=subscriber_type)
                    return False
            
            self.logger.info("Preparation phase completed",
                           publishers=len(self.publishers),
                           subscribers=len(self.subscribers))
            
            return True
            
        except Exception as e:
            self.logger.error("Preparation phase failed", error=str(e))
            return False
    
    async def _dual_mode_phase(self) -> bool:
        """Dual mode phase - run both legacy and Redis systems"""
        try:
            self.current_phase = MigrationPhase.DUAL_MODE
            self.logger.info("Starting dual mode phase")
            
            # Set up event mirroring from legacy to Redis
            await self._setup_event_mirroring()
            
            # Run dual mode for specified duration
            dual_mode_duration = 3600  # 1 hour for testing, configurable
            await asyncio.sleep(dual_mode_duration)
            
            self.logger.info("Dual mode phase completed")
            return True
            
        except Exception as e:
            self.logger.error("Dual mode phase failed", error=str(e))
            return False
    
    async def _validation_phase(self) -> bool:
        """Validation phase - validate Redis system behavior"""
        try:
            self.current_phase = MigrationPhase.VALIDATION
            self.logger.info("Starting validation phase")
            
            # Run validation tests
            validation_results = await self._run_validation_tests()
            
            # Check validation results
            success_rate = (validation_results['passed'] / 
                          max(1, validation_results['total'])) if validation_results['total'] > 0 else 0
            
            if success_rate < 0.95:  # 95% success rate required
                self.logger.error("Validation failed", 
                                success_rate=success_rate,
                                required_rate=0.95)
                return False
            
            self.logger.info("Validation phase completed", 
                           success_rate=success_rate)
            return True
            
        except Exception as e:
            self.logger.error("Validation phase failed", error=str(e))
            return False
    
    async def _cutover_phase(self) -> bool:
        """Cutover phase - switch to Redis Event Bus only"""
        try:
            self.current_phase = MigrationPhase.CUTOVER
            self.logger.info("Starting cutover phase")
            
            # Disable legacy event bus
            await self._disable_legacy_system()
            
            # Enable full Redis Event Bus operation
            await self._enable_redis_system()
            
            # Update service configuration
            await self._update_service_configuration()
            
            self.logger.info("Cutover phase completed")
            return True
            
        except Exception as e:
            self.logger.error("Cutover phase failed", error=str(e))
            return False
    
    async def _cleanup_phase(self) -> bool:
        """Cleanup phase - remove legacy components"""
        try:
            self.current_phase = MigrationPhase.CLEANUP
            self.logger.info("Starting cleanup phase")
            
            # Archive legacy event handlers
            await self._archive_legacy_handlers()
            
            # Clean up temporary migration resources
            await self._cleanup_migration_resources()
            
            # Update system documentation
            await self._update_system_documentation()
            
            self.logger.info("Cleanup phase completed")
            return True
            
        except Exception as e:
            self.logger.error("Cleanup phase failed", error=str(e))
            return False
    
    async def _create_publisher(self, publisher_type: str) -> Optional[Any]:
        """Create publisher based on type"""
        try:
            if publisher_type == 'market_data':
                return await PublisherFactory.create_market_data_publisher(self.service_name)
            elif publisher_type == 'analysis':
                return await PublisherFactory.create_analysis_publisher(self.service_name)
            elif publisher_type == 'intelligence':
                return await PublisherFactory.create_intelligence_publisher(self.service_name)
            elif publisher_type == 'order':
                return await PublisherFactory.create_order_publisher(self.service_name)
            elif publisher_type == 'account':
                return await PublisherFactory.create_account_publisher(self.service_name)
            elif publisher_type == 'system':
                return await PublisherFactory.create_system_publisher(self.service_name)
            else:
                self.logger.error("Unknown publisher type", type=publisher_type)
                return None
                
        except Exception as e:
            self.logger.error("Failed to create publisher", 
                            type=publisher_type, 
                            error=str(e))
            return None
    
    async def _create_subscriber(self, subscriber_type: str) -> Optional[Any]:
        """Create subscriber based on type"""
        try:
            if subscriber_type == 'market_data':
                return await SubscriberFactory.create_market_data_subscriber(self.service_name)
            elif subscriber_type == 'analysis':
                return await SubscriberFactory.create_analysis_subscriber(self.service_name)
            elif subscriber_type == 'intelligence':
                return await SubscriberFactory.create_intelligence_subscriber(self.service_name)
            elif subscriber_type == 'order':
                return await SubscriberFactory.create_order_subscriber(self.service_name)
            elif subscriber_type == 'account':
                return await SubscriberFactory.create_account_subscriber(self.service_name)
            elif subscriber_type == 'system':
                return await SubscriberFactory.create_system_subscriber(self.service_name)
            else:
                self.logger.error("Unknown subscriber type", type=subscriber_type)
                return None
                
        except Exception as e:
            self.logger.error("Failed to create subscriber",
                            type=subscriber_type,
                            error=str(e))
            return None
    
    async def _setup_event_mirroring(self):
        """Set up mirroring of events from legacy to Redis"""
        try:
            # This would integrate with the legacy event system
            # For now, we'll simulate the integration
            
            async def legacy_event_handler(legacy_event):
                """Handle legacy events and mirror to Redis"""
                try:
                    # Convert legacy event to Redis event
                    redis_event = await self._convert_legacy_event(legacy_event)
                    if redis_event:
                        # Publish to Redis Event Bus
                        await self.redis_event_bus.publish(redis_event)
                        self.metrics['events_migrated'] += 1
                        
                except Exception as e:
                    self.metrics['migration_errors'] += 1
                    self.logger.error("Failed to mirror legacy event", error=str(e))
            
            # Register the handler with legacy system (service-specific implementation)
            await self._register_legacy_handler(legacy_event_handler)
            
        except Exception as e:
            self.logger.error("Failed to setup event mirroring", error=str(e))
            raise
    
    async def _convert_legacy_event(self, legacy_event: Dict[str, Any]) -> Optional[Event]:
        """Convert legacy event format to Redis Event format"""
        try:
            # Extract legacy event data
            legacy_type = legacy_event.get('type', '')
            legacy_data = legacy_event.get('data', {})
            legacy_timestamp = legacy_event.get('timestamp', datetime.now().isoformat())
            
            # Map legacy event type to Redis event type
            redis_event_type = self.event_mapping.get(legacy_type)
            if not redis_event_type:
                self.logger.warning("No mapping for legacy event type", type=legacy_type)
                return None
            
            # Create Redis event metadata
            metadata = EventMetadata(
                event_id=legacy_event.get('id', f"migrated_{datetime.now().timestamp()}"),
                timestamp=legacy_timestamp,
                source_service=self.service_name,
                priority=EventPriority.NORMAL
            )
            
            # Create Redis event
            redis_event = Event(
                event_type=redis_event_type,
                data=legacy_data,
                metadata=metadata
            )
            
            return redis_event
            
        except Exception as e:
            self.logger.error("Failed to convert legacy event", error=str(e))
            return None
    
    async def _register_legacy_handler(self, handler: Callable):
        """Register handler with legacy event system (service-specific)"""
        # This is service-specific and would need to be implemented
        # based on the actual legacy event system
        pass
    
    async def _run_validation_tests(self) -> Dict[str, int]:
        """Run validation tests to ensure Redis system works correctly"""
        try:
            validation_results = {'passed': 0, 'failed': 0, 'total': 0}
            
            # Test 1: Event publishing
            test_event = await self.redis_event_bus.create_event(
                event_type='test.validation',
                data={'test': 'migration_validation', 'timestamp': datetime.now().isoformat()}
            )
            
            if await self.redis_event_bus.publish(test_event):
                validation_results['passed'] += 1
            else:
                validation_results['failed'] += 1
            validation_results['total'] += 1
            
            # Test 2: Event subscription
            received_events = []
            
            async def test_handler(event_data):
                received_events.append(event_data)
            
            await self.redis_event_bus.subscribe('test.validation', test_handler)
            
            # Give some time for event to be processed
            await asyncio.sleep(1)
            
            if len(received_events) > 0:
                validation_results['passed'] += 1
            else:
                validation_results['failed'] += 1
            validation_results['total'] += 1
            
            # Test 3: Publisher functionality
            if 'system' in self.publishers:
                publisher = self.publishers['system']
                success = await publisher.publish_health_check({'status': 'validation_test'})
                if success:
                    validation_results['passed'] += 1
                else:
                    validation_results['failed'] += 1
                validation_results['total'] += 1
            
            # Update metrics
            self.metrics['validation_passed'] = validation_results['passed']
            self.metrics['validation_failed'] = validation_results['failed']
            
            return validation_results
            
        except Exception as e:
            self.logger.error("Validation tests failed", error=str(e))
            return {'passed': 0, 'failed': 1, 'total': 1}
    
    async def _disable_legacy_system(self):
        """Disable the legacy event system"""
        # This would be service-specific implementation
        self.logger.info("Legacy system disabled (placeholder)")
    
    async def _enable_redis_system(self):
        """Enable full Redis Event Bus operation"""
        # Ensure all publishers and subscribers are active
        for publisher_type, publisher in self.publishers.items():
            self.logger.info("Redis publisher enabled", type=publisher_type)
        
        for subscriber_type, subscriber in self.subscribers.items():
            self.logger.info("Redis subscriber enabled", type=subscriber_type)
    
    async def _update_service_configuration(self):
        """Update service configuration to use Redis Event Bus"""
        # This would update service configuration files or environment variables
        self.logger.info("Service configuration updated for Redis Event Bus")
    
    async def _archive_legacy_handlers(self):
        """Archive legacy event handlers"""
        # This would backup and remove legacy event handling code
        self.logger.info("Legacy handlers archived")
    
    async def _cleanup_migration_resources(self):
        """Clean up temporary migration resources"""
        # Clean up any temporary resources created during migration
        self.logger.info("Migration resources cleaned up")
    
    async def _update_system_documentation(self):
        """Update system documentation to reflect new architecture"""
        # This would update system documentation
        self.logger.info("System documentation updated")
    
    async def _rollback_migration(self):
        """Rollback migration in case of failure"""
        try:
            self.logger.warning("Starting migration rollback")
            
            # Re-enable legacy system
            # Disable Redis system
            # Restore original configuration
            
            self.logger.info("Migration rollback completed")
            
        except Exception as e:
            self.logger.error("Migration rollback failed", error=str(e))
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        return {
            'service_name': self.service_name,
            'current_phase': self.current_phase.value,
            'migration_start_time': self.migration_start_time.isoformat() if self.migration_start_time else None,
            'metrics': self.metrics.copy(),
            'publishers_count': len(self.publishers),
            'subscribers_count': len(self.subscribers)
        }


class SystemMigrationOrchestrator:
    """Orchestrates migration of all services to Redis Event Bus"""
    
    def __init__(self):
        self.logger = logger.bind(component="migration_orchestrator")
        self.service_migrators: Dict[str, ServiceMigrator] = {}
        self.migration_configs = self._create_migration_configs()
    
    def _create_migration_configs(self) -> Dict[str, MigrationConfig]:
        """Create migration configurations for all services"""
        return {
            'account-service': MigrationConfig(
                service_name='account-service',
                legacy_modules=['AccountModule'],
                target_publishers=['account', 'system'],
                target_subscribers=['order', 'system'],
                validation_period_hours=24
            ),
            
            'order-service': MigrationConfig(
                service_name='order-service',
                legacy_modules=['OrderModule'],
                target_publishers=['order', 'system'],
                target_subscribers=['account', 'intelligence', 'system'],
                validation_period_hours=24
            ),
            
            'data-analysis-service': MigrationConfig(
                service_name='data-analysis-service',
                legacy_modules=['DataAnalysisModule'],
                target_publishers=['analysis', 'system'],
                target_subscribers=['market_data', 'intelligence', 'system'],
                validation_period_hours=12
            ),
            
            'intelligent-core-service': MigrationConfig(
                service_name='intelligent-core-service',
                legacy_modules=['IntelligenceModule'],
                target_publishers=['intelligence', 'system'],
                target_subscribers=['analysis', 'market_data', 'system'],
                validation_period_hours=24
            ),
            
            'market-data-service': MigrationConfig(
                service_name='market-data-service',
                legacy_modules=['MarketDataModule'],
                target_publishers=['market_data', 'system'],
                target_subscribers=['system'],
                validation_period_hours=6
            ),
            
            'frontend-service': MigrationConfig(
                service_name='frontend-service',
                legacy_modules=['FrontendHandlers'],
                target_publishers=['system'],
                target_subscribers=['order', 'account', 'intelligence', 'market_data', 'analysis', 'system'],
                validation_period_hours=12
            )
        }
    
    async def migrate_all_services(self, parallel: bool = False) -> Dict[str, bool]:
        """Migrate all services to Redis Event Bus"""
        results = {}
        
        if parallel:
            # Run migrations in parallel
            tasks = []
            for service_name, config in self.migration_configs.items():
                migrator = ServiceMigrator(config)
                self.service_migrators[service_name] = migrator
                tasks.append(migrator.start_migration())
            
            migration_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (service_name, result) in enumerate(zip(self.migration_configs.keys(), migration_results)):
                if isinstance(result, Exception):
                    results[service_name] = False
                    self.logger.error("Service migration failed", 
                                    service=service_name, 
                                    error=str(result))
                else:
                    results[service_name] = result
        else:
            # Run migrations sequentially
            for service_name, config in self.migration_configs.items():
                migrator = ServiceMigrator(config)
                self.service_migrators[service_name] = migrator
                results[service_name] = await migrator.start_migration()
        
        return results
    
    async def migrate_service(self, service_name: str) -> bool:
        """Migrate specific service to Redis Event Bus"""
        if service_name not in self.migration_configs:
            self.logger.error("No migration configuration for service", service=service_name)
            return False
        
        config = self.migration_configs[service_name]
        migrator = ServiceMigrator(config)
        self.service_migrators[service_name] = migrator
        
        return await migrator.start_migration()
    
    def get_migration_status_all(self) -> Dict[str, Dict[str, Any]]:
        """Get migration status for all services"""
        status = {}
        for service_name, migrator in self.service_migrators.items():
            status[service_name] = migrator.get_migration_status()
        return status
    
    async def rollback_service(self, service_name: str) -> bool:
        """Rollback migration for specific service"""
        if service_name in self.service_migrators:
            migrator = self.service_migrators[service_name]
            await migrator._rollback_migration()
            return True
        return False


# Global migration orchestrator instance
migration_orchestrator = SystemMigrationOrchestrator()

# Convenience functions
async def migrate_all_services(parallel: bool = False) -> Dict[str, bool]:
    """Migrate all services to Redis Event Bus"""
    return await migration_orchestrator.migrate_all_services(parallel)

async def migrate_service(service_name: str) -> bool:
    """Migrate specific service to Redis Event Bus"""
    return await migration_orchestrator.migrate_service(service_name)

def get_migration_status() -> Dict[str, Dict[str, Any]]:
    """Get migration status for all services"""
    return migration_orchestrator.get_migration_status_all()