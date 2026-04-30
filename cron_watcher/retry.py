"""Retry logic for alert dispatching with exponential backoff."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 30.0


@dataclass
class RetryResult:
    success: bool
    attempts: int
    last_exception: Exception | None = None
    value: Any = None


def _compute_delay(attempt: int, cfg: RetryConfig) -> float:
    """Return sleep duration for the given attempt number (0-indexed)."""
    delay = cfg.base_delay * (cfg.backoff_factor ** attempt)
    return min(delay, cfg.max_delay)


def with_retry(
    fn: Callable[[], Any],
    cfg: RetryConfig | None = None,
    *,
    label: str = "operation",
) -> RetryResult:
    """Call *fn* up to cfg.max_attempts times, backing off between failures.

    Returns a RetryResult describing the outcome.
    """
    if cfg is None:
        cfg = RetryConfig()

    last_exc: Exception | None = None
    for attempt in range(cfg.max_attempts):
        try:
            value = fn()
            logger.debug("%s succeeded on attempt %d", label, attempt + 1)
            return RetryResult(success=True, attempts=attempt + 1, value=value)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < cfg.max_attempts - 1:
                delay = _compute_delay(attempt, cfg)
                logger.warning(
                    "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                    label,
                    attempt + 1,
                    cfg.max_attempts,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "%s failed after %d attempts: %s",
                    label,
                    cfg.max_attempts,
                    exc,
                )

    return RetryResult(
        success=False,
        attempts=cfg.max_attempts,
        last_exception=last_exc,
    )


def retry_config_from_dict(data: dict) -> RetryConfig:
    """Build a RetryConfig from a plain dict (e.g. parsed from TOML/YAML)."""
    return RetryConfig(
        max_attempts=int(data.get("max_attempts", 3)),
        base_delay=float(data.get("base_delay", 1.0)),
        backoff_factor=float(data.get("backoff_factor", 2.0)),
        max_delay=float(data.get("max_delay", 30.0)),
    )
