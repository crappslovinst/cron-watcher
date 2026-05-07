"""Tests for cron_watcher.redact."""

import pytest
from cron_watcher.redact import (
    RedactConfig,
    redact,
    redact_config_from_dict,
    redact_event_command,
)

_REPLACEMENT = "[REDACTED]"


def test_redact_disabled_returns_original():
    cfg = RedactConfig(enabled=False)
    text = "backup --password supersecret"
    assert redact(text, cfg) == text


def test_redact_password_flag():
    text = "pg_dump --password mysecretpass --host localhost"
    result = redact(text)
    assert "mysecretpass" not in result
    assert _REPLACEMENT in result


def test_redact_env_style_assignment():
    text = "TOKEN=abc123xyz /usr/bin/deploy.sh"
    result = redact(text)
    assert "abc123xyz" not in result


def test_redact_api_key_variant():
    text = "curl -H 'api_key: deadbeefdeadbeef'"
    result = redact(text)
    assert "deadbeef" not in result


def test_redact_base64_blob():
    blob = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    text = f"run_job --auth {blob}"
    result = redact(text)
    assert blob not in result


def test_redact_no_sensitive_data_unchanged():
    text = "/usr/bin/backup.sh --verbose --output /var/log/backup.log"
    result = redact(text)
    # core path and flags should survive (no secrets present)
    assert "/usr/bin/backup.sh" in result
    assert "--verbose" in result


def test_redact_extra_patterns():
    cfg = RedactConfig(extra_patterns=[r"MY_CUSTOM_\w+"])
    text = "run_job MY_CUSTOM_VALUE --flag"
    result = redact(text, cfg)
    assert "MY_CUSTOM_VALUE" not in result


def test_redact_config_from_dict_defaults():
    cfg = redact_config_from_dict({})
    assert cfg.enabled is True
    assert cfg.extra_patterns == []


def test_redact_config_from_dict_full():
    cfg = redact_config_from_dict(
        {"redact": {"enabled": False, "extra_patterns": [r"MYTOKEN_\S+"]}}
    )
    assert cfg.enabled is False
    assert r"MYTOKEN_\S+" in cfg.extra_patterns


def test_redact_event_command_delegates():
    cmd = "deploy --secret topsecret"
    result = redact_event_command(cmd)
    assert "topsecret" not in result


def test_redact_none_cfg_uses_defaults():
    text = "job --token abc123"
    result = redact(text, None)
    assert "abc123" not in result
