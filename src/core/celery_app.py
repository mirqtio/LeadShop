"""
PRP-002: Celery Application Instance
Main Celery application for assessment orchestrator
"""

from celery import Celery
from src.core.celery_config import *

# Create Celery application instance
celery_app = Celery('assessment_orchestrator')

# Load configuration from celery_config module
celery_app.config_from_object('src.core.celery_config')

# Manually include tasks to avoid circular imports
# Note: We cannot use autodiscover_tasks here due to circular import issues

# Add periodic tasks for health monitoring
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # Health check every 5 minutes
    'health-check': {
        'task': 'src.assessment.tasks.health_check',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'high_priority'}
    },
    # Clean up expired results every hour
    'cleanup-results': {
        'task': 'src.assessment.tasks.cleanup_expired_results',
        'schedule': crontab(minute=0),  # Every hour
        'options': {'queue': 'default'}
    },
    # Assessment queue monitoring every minute
    'monitor-queues': {
        'task': 'src.assessment.tasks.monitor_assessment_queues',
        'schedule': crontab(minute='*'),  # Every minute
        'options': {'queue': 'high_priority'}
    },
}

# Configure task execution options
celery_app.conf.update(
    task_default_retry_delay=60,
    task_max_retries=3,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes hard limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=524288,  # 512MB
)

if __name__ == '__main__':
    celery_app.start()