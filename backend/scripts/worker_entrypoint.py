#!/usr/bin/env python3
"""
Worker entrypoint that runs Celery worker with a health check HTTP server.
Required for Cloud Run which expects containers to listen on a port.
"""

import os
import signal
import subprocess
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", "8080"))
celery_process = None


class HealthHandler(BaseHTTPRequestHandler):
    """Simple health check handler."""

    def log_message(self, format, *args):
        """Suppress logging for health checks."""
        pass

    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            # Check if Celery process is still running
            if celery_process and celery_process.poll() is None:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"healthy","service":"worker"}')
            else:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"unhealthy","service":"worker"}')
        else:
            self.send_response(404)
            self.end_headers()


def run_health_server():
    """Run the health check HTTP server."""
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"Health check server running on port {PORT}")
    server.serve_forever()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"Received signal {signum}, shutting down...")
    if celery_process:
        celery_process.terminate()
        celery_process.wait(timeout=30)
    sys.exit(0)


def main():
    global celery_process

    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start health check server in background
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Start Celery worker
    celery_cmd = [
        "celery",
        "-A", "app.worker",
        "worker",
        "--loglevel=info",
        "--concurrency=2",
        "--max-tasks-per-child=100",
    ]

    print(f"Starting Celery worker: {' '.join(celery_cmd)}")
    celery_process = subprocess.Popen(celery_cmd)

    # Wait for Celery to exit
    exit_code = celery_process.wait()
    print(f"Celery worker exited with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
