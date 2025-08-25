"""
Event Subscription Use Case - Clean Architecture Application Layer
Manages event subscriptions and handler registrations

Code-Qualität: HÖCHSTE PRIORITÄT
Version: 7.0.0
"""

import logging
import uuid
from typing import Dict, Any, Callable, Optional, List

from application.interfaces.event_subscriber import IEventSubscriber
from application.interfaces.event_repository import IEventRepository
from domain.entities.subscription import Subscription
from domain.services.event_routing_service import EventRoutingService


class EventSubscriptionUseCase:
    """
    Use Case for managing event subscriptions in the Event Bus system
    Coordinates subscription lifecycle and event routing
    """
    
    def __init__(
        self,
        event_subscriber: IEventSubscriber,
        event_repository: IEventRepository,
        routing_service: EventRoutingService
    ):
        """
        Initialize EventSubscriptionUseCase with dependencies
        
        Args:
            event_subscriber: Infrastructure layer event subscriber
            event_repository: Infrastructure layer event repository
            routing_service: Domain layer routing service
        """
        self.event_subscriber = event_subscriber
        self.event_repository = event_repository
        self.routing_service = routing_service
        self.logger = logging.getLogger(__name__)
        self.subscriptions: Dict[str, Subscription] = {}
    
    async def subscribe(
        self,
        event_type: str,
        service_name: str,
        handler_endpoint: str,
        filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new event subscription
        
        Args:
            event_type: Type of event to subscribe to
            service_name: Name of subscribing service
            handler_endpoint: Endpoint URL for event delivery
            filters: Optional event filters
            metadata: Optional subscription metadata
            
        Returns:
            Dict containing subscription details
        """
        try:
            subscription_id = str(uuid.uuid4())
            
            # Create domain subscription entity
            subscription = Subscription(
                subscription_id=subscription_id,
                event_type=event_type,
                service_name=service_name,
                handler_endpoint=handler_endpoint,
                filters=filters or {},
                metadata=metadata or {},
                is_active=True
            )
            
            # Register with routing service
            await self.routing_service.register_subscription(subscription)
            
            # Subscribe through infrastructure
            result = await self.event_subscriber.subscribe(
                event_type=event_type,
                handler=self._create_handler_wrapper(subscription)
            )
            
            # Store subscription
            self.subscriptions[subscription_id] = subscription
            
            # Persist to repository
            await self.event_repository.save_subscription(subscription)
            
            self.logger.info(
                f"Subscription created: {service_name} -> {event_type} ({subscription_id})"
            )
            
            return {
                "success": True,
                "subscription_id": subscription_id,
                "event_type": event_type,
                "service_name": service_name,
                "status": "active"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create subscription: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def unsubscribe(self, subscription_id: str) -> Dict[str, Any]:
        """
        Remove an event subscription
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            Dict containing unsubscribe result
        """
        try:
            if subscription_id not in self.subscriptions:
                return {
                    "success": False,
                    "error": "Subscription not found"
                }
            
            subscription = self.subscriptions[subscription_id]
            
            # Unregister from routing service
            await self.routing_service.unregister_subscription(subscription_id)
            
            # Unsubscribe through infrastructure
            await self.event_subscriber.unsubscribe(subscription_id)
            
            # Mark as inactive in repository
            subscription.is_active = False
            await self.event_repository.update_subscription(subscription)
            
            # Remove from local cache
            del self.subscriptions[subscription_id]
            
            self.logger.info(f"Subscription removed: {subscription_id}")
            
            return {
                "success": True,
                "subscription_id": subscription_id,
                "status": "unsubscribed"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_subscriptions(
        self,
        event_type: Optional[str] = None,
        service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List active subscriptions with optional filters
        
        Args:
            event_type: Filter by event type
            service_name: Filter by service name
            
        Returns:
            Dict containing subscription list
        """
        try:
            # Get subscriptions from repository
            all_subscriptions = await self.event_repository.get_subscriptions(
                event_type=event_type,
                service_name=service_name,
                is_active=True
            )
            
            subscription_list = [
                {
                    "subscription_id": sub.subscription_id,
                    "event_type": sub.event_type,
                    "service_name": sub.service_name,
                    "handler_endpoint": sub.handler_endpoint,
                    "is_active": sub.is_active,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None
                }
                for sub in all_subscriptions
            ]
            
            return {
                "success": True,
                "count": len(subscription_list),
                "subscriptions": subscription_list
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list subscriptions: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_handler_wrapper(self, subscription: Subscription) -> Callable:
        """
        Create a handler wrapper for subscription processing
        
        Args:
            subscription: Subscription entity
            
        Returns:
            Wrapped handler function
        """
        async def handler_wrapper(event: Dict[str, Any]):
            try:
                # Apply filters if configured
                if subscription.filters:
                    if not self._apply_filters(event, subscription.filters):
                        return
                
                # Route event through domain service
                await self.routing_service.route_event(
                    event=event,
                    subscription=subscription
                )
                
            except Exception as e:
                self.logger.error(
                    f"Error processing event for subscription {subscription.subscription_id}: {str(e)}"
                )
        
        return handler_wrapper
    
    def _apply_filters(self, event: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Apply subscription filters to event
        
        Args:
            event: Event data
            filters: Filter criteria
            
        Returns:
            True if event passes filters, False otherwise
        """
        for key, value in filters.items():
            event_value = event.get("event_data", {}).get(key)
            if event_value != value:
                return False
        return True