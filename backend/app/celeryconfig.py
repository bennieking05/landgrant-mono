"""Celery Beat scheduler configuration for LandRight.

This module defines the periodic task schedule for:
- Deadline monitoring (hourly)
- Daily digest notifications (8 AM)
- Law change monitoring (weekly)
- Compliance checks (daily)
- Cache cleanup (daily)

Usage:
    celery -A app.worker beat -l info
"""

from celery.schedules import crontab

# Beat scheduler configuration
beat_schedule = {
    # Deadline Monitoring - Check upcoming deadlines every hour
    "check-deadlines-hourly": {
        "task": "app.tasks.filing.check_all_deadlines",
        "schedule": crontab(minute=0),  # Every hour at :00
        "options": {"queue": "filing"},
    },
    
    # Daily Deadline Digest - Send summary at 8 AM local time
    "send-deadline-digest-daily": {
        "task": "app.tasks.notifications.send_deadline_digest",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
        "options": {"queue": "notifications"},
    },
    
    # Weekly Law Change Monitor - Check for legal updates Monday 6 AM
    "monitor-law-changes-weekly": {
        "task": "app.tasks.compliance.check_law_updates",
        "schedule": crontab(day_of_week=1, hour=6, minute=0),  # Monday 6 AM
        "options": {"queue": "compliance"},
    },
    
    # Daily Compliance Check - Verify all active cases at 2 AM
    "daily-compliance-audit": {
        "task": "app.tasks.compliance.audit_active_cases",
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM daily
        "options": {"queue": "compliance"},
    },
    
    # Escalation Review - Check pending escalations every 4 hours
    "check-pending-escalations": {
        "task": "app.tasks.compliance.check_pending_escalations",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
        "options": {"queue": "compliance"},
    },
    
    # Cache Cleanup - Remove stale external data cache daily
    "cleanup-external-cache": {
        "task": "app.tasks.intake.cleanup_stale_cache",
        "schedule": crontab(hour=3, minute=30),  # 3:30 AM daily
        "options": {"queue": "default"},
    },
    
    # AVM Data Refresh - Update property valuations weekly
    "refresh-avm-data-weekly": {
        "task": "app.tasks.valuation.refresh_avm_cache",
        "schedule": crontab(day_of_week=0, hour=1, minute=0),  # Sunday 1 AM
        "options": {"queue": "default"},
    },
    
    # RAG Knowledge Base Refresh - Re-ingest rule packs weekly
    "refresh-knowledge-base-weekly": {
        "task": "app.tasks.ingest.refresh_knowledge_base",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),  # Sunday 2 AM
        "options": {"queue": "default"},
    },
    
    # Workflow Stage Progression - Check every 15 minutes
    "check-stage-transitions": {
        "task": "app.tasks.workflow.check_stage_transitions",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "options": {"queue": "default"},
    },
    
    # Deadline Expiration Check - Check every hour
    "check-deadline-expirations": {
        "task": "app.tasks.workflow.check_deadline_expirations",
        "schedule": crontab(minute=30),  # Every hour at :30
        "options": {"queue": "default"},
    },
    
    # Pending Progressions Notification - Daily at 9 AM
    "notify-pending-progressions": {
        "task": "app.tasks.workflow.notify_pending_progressions",
        "schedule": crontab(hour=9, minute=0),  # 9:00 AM daily
        "options": {"queue": "notifications"},
    },
}

# Timezone for beat scheduler
timezone = "America/Chicago"

# Enable UTC for internal scheduling
enable_utc = True

# Beat scheduler persistence (use database in production)
beat_scheduler = "celery.beat:PersistentScheduler"
beat_schedule_filename = "/tmp/celerybeat-schedule"
