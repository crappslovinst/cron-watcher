"""Tests for cron_watcher.label and cron_watcher.label_integration."""
from __future__ import annotations

import pytest

from cron_watcher.log_parser import CronEvent
from cron_watcher.label import (
    LabelConfig,
    LabelRule,
    annotate_events,
    label_config_from_dict,
    resolve_tags,
)
from cron_watcher.label_integration import (
    get_label_config,
    reset_label_config,
    tagged_failures,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    reset_label_config()
    yield
    reset_label_config()


def _ev(job: str = "backup", exit_code: int = 1) -> CronEvent:
    return CronEvent(
        timestamp="2024-01-15T03:00:00",
        job=job,
        pid=42,
        exit_code=exit_code,
        is_failure=exit_code != 0,
        raw="raw line",
    )


# ---------------------------------------------------------------------------
# label_config_from_dict
# ---------------------------------------------------------------------------

def test_label_config_from_dict_empty():
    cfg = label_config_from_dict({})
    assert cfg.rules == []


def test_label_config_from_dict_parses_rules():
    raw = {"label_rules": [{"pattern": "backup", "tags": ["storage", "nightly"]}]}
    cfg = label_config_from_dict(raw)
    assert len(cfg.rules) == 1
    assert cfg.rules[0].tags == ["storage", "nightly"]


def test_label_config_skips_rule_without_pattern():
    raw = {"label_rules": [{"tags": ["orphan"]}]}
    cfg = label_config_from_dict(raw)
    assert cfg.rules == []


# ---------------------------------------------------------------------------
# resolve_tags
# ---------------------------------------------------------------------------

def test_resolve_tags_no_rules_returns_empty():
    cfg = LabelConfig()
    assert resolve_tags(_ev("backup"), cfg) == []


def test_resolve_tags_matching_rule():
    cfg = LabelConfig(rules=[LabelRule(pattern="backup", tags=["storage"])])
    assert resolve_tags(_ev("backup"), cfg) == ["storage"]


def test_resolve_tags_non_matching_rule():
    cfg = LabelConfig(rules=[LabelRule(pattern="sync", tags=["network"])])
    assert resolve_tags(_ev("backup"), cfg) == []


def test_resolve_tags_deduplicates():
    cfg = LabelConfig(rules=[
        LabelRule(pattern="backup", tags=["storage"]),
        LabelRule(pattern="back", tags=["storage", "nightly"]),
    ])
    tags = resolve_tags(_ev("backup"), cfg)
    assert tags.count("storage") == 1
    assert "nightly" in tags


# ---------------------------------------------------------------------------
# annotate_events
# ---------------------------------------------------------------------------

def test_annotate_events_adds_tags_key():
    cfg = LabelConfig(rules=[LabelRule(pattern="backup", tags=["storage"])])
    result = annotate_events([_ev("backup")], cfg)
    assert len(result) == 1
    assert result[0]["tags"] == ["storage"]


def test_annotate_events_empty_tags_for_no_match():
    cfg = LabelConfig()
    result = annotate_events([_ev("cleanup")], cfg)
    assert result[0]["tags"] == []


# ---------------------------------------------------------------------------
# label_integration
# ---------------------------------------------------------------------------

def test_get_label_config_returns_instance():
    cfg = get_label_config()
    assert isinstance(cfg, LabelConfig)


def test_get_label_config_is_cached():
    a = get_label_config()
    b = get_label_config()
    assert a is b


def test_reset_creates_new_instance():
    a = get_label_config()
    reset_label_config()
    b = get_label_config()
    assert a is not b


def test_tagged_failures_uses_shared_config():
    reset_label_config()
    get_label_config({"label_rules": [{"pattern": "backup", "tags": ["storage"]}]})
    result = tagged_failures([_ev("backup")])
    assert result[0]["tags"] == ["storage"]
