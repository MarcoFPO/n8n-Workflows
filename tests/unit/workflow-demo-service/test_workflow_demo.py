#!/usr/bin/env python3
"""
Unit Tests für Workflow Demo Service
Demonstriert Test-Driven Development für Clean Architecture
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

# Import services to test
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "services" / "workflow-demo-service"))

from main import (
    WorkflowDemoValue,
    WorkflowDemoEntity, 
    WorkflowDemoUseCase,
    WorkflowDemoRepository,
    WorkflowDemoRequest,
    WorkflowDemoResponse
)

# =============================================================================
# DOMAIN LAYER TESTS
# =============================================================================

class TestWorkflowDemoValue:
    """Test WorkflowDemoValue Value Object"""
    
    def test_valid_value_object_creation(self):
        """Test creating valid value object"""
        demo_value = WorkflowDemoValue(
            demo_id="demo123",
            timestamp=datetime.now(),
            status="pending"
        )
        
        assert demo_value.demo_id == "demo123"
        assert demo_value.status == "pending"
        assert isinstance(demo_value.timestamp, datetime)
    
    def test_invalid_demo_id_raises_error(self):
        """Test that invalid demo_id raises ValueError"""
        with pytest.raises(ValueError, match="Demo ID must be at least 3 characters"):
            WorkflowDemoValue(
                demo_id="ab",  # Too short
                timestamp=datetime.now(),
                status="pending"
            )
    
    def test_invalid_status_raises_error(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid status value"):
            WorkflowDemoValue(
                demo_id="demo123",
                timestamp=datetime.now(),
                status="invalid_status"  # Invalid status
            )
    
    def test_value_object_immutability(self):
        """Test that value object is immutable (frozen dataclass)"""
        demo_value = WorkflowDemoValue(
            demo_id="demo123",
            timestamp=datetime.now(),
            status="pending"
        )
        
        # Should raise AttributeError for frozen dataclass
        with pytest.raises(AttributeError):
            demo_value.demo_id = "new_id"

class TestWorkflowDemoEntity:
    """Test WorkflowDemoEntity Domain Entity"""
    
    def test_entity_creation(self):
        """Test creating workflow demo entity"""
        entity = WorkflowDemoEntity("demo123")
        
        assert entity.demo_id == "demo123"
        assert entity.status == "pending"
        assert entity.performance_target == Decimal('0.12')
        assert isinstance(entity.created_at, datetime)
        assert entity.execution_time is None
    
    def test_entity_with_custom_performance_target(self):
        """Test creating entity with custom performance target"""
        entity = WorkflowDemoEntity("demo123", Decimal('0.05'))
        
        assert entity.performance_target == Decimal('0.05')
    
    def test_start_processing_valid_transition(self):
        """Test valid state transition to processing"""
        entity = WorkflowDemoEntity("demo123")
        entity.start_processing()
        
        assert entity.status == "processing"
    
    def test_start_processing_invalid_transition(self):
        """Test invalid state transition raises error"""
        entity = WorkflowDemoEntity("demo123")
        entity.start_processing()  # Move to processing
        
        # Try to start again
        with pytest.raises(ValueError, match="Cannot start processing from status: processing"):
            entity.start_processing()
    
    def test_complete_processing_success(self):
        """Test successful processing completion"""
        entity = WorkflowDemoEntity("demo123", Decimal('0.12'))
        entity.start_processing()
        
        # Complete with execution time under target
        success = entity.complete_processing(Decimal('0.10'))
        
        assert success is True
        assert entity.status == "completed"
        assert entity.execution_time == Decimal('0.10')
        assert entity.performance_met is True
    
    def test_complete_processing_performance_failure(self):
        """Test processing completion with performance target missed"""
        entity = WorkflowDemoEntity("demo123", Decimal('0.12'))
        entity.start_processing()
        
        # Complete with execution time over target
        success = entity.complete_processing(Decimal('0.15'))
        
        assert success is False
        assert entity.status == "failed"
        assert entity.execution_time == Decimal('0.15')
        assert entity.performance_met is False
    
    def test_complete_processing_invalid_state(self):
        """Test completing processing from invalid state"""
        entity = WorkflowDemoEntity("demo123")
        # Don't start processing
        
        with pytest.raises(ValueError, match="Cannot complete from status: pending"):
            entity.complete_processing(Decimal('0.10'))

# =============================================================================
# APPLICATION LAYER TESTS  
# =============================================================================

class TestWorkflowDemoUseCase:
    """Test WorkflowDemoUseCase Application Layer"""
    
    @pytest.mark.asyncio
    async def test_execute_workflow_demo_success(self):
        """Test successful workflow demo execution"""
        use_case = WorkflowDemoUseCase(Decimal('0.12'))
        
        result = await use_case.execute_workflow_demo("demo123")
        
        assert isinstance(result, WorkflowDemoEntity)
        assert result.demo_id == "demo123"
        assert result.status == "completed"
        assert result.execution_time is not None
        assert result.execution_time <= Decimal('0.12')
        assert result.performance_met is True
    
    @pytest.mark.asyncio
    async def test_execute_workflow_demo_with_strict_target(self):
        """Test workflow demo with very strict performance target"""
        # Set very strict target that might not be met
        use_case = WorkflowDemoUseCase(Decimal('0.01'))  # 10ms target
        
        result = await use_case.execute_workflow_demo("demo123")
        
        assert isinstance(result, WorkflowDemoEntity)
        assert result.demo_id == "demo123"
        # Status could be completed or failed depending on actual execution time
        assert result.status in ["completed", "failed"]
        assert result.execution_time is not None

# =============================================================================
# INFRASTRUCTURE LAYER TESTS
# =============================================================================

class TestWorkflowDemoRepository:
    """Test WorkflowDemoRepository Infrastructure Layer"""
    
    @pytest.mark.asyncio
    async def test_save_and_find_entity(self):
        """Test saving and retrieving entity"""
        repository = WorkflowDemoRepository()
        entity = WorkflowDemoEntity("demo123")
        
        # Save entity
        await repository.save(entity)
        
        # Find entity
        found_entity = await repository.find_by_id("demo123")
        
        assert found_entity is not None
        assert found_entity.demo_id == "demo123"
        assert found_entity.status == "pending"
    
    @pytest.mark.asyncio
    async def test_find_nonexistent_entity(self):
        """Test finding non-existent entity returns None"""
        repository = WorkflowDemoRepository()
        
        result = await repository.find_by_id("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_entities(self):
        """Test retrieving all entities"""
        repository = WorkflowDemoRepository()
        
        # Save multiple entities
        entity1 = WorkflowDemoEntity("demo1")
        entity2 = WorkflowDemoEntity("demo2")
        
        await repository.save(entity1)
        await repository.save(entity2)
        
        # Get all
        all_entities = await repository.get_all()
        
        assert len(all_entities) == 2
        demo_ids = [entity.demo_id for entity in all_entities]
        assert "demo1" in demo_ids
        assert "demo2" in demo_ids

# =============================================================================
# PRESENTATION LAYER TESTS
# =============================================================================

class TestWorkflowDemoRequest:
    """Test WorkflowDemoRequest Presentation Layer Model"""
    
    def test_valid_request_creation(self):
        """Test creating valid request model"""
        request = WorkflowDemoRequest(
            demo_id="demo123",
            performance_target=Decimal('0.10')
        )
        
        assert request.demo_id == "demo123"
        assert request.performance_target == Decimal('0.10')
    
    def test_request_with_default_performance_target(self):
        """Test request with default performance target"""
        request = WorkflowDemoRequest(demo_id="demo123")
        
        assert request.demo_id == "demo123"
        assert request.performance_target == Decimal('0.10')
    
    def test_invalid_demo_id_validation(self):
        """Test demo_id validation"""
        with pytest.raises(ValueError, match="Demo ID must be at least 3 characters"):
            WorkflowDemoRequest(demo_id="ab")
    
    def test_invalid_performance_target_validation(self):
        """Test performance_target validation"""
        with pytest.raises(ValueError, match="Performance target must be between 0 and 1 seconds"):
            WorkflowDemoRequest(
                demo_id="demo123",
                performance_target=Decimal('2.0')  # Too high
            )
        
        with pytest.raises(ValueError, match="Performance target must be between 0 and 1 seconds"):
            WorkflowDemoRequest(
                demo_id="demo123", 
                performance_target=Decimal('0.0')  # Too low
            )

class TestWorkflowDemoResponse:
    """Test WorkflowDemoResponse Presentation Layer Model"""
    
    def test_response_creation(self):
        """Test creating response model"""
        response = WorkflowDemoResponse(
            demo_id="demo123",
            status="completed",
            execution_time=Decimal('0.05'),
            performance_met=True,
            created_at=datetime.now()
        )
        
        assert response.demo_id == "demo123"
        assert response.status == "completed"
        assert response.execution_time == Decimal('0.05')
        assert response.performance_met is True
        assert isinstance(response.created_at, datetime)
    
    def test_response_json_encoding(self):
        """Test JSON encoding configuration"""
        now = datetime.now()
        response = WorkflowDemoResponse(
            demo_id="demo123",
            status="completed",
            execution_time=Decimal('0.05'),
            performance_met=True,
            created_at=now
        )
        
        # Test that JSON encoding works (would raise exception if not configured)
        json_data = response.dict()
        
        assert json_data["demo_id"] == "demo123"
        assert json_data["execution_time"] == Decimal('0.05')
        assert json_data["created_at"] == now

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestWorkflowDemoIntegration:
    """Integration tests across all layers"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self):
        """Test complete workflow from request to response"""
        # Create request
        request = WorkflowDemoRequest(
            demo_id="integration_test_123",
            performance_target=Decimal('0.15')
        )
        
        # Execute use case
        use_case = WorkflowDemoUseCase(request.performance_target)
        entity = await use_case.execute_workflow_demo(request.demo_id)
        
        # Save to repository
        repository = WorkflowDemoRepository()
        await repository.save(entity)
        
        # Create response
        response = WorkflowDemoResponse(
            demo_id=entity.demo_id,
            status=entity.status,
            execution_time=entity.execution_time,
            performance_met=entity.performance_met,
            created_at=entity.created_at
        )
        
        # Verify integration
        assert response.demo_id == request.demo_id
        assert response.status == "completed"  # Should complete within 0.15s
        assert response.execution_time is not None
        assert response.performance_met is True
        
        # Verify persistence
        retrieved_entity = await repository.find_by_id(request.demo_id)
        assert retrieved_entity is not None
        assert retrieved_entity.demo_id == request.demo_id

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestWorkflowDemoPerformance:
    """Performance tests to validate response time requirements"""
    
    @pytest.mark.asyncio
    async def test_use_case_performance_requirement(self):
        """Test that use case meets performance requirement"""
        use_case = WorkflowDemoUseCase(Decimal('0.12'))
        
        start_time = datetime.now()
        result = await use_case.execute_workflow_demo("performance_test")
        end_time = datetime.now()
        
        actual_time = (end_time - start_time).total_seconds()
        
        # Should complete well under 0.12s requirement
        assert actual_time < 0.12
        assert result.performance_met is True
        
    @pytest.mark.asyncio  
    async def test_concurrent_execution_performance(self):
        """Test performance under concurrent load"""
        use_case = WorkflowDemoUseCase(Decimal('0.12'))
        
        # Execute multiple concurrent requests
        tasks = [
            use_case.execute_workflow_demo(f"concurrent_test_{i}")
            for i in range(10)
        ]
        
        start_time = datetime.now()
        results = await asyncio.gather(*tasks)
        end_time = datetime.now()
        
        total_time = (end_time - start_time).total_seconds()
        
        # All should complete successfully
        assert len(results) == 10
        for result in results:
            assert result.status == "completed"
            assert result.performance_met is True
        
        # Total time should be reasonable for concurrent execution
        assert total_time < 1.0  # Should complete in under 1 second

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])