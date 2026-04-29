"""Simple HTTP healthcheck server for cron-watcher daemon status."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from cron_watcher.daemon import CronWatcherDaemon


def _make_handler(get_status: Callable[[], dict]) -> type:
    """Return a request handler class closed over get_status."""

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                payload = get_status()
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt: str, *args) -> None:  # pragma: no cover
            pass  # suppress default stderr logging

    return _Handler


class HealthCheckServer:
    """Tiny HTTP server that exposes a /health endpoint."""

    def __init__(self, host: str, port: int, get_status: Callable[[], dict]) -> None:
        self._host = host
        self._port = port
        self._get_status = get_status
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        handler_cls = _make_handler(self._get_status)
        self._server = HTTPServer((self._host, self._port), handler_cls)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True, name="healthcheck"
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None


def build_status(daemon: "CronWatcherDaemon") -> dict:
    """Collect status information from a running daemon instance."""
    scheduler = daemon.scheduler
    return {
        "status": "ok",
        "pending_failures": len(daemon.pending_events),
        "scheduler": {
            "running": scheduler.running if scheduler else False,
            "run_count": scheduler.run_count if scheduler else 0,
            "last_run": scheduler.last_run.isoformat() if (scheduler and scheduler.last_run) else None,
        },
    }
