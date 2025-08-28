#!/usr/bin/env python3
"""
Dashboard Domain Service - Domain Layer
Frontend Service Clean Architecture v1.0.0

DOMAIN LAYER - DOMAIN SERVICES:
- Dashboard Business Logic Orchestration
- Cross-Entity Business Rules  
- Complex Domain Operations

CLEAN ARCHITECTURE PRINCIPLES:
- Domain Service Pattern: Complex business logic
- Single Responsibility: Dashboard domain coordination
- No Infrastructure Dependencies: Pure domain logic

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from ..entities.dashboard_entity import DashboardEntity, ServiceInfo, ServiceHealth
from ..value_objects.timeframe_vo import TimeframeValueObject, NavigationPeriod


class DashboardHealthAnalyzer:
    """
    Dashboard Health Analysis Domain Service
    
    BUSINESS RULES:
    - Service health evaluation algorithms
    - Performance threshold calculations
    - Health scoring and trending
    """
    
    @staticmethod
    def calculate_system_health_score(services: List[ServiceInfo]) -> float:
        """
        Calculate overall system health score
        
        BUSINESS RULE: Weighted health scoring based on service criticality
        - Active services: 1.0 points
        - Degraded services: 0.6 points  
        - Maintenance services: 0.4 points
        - Inactive services: 0.0 points
        """
        if not services:
            return 0.0
        
        # Service criticality weights (could be configurable)
        critical_services = {"ml-analytics", "data-processing", "event-bus"}
        
        total_weight = 0
        total_score = 0
        
        for service in services:
            # Determine service weight (critical services weighted higher)
            weight = 2.0 if service.name.lower() in critical_services else 1.0
            
            # Calculate service score
            if service.status == ServiceHealth.ACTIVE:
                service_score = 1.0
            elif service.status == ServiceHealth.DEGRADED:
                service_score = 0.6
            elif service.status == ServiceHealth.MAINTENANCE:
                service_score = 0.4
            else:  # INACTIVE
                service_score = 0.0
            
            # Add response time penalty for active services
            if service.status == ServiceHealth.ACTIVE and service.response_time_ms:
                if service.response_time_ms > 5000:  # >5s response time
                    service_score *= 0.7
                elif service.response_time_ms > 2000:  # >2s response time
                    service_score *= 0.85
            
            total_score += service_score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def identify_critical_issues(services: List[ServiceInfo]) -> List[Dict[str, Any]]:
        """
        Identify critical system issues
        
        BUSINESS RULE: Critical issues requiring immediate attention
        """
        issues = []
        
        # Check for inactive services
        inactive_services = [s for s in services if s.status == ServiceHealth.INACTIVE]
        if inactive_services:
            issues.append({
                "type": "service_down",
                "severity": "critical",
                "message": f"{len(inactive_services)} service(s) are down",
                "services": [s.name for s in inactive_services],
                "action_required": True
            })
        
        # Check for slow response times
        slow_services = [s for s in services 
                        if s.status == ServiceHealth.ACTIVE 
                        and s.response_time_ms and s.response_time_ms > 10000]
        if slow_services:
            issues.append({
                "type": "performance_degradation", 
                "severity": "warning",
                "message": f"{len(slow_services)} service(s) responding slowly",
                "services": [s.name for s in slow_services],
                "action_required": False
            })
        
        # Check for services in maintenance too long
        now = datetime.now()
        long_maintenance = [s for s in services
                          if s.status == ServiceHealth.MAINTENANCE
                          and (now - s.last_check).total_seconds() > 3600]  # >1 hour
        if long_maintenance:
            issues.append({
                "type": "extended_maintenance",
                "severity": "warning", 
                "message": f"{len(long_maintenance)} service(s) in extended maintenance",
                "services": [s.name for s in long_maintenance],
                "action_required": False
            })
        
        return issues
    
    @staticmethod
    def get_health_trend_indicator(current_score: float, previous_scores: List[float]) -> str:
        """
        Get health trend indicator
        
        BUSINESS RULE: Trend analysis over time
        """
        if not previous_scores:
            return "stable"
        
        recent_avg = sum(previous_scores[-3:]) / min(3, len(previous_scores))
        
        if current_score > recent_avg * 1.1:
            return "improving"
        elif current_score < recent_avg * 0.9:
            return "declining"
        else:
            return "stable"


class DashboardOrchestrationService:
    """
    Dashboard Orchestration Domain Service
    
    BUSINESS RULES:
    - Dashboard state coordination
    - Service integration orchestration
    - Business flow management
    """
    
    def __init__(self):
        self._health_analyzer = DashboardHealthAnalyzer()
    
    def prepare_dashboard_state(self, 
                              dashboard: DashboardEntity,
                              timeframe: TimeframeValueObject) -> Dict[str, Any]:
        """
        Prepare complete dashboard state
        
        BUSINESS RULE: Aggregates all dashboard information for presentation
        """
        # Get basic dashboard metrics
        status_summary = dashboard.get_status_summary()
        
        # Get navigation periods for timeframe
        nav_periods = timeframe.calculate_navigation_periods()
        
        # Analyze system health
        services_list = list(dashboard.services.values())
        health_score = self._health_analyzer.calculate_system_health_score(services_list)
        critical_issues = self._health_analyzer.identify_critical_issues(services_list)
        
        # Prepare service cards data
        service_cards = self._prepare_service_cards(services_list)
        
        return {
            "dashboard_info": {
                "id": dashboard.dashboard_id,
                "version": dashboard.version,
                "status": status_summary,
                "last_updated": status_summary["last_updated"]
            },
            "timeframe_info": {
                "current": timeframe.to_dict(),
                "navigation": {
                    "previous": nav_periods.previous_formatted,
                    "current": nav_periods.current_formatted,
                    "next": nav_periods.next_formatted,
                    "info": nav_periods.navigation_info
                }
            },
            "health_analysis": {
                "overall_score": health_score,
                "health_percentage": status_summary["health_percentage"],
                "status_indicator": self._get_status_indicator(health_score),
                "critical_issues": critical_issues,
                "requires_attention": len(critical_issues) > 0
            },
            "services": {
                "total_count": len(services_list),
                "service_cards": service_cards,
                "healthy_services": dashboard.get_healthy_services(),
                "critical_services": dashboard.get_critical_services()
            }
        }
    
    def validate_dashboard_update(self, 
                                dashboard: DashboardEntity,
                                service_updates: List[Dict[str, Any]]) -> List[str]:
        """
        Validate dashboard update operations
        
        BUSINESS RULE: Validate service updates before applying
        """
        validation_errors = []
        
        for update in service_updates:
            service_name = update.get("service_name")
            status = update.get("status")
            
            # Validate service exists
            if not dashboard.get_service(service_name):
                validation_errors.append(f"Service {service_name} not found")
                continue
            
            # Validate status is valid
            try:
                ServiceHealth(status)
            except ValueError:
                validation_errors.append(f"Invalid status {status} for service {service_name}")
                continue
            
            # Business rule: Cannot set critical services to inactive without confirmation
            if (service_name.lower() in {"ml-analytics", "data-processing", "event-bus"} 
                and status == ServiceHealth.INACTIVE.value):
                validation_errors.append(
                    f"Critical service {service_name} cannot be set inactive without override"
                )
        
        return validation_errors
    
    def _prepare_service_cards(self, services: List[ServiceInfo]) -> List[Dict[str, Any]]:
        """Prepare service cards data for UI"""
        cards = []
        
        for service in services:
            # Determine card styling
            if service.status == ServiceHealth.ACTIVE:
                card_class = "service-card-healthy"
                status_icon = "✅"
                status_color = "green"
            elif service.status == ServiceHealth.DEGRADED:
                card_class = "service-card-warning" 
                status_icon = "⚠️"
                status_color = "orange"
            elif service.status == ServiceHealth.MAINTENANCE:
                card_class = "service-card-maintenance"
                status_icon = "🔧"
                status_color = "blue"
            else:  # INACTIVE
                card_class = "service-card-critical"
                status_icon = "❌" 
                status_color = "red"
            
            # Format response time
            response_time_text = "N/A"
            if service.response_time_ms:
                if service.response_time_ms < 1000:
                    response_time_text = f"{service.response_time_ms}ms"
                else:
                    response_time_text = f"{service.response_time_ms/1000:.1f}s"
            
            cards.append({
                "name": service.name,
                "url": service.url,
                "port": service.port,
                "status": service.status.value,
                "status_icon": status_icon,
                "status_color": status_color,
                "card_class": card_class,
                "response_time": response_time_text,
                "last_check": service.last_check.strftime("%H:%M:%S"),
                "error_message": service.error_message,
                "is_critical": service.name.lower() in {"ml-analytics", "data-processing", "event-bus"}
            })
        
        return cards
    
    def _get_status_indicator(self, health_score: float) -> str:
        """Get status indicator based on health score"""
        if health_score >= 0.9:
            return "🟢 Excellent"
        elif health_score >= 0.7:
            return "🟡 Good"
        elif health_score >= 0.5:
            return "🟠 Warning"
        else:
            return "🔴 Critical"


class DashboardBusinessRules:
    """
    Dashboard Business Rules Service
    
    BUSINESS RULES:
    - Domain-specific validation rules
    - Business constraints enforcement
    - Policy implementation
    """
    
    # Business Constants
    MIN_HEALTHY_SERVICES_PERCENTAGE = 80
    MAX_RESPONSE_TIME_MS = 5000
    MAX_MAINTENANCE_DURATION_HOURS = 2
    CRITICAL_SERVICES = {"ml-analytics", "data-processing", "event-bus", "frontend"}
    
    @classmethod
    def validate_service_health_requirements(cls, services: List[ServiceInfo]) -> List[str]:
        """
        Validate service health against business requirements
        
        BUSINESS RULE: System must maintain minimum service levels
        """
        violations = []
        
        if not services:
            violations.append("No services configured - minimum 1 service required")
            return violations
        
        # Check minimum healthy services percentage
        active_services = [s for s in services if s.status == ServiceHealth.ACTIVE]
        health_percentage = (len(active_services) / len(services)) * 100
        
        if health_percentage < cls.MIN_HEALTHY_SERVICES_PERCENTAGE:
            violations.append(
                f"Service health {health_percentage:.1f}% below minimum {cls.MIN_HEALTHY_SERVICES_PERCENTAGE}%"
            )
        
        # Check critical services are active
        for service in services:
            if (service.name.lower() in cls.CRITICAL_SERVICES 
                and service.status == ServiceHealth.INACTIVE):
                violations.append(f"Critical service {service.name} is inactive")
        
        # Check response times
        for service in services:
            if (service.status == ServiceHealth.ACTIVE 
                and service.response_time_ms 
                and service.response_time_ms > cls.MAX_RESPONSE_TIME_MS):
                violations.append(
                    f"Service {service.name} response time {service.response_time_ms}ms exceeds limit"
                )
        
        return violations
    
    @classmethod
    def can_service_go_to_maintenance(cls, service_name: str, 
                                    other_services: List[ServiceInfo]) -> Tuple[bool, str]:
        """
        Check if service can go to maintenance
        
        BUSINESS RULE: Critical services require redundancy before maintenance
        """
        if service_name.lower() not in cls.CRITICAL_SERVICES:
            return True, "Non-critical service can go to maintenance"
        
        # Check if other critical services are healthy
        other_critical_active = [
            s for s in other_services 
            if (s.name.lower() in cls.CRITICAL_SERVICES 
                and s.name != service_name
                and s.status == ServiceHealth.ACTIVE)
        ]
        
        if len(other_critical_active) >= 2:  # At least 2 other critical services active
            return True, "Sufficient redundancy for maintenance"
        else:
            return False, f"Insufficient redundancy - only {len(other_critical_active)} other critical services active"
    
    @classmethod
    def get_maintenance_time_limit(cls, service_name: str) -> timedelta:
        """
        Get maintenance time limit for service
        
        BUSINESS RULE: Critical services have shorter maintenance windows
        """
        if service_name.lower() in cls.CRITICAL_SERVICES:
            return timedelta(hours=1)  # 1 hour for critical services
        else:
            return timedelta(hours=cls.MAX_MAINTENANCE_DURATION_HOURS)  # 2 hours for others