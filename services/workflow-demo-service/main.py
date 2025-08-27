#!/usr/bin/env python3
"""
Workflow Demonstration Service - Clean Architecture v6.0.0
Demonstrates proper Clean Architecture implementation for code review.

This service showcases:
- SOLID Principles adherence
- Clean Architecture layer separation
- Performance optimization (<0.12s requirement)
- Comprehensive error handling
- Type safety with Pydantic models
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, validator
import uvicorn

# =============================================================================
# DOMAIN LAYER - Pure Business Logic
# =============================================================================

@dataclass(frozen=True)
class WorkflowDemoValue:
    """Value Object für Workflow-Demonstration - Domain Layer"""
    demo_id: str
    timestamp: datetime
    status: str
    
    def __post_init__(self):
        if not self.demo_id or len(self.demo_id) < 3:
            raise ValueError("Demo ID must be at least 3 characters")
        if self.status not in ['pending', 'processing', 'completed', 'failed']:
            raise ValueError("Invalid status value")

class WorkflowDemoEntity:
    """Entity für Workflow-Demonstration - Domain Layer"""
    
    def __init__(self, demo_id: str, performance_target: Decimal = Decimal('0.12')):
        self.demo_id = demo_id
        self.performance_target = performance_target
        self.created_at = datetime.now()
        self.status = 'pending'
        self._execution_time: Optional[Decimal] = None
    
    def start_processing(self) -> None:
        """Start the workflow demonstration processing"""
        if self.status != 'pending':
            raise ValueError(f"Cannot start processing from status: {self.status}")
        self.status = 'processing'
    
    def complete_processing(self, execution_time: Decimal) -> bool:
        """Complete processing and validate performance"""
        if self.status != 'processing':
            raise ValueError(f"Cannot complete from status: {self.status}")
        
        self._execution_time = execution_time
        
        # Performance validation according to Clean Architecture standards
        if execution_time <= self.performance_target:
            self.status = 'completed'
            return True
        else:
            self.status = 'failed'
            return False
    
    @property
    def execution_time(self) -> Optional[Decimal]:
        return self._execution_time
    
    @property
    def performance_met(self) -> bool:
        """Check if performance requirements are met"""
        if self._execution_time is None:
            return False
        return self._execution_time <= self.performance_target

# =============================================================================
# APPLICATION LAYER - Use Cases & Business Logic Coordination
# =============================================================================

class WorkflowDemoUseCase:
    """Use Case für Workflow-Demonstration - Application Layer"""
    
    def __init__(self, performance_target: Decimal = Decimal('0.10')):
        self.performance_target = performance_target
        self.logger = logging.getLogger(__name__)
    
    async def execute_workflow_demo(self, demo_id: str) -> WorkflowDemoEntity:
        """Execute workflow demonstration with performance monitoring"""
        start_time = datetime.now()
        
        try:
            # Create domain entity
            demo_entity = WorkflowDemoEntity(demo_id, self.performance_target)
            
            # Start processing
            demo_entity.start_processing()
            self.logger.info(f"Started workflow demo: {demo_id}")
            
            # Simulate processing with performance optimization
            await self._simulate_optimized_processing()
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time = Decimal(str((end_time - start_time).total_seconds()))
            
            # Complete processing
            success = demo_entity.complete_processing(execution_time)
            
            if success:
                self.logger.info(f"Workflow demo completed successfully: {demo_id} in {execution_time}s")
            else:
                self.logger.warning(f"Workflow demo performance target missed: {demo_id} took {execution_time}s")
            
            return demo_entity
            
        except Exception as e:
            self.logger.error(f"Workflow demo failed: {demo_id} - {e}")
            raise
    
    async def _simulate_optimized_processing(self) -> None:
        """Simulate optimized processing to meet performance requirements"""
        # Simulate efficient processing (well under 0.12s target)
        await asyncio.sleep(0.05)  # 50ms - well within performance bounds

# =============================================================================
# INFRASTRUCTURE LAYER - External Services & Technical Implementation
# =============================================================================

class WorkflowDemoRepository:
    """Repository für Workflow-Demo Persistence - Infrastructure Layer"""
    
    def __init__(self):
        self._storage: dict[str, WorkflowDemoEntity] = {}
        self.logger = logging.getLogger(__name__)
    
    async def save(self, entity: WorkflowDemoEntity) -> None:
        """Save workflow demo entity"""
        try:
            self._storage[entity.demo_id] = entity
            self.logger.info(f"Saved workflow demo: {entity.demo_id}")
        except Exception as e:
            self.logger.error(f"Failed to save workflow demo: {entity.demo_id} - {e}")
            raise
    
    async def find_by_id(self, demo_id: str) -> Optional[WorkflowDemoEntity]:
        """Find workflow demo by ID"""
        return self._storage.get(demo_id)
    
    async def get_all(self) -> List[WorkflowDemoEntity]:
        """Get all workflow demos"""
        return list(self._storage.values())

# =============================================================================
# PRESENTATION LAYER - API Controllers & Request/Response Models
# =============================================================================

class WorkflowDemoRequest(BaseModel):
    """Request model for workflow demonstration - Presentation Layer"""
    demo_id: str
    performance_target: Optional[Decimal] = Decimal('0.10')
    
    @validator('demo_id')
    def validate_demo_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Demo ID must be at least 3 characters')
        return v
    
    @validator('performance_target')
    def validate_performance_target(cls, v):
        if v and (v <= 0 or v > 1):
            raise ValueError('Performance target must be between 0 and 1 seconds')
        return v

class WorkflowDemoResponse(BaseModel):
    """Response model for workflow demonstration - Presentation Layer"""
    demo_id: str
    status: str
    execution_time: Optional[Decimal] = None
    performance_met: bool
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

# =============================================================================
# DEPENDENCY INJECTION CONTAINER - Infrastructure Layer
# =============================================================================

class WorkflowDemoContainer:
    """Dependency Injection Container - Infrastructure Layer"""
    
    def __init__(self):
        self._repository = WorkflowDemoRepository()
        self._use_case = WorkflowDemoUseCase()
    
    def get_repository(self) -> WorkflowDemoRepository:
        return self._repository
    
    def get_use_case(self) -> WorkflowDemoUseCase:
        return self._use_case

# Global container instance
container = WorkflowDemoContainer()

# =============================================================================
# FASTAPI APPLICATION SETUP - Presentation Layer
# =============================================================================

app = FastAPI(
    title="Workflow Demo Service",
    description="Clean Architecture demonstration for code review workflow",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Dependency injection
def get_container() -> WorkflowDemoContainer:
    return container

# =============================================================================
# API ENDPOINTS - Presentation Layer
# =============================================================================

@app.post("/api/v1/workflow-demo", response_model=WorkflowDemoResponse)
async def create_workflow_demo(
    request: WorkflowDemoRequest,
    container: WorkflowDemoContainer = Depends(get_container)
) -> WorkflowDemoResponse:
    """Create and execute workflow demonstration"""
    try:
        # Execute use case
        use_case = container.get_use_case()
        entity = await use_case.execute_workflow_demo(request.demo_id)
        
        # Save to repository
        repository = container.get_repository()
        await repository.save(entity)
        
        # Return response
        return WorkflowDemoResponse(
            demo_id=entity.demo_id,
            status=entity.status,
            execution_time=entity.execution_time,
            performance_met=entity.performance_met,
            created_at=entity.created_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Workflow demo creation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/workflow-demo/{demo_id}", response_model=WorkflowDemoResponse)
async def get_workflow_demo(
    demo_id: str,
    container: WorkflowDemoContainer = Depends(get_container)
) -> WorkflowDemoResponse:
    """Get workflow demonstration by ID"""
    try:
        repository = container.get_repository()
        entity = await repository.find_by_id(demo_id)
        
        if not entity:
            raise HTTPException(status_code=404, detail="Workflow demo not found")
        
        return WorkflowDemoResponse(
            demo_id=entity.demo_id,
            status=entity.status,
            execution_time=entity.execution_time,
            performance_met=entity.performance_met,
            created_at=entity.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to retrieve workflow demo: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/workflow-demos", response_model=List[WorkflowDemoResponse])
async def list_workflow_demos(
    container: WorkflowDemoContainer = Depends(get_container)
) -> List[WorkflowDemoResponse]:
    """List all workflow demonstrations"""
    try:
        repository = container.get_repository()
        entities = await repository.get_all()
        
        return [
            WorkflowDemoResponse(
                demo_id=entity.demo_id,
                status=entity.status,
                execution_time=entity.execution_time,
                performance_met=entity.performance_met,
                created_at=entity.created_at
            )
            for entity in entities
        ]
        
    except Exception as e:
        logging.error(f"Failed to list workflow demos: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "workflow-demo-service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8030,
        log_level="info"
    )