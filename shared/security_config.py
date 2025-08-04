#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Security Configuration für aktienanalyse-ökosystem
Private Anwendung - pragmatische aber sichere Konfiguration
"""

import os
from typing import List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv('/opt/aktienanalyse-ökosystem/.env')

class SecurityConfig:
    """Zentrale Security-Konfiguration für private Anwendung"""
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Gibt CORS Origins für private Nutzung zurück"""
        cors_origins = os.getenv(
            'CORS_ORIGINS', 
            'https://10.1.1.174,http://10.1.1.174:8005,http://localhost:3000'
        )
        return [origin.strip() for origin in cors_origins.split(',')]
    
    @staticmethod
    def get_cors_middleware() -> CORSMiddleware:
        """Erstellt CORS-Middleware für private Anwendung"""
        return CORSMiddleware(
            allow_origins=SecurityConfig.get_cors_origins(),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
    
    @staticmethod
    def get_postgres_url() -> str:
        """Postgres URL aus Environment Variables"""
        return os.getenv(
            'POSTGRES_URL',
            'postgresql://aktienanalyse:ak7_s3cur3_db_2025@localhost:5432/aktienanalyse_events?sslmode=disable'
        )
    
    @staticmethod
    def get_redis_url() -> str:
        """Redis URL aus Environment Variables"""
        return os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    
    @staticmethod
    def get_rabbitmq_url() -> str:
        """RabbitMQ URL aus Environment Variables"""
        return os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
    
    @staticmethod
    def get_api_secret() -> str:
        """API Secret aus Environment Variables"""
        return os.getenv('API_SECRET', 'ak7_pr1v4t3_4p1_k3y_2025_m4x_s3cur3')
    
    @staticmethod
    def get_service_port(service_name: str) -> int:
        """Service Port aus Environment Variables"""
        port_mapping = {
            'frontend': int(os.getenv('FRONTEND_PORT', 8005)),
            'intelligent_core': int(os.getenv('INTELLIGENT_CORE_PORT', 8011)),
            'broker_gateway': int(os.getenv('BROKER_GATEWAY_PORT', 8012)),
            'diagnostic': int(os.getenv('DIAGNOSTIC_PORT', 8013)),
            'event_bus': int(os.getenv('EVENT_BUS_PORT', 8014)),
            'monitoring': int(os.getenv('MONITORING_PORT', 8015))
        }
        return port_mapping.get(service_name, 8000)
    
    @staticmethod
    def is_debug_mode() -> bool:
        """Debug Mode aus Environment Variables"""
        return os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    @staticmethod
    def get_log_level() -> str:
        """Log Level aus Environment Variables"""
        return os.getenv('LOG_LEVEL', 'INFO')


class PrivateSecurityMiddleware:
    """Middleware für private Anwendung - weniger restriktiv"""
    
    @staticmethod
    def setup_cors(app):
        """Setup CORS für private Anwendung"""
        app.add_middleware(SecurityConfig.get_cors_middleware())
        return app
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Einfache API-Key-Validierung für private Anwendung"""
        # Für private Anwendung: Optionale Validierung
        if not os.getenv('ENABLE_API_KEY_AUTH', 'false').lower() == 'true':
            return True
        
        expected_key = SecurityConfig.get_api_secret()
        return api_key == expected_key


# Backwards compatibility
def get_cors_middleware():
    """Legacy-Funktion für Backwards Compatibility"""
    return SecurityConfig.get_cors_middleware()

def get_postgres_url():
    """Legacy-Funktion für Backwards Compatibility"""
    return SecurityConfig.get_postgres_url()