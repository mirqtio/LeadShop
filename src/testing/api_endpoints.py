"""
PRP-013: Testing API Endpoints
FastAPI endpoints for the manual testing interface dashboard
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.testing.dashboard import TestingDashboard, run_full_pipeline_test, get_dashboard_status
from src.testing.websocket_manager import websocket_manager, WebSocketManager, MessageType
from src.core.config import settings

logger = logging.getLogger(__name__)

# Router for testing endpoints
router = APIRouter(prefix="/api/v1/testing", tags=["testing"])

# Pydantic models for request/response

class PipelineTestRequest(BaseModel):
    """Request model for pipeline test execution."""
    test_type: str = Field(default="full_pipeline", description="Type of test to run")
    lead_data: Dict[str, Any] = Field(..., description="Lead data for testing")
    timeout_seconds: Optional[int] = Field(default=600, description="Test timeout in seconds")

class TestExecutionResponse(BaseModel):
    """Response model for test execution status."""
    test_id: str
    status: str
    estimated_duration: str
    created_at: str
    user_id: int

class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    pipeline_health: str
    active_tests: int
    completed_tests: int
    failed_tests: int
    system_metrics: Dict[str, Any]
    component_health: Dict[str, str]
    timestamp: str

class TestHistoryResponse(BaseModel):
    """Response model for test history."""
    id: str
    test_type: str
    status: str
    execution_time_ms: Optional[int]
    success_rate: float
    created_at: str
    completed_at: Optional[str]
    lead_data: Dict[str, Any]
    pipeline_results: List[Dict[str, Any]]

class TestingMetricsResponse(BaseModel):
    """Response model for testing metrics."""
    period_days: int
    total_tests: int
    successful_tests: int
    failed_tests: int
    success_rate: float
    average_execution_time_ms: float
    step_statistics: Dict[str, Dict[str, Any]]
    generated_at: str

class LeadImportRequest(BaseModel):
    """Request model for lead import."""
    leads: List[Dict[str, Any]]
    validate_only: bool = Field(default=False, description="Only validate, don't import")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing leads")

class LeadImportResponse(BaseModel):
    """Response model for lead import results."""
    total_leads: int
    successful_imports: int
    failed_imports: int
    validation_errors: List[Dict[str, Any]]
    import_id: str

# Mock user dependency (replace with actual authentication)
class User(BaseModel):
    id: int
    name: str
    role: str
    permissions: List[str]

async def get_current_user() -> User:
    """Mock user authentication (replace with actual implementation)."""
    return User(
        id=1,
        name="Test User",
        role="qa_manager",
        permissions=["run_pipeline_tests", "view_test_results", "manage_leads"]
    )

async def get_current_user_from_websocket(websocket: WebSocket) -> User:
    """Mock user authentication for WebSocket (replace with actual implementation)."""
    return User(
        id=1,
        name="Test User",
        role="qa_manager",
        permissions=["run_pipeline_tests", "view_test_results", "manage_leads"]
    )

# Permission checking decorator
def require_permission(permission: str):
    """Decorator to require specific permission for endpoint access."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or permission not in current_user.permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission '{permission}' required"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# API Endpoints

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: User = Depends(get_current_user)
) -> SystemStatusResponse:
    """Get current system status and health metrics."""
    try:
        status = await get_dashboard_status()
        
        return SystemStatusResponse(
            pipeline_health=status.pipeline_health.value,
            active_tests=status.active_tests,
            completed_tests=status.completed_tests,
            failed_tests=status.failed_tests,
            system_metrics={
                "cpu_usage": status.system_metrics.cpu_usage,
                "memory_usage": status.system_metrics.memory_usage,
                "database_connections": status.system_metrics.database_connections,
                "queue_depth": status.system_metrics.queue_depth,
                "response_time_ms": status.system_metrics.response_time_ms,
                "error_rate": status.system_metrics.error_rate
            },
            component_health=status.component_health,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")

@router.post("/run-pipeline", response_model=TestExecutionResponse)
async def run_pipeline_test(
    test_request: PipelineTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> TestExecutionResponse:
    """Run a complete pipeline test for a lead."""
    try:
        # Validate required fields
        if not test_request.lead_data.get('website_url'):
            raise HTTPException(status_code=400, detail="Website URL is required")
        
        if not test_request.lead_data.get('business_name'):
            raise HTTPException(status_code=400, detail="Business name is required")
        
        # Start pipeline test in background
        background_tasks.add_task(
            execute_pipeline_test_with_notifications,
            test_request.lead_data,
            current_user.id
        )
        
        # Generate response
        test_id = f"test_{int(datetime.now().timestamp())}"
        
        return TestExecutionResponse(
            test_id=test_id,
            status="started",
            estimated_duration="5-8 minutes",
            created_at=datetime.now(timezone.utc).isoformat(),
            user_id=current_user.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start pipeline test: {e}")
        raise HTTPException(status_code=500, detail="Failed to start pipeline test")

async def execute_pipeline_test_with_notifications(lead_data: Dict[str, Any], user_id: int):
    """Execute pipeline test with WebSocket notifications."""
    try:
        from src.testing.websocket_manager import send_test_started, send_test_update, send_test_completed
        
        # Notify test started
        test_id = f"test_{int(datetime.now().timestamp())}"
        await send_test_started(test_id, {
            "test_id": test_id,
            "lead_data": lead_data,
            "user_id": user_id,
            "status": "started"
        })
        
        # Execute the test
        result = await run_full_pipeline_test(lead_data, user_id)
        
        # Notify test completed
        await send_test_completed(test_id, {
            "test_id": result.id,
            "status": result.status.value,
            "success_rate": result.success_rate,
            "execution_time_ms": result.execution_time_ms,
            "pipeline_results": [asdict(step) for step in result.pipeline_results]
        })
        
    except Exception as e:
        logger.error(f"Pipeline test execution failed: {e}")
        
        # Notify test failed
        await send_test_completed(test_id, {
            "test_id": test_id,
            "status": "failed",
            "error_message": str(e)
        })

@router.get("/active", response_model=List[TestExecutionResponse])
async def get_active_tests(
    current_user: User = Depends(get_current_user)
) -> List[TestExecutionResponse]:
    """Get all currently active test executions."""
    try:
        dashboard = TestingDashboard()
        active_tests = await dashboard.get_active_tests()
        
        return [
            TestExecutionResponse(
                test_id=test.id,
                status=test.status.value,
                estimated_duration="Variable",
                created_at=test.created_at.isoformat(),
                user_id=test.user_id
            )
            for test in active_tests
        ]
        
    except Exception as e:
        logger.error(f"Failed to get active tests: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active tests")

@router.get("/history", response_model=List[TestHistoryResponse])
async def get_test_history(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[TestHistoryResponse]:
    """Get test execution history with filtering."""
    try:
        dashboard = TestingDashboard()
        test_history = await dashboard.get_test_history(limit=limit)
        
        # Apply status filter if provided
        if status:
            test_history = [test for test in test_history if test.status.value == status]
        
        # Apply offset
        test_history = test_history[offset:]
        
        return [
            TestHistoryResponse(
                id=test.id,
                test_type=test.test_type,
                status=test.status.value,
                execution_time_ms=test.execution_time_ms,
                success_rate=test.success_rate,
                created_at=test.created_at.isoformat(),
                completed_at=test.completed_at.isoformat() if test.completed_at else None,
                lead_data=test.lead_data,
                pipeline_results=[asdict(step) for step in test.pipeline_results]
            )
            for test in test_history
        ]
        
    except Exception as e:
        logger.error(f"Failed to get test history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve test history")

@router.get("/metrics", response_model=TestingMetricsResponse)
async def get_testing_metrics(
    days: int = 7,
    current_user: User = Depends(get_current_user)
) -> TestingMetricsResponse:
    """Get comprehensive testing metrics and analytics."""
    try:
        dashboard = TestingDashboard()
        metrics = await dashboard.get_testing_metrics(days=days)
        
        return TestingMetricsResponse(
            period_days=metrics['period_days'],
            total_tests=metrics['total_tests'],
            successful_tests=metrics['successful_tests'],
            failed_tests=metrics['failed_tests'],
            success_rate=metrics['success_rate'],
            average_execution_time_ms=metrics['average_execution_time_ms'],
            step_statistics=metrics['step_statistics'],
            generated_at=metrics['generated_at']
        )
        
    except Exception as e:
        logger.error(f"Failed to get testing metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve testing metrics")

@router.post("/import-leads", response_model=LeadImportResponse)
async def import_leads(
    import_request: LeadImportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> LeadImportResponse:
    """Import leads from uploaded data."""
    try:
        if "manage_leads" not in current_user.permissions:
            raise HTTPException(status_code=403, detail="Lead management permission required")
        
        import_id = f"import_{int(datetime.now().timestamp())}"
        
        # Validate leads
        validation_errors = []
        valid_leads = []
        
        for i, lead_data in enumerate(import_request.leads):
            try:
                # Basic validation
                if not lead_data.get('business_name'):
                    validation_errors.append({
                        'row': i + 1,
                        'field': 'business_name',
                        'message': 'Business name is required'
                    })
                    continue
                
                if not lead_data.get('website_url'):
                    validation_errors.append({
                        'row': i + 1,
                        'field': 'website_url',
                        'message': 'Website URL is required'
                    })
                    continue
                
                if not lead_data.get('email'):
                    validation_errors.append({
                        'row': i + 1,
                        'field': 'email',
                        'message': 'Email is required'
                    })
                    continue
                
                # Email format validation
                import re
                email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                if not re.match(email_regex, lead_data['email']):
                    validation_errors.append({
                        'row': i + 1,
                        'field': 'email',
                        'message': 'Invalid email format'
                    })
                    continue
                
                valid_leads.append(lead_data)
                
            except Exception as e:
                validation_errors.append({
                    'row': i + 1,
                    'field': 'general',
                    'message': str(e)
                })
        
        if import_request.validate_only:
            return LeadImportResponse(
                total_leads=len(import_request.leads),
                successful_imports=len(valid_leads),
                failed_imports=len(validation_errors),
                validation_errors=validation_errors,
                import_id=import_id
            )
        
        # Start import process in background
        if valid_leads:
            background_tasks.add_task(
                process_lead_import,
                valid_leads,
                import_id,
                current_user.id
            )
        
        return LeadImportResponse(
            total_leads=len(import_request.leads),
            successful_imports=len(valid_leads),
            failed_imports=len(validation_errors),
            validation_errors=validation_errors,
            import_id=import_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import leads: {e}")
        raise HTTPException(status_code=500, detail="Failed to import leads")

async def process_lead_import(leads: List[Dict[str, Any]], import_id: str, user_id: int):
    """Process lead import in background."""
    try:
        from src.testing.websocket_manager import websocket_manager, MessageType, WebSocketMessage
        
        # Notify import started
        message = WebSocketMessage(
            type=MessageType.LEAD_IMPORTED,
            payload={
                "import_id": import_id,
                "status": "processing",
                "total_leads": len(leads),
                "processed": 0
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        )
        await websocket_manager.broadcast_to_user(user_id, message)
        
        # Process leads (mock implementation)
        for i, lead_data in enumerate(leads):
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            # Notify progress
            message = WebSocketMessage(
                type=MessageType.LEAD_IMPORTED,
                payload={
                    "import_id": import_id,
                    "status": "processing",
                    "total_leads": len(leads),
                    "processed": i + 1
                },
                timestamp=datetime.now(timezone.utc),
                user_id=user_id
            )
            await websocket_manager.broadcast_to_user(user_id, message)
        
        # Notify completion
        message = WebSocketMessage(
            type=MessageType.LEAD_IMPORTED,
            payload={
                "import_id": import_id,
                "status": "completed",
                "total_leads": len(leads),
                "processed": len(leads),
                "successful": len(leads),
                "failed": 0
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        )
        await websocket_manager.broadcast_to_user(user_id, message)
        
    except Exception as e:
        logger.error(f"Lead import processing failed: {e}")

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_from_websocket)
):
    """WebSocket endpoint for real-time testing updates."""
    await websocket.accept()
    connection = await websocket_manager.connect(websocket, current_user.id)
    
    try:
        while True:
            # Handle client messages
            data = await websocket.receive_text()
            message_data = json.loads(data) if data else {}
            
            await websocket_manager.handle_client_message(websocket, message_data)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, current_user.id)
    except Exception as e:
        logger.error(f"WebSocket error for user {current_user.id}: {e}")
        await websocket_manager.disconnect(websocket, current_user.id)

@router.get("/websocket-stats")
async def get_websocket_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get WebSocket manager statistics."""
    try:
        return websocket_manager.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get WebSocket statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve WebSocket statistics")

@router.post("/system-health-check")
async def run_system_health_check(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Run comprehensive system health check."""
    try:
        if "view_system_metrics" not in current_user.permissions:
            raise HTTPException(status_code=403, detail="System metrics permission required")
        
        dashboard = TestingDashboard()
        status = await dashboard.get_system_status()
        
        # Run additional health checks
        health_results = {
            "overall_health": status.pipeline_health.value,
            "component_health": status.component_health,
            "system_metrics": {
                "cpu_usage": status.system_metrics.cpu_usage,
                "memory_usage": status.system_metrics.memory_usage,
                "database_connections": status.system_metrics.database_connections,
                "queue_depth": status.system_metrics.queue_depth,
                "response_time_ms": status.system_metrics.response_time_ms,
                "error_rate": status.system_metrics.error_rate
            },
            "test_statistics": {
                "active_tests": status.active_tests,
                "completed_tests": status.completed_tests,
                "failed_tests": status.failed_tests,
                "success_rate": (status.completed_tests / (status.completed_tests + status.failed_tests)) * 100 if (status.completed_tests + status.failed_tests) > 0 else 0
            },
            "websocket_health": websocket_manager.get_statistics(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return health_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail="System health check failed")

# Startup and shutdown handlers for WebSocket manager

async def startup_websocket_manager():
    """Initialize WebSocket manager on application startup."""
    await websocket_manager.start()
    logger.info("Testing WebSocket manager started")

async def shutdown_websocket_manager():
    """Cleanup WebSocket manager on application shutdown."""
    await websocket_manager.stop()
    logger.info("Testing WebSocket manager stopped")

# Add these to your FastAPI app startup/shutdown events:
# app.add_event_handler("startup", startup_websocket_manager)
# app.add_event_handler("shutdown", shutdown_websocket_manager)