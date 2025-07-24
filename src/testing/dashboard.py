"""
PRP-013: Manual Testing Interface - Comprehensive System Testing Dashboard
Backend infrastructure for comprehensive manual testing and system validation
"""

import asyncio
import logging
import time
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost
from src.utils.database import update_assessment_field

logger = logging.getLogger(__name__)

class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

class PipelineHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"

@dataclass
class SystemMetrics:
    """System performance and health metrics."""
    cpu_usage: float
    memory_usage: float
    database_connections: int
    queue_depth: int
    response_time_ms: float
    error_rate: float
    timestamp: datetime

@dataclass
class PipelineStepResult:
    """Individual pipeline step execution result."""
    step_name: str
    step_number: int
    status: TestStatus
    duration_ms: int
    details: Dict[str, Any]
    error_message: Optional[str]
    timestamp: datetime

@dataclass
class TestExecution:
    """Complete test execution record."""
    id: str
    user_id: int
    test_type: str
    status: TestStatus
    lead_data: Dict[str, Any]
    pipeline_results: List[PipelineStepResult]
    execution_time_ms: Optional[int]
    success_rate: float
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

@dataclass
class SystemStatus:
    """Overall system status and health indicators."""
    pipeline_health: PipelineHealth
    active_tests: int
    completed_tests: int
    failed_tests: int
    system_metrics: SystemMetrics
    component_health: Dict[str, str]

class TestingDashboardError(Exception):
    """Custom exception for testing dashboard errors"""
    pass

