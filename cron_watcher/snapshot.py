"""Periodic snapshot writer — dumps current metrics + state to a JSON file."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class SnapshotConfig:
    enabled: bool = False
    path: str = "/var/lib/cron-watcher/snapshot.json"
    pretty: bool = False


def snapshot_config_from_dict(d: dict) -> SnapshotConfig:
    return SnapshotConfig(
        enabled=bool(d.get("enabled", False)),
        path=str(d.get("path", "/var/lib/cron-watcher/snapshot.json")),
        pretty=bool(d.get("pretty", False)),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_snapshot(
    cfg: SnapshotConfig,
    metrics_fn: Callable[[], dict],
    state_fn: Callable[[], dict],
    extra: Optional[dict] = None,
) -> bool:
    """Atomically write a snapshot JSON file.  Returns True on success."""
    if not cfg.enabled:
        return False

    payload: dict = {
        "timestamp": _now_iso(),
        "metrics": metrics_fn(),
        "state": state_fn(),
    }
    if extra:
        payload["extra"] = extra

    indent = 2 if cfg.pretty else None
    dest = Path(cfg.path)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dest.parent, prefix=".snap_")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(payload, fh, indent=indent, default=str)
        except Exception:
            os.unlink(tmp_path)
            raise
        os.replace(tmp_path, dest)
        log.debug("snapshot written to %s", dest)
        return True
    except OSError as exc:
        log.error("failed to write snapshot to %s: %s", dest, exc)
        return False
