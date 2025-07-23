# PRP-002: Assessment Orchestrator

## Task ID: PRP-002

## Wave: Foundation Infrastructure

## Business Logic

The LeadFactory system requires an asynchronous task orchestrator to execute comprehensive technical assessments on business leads to generate $399 audit reports. This assessment orchestrator coordinates multiple parallel assessment services (PageSpeed Insights, security header analysis, Google Business Profile data, SEMrush SEO metrics, visual website analysis, and LLM-powered insights) with robust retry logic, real-time status tracking, and error aggregation. The orchestrator ensures reliable assessment completion with proper memory management and containerized deployment for scaling assessment throughput based on lead volume.

## Overview

Implement Celery-based distributed task orchestration system with Redis broker for:
- Parallel execution of 6 assessment types with dependency management
- Retry strategy with exponential backoff for transient failures (3 attempts maximum)
- Real-time status updates stored in PostgreSQL database
- Error aggregation and failure recovery for partial assessment completion
- Memory management and resource optimization for concurrent assessments
- Docker containerization with worker scaling based on assessment queue depth
- Integration with lead data model for storing assessment results

## Dependencies

- **External**: Redis server for message broker, Celery framework, Docker for containerization
- **Internal**: PRP-001 (Lead Data Model & API) for storing assessment results, PRP-000 (AWS S3 Bucket Setup) for screenshot and report storage
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Orchestrator Operational**: `celery -A assessment_orchestrator worker --loglevel=info` starts worker successfully and processes assessment tasks from Redis queue
2. **Parallel Assessment Execution**: Complete assessment pipeline processes all 6 assessment types (PageSpeed, security, GBP, SEMrush, visual, LLM) in parallel within 90 seconds for single lead
3. **Retry Strategy Effective**: Failed assessments automatically retry 3 times with exponential backoff (1s, 2s, 4s delays), transient network failures recover successfully
4. **Status Tracking Accuracy**: Assessment status updates stored in database in real-time, API endpoint returns current progress (pending/in_progress/completed/failed) with completion percentage
5. **Error Aggregation Complete**: Failed assessments store detailed error messages, partial completions save successful results, error dashboard shows failure patterns
6. **Memory Management Enforced**: Worker processes consume <512MB memory per assessment, memory cleanup after task completion prevents memory leaks
7. **Container Scaling Functional**: Docker Compose scales worker containers based on queue depth, `docker-compose up --scale worker=4` processes 4x assessment throughput
8. **Database Integration Working**: Assessment results automatically saved to PostgreSQL via SQLAlchemy models, foreign key relationships maintained with lead records
9. **Performance Monitoring Active**: Celery Flower dashboard accessible at localhost:5555, worker health metrics and task completion rates visible
10. **Production Deployment Ready**: Full assessment pipeline processes 100 leads/hour with <2% failure rate, all Docker containers restart automatically on failure

## Integration Points

### Assessment Orchestrator Core (Celery Tasks)
- **Location**: `src/assessment/orchestrator.py`, `src/assessment/tasks.py`
- **Dependencies**: Celery, Redis, SQLAlchemy, assessment service clients
- **Functions**: coordinate_assessment(), pagespeed_task(), security_task(), gbp_task(), semrush_task(), visual_task(), llm_analysis_task()

### Assessment Service Clients (External API Integration)
- **Location**: `src/assessment/services/pagespeed.py`, `src/assessment/services/security.py`, `src/assessment/services/gbp.py`, `src/assessment/services/semrush.py`, `src/assessment/services/visual.py`, `src/assessment/services/llm.py`
- **Dependencies**: requests, API keys, rate limiting, timeout handling
- **Functions**: Individual service clients with retry logic and response validation

### Redis Configuration (Message Broker)
- **Location**: `docker-compose.yml`, `src/core/celery_config.py`
- **Dependencies**: Redis server, Celery broker configuration
- **Resources**: Task queues, result backend, worker monitoring

### Database Integration (Assessment Results)
- **Location**: `src/models/assessment_models.py` (from PRP-001)
- **Dependencies**: SQLAlchemy, PostgreSQL, Alembic migrations
- **Integration**: Assessment results stored via ORM with proper error handling

## Implementation Requirements

### Celery Orchestrator Implementation

**Assessment Coordinator Task**:
```python
from celery import Celery, group, chord
from celery.exceptions import Retry
from typing import Dict, Any, Optional
import logging
from datetime import datetime

app = Celery('assessment_orchestrator')
app.config_from_object('src.core.celery_config')

@app.task(
    bind=True,
    autoretry_for=(requests.RequestException, requests.Timeout),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3}
)
def coordinate_assessment(self, lead_id: int) -> Dict[str, Any]:
    """
    Orchestrate complete assessment pipeline for a business lead.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing assessment results and metadata
    """
    try:
        # Update assessment status to in_progress
        assessment = get_or_create_assessment(lead_id)
        assessment.status = "in_progress"
        assessment.started_at = datetime.utcnow()
        db.session.commit()
        
        # Create parallel task group
        assessment_tasks = group([
            pagespeed_task.s(lead_id),
            security_task.s(lead_id),
            gbp_task.s(lead_id),
            semrush_task.s(lead_id),
            visual_task.s(lead_id),
        ])
        
        # Execute parallel assessments with callback
        chord_result = chord(assessment_tasks)(
            aggregate_results.s(lead_id)
        )
        
        return {
            "lead_id": lead_id,
            "task_id": chord_result.id,
            "status": "processing",
            "started_at": assessment.started_at.isoformat()
        }
        
    except Exception as exc:
        # Log error and update database
        logger.error(f"Assessment coordination failed for lead {lead_id}: {exc}")
        update_assessment_error(lead_id, str(exc))
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            raise self.retry(countdown=2**self.request.retries)
        else:
            update_assessment_status(lead_id, "failed")
            raise

@app.task(
    bind=True,
    autoretry_for=(requests.RequestException, requests.Timeout, APIRateLimitError),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def pagespeed_task(self, lead_id: int) -> Dict[str, Any]:
    """Execute PageSpeed Insights assessment with retry logic."""
    try:
        lead = get_lead_by_id(lead_id)
        if not lead or not lead.url:
            raise ValueError(f"Invalid lead or missing URL for lead {lead_id}")
        
        # Execute PageSpeed assessment
        pagespeed_client = PageSpeedClient()
        results = pagespeed_client.analyze_url(
            url=lead.url,
            strategy='mobile',  # Also analyze desktop
            categories=['performance', 'accessibility', 'best-practices', 'seo']
        )
        
        # Store results in database
        update_assessment_field(
            lead_id, 
            'pagespeed_data', 
            results,
            'pagespeed_score',
            results.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0) * 100
        )
        
        return {
            "lead_id": lead_id,
            "task": "pagespeed",
            "status": "completed",
            "score": results.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0) * 100,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"PageSpeed assessment failed for lead {lead_id}: {exc}")
        if self.request.retries < 3:
            raise self.retry(countdown=2**self.request.retries)
        else:
            update_assessment_error(lead_id, f"PageSpeed: {str(exc)}")
            raise
```

### Celery Configuration

**Redis Broker Configuration**:
```python
# src/core/celery_config.py
from kombu import Queue
import os

# Broker settings
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 524288  # 512MB

# Queue configuration
task_routes = {
    'assessment_orchestrator.coordinate_assessment': {'queue': 'high_priority'},
    'assessment_orchestrator.pagespeed_task': {'queue': 'assessment'},
    'assessment_orchestrator.security_task': {'queue': 'assessment'},
    'assessment_orchestrator.gbp_task': {'queue': 'assessment'},
    'assessment_orchestrator.semrush_task': {'queue': 'assessment'},
    'assessment_orchestrator.visual_task': {'queue': 'assessment'},
    'assessment_orchestrator.llm_analysis_task': {'queue': 'llm'},
}

task_default_queue = 'default'
task_queues = (
    Queue('high_priority', routing_key='high_priority'),
    Queue('assessment', routing_key='assessment'),
    Queue('llm', routing_key='llm'),
    Queue('default', routing_key='default'),
)

# Retry settings
task_default_retry_delay = 60
task_max_retries = 3

# Result settings
result_expires = 3600  # 1 hour
result_persistent = True

# Monitoring
worker_send_task_events = True
task_send_sent_event = True
```

### Docker Containerization

**Docker Compose Configuration**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: leadfactory
      POSTGRES_USER: leadfactory
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U leadfactory"]
      interval: 30s
      timeout: 10s
      retries: 3

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://leadfactory:${POSTGRES_PASSWORD}@postgres:5432/leadfactory
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: .
    environment:
      - DATABASE_URL=postgresql://leadfactory:${POSTGRES_PASSWORD}@postgres:5432/leadfactory
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app
    command: celery -A assessment_orchestrator worker --loglevel=info --concurrency=4
    deploy:
      replicas: 2
    restart: unless-stopped

  flower:
    build: .
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    command: celery -A assessment_orchestrator flower --port=5555
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

