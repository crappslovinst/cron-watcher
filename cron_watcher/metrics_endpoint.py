"""Expose runtime metrics via a simple HTTP endpoint.

Mounts a /metrics path on the existing HealthCheckServer port if enabled,
or can be used standalone for testing.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from typing import Callable, Dict


class _MetricsHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves JSON metrics on GET /metrics."""

    _snapshot_fn: Callable[[], Dict]

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/metrics":
            payload = json.dumps(self._snapshot_fn(), indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args) -> None:  # noqa: D102
        pass  # suppress default stderr logging


class MetricsServer:
    """Lightweight HTTP server that exposes a /metrics JSON endpoint."""

    def __init__(self, host: str, port: int, snapshot_fn: Callable[[], Dict]) -> None:
        self._host = host
        self._port = port
        self._snapshot_fn = snapshot_fn
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        handler = type(
            "_BoundHandler",
            (_MetricsHandler,),
            {"_snapshot_fn": staticmethod(self._snapshot_fn)},
        )
        self._server = HTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