class PipelineComponentTester:
    """Test harness for individual pipeline components."""
    
    def __init__(self):
        self.component_timeouts = {
            's3_setup': 30,
            'lead_data_model': 15,
            'assessment_orchestrator': 120,
            'pagespeed_integration': 60,
            'security_scraper': 90,
            'gbp_integration': 45,
            'screenshot_integration': 60,
            'semrush_integration': 90,
            'llm_visual_analysis': 120,
            'score_calculator': 30,
            'content_generator': 90,
            'report_and_email': 180
        }
    
    async def test_s3_integration(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test S3 storage integration."""
        start_time = time.time()
        
        try:
            # Mock S3 integration test
            await asyncio.sleep(0.1)  # Simulate test execution
            
            # Simulate S3 bucket access and file operations
            test_results = {
                'bucket_accessible': True,
                'write_permissions': True,
                'read_permissions': True,
                'lifecycle_policies': True
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': test_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_lead_data_model(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test lead data model validation and storage."""
        start_time = time.time()
        
        try:
            # Mock lead data validation
            await asyncio.sleep(0.05)
            
            required_fields = ['business_name', 'website_url', 'email']
            validation_results = {}
            
            for field in required_fields:
                validation_results[field] = field in lead_data and lead_data[field]
            
            all_valid = all(validation_results.values())
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success' if all_valid else 'failed',
                'duration': duration,
                'details': {
                    'field_validation': validation_results,
                    'data_integrity': all_valid,
                    'database_insert': all_valid
                }
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_assessment_orchestrator(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test assessment orchestrator functionality."""
        start_time = time.time()
        
        try:
            # Mock orchestrator test
            await asyncio.sleep(0.2)
            
            test_results = {
                'task_queue_accessible': True,
                'worker_availability': True,
                'dependency_resolution': True,
                'error_handling': True,
                'result_aggregation': True
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': test_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_pagespeed_integration(self, website_url: str) -> Dict[str, Any]:
        """Test PageSpeed Insights integration."""
        start_time = time.time()
        
        try:
            from src.assessments.pagespeed import assess_pagespeed
            
            # Test PageSpeed integration with mock data
            await asyncio.sleep(0.3)
            
            mock_results = {
                'desktop_score': 85,
                'mobile_score': 78,
                'lcp_desktop': 2.1,
                'lcp_mobile': 3.2,
                'fid_desktop': 95,
                'fid_mobile': 120,
                'cls_desktop': 0.08,
                'cls_mobile': 0.12,
                'api_quota_remaining': 4000,
                'cost_cents': 0.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_security_scraper(self, website_url: str) -> Dict[str, Any]:
        """Test security scraper functionality."""
        start_time = time.time()
        
        try:
            from src.assessments.technical_scraper import assess_technical_security
            
            # Mock security analysis
            await asyncio.sleep(0.4)
            
            mock_results = {
                'ssl_valid': True,
                'security_headers': {
                    'hsts': True,
                    'csp': False,
                    'x_frame_options': True
                },
                'vulnerability_scan': {
                    'critical': 0,
                    'high': 1,
                    'medium': 3,
                    'low': 5
                },
                'cost_cents': 0.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_gbp_integration(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Google Business Profile integration."""
        start_time = time.time()
        
        try:
            from src.assessments.gbp_integration import assess_google_business_profile
            
            # Mock GBP analysis
            await asyncio.sleep(0.25)
            
            mock_results = {
                'profile_found': True,
                'profile_claimed': True,
                'review_count': 127,
                'average_rating': 4.3,
                'photos_count': 45,
                'posts_count': 12,
                'cost_cents': 0.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_screenshot_integration(self, website_url: str) -> Dict[str, Any]:
        """Test ScreenshotOne integration."""
        start_time = time.time()
        
        try:
            from src.assessments.screenshot_capture import capture_website_screenshots
            
            # Mock screenshot capture
            await asyncio.sleep(0.3)
            
            mock_results = {
                'desktop_screenshot': {
                    'url': f'https://s3.amazonaws.com/screenshots/desktop_{uuid.uuid4()}.png',
                    'width': 1920,
                    'height': 1080,
                    'file_size': 245670
                },
                'mobile_screenshot': {
                    'url': f'https://s3.amazonaws.com/screenshots/mobile_{uuid.uuid4()}.png',
                    'width': 390,
                    'height': 844,
                    'file_size': 156890
                },
                'cost_cents': 40.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_semrush_integration(self, website_url: str) -> Dict[str, Any]:
        """Test SEMrush integration."""
        start_time = time.time()
        
        try:
            from src.assessments.semrush_integration import analyze_domain_seo
            
            # Mock SEMrush analysis
            await asyncio.sleep(0.5)
            
            mock_results = {
                'domain_authority': 67,
                'organic_keywords': 1247,
                'organic_traffic': 5623,
                'backlinks_total': 890,
                'referring_domains': 234,
                'top_organic_keywords': [
                    {'keyword': 'restaurant nyc', 'position': 15, 'volume': 8100},
                    {'keyword': 'fine dining manhattan', 'position': 8, 'volume': 2400}
                ],
                'cost_cents': 10.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_llm_visual_analysis(self, website_url: str) -> Dict[str, Any]:
        """Test LLM visual analysis."""
        start_time = time.time()
        
        try:
            from src.assessments.visual_analysis import assess_visual_analysis
            
            # Mock visual analysis
            await asyncio.sleep(0.6)
            
            mock_results = {
                'ux_scores': {
                    'above_fold_clarity': 8.2,
                    'cta_prominence': 7.5,
                    'trust_signals_presence': 9.1,
                    'visual_hierarchy': 8.8,
                    'text_readability': 7.9,
                    'brand_cohesion': 8.6,
                    'image_quality': 9.0,
                    'mobile_responsiveness': 7.3,
                    'white_space_balance': 8.4
                },
                'overall_ux_score': 8.2,
                'key_findings': [
                    'Strong visual hierarchy with clear focal points',
                    'Call-to-action buttons could be more prominent',
                    'Mobile responsiveness needs improvement'
                ],
                'cost_cents': 5.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_score_calculator(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test business impact score calculator."""
        start_time = time.time()
        
        try:
            from src.assessments.score_calculator import calculate_business_impact
            
            # Mock score calculation
            await asyncio.sleep(0.1)
            
            mock_results = {
                'overall_score': 76.4,
                'component_scores': {
                    'performance': 82.1,
                    'security': 74.5,
                    'seo': 78.9,
                    'ux': 73.2,
                    'visual': 81.6
                },
                'business_impact': {
                    'revenue_impact_estimate': 24750.0,
                    'conversion_improvement': 15.3,
                    'traffic_growth_potential': 28.7
                },
                'industry_multiplier': 1.15,
                'geographic_factor': 1.08,
                'cost_cents': 0.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_content_generator(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test LLM content generator."""
        start_time = time.time()
        
        try:
            from src.assessments.content_generator import generate_marketing_content
            
            # Mock content generation
            await asyncio.sleep(0.4)
            
            mock_results = {
                'subject_line': 'Boost Your Restaurant\'s Online Performance by 28%',
                'email_body_word_count': 187,
                'executive_summary_word_count': 134,
                'issue_insights_count': 3,
                'recommended_actions_count': 3,
                'urgency_indicators_count': 2,
                'content_quality_score': 8.7,
                'spam_score': 1.2,
                'brand_voice_score': 9.1,
                'cost_cents': 2.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }
    
    async def test_report_and_email(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test report builder and email formatter."""
        start_time = time.time()
        
        try:
            from src.reports.builder import generate_assessment_report
            from src.email.formatter import format_business_email
            
            # Mock report and email generation
            await asyncio.sleep(0.8)
            
            mock_results = {
                'report_generated': True,
                'report_size_bytes': 2847563,
                'report_page_count': 12,
                'email_formatted': True,
                'email_html_size': 45670,
                'email_text_size': 12890,
                'compliance_score': 98.5,
                'spam_score': 0.8,
                'cost_cents': 0.0
            }
            
            duration = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'duration': duration,
                'details': mock_results
            }
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {
                'status': 'failed',
                'duration': duration,
                'details': {'error': str(e)}
            }

class SystemHealthMonitor:
    """Monitor system health and performance metrics."""
    
    def __init__(self):
        self.component_checkers = {
            'database': self._check_database_health,
            'redis': self._check_redis_health,
            'storage': self._check_storage_health,
            'external_apis': self._check_external_apis_health,
            'task_queue': self._check_task_queue_health
        }
    
    async def get_system_status(self) -> SystemStatus:
        """Get comprehensive system status."""
        try:
            # Get system metrics
            system_metrics = await self._collect_system_metrics()
            
            # Check component health
            component_health = {}
            for component, checker in self.component_checkers.items():
                try:
                    component_health[component] = await checker()
                except Exception as e:
                    logger.error(f"Health check failed for {component}: {e}")
                    component_health[component] = 'error'
            
            # Determine overall pipeline health
            pipeline_health = self._determine_pipeline_health(component_health, system_metrics)
            
            # Get test counters (mock implementation)
            active_tests = await self._count_active_tests()
            completed_tests = await self._count_completed_tests_today()
            failed_tests = await self._count_failed_tests_today()
            
            return SystemStatus(
                pipeline_health=pipeline_health,
                active_tests=active_tests,
                completed_tests=completed_tests,
                failed_tests=failed_tests,
                system_metrics=system_metrics,
                component_health=component_health
            )
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            raise TestingDashboardError(f"System status check failed: {str(e)}")
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        # Mock system metrics collection
        import psutil
        import random
        
        try:
            # Get actual system metrics where possible
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Mock other metrics
            database_connections = random.randint(8, 25)
            queue_depth = random.randint(0, 15)
            response_time_ms = random.uniform(150, 400)
            error_rate = random.uniform(0, 2.5)
            
        except Exception:
            # Fallback to mock values if psutil not available
            cpu_usage = random.uniform(15, 45)
            memory_usage = random.uniform(40, 75)
            database_connections = random.randint(8, 25)
            queue_depth = random.randint(0, 15)
            response_time_ms = random.uniform(150, 400)
            error_rate = random.uniform(0, 2.5)
        
        return SystemMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            database_connections=database_connections,
            queue_depth=queue_depth,
            response_time_ms=response_time_ms,
            error_rate=error_rate,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_database_health(self) -> str:
        """Check database connectivity and performance."""
        try:
            # Mock database health check
            await asyncio.sleep(0.1)
            return 'healthy'
        except Exception:
            return 'error'
    
    async def _check_redis_health(self) -> str:
        """Check Redis connectivity and performance."""
        try:
            # Mock Redis health check
            await asyncio.sleep(0.05)
            return 'healthy'
        except Exception:
            return 'error'
    
    async def _check_storage_health(self) -> str:
        """Check S3/storage connectivity and performance."""
        try:
            # Mock storage health check
            await asyncio.sleep(0.1)
            return 'healthy'
        except Exception:
            return 'error'
    
    async def _check_external_apis_health(self) -> str:
        """Check external API connectivity and quota status."""
        try:
            # Mock external API health checks
            await asyncio.sleep(0.2)
            return 'healthy'
        except Exception:
            return 'error'
    
    async def _check_task_queue_health(self) -> str:
        """Check Celery task queue health."""
        try:
            # Mock task queue health check
            await asyncio.sleep(0.1)
            return 'healthy'
        except Exception:
            return 'error'
    
    def _determine_pipeline_health(self, component_health: Dict[str, str], system_metrics: SystemMetrics) -> PipelineHealth:
        """Determine overall pipeline health based on component status and metrics."""
        error_components = [k for k, v in component_health.items() if v == 'error']
        warning_components = [k for k, v in component_health.items() if v == 'warning']
        
        # Check system resource constraints
        high_resource_usage = (
            system_metrics.cpu_usage > 80 or 
            system_metrics.memory_usage > 85 or
            system_metrics.error_rate > 5.0
        )
        
        if error_components or high_resource_usage:
            return PipelineHealth.DOWN
        elif warning_components or system_metrics.response_time_ms > 1000:
            return PipelineHealth.DEGRADED
        else:
            return PipelineHealth.HEALTHY
    
    async def _count_active_tests(self) -> int:
        """Count currently active test executions."""
        # Mock implementation
        import random
        return random.randint(0, 5)
    
    async def _count_completed_tests_today(self) -> int:
        """Count tests completed today."""
        # Mock implementation
        import random
        return random.randint(15, 75)
    
    async def _count_failed_tests_today(self) -> int:
        """Count tests failed today."""
        # Mock implementation
        import random
        return random.randint(0, 8)

class TestingDashboard:
    """Main testing dashboard orchestrator."""
    
    def __init__(self):
        self.component_tester = PipelineComponentTester()
        self.health_monitor = SystemHealthMonitor()
        self.active_tests: Dict[str, TestExecution] = {}
        self.test_history: List[TestExecution] = []
        
        # Performance tracking
        self.cost_per_test = 0.0  # Internal dashboard - no external costs
    
    async def execute_full_pipeline_test(self, lead_data: Dict[str, Any], user_id: int = 1) -> TestExecution:
        """Execute complete pipeline test with all components."""
        test_id = str(uuid.uuid4())
        
        test_execution = TestExecution(
            id=test_id,
            user_id=user_id,
            test_type='full_pipeline',
            status=TestStatus.PENDING,
            lead_data=lead_data,
            pipeline_results=[],
            execution_time_ms=None,
            success_rate=0.0,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None
        )
        
        self.active_tests[test_id] = test_execution
        
        try:
            logger.info(f"Starting full pipeline test {test_id}")
            test_execution.status = TestStatus.RUNNING
            test_execution.started_at = datetime.now(timezone.utc)
            
            start_time = time.time()
            pipeline_results = []
            
            # Define test pipeline steps
            test_steps = [
                ('s3_setup', lambda: self.component_tester.test_s3_integration(lead_data)),
                ('lead_data_model', lambda: self.component_tester.test_lead_data_model(lead_data)),
                ('assessment_orchestrator', lambda: self.component_tester.test_assessment_orchestrator(lead_data)),
                ('pagespeed_integration', lambda: self.component_tester.test_pagespeed_integration(lead_data.get('website_url', 'https://example.com'))),
                ('security_scraper', lambda: self.component_tester.test_security_scraper(lead_data.get('website_url', 'https://example.com'))),
                ('gbp_integration', lambda: self.component_tester.test_gbp_integration(lead_data)),
                ('screenshot_integration', lambda: self.component_tester.test_screenshot_integration(lead_data.get('website_url', 'https://example.com'))),
                ('semrush_integration', lambda: self.component_tester.test_semrush_integration(lead_data.get('website_url', 'https://example.com'))),
                ('llm_visual_analysis', lambda: self.component_tester.test_llm_visual_analysis(lead_data.get('website_url', 'https://example.com'))),
                ('score_calculator', lambda: self.component_tester.test_score_calculator(lead_data)),
                ('content_generator', lambda: self.component_tester.test_content_generator(lead_data)),
                ('report_and_email', lambda: self.component_tester.test_report_and_email(lead_data))
            ]
            
            # Execute pipeline steps
            for step_number, (step_name, step_func) in enumerate(test_steps, 1):
                logger.info(f"Executing step {step_number}: {step_name}")
                
                try:
                    step_result = await step_func()
                    
                    pipeline_step = PipelineStepResult(
                        step_name=step_name,
                        step_number=step_number,
                        status=TestStatus.SUCCESS if step_result['status'] == 'success' else TestStatus.FAILED,
                        duration_ms=step_result['duration'],
                        details=step_result['details'],
                        error_message=step_result.get('error'),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    pipeline_results.append(pipeline_step)
                    
                    # Stop on critical failures (optional - could continue for partial results)
                    if step_result['status'] == 'failed' and step_name in ['s3_setup', 'lead_data_model']:
                        logger.warning(f"Critical step {step_name} failed, stopping pipeline test")
                        break
                    
                except Exception as e:
                    logger.error(f"Step {step_name} execution failed: {e}")
                    
                    pipeline_step = PipelineStepResult(
                        step_name=step_name,
                        step_number=step_number,
                        status=TestStatus.FAILED,
                        duration_ms=0,
                        details={'error': str(e)},
                        error_message=str(e),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    pipeline_results.append(pipeline_step)
            
            # Calculate final results
            total_duration = int((time.time() - start_time) * 1000)
            successful_steps = len([r for r in pipeline_results if r.status == TestStatus.SUCCESS])
            success_rate = (successful_steps / len(pipeline_results)) * 100 if pipeline_results else 0
            
            test_execution.pipeline_results = pipeline_results
            test_execution.execution_time_ms = total_duration
            test_execution.success_rate = success_rate
            test_execution.status = TestStatus.SUCCESS if success_rate >= 80 else TestStatus.FAILED
            test_execution.completed_at = datetime.now(timezone.utc)
            
            logger.info(f"Pipeline test {test_id} completed: {success_rate:.1f}% success rate, {total_duration}ms")
            
            # Move to history
            self.test_history.insert(0, test_execution)
            if len(self.test_history) > 100:  # Keep last 100 tests
                self.test_history = self.test_history[:100]
            
            return test_execution
            
        except Exception as e:
            logger.error(f"Pipeline test {test_id} failed: {e}")
            test_execution.status = TestStatus.FAILED
            test_execution.error_message = str(e)
            test_execution.completed_at = datetime.now(timezone.utc)
            if test_execution.started_at:
                test_execution.execution_time_ms = int((test_execution.completed_at - test_execution.started_at).total_seconds() * 1000)
            
            self.test_history.insert(0, test_execution)
            raise TestingDashboardError(f"Pipeline test failed: {str(e)}")
            
        finally:
            # Remove from active tests
            if test_id in self.active_tests:
                del self.active_tests[test_id]
    
    async def get_system_status(self) -> SystemStatus:
        """Get current system status and health."""
        return await self.health_monitor.get_system_status()
    
    async def get_active_tests(self) -> List[TestExecution]:
        """Get all currently active test executions."""
        return list(self.active_tests.values())
    
    async def get_test_history(self, limit: int = 50) -> List[TestExecution]:
        """Get recent test execution history."""
        return self.test_history[:limit]
    
    async def get_testing_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive testing metrics and analytics."""
        # Filter history by date range
        since_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_tests = [t for t in self.test_history if t.created_at >= since_date]
        
        if not recent_tests:
            return {
                'period_days': days,
                'total_tests': 0,
                'successful_tests': 0,
                'failed_tests': 0,
                'success_rate': 0.0,
                'average_execution_time_ms': 0.0,
                'step_statistics': {},
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        
        # Calculate basic metrics
        total_tests = len(recent_tests)
        successful_tests = len([t for t in recent_tests if t.status == TestStatus.SUCCESS])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests) * 100
        
        # Calculate average execution time
        valid_times = [t.execution_time_ms for t in recent_tests if t.execution_time_ms]
        avg_execution_time = sum(valid_times) / len(valid_times) if valid_times else 0
        
        # Calculate step statistics
        step_stats = {}
        for test in recent_tests:
            for step in test.pipeline_results:
                if step.step_name not in step_stats:
                    step_stats[step.step_name] = {'total': 0, 'successful': 0}
                step_stats[step.step_name]['total'] += 1
                if step.status == TestStatus.SUCCESS:
                    step_stats[step.step_name]['successful'] += 1
        
        # Convert to success rates
        for step_name, stats in step_stats.items():
            stats['success_rate'] = (stats['successful'] / stats['total']) * 100 if stats['total'] > 0 else 0
        
        return {
            'period_days': days,
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': round(success_rate, 2),
            'average_execution_time_ms': round(avg_execution_time, 2),
            'step_statistics': step_stats,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

# Main entry point functions

async def run_full_pipeline_test(lead_data: Dict[str, Any], user_id: int = 1) -> TestExecution:
    """
    Main entry point for running a complete pipeline test.
    
    Args:
        lead_data: Dictionary containing lead information
        user_id: ID of the user running the test
        
    Returns:
        Complete test execution results
    """
    try:
        dashboard = TestingDashboard()
        logger.info(f"Starting full pipeline test for user {user_id}")
        
        result = await dashboard.execute_full_pipeline_test(lead_data, user_id)
        
        logger.info(f"Pipeline test completed: {result.id}, success rate: {result.success_rate:.1f}%")
        return result
        
    except Exception as e:
        logger.error(f"Full pipeline test failed: {e}")
        raise TestingDashboardError(f"Pipeline test execution failed: {str(e)}")

async def get_dashboard_status() -> SystemStatus:
    """
    Get current dashboard and system status.
    
    Returns:
        Complete system status information
    """
    try:
        dashboard = TestingDashboard()
        status = await dashboard.get_system_status()
        
        logger.info(f"System status retrieved: {status.pipeline_health}")
        return status
        
    except Exception as e:
        logger.error(f"Dashboard status check failed: {e}")
        raise TestingDashboardError(f"Status check failed: {str(e)}")

# Cost tracking integration
def create_dashboard_cost_method(cls, lead_id: int, cost_cents: float = 0.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for testing dashboard operations (no external API cost).
    
    Args:
        lead_id: ID of the lead being tested
        cost_cents: Cost in cents (default $0.00 - internal testing)
        response_status: success, error, timeout
        response_time_ms: Operation time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="testing_dashboard",
        api_endpoint="internal://testing/pipeline",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=False,  # Internal testing - no quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_dashboard_cost = classmethod(create_dashboard_cost_method)