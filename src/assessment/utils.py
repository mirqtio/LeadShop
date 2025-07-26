"""
PRP-002: Assessment Utilities
Database utilities for updating assessment status and fields
"""

import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.core.database import get_db
from src.models.lead import Lead, Assessment
from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

def run_async_in_celery(async_func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    """
    Safely run async functions in Celery workers that don't have event loops.
    
    This function handles the event loop management for async functions
    called from synchronous Celery task contexts.
    
    Args:
        async_func: The async function to run
        *args: Positional arguments for the async function
        **kwargs: Keyword arguments for the async function
        
    Returns:
        The result of the async function
        
    Raises:
        Any exception raised by the async function
    """
    # First validate that we have an async function
    if not asyncio.iscoroutinefunction(async_func):
        raise TypeError(f"Function {async_func.__name__} is not an async function")
    
    logger.debug(f"Starting async execution for {async_func.__name__}")
    
    # Try different strategies for running the async function
    try:
        # Strategy 1: Check if there's a running event loop
        try:
            loop = asyncio.get_running_loop()
            logger.debug(f"Found running loop for {async_func.__name__}, using thread executor")
            # There's a running loop, we need to run in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run_async_in_new_loop, async_func, *args, **kwargs)
                result = future.result()
                logger.debug(f"Successfully completed {async_func.__name__} via thread executor")
                return result
        except RuntimeError:
            # No running loop, try to use existing loop for this thread
            logger.debug(f"No running loop found for {async_func.__name__}")
            pass
        
        # Strategy 2: Try to get the current thread's event loop
        try:
            # In Python 3.10+, get_event_loop() raises DeprecationWarning if no loop
            # In older versions, it creates a loop if none exists
            if hasattr(asyncio, 'get_running_loop'):
                # Python 3.7+ - be more careful about loop handling
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        logger.debug(f"Found running loop in thread for {async_func.__name__}, using new loop")
                        return _run_async_in_new_loop(async_func, *args, **kwargs)
                    else:
                        logger.debug(f"Using existing thread loop for {async_func.__name__}")
                        result = loop.run_until_complete(async_func(*args, **kwargs))
                        logger.debug(f"Successfully completed {async_func.__name__} via existing loop")
                        return result
                except RuntimeError:
                    # No loop for this thread
                    logger.debug(f"No existing loop for thread, creating new one for {async_func.__name__}")
                    return _run_async_in_new_loop(async_func, *args, **kwargs)
            else:
                # Python < 3.7 fallback
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(async_func(*args, **kwargs))
                logger.debug(f"Successfully completed {async_func.__name__} via legacy loop")
                return result
        except Exception as loop_error:
            logger.debug(f"Loop handling failed for {async_func.__name__}: {loop_error}")
            # Fall through to new loop strategy
    
    except Exception as e:
        logger.warning(f"Error in async execution strategy for {async_func.__name__}: {e}")
    
    # Strategy 3: Fallback - always create a new loop
    logger.debug(f"Falling back to new loop for {async_func.__name__}")
    return _run_async_in_new_loop(async_func, *args, **kwargs)

def _run_async_in_new_loop(async_func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    """Helper function to run async function in a new event loop."""
    import nest_asyncio
    # Allow nested event loops - this helps with asyncpg connections
    nest_asyncio.apply()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coro = None
    try:
        logger.debug(f"Created new event loop for {async_func.__name__}")
        coro = async_func(*args, **kwargs)
        if not asyncio.iscoroutine(coro):
            raise TypeError(f"Function {async_func.__name__} did not return a coroutine")
        
        # Ensure the coroutine gets awaited
        result = loop.run_until_complete(coro)
        logger.debug(f"Successfully awaited coroutine for {async_func.__name__}")
        return result
        
    except Exception as e:
        logger.error(f"Error in new event loop for {async_func.__name__}: {e}")
        # If we have a coroutine that wasn't awaited, close it to prevent warnings
        if coro is not None and asyncio.iscoroutine(coro):
            try:
                coro.close()
                logger.debug(f"Closed unawaited coroutine for {async_func.__name__}")
            except Exception:
                pass
        raise
    finally:
        try:
            # Cancel any remaining tasks
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.debug(f"Cleaning up {len(pending)} pending tasks")
                for task in pending:
                    task.cancel()
                # Give tasks a moment to cancel gracefully
                try:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass  # Tasks may already be cancelled
        except Exception as cleanup_error:
            logger.debug(f"Task cleanup completed with minor issues: {cleanup_error}")
        finally:
            try:
                loop.close()
                logger.debug(f"Closed event loop for {async_func.__name__}")
            except Exception as close_error:
                logger.debug(f"Loop closure completed: {close_error}")
            finally:
                # Clear the event loop for the thread
                asyncio.set_event_loop(None)

# Assessment status constants
ASSESSMENT_STATUS = {
    'PENDING': 'pending',
    'IN_PROGRESS': 'in_progress', 
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'VISUAL_COMPLETED': 'visual_completed',
    'SCORING_COMPLETED': 'scoring_completed',
    'CONTENT_COMPLETED': 'content_completed',
    'SETUP_COMPLETED': 'setup_completed'
}

class AssessmentError(Exception):
    """Custom exception for assessment errors"""
    pass

async def update_assessment_status(
    lead_id: str, 
    status: str, 
    error_message: Optional[str] = None
) -> bool:
    """
    Update assessment status with optional error message
    
    Args:
        lead_id: The lead ID to update
        status: New status value
        error_message: Optional error message if status is failed
        
    Returns:
        bool: True if update was successful
        
    Raises:
        AssessmentError: If lead not found or update fails
    """
    try:
        from src.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # First verify the lead exists
            lead_query = select(Lead).where(Lead.id == lead_id)
            result = await session.execute(lead_query)
            lead = result.scalar_one_or_none()
            
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            
            # Prepare update data
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if error_message:
                update_data["error_message"] = error_message
            
            # Update assessment via Lead relationship - get the most recent one
            assessment_query = (
                select(Assessment)
                .where(Assessment.lead_id == lead_id)
                .order_by(Assessment.created_at.desc())
                .limit(1)
            )
            assessment_result = await session.execute(assessment_query)
            assessment = assessment_result.scalar_one_or_none()
            
            if not assessment:
                raise AssessmentError(f"Assessment for lead {lead_id} not found")
            
            update_query = (
                update(Assessment)
                .where(Assessment.id == assessment.id)
                .values(**update_data)
            )
            
            await session.execute(update_query)
            await session.commit()
            
            logger.info(f"Updated assessment status for lead {lead_id}: {status}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update assessment status for lead {lead_id}: {e}")
        raise AssessmentError(f"Database update failed: {e}")


def sync_update_assessment_field(
    lead_id: str, 
    field_name: str, 
    field_value: Any,
    merge_dict: bool = False
) -> bool:
    """
    Synchronous version of update_assessment_field for Celery workers
    """
    try:
        from src.core.database import SyncSessionLocal
        from sqlalchemy import select, update
        
        with SyncSessionLocal() as session:
            # Get current assessment - get the most recent one if multiple exist
            assessment_query = (
                select(Assessment)
                .where(Assessment.lead_id == lead_id)
                .order_by(Assessment.created_at.desc())
                .limit(1)
            )
            result = session.execute(assessment_query)
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise AssessmentError(f"Assessment for lead {lead_id} not found")
            
            # Handle dictionary merging
            if merge_dict and isinstance(field_value, dict):
                current_data = getattr(assessment, field_name) or {}
                if isinstance(current_data, dict):
                    current_data.update(field_value)
                    field_value = current_data
            
            # Update the field - use specific assessment ID to avoid conflicts
            update_query = (
                update(Assessment)
                .where(Assessment.id == assessment.id)
                .values({
                    field_name: field_value,
                    "updated_at": datetime.now(timezone.utc)
                })
            )
            
            session.execute(update_query)
            session.commit()
            
            logger.debug(f"Updated assessment field {field_name} for lead {lead_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update assessment field {field_name} for lead {lead_id}: {e}")
        raise AssessmentError(f"Field update failed: {e}")

async def update_assessment_field(
    lead_id: str, 
    field_name: str, 
    field_value: Any,
    merge_dict: bool = False
) -> bool:
    """
    Update a specific field in the assessment data
    
    Args:
        lead_id: The lead ID to update
        field_name: Name of the field to update
        field_value: Value to set for the field
        merge_dict: If True and field_value is dict, merge with existing data
        
    Returns:
        bool: True if update was successful
        
    Raises:
        AssessmentError: If lead not found or update fails
    """
    try:
        from src.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # Get current assessment - get the most recent one if multiple exist
            assessment_query = (
                select(Assessment)
                .where(Assessment.lead_id == lead_id)
                .order_by(Assessment.created_at.desc())
                .limit(1)
            )
            result = await session.execute(assessment_query)
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise AssessmentError(f"Assessment for lead {lead_id} not found")
            
            # Handle dictionary merging
            if merge_dict and isinstance(field_value, dict):
                current_data = getattr(assessment, field_name) or {}
                if isinstance(current_data, dict):
                    current_data.update(field_value)
                    field_value = current_data
            
            # Update the field - use specific assessment ID to avoid conflicts
            update_query = (
                update(Assessment)
                .where(Assessment.id == assessment.id)
                .values({
                    field_name: field_value,
                    "updated_at": datetime.now(timezone.utc)
                })
            )
            
            await session.execute(update_query)
            await session.commit()
            
            logger.debug(f"Updated assessment field {field_name} for lead {lead_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update assessment field {field_name} for lead {lead_id}: {e}")
        raise AssessmentError(f"Field update failed: {e}")


def sync_update_assessment_status(
    lead_id: str, 
    status: str, 
    error_message: Optional[str] = None
) -> bool:
    """
    Synchronous version of update_assessment_status for Celery workers
    """
    try:
        from src.core.database import SyncSessionLocal
        from sqlalchemy import select, update
        
        with SyncSessionLocal() as session:
            # First verify the lead exists
            lead_query = select(Lead).where(Lead.id == lead_id)
            result = session.execute(lead_query)
            lead = result.scalar_one_or_none()
            
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            
            # Prepare update data
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if error_message:
                update_data["error_message"] = error_message
            
            # Update assessment via Lead relationship - get the most recent one
            assessment_query = (
                select(Assessment)
                .where(Assessment.lead_id == lead_id)
                .order_by(Assessment.created_at.desc())
                .limit(1)
            )
            assessment_result = session.execute(assessment_query)
            assessment = assessment_result.scalar_one_or_none()
            
            if not assessment:
                raise AssessmentError(f"Assessment for lead {lead_id} not found")
            
            update_query = (
                update(Assessment)
                .where(Assessment.id == assessment.id)
                .values(**update_data)
            )
            
            session.execute(update_query)
            session.commit()
            
            logger.info(f"Updated assessment status for lead {lead_id}: {status}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update assessment status for lead {lead_id}: {e}")
        raise AssessmentError(f"Database update failed: {e}")


def sync_get_lead_info(lead_id: str, fields: Optional[list] = None):
    """
    Synchronous version of get lead info for Celery workers
    
    Args:
        lead_id: The lead ID to retrieve
        fields: Optional list of specific fields to return. 
               If None, returns (url, company) for backward compatibility.
               If provided, returns values in order specified.
    """
    try:
        from src.core.database import SyncSessionLocal
        from sqlalchemy import select
        
        with SyncSessionLocal() as session:
            result = session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            
            # If no specific fields requested, return backward compatible format
            if fields is None:
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for assessment")
                return lead.url, lead.company
            
            # Return requested fields in order
            result_values = []
            for field in fields:
                value = getattr(lead, field, None)
                result_values.append(value)
            
            return tuple(result_values)
            
    except Exception as e:
        logger.error(f"Failed to get lead info for lead {lead_id}: {e}")
        raise AssessmentError(f"Lead retrieval failed: {e}")


def sync_assess_google_business_profile(business_name: str, address: Optional[str] = None, 
                                       city: Optional[str] = None, state: Optional[str] = None,
                                       lead_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Synchronous wrapper for assess_google_business_profile async function
    
    Args:
        business_name: Name of the business to search for
        address: Business address (optional)
        city: Business city (optional) 
        state: Business state (optional)
        lead_id: Lead ID for cost tracking (optional)
        
    Returns:
        Dict containing GBP assessment results
    """
    import asyncio
    
    try:
        from src.assessments.gbp_integration import assess_google_business_profile
        
        # Create and run new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(assess_google_business_profile(
                business_name=business_name,
                address=address,
                city=city,
                state=state,
                lead_id=lead_id
            ))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to execute GBP assessment: {e}")
        raise AssessmentError(f"GBP assessment failed: {e}")


def sync_store_cost_records(cost_records: list) -> bool:
    """
    Synchronous function to store cost records in database
    
    Args:
        cost_records: List of cost record objects to store
        
    Returns:
        bool: True if successful
    """
    try:
        from src.core.database import SyncSessionLocal
        
        with SyncSessionLocal() as session:
            for cost_record in cost_records:
                session.add(cost_record)
            session.commit()
            
            logger.debug(f"Stored {len(cost_records)} cost records")
            return True
            
    except Exception as e:
        logger.error(f"Failed to store cost records: {e}")
        raise AssessmentError(f"Cost record storage failed: {e}")


# Test function for async handling
async def _test_async_function(test_arg: str = "test") -> str:
    """Simple async function for testing the run_async_in_celery function."""
    await asyncio.sleep(0.1)  # Simulate some async work
    return f"async_result_{test_arg}"


def test_async_handling() -> bool:
    """
    Test function to verify async handling works correctly.
    
    Returns:
        bool: True if async handling is working correctly
    """
    try:
        result = run_async_in_celery(_test_async_function, "hello")
        expected = "async_result_hello"
        
        if result == expected:
            logger.info("Async handling test passed")
            return True
        else:
            logger.error(f"Async handling test failed: expected {expected}, got {result}")
            return False
            
    except Exception as e:
        logger.error(f"Async handling test error: {e}")
        return False


def debug_async_function_call(func_name: str, async_func: Callable, *args, **kwargs):
    """
    Debug helper to validate async function calls in tasks.
    
    Args:
        func_name: Name of the function for logging
        async_func: The async function to call
        *args: Arguments to pass
        **kwargs: Keyword arguments to pass
        
    Returns:
        Result of the async function call
    """
    logger.info(f"Debug: Calling async function {func_name}")
    logger.debug(f"Function is coroutine function: {asyncio.iscoroutinefunction(async_func)}")
    
    try:
        result = run_async_in_celery(async_func, *args, **kwargs)
        logger.info(f"Debug: {func_name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Debug: {func_name} failed with error: {e}")
        logger.exception("Full traceback:")
        raise


def serialize_assessment_cost(cost_record) -> Dict[str, Any]:
    """
    Convert AssessmentCost object to JSON-serializable dictionary
    
    Args:
        cost_record: AssessmentCost object to serialize
        
    Returns:
        Dict containing serializable cost record data
    """
    from src.models.assessment_cost import AssessmentCost
    
    if not isinstance(cost_record, AssessmentCost):
        return cost_record
    
    return {
        "id": cost_record.id,
        "lead_id": cost_record.lead_id,
        "assessment_id": cost_record.assessment_id,
        "service_name": cost_record.service_name,
        "api_endpoint": cost_record.api_endpoint,
        "cost_cents": cost_record.cost_cents,
        "cost_dollars": cost_record.cost_dollars,
        "currency": cost_record.currency,
        "request_timestamp": cost_record.request_timestamp.isoformat() if cost_record.request_timestamp else None,
        "response_status": cost_record.response_status,
        "response_time_ms": cost_record.response_time_ms,
        "api_quota_used": cost_record.api_quota_used,
        "rate_limited": cost_record.rate_limited,
        "retry_count": cost_record.retry_count,
        "error_code": cost_record.error_code,
        "error_message": cost_record.error_message,
        "daily_budget_date": cost_record.daily_budget_date,
        "monthly_budget_date": cost_record.monthly_budget_date
    }


def prepare_assessment_data_for_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare assessment data for JSON storage by handling non-serializable objects
    
    Args:
        data: Assessment data dictionary that may contain AssessmentCost objects
        
    Returns:
        Dict with all non-serializable objects converted to serializable format
    """
    if not isinstance(data, dict):
        return data
    
    cleaned_data = {}
    
    for key, value in data.items():
        if key == "cost_records" and isinstance(value, list):
            # Convert AssessmentCost objects to serializable dictionaries
            cleaned_data[key] = [serialize_assessment_cost(record) for record in value]
        elif isinstance(value, dict):
            # Recursively clean nested dictionaries
            cleaned_data[key] = prepare_assessment_data_for_storage(value)
        elif isinstance(value, list):
            # Handle lists that might contain non-serializable objects
            cleaned_list = []
            for item in value:
                if hasattr(item, '__tablename__'):
                    # SQLAlchemy model
                    cleaned_list.append(serialize_assessment_cost(item))
                elif hasattr(item, 'dict') and callable(getattr(item, 'dict')):
                    # Pydantic model with dict() method
                    cleaned_list.append(item.dict())
                elif hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool, type(None))):
                    # Object with __dict__ attribute (like dataclasses)
                    cleaned_list.append(item.__dict__)
                elif isinstance(item, dict):
                    # Nested dictionary
                    cleaned_list.append(prepare_assessment_data_for_storage(item))
                else:
                    # Primitive types or already serializable
                    cleaned_list.append(item)
            cleaned_data[key] = cleaned_list
        elif hasattr(value, 'dict') and callable(getattr(value, 'dict')):
            # Pydantic model with dict() method
            cleaned_data[key] = value.dict()
        elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
            # Object with __dict__ attribute (like dataclasses)
            cleaned_data[key] = value.__dict__
        else:
            cleaned_data[key] = value
    
    return cleaned_data
