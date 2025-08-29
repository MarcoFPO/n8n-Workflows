#!/usr/bin/env python3
"""
Security Configuration - Minimal Implementation
Issue #65 Integration-Fix
"""

from typing import List
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


class SecurityConfig:
    """Security Configuration - Minimal für privaten Gebrauch"""
    
    def __init__(self):
        self.cors_origins = ["*"]  # Privat usage - permissive
        self.allow_credentials = True
        self.allow_methods = ["*"]
        self.allow_headers = ["*"]


class PrivateSecurityMiddleware:
    """Private Security Middleware - Minimal Implementation"""
    
    @staticmethod
    def setup_cors(app: FastAPI, origins: List[str] = None):
        """Setup CORS Middleware"""
        if origins is None:
            origins = ["*"]
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )