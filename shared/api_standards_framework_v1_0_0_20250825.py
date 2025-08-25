#!/usr/bin/env python3
"""
API Standards Framework v1.0.0 - Clean Architecture
Einheitliche API-Standards für alle Services im Aktienanalyse-Ökosystem

SHARED INFRASTRUCTURE - API STANDARDIZATION:
- Konsistente URL-Strukturen und Namenskonventionen
- Einheitliche HTTP-Methoden und Status Codes
- Standardisierte Request/Response Patterns
- API Versioning Strategies
- OpenAPI/Swagger Documentation Standards

DESIGN PATTERNS IMPLEMENTIERT:
- Template Method Pattern: Standardisierte API-Struktur
- Strategy Pattern: Verschiedene Versioning-Strategien
- Builder Pattern: API Endpoint Construction
- Factory Pattern: Response DTO Creation

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 1.0.0
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Type
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, Path, Body, status
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


# =============================================================================
# API STANDARDS CONFIGURATION
# =============================================================================

class APIVersionStrategy(Enum):
    """API Versioning Strategies"""
    URL_PATH = "url_path"          # /api/v1/resource
    HEADER = "header"              # Accept: application/vnd.api+json;version=1
    QUERY_PARAM = "query_param"    # /api/resource?version=1
    SUBDOMAIN = "subdomain"        # v1.api.domain.com


@dataclass
class APIStandards:
    """API Standards Configuration"""
    
    # Versioning
    version_strategy: APIVersionStrategy = APIVersionStrategy.URL_PATH
    current_version: str = "v1"
    supported_versions: List[str] = None
    
    # URL Patterns
    base_path: str = "/api"
    health_endpoint: str = "/health"
    status_endpoint: str = "/status"
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    page_param: str = "page"
    size_param: str = "size"
    
    # Filtering and Sorting
    filter_prefix: str = "filter_"
    sort_param: str = "sort"
    order_param: str = "order"
    
    # Response Format
    include_metadata: bool = True
    include_pagination_info: bool = True
    include_timing_info: bool = True
    
    def __post_init__(self):
        if self.supported_versions is None:
            self.supported_versions = [self.current_version]


# =============================================================================
# STANDARD REQUEST/RESPONSE MODELS
# =============================================================================

class PaginationRequest(BaseModel):
    """Standard Pagination Request Parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")


class SortRequest(BaseModel):
    """Standard Sorting Request Parameters"""
    sort: Optional[str] = Field(default=None, description="Sort field")
    order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")


class FilterRequest(BaseModel):
    """Base class for filter requests"""
    pass


class StandardMetadata(BaseModel):
    """Standard Response Metadata"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str
    version: str
    request_id: Optional[str] = None
    processing_time_ms: Optional[float] = None


class PaginationMetadata(BaseModel):
    """Pagination Metadata for List Responses"""
    page: int
    size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool


class StandardListResponse(BaseModel):
    """Standard List Response with Pagination"""
    data: List[Dict[str, Any]]
    metadata: StandardMetadata
    pagination: Optional[PaginationMetadata] = None


class StandardItemResponse(BaseModel):
    """Standard Single Item Response"""
    data: Dict[str, Any]
    metadata: StandardMetadata


class StandardErrorResponse(BaseModel):
    """Standard Error Response"""
    error: bool = True
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    metadata: StandardMetadata


class StandardHealthResponse(BaseModel):
    """Standard Health Check Response"""
    status: str = Field(description="Service health status")
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: Optional[Dict[str, Any]] = None
    dependencies: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


class StandardStatusResponse(BaseModel):
    """Standard Service Status Response"""
    service: str
    version: str
    status: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    configuration: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None


# =============================================================================
# API ENDPOINT BUILDER
# =============================================================================

class APIEndpointBuilder:
    """Builder für standardisierte API Endpoints"""
    
    def __init__(self, service_name: str, standards: APIStandards = None):
        self.service_name = service_name
        self.standards = standards or APIStandards()
        self.router = APIRouter()
        
    def build_health_endpoint(self) -> callable:
        """Build standard health check endpoint"""
        
        @self.router.get(
            self.standards.health_endpoint,
            response_model=StandardHealthResponse,
            tags=["Health"],
            summary="Service Health Check",
            description="Returns service health status and dependencies"
        )
        async def health_check():
            return StandardHealthResponse(
                status="healthy",
                version=self.standards.current_version,
                service=self.service_name
            )
        
        return health_check
    
    def build_status_endpoint(self, status_provider: callable = None) -> callable:
        """Build standard status endpoint"""
        
        @self.router.get(
            f"{self.standards.base_path}/{self.standards.current_version}/status",
            response_model=StandardStatusResponse,
            tags=["Status"],
            summary="Service Status",
            description="Returns detailed service status and metrics"
        )
        async def service_status():
            status_data = {
                "service": self.service_name,
                "version": self.standards.current_version,
                "status": "running",
                "uptime_seconds": 0.0  # Should be calculated from service start time
            }
            
            if status_provider:
                additional_status = await status_provider()
                status_data.update(additional_status)
            
            return StandardStatusResponse(**status_data)
        
        return service_status
    
    def build_list_endpoint(
        self,
        resource_name: str,
        data_provider: callable,
        response_model: Type[BaseModel] = None,
        filters: Type[FilterRequest] = None
    ) -> callable:
        """Build standard list endpoint with pagination and filtering"""
        
        endpoint_path = f"{self.standards.base_path}/{self.standards.current_version}/{resource_name}"
        
        @self.router.get(
            endpoint_path,
            response_model=response_model or StandardListResponse,
            tags=[resource_name.title()],
            summary=f"List {resource_name.title()}",
            description=f"Returns paginated list of {resource_name}"
        )
        async def list_resources(
            pagination: PaginationRequest = Depends(),
            sort: SortRequest = Depends(),
            filters: filters = Depends() if filters else None
        ):
            # Call data provider with standard parameters
            result = await data_provider(
                page=pagination.page,
                size=pagination.size,
                sort=sort.sort,
                order=sort.order,
                filters=filters
            )
            
            return StandardListResponse(
                data=result.get("items", []),
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                ),
                pagination=PaginationMetadata(
                    page=pagination.page,
                    size=pagination.size,
                    total_pages=result.get("total_pages", 1),
                    total_items=result.get("total_items", 0),
                    has_next=result.get("has_next", False),
                    has_previous=result.get("has_previous", False)
                ) if self.standards.include_pagination_info else None
            )
        
        return list_resources
    
    def build_get_endpoint(
        self,
        resource_name: str,
        data_provider: callable,
        response_model: Type[BaseModel] = None
    ) -> callable:
        """Build standard get single item endpoint"""
        
        endpoint_path = f"{self.standards.base_path}/{self.standards.current_version}/{resource_name}/{{item_id}}"
        
        @self.router.get(
            endpoint_path,
            response_model=response_model or StandardItemResponse,
            tags=[resource_name.title()],
            summary=f"Get {resource_name.title()}",
            description=f"Returns single {resource_name} by ID"
        )
        async def get_resource(
            item_id: str = Path(..., description=f"{resource_name.title()} ID")
        ):
            result = await data_provider(item_id)
            
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        return get_resource
    
    def build_create_endpoint(
        self,
        resource_name: str,
        data_processor: callable,
        request_model: Type[BaseModel],
        response_model: Type[BaseModel] = None
    ) -> callable:
        """Build standard create endpoint"""
        
        endpoint_path = f"{self.standards.base_path}/{self.standards.current_version}/{resource_name}"
        
        @self.router.post(
            endpoint_path,
            response_model=response_model or StandardItemResponse,
            status_code=status.HTTP_201_CREATED,
            tags=[resource_name.title()],
            summary=f"Create {resource_name.title()}",
            description=f"Creates new {resource_name}"
        )
        async def create_resource(
            request: request_model = Body(...)
        ):
            result = await data_processor(request)
            
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        return create_resource
    
    def build_update_endpoint(
        self,
        resource_name: str,
        data_processor: callable,
        request_model: Type[BaseModel],
        response_model: Type[BaseModel] = None
    ) -> callable:
        """Build standard update endpoint"""
        
        endpoint_path = f"{self.standards.base_path}/{self.standards.current_version}/{resource_name}/{{item_id}}"
        
        @self.router.put(
            endpoint_path,
            response_model=response_model or StandardItemResponse,
            tags=[resource_name.title()],
            summary=f"Update {resource_name.title()}",
            description=f"Updates existing {resource_name}"
        )
        async def update_resource(
            item_id: str = Path(..., description=f"{resource_name.title()} ID"),
            request: request_model = Body(...)
        ):
            result = await data_processor(item_id, request)
            
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        return update_resource
    
    def build_delete_endpoint(
        self,
        resource_name: str,
        data_processor: callable
    ) -> callable:
        """Build standard delete endpoint"""
        
        endpoint_path = f"{self.standards.base_path}/{self.standards.current_version}/{resource_name}/{{item_id}}"
        
        @self.router.delete(
            endpoint_path,
            status_code=status.HTTP_204_NO_CONTENT,
            tags=[resource_name.title()],
            summary=f"Delete {resource_name.title()}",
            description=f"Deletes {resource_name} by ID"
        )
        async def delete_resource(
            item_id: str = Path(..., description=f"{resource_name.title()} ID")
        ):
            await data_processor(item_id)
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content=None
            )
        
        return delete_resource
    
    def get_router(self) -> APIRouter:
        """Get configured APIRouter"""
        return self.router


# =============================================================================
# RESOURCE CRUD TEMPLATE
# =============================================================================

class ResourceCRUDTemplate:
    """Template für Standard CRUD Operations"""
    
    def __init__(
        self,
        resource_name: str,
        service_name: str,
        standards: APIStandards = None
    ):
        self.resource_name = resource_name
        self.service_name = service_name
        self.standards = standards or APIStandards()
        self.builder = APIEndpointBuilder(service_name, standards)
    
    def create_full_crud_router(
        self,
        list_provider: callable,
        get_provider: callable,
        create_processor: callable,
        update_processor: callable,
        delete_processor: callable,
        request_model: Type[BaseModel],
        response_model: Type[BaseModel] = None,
        filters: Type[FilterRequest] = None
    ) -> APIRouter:
        """Create complete CRUD router for resource"""
        
        # Build all CRUD endpoints
        self.builder.build_list_endpoint(
            self.resource_name, 
            list_provider, 
            response_model, 
            filters
        )
        
        self.builder.build_get_endpoint(
            self.resource_name,
            get_provider,
            response_model
        )
        
        self.builder.build_create_endpoint(
            self.resource_name,
            create_processor,
            request_model,
            response_model
        )
        
        self.builder.build_update_endpoint(
            self.resource_name,
            update_processor,
            request_model,
            response_model
        )
        
        self.builder.build_delete_endpoint(
            self.resource_name,
            delete_processor
        )
        
        return self.builder.get_router()


# =============================================================================
# API DOCUMENTATION STANDARDS
# =============================================================================

class APIDocumentationStandards:
    """Standards für API Documentation"""
    
    @staticmethod
    def get_openapi_config(
        service_name: str,
        version: str,
        description: str = None
    ) -> Dict[str, Any]:
        """Standard OpenAPI Configuration"""
        
        return {
            "title": f"{service_name.replace('-', ' ').title()} API",
            "description": description or f"API for {service_name} with Clean Architecture",
            "version": version,
            "terms_of_service": None,
            "contact": {
                "name": "Architecture Team",
                "email": "architecture@aktienanalyse.local"
            },
            "license": {
                "name": "Internal Use Only",
                "identifier": "proprietary"
            },
            "servers": [
                {
                    "url": "http://10.1.1.174:8000",
                    "description": "Production Server"
                },
                {
                    "url": "http://localhost:8000",
                    "description": "Development Server"
                }
            ]
        }
    
    @staticmethod
    def get_tag_metadata(resource_groups: List[str]) -> List[Dict[str, str]]:
        """Standard Tag Metadata für OpenAPI"""
        
        standard_tags = [
            {
                "name": "Health",
                "description": "Health check and monitoring endpoints"
            },
            {
                "name": "Status",
                "description": "Service status and metrics endpoints"
            }
        ]
        
        for group in resource_groups:
            standard_tags.append({
                "name": group.title(),
                "description": f"{group.title()} management endpoints"
            })
        
        return standard_tags


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_standard_api_router(
    service_name: str,
    version: str = "v1",
    include_health: bool = True,
    include_status: bool = True
) -> APIRouter:
    """Create standard API router with health and status endpoints"""
    
    standards = APIStandards(current_version=version)
    builder = APIEndpointBuilder(service_name, standards)
    
    if include_health:
        builder.build_health_endpoint()
    
    if include_status:
        builder.build_status_endpoint()
    
    return builder.get_router()


def apply_api_standards_to_app(
    app,
    service_name: str,
    version: str = "v1",
    description: str = None
) -> None:
    """Apply API standards to existing FastAPI app"""
    
    # Update OpenAPI configuration
    openapi_config = APIDocumentationStandards.get_openapi_config(
        service_name,
        version,
        description
    )
    
    app.title = openapi_config["title"]
    app.description = openapi_config["description"]
    app.version = openapi_config["version"]
    app.contact = openapi_config["contact"]
    app.license_info = openapi_config["license"]


# =============================================================================
# API VALIDATION UTILITIES
# =============================================================================

class APIValidationUtils:
    """Utilities für API Validation"""
    
    @staticmethod
    def validate_pagination_params(page: int, size: int, max_size: int = 100) -> None:
        """Validate pagination parameters"""
        if page < 1:
            raise ValueError("Page must be >= 1")
        if size < 1:
            raise ValueError("Size must be >= 1")
        if size > max_size:
            raise ValueError(f"Size must be <= {max_size}")
    
    @staticmethod
    def validate_sort_params(sort: str, valid_fields: List[str]) -> None:
        """Validate sort parameters"""
        if sort and sort not in valid_fields:
            raise ValueError(f"Invalid sort field: {sort}. Valid fields: {valid_fields}")


# =============================================================================
# API RESPONSE BUILDERS
# =============================================================================

class APIResponseBuilder:
    """Builder für standardisierte API Responses"""
    
    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
    
    def build_success_response(
        self,
        data: Any,
        processing_time_ms: float = None
    ) -> StandardItemResponse:
        """Build standardized success response"""
        
        metadata = StandardMetadata(
            service=self.service_name,
            version=self.version,
            processing_time_ms=processing_time_ms
        )
        
        return StandardItemResponse(data=data, metadata=metadata)
    
    def build_list_response(
        self,
        items: List[Any],
        pagination_info: Dict[str, Any] = None,
        processing_time_ms: float = None
    ) -> StandardListResponse:
        """Build standardized list response"""
        
        metadata = StandardMetadata(
            service=self.service_name,
            version=self.version,
            processing_time_ms=processing_time_ms
        )
        
        pagination = None
        if pagination_info:
            pagination = PaginationMetadata(**pagination_info)
        
        return StandardListResponse(
            data=items,
            metadata=metadata,
            pagination=pagination
        )