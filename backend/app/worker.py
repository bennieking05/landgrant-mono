"""Celery worker initialization for LandRight background tasks.

This module initializes the Celery application and discovers tasks from
the tasks package. It supports both Redis broker and Cloud Pub/Sub (planned).

Usage:
    # Start worker
    celery -A app.worker worker -l info
    
    # Start beat scheduler (deadline monitoring)
    celery -A app.worker beat -l info
    
    # Start both (development)
    celery -A app.worker worker -B -l info
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Initialize Celery app
app = Celery(
    "landright",
    broker=settings.effective_redis_url,
    backend=settings.effective_redis_url,
    include=[
        "app.tasks.intake",
        "app.tasks.compliance",
        "app.tasks.valuation",
        "app.tasks.docgen",
        "app.tasks.filing",
        "app.tasks.title",
        "app.tasks.edge_cases",
        "app.tasks.notifications",
        "app.tasks.workflow",
        "app.tasks.ingest",
    ],
)

# Load configuration
app.config_from_object("app.celeryconfig")

# Optional: Configure for Cloud Tasks/Pub/Sub in production
if settings.environment == "production":
    # Future: Configure Cloud Tasks integration
    pass


# Task routing - allows directing tasks to specific queues
app.conf.task_routes = {
    "app.tasks.filing.*": {"queue": "filing"},
    "app.tasks.compliance.*": {"queue": "compliance"},
    "app.tasks.title.*": {"queue": "title"},
    "app.tasks.notifications.*": {"queue": "notifications"},
    # Default queue for others
    "app.tasks.*": {"queue": "default"},
}

# Retry configuration
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True

# Serialization
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]

# Time limits (in seconds)
app.conf.task_soft_time_limit = 300  # 5 minutes soft limit
app.conf.task_time_limit = 600  # 10 minutes hard limit

# Result expiration
app.conf.result_expires = 86400  # 24 hours


if __name__ == "__main__":
    app.start()