## Tests to Pass

1. **Orchestrator Tests**: `pytest tests/test_assessment_orchestrator.py -v` passes with ≥90% coverage for coordinate_assessment(), retry logic, and task coordination
2. **Individual Task Tests**: `pytest tests/test_assessment_tasks.py -v` validates pagespeed_task(), security_task(), gbp_task(), semrush_task(), visual_task(), llm_analysis_task() with proper error handling
3. **Integration Tests**: `pytest tests/integration/test_assessment_pipeline.py -v` validates complete assessment pipeline from lead input to result storage
4. **Performance Tests**: Assessment pipeline processes single lead within 90 seconds, parallel processing handles 100+ leads/hour with 3 workers
5. **Memory Tests**: Worker processes maintain <512MB memory usage during assessment execution, proper cleanup after task completion
6. **Redis Tests**: Task queuing, status tracking, and result storage function correctly with Redis message broker
7. **Docker Tests**: `docker-compose up --scale worker=4` successfully scales workers, containers restart automatically on failure
8. **Database Tests**: Assessment results properly stored in PostgreSQL via SQLAlchemy models, foreign key relationships maintained
9. **Retry Tests**: Failed tasks retry 3 times with exponential backoff (1s, 2s, 4s delays), permanent failures marked correctly
10. **Monitoring Tests**: Celery Flower dashboard accessible at localhost:5555, displays accurate worker health and task metrics

## Implementation Guide

### Phase 1: Core Infrastructure Setup (Days 1-3)
1. **Redis Configuration**: Set up Redis server with proper persistence and queue configuration
2. **Celery Setup**: Install and configure Celery with Redis broker and result backend
3. **Docker Environment**: Create Docker Compose configuration for multi-container deployment
4. **Basic Orchestrator**: Implement coordinate_assessment() task with basic parallel execution
5. **Task Queue Setup**: Configure task routing and queue priorities for different assessment types

### Phase 2: Assessment Tasks Implementation (Days 4-6)
1. **PageSpeed Task**: Implement pagespeed_task() with Google PageSpeed Insights API integration
2. **Security Task**: Implement security_task() with security header analysis client
3. **GBP Task**: Implement gbp_task() with Google Business Profile data collection
4. **SEMrush Task**: Implement semrush_task() with SEO metrics and keyword analysis
5. **Visual Task**: Implement visual_task() with website screenshot and visual analysis
6. **LLM Task**: Implement llm_analysis_task() with AI-powered insights generation

### Phase 3: Error Handling & Monitoring (Days 7-9)
1. **Retry Logic**: Implement exponential backoff retry strategy with proper exception handling
2. **Error Aggregation**: Create error tracking and aggregation system for failed assessments
3. **Status Tracking**: Implement real-time status updates with Redis caching and database persistence
4. **Memory Management**: Add memory monitoring and cleanup mechanisms for worker processes
5. **Flower Dashboard**: Set up Celery Flower for worker monitoring and task visualization

### Phase 4: Integration & Testing (Days 10-12)
1. **Database Integration**: Connect assessment results to PostgreSQL via SQLAlchemy models from PRP-001
2. **API Integration**: Create FastAPI endpoints for task submission and status monitoring
3. **Unit Testing**: Write comprehensive unit tests for all orchestrator and task functions
4. **Integration Testing**: Test complete assessment pipeline with real external services
5. **Performance Testing**: Validate throughput, latency, and memory usage requirements

## Validation Commands

```bash
# Infrastructure validation
docker-compose up -d redis postgres
redis-cli ping
psql -h localhost -U leadfactory -d leadfactory -c "SELECT 1;"

# Celery worker validation
celery -A assessment_orchestrator worker --loglevel=info --dry-run
celery -A assessment_orchestrator inspect active

# Assessment pipeline validation
python -c "from src.assessment.orchestrator import coordinate_assessment; print(coordinate_assessment.delay(1).get())"

# Performance validation
python scripts/assessment_load_test.py --leads=100 --workers=3 --duration=300

# Memory validation
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep worker

# Monitoring validation
curl http://localhost:5555/api/workers
curl http://localhost:8000/api/v1/assessments/1/status

# Database validation
psql -h localhost -U leadfactory -d leadfactory -c "SELECT COUNT(*) FROM assessments WHERE status='completed';"
```

