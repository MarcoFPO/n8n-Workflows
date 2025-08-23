"""
GUI Testing Handler - Single Function Module
Verantwortlich ausschließlich für GUI Testing und Monitoring Logic
"""

from typing import Dict, Any, List, Optional
import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

from shared.common_imports import (
    datetime, timedelta, BaseModel, structlog
)
from modules.single_function_module_base_v1_2_0_20250809 import SingleFunctionModule
from shared.event_bus import Event, EventType


class GUITestRequest(BaseModel):
    request_type: str  # 'get_elements', 'get_status', 'run_test', 'validate_elements', 'performance_check'
    test_scope: Optional[str] = None  # 'dashboard', 'market_data', 'trading', 'all'
    element_filter: Optional[List[str]] = None
    include_performance: Optional[bool] = False
    test_depth: Optional[str] = 'basic'  # 'basic', 'detailed', 'comprehensive'


class GUIElement(BaseModel):
    element_id: str
    element_type: str  # 'button', 'input', 'display', 'chart', 'table', 'widget'
    element_category: str  # 'dashboard', 'market_data', 'trading', 'navigation'
    selector: str  # CSS/XPath selector
    is_visible: bool
    is_interactive: bool
    accessibility_score: float  # 0-100
    performance_score: float  # 0-100
    last_tested: datetime
    test_status: str  # 'pass', 'fail', 'warning', 'not_tested'
    test_warnings: List[str]


class GUITestResult(BaseModel):
    test_successful: bool
    elements_tested: int
    elements_passed: int
    elements_failed: int
    elements_with_warnings: int
    gui_elements: Dict[str, GUIElement]
    performance_metrics: Dict[str, Any]
    accessibility_score: float
    overall_health_score: float
    test_warnings: List[str]
    test_timestamp: datetime


