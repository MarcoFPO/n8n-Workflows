#!/usr/bin/env python3
"""
HTML Template Service - Presentation Layer
Frontend Service Clean Architecture v1.0.0

PRESENTATION LAYER - TEMPLATE SERVICE:
- HTML Template Generation Implementation
- Bootstrap 5 UI Components
- Responsive Design Templates
- Theme Support

CLEAN ARCHITECTURE PRINCIPLES:
- Implements ITemplateService Interface
- Single Responsibility: Only template rendering
- No Business Logic: Pure presentation concern

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ...application.interfaces.template_service_interface import (
    ITemplateService, 
    TemplateType, 
    TemplateTheme,
    TemplateRenderError,
    TemplateNotFoundError
)


logger = logging.getLogger(__name__)


class HTMLTemplateService(ITemplateService):
    """
    HTML Template Service Implementation
    
    RESPONSIBILITIES:
    - Generate HTML templates with Bootstrap 5
    - Provide responsive UI components
    - Support multiple themes
    - Cache templates for performance
    
    DESIGN PATTERNS:
    - Template Method Pattern: Base template with customizable content
    - Factory Pattern: Create different template types
    - Builder Pattern: Build complex templates step by step
    """
    
    def __init__(self, version: str = "1.0.0", theme: str = "default"):
        """
        Initialize HTML Template Service
        
        Args:
            version: Service version for template metadata
            theme: Default theme for templates
        """
        self._version = version
        self._default_theme = theme
        self._template_cache: Dict[str, str] = {}
        self._is_initialized = False
        
        logger.info(f"HTML Template Service initialized - version: {version}, theme: {theme}")
    
    async def initialize(self) -> None:
        """Initialize template service"""
        if self._is_initialized:
            return
        
        # Pre-compile common template components
        await self._precompile_common_templates()
        
        self._is_initialized = True
        logger.info("HTML Template Service initialization completed")
    
    async def render_base_template(self, 
                                 title: str, 
                                 content: str,
                                 theme: TemplateTheme = TemplateTheme.DEFAULT,
                                 meta_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Render base HTML template
        
        Args:
            title: Page title
            content: Page content HTML
            theme: Template theme
            meta_data: Additional metadata
            
        Returns:
            Complete HTML page as string
        """
        try:
            logger.debug(f"Rendering base template: {title}")
            
            # Generate theme-specific CSS classes
            theme_classes = self._get_theme_classes(theme)
            
            # Build navigation menu
            nav_menu = self._build_navigation_menu()
            
            # Build header section
            header_section = self._build_header_section(title)
            
            # Build footer section
            footer_section = self._build_footer_section()
            
            # Compose complete HTML page
            html_page = f"""
            <!DOCTYPE html>
            <html lang="de" class="{theme_classes['html']}">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title} - Frontend Service v{self._version}</title>
                
                <!-- Bootstrap 5 CSS -->
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                
                <!-- Custom CSS -->
                <style>
                    {self._get_custom_css(theme)}
                </style>
                
                <!-- Custom JavaScript -->
                <script>
                    {self._get_custom_javascript()}
                </script>
            </head>
            <body class="{theme_classes['body']}">
                <div class="container-fluid">
                    {header_section}
                    {nav_menu}
                    <main class="content-main py-4">
                        {content}
                    </main>
                    {footer_section}
                </div>
                
                <!-- Bootstrap 5 JavaScript -->
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
            </body>
            </html>
            """
            
            logger.debug(f"Base template rendered successfully: {len(html_page)} characters")
            return html_page
            
        except Exception as e:
            logger.error(f"Base template rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render base template: {str(e)}")
    
    async def render_dashboard_template(self,
                                      dashboard_data: Dict[str, Any],
                                      theme: TemplateTheme = TemplateTheme.DEFAULT) -> str:
        """
        Render dashboard template with data
        
        Args:
            dashboard_data: Dashboard data for rendering
            theme: Template theme
            
        Returns:
            Dashboard HTML page
        """
        try:
            logger.debug("Rendering dashboard template")
            
            # Extract dashboard information
            dashboard_info = dashboard_data.get('dashboard_info', {})
            health_analysis = dashboard_data.get('health_analysis', {})
            services = dashboard_data.get('services', {})
            
            # Build dashboard content sections
            overview_section = self._build_dashboard_overview(health_analysis)
            services_section = self._build_services_grid(services.get('service_cards', []))
            metrics_section = self._build_metrics_section(health_analysis)
            
            # Compose dashboard content
            dashboard_content = f"""
                <h2 class="mb-4">
                    <i class="fas fa-tachometer-alt text-primary"></i>
                    Dashboard - System Overview
                </h2>
                
                {overview_section}
                {metrics_section}
                {services_section}
                
                <div class="alert alert-info mt-4">
                    <h5><i class="fas fa-info-circle"></i> Clean Architecture v1.0.0</h5>
                    <ul class="mb-0">
                        <li><strong>Migration Status:</strong> God Object (1,500 lines) → Clean Architecture</li>
                        <li><strong>Pattern:</strong> 4-Layer Architecture (Domain/Application/Infrastructure/Presentation)</li>
                        <li><strong>Service:</strong> {dashboard_info.get('version', 'N/A')}</li>
                    </ul>
                </div>
            """
            
            # Render complete page
            return await self.render_base_template(
                title="Dashboard",
                content=dashboard_content,
                theme=theme
            )
            
        except Exception as e:
            logger.error(f"Dashboard template rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render dashboard template: {str(e)}")
    
    async def render_data_table(self,
                               headers: List[str],
                               rows: List[List[Any]], 
                               table_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Render data table HTML
        
        Args:
            headers: Table column headers
            rows: Table data rows
            table_config: Table configuration
            
        Returns:
            HTML table as string
        """
        try:
            config = table_config or {}
            
            # Table CSS classes
            table_classes = [
                "table",
                "table-striped" if config.get("striped", True) else "",
                "table-hover" if config.get("hover", True) else "",
                "table-responsive" if config.get("responsive", True) else ""
            ]
            
            # Build table header
            header_html = "<thead class='table-dark'><tr>"
            for header in headers:
                header_html += f"<th scope='col'>{header}</th>"
            header_html += "</tr></thead>"
            
            # Build table body
            body_html = "<tbody>"
            for row in rows:
                body_html += "<tr>"
                for cell in row:
                    body_html += f"<td>{cell}</td>"
                body_html += "</tr>"
            body_html += "</tbody>"
            
            # Complete table
            table_html = f"""
                <div class="table-responsive">
                    <table class="{' '.join(filter(None, table_classes))}">
                        {header_html}
                        {body_html}
                    </table>
                </div>
            """
            
            logger.debug(f"Data table rendered: {len(headers)} columns, {len(rows)} rows")
            return table_html
            
        except Exception as e:
            logger.error(f"Data table rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render data table: {str(e)}")
    
    async def render_timeframe_selector(self,
                                      current_timeframe: str,
                                      available_timeframes: List[Dict[str, Any]],
                                      endpoint: str) -> str:
        """
        Render timeframe selector UI component
        
        Args:
            current_timeframe: Currently selected timeframe
            available_timeframes: List of available timeframes
            endpoint: Target endpoint for timeframe changes
            
        Returns:
            Timeframe selector HTML
        """
        try:
            buttons_html = ""
            
            for timeframe in available_timeframes:
                code = timeframe.get('code', '')
                display_name = timeframe.get('display_name', code)
                icon = timeframe.get('icon', '📊')
                
                is_active = code == current_timeframe
                btn_class = "btn-primary" if is_active else "btn-outline-primary"
                
                buttons_html += f"""
                    <button type="button" 
                            class="btn {btn_class} mx-1" 
                            onclick="window.location.href='{endpoint}?timeframe={code}'">
                        {icon} {display_name}
                    </button>
                """
            
            selector_html = f"""
                <div class="timeframe-selector mb-4">
                    <h5><i class="fas fa-clock text-primary"></i> Zeitraum auswählen</h5>
                    <div class="btn-group-custom">
                        {buttons_html}
                    </div>
                </div>
            """
            
            return selector_html
            
        except Exception as e:
            logger.error(f"Timeframe selector rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render timeframe selector: {str(e)}")
    
    async def render_navigation_controls(self,
                                       navigation_data: Dict[str, Any],
                                       endpoint: str) -> str:
        """
        Render navigation controls (previous/next)
        
        Args:
            navigation_data: Navigation period data
            endpoint: Target endpoint for navigation
            
        Returns:
            Navigation controls HTML
        """
        try:
            previous = navigation_data.get('previous', '')
            current = navigation_data.get('current', '')
            next_date = navigation_data.get('next', '')
            nav_info = navigation_data.get('info', 'Navigation')
            
            navigation_html = f"""
                <div class="navigation-controls mb-4 p-3 bg-light rounded">
                    <div class="row align-items-center">
                        <div class="col-md-4">
                            <button class="btn btn-secondary" 
                                    onclick="navigateToDate('previous', '{endpoint}')">
                                <i class="fas fa-chevron-left"></i> {previous}
                            </button>
                        </div>
                        <div class="col-md-4 text-center">
                            <strong>{nav_info}</strong><br>
                            <span class="text-primary fs-5">{current}</span>
                        </div>
                        <div class="col-md-4 text-end">
                            <button class="btn btn-primary" 
                                    onclick="navigateToDate('next', '{endpoint}')">
                                {next_date} <i class="fas fa-chevron-right"></i>
                            </button>
                        </div>
                    </div>
                </div>
            """
            
            return navigation_html
            
        except Exception as e:
            logger.error(f"Navigation controls rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render navigation controls: {str(e)}")
    
    async def render_service_status_card(self, service_data: Dict[str, Any]) -> str:
        """
        Render service status card
        
        Args:
            service_data: Service status information
            
        Returns:
            Service status card HTML
        """
        try:
            name = service_data.get('name', 'Unknown Service')
            status = service_data.get('status', 'unknown')
            status_icon = service_data.get('status_icon', '❓')
            url = service_data.get('url', '#')
            port = service_data.get('port', 'N/A')
            response_time = service_data.get('response_time', 'N/A')
            is_critical = service_data.get('is_critical', False)
            
            # Determine card styling based on status
            status_color = {
                'active': 'success',
                'inactive': 'danger', 
                'degraded': 'warning',
                'maintenance': 'info'
            }.get(status, 'secondary')
            
            critical_badge = '<span class="badge bg-danger ms-2">Critical</span>' if is_critical else ''
            
            card_html = f"""
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card border-{status_color}">
                        <div class="card-header bg-{status_color} text-white">
                            <h6 class="card-title mb-0">
                                {status_icon} {name} {critical_badge}
                            </h6>
                        </div>
                        <div class="card-body">
                            <p class="card-text">
                                <strong>URL:</strong> <code>{url}</code><br>
                                <strong>Port:</strong> {port}<br>
                                <strong>Response Time:</strong> {response_time}
                            </p>
                        </div>
                    </div>
                </div>
            """
            
            return card_html
            
        except Exception as e:
            logger.error(f"Service status card rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render service status card: {str(e)}")
    
    async def render_alert_message(self,
                                 message: str,
                                 alert_type: str = "info",
                                 dismissible: bool = True) -> str:
        """
        Render alert message component
        
        Args:
            message: Alert message text
            alert_type: Type of alert
            dismissible: Whether alert can be dismissed
            
        Returns:
            Alert message HTML
        """
        try:
            # Map alert types to Bootstrap classes
            alert_class = {
                'info': 'alert-info',
                'warning': 'alert-warning', 
                'error': 'alert-danger',
                'success': 'alert-success'
            }.get(alert_type, 'alert-info')
            
            # Add dismissible functionality
            dismissible_class = " alert-dismissible" if dismissible else ""
            dismiss_button = """
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            """ if dismissible else ""
            
            alert_html = f"""
                <div class="alert {alert_class}{dismissible_class}" role="alert">
                    {message}
                    {dismiss_button}
                </div>
            """
            
            return alert_html
            
        except Exception as e:
            logger.error(f"Alert message rendering failed: {str(e)}")
            raise TemplateRenderError(f"Failed to render alert message: {str(e)}")
    
    # ==========================================================================
    # PRIVATE HELPER METHODS
    # ==========================================================================
    
    async def _precompile_common_templates(self) -> None:
        """Pre-compile commonly used template components"""
        # Pre-compile navigation, header, footer templates
        # This could be extended with actual template compilation
        pass
    
    def _get_theme_classes(self, theme: TemplateTheme) -> Dict[str, str]:
        """Get CSS classes for theme"""
        if theme == TemplateTheme.DARK:
            return {
                'html': 'dark-theme',
                'body': 'bg-dark text-light'
            }
        elif theme == TemplateTheme.HIGH_CONTRAST:
            return {
                'html': 'high-contrast-theme',
                'body': 'high-contrast'
            }
        else:
            return {
                'html': 'default-theme',
                'body': 'bg-light'
            }
    
    def _build_navigation_menu(self) -> str:
        """Build navigation menu HTML"""
        nav_items = [
            ('/', 'fas fa-home', 'Dashboard'),
            ('/prognosen', 'fas fa-chart-line', 'KI-Prognosen'),
            ('/vergleichsanalyse', 'fas fa-balance-scale', 'SOLL-IST Vergleich'),
            ('/depot', 'fas fa-briefcase', 'Depot-Analyse'),
            ('/prediction-averages', 'fas fa-chart-bar', 'Vorhersage-Mittelwerte'),
            ('/system', 'fas fa-cog', 'System-Status'),
            ('/docs', 'fas fa-book', 'API Docs')
        ]
        
        nav_html = '<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4"><div class="container-fluid">'
        nav_html += '<div class="navbar-nav">'
        
        for url, icon, title in nav_items:
            nav_html += f'<a class="nav-link" href="{url}"><i class="{icon}"></i> {title}</a>'
        
        nav_html += '</div></div></nav>'
        return nav_html
    
    def _build_header_section(self, title: str) -> str:
        """Build header section HTML"""
        return f"""
            <header class="bg-gradient bg-primary text-white py-4 mb-4 rounded">
                <div class="container-fluid">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h1 class="display-6"><i class="fas fa-rocket"></i> {title}</h1>
                            <p class="lead mb-0">Frontend Service Clean Architecture v{self._version}</p>
                        </div>
                        <div class="col-md-4 text-end">
                            <small class="opacity-75">
                                <i class="fas fa-clock"></i> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
                            </small>
                        </div>
                    </div>
                </div>
            </header>
        """
    
    def _build_footer_section(self) -> str:
        """Build footer section HTML"""
        return f"""
            <footer class="bg-dark text-light py-4 mt-5 rounded">
                <div class="container-fluid text-center">
                    <p class="mb-0">
                        🤖 Generated with 
                        <a href="https://claude.ai/code" class="text-info">Claude Code</a> | 
                        Clean Architecture v{self._version} | 
                        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </footer>
        """
    
    def _build_dashboard_overview(self, health_analysis: Dict[str, Any]) -> str:
        """Build dashboard overview section"""
        overall_score = health_analysis.get('overall_score', 0.0)
        status_indicator = health_analysis.get('status_indicator', '❓ Unknown')
        
        return f"""
            <div class="row mb-4">
                <div class="col-md-12">
                    <div class="alert alert-primary">
                        <h4><i class="fas fa-heartbeat"></i> System Health: {status_indicator}</h4>
                        <div class="progress mb-2">
                            <div class="progress-bar" style="width: {overall_score*100:.1f}%"></div>
                        </div>
                        <small>Overall Health Score: {overall_score:.2f}</small>
                    </div>
                </div>
            </div>
        """
    
    def _build_services_grid(self, service_cards: List[Dict[str, Any]]) -> str:
        """Build services grid section"""
        if not service_cards:
            return '<div class="alert alert-warning">No services configured</div>'
        
        services_html = '<h3 class="mb-3"><i class="fas fa-server"></i> Services Status</h3><div class="row">'
        
        for service in service_cards:
            services_html += f"""
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">
                                {service.get('status_icon', '📊')} {service.get('name', 'Unknown')}
                            </h5>
                            <p class="card-text">
                                Status: <span class="badge bg-{service.get('status_color', 'secondary')}">{service.get('status', 'unknown')}</span><br>
                                Response: {service.get('response_time', 'N/A')}<br>
                                Port: {service.get('port', 'N/A')}
                            </p>
                        </div>
                    </div>
                </div>
            """
        
        services_html += '</div>'
        return services_html
    
    def _build_metrics_section(self, health_analysis: Dict[str, Any]) -> str:
        """Build metrics section"""
        return """
            <div class="alert alert-info">
                <h5><i class="fas fa-chart-bar"></i> System Metrics</h5>
                <p>Detailed system metrics and performance indicators will be displayed here.</p>
            </div>
        """
    
    def _get_custom_css(self, theme: TemplateTheme) -> str:
        """Get custom CSS for theme"""
        return """
            .content-main { min-height: 500px; }
            .service-card { transition: transform 0.2s; }
            .service-card:hover { transform: translateY(-2px); }
            .navigation-controls button { min-width: 120px; }
            .timeframe-selector .btn { margin: 2px; }
        """
    
    def _get_custom_javascript(self) -> str:
        """Get custom JavaScript functions"""
        return """
            function navigateToDate(direction, endpoint) {
                // Navigation functionality
                const timestamp = Math.floor(Date.now() / 1000);
                const url = new URL(window.location);
                url.searchParams.set('nav_timestamp', timestamp);
                url.searchParams.set('nav_direction', direction);
                window.location.href = url.toString();
            }
        """