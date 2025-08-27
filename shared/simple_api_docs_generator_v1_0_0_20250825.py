#!/usr/bin/env python3
"""
Simplified API Documentation Generator v1.0.0 - 25. August 2025
===============================================================

Optimiert für das Aktienanalyse-Ökosystem mit verbesserter Performance und Timeout-Handling.

Features:
- Service-by-Service Documentation Generation
- Configurable Timeouts
- Health Check Integration  
- Error Resilient Processing
- Clean Architecture Support

Code-Qualität: HÖCHSTE PRIORITÄT - Reliable API Documentation
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceAPIDocumenter:
    """Simplified API Documentation Generator for individual services."""
    
    def __init__(self):
        self.base_url = "http://10.1.1.174"
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        self.output_dir = Path("/tmp/api-docs")
        self.output_dir.mkdir(exist_ok=True)
        
        # Known service configurations  
        self.services = {
            "frontend-service": {"port": 8080, "health_path": "/health"},
            "event-bus-service": {"port": 8014, "health_path": "/health"}, 
            "data-processing-service": {"port": 8013, "health_path": "/health"},
            "core-service": {"port": 8012, "health_path": "/health"},
            "broker-gateway-service": {"port": 8015, "health_path": "/health"}
        }
    
    async def check_service_health(self, service_name: str, config: Dict) -> bool:
        """Check if a service is available and responding."""
        url = f"{self.base_url}:{config['port']}{config['health_path']}"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        logger.info(f"✅ {service_name} is healthy")
                        return True
                    else:
                        logger.warning(f"❌ {service_name} health check failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ {service_name} health check error: {e}")
            return False
    
    async def extract_openapi_spec(self, service_name: str, config: Dict) -> Optional[Dict]:
        """Extract OpenAPI specification from a service."""
        # Try multiple possible OpenAPI endpoints
        openapi_paths = ["/openapi.json", "/docs/openapi.json", "/api/openapi.json"]
        
        for path in openapi_paths:
            url = f"{self.base_url}:{config['port']}{path}"
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            spec = await response.json()
                            logger.info(f"✅ OpenAPI spec extracted from {service_name} at {path}")
                            return spec
            except Exception as e:
                logger.debug(f"Failed to get OpenAPI spec from {url}: {e}")
                continue
        
        logger.warning(f"❌ Could not extract OpenAPI spec from {service_name}")
        return None
    
    async def document_service(self, service_name: str) -> bool:
        """Generate documentation for a single service."""
        logger.info(f"🔍 Processing {service_name}...")
        
        config = self.services.get(service_name)
        if not config:
            logger.error(f"❌ Unknown service: {service_name}")
            return False
        
        # Check service health first
        if not await self.check_service_health(service_name, config):
            return False
        
        # Extract OpenAPI specification
        openapi_spec = await self.extract_openapi_spec(service_name, config)
        if not openapi_spec:
            return False
        
        # Save individual service documentation
        service_doc_file = self.output_dir / f"{service_name}-openapi.json"
        with open(service_doc_file, 'w', encoding='utf-8') as f:
            json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Documentation saved for {service_name}")
        return True
    
    async def generate_consolidated_docs(self) -> Dict:
        """Generate consolidated API documentation for all services."""
        consolidated_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Aktienanalyse-Ökosystem API",
                "description": "Comprehensive API Documentation for Stock Analysis Ecosystem",
                "version": "4.0.0",
                "contact": {
                    "name": "Claude Code Architecture Team",
                    "email": "architecture@aktienanalyse.local"
                }
            },
            "servers": [
                {
                    "url": "http://10.1.1.174:8080",
                    "description": "Production Server - Frontend Service"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "responses": {},
                "parameters": {},
                "securitySchemes": {}
            },
            "tags": []
        }
        
        services_documented = []
        
        # Process each service
        for service_name in self.services:
            success = await self.document_service(service_name)
            if success:
                services_documented.append(service_name)
                
                # Load service spec and merge
                service_doc_file = self.output_dir / f"{service_name}-openapi.json"
                if service_doc_file.exists():
                    with open(service_doc_file, 'r', encoding='utf-8') as f:
                        service_spec = json.load(f)
                    
                    # Merge paths with service prefix
                    if "paths" in service_spec:
                        for path, operations in service_spec["paths"].items():
                            prefixed_path = f"/{service_name.replace('-service', '')}{path}"
                            consolidated_spec["paths"][prefixed_path] = operations
                    
                    # Merge components
                    if "components" in service_spec:
                        for component_type, components in service_spec["components"].items():
                            if component_type in consolidated_spec["components"]:
                                consolidated_spec["components"][component_type].update(components)
                    
                    # Add service tag
                    consolidated_spec["tags"].append({
                        "name": service_name,
                        "description": f"API endpoints for {service_name}"
                    })
        
        # Save consolidated documentation
        consolidated_file = self.output_dir / "aktienanalyse-consolidated-openapi.json"
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated_spec, f, indent=2, ensure_ascii=False)
        
        # Generate summary report
        summary = {
            "generation_timestamp": datetime.now().isoformat(),
            "services_documented": services_documented,
            "total_services": len(self.services),
            "success_rate": f"{len(services_documented)}/{len(self.services)}",
            "output_files": [
                str(consolidated_file),
                *[str(self.output_dir / f"{service}-openapi.json") for service in services_documented]
            ]
        }
        
        summary_file = self.output_dir / "documentation-summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"🎉 Documentation generation complete!")
        logger.info(f"✅ Services documented: {len(services_documented)}/{len(self.services)}")
        logger.info(f"📁 Output directory: {self.output_dir}")
        
        return summary

async def main():
    """Main entry point for API documentation generation."""
    logger.info("🚀 Starting Simplified API Documentation Generation")
    
    documenter = ServiceAPIDocumenter()
    summary = await documenter.generate_consolidated_docs()
    
    print("\n" + "="*60)
    print("📊 API DOCUMENTATION GENERATION SUMMARY")
    print("="*60)
    print(f"Services documented: {summary['success_rate']}")
    print(f"Generation time: {summary['generation_timestamp']}")
    print(f"Output directory: /tmp/api-docs/")
    print("\nGenerated files:")
    for file_path in summary['output_files']:
        print(f"  - {file_path}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())