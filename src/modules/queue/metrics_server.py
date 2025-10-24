"""
Metrics server for Celery worker.

Runs a simple HTTP server in a background thread to expose Prometheus metrics
from the Celery worker process.
"""

import threading
from wsgiref.simple_server import make_server

from prometheus_client import REGISTRY, generate_latest

# Set to track if server is already started
_server_started = False
_server_lock = threading.Lock()


class MetricsServer:
    """Simple WSGI server for exposing Prometheus metrics from Celery."""

    def __init__(self, port: int = 9091):
        """
        Initialize metrics server.

        Args:
            port: Port to run the metrics server on
        """
        self.port = port
        self.server = None
        self.thread = None

    def metrics_app(self, environ, start_response):
        """WSGI application to serve Prometheus metrics."""
        if environ["PATH_INFO"] == "/metrics":
            output = generate_latest(REGISTRY)
            status = "200 OK"
            headers = [("Content-Type", "text/plain; charset=utf-8")]
            start_response(status, headers)
            return [output]
        else:
            status = "404 Not Found"
            headers = [("Content-Type", "text/plain")]
            start_response(status, headers)
            return [b"Not Found. Try /metrics"]

    def start(self):
        """Start the metrics server in a background thread."""
        global _server_started

        with _server_lock:
            if _server_started:
                print("⚠️  Metrics server already started")
                return

            try:
                # Create WSGI server
                self.server = make_server("0.0.0.0", self.port, self.metrics_app)

                # Make server non-blocking
                self.server.timeout = 0.5

                # Start server in daemon thread
                self.thread = threading.Thread(
                    target=self._run_server, daemon=True, name="MetricsServer"
                )
                self.thread.start()

                _server_started = True
                print(
                    f"✅ Celery metrics server started on http://0.0.0.0:{self.port}/metrics"
                )

            except OSError as e:
                if e.errno == 48:  # Address already in use
                    print(
                        f"⚠️  Port {self.port} already in use, metrics server not started"
                    )
                else:
                    print(f"❌ Failed to start metrics server: {e}")

    def _run_server(self):
        """Run the server loop."""
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"❌ Metrics server error: {e}")

    def stop(self):
        """Stop the metrics server."""
        if self.server:
            self.server.shutdown()
            print("🛑 Metrics server stopped")


# Global instance
_metrics_server = None


def start_metrics_server(port: int = 9091):
    """
    Start the Celery metrics server if not already running.

    Args:
        port: Port to run the metrics server on (default: 9091)
    """
    global _metrics_server

    if _metrics_server is None:
        _metrics_server = MetricsServer(port=port)
        _metrics_server.start()
    else:
        print("⚠️  Metrics server already initialized")


def stop_metrics_server():
    """Stop the Celery metrics server."""
    global _metrics_server

    if _metrics_server:
        _metrics_server.stop()
        _metrics_server = None
