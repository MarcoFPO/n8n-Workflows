from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Current Usage Calculation Module - Single Function Module
Verantwortlich ausschließlich für Current Usage Calculation Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class UsagePeriod(BaseModel):
    start_date: datetime
    end_date: datetime
    period_type: str  # 'daily', 'weekly', 'monthly', 'yearly'


class UsageMetric(BaseModel):
    metric_name: str
    current_value: float
    limit_value: float
    usage_percentage: float
    remaining_value: float
    status: str  # 'normal', 'warning', 'critical', 'exceeded'


class CurrentUsageResult(BaseModel):
    calculation_period: UsagePeriod
    usage_metrics: Dict[str, Dict[str, Any]]
    summary_statistics: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    usage_warnings: List[str]
    calculation_timestamp: datetime


class CurrentUsageCalculationModule(SingleFunctionModule):
    """
    Single Function Module: Current Usage Calculation
    Verantwortlichkeit: Ausschließlich Current-Usage-Calculation-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("current_usage_calculation", event_bus)
        
        # Account Limits für Usage Calculation
        self.account_limits = {
            'daily_withdrawal_limit': 50000.0,
            'weekly_trading_limit': 500000.0,
            'monthly_trading_limit': 1000000.0,
            'yearly_transaction_limit': 10000000.0,
            'max_open_orders': 100,
            'max_position_size': 100000.0
        }
        
        # Mock Transaction History für Usage Calculation
        self.transaction_history = self._generate_mock_transaction_history()
        
        # Usage Calculation Cache
        self.usage_cache = {}
        self.cache_timestamps = {}
        
        # Calculation History
        self.calculation_history = []
        self.calculation_counter = 0
        
        # Usage Thresholds für Warnings
        self.usage_thresholds = {
            'warning_threshold': 0.7,    # 70% usage = warning
            'critical_threshold': 0.9,   # 90% usage = critical
            'exceeded_threshold': 1.0    # 100%+ usage = exceeded
        }
        
        # Trend Analysis Configuration
        self.trend_config = {
            'trend_period_days': 30,
            'comparison_periods': ['daily', 'weekly', 'monthly'],
            'growth_rate_threshold': 0.1  # 10% growth = significant
        }
        

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _generate_mock_transaction_history(self) -> List[Dict[str, Any]]:
        """Generiert Mock Transaction History für Usage Calculation"""
        
        transactions = []
        base_date = datetime.now()
        
        # Generate transactions für die letzten 60 Tage
        for days_ago in range(60):
            transaction_date = base_date - timedelta(days=days_ago)
            
            # Verschiedene Transaction Types
            daily_transactions = [
                {
                    'transaction_id': f'TXN_{transaction_date.strftime("%Y%m%d")}_001',
                    'type': 'trade_buy',
                    'currency_code': 'EUR',
                    'amount': 1500.0,
                    'timestamp': transaction_date,
                    'category': 'trading'
                },
                {
                    'transaction_id': f'TXN_{transaction_date.strftime("%Y%m%d")}_002',
                    'type': 'withdrawal',
                    'currency_code': 'EUR',
                    'amount': 500.0,
                    'timestamp': transaction_date - timedelta(hours=2),
                    'category': 'withdrawal'
                },
                {
                    'transaction_id': f'TXN_{transaction_date.strftime("%Y%m%d")}_003',
                    'type': 'trade_sell',
                    'currency_code': 'BTC',
                    'amount': 0.05,
                    'timestamp': transaction_date - timedelta(hours=5),
                    'category': 'trading'
                }
            ]
            
            transactions.extend(daily_transactions)
        
        return transactions
    
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Current Usage Calculation
        
        Args:
            input_data: {
                'calculation_period': optional string ('daily', 'weekly', 'monthly', 'yearly'),
                'include_trend_analysis': optional bool (default: true),
                'refresh_cache': optional bool (default: false),
                'metric_filters': optional list of specific metrics to calculate,
                'custom_period': optional dict with 'start_date' and 'end_date'
            }
            
        Returns:
            Dict mit Current-Usage-Calculation-Result
        """
        calculation_period = input_data.get('calculation_period', 'monthly')
        include_trend_analysis = input_data.get('include_trend_analysis', True)
        refresh_cache = input_data.get('refresh_cache', False)
        metric_filters = input_data.get('metric_filters', [])
        custom_period = input_data.get('custom_period')
        
        # Usage Calculation durchführen
        usage_result = await self._calculate_current_usage(
            calculation_period, include_trend_analysis, refresh_cache, 
            metric_filters, custom_period
        )
        
        # Statistics Update
        self.calculation_counter += 1
        
        # Calculation History
        self.calculation_history.append({
            'timestamp': datetime.now(),
            'calculation_period': calculation_period,
            'metrics_calculated': len(usage_result.usage_metrics),
            'warnings_generated': len(usage_result.usage_warnings),
            'cache_used': not refresh_cache and self._has_valid_cache(calculation_period),
            'calculation_id': self.calculation_counter
        })
        
        # Limit History
        if len(self.calculation_history) > 100:
            self.calculation_history.pop(0)
        
        self.logger.info(f"Current usage calculated successfully",
                       calculation_period=calculation_period,
                       metrics_count=len(usage_result.usage_metrics),
                       warnings_count=len(usage_result.usage_warnings),
                       include_trend_analysis=include_trend_analysis,
                       calculation_id=self.calculation_counter)
        
        return {
            'success': True,
            'calculation_period': {
                'start_date': usage_result.calculation_period.start_date.isoformat(),
                'end_date': usage_result.calculation_period.end_date.isoformat(),
                'period_type': usage_result.calculation_period.period_type
            },
            'usage_metrics': usage_result.usage_metrics,
            'summary_statistics': usage_result.summary_statistics,
            'trend_analysis': usage_result.trend_analysis if include_trend_analysis else {},
            'usage_warnings': usage_result.usage_warnings,
            'calculation_timestamp': usage_result.calculation_timestamp.isoformat()
        }
    
    async def _calculate_current_usage(self, period_type: str, include_trend: bool,
                                     refresh_cache: bool, metric_filters: List[str],
                                     custom_period: Optional[Dict]) -> CurrentUsageResult:
        """Berechnet Current Usage für specified Period"""
        
        # Cache Check
        cache_key = f"{period_type}_{custom_period or 'default'}"
        if (not refresh_cache and 
            self._has_valid_cache(cache_key) and
            not metric_filters):  # Skip cache for filtered requests
            
            return self.usage_cache[cache_key]
        
        # Calculation Period bestimmen
        calculation_period = await self._determine_calculation_period(period_type, custom_period)
        
        # Usage Metrics berechnen
        usage_metrics = await self._calculate_usage_metrics(
            calculation_period, metric_filters
        )
        
        # Summary Statistics
        summary_stats = await self._calculate_summary_statistics(usage_metrics)
        
        # Trend Analysis
        trend_analysis = {}
        if include_trend:
            trend_analysis = await self._perform_trend_analysis(calculation_period, usage_metrics)
        
        # Usage Warnings generieren
        usage_warnings = await self._generate_usage_warnings(usage_metrics)
        
        # Usage Result erstellen
        usage_result = CurrentUsageResult(
            calculation_period=calculation_period,
            usage_metrics=usage_metrics,
            summary_statistics=summary_stats,
            trend_analysis=trend_analysis,
            usage_warnings=usage_warnings,
            calculation_timestamp=datetime.now()
        )
        
        # Cache Update
        self.usage_cache[cache_key] = usage_result
        self.cache_timestamps[cache_key] = datetime.now()
        
        return usage_result
    
    async def _determine_calculation_period(self, period_type: str, 
                                          custom_period: Optional[Dict]) -> UsagePeriod:
        """Bestimmt Calculation Period basierend auf Input"""
        
        if custom_period:
            start_date = datetime.fromisoformat(custom_period['start_date'].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(custom_period['end_date'].replace('Z', '+00:00'))
            return UsagePeriod(
                start_date=start_date,
                end_date=end_date,
                period_type='custom'
            )
        
        now = datetime.now()
        
        if period_type == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period_type == 'weekly':
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period_type == 'monthly':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period_type == 'yearly':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:
            # Default to monthly
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_type = 'monthly'
        
        return UsagePeriod(
            start_date=start_date,
            end_date=end_date,
            period_type=period_type
        )
    
    async def _calculate_usage_metrics(self, period: UsagePeriod, 
                                     filters: List[str]) -> Dict[str, Dict[str, Any]]:
        """Berechnet Usage Metrics für specified Period"""
        
        metrics = {}
        
        # Filter transactions for the period
        period_transactions = [
            txn for txn in self.transaction_history
            if period.start_date <= txn['timestamp'] <= period.end_date
        ]
        
        # Daily Withdrawal Usage
        if not filters or 'daily_withdrawals' in filters:
            daily_withdrawals = await self._calculate_daily_withdrawals(period_transactions)
            metrics['daily_withdrawals'] = self._create_usage_metric(
                'Daily Withdrawals',
                daily_withdrawals,
                self.account_limits['daily_withdrawal_limit']
            )
        
        # Trading Volume Usage
        if not filters or 'trading_volume' in filters:
            trading_volume = await self._calculate_trading_volume(period_transactions, period.period_type)
            limit_key = f"{period.period_type}_trading_limit"
            trading_limit = self.account_limits.get(limit_key, self.account_limits['monthly_trading_limit'])
            
            metrics['trading_volume'] = self._create_usage_metric(
                f'{period.period_type.title()} Trading Volume',
                trading_volume,
                trading_limit
            )
        
        # Transaction Count Usage
        if not filters or 'transaction_count' in filters:
            transaction_count = len(period_transactions)
            # Mock limit basierend auf period type
            count_limits = {
                'daily': 50,
                'weekly': 300,
                'monthly': 1000,
                'yearly': 10000
            }
            count_limit = count_limits.get(period.period_type, 1000)
            
            metrics['transaction_count'] = self._create_usage_metric(
                f'{period.period_type.title()} Transaction Count',
                transaction_count,
                count_limit
            )
        
        # Open Orders Usage (current state, nicht period-basiert)
        if not filters or 'open_orders' in filters:
            open_orders_count = 5  # Mock current open orders
            metrics['open_orders'] = self._create_usage_metric(
                'Open Orders',
                open_orders_count,
                self.account_limits['max_open_orders']
            )
        
        # Position Size Usage
        if not filters or 'position_size' in filters:
            largest_position = 15000.0  # Mock largest position in EUR
            metrics['position_size'] = self._create_usage_metric(
                'Largest Position Size',
                largest_position,
                self.account_limits['max_position_size']
            )
        
        # Fee Usage (estimated)
        if not filters or 'fees_paid' in filters:
            fees_paid = await self._calculate_fees_paid(period_transactions)
            estimated_fee_limit = trading_volume * 0.01 if 'trading_volume' in metrics else 1000.0  # 1% of trading volume
            
            metrics['fees_paid'] = self._create_usage_metric(
                f'{period.period_type.title()} Fees Paid',
                fees_paid,
                estimated_fee_limit
            )
        
        return metrics
    
    def _create_usage_metric(self, metric_name: str, current_value: float, 
                           limit_value: float) -> Dict[str, Any]:
        """Erstellt Usage Metric Dictionary"""
        
        usage_percentage = (current_value / limit_value * 100) if limit_value > 0 else 0
        remaining_value = max(0, limit_value - current_value)
        
        # Status bestimmen
        if usage_percentage >= (self.usage_thresholds['exceeded_threshold'] * 100):
            status = 'exceeded'
        elif usage_percentage >= (self.usage_thresholds['critical_threshold'] * 100):
            status = 'critical'
        elif usage_percentage >= (self.usage_thresholds['warning_threshold'] * 100):
            status = 'warning'
        else:
            status = 'normal'
        
        return {
            'metric_name': metric_name,
            'current_value': round(current_value, 2),
            'limit_value': round(limit_value, 2),
            'usage_percentage': round(usage_percentage, 1),
            'remaining_value': round(remaining_value, 2),
            'status': status
        }
    
    async def _calculate_daily_withdrawals(self, transactions: List[Dict]) -> float:
        """Berechnet Daily Withdrawals für heute"""
        
        today = datetime.now().date()
        daily_withdrawals = 0.0
        
        for txn in transactions:
            if (txn['timestamp'].date() == today and 
                txn['type'] == 'withdrawal' and 
                txn['currency_code'] == 'EUR'):
                daily_withdrawals += txn['amount']
        
        return daily_withdrawals
    
    async def _calculate_trading_volume(self, transactions: List[Dict], period_type: str) -> float:
        """Berechnet Trading Volume für specified Period"""
        
        trading_volume = 0.0
        
        for txn in transactions:
            if txn['type'].startswith('trade') and txn['currency_code'] == 'EUR':
                trading_volume += txn['amount']
        
        return trading_volume
    
    async def _calculate_fees_paid(self, transactions: List[Dict]) -> float:
        """Berechnet geschätzte Fees für Transactions"""
        
        fees_paid = 0.0
        
        for txn in transactions:
            if txn['type'].startswith('trade'):
                # Geschätzte Fee: 0.1% des Trade Volume
                estimated_fee = txn['amount'] * 0.001
                fees_paid += estimated_fee
            elif txn['type'] == 'withdrawal':
                # Geschätzte Withdrawal Fee
                fees_paid += min(txn['amount'] * 0.005, 10.0)  # 0.5% max 10 EUR
        
        return fees_paid
    
    async def _calculate_summary_statistics(self, usage_metrics: Dict[str, Dict]) -> Dict[str, Any]:
        """Berechnet Summary Statistics für Usage Metrics"""
        
        if not usage_metrics:
            return {}
        
        # Overall Usage Statistics
        usage_percentages = [metric['usage_percentage'] for metric in usage_metrics.values()]
        
        avg_usage_percentage = round(sum(usage_percentages) / len(usage_percentages), 1)
        max_usage_percentage = round(max(usage_percentages), 1)
        min_usage_percentage = round(min(usage_percentages), 1)
        
        # Status Distribution
        status_counts = {}
        for metric in usage_metrics.values():
            status = metric['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Critical Metrics
        critical_metrics = [
            metric['metric_name'] for metric in usage_metrics.values()
            if metric['status'] in ['critical', 'exceeded']
        ]
        
        # Usage Efficiency (wie gut werden Limits genutzt)
        efficiency_score = min(100, avg_usage_percentage)  # Optimal nutzung ohne überschreitung
        
        return {
            'total_metrics': len(usage_metrics),
            'average_usage_percentage': avg_usage_percentage,
            'maximum_usage_percentage': max_usage_percentage,
            'minimum_usage_percentage': min_usage_percentage,
            'status_distribution': status_counts,
            'critical_metrics_count': len(critical_metrics),
            'critical_metrics': critical_metrics,
            'usage_efficiency_score': round(efficiency_score, 1),
            'overall_status': self._determine_overall_status(status_counts, avg_usage_percentage)
        }
    
    def _determine_overall_status(self, status_counts: Dict[str, int], 
                                avg_usage: float) -> str:
        """Bestimmt Overall Status basierend auf Metric Status"""
        
        if status_counts.get('exceeded', 0) > 0:
            return 'exceeded'
        elif status_counts.get('critical', 0) > 0:
            return 'critical'
        elif status_counts.get('warning', 0) > 0 or avg_usage > 70:
            return 'warning'
        else:
            return 'normal'
    
    async def _perform_trend_analysis(self, current_period: UsagePeriod, 
                                    current_metrics: Dict[str, Dict]) -> Dict[str, Any]:
        """Führt Trend Analysis für Usage Metrics durch"""
        
        trend_analysis = {}
        
        # Vergleiche mit vorheriger Period
        previous_period = await self._get_previous_period(current_period)
        previous_metrics = await self._calculate_usage_metrics(previous_period, [])
        
        # Metric-by-Metric Trend Comparison
        metric_trends = {}
        for metric_name, current_metric in current_metrics.items():
            if metric_name in previous_metrics:
                previous_value = previous_metrics[metric_name]['current_value']
                current_value = current_metric['current_value']
                
                if previous_value > 0:
                    growth_rate = ((current_value - previous_value) / previous_value) * 100
                else:
                    growth_rate = 100.0 if current_value > 0 else 0.0
                
                trend_direction = 'increasing' if growth_rate > 0 else 'decreasing' if growth_rate < 0 else 'stable'
                trend_significance = 'significant' if abs(growth_rate) > (self.trend_config['growth_rate_threshold'] * 100) else 'minor'
                
                metric_trends[metric_name] = {
                    'previous_value': round(previous_value, 2),
                    'current_value': round(current_value, 2),
                    'growth_rate_percentage': round(growth_rate, 1),
                    'trend_direction': trend_direction,
                    'trend_significance': trend_significance
                }
        
        # Overall Trend Assessment
        growth_rates = [trend['growth_rate_percentage'] for trend in metric_trends.values()]
        avg_growth_rate = round(sum(growth_rates) / len(growth_rates), 1) if growth_rates else 0
        
        trend_analysis = {
            'comparison_period': {
                'start_date': previous_period.start_date.isoformat(),
                'end_date': previous_period.end_date.isoformat(),
                'period_type': previous_period.period_type
            },
            'metric_trends': metric_trends,
            'overall_trend': {
                'average_growth_rate_percentage': avg_growth_rate,
                'trending_direction': 'up' if avg_growth_rate > 5 else 'down' if avg_growth_rate < -5 else 'stable',
                'concerning_trends': self._identify_concerning_trends(metric_trends)
            }
        }
        
        return trend_analysis
    
    async def _get_previous_period(self, current_period: UsagePeriod) -> UsagePeriod:
        """Bestimmt die vorherige Vergleichsperiode"""
        
        period_duration = current_period.end_date - current_period.start_date
        
        previous_end = current_period.start_date
        previous_start = previous_end - period_duration
        
        return UsagePeriod(
            start_date=previous_start,
            end_date=previous_end,
            period_type=current_period.period_type
        )
    
    def _identify_concerning_trends(self, metric_trends: Dict[str, Dict]) -> List[str]:
        """Identifiziert concerning Trends in Usage Metrics"""
        
        concerning_trends = []
        
        for metric_name, trend_data in metric_trends.items():
            growth_rate = trend_data['growth_rate_percentage']
            significance = trend_data['trend_significance']
            
            if significance == 'significant' and growth_rate > 50:
                concerning_trends.append(f'{metric_name} increased by {growth_rate}% - rapid growth')
            elif growth_rate > 100:
                concerning_trends.append(f'{metric_name} more than doubled - investigate cause')
        
        return concerning_trends
    
    async def _generate_usage_warnings(self, usage_metrics: Dict[str, Dict]) -> List[str]:
        """Generiert Usage Warnings basierend auf Metrics"""
        
        warnings = []
        
        for metric_name, metric_data in usage_metrics.items():
            status = metric_data['status']
            usage_percentage = metric_data['usage_percentage']
            
            if status == 'exceeded':
                warnings.append(f'{metric_name}: Limit exceeded ({usage_percentage}% of limit used)')
            elif status == 'critical':
                warnings.append(f'{metric_name}: Critical usage level ({usage_percentage}% of limit used)')
            elif status == 'warning':
                warnings.append(f'{metric_name}: High usage ({usage_percentage}% of limit used)')
        
        # Additional Warnings
        if len([m for m in usage_metrics.values() if m['status'] in ['critical', 'exceeded']]) >= 3:
            warnings.append('Multiple limits approaching - consider reducing activity')
        
        return warnings
    
    def _has_valid_cache(self, cache_key: str) -> bool:
        """Prüft ob Cache für Key noch gültig ist"""
        
        if cache_key not in self.cache_timestamps:
            return False
        
        cache_age = (datetime.now() - self.cache_timestamps[cache_key]).seconds
        max_cache_age = 300  # 5 minutes
        
        return cache_age < max_cache_age
    
    def get_usage_summary_for_period(self, period_type: str) -> Dict[str, Any]:
        """Gibt schnelle Usage Summary für Period zurück"""
        
        cache_key = f"{period_type}_default"
        if self._has_valid_cache(cache_key):
            cached_result = self.usage_cache[cache_key]
            return {
                'period_type': period_type,
                'overall_status': cached_result.summary_statistics.get('overall_status', 'unknown'),
                'average_usage_percentage': cached_result.summary_statistics.get('average_usage_percentage', 0),
                'critical_metrics_count': cached_result.summary_statistics.get('critical_metrics_count', 0),
                'warnings_count': len(cached_result.usage_warnings),
                'last_calculated': cached_result.calculation_timestamp.isoformat()
            }
        
        return {'error': 'No cached data available', 'period_type': period_type}
    
    def clear_usage_cache(self):
        """Leert Usage Cache (für externe Cache Management)"""
        self.usage_cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("Usage calculation cache cleared")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'current_usage_calculation',
            'description': 'Calculates current usage against account limits with trend analysis',
            'responsibility': 'Current usage calculation logic only',
            'input_parameters': {
                'calculation_period': 'Period type for calculation (daily, weekly, monthly, yearly)',
                'include_trend_analysis': 'Whether to include trend analysis (default: true)',
                'refresh_cache': 'Whether to refresh cached calculations (default: false)',
                'metric_filters': 'Optional list of specific metrics to calculate',
                'custom_period': 'Optional custom period with start_date and end_date'
            },
            'output_format': {
                'calculation_period': 'Period information used for calculation',
                'usage_metrics': 'Detailed usage metrics with current values and limits',
                'summary_statistics': 'Summary statistics across all metrics',
                'trend_analysis': 'Trend analysis comparing to previous period',
                'usage_warnings': 'List of usage warnings and alerts',
                'calculation_timestamp': 'Timestamp of calculation'
            },
            'supported_periods': ['daily', 'weekly', 'monthly', 'yearly', 'custom'],
            'supported_metrics': [
                'daily_withdrawals', 'trading_volume', 'transaction_count',
                'open_orders', 'position_size', 'fees_paid'
            ],
            'usage_thresholds': self.usage_thresholds,
            'cache_duration_seconds': 300,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Current Usage Calculation Module Statistiken"""
        total_calculations = len(self.calculation_history)
        
        if total_calculations == 0:
            return {
                'total_calculations': 0,
                'cache_entries': len(self.usage_cache),
                'supported_metrics': 6
            }
        
        # Calculation Frequency per Period Type
        period_distribution = {}
        for calc in self.calculation_history:
            period = calc['calculation_period']
            period_distribution[period] = period_distribution.get(period, 0) + 1
        
        # Cache Hit Rate
        cache_hits = sum(1 for calc in self.calculation_history if calc.get('cache_used', False))
        cache_hit_rate = round((cache_hits / total_calculations) * 100, 1) if total_calculations > 0 else 0
        
        # Average Warnings per Calculation
        total_warnings = sum(calc['warnings_generated'] for calc in self.calculation_history)
        avg_warnings = round(total_warnings / total_calculations, 1) if total_calculations > 0 else 0
        
        # Recent Activity
        recent_calculations = [
            calc for calc in self.calculation_history
            if (datetime.now() - calc['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_calculations': total_calculations,
            'recent_calculations_last_hour': len(recent_calculations),
            'period_type_distribution': dict(sorted(
                period_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'cache_hit_rate_percent': cache_hit_rate,
            'cache_entries_active': len(self.usage_cache),
            'average_warnings_per_calculation': avg_warnings,
            'supported_metrics_count': 6,
            'average_processing_time': self.average_execution_time
        }

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions"""
        try:
            # Subscribe to relevant events for this module
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            
            self.logger.info("Event subscriptions setup completed", 
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)
    
    async def process_event(self, event):
        """Process incoming events"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'execution_count': getattr(self, 'execution_history', []),
                        'average_execution_time_ms': self.average_execution_time,
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
            elif event_type == f'{self.module_name}.request':
                # Module-specific request
                event_data = event.get('data', {})
                result = await self.execute_function(event_data)
                
                response_event = {
                    'event_type': f'{self.module_name}.response',
                    'stream_id': event.get('stream_id', f'{self.module_name}-request'),
                    'data': result,
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(response_event)
            
            else:
                self.logger.debug("Unhandled event type", 
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)
