"""Celery tasks package for LandRight AI agents.

This package contains background tasks organized by agent/feature:

- intake: Case intake and property data fetching
- compliance: State-specific compliance checking and law monitoring
- valuation: AVM integration and compensation calculations
- docgen: Document generation and template processing
- filing: Deadline monitoring and e-filing
- title: Title search and OCR processing
- edge_cases: Special scenario handling
- notifications: Email/SMS notifications

Each module contains Celery tasks that wrap the corresponding agent
logic for async execution.
"""

from app.worker import app as celery_app

__all__ = ["celery_app"]
