"""
Integration tests for PRP-003 PageSpeed Integration
Tests complete workflow from task execution to database storage
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessment.orchestrator import coordinate_assessment
from src.assessment.tasks import pagespeed_task
from src.models.lead import Lead, Assessment
from src.models.assessment_cost import AssessmentCost
from src.core.database import get_db


@pytest.mark.integration
class TestPageSpeedTaskIntegration:
    """Test PageSpeed task integration with database and orchestrator"""
    
    @pytest.fixture
    async def test_lead(self, async_db_session):
        """Create test lead for assessment"""
        lead = Lead(
            company="Test Company",
            email="test@example.com",
            source="test",
            url="https://example.com",
            city="San Francisco",
            state="CA"
        )
        
        async_db_session.add(lead)
        await async_db_session.commit()
        await async_db_session.refresh(lead)
        
        return lead
    
    @pytest.fixture
    def mock_pagespeed_response(self):
        """Mock successful PageSpeed assessment response"""
        return {
            "url": "https://example.com",
            "company": "Test Company",
            "mobile_analysis": {
                "url": "https://example.com",
                "strategy": "mobile",
                "core_web_vitals": {
                    "first_contentful_paint": 1200.5,
                    "largest_contentful_paint": 2800.3,
                    "cumulative_layout_shift": 0.12,
                    "total_blocking_time": 150.0,
                    "time_to_interactive": 3200.8,
                    "performance_score": 85
                },
                "lighthouse_result": {
                    "categories": {
                        "performance": {"score": 0.85},
                        "accessibility": {"score": 0.92}
                    }
                },
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_duration_ms": 5000,
                "cost_cents": 0.25
            },
            "desktop_analysis": {
                "url": "https://example.com", 
                "strategy": "desktop",
                "core_web_vitals": {"performance_score": 90},
                "cost_cents": 0.25
            },
            "primary_strategy": "mobile",
            "core_web_vitals": {
                "first_contentful_paint": 1200.5,
                "largest_contentful_paint": 2800.3,
                "cumulative_layout_shift": 0.12,
                "total_blocking_time": 150.0,
                "time_to_interactive": 3200.8,
                "performance_score": 85
            },
            "performance_score": 85,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cost_cents": 0.5,
            "api_calls_made": 2,
            "cost_records": []  # Will be populated in test
        }
    
    @pytest.mark.asyncio
    async def test_pagespeed_task_success(self, test_lead, async_db_session, mock_pagespeed_response):
        """Test successful PageSpeed task execution"""
        # Create mock cost records
        cost_records = [
            AssessmentCost.create_pagespeed_cost(
                lead_id=test_lead.id,
                cost_cents=0.25,
                response_status="success",
                response_time_ms=5000
            ),
            AssessmentCost.create_pagespeed_cost(
                lead_id=test_lead.id,
                cost_cents=0.25,
                response_status="success", 
                response_time_ms=4500
            )
        ]
        mock_pagespeed_response["cost_records"] = cost_records
        
        with patch('src.assessments.pagespeed.assess_pagespeed', return_value=mock_pagespeed_response):
            # Create mock Celery task context
            mock_task = Mock()
            mock_task.request.hostname = "test-worker"
            mock_task.request.retries = 0
            
            # Execute PageSpeed task
            result = pagespeed_task(mock_task, test_lead.id)
            
            # Verify task result
            assert result["lead_id"] == test_lead.id
            assert result["task"] == "pagespeed"
            assert result["status"] == "completed"
            assert result["score"] == 85
            assert result["url_analyzed"] == "https://example.com"
            assert result["company"] == "Test Company"
            
            # Verify database was updated
            await async_db_session.refresh(test_lead)
            assessment = await async_db_session.get(Assessment, {"lead_id": test_lead.id})
            
            assert assessment.pagespeed_score == 85
            assert assessment.pagespeed_data["performance_score"] == 85
            assert assessment.pagespeed_data["primary_strategy"] == "mobile"
            
            # Verify cost records were stored
            cost_records_db = await async_db_session.execute(
                "SELECT * FROM assessment_costs WHERE lead_id = :lead_id",
                {"lead_id": test_lead.id}
            )
            costs = cost_records_db.fetchall()
            
            assert len(costs) == 2
            assert all(cost.service_name == "pagespeed" for cost in costs)
            assert sum(cost.cost_cents for cost in costs) == 0.5
    
    @pytest.mark.asyncio
    async def test_pagespeed_task_api_error(self, test_lead, async_db_session):
        """Test PageSpeed task with API error"""
        from src.assessments.pagespeed import PageSpeedError
        
        with patch('src.assessments.pagespeed.assess_pagespeed', side_effect=PageSpeedError("API failed")):
            mock_task = Mock()
            mock_task.request.hostname = "test-worker"
            mock_task.request.retries = 3  # Max retries reached
            
            # Task should return error result instead of raising
            result = pagespeed_task(mock_task, test_lead.id)
            
            assert result["lead_id"] == test_lead.id
            assert result["task"] == "pagespeed"
            assert result["status"] == "failed"
            assert "API failed" in result["error"]
            
            # Verify error was stored in database
            await async_db_session.refresh(test_lead)
            assessment = await async_db_session.get(Assessment, {"lead_id": test_lead.id})
            
            assert assessment.pagespeed_score == 0
            assert "error" in assessment.pagespeed_data
    
    @pytest.mark.asyncio
    async def test_pagespeed_task_timeout_retry(self, test_lead):
        """Test PageSpeed task retry logic on timeout"""
        from src.assessments.pagespeed import PageSpeedError
        
        with patch('src.assessments.pagespeed.assess_pagespeed', side_effect=PageSpeedError("timed out")):
            mock_task = Mock()
            mock_task.request.hostname = "test-worker"
            mock_task.request.retries = 1  # Still has retries left
            mock_task.retry = Mock(side_effect=Exception("Retry called"))
            
            # Task should call retry()
            with pytest.raises(Exception, match="Retry called"):
                pagespeed_task(mock_task, test_lead.id)
            
            # Verify retry was called with exponential backoff
            mock_task.retry.assert_called_once()
            retry_args = mock_task.retry.call_args
            assert retry_args[1]["countdown"] == 2  # 2^1 for retry 1


@pytest.mark.integration
class TestPageSpeedOrchestrationIntegration:
    """Test PageSpeed integration with assessment orchestrator"""
    
    @pytest.fixture
    async def test_lead_with_assessment(self, async_db_session):
        """Create test lead with assessment record"""
        lead = Lead(
            company="Test Company",
            email="test@example.com", 
            source="test",
            url="https://example.com"
        )
        
        async_db_session.add(lead)
        await async_db_session.commit()
        await async_db_session.refresh(lead)
        
        assessment = Assessment(
            lead_id=lead.id,
            status="pending",
            created_at=datetime.now(timezone.utc)
        )
        
        async_db_session.add(assessment)
        await async_db_session.commit()
        await async_db_session.refresh(assessment)
        
        return lead, assessment
    
    @pytest.mark.asyncio
    async def test_orchestrator_includes_pagespeed(self, test_lead_with_assessment):
        """Test that orchestrator includes PageSpeed in assessment pipeline"""
        lead, assessment = test_lead_with_assessment
        
        # Mock all assessment tasks to avoid external API calls
        with patch('src.assessment.tasks.pagespeed_task') as mock_pagespeed, \
             patch('src.assessment.tasks.security_task') as mock_security, \
             patch('src.assessment.tasks.gbp_task') as mock_gbp, \
             patch('src.assessment.tasks.semrush_task') as mock_semrush, \
             patch('src.assessment.tasks.visual_task') as mock_visual, \
             patch('src.assessment.tasks.aggregate_results') as mock_aggregate:
            
            # Configure mock returns
            mock_pagespeed.s.return_value = Mock()
            mock_security.s.return_value = Mock()
            mock_gbp.s.return_value = Mock()
            mock_semrush.s.return_value = Mock()
            mock_visual.s.return_value = Mock()
            
            # Mock Celery task execution
            mock_task = Mock()
            mock_task.request.id = "test-task-id"
            mock_task.request.hostname = "test-worker"
            mock_task.request.delivery_info = {"routing_key": "assessment"}
            
            with patch('celery.group') as mock_group, \
                 patch('celery.chord') as mock_chord:
                
                mock_chord_result = Mock()
                mock_chord_result.id = "chord-123"
                mock_chord.return_value = mock_chord_result
                
                # Execute coordination
                result = coordinate_assessment(mock_task, lead.id)
                
                # Verify PageSpeed task was included in parallel group
                mock_group.assert_called_once()
                group_args = mock_group.call_args[0][0]
                
                # Should include pagespeed_task along with other tasks
                assert len(group_args) == 5  # pagespeed, security, gbp, semrush, visual
                mock_pagespeed.s.assert_called_once_with(lead.id)
                
                # Verify coordination result includes PageSpeed
                assert result["lead_id"] == lead.id
                assert result["assessment_id"] == assessment.id
                assert result["status"] == "coordinating"


@pytest.mark.integration
class TestPageSpeedCostTracking:
    """Test cost tracking integration for PageSpeed assessments"""
    
    @pytest.fixture
    async def test_lead(self, async_db_session):
        """Create test lead for cost tracking"""
        lead = Lead(
            company="Cost Test Company",
            email="cost@example.com",
            source="test",
            url="https://example.com"
        )
        
        async_db_session.add(lead)
        await async_db_session.commit()
        await async_db_session.refresh(lead)
        
        return lead
    
    @pytest.mark.asyncio
    async def test_cost_record_creation(self, test_lead, async_db_session):
        """Test that cost records are created for PageSpeed calls"""
        # Create cost records
        mobile_cost = AssessmentCost.create_pagespeed_cost(
            lead_id=test_lead.id,
            cost_cents=0.25,
            response_status="success",
            response_time_ms=5000,
            api_quota_used=False
        )
        
        desktop_cost = AssessmentCost.create_pagespeed_cost(
            lead_id=test_lead.id,
            cost_cents=0.25,
            response_status="success",
            response_time_ms=4500,
            api_quota_used=False
        )
        
        async_db_session.add(mobile_cost)
        async_db_session.add(desktop_cost)
        await async_db_session.commit()
        
        # Verify cost records
        assert mobile_cost.lead_id == test_lead.id
        assert mobile_cost.service_name == "pagespeed"
        assert mobile_cost.cost_cents == 0.25
        assert mobile_cost.cost_dollars == 0.0025
        assert mobile_cost.response_status == "success"
        assert mobile_cost.response_time_ms == 5000
        
        # Test daily cost calculation
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_cost = AssessmentCost.get_daily_cost(async_db_session, today, "pagespeed")
        assert daily_cost == 0.5  # 0.25 + 0.25
        
        # Test monthly cost calculation
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        monthly_cost = AssessmentCost.get_monthly_cost(async_db_session, this_month, "pagespeed")
        assert monthly_cost == 0.5
        
        # Test quota usage tracking
        quota_usage = AssessmentCost.get_quota_usage_today(async_db_session, "pagespeed")
        assert quota_usage == 2  # Two successful API calls
    
    @pytest.mark.asyncio
    async def test_error_cost_tracking(self, test_lead, async_db_session):
        """Test cost tracking for failed PageSpeed requests"""
        error_cost = AssessmentCost.create_pagespeed_cost(
            lead_id=test_lead.id,
            cost_cents=0.0,  # No cost for failed requests
            response_status="error",
            error_code="timeout",
            error_message="Request timed out after 30 seconds"
        )
        
        async_db_session.add(error_cost)
        await async_db_session.commit()
        
        # Verify error tracking
        assert error_cost.cost_cents == 0.0
        assert error_cost.response_status == "error"
        assert error_cost.error_code == "timeout"
        assert "timed out" in error_cost.error_message
        
        # Failed requests don't count toward quota
        quota_usage = AssessmentCost.get_quota_usage_today(async_db_session, "pagespeed")
        assert quota_usage == 0


@pytest.mark.integration
class TestPageSpeedEndToEnd:
    """End-to-end integration tests for complete PageSpeed workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_pagespeed_workflow(self, async_db_session):
        """Test complete workflow from lead creation to assessment completion"""
        # Create test lead
        lead = Lead(
            company="E2E Test Company",
            email="e2e@example.com",
            source="test",
            url="https://web.dev"  # Use a known good URL
        )
        
        async_db_session.add(lead)
        await async_db_session.commit()
        await async_db_session.refresh(lead)
        
        # Mock successful PageSpeed assessment
        mock_assessment_data = {
            "url": "https://web.dev",
            "company": "E2E Test Company",
            "performance_score": 95,
            "total_cost_cents": 0.5,
            "api_calls_made": 2,
            "cost_records": [
                AssessmentCost.create_pagespeed_cost(
                    lead_id=lead.id,
                    cost_cents=0.25,
                    response_status="success"
                ),
                AssessmentCost.create_pagespeed_cost(
                    lead_id=lead.id, 
                    cost_cents=0.25,
                    response_status="success"
                )
            ],
            "core_web_vitals": {
                "first_contentful_paint": 800.0,
                "largest_contentful_paint": 1200.0,
                "cumulative_layout_shift": 0.05,
                "performance_score": 95
            }
        }
        
        with patch('src.assessments.pagespeed.assess_pagespeed', return_value=mock_assessment_data):
            # Execute PageSpeed task directly
            mock_task = Mock()
            mock_task.request.hostname = "test-worker"
            mock_task.request.retries = 0
            
            result = pagespeed_task(mock_task, lead.id)
            
            # Verify complete workflow success
            assert result["status"] == "completed"
            assert result["score"] == 95
            assert result["url_analyzed"] == "https://web.dev"
            
            # Verify database state
            await async_db_session.refresh(lead)
            
            # Check assessment was created and updated
            assessment = await async_db_session.execute(
                "SELECT * FROM assessments WHERE lead_id = :lead_id",
                {"lead_id": lead.id}
            )
            assessment_record = assessment.fetchone()
            
            assert assessment_record.pagespeed_score == 95
            assert assessment_record.pagespeed_data["performance_score"] == 95
            
            # Check cost records were stored
            cost_records = await async_db_session.execute(
                "SELECT * FROM assessment_costs WHERE lead_id = :lead_id",
                {"lead_id": lead.id}
            )
            costs = cost_records.fetchall()
            
            assert len(costs) == 2
            assert all(cost.service_name == "pagespeed" for cost in costs)
            assert sum(cost.cost_cents for cost in costs) == 0.5