## Rollback Strategy

### Emergency Procedures
1. **Service Degradation**: Route assessment requests to synchronous fallback processing system
2. **Worker Failure**: Scale down failed workers and redistribute tasks to healthy instances
3. **Redis Failure**: Switch to database-backed task queue with reduced performance
4. **Database Issues**: Cache assessment results in Redis until database connectivity restored

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show task failure rate >5% or system unavailability
2. **Immediate Response**: Stop new task submissions and allow existing tasks to complete or timeout
3. **Service Fallback**: Activate synchronous assessment processing for new requests
4. **Data Preservation**: Ensure all completed assessment results are committed to database
5. **System Analysis**: Analyze logs, metrics, and error patterns to identify root cause
6. **Gradual Recovery**: Test fixes in staging environment before re-enabling async processing

## Success Criteria

1. **Infrastructure Complete**: Docker Compose deployment with Redis, PostgreSQL, Celery workers, and Flower monitoring
2. **Integration Working**: Assessment orchestrator successfully coordinates all 6 assessment types with database storage
3. **Performance Met**: 100+ leads/hour processing rate with <2% failure rate and 90-second completion time
4. **Memory Optimized**: Worker processes maintain <512MB memory usage with automatic cleanup
5. **Monitoring Active**: Celery Flower dashboard operational with real-time worker health and task metrics
6. **Error Handling**: Retry logic with exponential backoff handles transient failures, permanent failures properly escalated
7. **Testing Complete**: Unit tests ≥90% coverage, integration tests validate complete pipeline functionality
8. **Production Ready**: Docker container scaling, auto-restart, and production deployment configuration validated

## Critical Context

### Assessment Pipeline Components
- **PageSpeed Insights**: Google PageSpeed API for performance metrics and Core Web Vitals
- **Security Headers**: HTTP security header analysis and vulnerability assessment
- **Google Business Profile**: Business listing data and review analysis
- **SEMrush Integration**: SEO metrics, keyword analysis, and competitive intelligence
- **Visual Analysis**: Website screenshot capture and visual quality assessment
- **LLM Insights**: AI-powered analysis generating actionable recommendations

### Performance Requirements
- **Throughput**: 100+ leads/hour processing capacity with 3 worker instances
- **Latency**: 90-second maximum completion time for single lead assessment
- **Memory**: <512MB per worker process with automatic cleanup and restart
- **Reliability**: <2% failure rate for production assessment pipeline
- **Scaling**: Linear performance scaling with additional worker containers

### Integration Dependencies
- **Database Schema**: Assessment results stored in PostgreSQL via PRP-001 lead data model
- **File Storage**: Screenshots and reports stored in AWS S3 via PRP-000 bucket setup
- **API Endpoints**: FastAPI integration for task submission and real-time status monitoring
- **External Services**: PageSpeed API, security scanning services, SEMrush API, OpenAI API
- **Monitoring Stack**: Celery Flower dashboard, Redis monitoring, Docker container health checks

### Business Impact Metrics
- **Revenue Attribution**: Assessment results enable $399 audit report generation and sales
- **Lead Processing**: Transforms raw business leads into comprehensive technical assessments
- **Operational Efficiency**: Reduces manual assessment time from hours to minutes
- **Scalability**: Supports platform growth to 10x current lead volume capacity
- **Quality Assurance**: Consistent assessment standards across all business evaluations

## Definition of Done

- [ ] Celery orchestrator implemented with Redis broker and task queue configuration
- [ ] All 6 assessment service clients implemented with retry logic and error handling
- [ ] Docker Compose configuration supports multi-container deployment with scaling
- [ ] Database integration stores assessment results via SQLAlchemy models
- [ ] Unit tests written for all orchestrator tasks with ≥90% coverage
- [ ] Integration tests validate complete assessment pipeline with ≥80% coverage  
- [ ] Performance testing confirms memory limits and throughput requirements
- [ ] Celery Flower monitoring dashboard accessible and functional
- [ ] Error aggregation and logging provide detailed failure analysis
- [ ] Production deployment tested with Docker container scaling and auto-restart
- [ ] Code review completed with architecture and security validation
- [ ] Documentation updated with deployment instructions and monitoring procedures