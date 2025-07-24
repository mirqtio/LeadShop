"""
PRP-002: Celery Configuration for Assessment Orchestrator
Redis broker configuration with task routing and worker settings
"""

import os
from kombu import Queue
from celery import Celery

# Environment configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://leadfactory:pass@localhost:5432/leadfactory_dev')

# Broker settings
broker_url = REDIS_URL
result_backend = REDIS_URL

# Task serialization
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker settings for memory optimization
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 524288  # 512MB limit per PRP-002 requirements

# Task routing configuration
task_routes = {
    'src.assessment.orchestrator.coordinate_assessment': {'queue': 'high_priority'},
    'src.assessment.tasks.pagespeed_task': {'queue': 'assessment'},
    'src.assessment.tasks.security_task': {'queue': 'assessment'},
    'src.assessment.tasks.gbp_task': {'queue': 'assessment'},
    'src.assessment.tasks.semrush_task': {'queue': 'assessment'},
    'src.assessment.tasks.visual_task': {'queue': 'assessment'},
    'src.assessment.tasks.llm_analysis_task': {'queue': 'llm'},
    'src.assessment.tasks.aggregate_results': {'queue': 'high_priority'},
    'src.assessment.tasks.health_check': {'queue': 'high_priority'},
    'src.assessment.tasks.cleanup_expired_results': {'queue': 'default'},
    'src.assessment.tasks.monitor_assessment_queues': {'queue': 'high_priority'},
}

# Queue definitions
task_default_queue = 'default'
task_queues = (
    Queue('high_priority', routing_key='high_priority'),
    Queue('assessment', routing_key='assessment'),
    Queue('llm', routing_key='llm'),
    Queue('default', routing_key='default'),
)

# Retry settings (exponential backoff: 1s, 2s, 4s)
task_default_retry_delay = 60
task_max_retries = 3

# Result settings
result_expires = 3600  # 1 hour
result_persistent = True
result_compression = 'gzip'

# Monitoring settings for Celery Flower
worker_send_task_events = True
task_send_sent_event = True

# Security settings
task_always_eager = False  # Never execute tasks synchronously in production
task_eager_propagates = True
task_reject_on_worker_lost = True

# Logging
worker_log_color = True
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Performance settings
task_compression = 'gzip'
result_compression = 'gzip'
worker_disable_rate_limits = True

# Error handling
task_soft_time_limit = 300  # 5 minutes soft limit
task_time_limit = 600       # 10 minutes hard limit

# Health checks
worker_send_task_events = True
task_send_sent_event = True
worker_enable_remote_control = True