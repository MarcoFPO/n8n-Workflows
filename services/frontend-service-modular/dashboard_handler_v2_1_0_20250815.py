"""
Dashboard Handler - Single Function Module
Verantwortlich ausschließlich für Dashboard Data Management Logic
"""

from typing import Dict, Any, List, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, timedelta, BaseModel, structlog
)
from modules.single_function_module_base_v1_2_0_20250809 import SingleFunctionModule
from shared.event_bus import Event, EventType


class DashboardRequest(BaseModel):
    request_type: str  # 'get_data', 'update_portfolio', 'refresh_data', 'get_widgets'
    portfolio_data: Optional[Dict[str, Any]] = None
    widget_config: Optional[Dict[str, Any]] = None
    refresh_interval: Optional[int] = None


class DashboardWidgetData(BaseModel):
    widget_id: str
    widget_type: str  # 'balance', 'portfolio', 'recent_trades', 'news', 'charts', 'alerts'
    widget_data: Dict[str, Any]
    last_updated: datetime
    refresh_rate: int  # seconds
    is_active: bool = True


class DashboardDataResult(BaseModel):
    dashboard_successful: bool
    dashboard_data: Dict[str, Any]
    active_widgets: List[str]
    widget_details: Dict[str, DashboardWidgetData]
    data_freshness: Dict[str, str]  # widget_id -> freshness status
    last_refresh: datetime
    next_auto_refresh: Optional[datetime] = None
    update_warnings: List[str]


