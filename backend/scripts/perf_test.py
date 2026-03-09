"""
Performance Testing Script using Locust

This script provides load testing for the LandRight API endpoints.
Run with: locust -f scripts/perf_test.py --headless -u 50 -r 10 --run-time 2m

Alternatively, run with UI:
    locust -f scripts/perf_test.py
    Then open http://localhost:8089
"""

from locust import HttpUser, task, between, events
import json
import random
import time
from datetime import datetime, timedelta
from uuid import uuid4


class APIUser(HttpUser):
    """Base user with common authentication and setup."""
    
    wait_time = between(0.5, 2)  # Wait between requests
    host = "http://localhost:8050"
    
    def on_start(self):
        """Set up user session."""
        self.project_id = "PRJ-001"
        self.parcel_id = f"PARCEL-PERF-{random.randint(1, 1000)}"
        self.persona = random.choice(["land_agent", "in_house_counsel"])
        self.headers = {
            "X-Persona": self.persona,
            "Content-Type": "application/json",
        }


class LandAgentUser(APIUser):
    """Simulates land agent workflows."""
    
    weight = 3  # 3x more likely to be spawned
    
    def on_start(self):
        super().on_start()
        self.persona = "land_agent"
        self.headers["X-Persona"] = self.persona

    @task(10)
    def list_parcels(self):
        """List parcels for a project."""
        self.client.get(
            f"/parcels?project_id={self.project_id}",
            headers=self.headers,
            name="/parcels"
        )

    @task(5)
    def get_communications(self):
        """Get communications for a parcel."""
        self.client.get(
            f"/communications?parcel_id={self.parcel_id}",
            headers=self.headers,
            name="/communications"
        )

    @task(3)
    def list_roes(self):
        """List ROE agreements."""
        self.client.get(
            f"/roe?parcel_id={self.parcel_id}",
            headers=self.headers,
            name="/roe"
        )

    @task(3)
    def list_offers(self):
        """List offers for a parcel."""
        self.client.get(
            f"/offers?parcel_id={self.parcel_id}",
            headers=self.headers,
            name="/offers"
        )

    @task(2)
    def create_roe(self):
        """Create an ROE agreement."""
        self.client.post(
            "/roe",
            headers=self.headers,
            json={
                "parcel_id": self.parcel_id,
                "project_id": self.project_id,
                "effective_date": datetime.utcnow().isoformat(),
                "expiry_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                "conditions": "Performance test ROE",
            },
            name="/roe [POST]"
        )

    @task(2)
    def create_offer(self):
        """Create an offer."""
        self.client.post(
            "/offers",
            headers=self.headers,
            json={
                "parcel_id": self.parcel_id,
                "project_id": self.project_id,
                "offer_type": "initial",
                "amount": random.randint(50000, 500000),
            },
            name="/offers [POST]"
        )

    @task(1)
    def get_title_instruments(self):
        """Get title instruments for a parcel."""
        self.client.get(
            f"/title?parcel_id={self.parcel_id}",
            headers=self.headers,
            name="/title"
        )


class CounselUser(APIUser):
    """Simulates counsel workflows."""
    
    weight = 2
    
    def on_start(self):
        super().on_start()
        self.persona = "in_house_counsel"
        self.headers["X-Persona"] = self.persona

    @task(5)
    def list_litigation(self):
        """List litigation cases."""
        self.client.get(
            f"/litigation?project_id={self.project_id}",
            headers=self.headers,
            name="/litigation"
        )

    @task(3)
    def get_litigation_analytics(self):
        """Get litigation analytics."""
        self.client.get(
            f"/litigation/analytics/summary?project_id={self.project_id}",
            headers=self.headers,
            name="/litigation/analytics"
        )

    @task(2)
    def create_litigation_case(self):
        """Create a litigation case."""
        self.client.post(
            "/litigation",
            headers=self.headers,
            json={
                "parcel_id": f"PARCEL-LIT-{uuid4().hex[:8]}",
                "project_id": self.project_id,
                "court": "District Court",
                "court_county": "Travis",
                "is_quick_take": random.choice([True, False]),
            },
            name="/litigation [POST]"
        )

    @task(3)
    def list_deadlines(self):
        """List deadlines."""
        self.client.get(
            f"/deadlines?project_id={self.project_id}",
            headers=self.headers,
            name="/deadlines"
        )

    @task(2)
    def list_esign_envelopes(self):
        """List e-sign envelopes."""
        self.client.get(
            f"/esign/list?project_id={self.project_id}",
            headers=self.headers,
            name="/esign/list"
        )


class PortalUser(APIUser):
    """Simulates landowner portal access."""
    
    weight = 2
    
    def on_start(self):
        super().on_start()
        self.persona = "landowner"
        self.headers["X-Persona"] = self.persona

    @task(5)
    def get_decision_options(self):
        """Get decision options."""
        self.client.get(
            "/portal/decision/options",
            headers=self.headers,
            name="/portal/decision/options"
        )

    @task(3)
    def list_uploads(self):
        """List portal uploads."""
        self.client.get(
            f"/portal/uploads?parcel_id={self.parcel_id}",
            headers=self.headers,
            name="/portal/uploads"
        )

    @task(2)
    def create_invite(self):
        """Create portal invite."""
        self.headers["X-Persona"] = "land_agent"  # Temporarily switch
        self.client.post(
            "/portal/invites",
            headers=self.headers,
            json={
                "email": f"perf-test-{uuid4().hex[:8]}@example.com",
                "parcel_id": self.parcel_id,
                "project_id": self.project_id,
            },
            name="/portal/invites [POST]"
        )
        self.headers["X-Persona"] = self.persona  # Switch back


class HealthCheckUser(HttpUser):
    """Lightweight user for health checks."""
    
    wait_time = between(1, 3)
    weight = 1
    host = "http://localhost:8050"

    @task
    def health_live(self):
        """Check liveness."""
        self.client.get("/health/live", name="/health/live")

    @task
    def health_invite(self):
        """Check invite flow health."""
        self.client.get("/health/invite", name="/health/invite")


# Event hooks for custom metrics

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests for analysis."""
    if response_time > 1000:  # More than 1 second
        print(f"SLOW REQUEST: {request_type} {name} took {response_time}ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics."""
    stats = environment.stats
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99)}ms")
    print(f"Requests/s: {stats.total.total_rps:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    import os
    print("Performance test script loaded.")
    print("Run with: locust -f scripts/perf_test.py")
    print("Or headless: locust -f scripts/perf_test.py --headless -u 50 -r 10 --run-time 2m")