class GUITestingHandler(SingleFunctionModule):
    """
    Single Function Module: GUI Testing and Monitoring
    Verantwortlichkeit: Ausschließlich GUI-Testing-und-Monitoring-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("gui_testing_handler", event_bus)
        
        # GUI Elements Registry
        self.gui_elements = {
            # Dashboard Elements
            'portfolio_value': GUIElement(
                element_id='portfolio_value',
                element_type='display',
                element_category='dashboard',
                selector='#portfolio-value',
                is_visible=True,
                is_interactive=False,
                accessibility_score=85.0,
                performance_score=92.0,
                last_tested=datetime.now() - timedelta(hours=1),
                test_status='pass',
                test_warnings=[]
            ),
            'daily_change': GUIElement(
                element_id='daily_change',
                element_type='display',
                element_category='dashboard',
                selector='#daily-change',
                is_visible=True,
                is_interactive=False,
                accessibility_score=88.0,
                performance_score=90.0,
                last_tested=datetime.now() - timedelta(hours=1),
                test_status='pass',
                test_warnings=['Consider adding color-blind friendly indicators']
            ),
            'active_orders': GUIElement(
                element_id='active_orders',
                element_type='display',
                element_category='dashboard',
                selector='#active-orders-count',
                is_visible=True,
                is_interactive=True,
                accessibility_score=82.0,
                performance_score=88.0,
                last_tested=datetime.now() - timedelta(hours=1),
                test_status='pass',
                test_warnings=[]
            ),
            'refresh_button': GUIElement(
                element_id='refresh_button',
                element_type='button',
                element_category='dashboard',
                selector='#refresh-dashboard-btn',
                is_visible=True,
                is_interactive=True,
                accessibility_score=95.0,
                performance_score=85.0,
                last_tested=datetime.now() - timedelta(hours=1),
                test_status='pass',
                test_warnings=[]
            ),
            
            # Market Data Elements
            'price_chart': GUIElement(
                element_id='price_chart',
                element_type='chart',
                element_category='market_data',
                selector='#market-price-chart',
                is_visible=True,
                is_interactive=True,
                accessibility_score=75.0,
                performance_score=78.0,
                last_tested=datetime.now() - timedelta(hours=2),
                test_status='warning',
                test_warnings=['Chart loading time above optimal', 'Missing alt text for screen readers']
            ),
            'watchlist': GUIElement(
                element_id='watchlist',
                element_type='table',
                element_category='market_data',
                selector='#watchlist-table',
                is_visible=True,
                is_interactive=True,
                accessibility_score=90.0,
                performance_score=92.0,
                last_tested=datetime.now() - timedelta(hours=2),
                test_status='pass',
                test_warnings=[]
            ),
            'symbol_search': GUIElement(
                element_id='symbol_search',
                element_type='input',
                element_category='market_data',
                selector='#symbol-search-input',
                is_visible=True,
                is_interactive=True,
                accessibility_score=88.0,
                performance_score=94.0,
                last_tested=datetime.now() - timedelta(hours=2),
                test_status='pass',
                test_warnings=[]
            ),
            'add_to_watchlist_btn': GUIElement(
                element_id='add_to_watchlist_btn',
                element_type='button',
                element_category='market_data',
                selector='#add-watchlist-btn',
                is_visible=True,
                is_interactive=True,
                accessibility_score=92.0,
                performance_score=89.0,
                last_tested=datetime.now() - timedelta(hours=2),
                test_status='pass',
                test_warnings=[]
            ),
            
            # Trading Elements
            'order_form': GUIElement(
                element_id='order_form',
                element_type='input',
                element_category='trading',
                selector='#new-order-form',
                is_visible=True,
                is_interactive=True,
                accessibility_score=85.0,
                performance_score=87.0,
                last_tested=datetime.now() - timedelta(hours=3),
                test_status='pass',
                test_warnings=['Form validation feedback could be improved']
            ),
            'order_history': GUIElement(
                element_id='order_history',
                element_type='table',
                element_category='trading',
                selector='#order-history-table',
                is_visible=True,
                is_interactive=True,
                accessibility_score=88.0,
                performance_score=85.0,
                last_tested=datetime.now() - timedelta(hours=3),
                test_status='pass',
                test_warnings=[]
            ),
            'active_orders_table': GUIElement(
                element_id='active_orders_table',
                element_type='table',
                element_category='trading',
                selector='#active-orders-table',
                is_visible=True,
                is_interactive=True,
                accessibility_score=86.0,
                performance_score=90.0,
                last_tested=datetime.now() - timedelta(hours=3),
                test_status='pass',
                test_warnings=[]
            ),
            'cancel_order_btn': GUIElement(
                element_id='cancel_order_btn',
                element_type='button',
                element_category='trading',
                selector='.cancel-order-btn',
                is_visible=True,
                is_interactive=True,
                accessibility_score=90.0,
                performance_score=92.0,
                last_tested=datetime.now() - timedelta(hours=3),
                test_status='pass',
                test_warnings=[]
            ),
            
            # Navigation Elements
            'main_nav': GUIElement(
                element_id='main_nav',
                element_type='widget',
                element_category='navigation',
                selector='#main-navigation',
                is_visible=True,
                is_interactive=True,
                accessibility_score=95.0,
                performance_score=96.0,
                last_tested=datetime.now() - timedelta(minutes=30),
                test_status='pass',
                test_warnings=[]
            ),
            'user_menu': GUIElement(
                element_id='user_menu',
                element_type='widget',
                element_category='navigation',
                selector='#user-menu',
                is_visible=True,
                is_interactive=True,
                accessibility_score=92.0,
                performance_score=94.0,
                last_tested=datetime.now() - timedelta(minutes=30),
                test_status='pass',
                test_warnings=[]
            )
        }
        
        # GUI Testing Configuration
        self.testing_config = {
            'auto_testing_enabled': True,
            'test_interval_minutes': 30,
            'performance_threshold_ms': 2000,
            'accessibility_threshold': 80.0,
            'health_score_threshold': 85.0,
            'element_visibility_timeout': 5000,  # ms
            'interaction_timeout': 3000,  # ms
            'screenshot_on_failure': True,
            'test_retries': 2,
            'parallel_testing': True,
            'browser_compatibility': ['chrome', 'firefox', 'safari', 'edge'],
            'responsive_breakpoints': [320, 768, 1024, 1920],
            'performance_budgets': {
                'page_load_time': 3000,  # ms
                'first_contentful_paint': 1500,  # ms
                'largest_contentful_paint': 2500,  # ms
                'cumulative_layout_shift': 0.1
            }
        }
        
        # Performance Metrics
        self.performance_metrics = {
            'page_load_time_ms': 2850,
            'first_contentful_paint_ms': 1250,
            'largest_contentful_paint_ms': 2100,
            'cumulative_layout_shift': 0.08,
            'time_to_interactive_ms': 3200,
            'total_blocking_time_ms': 150,
            'dom_content_loaded_ms': 1800,
            'dom_complete_ms': 2850,
            'resource_count': 45,
            'total_resource_size_kb': 1250,
            'javascript_size_kb': 450,
            'css_size_kb': 125,
            'images_size_kb': 675,
            'memory_usage_mb': 85,
            'cpu_usage_percent': 12
        }
        
        # Test Execution History
        self.test_history = []
        self.test_counter = 0
        
        # Page Registry (for testing)
        self.test_pages = {
            'dashboard': {
                'url': '/',
                'title': 'Aktienanalyse Dashboard v2',
                'key_elements': ['portfolio_value', 'daily_change', 'active_orders', 'refresh_button'],
                'load_timeout': 5000
            },
            'market_data': {
                'url': '/market',
                'title': 'Market Data',
                'key_elements': ['price_chart', 'watchlist', 'symbol_search'],
                'load_timeout': 7000
            },
            'trading': {
                'url': '/trading',
                'title': 'Trading Interface',
                'key_elements': ['order_form', 'order_history', 'active_orders_table'],
                'load_timeout': 6000
            }
        }
        
        # Browser Compatibility Results
        self.browser_test_results = {
            'chrome': {'compatibility_score': 98.5, 'last_tested': datetime.now() - timedelta(hours=6)},
            'firefox': {'compatibility_score': 95.2, 'last_tested': datetime.now() - timedelta(hours=6)},
            'safari': {'compatibility_score': 92.8, 'last_tested': datetime.now() - timedelta(hours=12)},
            'edge': {'compatibility_score': 96.1, 'last_tested': datetime.now() - timedelta(hours=6)}
        }
        
        # Responsive Design Test Results
        self.responsive_test_results = {
            320: {'score': 88.5, 'warnings': ['Navigation menu overlaps content']},
            768: {'score': 95.2, 'warnings': []},
            1024: {'score': 97.8, 'warnings': []},
            1920: {'score': 96.5, 'warnings': ['Large screen optimization possible']}
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: GUI Testing and Monitoring
        
        Args:
            input_data: {
                'request_type': required string ('get_elements', 'get_status', 'run_test', 'validate_elements', 'performance_check'),
                'test_scope': optional string ('dashboard', 'market_data', 'trading', 'all'),
                'element_filter': optional list of element IDs to test,
                'include_performance': optional bool (default: false),
                'test_depth': optional string ('basic', 'detailed', 'comprehensive'),
                'run_accessibility_check': optional bool (default: true),
                'check_responsiveness': optional bool (default: false),
                'browser_compatibility': optional bool (default: false)
            }
            
        Returns:
            Dict mit GUI-Test-Result
        """
        start_time = datetime.now()
        
        try:
            # GUI Test Request erstellen
            gui_request = GUITestRequest(
                request_type=input_data.get('request_type'),
                test_scope=input_data.get('test_scope', 'all'),
                element_filter=input_data.get('element_filter'),
                include_performance=input_data.get('include_performance', False),
                test_depth=input_data.get('test_depth', 'basic')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid GUI test request: {str(e)}'
            }
        
        run_accessibility = input_data.get('run_accessibility_check', True)
        check_responsive = input_data.get('check_responsiveness', False)
        browser_compat = input_data.get('browser_compatibility', False)
        
        # GUI Test Processing
        gui_result = await self._process_gui_test_request(
            gui_request, run_accessibility, check_responsive, browser_compat
        )
        
        # Statistics Update
        self.test_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Test History
        self.test_history.append({
            'timestamp': datetime.now(),
            'request_type': gui_request.request_type,
            'test_scope': gui_request.test_scope,
            'test_successful': gui_result.test_successful,
            'elements_tested': gui_result.elements_tested,
            'elements_passed': gui_result.elements_passed,
            'elements_failed': gui_result.elements_failed,
            'warnings_count': len(gui_result.test_warnings),
            'processing_time_ms': processing_time_ms,
            'test_id': self.test_counter
        })
        
        # Limit History
        if len(self.test_history) > 300:
            self.test_history.pop(0)
        
        # Event Publishing für GUI Test Events
        await self._publish_gui_test_event(gui_result, gui_request)
        
        self.logger.info(f"GUI test request processed",
                       request_type=gui_request.request_type,
                       test_scope=gui_request.test_scope,
                       test_successful=gui_result.test_successful,
                       elements_tested=gui_result.elements_tested,
                       elements_passed=gui_result.elements_passed,
                       elements_failed=gui_result.elements_failed,
                       warnings_count=len(gui_result.test_warnings),
                       processing_time_ms=round(processing_time_ms, 2),
                       test_id=self.test_counter)
        
        return {
            'success': True,
            'test_successful': gui_result.test_successful,
            'elements_tested': gui_result.elements_tested,
            'elements_passed': gui_result.elements_passed,
            'elements_failed': gui_result.elements_failed,
            'elements_with_warnings': gui_result.elements_with_warnings,
            'gui_elements': {k: {
                'element_id': v.element_id,
                'element_type': v.element_type,
                'element_category': v.element_category,
                'selector': v.selector,
                'is_visible': v.is_visible,
                'is_interactive': v.is_interactive,
                'accessibility_score': v.accessibility_score,
                'performance_score': v.performance_score,
                'last_tested': v.last_tested.isoformat(),
                'test_status': v.test_status,
                'test_warnings': v.test_warnings
            } for k, v in gui_result.gui_elements.items()},
            'performance_metrics': gui_result.performance_metrics,
            'accessibility_score': gui_result.accessibility_score,
            'overall_health_score': gui_result.overall_health_score,
            'test_warnings': gui_result.test_warnings,
            'test_timestamp': gui_result.test_timestamp.isoformat()
        }
    
    async def _process_gui_test_request(self, request: GUITestRequest,
                                      run_accessibility: bool,
                                      check_responsive: bool,
                                      browser_compat: bool) -> GUITestResult:
        """Verarbeitet GUI Test Request komplett"""
        
        test_warnings = []
        
        if request.request_type == 'get_elements':
            # GUI Elements abrufen
            elements = await self._get_filtered_elements(request.test_scope, request.element_filter)
            
        elif request.request_type == 'get_status':
            # GUI Status abrufen
            elements = await self._get_gui_status(request.test_scope)
            
        elif request.request_type == 'run_test':
            # Tests ausführen
            elements = await self._run_gui_tests(request.test_scope, request.test_depth, request.element_filter)
            
        elif request.request_type == 'validate_elements':
            # Element Validation
            elements = await self._validate_gui_elements(request.element_filter or list(self.gui_elements.keys()))
            
        elif request.request_type == 'performance_check':
            # Performance Check
            elements = await self._run_performance_tests()
            
        else:
            elements = await self._get_filtered_elements(request.test_scope, request.element_filter)
            test_warnings.append(f'Unknown request type: {request.request_type}, fallback to get_elements')
        
        # Performance Metrics einbeziehen
        performance_metrics = {}
        if request.include_performance:
            performance_metrics = await self._get_performance_metrics()
            
            # Performance Warnings
            perf_warnings = await self._check_performance_thresholds(performance_metrics)
            test_warnings.extend(perf_warnings)
        
        # Accessibility Check
        accessibility_score = 0.0
        if run_accessibility:
            accessibility_score = await self._calculate_accessibility_score(elements)
            
            if accessibility_score < self.testing_config['accessibility_threshold']:
                test_warnings.append(f'Accessibility score below threshold: {accessibility_score:.1f}%')
        
        # Responsive Design Check
        if check_responsive:
            responsive_warnings = await self._check_responsive_design()
            test_warnings.extend(responsive_warnings)
        
        # Browser Compatibility Check
        if browser_compat:
            compat_warnings = await self._check_browser_compatibility()
            test_warnings.extend(compat_warnings)
        
        # Test Statistics berechnen
        elements_tested = len(elements)
        elements_passed = sum(1 for e in elements.values() if e.test_status == 'pass')
        elements_failed = sum(1 for e in elements.values() if e.test_status == 'fail')
        elements_with_warnings = sum(1 for e in elements.values() if e.test_warnings)
        
        # Overall Health Score
        overall_health = await self._calculate_overall_health_score(
            elements, performance_metrics, accessibility_score
        )
        
        test_successful = (
            elements_failed == 0 and 
            overall_health >= self.testing_config['health_score_threshold']
        )
        
        return GUITestResult(
            test_successful=test_successful,
            elements_tested=elements_tested,
            elements_passed=elements_passed,
            elements_failed=elements_failed,
            elements_with_warnings=elements_with_warnings,
            gui_elements=elements,
            performance_metrics=performance_metrics,
            accessibility_score=accessibility_score,
            overall_health_score=overall_health,
            test_warnings=test_warnings,
            test_timestamp=datetime.now()
        )
    
    async def _get_filtered_elements(self, test_scope: str, 
                                   element_filter: Optional[List[str]]) -> Dict[str, GUIElement]:
        """Holt gefilterte GUI Elements"""
        
        elements = {}
        
        for element_id, element in self.gui_elements.items():
            # Scope Filter
            if test_scope != 'all' and element.element_category != test_scope:
                continue
            
            # Element Filter
            if element_filter and element_id not in element_filter:
                continue
            
            elements[element_id] = element
        
        return elements
    
    async def _get_gui_status(self, test_scope: str) -> Dict[str, GUIElement]:
        """Holt aktuellen GUI Status"""
        
        elements = await self._get_filtered_elements(test_scope, None)
        
        # Status Update für alle Elements
        for element in elements.values():
            # Mock Status Update - in Produktion würde echte DOM-Checks stattfinden
            await self._update_element_status(element)
        
        return elements
    
    async def _run_gui_tests(self, test_scope: str, test_depth: str,
                           element_filter: Optional[List[str]]) -> Dict[str, GUIElement]:
        """Führt GUI Tests aus"""
        
        elements = await self._get_filtered_elements(test_scope, element_filter)
        
        for element in elements.values():
            # Test ausführen basierend auf depth
            await self._run_element_test(element, test_depth)
            element.last_tested = datetime.now()
        
        return elements
    
    async def _validate_gui_elements(self, element_ids: List[str]) -> Dict[str, GUIElement]:
        """Validiert spezifische GUI Elements"""
        
        elements = {}
        
        for element_id in element_ids:
            if element_id in self.gui_elements:
                element = self.gui_elements[element_id]
                await self._validate_single_element(element)
                elements[element_id] = element
        
        return elements
    
    async def _run_performance_tests(self) -> Dict[str, GUIElement]:
        """Führt Performance-fokussierte Tests aus"""
        
        elements = self.gui_elements.copy()
        
        # Performance Tests für alle Elements
        for element in elements.values():
            element.performance_score = await self._measure_element_performance(element)
            element.last_tested = datetime.now()
            
            # Performance-basierte Warnings
            if element.performance_score < 80:
                element.test_warnings.append(f'Performance score below optimal: {element.performance_score:.1f}%')
                element.test_status = 'warning'
        
        return elements
    
    async def _update_element_status(self, element: GUIElement):
        """Aktualisiert Element Status (Mock Implementation)"""
        
        import random
        
        # Mock Status Updates
        element.is_visible = random.choice([True, True, True, False])  # 75% visible
        
        if not element.is_visible:
            element.test_status = 'fail'
            element.test_warnings = ['Element not visible']
        else:
            element.test_status = 'pass'
            element.test_warnings = []
        
        # Mock Performance Score Variation
        element.performance_score = max(70, min(100, element.performance_score + random.uniform(-5, 5)))
    
    async def _run_element_test(self, element: GUIElement, test_depth: str):
        """Führt Test für einzelnes Element aus"""
        
        import random
        
        # Mock Test Implementation
        test_results = []
        
        # Basic Tests
        if element.is_visible:
            test_results.append('visibility_pass')
        else:
            test_results.append('visibility_fail')
        
        if element.is_interactive:
            # Mock interaction test
            interaction_success = random.random() > 0.05  # 95% success rate
            if interaction_success:
                test_results.append('interaction_pass')
            else:
                test_results.append('interaction_fail')
        
        # Detailed Tests
        if test_depth in ['detailed', 'comprehensive']:
            # Accessibility test
            if element.accessibility_score >= 80:
                test_results.append('accessibility_pass')
            else:
                test_results.append('accessibility_warning')
        
        # Comprehensive Tests
        if test_depth == 'comprehensive':
            # Performance test
            if element.performance_score >= 85:
                test_results.append('performance_pass')
            else:
                test_results.append('performance_warning')
        
        # Update Element basierend auf Test Results
        failed_tests = [r for r in test_results if 'fail' in r]
        warning_tests = [r for r in test_results if 'warning' in r]
        
        if failed_tests:
            element.test_status = 'fail'
            element.test_warnings = [f'Failed test: {test}' for test in failed_tests]
        elif warning_tests:
            element.test_status = 'warning'
            element.test_warnings = [f'Warning in test: {test}' for test in warning_tests]
        else:
            element.test_status = 'pass'
            element.test_warnings = []
    
    async def _validate_single_element(self, element: GUIElement):
        """Validiert einzelnes Element"""
        
        validation_warnings = []
        
        # Selector Validation
        if not element.selector or not element.selector.strip():
            validation_warnings.append('Missing or empty selector')
        
        # Category Validation
        valid_categories = ['dashboard', 'market_data', 'trading', 'navigation']
        if element.element_category not in valid_categories:
            validation_warnings.append(f'Invalid category: {element.element_category}')
        
        # Accessibility Score Validation
        if element.accessibility_score < 70:
            validation_warnings.append(f'Low accessibility score: {element.accessibility_score}%')
        
        # Performance Score Validation
        if element.performance_score < 75:
            validation_warnings.append(f'Low performance score: {element.performance_score}%')
        
        # Last Tested Validation
        hours_since_test = (datetime.now() - element.last_tested).total_seconds() / 3600
        if hours_since_test > 24:
            validation_warnings.append(f'Element not tested recently: {hours_since_test:.1f} hours ago')
        
        # Update Element
        if validation_warnings:
            element.test_status = 'warning'
            element.test_warnings = validation_warnings
        else:
            element.test_status = 'pass'
            element.test_warnings = []
        
        element.last_tested = datetime.now()
    
    async def _measure_element_performance(self, element: GUIElement) -> float:
        """Misst Performance für Element (Mock Implementation)"""
        
        import random
        
        # Mock Performance Measurements
        base_score = element.performance_score
        
        # Element Type spezifische Performance
        if element.element_type == 'chart':
            # Charts sind typischerweise langsamer
            performance_factor = random.uniform(0.7, 0.9)
        elif element.element_type == 'table':
            # Tables können bei vielen Daten langsam werden
            performance_factor = random.uniform(0.8, 0.95)
        elif element.element_type == 'input':
            # Inputs sind normalerweise schnell
            performance_factor = random.uniform(0.95, 1.0)
        else:
            performance_factor = random.uniform(0.85, 0.98)
        
        new_score = base_score * performance_factor
        return round(max(0, min(100, new_score)), 1)
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Holt aktuelle Performance Metrics"""
        
        # Mock Performance Metrics Update
        import random
        
        metrics = self.performance_metrics.copy()
        
        # Simulate slight variations
        metrics['page_load_time_ms'] = max(1000, metrics['page_load_time_ms'] + random.randint(-200, 300))
        metrics['first_contentful_paint_ms'] = max(500, metrics['first_contentful_paint_ms'] + random.randint(-100, 200))
        metrics['memory_usage_mb'] = max(50, metrics['memory_usage_mb'] + random.randint(-10, 15))
        metrics['cpu_usage_percent'] = max(5, min(30, metrics['cpu_usage_percent'] + random.randint(-3, 5)))
        
        return metrics
    
    async def _check_performance_thresholds(self, metrics: Dict[str, Any]) -> List[str]:
        """Prüft Performance gegen Thresholds"""
        
        warnings = []
        budgets = self.testing_config['performance_budgets']
        
        if metrics.get('page_load_time_ms', 0) > budgets['page_load_time']:
            warnings.append(f"Page load time exceeds budget: {metrics['page_load_time_ms']}ms > {budgets['page_load_time']}ms")
        
        if metrics.get('first_contentful_paint_ms', 0) > budgets['first_contentful_paint']:
            warnings.append(f"FCP exceeds budget: {metrics['first_contentful_paint_ms']}ms > {budgets['first_contentful_paint']}ms")
        
        if metrics.get('largest_contentful_paint_ms', 0) > budgets['largest_contentful_paint']:
            warnings.append(f"LCP exceeds budget: {metrics['largest_contentful_paint_ms']}ms > {budgets['largest_contentful_paint']}ms")
        
        if metrics.get('cumulative_layout_shift', 0) > budgets['cumulative_layout_shift']:
            warnings.append(f"CLS exceeds budget: {metrics['cumulative_layout_shift']} > {budgets['cumulative_layout_shift']}")
        
        return warnings
    
    async def _calculate_accessibility_score(self, elements: Dict[str, GUIElement]) -> float:
        """Berechnet Accessibility Score"""
        
        if not elements:
            return 0.0
        
        total_score = sum(element.accessibility_score for element in elements.values())
        return round(total_score / len(elements), 1)
    
    async def _check_responsive_design(self) -> List[str]:
        """Prüft Responsive Design"""
        
        warnings = []
        
        for breakpoint, result in self.responsive_test_results.items():
            if result['score'] < 90:
                warnings.append(f"Low responsive score at {breakpoint}px: {result['score']}%")
            
            if result['warnings']:
                warnings.extend([f"{breakpoint}px: {warning}" for warning in result['warnings']])
        
        return warnings
    
    async def _check_browser_compatibility(self) -> List[str]:
        """Prüft Browser Compatibility"""
        
        warnings = []
        
        for browser, result in self.browser_test_results.items():
            if result['compatibility_score'] < 95:
                warnings.append(f"Low compatibility score for {browser}: {result['compatibility_score']}%")
            
            # Check if test is outdated
            hours_since_test = (datetime.now() - result['last_tested']).total_seconds() / 3600
            if hours_since_test > 48:
                warnings.append(f"Browser compatibility test for {browser} outdated: {hours_since_test:.1f} hours")
        
        return warnings
    
    async def _calculate_overall_health_score(self, elements: Dict[str, GUIElement],
                                           performance_metrics: Dict[str, Any],
                                           accessibility_score: float) -> float:
        """Berechnet Overall Health Score"""
        
        # Element Health (40%)
        if elements:
            passed_elements = sum(1 for e in elements.values() if e.test_status == 'pass')
            element_score = (passed_elements / len(elements)) * 100
        else:
            element_score = 0
        
        # Performance Score (35%)
        if performance_metrics:
            # Normalize performance metrics to 0-100 score
            page_load_score = max(0, 100 - (performance_metrics.get('page_load_time_ms', 3000) / 30))
            memory_score = max(0, 100 - (performance_metrics.get('memory_usage_mb', 100) / 2))
            performance_score = (page_load_score + memory_score) / 2
        else:
            performance_score = 85  # Default if no metrics
        
        # Accessibility Score (25%)
        accessibility_weight = accessibility_score if accessibility_score > 0 else 80
        
        # Weighted Average
        overall_score = (
            element_score * 0.40 +
            performance_score * 0.35 +
            accessibility_weight * 0.25
        )
        
        return round(overall_score, 1)
    
    async def _publish_gui_test_event(self, result: GUITestResult,
                                    request: GUITestRequest):
        """Published GUI Test Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Nur für Test-Runs publishen
        if request.request_type in ['run_test', 'performance_check']:
            from event_bus import Event
            
            event = Event(
                event_type="gui_test_completed",
                stream_id=f"gui-test-{self.test_counter}",
                data={
                    'request_type': request.request_type,
                    'test_scope': request.test_scope,
                    'test_successful': result.test_successful,
                    'elements_tested': result.elements_tested,
                    'elements_passed': result.elements_passed,
                    'elements_failed': result.elements_failed,
                    'overall_health_score': result.overall_health_score,
                    'accessibility_score': result.accessibility_score,
                    'test_warnings_count': len(result.test_warnings),
                    'test_timestamp': result.test_timestamp.isoformat()
                },
                source="gui_testing_handler"
            )
            
            await self.event_bus.publish(event)
    
    def get_gui_testing_summary(self) -> Dict[str, Any]:
        """Gibt GUI Testing Summary zurück"""
        
        # Element Status Distribution
        status_distribution = {}
        for element in self.gui_elements.values():
            status = element.test_status
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # Category Distribution
        category_distribution = {}
        for element in self.gui_elements.values():
            category = element.element_category
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # Average Scores
        avg_accessibility = sum(e.accessibility_score for e in self.gui_elements.values()) / len(self.gui_elements)
        avg_performance = sum(e.performance_score for e in self.gui_elements.values()) / len(self.gui_elements)
        
        # Recent Test Activity
        recent_tests = [
            t for t in self.test_history
            if (datetime.now() - t['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_elements': len(self.gui_elements),
            'element_status_distribution': status_distribution,
            'element_category_distribution': category_distribution,
            'average_accessibility_score': round(avg_accessibility, 1),
            'average_performance_score': round(avg_performance, 1),
            'auto_testing_enabled': self.testing_config['auto_testing_enabled'],
            'test_interval_minutes': self.testing_config['test_interval_minutes'],
            'recent_tests_last_hour': len(recent_tests),
            'total_tests_run': len(self.test_history),
            'performance_budgets_met': await self._check_budgets_compliance(),
            'browser_compatibility_average': round(
                sum(r['compatibility_score'] for r in self.browser_test_results.values()) / 
                len(self.browser_test_results), 1
            ),
            'responsive_design_average': round(
                sum(r['score'] for r in self.responsive_test_results.values()) / 
                len(self.responsive_test_results), 1
            )
        }
    
    async def _check_budgets_compliance(self) -> bool:
        """Prüft Performance Budget Compliance"""
        
        budgets = self.testing_config['performance_budgets']
        metrics = self.performance_metrics
        
        return all([
            metrics['page_load_time_ms'] <= budgets['page_load_time'],
            metrics['first_contentful_paint_ms'] <= budgets['first_contentful_paint'],
            metrics['largest_contentful_paint_ms'] <= budgets['largest_contentful_paint'],
            metrics['cumulative_layout_shift'] <= budgets['cumulative_layout_shift']
        ])
    
    def configure_testing(self, config_updates: Dict[str, Any]):
        """Aktualisiert Testing Configuration"""
        
        for config_key, config_value in config_updates.items():
            if config_key in self.testing_config:
                self.testing_config[config_key] = config_value
                self.logger.info(f"Testing configuration updated",
                               config_key=config_key,
                               new_value=config_value)
    
    def add_gui_element(self, element_id: str, element_config: Dict[str, Any]):
        """Fügt neues GUI Element hinzu"""
        
        try:
            gui_element = GUIElement(
                element_id=element_id,
                element_type=element_config['element_type'],
                element_category=element_config['element_category'],
                selector=element_config['selector'],
                is_visible=element_config.get('is_visible', True),
                is_interactive=element_config.get('is_interactive', True),
                accessibility_score=element_config.get('accessibility_score', 80.0),
                performance_score=element_config.get('performance_score', 85.0),
                last_tested=datetime.now(),
                test_status='not_tested',
                test_warnings=[]
            )
            
            self.gui_elements[element_id] = gui_element
            
            self.logger.info(f"GUI element added",
                           element_id=element_id,
                           element_type=gui_element.element_type,
                           element_category=gui_element.element_category)
            
        except Exception as e:
            self.logger.error(f"Failed to add GUI element: {e}")
    
    def remove_gui_element(self, element_id: str):
        """Entfernt GUI Element"""
        
        if element_id in self.gui_elements:
            del self.gui_elements[element_id]
            self.logger.info(f"GUI element removed", element_id=element_id)
        else:
            self.logger.warning(f"GUI element not found for removal: {element_id}")
    
    def reset_test_results(self):
        """Reset Test Results (Administrative Function)"""
        
        for element in self.gui_elements.values():
            element.test_status = 'not_tested'
            element.test_warnings = []
            element.last_tested = datetime.now() - timedelta(days=1)
        
        self.test_history.clear()
        self.test_counter = 0
        
        self.logger.warning("GUI test results reset")
    
    async def _setup_event_subscriptions(self):
        """
        Setup Event-Bus subscriptions for GUI testing updates
        Event-Bus Compliance: Subscribe to relevant events instead of direct calls
        """
        if not self.event_bus or not self.event_bus.connected:
            return
        
        try:
            # Subscribe to module test requests
            await self.event_bus.subscribe(
                EventType.MODULE_TEST_REQUEST.value,
                self._handle_test_request,
                f"gui_test_request_{self.module_name}"
            )
            
            # Subscribe to system health requests
            await self.event_bus.subscribe(
                EventType.SYSTEM_HEALTH_REQUEST.value,
                self._handle_health_event,
                f"gui_testing_health_{self.module_name}"
            )
            
            self.logger.info("GUI testing event subscriptions established")
            
        except Exception as e:
            self.logger.error(f"Failed to setup event subscriptions: {e}")
    
    async def _handle_test_request(self, event: Event):
        """
        Handle GUI test request events
        Event-Bus Compliance: Process test requests via events
        """
        try:
            request_data = event.data
            
            # Map test request to GUI test format
            gui_test_data = {
                'request_type': request_data.get('request_type', 'run_test'),
                'element_ids': request_data.get('element_ids'),
                'test_types': request_data.get('test_types', ['element_validation', 'performance_check']),
                'include_accessibility': request_data.get('include_accessibility', True)
            }
            
            # Process GUI test request
            result = await self.execute_function(gui_test_data)
            
            # Send response via event-bus
            response_event = Event(
                event_type=EventType.MODULE_TEST_RESPONSE.value,
                stream_id=event.stream_id,
                data=result,
                source=self.module_name,
                correlation_id=event.correlation_id
            )
            
            await self.event_bus.publish(response_event)
            self.logger.debug("GUI test response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle test request: {e}")
    
    async def _handle_health_event(self, event: Event):
        """
        Handle system health request events
        Event-Bus Compliance: Respond to health checks via events
        """
        try:
            request_data = event.data
            
            if request_data.get('request_type') == 'gui_testing_health':
                # Calculate GUI testing health metrics
                gui_summary = self.get_gui_testing_summary()
                
                # Respond with GUI testing health status
                health_response = Event(
                    event_type=EventType.SYSTEM_HEALTH_RESPONSE.value,
                    stream_id=f"gui-testing-health-{event.stream_id}",
                    data={
                        'module': 'gui_testing_handler',
                        'status': 'healthy' if gui_summary['average_accessibility_score'] > 70 else 'warning',
                        'total_elements': gui_summary['total_elements'],
                        'average_accessibility_score': gui_summary['average_accessibility_score'],
                        'average_performance_score': gui_summary['average_performance_score'],
                        'performance_budgets_met': gui_summary['performance_budgets_met'],
                        'recent_tests_count': gui_summary['recent_tests_last_hour'],
                        'auto_testing_enabled': gui_summary['auto_testing_enabled'],
                        'last_test_timestamp': max([elem.last_tested for elem in self.gui_elements.values()], default=datetime.now()).isoformat()
                    },
                    source=self.module_name,
                    correlation_id=event.correlation_id
                )
                
                await self.event_bus.publish(health_response)
                self.logger.debug("GUI testing health response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle health event: {e}")
    
    async def process_event(self, event: Event):
        """
        Process incoming events - Event-Bus Compliance
        """
        try:
            if event.event_type == EventType.MODULE_TEST_REQUEST.value:
                await self._handle_test_request(event)
            
            elif event.event_type == EventType.SYSTEM_HEALTH_REQUEST.value:
                await self._handle_health_event(event)
            
            else:
                self.logger.debug(f"Unhandled event type: {event.event_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_type}: {e}")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'gui_testing_handler',
            'description': 'Complete GUI testing and monitoring with performance, accessibility, and compatibility checks',
            'responsibility': 'GUI testing and monitoring logic only',
            'input_parameters': {
                'request_type': 'Required request type (get_elements, get_status, run_test, validate_elements, performance_check)',
                'test_scope': 'Optional test scope (dashboard, market_data, trading, all)',
                'element_filter': 'Optional list of element IDs to test',
                'include_performance': 'Whether to include performance metrics (default: false)',
                'test_depth': 'Test depth level (basic, detailed, comprehensive)',
                'run_accessibility_check': 'Whether to run accessibility check (default: true)',
                'check_responsiveness': 'Whether to check responsive design (default: false)',
                'browser_compatibility': 'Whether to check browser compatibility (default: false)'
            },
            'output_format': {
                'test_successful': 'Whether GUI testing was successful',
                'elements_tested': 'Number of elements tested',
                'elements_passed': 'Number of elements that passed tests',
                'elements_failed': 'Number of elements that failed tests',
                'elements_with_warnings': 'Number of elements with warnings',
                'gui_elements': 'Detailed information about GUI elements',
                'performance_metrics': 'Performance metrics if requested',
                'accessibility_score': 'Overall accessibility score',
                'overall_health_score': 'Overall GUI health score',
                'test_warnings': 'List of test warnings if any',
                'test_timestamp': 'Timestamp of testing operation'
            },
            'supported_request_types': ['get_elements', 'get_status', 'run_test', 'validate_elements', 'performance_check'],
            'supported_test_scopes': ['dashboard', 'market_data', 'trading', 'navigation', 'all'],
            'supported_test_depths': ['basic', 'detailed', 'comprehensive'],
            'testing_configuration': self.testing_config,
            'performance_budgets': self.testing_config['performance_budgets'],
            'browser_support': self.testing_config['browser_compatibility'],
            'responsive_breakpoints': self.testing_config['responsive_breakpoints'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_gui_testing_statistics(self) -> Dict[str, Any]:
        """GUI Testing Handler Module Statistiken"""
        total_tests = len(self.test_history)
        
        if total_tests == 0:
            return {
                'total_tests': 0,
                'total_elements': len(self.gui_elements),
                'auto_testing_enabled': self.testing_config['auto_testing_enabled']
            }
        
        # Success Rate
        successful_tests = sum(1 for t in self.test_history if t['test_successful'])
        success_rate = round((successful_tests / total_tests) * 100, 1) if total_tests > 0 else 0
        
        # Request Type Distribution
        request_type_distribution = {}
        for test in self.test_history:
            req_type = test['request_type']
            request_type_distribution[req_type] = request_type_distribution.get(req_type, 0) + 1
        
        # Test Scope Distribution
        scope_distribution = {}
        for test in self.test_history:
            scope = test['test_scope']
            scope_distribution[scope] = scope_distribution.get(scope, 0) + 1
        
        # Element Status Statistics
        element_stats = {}
        for status in ['pass', 'fail', 'warning', 'not_tested']:
            element_stats[f'elements_{status}'] = sum(1 for e in self.gui_elements.values() if e.test_status == status)
        
        # Average Test Metrics
        avg_elements_tested = sum(t['elements_tested'] for t in self.test_history) / total_tests
        avg_pass_rate = sum(t['elements_passed'] / max(1, t['elements_tested']) for t in self.test_history) / total_tests * 100
        
        # Recent Activity
        recent_tests = [
            t for t in self.test_history
            if (datetime.now() - t['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate_percent': success_rate,
            'recent_tests_last_hour': len(recent_tests),
            'request_type_distribution': dict(sorted(
                request_type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'test_scope_distribution': dict(sorted(
                scope_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'element_statistics': element_stats,
            'average_elements_tested_per_run': round(avg_elements_tested, 1),
            'average_pass_rate_percent': round(avg_pass_rate, 1),
            'total_elements': len(self.gui_elements),
            'auto_testing_enabled': self.testing_config['auto_testing_enabled'],
            'performance_budgets_compliant': await self._check_budgets_compliance(),
            'average_processing_time': self.average_execution_time
        }