class DashboardHandler(SingleFunctionModule):
    """
    Single Function Module: Dashboard Data Management
    Verantwortlichkeit: Ausschließlich Dashboard-Data-Management-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("dashboard_handler", event_bus)
        
        # Dashboard Core Data
        self.dashboard_data = {
            "portfolio_value": 45750.32,
            "daily_change": 1250.75,
            "daily_change_percent": 2.8,
            "weekly_change": 2890.50,
            "monthly_change": 8750.20,
            "active_orders": 7,
            "pending_orders": 3,
            "completed_orders_today": 12,
            "total_balance": 48890.50,
            "available_balance": 42150.75,
            "locked_balance": 6739.75,
            "positions_count": 15,
            "profitable_positions": 11,
            "losing_positions": 4,
            "last_update": datetime.now(),
            "data_source": "bitpanda_simulation",
            "account_status": "verified",
            "trading_status": "active"
        }
        
        # Dashboard Widgets Configuration
        self.widget_registry = {
            'balance': DashboardWidgetData(
                widget_id='balance',
                widget_type='balance',
                widget_data={
                    'total_balance': 48890.50,
                    'available': 42150.75,
                    'locked': 6739.75,
                    'currencies': ['EUR', 'USD', 'BTC', 'ETH']
                },
                last_updated=datetime.now(),
                refresh_rate=30,  # 30 seconds
                is_active=True
            ),
            'portfolio': DashboardWidgetData(
                widget_id='portfolio',
                widget_type='portfolio',
                widget_data={
                    'total_value': 45750.32,
                    'daily_change': 1250.75,
                    'positions': 15,
                    'top_performers': ['BTC', 'ETH', 'AAPL'],
                    'worst_performers': ['TSLA']
                },
                last_updated=datetime.now(),
                refresh_rate=60,  # 1 minute
                is_active=True
            ),
            'recent_trades': DashboardWidgetData(
                widget_id='recent_trades',
                widget_type='recent_trades',
                widget_data={
                    'trades_today': 12,
                    'last_trade_time': datetime.now() - timedelta(minutes=15),
                    'last_trade_symbol': 'BTC/EUR',
                    'last_trade_amount': 0.05,
                    'recent_trades': []
                },
                last_updated=datetime.now(),
                refresh_rate=15,  # 15 seconds
                is_active=True
            ),
            'news': DashboardWidgetData(
                widget_id='news',
                widget_type='news',
                widget_data={
                    'latest_headlines': [
                        'Bitcoin reaches new monthly high',
                        'European markets show strong performance',
                        'ECB maintains interest rates'
                    ],
                    'market_sentiment': 'positive',
                    'news_count_today': 47
                },
                last_updated=datetime.now(),
                refresh_rate=300,  # 5 minutes
                is_active=True
            ),
            'charts': DashboardWidgetData(
                widget_id='charts',
                widget_type='charts',
                widget_data={
                    'active_chart': 'portfolio_performance',
                    'timeframe': '1D',
                    'chart_type': 'line',
                    'data_points': 24
                },
                last_updated=datetime.now(),
                refresh_rate=120,  # 2 minutes
                is_active=False  # Optional widget
            ),
            'alerts': DashboardWidgetData(
                widget_id='alerts',
                widget_type='alerts',
                widget_data={
                    'active_alerts': 3,
                    'triggered_alerts_today': 1,
                    'price_alerts': 2,
                    'balance_alerts': 1,
                    'latest_alert': 'BTC price above €45,000'
                },
                last_updated=datetime.now(),
                refresh_rate=60,  # 1 minute
                is_active=True
            )
        }
        
        # Dashboard Processing History
        self.dashboard_history = []
        self.dashboard_counter = 0
        
        # Dashboard Configuration
        self.dashboard_config = {
            'auto_refresh_enabled': True,
            'default_refresh_interval': 60,  # seconds
            'max_widget_count': 8,
            'enable_real_time_updates': True,
            'cache_dashboard_data': True,
            'cache_expiry_minutes': 5,
            'enable_background_refresh': True,
            'dashboard_theme': 'modern_light',
            'widget_animation': True,
            'notification_badge_enabled': True
        }
        
        # Dashboard Performance Metrics
        self.performance_metrics = {
            'average_load_time_ms': 0,
            'cache_hit_rate': 0.95,
            'widget_error_rate': 0.02,
            'real_time_update_latency_ms': 150,
            'data_freshness_score': 0.88
        }
        
        # Widget Update Scheduler
        self.widget_update_schedule = {}
        self.last_auto_refresh = datetime.now()
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Dashboard Data Management
        
        Args:
            input_data: {
                'request_type': required string ('get_data', 'update_portfolio', 'refresh_data', 'get_widgets'),
                'portfolio_data': optional dict for portfolio updates,
                'widget_config': optional dict for widget configuration,
                'refresh_interval': optional int for refresh rate adjustment,
                'force_refresh': optional bool (default: false),
                'include_inactive_widgets': optional bool (default: false),
                'widget_filter': optional list of widget_ids to include
            }
            
        Returns:
            Dict mit Dashboard-Data-Result
        """
        start_time = datetime.now()
        
        try:
            # Dashboard Request erstellen
            dashboard_request = DashboardRequest(
                request_type=input_data.get('request_type'),
                portfolio_data=input_data.get('portfolio_data'),
                widget_config=input_data.get('widget_config'),
                refresh_interval=input_data.get('refresh_interval')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid dashboard request: {str(e)}'
            }
        
        force_refresh = input_data.get('force_refresh', False)
        include_inactive = input_data.get('include_inactive_widgets', False)
        widget_filter = input_data.get('widget_filter')
        
        # Dashboard Processing
        dashboard_result = await self._process_dashboard_request(
            dashboard_request, force_refresh, include_inactive, widget_filter
        )
        
        # Statistics Update
        self.dashboard_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Dashboard History
        self.dashboard_history.append({
            'timestamp': datetime.now(),
            'request_type': dashboard_request.request_type,
            'dashboard_successful': dashboard_result.dashboard_successful,
            'active_widgets_count': len(dashboard_result.active_widgets),
            'warnings_count': len(dashboard_result.update_warnings),
            'processing_time_ms': processing_time_ms,
            'dashboard_id': self.dashboard_counter
        })
        
        # Limit History
        if len(self.dashboard_history) > 200:
            self.dashboard_history.pop(0)
        
        # Event Publishing für Dashboard Updates
        await self._publish_dashboard_event(dashboard_result, dashboard_request)
        
        # Event-Bus Integration: Subscribe to relevant events
        await self._setup_event_subscriptions()
        
        self.logger.info(f"Dashboard request processed",
                       request_type=dashboard_request.request_type,
                       dashboard_successful=dashboard_result.dashboard_successful,
                       active_widgets=len(dashboard_result.active_widgets),
                       warnings_count=len(dashboard_result.update_warnings),
                       processing_time_ms=round(processing_time_ms, 2),
                       dashboard_id=self.dashboard_counter)
        
        return {
            'success': True,
            'dashboard_successful': dashboard_result.dashboard_successful,
            'dashboard_data': dashboard_result.dashboard_data,
            'active_widgets': dashboard_result.active_widgets,
            'widget_details': {k: {
                'widget_id': v.widget_id,
                'widget_type': v.widget_type,
                'widget_data': v.widget_data,
                'last_updated': v.last_updated.isoformat(),
                'refresh_rate': v.refresh_rate,
                'is_active': v.is_active
            } for k, v in dashboard_result.widget_details.items()},
            'data_freshness': dashboard_result.data_freshness,
            'last_refresh': dashboard_result.last_refresh.isoformat(),
            'next_auto_refresh': dashboard_result.next_auto_refresh.isoformat() if dashboard_result.next_auto_refresh else None,
            'update_warnings': dashboard_result.update_warnings
        }
    
    async def _process_dashboard_request(self, request: DashboardRequest,
                                       force_refresh: bool,
                                       include_inactive: bool,
                                       widget_filter: Optional[List[str]]) -> DashboardDataResult:
        """Verarbeitet Dashboard Request komplett"""
        
        update_warnings = []
        
        if request.request_type == 'get_data':
            # Standard Dashboard Data abrufen
            dashboard_data = await self._get_dashboard_data(force_refresh)
            
        elif request.request_type == 'update_portfolio':
            # Portfolio Data aktualisieren
            if request.portfolio_data:
                dashboard_data = await self._update_portfolio_data(request.portfolio_data)
                update_warnings.append('Portfolio data updated from external source')
            else:
                dashboard_data = await self._get_dashboard_data(force_refresh)
                update_warnings.append('No portfolio data provided for update')
                
        elif request.request_type == 'refresh_data':
            # Force Refresh aller Widgets
            dashboard_data = await self._refresh_all_widgets()
            
        elif request.request_type == 'get_widgets':
            # Widget-spezifische Daten abrufen
            dashboard_data = await self._get_widget_data(widget_filter, include_inactive)
            
        else:
            dashboard_data = await self._get_dashboard_data(force_refresh)
            update_warnings.append(f'Unknown request type: {request.request_type}, fallback to get_data')
        
        # Widget Details filtern
        widget_details = {}
        active_widgets = []
        
        for widget_id, widget in self.widget_registry.items():
            # Filter anwenden
            if widget_filter and widget_id not in widget_filter:
                continue
            
            # Inactive Widgets filtern
            if not include_inactive and not widget.is_active:
                continue
            
            widget_details[widget_id] = widget
            if widget.is_active:
                active_widgets.append(widget_id)
        
        # Data Freshness prüfen
        data_freshness = await self._assess_data_freshness(widget_details)
        
        # Next Auto Refresh berechnen
        next_refresh = await self._calculate_next_auto_refresh()
        
        return DashboardDataResult(
            dashboard_successful=True,
            dashboard_data=dashboard_data,
            active_widgets=active_widgets,
            widget_details=widget_details,
            data_freshness=data_freshness,
            last_refresh=datetime.now(),
            next_auto_refresh=next_refresh,
            update_warnings=update_warnings
        )
    
    async def _get_dashboard_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Holt aktuelle Dashboard Data"""
        
        # Cache Check
        if not force_refresh and self.dashboard_config['cache_dashboard_data']:
            cache_age_minutes = (datetime.now() - self.dashboard_data['last_update']).total_seconds() / 60
            if cache_age_minutes < self.dashboard_config['cache_expiry_minutes']:
                return self.dashboard_data.copy()
        
        # Data Refresh (Mock - in Produktion würde hier echte API-Calls stattfinden)
        if force_refresh or self._should_refresh_data():
            await self._refresh_dashboard_data()
        
        return self.dashboard_data.copy()
    
    async def _update_portfolio_data(self, portfolio_update: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualisiert Portfolio-spezifische Dashboard Data"""
        
        # Portfolio Values updaten
        if 'portfolio_value' in portfolio_update:
            old_value = self.dashboard_data['portfolio_value']
            new_value = float(portfolio_update['portfolio_value'])
            
            self.dashboard_data['portfolio_value'] = new_value
            self.dashboard_data['daily_change'] = new_value - old_value
            
            # Update entsprechende Widgets
            if 'portfolio' in self.widget_registry:
                self.widget_registry['portfolio'].widget_data.update({
                    'total_value': new_value,
                    'daily_change': new_value - old_value
                })
                self.widget_registry['portfolio'].last_updated = datetime.now()
        
        # Weitere Portfolio-Updates
        if 'positions_count' in portfolio_update:
            self.dashboard_data['positions_count'] = portfolio_update['positions_count']
        
        if 'active_orders' in portfolio_update:
            self.dashboard_data['active_orders'] = portfolio_update['active_orders']
        
        # Last Update Time
        self.dashboard_data['last_update'] = datetime.now()
        
        return self.dashboard_data.copy()
    
    async def _refresh_all_widgets(self) -> Dict[str, Any]:
        """Refresht alle aktiven Widgets"""
        
        current_time = datetime.now()
        
        for widget_id, widget in self.widget_registry.items():
            if widget.is_active:
                # Mock Widget Refresh
                await self._refresh_single_widget(widget_id)
                widget.last_updated = current_time
        
        # Dashboard Core Data auch refreshen
        await self._refresh_dashboard_data()
        
        return self.dashboard_data.copy()
    
    async def _get_widget_data(self, widget_filter: Optional[List[str]],
                             include_inactive: bool) -> Dict[str, Any]:
        """Holt Widget-spezifische Daten"""
        
        widget_data = {}
        
        for widget_id, widget in self.widget_registry.items():
            # Filter Check
            if widget_filter and widget_id not in widget_filter:
                continue
            
            # Active Check
            if not include_inactive and not widget.is_active:
                continue
            
            # Check if refresh needed
            if self._widget_needs_refresh(widget):
                await self._refresh_single_widget(widget_id)
            
            widget_data[widget_id] = widget.widget_data
        
        return widget_data
    
    async def _refresh_dashboard_data(self):
        """Refresht Core Dashboard Data"""
        
        # Mock Data Refresh - in Produktion würde hier API-Calls zu verschiedenen Services stattfinden
        import random
        
        # Portfolio Value mit realistischen Schwankungen
        base_value = 45750.32
        change_percent = random.uniform(-0.05, 0.05)  # ±5% Schwankung
        new_value = base_value * (1 + change_percent)
        
        self.dashboard_data.update({
            'portfolio_value': round(new_value, 2),
            'daily_change': round(new_value - base_value, 2),
            'daily_change_percent': round(change_percent * 100, 1),
            'active_orders': random.randint(5, 12),
            'completed_orders_today': random.randint(8, 20),
            'last_update': datetime.now()
        })
        
        # Update Performance Metrics
        self.performance_metrics['data_freshness_score'] = random.uniform(0.85, 0.95)
        self.last_auto_refresh = datetime.now()
    
    async def _refresh_single_widget(self, widget_id: str):
        """Refresht einzelnes Widget"""
        
        if widget_id not in self.widget_registry:
            return
        
        widget = self.widget_registry[widget_id]
        
        # Mock Widget-spezifische Refreshs
        import random
        
        if widget_id == 'balance':
            widget.widget_data.update({
                'total_balance': self.dashboard_data.get('total_balance', 48890.50) + random.uniform(-100, 100),
                'available': random.uniform(40000, 45000),
                'locked': random.uniform(5000, 8000)
            })
        
        elif widget_id == 'portfolio':
            widget.widget_data.update({
                'total_value': self.dashboard_data.get('portfolio_value', 45750.32),
                'daily_change': self.dashboard_data.get('daily_change', 1250.75),
                'positions': random.randint(12, 18)
            })
        
        elif widget_id == 'recent_trades':
            widget.widget_data.update({
                'trades_today': random.randint(5, 15),
                'last_trade_time': datetime.now() - timedelta(minutes=random.randint(1, 30))
            })
        
        elif widget_id == 'alerts':
            widget.widget_data.update({
                'active_alerts': random.randint(0, 5),
                'triggered_alerts_today': random.randint(0, 3)
            })
        
        widget.last_updated = datetime.now()
    
    def _widget_needs_refresh(self, widget: DashboardWidgetData) -> bool:
        """Prüft ob Widget einen Refresh benötigt"""
        
        if not widget.is_active:
            return False
        
        time_since_update = (datetime.now() - widget.last_updated).total_seconds()
        return time_since_update >= widget.refresh_rate
    
    def _should_refresh_data(self) -> bool:
        """Prüft ob Dashboard Data refresht werden sollte"""
        
        if not self.dashboard_config['auto_refresh_enabled']:
            return False
        
        time_since_refresh = (datetime.now() - self.last_auto_refresh).total_seconds()
        return time_since_refresh >= self.dashboard_config['default_refresh_interval']
    
    async def _assess_data_freshness(self, widgets: Dict[str, DashboardWidgetData]) -> Dict[str, str]:
        """Bewertet Data Freshness für alle Widgets"""
        
        freshness = {}
        current_time = datetime.now()
        
        for widget_id, widget in widgets.items():
            age_seconds = (current_time - widget.last_updated).total_seconds()
            
            if age_seconds <= widget.refresh_rate:
                freshness[widget_id] = 'fresh'
            elif age_seconds <= widget.refresh_rate * 2:
                freshness[widget_id] = 'acceptable'
            elif age_seconds <= widget.refresh_rate * 5:
                freshness[widget_id] = 'stale'
            else:
                freshness[widget_id] = 'outdated'
        
        return freshness
    
    async def _calculate_next_auto_refresh(self) -> Optional[datetime]:
        """Berechnet nächsten Auto-Refresh Zeitpunkt"""
        
        if not self.dashboard_config['auto_refresh_enabled']:
            return None
        
        # Finde das Widget mit der kürzesten Refresh Rate
        min_refresh_rate = min(
            [w.refresh_rate for w in self.widget_registry.values() if w.is_active],
            default=self.dashboard_config['default_refresh_interval']
        )
        
        return datetime.now() + timedelta(seconds=min_refresh_rate)
    
    async def _publish_dashboard_event(self, result: DashboardDataResult,
                                     request: DashboardRequest):
        """Published Dashboard Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Nur für relevante Events publishen
        if request.request_type in ['update_portfolio', 'refresh_data']:
            from event_bus import Event
            
            event = Event(
                event_type="dashboard_updated",
                stream_id=f"dashboard-{self.dashboard_counter}",
                data={
                    'request_type': request.request_type,
                    'dashboard_successful': result.dashboard_successful,
                    'active_widgets_count': len(result.active_widgets),
                    'portfolio_value': result.dashboard_data.get('portfolio_value'),
                    'data_freshness_score': self.performance_metrics['data_freshness_score'],
                    'update_timestamp': result.last_refresh.isoformat()
                },
                source="dashboard_handler"
            )
            
            await self.event_bus.publish(event)
    
    async def _setup_event_subscriptions(self):
        """
        Setup Event-Bus subscriptions for dashboard updates
        Event-Bus Compliance: Subscribe to relevant events instead of direct calls
        """
        if not self.event_bus or not self.event_bus.connected:
            return
        
        try:
            # Subscribe to portfolio updates
            await self.event_bus.subscribe(
                EventType.PORTFOLIO_STATE_CHANGED.value,
                self._handle_portfolio_event,
                f"dashboard_portfolio_{self.module_name}"
            )
            
            # Subscribe to trading updates
            await self.event_bus.subscribe(
                EventType.TRADING_STATE_CHANGED.value,
                self._handle_trading_event,
                f"dashboard_trading_{self.module_name}"
            )
            
            # Subscribe to system health updates
            await self.event_bus.subscribe(
                EventType.SYSTEM_HEALTH_REQUEST.value,
                self._handle_health_event,
                f"dashboard_health_{self.module_name}"
            )
            
            self.logger.info("Dashboard event subscriptions established")
            
        except Exception as e:
            self.logger.error(f"Failed to setup event subscriptions: {e}")
    
    async def _handle_portfolio_event(self, event: Event):
        """
        Handle portfolio state change events
        Event-Bus Compliance: React to portfolio changes via events
        """
        try:
            portfolio_data = event.data
            
            # Update dashboard data based on portfolio changes
            if 'portfolio_value' in portfolio_data:
                await self._update_portfolio_data(portfolio_data)
                
                self.logger.debug("Dashboard updated via portfolio event",
                                portfolio_value=portfolio_data.get('portfolio_value'))
            
        except Exception as e:
            self.logger.error(f"Failed to handle portfolio event: {e}")
    
    async def _handle_trading_event(self, event: Event):
        """
        Handle trading state change events
        Event-Bus Compliance: React to trading changes via events
        """
        try:
            trading_data = event.data
            
            # Update trading-related dashboard widgets
            if 'orders' in trading_data:
                orders_count = len(trading_data['orders'])
                self.dashboard_data['active_orders'] = orders_count
                
                # Update trading widget if exists
                if 'recent_trades' in self.widget_registry:
                    self.widget_registry['recent_trades'].widget_data.update({
                        'trades_today': orders_count,
                        'last_trade_time': datetime.now() - timedelta(minutes=5)
                    })
                    self.widget_registry['recent_trades'].last_updated = datetime.now()
                
                self.logger.debug("Dashboard updated via trading event",
                                active_orders=orders_count)
            
        except Exception as e:
            self.logger.error(f"Failed to handle trading event: {e}")
    
    async def _handle_health_event(self, event: Event):
        """
        Handle system health request events
        Event-Bus Compliance: Respond to health checks via events
        """
        try:
            request_data = event.data
            
            if request_data.get('request_type') == 'dashboard_health':
                # Respond with dashboard health status
                health_response = Event(
                    event_type=EventType.SYSTEM_HEALTH_RESPONSE.value,
                    stream_id=f"dashboard-health-{event.stream_id}",
                    data={
                        'module': 'dashboard_handler',
                        'status': 'healthy',
                        'widget_count': len(self.widget_registry),
                        'active_widgets': len([w for w in self.widget_registry.values() if w.is_active]),
                        'data_freshness_score': self.performance_metrics['data_freshness_score'],
                        'last_update': self.dashboard_data['last_update'].isoformat()
                    },
                    source=self.module_name,
                    correlation_id=event.correlation_id
                )
                
                await self.event_bus.publish(health_response)
                self.logger.debug("Dashboard health response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle health event: {e}")
    
    async def process_event(self, event: Event):
        """
        Process incoming events - Event-Bus Compliance
        """
        try:
            if event.event_type == EventType.DASHBOARD_REQUEST.value:
                # Process dashboard request via event
                result = await self.execute_function(event.data)
                
                # Send response via event-bus
                response_event = Event(
                    event_type=EventType.DASHBOARD_RESPONSE.value,
                    stream_id=event.stream_id,
                    data=result,
                    source=self.module_name,
                    correlation_id=event.correlation_id
                )
                
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(response_event)
            
            elif event.event_type == EventType.PORTFOLIO_STATE_CHANGED.value:
                await self._handle_portfolio_event(event)
            
            elif event.event_type == EventType.TRADING_STATE_CHANGED.value:
                await self._handle_trading_event(event)
            
            elif event.event_type == EventType.SYSTEM_HEALTH_REQUEST.value:
                await self._handle_health_event(event)
            
            else:
                self.logger.debug(f"Unhandled event type: {event.event_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_type}: {e}")
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Gibt Dashboard Summary zurück"""
        
        # Widget Status
        active_widgets = sum(1 for w in self.widget_registry.values() if w.is_active)
        total_widgets = len(self.widget_registry)
        
        # Performance Metrics
        avg_processing_time = (
            sum(h['processing_time_ms'] for h in self.dashboard_history) / 
            len(self.dashboard_history) if self.dashboard_history else 0
        )
        
        # Data Freshness
        outdated_widgets = sum(
            1 for w in self.widget_registry.values() 
            if w.is_active and (datetime.now() - w.last_updated).total_seconds() > w.refresh_rate * 3
        )
        
        return {
            'dashboard_status': 'active',
            'total_widgets': total_widgets,
            'active_widgets': active_widgets,
            'inactive_widgets': total_widgets - active_widgets,
            'outdated_widgets': outdated_widgets,
            'portfolio_value': self.dashboard_data.get('portfolio_value', 0),
            'last_update': self.dashboard_data['last_update'].isoformat(),
            'auto_refresh_enabled': self.dashboard_config['auto_refresh_enabled'],
            'average_processing_time_ms': round(avg_processing_time, 2),
            'data_freshness_score': self.performance_metrics['data_freshness_score'],
            'cache_hit_rate': self.performance_metrics['cache_hit_rate']
        }
    
    def configure_widget(self, widget_id: str, config: Dict[str, Any]):
        """Konfiguriert einzelnes Widget"""
        
        if widget_id not in self.widget_registry:
            self.logger.warning(f"Widget not found for configuration: {widget_id}")
            return
        
        widget = self.widget_registry[widget_id]
        
        if 'is_active' in config:
            widget.is_active = config['is_active']
        
        if 'refresh_rate' in config:
            widget.refresh_rate = max(5, config['refresh_rate'])  # Min 5 seconds
        
        if 'widget_data' in config:
            widget.widget_data.update(config['widget_data'])
        
        widget.last_updated = datetime.now()
        
        self.logger.info(f"Widget configured",
                       widget_id=widget_id,
                       is_active=widget.is_active,
                       refresh_rate=widget.refresh_rate)
    
    def reset_dashboard_data(self):
        """Reset Dashboard Data to defaults (Administrative Function)"""
        
        self.dashboard_data = {
            "portfolio_value": 45750.32,
            "daily_change": 1250.75,
            "daily_change_percent": 2.8,
            "active_orders": 7,
            "total_balance": 48890.50,
            "available_balance": 42150.75,
            "locked_balance": 6739.75,
            "positions_count": 15,
            "last_update": datetime.now(),
            "data_source": "bitpanda_simulation",
            "account_status": "verified",
            "trading_status": "active"
        }
        
        # Reset alle Widgets
        for widget in self.widget_registry.values():
            widget.last_updated = datetime.now()
        
        self.logger.warning("Dashboard data reset to defaults")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'dashboard_handler',
            'description': 'Complete dashboard data management with widget orchestration and real-time updates',
            'responsibility': 'Dashboard data management logic only',
            'input_parameters': {
                'request_type': 'Required request type (get_data, update_portfolio, refresh_data, get_widgets)',
                'portfolio_data': 'Optional portfolio data for updates',
                'widget_config': 'Optional widget configuration data',
                'refresh_interval': 'Optional refresh interval adjustment',
                'force_refresh': 'Whether to force refresh all data (default: false)',
                'include_inactive_widgets': 'Whether to include inactive widgets (default: false)',
                'widget_filter': 'Optional list of widget IDs to include'
            },
            'output_format': {
                'dashboard_successful': 'Whether dashboard operation was successful',
                'dashboard_data': 'Core dashboard data',
                'active_widgets': 'List of active widget IDs',
                'widget_details': 'Detailed widget information',
                'data_freshness': 'Data freshness status per widget',
                'last_refresh': 'Timestamp of last data refresh',
                'next_auto_refresh': 'Next scheduled auto refresh',
                'update_warnings': 'List of update warnings if any'
            },
            'supported_request_types': ['get_data', 'update_portfolio', 'refresh_data', 'get_widgets'],
            'available_widgets': list(self.widget_registry.keys()),
            'widget_configuration': self.widget_registry,
            'dashboard_configuration': self.dashboard_config,
            'performance_metrics': self.performance_metrics,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """Dashboard Handler Module Statistiken"""
        total_requests = len(self.dashboard_history)
        
        if total_requests == 0:
            return {
                'total_requests': 0,
                'total_widgets': len(self.widget_registry),
                'active_widgets': sum(1 for w in self.widget_registry.values() if w.is_active)
            }
        
        # Success Rate
        successful_requests = sum(1 for h in self.dashboard_history if h['dashboard_successful'])
        success_rate = round((successful_requests / total_requests) * 100, 1) if total_requests > 0 else 0
        
        # Request Type Distribution
        request_type_distribution = {}
        for request in self.dashboard_history:
            req_type = request['request_type']
            request_type_distribution[req_type] = request_type_distribution.get(req_type, 0) + 1
        
        # Widget Performance
        widget_error_count = sum(h['warnings_count'] for h in self.dashboard_history)
        widget_error_rate = round((widget_error_count / total_requests) * 100, 1)
        
        # Recent Activity
        recent_requests = [
            h for h in self.dashboard_history
            if (datetime.now() - h['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate_percent': success_rate,
            'recent_requests_last_hour': len(recent_requests),
            'request_type_distribution': dict(sorted(
                request_type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'widget_error_rate_percent': widget_error_rate,
            'total_widgets': len(self.widget_registry),
            'active_widgets': sum(1 for w in self.widget_registry.values() if w.is_active),
            'average_widget_count_per_request': round(
                sum(h['active_widgets_count'] for h in self.dashboard_history) / total_requests, 1
            ) if total_requests > 0 else 0,
            'dashboard_data_freshness_score': self.performance_metrics['data_freshness_score'],
            'cache_hit_rate': self.performance_metrics['cache_hit_rate'],
            'average_processing_time': self.average_execution_time
        }