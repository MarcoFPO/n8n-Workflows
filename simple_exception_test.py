#!/usr/bin/env python3
"""
Simple Exception-Framework Test
Grundlegende Tests für die Exception-Implementation
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

def test_basic_exception():
    """Test basic exception creation"""
    from shared.exceptions import ValidationException, ErrorCategory, ErrorSeverity
    
    exc = ValidationException("Test error")
    print(f"Message: {exc.message}")
    print(f"Category: {exc.category}")
    print(f"Severity: {exc.severity}")
    print(f"HTTP Status: {exc.http_status_code}")
    print(f"Has category attribute: {hasattr(exc, 'category')}")
    print(f"Category value: {exc.category.value}")
    
    # Test to_dict
    error_dict = exc.to_dict()
    print(f"Error dict keys: {list(error_dict.keys())}")
    
    return True

def test_database_exception():
    """Test database exception"""
    from shared.exceptions import ConnectionException
    
    exc = ConnectionException("DB connection failed")
    print(f"DB Exception - Message: {exc.message}")
    print(f"DB Exception - Category: {exc.category}")
    print(f"DB Exception - HTTP Status: {exc.http_status_code}")
    
    return True

if __name__ == "__main__":
    print("=== Basic Exception Test ===")
    test_basic_exception()
    print("\n=== Database Exception Test ===")
    test_database_exception()
    print("\n✅ Basic tests completed")